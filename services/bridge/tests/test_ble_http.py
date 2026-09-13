"""Authenticated narrow BLE HTTP boundary; fixtures never access a headset."""
from contextlib import contextmanager
import json
import threading
import time

import pytest

from services.bridge.server import BridgeServer, Companion
from services.bridge.tests.test_bridge import ORIGIN, request, session


class Manager:
    def __init__(self, companion):
        self.companion = companion
        self.owner = None
        self.calls = []
        self.closed = False
        self.state = 'idle'

    def snapshot(self):
        return {'transport': 'bleak', 'bluetooth_state': self.state, 'device_name': 'Muse-fixture',
                'ble_connected': self.state == 'streaming', 'reconnect_required': False, 'last_error': None}

    def scan(self, owner):
        self.owner = owner
        self.calls.append('scan')
        return {'devices': [{'id': 'opaque-fixture', 'name': 'Muse-fixture'}]}

    def connect(self, device_id, owner):
        if owner != self.owner or device_id != 'opaque-fixture':
            raise ValueError('scan_result_expired')
        self.calls.append('connect')
        self.state = 'streaming'
        self.companion.connected = True

    def disconnect(self):
        self.calls.append('disconnect')
        self.state = 'disconnected'
        self.companion.fault('operator_disconnected_reconnect_required')

    def close(self):
        self.closed = True


@contextmanager
def served():
    companion = Companion(mode='LIVE_MUSE')
    manager = Manager(companion)
    server = BridgeServer(companion, [ORIGIN], token='t' * 43, port=0, muse_manager=manager)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, name='ble-http-fixture')
    thread.start()
    try:
        yield server, manager
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()
        assert manager.closed


def test_ble_auth_origin_host_no_cache_and_no_raw_responses(capsys):
    with served() as (server, manager):
        assert request(server, '/v1/muse/scan', method='POST')[0] == 401
        token = session(server)
        assert request(server, '/v1/muse/scan', method='POST', token=token,
                       origin='https://wrong.example')[0] == 403
        assert request(server, '/v1/muse/scan', method='POST', token=token,
                       host='evil.example')[0] == 403
        code, headers, result = request(server, '/v1/muse/scan', method='POST', token=token)
        assert code == 200 and headers['Cache-Control'] == 'no-store'
        assert result['devices'] == [{'id': 'opaque-fixture', 'name': 'Muse-fixture'}]
        assert result['status']['transport'] == 'bleak'
        code, _, status = request(server, '/v1/muse/connect', method='POST', token=token,
                                  body={'device_id': 'opaque-fixture'})
        assert code == 200 and status['connected'] and not status['hardware_verified']
        assert status['quality'] == 'unverified' and not status['armed']
        for forbidden in ('samples', 'device_times_s', 'raw_channels', 'address', 'token'):
            assert '"' + forbidden + '"' not in json.dumps([result, status])
        assert manager.calls == ['scan', 'connect']
    output = capsys.readouterr()
    assert token not in output.out + output.err


@pytest.mark.parametrize('body', [{}, {'device_id': ''}, {'device_id': 'x' * 129},
                                  {'device_id': 42}, {'device_id': True}, [], None,
                                  {'device_id': 'opaque-fixture', 'command': 'd'}])
def test_connect_accepts_exact_bounded_device_id_only(body):
    with served() as (server, manager):
        token = session(server)
        assert request(server, '/v1/muse/connect', method='POST', token=token, body=body)[0] == 400
        assert manager.calls == []


def test_scan_disconnect_empty_only_session_scoping_expiry_and_disarm():
    with served() as (server, manager):
        first = session(server)
        for path in ('/v1/muse/scan', '/v1/muse/disconnect'):
            assert request(server, path, method='POST', token=first, body={'path': '/tmp/raw'})[0] == 400
        request(server, '/v1/muse/scan', method='POST', token=first)
        second = session(server)
        assert request(server, '/v1/muse/connect', method='POST', token=second,
                       body={'device_id': 'opaque-fixture'})[2]['error'] == 'scan_result_expired'
        assert request(server, '/v1/muse/connect', method='POST', token=first,
                       body={'device_id': 'arbitrary-corebluetooth-uuid'})[0] == 400
        request(server, '/v1/muse/connect', method='POST', token=first, body={'device_id': 'opaque-fixture'})
        server.companion.detector.armed = True
        code, _, status = request(server, '/v1/muse/disconnect', method='POST', token=first)
        assert code == 200 and not status['armed'] and not status['connected']
        assert not server.companion.detector.grammar.pending
        server.sessions[first] = (time.monotonic() - 1, ORIGIN)
        assert request(server, '/v1/muse/scan', method='POST', token=first)[0] == 401
