import json
from pathlib import Path
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).parents[1]))
from muse_test_app import Handler, Session, ThreadingHTTPServer


class AppTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.session = Session()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.session.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.assertFalse(self.thread.is_alive())
        worker = self.server.session.worker
        self.assertFalse(worker and worker.is_alive())

    def post(self, route, data, origin=None):
        request = urllib.request.Request(self.url + '/api/' + route, data=json.dumps(data).encode(),
                                         headers={'Content-Type': 'application/json', 'X-Muse-Test': '1',
                                                  'Origin': origin or self.url})
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def wait_for(self, predicate, seconds=5):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            with urllib.request.urlopen(self.url + '/api/state') as response:
                state = json.load(response)
            if predicate(state):
                return state
            time.sleep(.05)
        self.fail('Timed out waiting for session state')

    def test_simulation_through_http(self):
        with urllib.request.urlopen(self.url) as response:
            self.assertEqual(response.status, 200)
        self.post('start', {'mode': 'synthetic'})
        self.wait_for(lambda state: state['status'] == 'ready')
        self.post('inject', {'count': 2})
        state = self.wait_for(lambda state: state['doubles'] == 1)
        self.assertEqual(state['blinks'], 2)
        self.assertEqual(state['mode'], 'synthetic')
        self.assertGreater(len(state['samples']), 0)
        self.post('stop', {})
        self.wait_for(lambda state: state['status'] == 'stopped')

    def test_cross_origin_and_live_confirmation(self):
        for data, origin, expected in (({'mode': 'synthetic'}, 'https://untrusted.example', 403),
                                       ({'mode': 'real_device'}, self.url, 400),
                                       ({'mode': 'synthetic', 'threshold': 'NaN'}, self.url, 400)):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.post('start', data, origin)
            self.assertEqual(error.exception.code, expected)
        self.assertIsNone(self.server.session.worker)

    def test_unknown_paths_not_served(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.url + '/muse_blinks.py')
        self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
