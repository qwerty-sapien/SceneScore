"""Loopback-only HTML test app for the MU-02 detector. Run, then open the printed URL."""
from __future__ import annotations

import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import threading
import time
from types import SimpleNamespace

from muse_blinks import Detector, live


class Session:
    def __init__(self):
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.worker = None
        self.status, self.mode, self.error = 'idle', 'synthetic', None
        self.samples, self.events = deque(maxlen=600), deque(maxlen=100)
        self.blinks = self.doubles = self.progress = 0
        self.pulses = []
        self.sim_time = 0
        self.last_poll = time.monotonic()

    def snapshot(self):
        with self.lock:
            self.last_poll = time.monotonic()
            return dict(status=self.status, mode=self.mode, error=self.error,
                        samples=list(self.samples), events=list(self.events),
                        blinks=self.blinks, doubles=self.doubles, progress=self.progress)

    def event(self, event, mode):
        with self.lock:
            if event['event'] == 'ready':
                self.status = 'ready'
            self.blinks += event['event'] == 'blink'
            self.doubles += event['event'] == 'double_blink'
            self.events.append(dict(event, source_mode=mode, received=time.time()))

    def sample(self, timestamp, values, count, rate, calibration):
        with self.lock:
            if count % 4 == 0:
                self.samples.append([timestamp, *values])
            self.progress = min(1, count / (rate * calibration))
            if self.status == 'connecting':
                self.status = 'calibrating'

    def start(self, config):
        mode = config.get('mode', 'synthetic')
        threshold = float(config.get('threshold', 5))
        if mode not in ('synthetic', 'real_device') or not 2 <= threshold <= 20:
            raise ValueError('Invalid source or sensitivity')
        if mode == 'real_device' and config.get('unplugged') is not True:
            raise ValueError('Unplug the charged headset before connecting')
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError('Stop the current session first')
            self.stop.clear()
            self.mode, self.status, self.error = mode, 'connecting', None
            self.samples.clear()
            self.events.clear()
            self.blinks = self.doubles = self.progress = 0
            self.pulses = []
            self.sim_time = 0
            self.last_poll = time.monotonic()
            self.worker = threading.Thread(target=self.run, args=(threshold, str(config.get('name', ''))[:80]), daemon=True)
            self.worker.start()

    def run(self, threshold, name):
        try:
            if self.mode == 'real_device':
                args = SimpleNamespace(name=name, seconds=600, calibration=10, threshold=threshold, gap=.5)
                live(args, on_event=self.event, on_sample=self.sample, stop=self.stop)
            else:
                detector = Detector(calibration=3, threshold=threshold)
                began = time.monotonic()
                count = 0
                while not self.stop.wait(.015) and time.monotonic() - began < 600:
                    target = int((time.monotonic() - began) * 256)
                    while count <= target:
                        t = count / 256
                        with self.lock:
                            self.sim_time = t
                            self.pulses = [p for p in self.pulses if t - p < 1]
                            peaks = list(self.pulses)
                        x = 2 * math.sin(2 * math.pi * 3 * t) + math.sin(2 * math.pi * 7 * t)
                        x += sum(160 * math.exp(-((t - p) / .045) ** 2) for p in peaks)
                        for event in detector.feed(t, [800 + x, 810 + .95 * x]):
                            self.event(event, 'synthetic')
                        self.sample(t, detector.smooth, detector.count, 256, 3)
                        count += 1
        except Exception as exc:
            with self.lock:
                self.error = ('BrainFlow is not installed. Follow the install command in tools/MUSE_BLINKS.md.'
                              if isinstance(exc, ImportError) else str(exc))
                self.status = 'error'
        finally:
            with self.lock:
                if self.status != 'error':
                    self.status = 'stopped'

    def inject(self, count):
        with self.lock:
            if self.mode != 'synthetic' or self.status != 'ready' or count not in (1, 2, 3):
                raise ValueError('Start the simulation and wait until ready')
            if self.pulses:
                raise ValueError('Wait for the previous gesture to finish')
            self.pulses = [self.sim_time + .15 + .4 * i for i in range(count)]

    def close(self):
        self.stop.set()
        if self.worker:
            self.worker.join(timeout=20)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, kind='application/json'):
        encoded = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(encoded)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def trusted(self):
        expected = f'127.0.0.1:{self.server.server_port}'
        return self.headers.get('Host') == expected

    def do_GET(self):
        if not self.trusted():
            return self.reply(403, {'error': 'Use the printed loopback URL'})
        if self.path == '/api/state':
            return self.reply(200, self.server.session.snapshot())
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path not in files:
            return self.reply(404, {'error': 'Not found'})
        name, kind = files[self.path]
        self.reply(200, (Path(__file__).parent / 'muse-test-ui' / name).read_bytes(), kind)

    def do_POST(self):
        if (not self.trusted() or self.headers.get('X-Muse-Test') != '1'
                or self.headers.get('Origin') != f'http://127.0.0.1:{self.server.server_port}'):
            return self.reply(403, {'error': 'Same-origin requests only'})
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 2048:
                raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Expected an object')
            if self.path == '/api/start':
                self.server.session.start(data)
            elif self.path == '/api/stop':
                self.server.session.stop.set()
            elif self.path == '/api/inject':
                self.server.session.inject(data.get('count'))
            else:
                return self.reply(404, {'error': 'Not found'})
            self.reply(200, {'ok': True})
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8780)
    args = parser.parse_args()
    session = Session()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.session = session
    server.timeout = .25
    print(f'Muse test panel: http://127.0.0.1:{server.server_port}', flush=True)
    print('Ctrl-C stops the server and releases the headset. No EEG is saved or uploaded.', flush=True)
    try:
        while True:
            server.handle_request()
            if time.monotonic() - session.last_poll > 5:
                session.stop.set()
    except KeyboardInterrupt:
        pass
    finally:
        session.close()
        server.server_close()


if __name__ == '__main__':
    main()
