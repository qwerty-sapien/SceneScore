"""Synthetic software checks only; no hardware, participant or output claims."""
import json
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

from services.bridge.server import BridgeServer, Companion, synthetic_source

ORIGIN = 'http://127.0.0.1:5173'


@contextmanager
def served():
    companion = Companion()
    server = BridgeServer(companion, [ORIGIN, 'https://studio.example'], token='a' * 43, port=0)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, name='test-muse-http')
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


def request(server, path, *, method='GET', token=None, origin=ORIGIN, host=None, body=None):
    headers = {'Origin': origin}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if host:
        headers['Host'] = host
    if method == 'POST':
        headers['Content-Type'] = 'application/json'
    data = json.dumps({} if body is None else body).encode() if method == 'POST' else None
    req = urllib.request.Request(f'http://127.0.0.1:{server.server_port}{path}', data=data, method=method, headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, dict(response.headers), json.load(response)


def session(server):
    code, headers, value = request(server, '/v1/session', method='POST', token=server.token)
    assert code == 200
    assert headers['Access-Control-Allow-Origin'] == ORIGIN
    return value['session']


def test_origin_host_auth_and_narrow_commands():
    with served() as server:
        assert server.server_address[0] == '127.0.0.1'
        assert request(server, '/v1/status')[0] == 401
        assert request(server, '/v1/status', origin='https://unlisted.example')[0] == 403
        assert request(server, '/v1/status', host='unlisted.example')[0] == 403
        assert request(server, '/v1/session', method='POST', token='bad')[0] == 401
        token = session(server)
        assert request(server, '/v1/status', token=token, origin='https://studio.example')[0] == 401
        assert request(server, '/v1/execute', method='POST', token=token)[0] == 404
        assert request(server, '/v1/arm', method='POST', token=token, body={'source': '/any/path'})[0] == 400
        assert request(server, '/v1/arm', method='POST', token=token)[2]['error'] == 'source_not_connected'
        code, _, status = request(server, '/v1/status', token=token)
        assert code == 200 and status['recording'] is False and status['mode'] == 'SYNTHETIC_TEST'
        assert not any(key in status for key in ['samples', 'raw_channels', 'device_times_s'])
        assert request(server, '/v1/events?cursor=900', token=token)[0] == 400
        server.sessions[token] = (time.monotonic() - 1, ORIGIN)
        assert request(server, '/v1/status', token=token)[0] == 401


def test_live_never_arms_without_verified_stream_quality():
    companion = Companion(mode='LIVE_MUSE')
    companion.connected = True
    companion.quality = 'good'
    companion.detector.count = 1000
    with pytest.raises(ValueError, match='hardware_not_verified'):
        companion.arm()
    companion.metadata['hardware_verified'] = True
    companion.stream_verified = True
    companion.quality = 'unverified'
    with pytest.raises(ValueError, match='quality_not_verified_good'):
        companion.arm()


def test_actual_synthetic_source_closes_one_double_then_fault_clears_state():
    companion = Companion()
    stop = threading.Event()
    source = threading.Thread(target=synthetic_source, args=(companion, stop), name='test-muse-synthetic-source')
    source.start()
    events = []
    cursor = 0
    deadline = time.monotonic() + 6
    try:
        while time.monotonic() < deadline:
            batch = companion.subscribe(cursor)
            cursor = batch['cursor']
            events.extend(batch['events'])
            if batch['status']['warmup_ready'] and not batch['status']['armed']:
                companion.arm()
            if any(event['kind'] == 'gesture' for event in events):
                break
        candidates = [event for event in events if event['kind'] == 'candidate']
        gestures = [event for event in events if event['kind'] == 'gesture']
        assert len(candidates) == 2
        assert len(gestures) == 1
        gesture = gestures[0]['gesture']
        assert gesture['provenance']['source_mode'] == 'synthetic'
        assert gesture['gesture_count'] == 2
        assert gesture['closure_delay_s'] > .5
        assert companion.clock()['uncertainty_s'] < .05
        serialized = json.dumps(events)
        assert '"samples"' not in serialized and 'raw_channels' not in serialized
        companion.fault('test_dropout')
        state = companion.status()
        assert state['armed'] is False and state['warmup_ready'] is False
        assert not companion.detector.grammar.pending
    finally:
        stop.set()
        source.join(2)
        assert not source.is_alive()


def test_reconnect_and_event_overflow_require_rearm():
    with served() as server:
        companion = server.companion
        companion.detector.armed = True
        session(server)
        assert not companion.detector.armed
        with companion.lock:
            for number in range(140):
                companion._emit('status', at_s=number, reason='fixture')
        companion.detector.armed = True
        assert companion.subscribe(0)['overflow']
        assert not companion.detector.armed


def test_signal_quality_stale_status_clears_armed_state():
    class Gate:
        def status(self, now, epoch):
            return {'state': 'bad', 'reason': 'signal_quality_stale'}
        def reset(self):
            pass
    companion = Companion()
    companion.connected = True
    companion.detector.armed = True
    companion.quality_gate = Gate()
    status = companion.status()
    assert status['armed'] is False
    assert status['quality'] == 'bad'
    assert status['reason'] == 'signal_quality_stale'


@pytest.mark.parametrize('profile', [None, {'mock_only': 'eligible-profile'}])
def test_live_source_wires_quality_full_descriptor_and_closes_inlet(monkeypatch, profile):
    """Mock LSL and gate wiring only. No real-device evidence is generated."""
    import sys
    from types import SimpleNamespace
    from services.bridge import lsl_clock
    from services.bridge.server import live_lsl_source, synthetic_metadata
    stopped = threading.Event()
    quality_calls = []
    class Gate:
        def __init__(self, metadata, supplied):
            assert supplied == profile
        def consume(self, raw):
            quality_calls.append((raw['sequence'], raw['samples'][0][:]))
            return self.status(0, '')
        def status(self, now, epoch):
            return {'state': 'good' if profile else 'unverified',
                    'reason': 'calibrated_signal_checks_passed_contact_not_measured' if profile else 'calibrated_quality_profile_missing'}
        def reset(self):
            pass
    monkeypatch.setitem(sys.modules, 'modules.muse.runtime.quality', SimpleNamespace(QualityGate=Gate))
    class Descriptor:
        def __init__(self, index=0):
            self.index = index
        def child(self, name):
            return self
        def child_value(self, name):
            return ['AF7', 'AF8'][self.index] if name == 'label' else 'uV'
        def next_sibling(self):
            return Descriptor(self.index + 1)
    class Info:
        def channel_count(self):
            return 2
        def nominal_srate(self):
            return 256
        def desc(self):
            return Descriptor()
    class Inlet:
        full_info_requested = False
        closed = False
        count = 0
        def info(self, timeout):
            self.full_info_requested = True
            return Info()
        def was_clock_reset(self):
            return False
        def pull_chunk(self, timeout, max_samples):
            assert max_samples == 4
            start = self.count
            self.count += 4
            if self.count >= 320:
                stopped.set()
            return [[.1 * (number % 7), .1 * (number % 5)] for number in range(start, start + 4)], [number / 256 for number in range(start, start + 4)]
        def close_stream(self):
            self.closed = True
    inlet = Inlet()
    monkeypatch.setitem(sys.modules, 'pylsl', SimpleNamespace(resolve_byprop=lambda *args, **kwargs: [Info()], StreamInlet=lambda *args, **kwargs: inlet))
    monkeypatch.setattr(lsl_clock, 'LSLClock', lambda *args: SimpleNamespace(probe=lambda: {'device_s': 0, 'host_s': 0, 'uncertainty_s': .01}))
    metadata = synthetic_metadata()
    metadata['provenance']['source_mode'] = 'real_device'
    metadata['transport'] = 'lsl'
    metadata['hardware_verified'] = True
    companion = Companion(metadata, mode='LIVE_MUSE')
    live_lsl_source(companion, stopped, 'mock-exact-source', profile)
    assert inlet.full_info_requested and inlet.closed
    assert len(quality_calls) == 320
    assert companion.stream_verified
    assert companion.source_clock_probe is None
    if profile:
        assert companion.arm()['armed']
    else:
        assert companion.status()['reason'] == 'calibrated_quality_profile_missing'
        with pytest.raises(ValueError, match='quality_not_verified_good'):
            companion.arm()


def test_actual_runtime_gate_rejects_synthetic_calibration_for_real_lsl():
    """Actual profile validation runs before optional pylsl or any stream acquisition."""
    import copy
    from modules.muse.acquisition.tests.helpers import metadata
    from modules.muse.runtime.tests.test_quality import profile
    from services.bridge.server import live_lsl_source
    synthetic_profile = profile()
    real_metadata = copy.deepcopy(metadata())
    real_metadata['provenance']['source_mode'] = 'real_device'
    real_metadata['hardware_verified'] = True
    real_metadata['transport'] = 'lsl'
    companion = Companion(real_metadata, mode='LIVE_MUSE')
    with pytest.raises(ValueError, match='quality_profile_'):
        live_lsl_source(companion, threading.Event(), 'never-opened', synthetic_profile)
    assert companion.sample_count == 0 and not companion.stream_verified
