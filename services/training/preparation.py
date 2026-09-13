"""Local connection and in-memory EEG check before recording is permitted."""
from collections import deque
import copy
import math
import queue
import secrets
import threading
import time

from modules.muse.acquisition.ble import BleMuseManager
from services.training.brainflow_source import BrainFlowSource


class BluetoothSource:
    """Trainer-owned adapter; the shared BLE manager remains unchanged."""
    def __init__(self, manager_factory=BleMuseManager, *, progress=None):
        self.frames = queue.Queue(maxsize=64)
        self.error = None
        self.closed = False
        self.manager = manager_factory(on_frame=self._frame, on_fault=self._fault, on_discontinuity=self._fault)
        try:
            session = "trainer-" + secrets.token_hex(12)
            devices = self.manager.scan(session)["devices"]
            if len(devices) != 1:
                raise ValueError("Muse did not advertise during the scan. Switch it off and back on, then reconnect." if not devices
                                 else "More than one Muse found. Switch off the other headset, then reconnect.")
            if progress is not None:
                progress("Muse found. Connecting and starting EEG…")
            self.manager.connect(devices[0]["id"], session)
            self.description = {"id": "local-muse-bluetooth", "name": devices[0]["name"],
                                "transport": "bleak", "sample_rate_hz": 256,
                                "channels": [{"name": n, "unit": "uV"} for n in ("TP9", "AF7", "AF8", "TP10")],
                                "frontal_indices": [1, 2], "original_channels": [],
                                "observed_profile": "classic-muse-gatt", "hardware_verified": False}
        except BaseException:
            self.close()
            raise

    def _fault(self, reason):
        self.error = reason

    def _frame(self, frame):
        try:
            self.frames.put_nowait(frame)
        except queue.Full:
            self.error = "EEG buffer fell behind. Reconnect your headset."

    def pull(self):
        if self.error:
            raise ValueError(self.error)
        if self.closed:
            return [], []
        try:
            frame = self.frames.get(timeout=.1)
        except queue.Empty:
            return [], []
        if time.monotonic() - frame.received_monotonic_s > .5:
            raise ValueError("EEG samples are delayed. Reconnect your headset.")
        return [list(row) for row in frame.samples_uv], list(frame.device_times_s)

    def close(self):
        if not self.closed:
            self.closed = True
            self.manager.close()


