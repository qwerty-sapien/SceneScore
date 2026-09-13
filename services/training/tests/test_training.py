"""Synthetic HTTP/source/storage fixtures; no participant or hardware evidence."""

from contextlib import contextmanager
import copy
import http.client
import json
import threading
import time
from types import SimpleNamespace

import pytest

from modules.muse.acquisition.tests.helpers import metadata
from modules.muse.acquisition.store import atomic, replay
from services.training.server import TrainingServer
from services.training.sources import SyntheticSource, descriptor, normalized_unit
from services.training.state import Workspace


def wait(predicate, timeout=3):
    end = time.monotonic() + timeout
    while not predicate() and time.monotonic() < end:
        time.sleep(0.01)
    assert predicate()


@contextmanager
def http_workspace(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<html>local training</html>")
    (web / ".env").write_text("private fixture")
    (web / "hidden-link").symlink_to(web / ".env")
    state = Workspace(tmp_path / "data")
    server = TrainingServer(("127.0.0.1", 0), state, "startup-test-token-0123456789", web, ["http://127.0.0.1:8767"])
    port = server.server_address[1]
    origin = f"http://127.0.0.1:{port}"
    server.origins = {origin}
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, name="training-http-fixture")
    thread.start()
    session = [None]

    def request(method, route, body=None, *, token=None, origin_value=origin, host=None):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        headers = {
            "Host": host or f"127.0.0.1:{port}",
            "Authorization": "Bearer " + (token or session[0] or server.token),
        }
        if origin_value is not None:
            headers["Origin"] = origin_value
        payload = None
        if body is not None:
            payload = json.dumps(body)
            headers["Content-Type"] = "application/json"
        connection.request(method, route, payload, headers)
        response = connection.getresponse()
        raw = response.read()
        status = response.status
        connection.close()
        return status, json.loads(raw) if raw.startswith(b"{") else raw

    try:
        status, value = request("POST", "/v1/session", {})
        assert status == 200
        session[0] = value["session"]
        yield state, server, request
    finally:
        state.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()
        assert state.worker is None


def manual(tmp_path, trainer=None, predictor=None):
    state = Workspace(tmp_path, trainer=trainer, predictor=predictor)
    state.metadata = metadata()
    state.mode, state.source = "synthetic", copy.deepcopy(SyntheticSource.description)
    state.connected = True
    state.consume([[0, 0]], [0.0], time.monotonic())
    return state


def record_body(**extra):
    return {
        "participant_id": "fixture-person",
        "refit_id": "fixture-refit",
        "role": "train",
        "consent": True,
        "consent_statement": "Synthetic fixture only, no person recorded",
        "seconds": 30,
        **extra,
    }


def feed(state, duration=20):
    start = state.last_device_s + 1 / 256
    for offset in range(0, int(duration * 256), 128):
        times = [start + (offset + i) / 256 for i in range(128)]
        state.consume([[float(i % 7), float(i % 5)] for i in range(128)], times, time.monotonic())


def test_http_real_lifecycle_is_explicit_local_and_bounded(tmp_path):
    with http_workspace(tmp_path) as (state, server, request):
        assert request("GET", "/v1/trace")[1]["samples"] == []
        assert (
            request("POST", "/v1/connect", {"source_id": "synthetic", "device_model": "fixture", "consent": False})[0]
            == 400
        )
        assert (
            request("POST", "/v1/connect", {"source_id": "synthetic", "device_model": "fixture", "consent": True})[0]
            == 200
        )
        wait(lambda: state.sample_count > 32)
        assert request("POST", "/v1/record/start", record_body(consent=False))[0] == 400
        assert request("POST", "/v1/record/start", record_body())[0] == 200
        wait(lambda: state.records[state.current_session_id]["samples"] > 64)
        marker = {"event": "down", "id": "fixture-key", "class_name": "double", "client_ms": 1234}
        assert request("POST", "/v1/marker", marker)[0] == 200
        request("POST", "/v1/marker", marker)
        assert len(state.markers(state.current_session_id)) == 1
        assert request("POST", "/v1/review", {"session_id": state.current_session_id})[0] == 400
        request("POST", "/v1/record/stop", {})
        sid = state.current_session_id
        status, raw = request("GET", "/v1/export?session_id=" + sid)
        assert status == 200
        assert raw["markers"][0]["end_s"] is not None
        assert raw["markers"][0]["browser_start_ms"] == 1234
        assert not raw["markers"][0]["is_ground_truth"]
        assert list(replay(state.root / sid)) == raw["chunks"]
        assert sum(len(c["samples"]) for c in raw["chunks"]) == state.records[sid]["samples"]
        assert request("POST", "/v1/disconnect", {})[1]["connected"] is False
        assert request("POST", "/v1/delete", {"session_id": sid, "confirmed_session_id": "wrong"})[0] == 400
        assert request("POST", "/v1/delete", {"session_id": sid, "confirmed_session_id": sid})[0] == 200
        assert not (state.root / sid).exists()


