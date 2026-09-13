"""Owned local Muse acquisition using the user's verified BrainFlow setup."""

import copy
import json
import math
import os
import select
import subprocess
import sys
import time


class BoardSource:
    """Runs on the helper's main thread; only EEG and source timestamps leave it."""

    def __init__(self, board_api=None, *, wall_clock=time.time, sleep=time.sleep, progress=None):
        if board_api is None:
            try:
                from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
            except ImportError as error:
                raise ValueError("BrainFlow is missing. Install tools/muse-training-requirements.txt in the launcher runtime.") from error
            board_api = BoardShim, BrainFlowInputParams, int(BoardIds.MUSE_2_BOARD)
        shim, params_type, board_id = board_api
        shim.enable_dev_board_logger()
        self.board = None
        self.started = self.closed = False
        self.wall_clock, self.sleep = wall_clock, sleep
        descriptor = shim.get_board_descr(board_id)
        names = descriptor["eeg_names"].split(",")
        self.channels = descriptor["eeg_channels"]
        self.timestamp = descriptor["timestamp_channel"]
        self.rate = descriptor["sampling_rate"]
        if (len(names) != len(self.channels) or not {"AF7", "AF8"}.issubset(names)
                or not 32 <= self.rate <= 1024):
            raise ValueError("BrainFlow did not provide a compatible frontal EEG descriptor.")
        self.description = {
            "id": "local-muse-brainflow", "name": descriptor["name"], "transport": "brainflow",
            "sample_rate_hz": self.rate, "channels": [{"name": n, "unit": "uV"} for n in names],
            "frontal_indices": [names.index("AF7"), names.index("AF8")],
            "original_channels": [{"name": n, "unit": "uV", "brainflow_row": i}
                                  for n, i in zip(names, self.channels)],
            "brainflow_board_id": board_id, "brainflow_version": shim.get_version(),
            "brainflow_preset": "DEFAULT_PRESET", "brainflow_descriptor": copy.deepcopy(descriptor),
            "timestamp_origin": "brainflow_timestamp_channel_unmodified",
            "device_identity": None, "hardware_verified": False,
        }
        params = params_type()
        params.timeout = 15
        stage = "connect"
        try:
            self.board = shim(board_id, params)
            if progress is not None:
                progress("Searching for Muse with BrainFlow…")
            self.board.prepare_session()
            stage = "start EEG"
            if progress is not None:
                progress("CONNECTED · Starting EEG…")
            self.board.start_stream()
            self.started = True
        except Exception as error:
            self.close()
            raise ValueError(f"BrainFlow could not {stage}. Close the test script and other Muse apps, then reconnect. ({error})") from error

    def pull(self):
        if self.closed:
            return [], []
        count = int(self.board.get_board_data_count())
        if not count:
            self.sleep(.02)
            return [], []
        if count > self.rate // 2:
            raise ValueError("EEG buffer fell behind. Reconnect your headset.")
        data = self.board.get_board_data(min(128, count))
        times = data[self.timestamp].tolist()
        if times and (not all(math.isfinite(t) for t in times)
                      or not -.5 <= self.wall_clock() - times[0] <= .5):
            raise ValueError("EEG samples are delayed or the source clock changed. Reconnect your headset.")
        return data[self.channels].T.tolist(), times

    def close(self):
        if self.closed:
            return
        try:
            if self.board is not None and self.board.is_prepared():
                try:
                    if self.started:
                        self.board.stop_stream()
                finally:
                    self.board.release_session()
        finally:
            self.closed = True


class LocalSourceProcess:
    """Own one child process and exchange bounded batches over private pipes."""

    def __init__(self, *, backend="brainflow", cancel=None, on_progress=None):
        if backend not in {"brainflow", "bleak"}:
            raise ValueError("Unsupported local headset backend.")
        self.backend, self.on_progress = backend, on_progress
        self.closed = False
        self.buffer = bytearray()
        # Inherit the launcher's process group so its shutdown also owns this child.
        self.process = subprocess.Popen(
            [sys.executable, "-u", "-m", "services.training.brainflow_source"]
            + ["--" + backend],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0,
        )
        try:
            self.description = self._receive(45, cancel=cancel, stage="connect")["description"]
        except BaseException:
            self.close()
            raise

    def _receive(self, timeout, *, cancel=None, stage="read EEG"):
        deadline = time.monotonic() + timeout
        while True:
            if cancel is not None and cancel.is_set():
                raise ValueError("Headset connection cancelled. Reconnect when ready.")
            if time.monotonic() >= deadline:
                raise ValueError(f"{self.backend} could not {stage} before the deadline. Power-cycle the Muse and reconnect.")
            if b"\n" in self.buffer:
                line, _, rest = self.buffer.partition(b"\n")
                self.buffer = bytearray(rest)
                message = json.loads(line)
                if "error" in message:
                    raise ValueError(message["error"])
                if "progress" in message:
                    if self.on_progress is not None:
                        self.on_progress(message["progress"])
                    continue
                return message
            if select.select([self.process.stdout], [], [], .05)[0]:
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise ValueError(f"{self.backend} stopped. Check the launcher terminal and reconnect.")
                self.buffer.extend(chunk)
                if len(self.buffer) > 65536:
                    raise ValueError("Invalid headset response size.")

    def pull(self):
        if self.closed:
            return [], []
        self.process.stdin.write(b"pull\n")
        result = self._receive(2)
        return result["rows"], result["times"]

    def close(self):
        if self.closed:
            return
        try:
            if self.process.poll() is None:
                try:
                    self.process.stdin.write(b"close\n")
                except (BrokenPipeError, OSError):
                    pass
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=1)
        finally:
            self.process.stdin.close()
            self.process.stdout.close()
            self.closed = True


class BrainFlowSource(LocalSourceProcess):
    """Muse 2 setup matching the user's successful standalone collection."""

    def __init__(self, *, cancel=None, on_progress=None):
        super().__init__(backend="brainflow", cancel=cancel, on_progress=on_progress)


class BleakSource(LocalSourceProcess):
    def __init__(self, *, cancel=None, on_progress=None):
        super().__init__(backend="bleak", cancel=cancel, on_progress=on_progress)


def main():
    source = None
    try:
        def progress(message):
            print(json.dumps({"progress": message}), flush=True)

        # No-argument helpers belong to older launchers whose IPC accepts only
        # descriptor/error frames. They still get BrainFlow, without progress.
        callback = progress if sys.argv[1:] else None
        if sys.argv[1:] in ([], ["--brainflow"]):
            source = BoardSource(progress=callback)
        elif sys.argv[1:] == ["--bleak"]:
            from modules.muse.acquisition.ble import BleMuseManager
            from services.training.preparation import BluetoothSource
            if callback is not None:
                callback("Searching for your Muse over Bluetooth (up to 15 seconds)…")
            source = BluetoothSource(lambda **callbacks: BleMuseManager(scan_timeout_s=15, **callbacks),
                                     progress=callback)
        else:
            raise ValueError("Unsupported headset helper arguments.")
        print(json.dumps({"description": source.description}), flush=True)
        for command in sys.stdin:
            if command.strip() != "pull":
                break
            rows, times = source.pull()
            print(json.dumps({"rows": rows, "times": times}, allow_nan=False), flush=True)
    except Exception as error:
        print(json.dumps({"error": str(error)}), flush=True)
    finally:
        if source is not None:
            source.close()


if __name__ == "__main__":
    main()