class Preparation:
    def __init__(self, sources, *, bluetooth_factory=None, clock=time.monotonic):
        self.sources, self.bluetooth_factory, self.clock = sources, bluetooth_factory, clock
        self.lock = threading.RLock()
        self.thread = None
        self.cancel = threading.Event()
        self.source = None
        self.closed = self.handoff = False
        self.state, self.message = "idle", "Switch on your Muse, then connect it."
        self.subscriber = clock()
        self.last_host = None
        self.received_samples = 0
        self.signal = {"measurable": False, "seconds": 0, "peak_to_peak_uv": [], "rate_hz": None}

    def snapshot(self, *, touch=False):
        with self.lock:
            if touch:
                self.subscriber = self.clock()
            fresh = self.last_host is not None and self.clock() - self.last_host <= .5
            return {"state": self.state, "message": self.message,
                    "ready": self.state == "ready" and fresh and not self.cancel.is_set(),
                    "signal": {**self.signal, "measurable": self.signal["measurable"] and fresh},
                    "recording": False}

    def connect(self, *, synthetic=False):
        with self.lock:
            if self.closed or self.thread and self.thread.is_alive():
                raise ValueError("Connection is already being checked.")
            self.cancel = threading.Event()
            self.handoff, self.last_host = False, None
            self.received_samples = 0
            self.signal = {"measurable": False, "seconds": 0, "peak_to_peak_uv": [], "rate_hz": None}
            self.state, self.message = "connecting", "Connecting to your headset…"
            self.subscriber = self.clock()
            self.thread = threading.Thread(target=self._worker, args=(synthetic,), name="trainer-eeg-check", daemon=False)
            self.thread.start()
        return self.snapshot()

    def _open(self, synthetic):
        if synthetic:
            return self.sources.open("synthetic")
        # "synthetic" is reserved by Sources.open; never select it from real
        # discovery and silently turn a real-device run into a fixture.
        discovered = [s for s in self.sources.discover()["sources"] if s["id"] != "synthetic"]
        if len(discovered) > 1:
            raise ValueError("More than one EEG stream found. Leave only your Muse stream running.")
        if discovered:
            return self.sources.open(discovered[0]["id"])
        if self.bluetooth_factory is not None:
            return self.bluetooth_factory()
        return BrainFlowSource(cancel=self.cancel, on_progress=self._progress)

    def _progress(self, message):
        with self.lock:
            self.message = message

    def _worker(self, synthetic):
        started, samples = self.clock(), deque(maxlen=4096)
        try:
            self.source = self._open(synthetic)
            description = self.source.description
            rate, indices = description["sample_rate_hz"], description["frontal_indices"]
            if not 32 <= rate <= 1024 or len(indices) != 2:
                raise ValueError("A supported source with two frontal EEG channels is required.")
            with self.lock:
                self.state, self.message = "checking", "Headset connected. Checking for measurable EEG…"
            opened = self.clock()
            while not self.cancel.is_set():
                now = self.clock()
                if now - self.subscriber > 5 or now - started > 180:
                    raise ValueError("Connection check ended. Reconnect when you are ready.")
                rows, times = self.source.pull()
                if not times:
                    if now - (self.last_host if self.last_host is not None else opened) > 2:
                        raise ValueError("Headset connected, but no fresh EEG is arriving. Check the fit and reconnect.")
                    continue
                if (len(rows) != len(times) or not 1 <= len(times) <= 128
                        or any(not isinstance(t, (int, float)) or not math.isfinite(t) or t < 0 for t in times)
                        or any(len(row) != len(description["channels"]) or any(not isinstance(v, (int, float))
                               or not math.isfinite(v) or abs(v) > 1e9 for v in row) for row in rows)):
                    raise ValueError("Invalid EEG samples. Reconnect your headset.")
                for t, row in zip(times, rows):
                    if samples and not .5 / rate <= t - samples[-1][0] <= 1.5 / rate:
                        samples.clear()
                    samples.append((t, row))
                while samples and samples[0][0] < times[-1] - 3:
                    samples.popleft()
                duration = samples[-1][0] - samples[0][0]
                spans = [max(row[i] for _, row in samples) - min(row[i] for _, row in samples) for i in indices]
                observed_rate = (len(samples) - 1) / duration if duration else None
                measurable = (duration >= 3 - 1.1 / rate and all(span >= 1 for span in spans)
                              and observed_rate is not None and abs(observed_rate / rate - 1) <= .02)
                with self.lock:
                    self.last_host = self.clock()
                    self.received_samples += len(times)
                    self.signal = {"measurable": measurable, "seconds": duration,
                                   "peak_to_peak_uv": spans, "rate_hz": observed_rate,
                                   "received_samples": self.received_samples,
                                   "eeg_channels": len(description["channels"])}
                    self.state = "ready" if measurable else "checking"
                    receipt = f"Connected · received {self.received_samples:,} samples on {len(description['channels'])} EEG channels. "
                    self.message = receipt + ("Measurable EEG detected. Ready to train." if measurable else
                                              "Checking for measurable EEG…")
                if not measurable and self.clock() - opened > 20:
                    raise ValueError("No stable, measurable EEG yet. Adjust the headset and reconnect.")
        except Exception as error:
            friendly = {"bluetooth_permission_denied": "Allow Bluetooth for the local launcher in System Settings, then reconnect.",
                        "bluetooth_powered_off": "Switch on Bluetooth, then reconnect.",
                        "bluetooth_unavailable": "Bluetooth is unavailable. Check local Bluetooth access, then reconnect.",
                        "connect_timeout": "Muse found, but Bluetooth connection timed out. Power-cycle it and reconnect.",
                        "scan_timeout": "Bluetooth scanning timed out. Check Bluetooth access and reconnect.",
                        "stream_start_timeout": "Headset connected, but EEG did not start. Close other Muse apps and reconnect."}
            with self.lock:
                self.state, self.message = "error", friendly.get(str(error), str(error))
        finally:
            if self.source is not None and (not self.handoff or self.state == "error"):
                try:
                    self.source.close()
                except Exception as error:
                    self.state, self.message = "error", "Headset disconnect failed: " + str(error)
                self.source = None
            if self.state != "error" and not self.handoff:
                self.state, self.message = "idle", "Connection closed. Reconnect when you are ready."

    def take(self):
        with self.lock:
            if not self.snapshot()["ready"]:
                raise ValueError("Connect the headset and wait for measurable EEG before training.")
            self.handoff = True
            self.cancel.set()
            evidence = copy.deepcopy(self.signal)
        self.thread.join(3)
        with self.lock:
            if self.thread.is_alive() or self.state == "error":
                self.handoff = False
                raise ValueError("EEG check changed. Reconnect before training.")
            source, self.source = self.source, None
            self.state, self.message = "idle", "Reconnect to check EEG before your next training session."
            self.last_host = None
            return source, evidence

    def stop(self):
        self.cancel.set()
        return self.snapshot()

    def close(self):
        self.closed = True
        self.stop()
        if self.thread:
            self.thread.join(55)
            if self.thread.is_alive():
                raise RuntimeError("EEG_check_worker_did_not_exit")
