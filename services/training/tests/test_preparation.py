import math
import time
from types import SimpleNamespace

import pytest

from services.training.preparation import BluetoothSource, Preparation
from services.training.sources import Sources, SyntheticSource


def wait(predicate, seconds=6):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError('fixture did not reach expected state')


def test_measurable_check_is_memory_only_and_handoff_keeps_same_source():
    prep = Preparation(Sources())
    try:
        with pytest.raises(ValueError, match='measurable EEG'):
            prep.take()
        prep.connect(synthetic=True)
        wait(lambda: prep.snapshot(touch=True)['ready'])
        source = prep.source
        snapshot = prep.snapshot()
        assert snapshot['signal']['seconds'] >= 2.99 and not snapshot['recording']
        assert snapshot['signal']['received_samples'] >= 768
        assert snapshot['signal']['eeg_channels'] == 2
        assert 'Connected · received' in snapshot['message']
        got, evidence = prep.take()
        assert got is source and not source.closed and evidence['measurable']
        assert not prep.snapshot()['ready'] and not prep.thread.is_alive()
        got.close()
    finally:
        prep.close()


def test_flat_or_gapped_EEG_never_enables_training_and_worker_closes():
    for gapped in (False, True):
        clock = [0.0]
        closed = []
        description = {**SyntheticSource.description, 'sample_rate_hz': 64}
        def pull():
            start = clock[0]
            clock[0] += .5
            times = [start + i / (32 if gapped else 64) for i in range(32)]
            rows = [[math.sin(t * 12), math.cos(t * 9)] if gapped else [0, 0] for t in times]
            return rows, times
        source = SimpleNamespace(description=description, pull=pull, close=lambda: closed.append(True))
        prep = Preparation(SimpleNamespace(open=lambda _: source), clock=lambda: clock[0])
        prep.connect(synthetic=True)
        prep.thread.join(3)
        assert not prep.snapshot()['ready'] and closed and not prep.thread.is_alive()
        prep.close()


def test_stale_ready_check_cannot_be_used_for_training():
    prep = Preparation(Sources(), clock=lambda: 10.)
    prep.state, prep.last_host = 'ready', 9.
    prep.signal['measurable'] = True
    assert not prep.snapshot()['ready']
    with pytest.raises(ValueError, match='measurable EEG'):
        prep.take()
    prep.close()


def test_bluetooth_source_uses_real_frames_without_attesting_contact_or_identity():
    calls = []
    class Manager:
        def __init__(self, **callbacks):
            self.callbacks = callbacks
        def scan(self, session):
            calls.append(('scan', session))
            return {'devices': [{'id': 'opaque', 'name': 'Muse-fixture'}]}
        def connect(self, device, session):
            calls.append(('connect', device, session))
            self.callbacks['on_frame'](SimpleNamespace(received_monotonic_s=time.monotonic(),
                                                       samples_uv=((1, 2, 3, 4),), device_times_s=(5.,)))
        def close(self):
            calls.append(('close',))
    source = BluetoothSource(Manager)
    assert source.description['transport'] == 'bleak'
    assert source.description['hardware_verified'] is False
    assert source.pull() == ([[1, 2, 3, 4]], [5.])
    source.close()
    assert calls[-1] == ('close',)
    assert calls[0][1] == calls[1][2]


def test_ambiguous_headsets_close_bluetooth_manager():
    closed = []
    manager = SimpleNamespace(scan=lambda _: {'devices': [{'id': 'one'}, {'id': 'two'}]}, close=lambda: closed.append(True))
    with pytest.raises(ValueError, match='More than one Muse'):
        BluetoothSource(lambda **_: manager)
    assert closed


def test_real_discovery_cannot_select_the_reserved_synthetic_source():
    source = object()
    sources = SimpleNamespace(discover=lambda: {"sources": [{"id": "synthetic"}]},
                              open=lambda _: pytest.fail("Synthetic source selected as real"))
    prep = Preparation(sources, bluetooth_factory=lambda: source)
    assert prep._open(False) is source
    prep.close()
