"""Local recorder worker tests; all EEG here is explicitly synthetic."""
from copy import deepcopy
import threading

import pytest

from modules.muse.acquisition.store import replay
from services.bridge.server import chunk
from services.bridge.ble_source import ble_metadata
from tools.muse_ble_recording import LocalRecording


def fixture_data():
    metadata = ble_metadata()
    raw = chunk(metadata, [[1., -2.], [3., -4.]], [1., 1. + 1 / 256], 0, 0, 2., 'fixture-host')
    return metadata, raw


def test_explicit_recording_preserves_values_clocks_and_closes(tmp_path):
    metadata, raw = fixture_data()
    expected = deepcopy(raw)
    worker = LocalRecording(tmp_path / 'raw')
    worker.submit(metadata, raw)
    raw['samples'][0][0] = 999.
    worker.close()
    assert not worker.thread.is_alive()
    assert list(replay(worker.path)) == [expected]
    summary = worker.summary()
    assert summary['replay_validation'] == 'PASS'
    assert summary['samples_per_channel'] == 2
    assert summary['source_mode'] == 'synthetic'
    assert 'samples' not in summary
    assert worker.path.stat().st_mode & 0o777 == 0o700
    assert (worker.path / 'manifest.json').stat().st_mode & 0o777 == 0o600


def test_no_samples_creates_no_raw_session(tmp_path):
    worker = LocalRecording(tmp_path / 'none')
    worker.close('diagnostic_failed')
    assert worker.summary() == {'recording_created': False}
    assert not worker.path.exists()


def test_full_queue_fails_without_silent_loss(tmp_path, monkeypatch):
    release = threading.Event()
    original = LocalRecording._write
    monkeypatch.setattr(LocalRecording, '_write', lambda self: (release.wait(3), original(self)))
    worker = LocalRecording(tmp_path / 'bounded', capacity=1)
    try:
        metadata, raw = fixture_data()
        worker.submit(metadata, raw)
        with pytest.raises(ValueError, match='recording_buffer_full'):
            worker.submit(metadata, raw)
    finally:
        release.set()
        worker.close('diagnostic_failed')
    assert worker.summary()['chunks'] == 1


def test_writer_failure_propagates_and_stops_thread(tmp_path):
    metadata, raw = fixture_data()
    raw['sequence'] = 9
    worker = LocalRecording(tmp_path / 'invalid')
    worker.submit(metadata, raw)
    with pytest.raises(ValueError, match='initial_indices'):
        worker.close()
    assert not worker.thread.is_alive()