def test_http_auth_origin_host_expiry_and_static_confinement(tmp_path):
    with http_workspace(tmp_path) as (_, server, request):
        assert request("GET", "/v1/status", token="wrong")[0] == 403
        assert request("GET", "/v1/status", origin_value="https://untrusted.example")[0] == 403
        assert request("POST", "/v1/disconnect", {}, origin_value=None)[0] == 403
        assert request("GET", "/v1/status", host="evil.example")[0] == 403
        assert request("GET", "/v1/status", origin_value=None)[0] == 200
        old = server.session_expiry = time.monotonic() + 0.1
        assert request("GET", "/v1/status")[0] == 200
        assert server.session_expiry > old + 500
        server.session_expiry = 0
        assert request("GET", "/v1/status")[0] == 403
        assert request("GET", "/.env")[0] == 403
        assert request("GET", "/hidden-link")[0] == 403
        assert request("GET", "/%2e%2e/.env")[0] == 403
        assert request("GET", "/")[0] == 200


def test_split_review_training_prediction_and_invalidation(tmp_path):
    seen = []

    def trainer(examples):
        seen.extend(examples)
        return {
            "model": {
                "id": "synthetic-model",
                "status": "PIPELINE_TESTED_ONLY",
                "positive_examples": 3,
                "negative_examples": 3,
                "source_mode": "synthetic",
                "held_out": None,
                "model_kind": "test-stub",
                "control_authority": False,
            },
            "report": {},
        }

    state = manual(tmp_path, trainer, lambda *args: 0.7)
    try:
        state.record_start(record_body())
        feed(state)
        sid = state.current_session_id
        for i in range(7):
            state.marker(
                {"event": "cue", "id": f"m{i}", "class_name": "double" if i < 3 else "natural", "client_ms": i}
            )
        state.record_stop()
        assert all(m["end_s"] <= state.records[sid]["end_s"] for m in state.markers(sid))
        for i in range(7):
            state.review(
                {
                    "session_id": sid,
                    "marker_id": f"m{i}",
                    "start_s": i * 2.5 + 0.2,
                    "end_s": i * 2.5 + 2.3,
                    "class_name": "double" if i < 3 else "natural",
                    "certainty": "uncertain" if i == 6 else "reviewed",
                    "reviewer": "fixture-reviewer",
                    "notes": "Synthetic fixture human-review route",
                }
            )
        result = state.train()
        assert len(seen) == 6
        assert len(result["report"]["backend_excluded_uncertain_review_ids"]) == 1
        assert all(e["role"] == "train" and len(e["samples"]) >= 512 for e in seen)
        assert state.trace()["prediction"]["score"] == 0.7
        state.review(
            {
                "session_id": sid,
                "marker_id": "m0",
                "start_s": 0.2,
                "end_s": 2.3,
                "class_name": "artifact",
                "certainty": "reviewed",
                "reviewer": "fixture-reviewer",
                "notes": "Correction",
            }
        )
        assert state.model is None and not (state.root / "model.json").exists()
        with pytest.raises(ValueError, match="refit_split"):
            state.record_start(record_body(role="development"))
    finally:
        state.close()


def test_raw_gap_roundtrip_and_corruption_invalidates_exact_byte_cache(tmp_path):
    state = manual(tmp_path)
    try:
        state.record_start(record_body())
        state.consume([[1, 2], [3, 4], [5, 6]], [0.1, 0.1 + 1 / 256, 0.2], time.monotonic())
        state.record_stop()
        sid = state.current_session_id
        raw = state.raw(sid)
        assert len(raw["chunks"]) == 2 and raw["chunks"][1]["dropped_samples_before"] > 0
        assert state.raw(sid)["chunks"] == raw["chunks"]
        path = state.root / sid / "chunks" / "000000001.json"
        bad = json.loads(path.read_text())
        bad["samples"][0] = [9]
        path.write_text(json.dumps(bad))
        with pytest.raises(Exception):
            state.raw(sid)
    finally:
        state.close()


def test_missing_attestation_and_clock_reset_fail_closed(tmp_path):
    state = manual(tmp_path)
    try:
        state.mode = "real_device"
        with pytest.raises(ValueError, match="attestation"):
            state.record_start(record_body())
        with pytest.raises(ValueError, match="timestamp_reset"):
            state.consume([[0, 0]], [0.0], time.monotonic())
    finally:
        state.close()


def test_source_fault_subscriber_timeout_and_shutdown(tmp_path):
    class Bad:
        description = SyntheticSource.description
        closed = False

        def pull(self):
            raise RuntimeError("synthetic_source_fault")

        def close(self):
            self.closed = True

    source = Bad()
    state = Workspace(tmp_path / "fault", sources=SimpleNamespace(open=lambda _: source))
    state.connect({"source_id": "synthetic", "device_model": "fixture", "consent": True})
    wait(lambda: state.worker is None)
    assert source.closed and not state.connected and "source_fault" in state.reason
    state.close()
    state = Workspace(tmp_path / "timeout", subscriber_timeout=0.08)
    state.connect({"source_id": "synthetic", "device_model": "fixture", "consent": True})
    wait(lambda: state.worker is None)
    assert not state.connected and state.reason == "browser_subscriber_timeout"
    state.close()


