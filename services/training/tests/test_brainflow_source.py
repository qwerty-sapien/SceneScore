"""Explicit fixtures only: no Bluetooth discovery or headset connection."""

import json
import io
import subprocess
import sys
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from services.training import brainflow_source
from services.training.brainflow_source import BoardSource, BrainFlowSource, BleakSource
from services.training.preparation import Preparation


class FakeBoard:
    instance = None
    fail = None
    logger_enabled = False

    @classmethod
    def enable_dev_board_logger(cls):
        cls.logger_enabled = True

    @staticmethod
    def get_board_descr(board_id):
        assert board_id == 38
        return {"name": "Muse2", "eeg_names": "TP9,AF7,AF8,TP10", "eeg_channels": [1, 2, 3, 4],
                "timestamp_channel": 6, "sampling_rate": 256, "num_rows": 8}

    @staticmethod
    def get_version():
        return "fixture"

    def __init__(self, board_id, params):
        type(self).instance = self
        self.calls, self.prepared = [], False
        self.params, self.board_id = params, board_id
        self.data = np.arange(8 * 12, dtype=float).reshape(8, 12)
        self.data[6] = 100 + np.arange(12) / 256

    def prepare_session(self):
        self.calls.append("prepare")
        self.prepared = True
        if self.fail == "prepare":
            raise ValueError("fixture prepare error")

    def start_stream(self):
        self.calls.append("start")
        if self.fail == "start":
            raise ValueError("fixture start error")

    def get_board_data_count(self):
        return self.data.shape[1]

    def get_board_data(self, count):
        self.calls.append(("read", count))
        result, self.data = self.data[:, :count], self.data[:, count:]
        return result

    def is_prepared(self):
        return self.prepared

    def stop_stream(self):
        self.calls.append("stop")
        if self.fail == "stop":
            raise ValueError("fixture stop error")

    def release_session(self):
        self.calls.append("release")
        self.prepared = False


@pytest.fixture
def source():
    FakeBoard.fail = None
    value = BoardSource((FakeBoard, SimpleNamespace, 38), wall_clock=lambda: 100.1, sleep=lambda _: None)
    try:
        yield value
    finally:
        value.close()


def test_matches_user_board_setup_and_preserves_eeg_timestamp_provenance(source):
    board = FakeBoard.instance
    expected = board.data.copy()
    assert board.params.timeout == 15 and board.board_id == 38
    assert board.calls == ["prepare", "start"] and FakeBoard.logger_enabled
    rows, times = source.pull()
    assert rows == expected[[1, 2, 3, 4]].T.tolist()
    assert times == expected[6].tolist()
    assert source.pull() == ([], [])
    assert source.description["frontal_indices"] == [1, 2]
    assert source.description["brainflow_board_id"] == 38
    assert source.description["device_identity"] is None
    assert not source.description["hardware_verified"]
    source.close()
    source.close()
    assert board.calls[-2:] == ["stop", "release"] and board.calls.count("release") == 1


@pytest.mark.parametrize("fail", ["prepare", "start"])
def test_failed_open_releases_partial_session(fail):
    FakeBoard.fail = fail
    try:
        with pytest.raises(ValueError, match="BrainFlow could not"):
            BoardSource((FakeBoard, SimpleNamespace, 38))
        assert FakeBoard.instance.calls[-1] == "release"
        assert not FakeBoard.instance.prepared
    finally:
        FakeBoard.fail = None


def test_stop_failure_still_releases_board(source):
    FakeBoard.fail = "stop"
    try:
        with pytest.raises(ValueError, match="fixture stop error"):
            source.close()
        assert FakeBoard.instance.calls[-1] == "release"
    finally:
        FakeBoard.fail = None


@pytest.mark.parametrize("problem", ["backlog", "stale", "future", "nan"])
def test_buffer_and_timestamp_faults_are_not_fresh_eeg(source, problem):
    board = FakeBoard.instance
    if problem == "backlog":
        board.data = np.zeros((8, 129))
    else:
        board.data[6] = {"stale": 98, "future": 102, "nan": float("nan")}[problem]
    with pytest.raises(ValueError, match="EEG"):
        source.pull()


