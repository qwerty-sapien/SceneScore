import copy
import json
import math
from types import SimpleNamespace

import pytest

from services.training.automatic import AutomaticTrainer, FORMAT, check_metrics
from services.training.sources import SyntheticSource
from modules.muse.training.checkpoints import atomic_json, _digest
from modules.muse.training.tests.test_checkpoints import checkpoint, contract


def labels(n=100):
    return [{"id": f"b{i}", "epoch": "one", "source_s": i * 3 + 2} for i in range(n)]


def decisions(n=100):
    return [{"id": f"d{i}", "epoch": "one", "final_blink_s": i * 3 + 1.8, "decision_s": i * 3 + 2.3}
            for i in range(n)]


def metrics(b, d, **extra):
    return check_metrics(b, d, elapsed_s=400, usable_s=399, background_s=80, complete=True, **extra)


def test_advisory_target_strict_boundary_duplicates_misses_and_zero_denominators():
    assert not metrics(labels(), decisions(93))["target_reached"]
    assert metrics(labels(), decisions(94))["target_reached"]
    duplicated = decisions() + [{**decisions()[0], "id": "duplicate"}]
    result = metrics(labels(), duplicated)
    assert (result["tp"], result["fp"], result["fn"]) == (100, 1, 0)
    assert metrics(labels(), [])["recall"] == 0
    assert metrics([], [])["precision"] is None
    assert metrics([], [])["recall"] is None
    assert not metrics(labels(29), decisions(29))["complete"]
    assert metrics(labels(), decisions())["production_accuracy_gate"] is False


def test_timing_boundaries_epochs_quality_and_background_are_not_hidden():
    b = labels(30)
    d = decisions(30)
    d[0]["epoch"] = "different"
    d[1]["final_blink_s"] = b[1]["source_s"] - 1.0001
    d[2]["final_blink_s"] = b[2]["source_s"] + .2501
    result = metrics(b, d)
    assert result["fn"] == 3 and result["fp"] == 3
    report = check_metrics(b, decisions(30), elapsed_s=150, usable_s=100, background_s=70, complete=True)
    assert report["recall"] == 1 and not report["target_reached"]
    assert not check_metrics(b, decisions(30), elapsed_s=150, usable_s=150, background_s=59, complete=True)["complete"]


def manual(tmp_path, mode="synthetic"):
    clock = [0.0]
    description = copy.deepcopy(SyntheticSource.description)
    description["sample_rate_hz"] = 64
    source = SimpleNamespace(description=description, close=lambda: None)
    sources = SimpleNamespace(open=lambda _: source, discover=lambda: {"sources": [{"id": "fixture-real-descriptor"}]})
    trainer = AutomaticTrainer(tmp_path, sources, synthetic=mode == "synthetic", clock=lambda: clock[0])
    trainer.run = {"id": "run-fixture", "format": FORMAT, "source_mode": mode, "hardware_verified": False}
    trainer.path = tmp_path / "runs" / "run-fixture"
    atomic_json(trainer.path / "run.json", trainer.run)
    trainer._open()
    return trainer, clock