def test_source_descriptor_exact_pair_units_and_synthetic_close():
    class Channel:
        def __init__(self, labels, i=0):
            self.labels, self.i = labels, i

        def child_value(self, name):
            return self.labels[self.i] if name == "label" else "microvolts"

        def next_sibling(self):
            return Channel(self.labels, self.i + 1)

    class Desc:
        def __init__(self, labels):
            self.labels = labels

        def child(self, name):
            return Channel(self.labels) if name == "channel" else self

    def info(labels):
        return SimpleNamespace(
            channel_count=lambda: 2,
            nominal_srate=lambda: 256,
            desc=lambda: Desc(labels),
            source_id=lambda: "fixture",
            name=lambda: "fixture",
        )

    assert descriptor(info(["AF8", "AF7"]))["frontal_indices"] == [1, 0]
    with pytest.raises(ValueError, match="frontal"):
        descriptor(info(["AF7", "FP1"]))
    assert normalized_unit("µV") == "uV"
    with pytest.raises(ValueError, match="unit"):
        normalized_unit("mV")
    source = SyntheticSource()
    source.close()
    assert source.pull() == ([], [])


def test_interrupted_recording_recovers_counts_from_persisted_raw(tmp_path):
    state = manual(tmp_path)
    state.record_start(record_body())
    feed(state, 1)
    sid = state.current_session_id
    state.record_stop()
    value = copy.deepcopy(state.records[sid])
    value.update(status="recording", samples=0, start_s=None, end_s=None)
    atomic(state.root / sid / "session.json", value)
    state.close()
    recovered = Workspace(tmp_path)
    try:
        assert recovered.records[sid]["samples"] == 256
        assert recovered.records[sid]["status"] == "closed"
        assert recovered.records[sid]["stop_reason"] == "recovered_interrupted_recording"
    finally:
        recovered.close()


def test_connect_disconnect_transaction_cancels_uncommitted_source(tmp_path):
    entered, release = threading.Event(), threading.Event()
    source = SyntheticSource()

    def opening(_):
        entered.set()
        assert release.wait(2)
        return source

    state = Workspace(tmp_path, sources=SimpleNamespace(open=opening))
    errors = []

    def connect():
        try:
            state.connect({"source_id": "synthetic", "device_model": "fixture", "consent": True})
        except ValueError as exc:
            errors.append(str(exc))

    thread = threading.Thread(target=connect, name="training-connect-race-fixture")
    thread.start()
    assert entered.wait(2)
    state.disconnect()
    release.set()
    thread.join(2)
    assert not thread.is_alive() and source.closed and state.worker is None
    assert errors == ["connect_cancelled"]
    state.close()


def test_persistence_error_still_closes_and_joins_source(tmp_path, monkeypatch):
    state = Workspace(tmp_path)
    state.connect({"source_id": "synthetic", "device_model": "fixture", "consent": True})
    wait(lambda: state.sample_count > 32)
    state.record_start(record_body())
    wait(lambda: state.records[state.current_session_id]["samples"] > 32)

    def fail(_):
        raise OSError("fixture_disk_failure")

    monkeypatch.setattr(state.recorder, "close", fail)
    with pytest.raises(RuntimeError, match="persistence_fault"):
        state.disconnect()
    assert state.worker is None and not state.connected and state.recorder is None
    state.close()


def test_same_discovery_duplicate_source_ids_are_unselectable(monkeypatch):
    import sys
    from services.training.sources import Sources

    closed = []

    class Channel:
        def __init__(self, i=0):
            self.i = i

        def child_value(self, key):
            return ["AF7", "AF8"][self.i] if key == "label" else "µV"

        def next_sibling(self):
            return Channel(self.i + 1)

    class Desc:
        def child(self, key):
            return Channel() if key == "channel" else self

    info = SimpleNamespace(
        channel_count=lambda: 2,
        nominal_srate=lambda: 256,
        desc=Desc,
        source_id=lambda: "duplicate",
        name=lambda: "fixture",
    )

    class Inlet:
        def __init__(self, *args, **kwargs):
            pass

        def info(self, **kwargs):
            return info

        def close_stream(self):
            closed.append(True)

    monkeypatch.setitem(
        sys.modules, "pylsl", SimpleNamespace(resolve_streams=lambda **kwargs: [info, info], StreamInlet=Inlet)
    )
    sources = Sources()
    result = sources.discover()
    assert result["sources"] == [] and sources.known == {}
    assert "duplicate_source_id" in result["blockers"] and len(closed) == 2