def test_real_preparation_uses_verified_brainflow_setup_and_existing_lsl_still_wins(monkeypatch):
    opened = []
    monkeypatch.setattr("services.training.preparation.BrainFlowSource", lambda **kw: opened.append(kw) or "brainflow")
    sources = SimpleNamespace(discover=lambda: {"sources": []}, open=lambda _: "lsl")
    prep = Preparation(sources)
    assert prep._open(False) == "brainflow" and opened == [{"cancel": prep.cancel, "on_progress": prep._progress}]
    opened[0]["on_progress"]("Muse found. Connecting…")
    assert prep.snapshot()["message"] == "Muse found. Connecting…"
    sources.discover = lambda: {"sources": [{"id": "fixture-lsl"}]}
    assert prep._open(False) == "lsl" and len(opened) == 1
    prep.close()


def fixture_helper(monkeypatch, program):
    real_popen = subprocess.Popen
    children = []
    def start(command, **kwargs):
        assert command[3] == "services.training.brainflow_source"
        child = real_popen([sys.executable, "-u", "-c", program], **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(brainflow_source.subprocess, "Popen", start)
    return children


def test_helper_protocol_and_exact_child_teardown(monkeypatch):
    program = '''import json, sys
print(json.dumps({"description": {"name": "explicit fixture"}}), flush=True)
for line in sys.stdin:
    if line.strip() == "close": break
    print(json.dumps({"rows": [[1, 2]], "times": [100.]}), flush=True)
'''
    children = fixture_helper(monkeypatch, program)
    source = BrainFlowSource()
    try:
        assert source.description["name"] == "explicit fixture"
        assert source.pull() == ([[1, 2]], [100.])
    finally:
        source.close()
    assert children[0].poll() == 0
    assert children[0].stdin.closed and children[0].stdout.closed


def test_native_setup_can_be_cancelled_and_child_is_reaped(monkeypatch):
    children = fixture_helper(monkeypatch, "import time; time.sleep(30)")
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(ValueError, match="cancelled"):
        BrainFlowSource(cancel=cancel)
    assert children[0].poll() is not None


def test_helper_error_is_visible_and_child_exits(monkeypatch):
    payload = json.dumps({"error": "fixture connection failed"})
    children = fixture_helper(monkeypatch, f"print({payload!r}, flush=True)")
    with pytest.raises(ValueError, match="fixture connection failed"):
        BrainFlowSource()
    assert children[0].poll() is not None


def test_bleak_progress_does_not_hide_ready_message_in_same_pipe_batch(monkeypatch):
    messages = [{"progress": "Searching…"}, {"progress": "Muse found. Connecting…"},
                {"description": {"name": "explicit fixture", "transport": "bleak"}}]
    payload = "\n".join(json.dumps(m) for m in messages)
    children = fixture_helper(monkeypatch, f"import sys; print({payload!r}, flush=True); sys.stdin.readline()")
    progress = []
    source = BleakSource(on_progress=progress.append)
    try:
        assert source.backend == "bleak"
        assert source.description["transport"] == "bleak"
        assert progress == ["Searching…", "Muse found. Connecting…"]
    finally:
        source.close()
    assert children[0].poll() == 0


def test_read_timeout_is_distinct_from_connection_timeout(monkeypatch):
    children = fixture_helper(monkeypatch, 'import sys; print(\'{"description": {}}\', flush=True); sys.stdin.readline()')
    source = BleakSource()
    try:
        with pytest.raises(ValueError, match="read EEG"):
            source._receive(0)
        with pytest.raises(ValueError, match="connect"):
            source._receive(0, stage="connect")
    finally:
        source.close()
    assert children[0].poll() == 0


@pytest.mark.parametrize("arguments", [[], ["--brainflow"]])
def test_existing_launcher_also_gets_brainflow_without_unknown_progress_frames(monkeypatch, capsys, arguments):
    closed = []
    def source(*, progress):
        if progress is not None:
            progress("Searching for Muse with BrainFlow…")
            progress("CONNECTED · Starting EEG…")
        return SimpleNamespace(description={"transport": "brainflow", "name": "explicit fixture"},
                               close=lambda: closed.append(True))
    monkeypatch.setattr(brainflow_source, "BoardSource", source)
    monkeypatch.setattr("services.training.preparation.BluetoothSource", lambda *a, **kw: pytest.fail("Default used Bleak"))
    monkeypatch.setattr(sys, "argv", ["headset-helper", *arguments])
    monkeypatch.setattr(sys, "stdin", io.StringIO("close\n"))
    brainflow_source.main()
    messages = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert messages[-1]["description"]["transport"] == "brainflow" and closed
    assert len(messages) == (3 if arguments else 1)