def feed(trainer, clock, seconds):
    start = trainer.last_source_s + 1 / 64 if trainer.last_source_s is not None else 0
    for index in range(int(seconds * 64) // 32):
        times = [start + (index * 32 + i) / 64 for i in range(32)]
        rows = [[2 * math.sin(t * 13) + .02*t, 2 * math.cos(t * 17) + .03*t] for t in times]
        clock[0] = times[-1]
        trainer.consume(rows, times, clock[0])
        trainer._accept_fit()


def test_real_descriptor_is_not_attested_by_auto_training_and_B_is_idempotent(tmp_path):
    trainer, clock = manual(tmp_path, mode="real_device")
    try:
        feed(trainer, clock, 4)
        body = {"id": "one", "run_id": trainer.run["id"], "client_ms": 25}
        assert trainer.label(body)["saved"]
        assert trainer.label(body)["saved"] and len(trainer.labels) == 1
        assert trainer.run["hardware_verified"] is False
        assert trainer.metadata["provenance"]["source_mode"] == "real_device"
        assert trainer.learning[-1]["label"] == 1
        assert "client_ms" not in trainer.learning[-1]["features"]
        with pytest.raises(ValueError, match="stale"):
            trainer.label({**body, "run_id": "older-run"})
        stored = json.loads((trainer.path / "labels.jsonl").read_text())
        assert stored["semantics"].startswith("reported_double")
    finally:
        trainer.close()


def test_background_delay_and_check_partition_never_enter_learning(tmp_path):
    trainer, clock = manual(tmp_path)
    try:
        feed(trainer, clock, 12)
        for e in trainer.learning:
            assert e["label"] == 0
            assert e["end_s"] <= trainer.last_source_s - 2.25
        before = copy.deepcopy(trainer.learning)
        trainer.checkpoint = trainer.store.save(checkpoint())
        trainer.fit_result = trainer.checkpoint
        trainer._accept_fit()
        feed(trainer, clock, 4)
        trainer.label({"id": "checking-key", "run_id": trainer.run["id"], "client_ms": 1})
        feed(trainer, clock, 5)
        assert trainer.learning == before
        report = trainer._save_check(complete=False)
        assert report["labels"] == 1 and report["fn"] == 1
        assert not report["complete"]
        assert trainer.store.latest(contract()) is not None
        trainer.stop()
        assert trainer.phase == "checking"  # Stop preserves the partition until finalization.
    finally:
        trainer.close()


def test_history_reload_checks_digest_and_excludes_check_data(tmp_path):
    trainer, clock = manual(tmp_path)
    try:
        feed(trainer, clock, 12)
        assert trainer._load_learning() == trainer.learning
        path = trainer.path / "examples.jsonl"
        example = trainer.learning[0]
        bad = {**example, "partition": "checking"}
        bad["id"] = "example-" + _digest({k: v for k, v in bad.items() if k != "id"})
        path.write_text(json.dumps(bad) + "\n")
        with pytest.raises(ValueError, match="check_data"):
            trainer._load_learning()
    finally:
        trainer.close()


def test_false_detections_do_not_postpone_a_failed_check_or_delete_its_checkpoint(tmp_path):
    trainer, clock = manual(tmp_path)
    try:
        trainer.checkpoint = trainer.store.save(checkpoint())
        trainer.fit_result = trainer.checkpoint
        trainer.last_source_s = 0
        trainer._accept_fit()
        clock[0], trainer.last_source_s = 300., 300.
        trainer.labels = labels(30)
        trainer.check_decisions = decisions(30) + [
            {"id": f"extra-{i}", "epoch": "one", "final_blink_s": 291 + i, "decision_s": 291.5 + i}
            for i in range(10)]
        trainer.usable_intervals = [[0., 300.]]
        trainer._maybe_check()
        assert trainer.phase == "learning" and trainer.stage_new == [0, 0]
        assert trainer.evaluation["complete"] and trainer.evaluation["fp"] == 10
        assert not trainer.evaluation["target_reached"]
        assert trainer.store.load(trainer.checkpoint["id"]) == trainer.checkpoint
    finally:
        trainer.close()


def test_full_learning_saves_checkpoint_before_check_and_partial_check_keeps_it(tmp_path):
    trainer, clock = manual(tmp_path)
    try:
        feed(trainer, clock, 100)
        for i in range(20):
            feed(trainer, clock, 3)
            trainer.label({"id": f"learning-{i}", "client_ms": i, "run_id": trainer.run["id"]})
        feed(trainer, clock, .5)
        assert trainer.fit_thread is not None
        trainer.fit_thread.join(5)
        assert not trainer.fit_thread.is_alive()
        assert trainer.store.latest(contract()) is not None
        trainer._accept_fit()
        assert trainer.phase == "checking" and trainer.evaluation is None
        saved = trainer.checkpoint
        feed(trainer, clock, 4)
        trainer.label({"id": "check-only", "client_ms": 100, "run_id": trainer.run["id"]})
        assert trainer.detector.armed and trainer.detector.count >= trainer.rate
        trainer._save_check(complete=False)
        assert trainer.store.latest(contract()) == saved
        assert "check-only" not in str(saved["examples"])
        assert trainer._load_learning() == trainer.learning
    finally:
        trainer.close()


def test_http_automatic_flow_requires_explicit_train_and_cleans_up(tmp_path):
    from services.training.tests.test_training import http_workspace, wait
    with http_workspace(tmp_path) as (state, server, request):
        state.automatic.synthetic = True
        assert request("GET", "/v1/automatic/status")[1]["phase"] == "idle"
        assert request("POST", "/v1/automatic/start", {"consent": False})[0] == 400
        assert request("POST", "/v1/automatic/start", {"consent": True})[0] == 400
        assert request("POST", "/v1/automatic/connect", {"consent": True})[0] == 200
        wait(lambda: state.preparation.snapshot()["ready"], timeout=6)
        assert state.automatic.run is None
        assert not (tmp_path / "automatic" / "runs").exists()
        assert request("POST", "/v1/automatic/start", {"consent": True})[0] == 200
        wait(lambda: state.automatic.last_source_s is not None)
        status = request("GET", "/v1/automatic/status")[1]
        label = {"id": "http-label", "client_ms": 4, "run_id": status["run_id"]}
        assert request("POST", "/v1/automatic/label", label)[1]["saved"]
        assert request("POST", "/v1/automatic/label", label)[1]["saved"]
        assert request("GET", "/v1/automatic/status")[1]["labels"] == 1
        assert request("POST", "/v1/automatic/stop", {})[0] == 200
        wait(lambda: not state.automatic.status()["active"])
        assert state.automatic.source is None
        assert not state.automatic.thread.is_alive()


def test_ten_minute_cap_and_source_error_preserve_prior_checkpoint(tmp_path):
    import time
    clock = [0.0]
    description = copy.deepcopy(SyntheticSource.description)
    description["sample_rate_hz"] = 64
    closed = []
    def pull():
        clock[0] = 600.1
        return [], []
    source = SimpleNamespace(description=description, pull=pull, close=lambda: closed.append(True))
    trainer = AutomaticTrainer(tmp_path, SimpleNamespace(open=lambda _: source), synthetic=True, clock=lambda: clock[0])
    saved = trainer.store.save(checkpoint())
    trainer.start({"consent": True})
    trainer.thread.join(5)
    assert not trainer.thread.is_alive() and closed
    assert trainer.store.latest(contract()) == saved
    assert trainer.status()["elapsed_s"] >= 600
    assert not trainer.status()["active"]
    trainer.close()
    # No waiting or data collection occurs after a known source fault.
    clock[0] = time.monotonic()
    source.pull = lambda: (_ for _ in ()).throw(OSError("fixture source fault"))
    recovered = AutomaticTrainer(tmp_path, SimpleNamespace(open=lambda _: source), synthetic=True, clock=lambda: clock[0])
    recovered.start({"consent": True})
    recovered.thread.join(5)
    assert recovered.phase == "error"
    assert recovered.store.latest(contract()) == saved
    recovered.close()
