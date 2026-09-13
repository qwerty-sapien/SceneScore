"""Bounded local recording worker for the explicit BLE diagnostic command."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import queue
import threading

from modules.muse.acquisition.store import Recorder, manifest, replay


class LocalRecording:
    """Keep filesystem sync off the BLE loop; overflow ends capture visibly."""

    def __init__(self, path: Path, *, capacity=128):
        if path.exists():
            raise ValueError('recording_path_exists')
        self.path = path
        self.queue = queue.Queue(maxsize=capacity)
        self.done = threading.Event()
        self.error = None
        self.recorder = None
        self.reason = 'diagnostic_complete'
        self.thread = threading.Thread(target=self._write, name='scenescore-ble-recorder', daemon=False)
        self.thread.start()

    def submit(self, metadata, chunk):
        self.check()
        if self.done.is_set():
            raise ValueError('recording_closed')
        try:
            self.queue.put_nowait((deepcopy(metadata), deepcopy(chunk)))
        except queue.Full:
            raise ValueError('recording_buffer_full') from None

    def check(self):
        if self.error is not None:
            raise self.error

    def _write(self):
        try:
            while not self.done.is_set() or not self.queue.empty():
                try:
                    metadata, chunk = self.queue.get(timeout=.1)
                except queue.Empty:
                    continue
                if self.recorder is None:
                    self.recorder = Recorder(self.path, metadata, explicitly_started=True)
                self.recorder.append(chunk)
        except Exception as error:
            self.error = error
        finally:
            if self.recorder is not None:
                try:
                    self.recorder.close('recording_failed' if self.error else self.reason)
                except Exception as error:
                    self.error = error

    def close(self, reason='diagnostic_complete'):
        self.reason = reason
        self.done.set()
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            raise RuntimeError('recording_thread_shutdown_failed')
        self.check()

    def summary(self):
        """Validate replay without returning any EEG values to the console."""
        if self.thread.is_alive():
            raise ValueError('recording_still_active')
        self.check()
        if self.recorder is None:
            return {'recording_created': False}
        chunks = samples = dropped = 0
        first = last = None
        for chunk in replay(self.path):
            chunks += 1
            samples += len(chunk['samples'])
            dropped += chunk['dropped_samples_before']
            first = chunk['device_times_s'][0] if first is None else first
            last = chunk['device_times_s'][-1]
        value = manifest(self.path)
        if value['status'] != 'closed' or value['committed_chunks'] != chunks:
            raise ValueError('recording_manifest_mismatch')
        return {'recording_created': True, 'path': str(self.path), 'replay_validation': 'PASS',
                'chunks': chunks, 'samples_per_channel': samples, 'dropped_samples': dropped,
                'channels': [c['name'] for c in value['metadata']['channels']],
                'source_mode': value['metadata']['provenance']['source_mode'],
                'device_duration_s': 0 if first is None else last - first + 1 / 256,
                'stop_reason': value['stop_reason']}
