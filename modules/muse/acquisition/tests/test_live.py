"""Fake transport tests only: these do not verify LSL/headset hardware."""
import sys
import threading
from types import SimpleNamespace
import pytest
from modules.muse.acquisition.live import capture_lsl
from modules.muse.acquisition.store import manifest, replay
from modules.muse.acquisition.tests.helpers import metadata


def fake_lsl(monkeypatch, *, fault=False, mismatch=False, cancel=False):
    closed = []
    channel_index = [0]
    stop = threading.Event()

    class Channel:
        def child_value(self, name):
            if name == 'label':
                return ['AF7', 'AF8'][channel_index[0]]
            return 'V' if mismatch else 'uV'

        def next_sibling(self):
            channel_index[0] += 1
            return self

    class Description:
        def child(self, name):
            return Channel() if name == 'channel' else self

    class Info:
        def channel_count(self):
            return 2

        def nominal_srate(self):
            return 256

        def desc(self):
            return Description()

    class Inlet:
        def __init__(self, *args, **kwargs):
            self.count = 0
            assert kwargs['recover'] is False

        def pull_chunk(self, **kwargs):
            if fault:
                raise RuntimeError('simulated_disconnect')
            self.count += 1
            stop.set()
            return [[1.2, -3.4], [5.6, 7.8]], [10, 10+1/256]

        def close_stream(self):
            closed.append(True)

    if cancel:
        stop.set()
    monkeypatch.setitem(sys.modules, 'pylsl', SimpleNamespace(resolve_byprop=lambda *a, **k: [Info()], StreamInlet=Inlet))
    return stop, closed


def live_metadata():
    meta = metadata()
    meta.update(hardware_verified=True, device_model='operator-fixture-not-real', transport='lsl')
    meta['provenance']['source_mode'] = 'real_device'
    return meta


def test_fake_transport_preserves_raw_and_closes_on_cancel(tmp_path, monkeypatch):
    stop, closed = fake_lsl(monkeypatch)
    result = capture_lsl(tmp_path/'s', live_metadata(), source_id='fixture', seconds=1, consent=True, stop=stop, report=lambda x: None)
    assert result['status'] == 'cancelled'
    assert closed == [True]
    rows = list(replay(tmp_path/'s'))
    assert rows[0]['samples'] == [[1.2, -3.4]]
    assert rows[1]['device_times_s'] == [10+1/256]
    assert rows[0]['host_receipt'] == rows[1]['host_receipt']
    assert rows[0]['quality']['state'] == 'unverified'


def test_fake_disconnect_closes_recoverable_recording(tmp_path, monkeypatch):
    stop, closed = fake_lsl(monkeypatch, fault=True)
    with pytest.raises(RuntimeError):
        capture_lsl(tmp_path/'s', live_metadata(), source_id='fixture', seconds=1, consent=True, stop=stop, report=lambda x: None)
    assert closed == [True]
    assert manifest(tmp_path/'s')['stop_reason'] == 'fault_disconnect_rearm_required'
    assert list(replay(tmp_path/'s')) == []


def test_fake_units_mismatch_rejected_before_recording(tmp_path, monkeypatch):
    _, closed = fake_lsl(monkeypatch, mismatch=True)
    with pytest.raises(ValueError, match='unit_unverified'):
        capture_lsl(tmp_path/'s', live_metadata(), source_id='fixture', seconds=1, consent=True)
    assert not (tmp_path/'s').exists()
    assert closed == []


def test_pre_cancel_still_tears_down(tmp_path, monkeypatch):
    stop, closed = fake_lsl(monkeypatch, cancel=True)
    capture_lsl(tmp_path/'s', live_metadata(), source_id='fixture', seconds=1, consent=True, stop=stop, report=lambda x: None)
    assert closed == [True]
    assert list(replay(tmp_path/'s')) == []


def test_empty_stream_fails_loudly_and_closes(tmp_path, monkeypatch):
    from modules.muse.acquisition import live
    closed = []
    channel_index = [0]
    class Channel:
        def child_value(self, name):
            return ["AF7", "AF8"][channel_index[0]] if name == "label" else "uV"
        def next_sibling(self):
            channel_index[0] += 1
            return self
    class Description:
        def child(self, name):
            return Channel() if name == "channel" else self
    info = SimpleNamespace(channel_count=lambda: 2, nominal_srate=lambda: 256, desc=Description)
    class Inlet:
        def __init__(self, *args, **kwargs):
            pass
        def pull_chunk(self, **kwargs):
            return [], []
        def close_stream(self):
            closed.append(True)
    ticks = iter([0.0, 0.1, 3.0])
    monkeypatch.setattr(live.time, "monotonic", lambda: next(ticks))
    monkeypatch.setitem(sys.modules, "pylsl", SimpleNamespace(resolve_byprop=lambda *a, **k: [info], StreamInlet=Inlet))
    with pytest.raises(RuntimeError, match="NO_SAMPLES_RECORDED"):
        capture_lsl(tmp_path / "s", live_metadata(), source_id="fixture", seconds=10, consent=True, report=lambda x: None)
    assert closed == [True]
    assert manifest(tmp_path / "s")["committed_chunks"] == 0
