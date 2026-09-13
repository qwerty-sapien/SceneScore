"""Synthetic feature fixtures verify persistence, not real EEG accuracy."""
import copy
import math

import pytest

from modules.muse.training.checkpoints import (
    CheckpointStore, fit_checkpoint, training_batch, validate_checkpoint, _digest,
)


def contract(rate=64, mode="synthetic"):
    return {"source_mode": mode, "sample_rate_hz": rate, "channels": [["AF7", "uV"], ["AF8", "uV"]]}


def examples(offset=0, count=24, *, rate=64, mode="synthetic"):
    return [{"id": f"synthetic-example-{offset}-{label}-{i}", "partition": "learning", "label": label,
             "contract": contract(rate, mode), "created_ns": offset + i,
             "features": [label * (j + 1) + math.sin(i + j + offset) * .2 for j in range(14)]}
            for label in (0, 1) for i in range(count)]


def checkpoint(rate=64, mode="synthetic"):
    return fit_checkpoint(examples(rate=rate, mode=mode), contract(rate, mode))


def test_warm_start_keeps_scaler_and_weights_and_records_parent():
    first = checkpoint()
    more = examples(100)
    resumed = fit_checkpoint(more, contract(), first)
    reset = fit_checkpoint(more, contract())
    assert resumed["model"]["mean"] == first["model"]["mean"]
    assert resumed["model"]["scale"] == first["model"]["scale"]
    assert resumed["model"]["weights"] != reset["model"]["weights"]
    assert resumed["training_steps"] == 400 and resumed["parent_id"] == first["id"]
    assert first["training_steps"] == 200
    with pytest.raises(ValueError, match="parent"):
        fit_checkpoint(examples(mode="real_device"), contract(mode="real_device"), first)


def test_checkpoint_saved_before_check_survives_failure_and_restart(tmp_path):
    store = CheckpointStore(tmp_path)
    first = store.save(checkpoint())
    original = (tmp_path / "checkpoints" / (first["id"] + ".json")).read_bytes()
    store.save_evaluation(first["id"], {"precision": .4, "recall": .5, "target_reached": False, "complete": True})
    restarted = CheckpointStore(tmp_path)
    assert restarted.latest(contract()) == first
    assert (tmp_path / "checkpoints" / (first["id"] + ".json")).read_bytes() == original
    second = store.save(fit_checkpoint(examples(100), contract(), first))
    assert store.latest(contract())["id"] == second["id"]
    assert store.load(first["id"])["model"]["weights"] == first["model"]["weights"]
    assert store.evaluation(second["id"]) is None
    assert store.latest(contract(mode="real_device")) is None


def test_interrupted_write_corruption_and_unsafe_coefficients_never_load(tmp_path, monkeypatch):
    import modules.muse.training.checkpoints as module
    store = CheckpointStore(tmp_path)
    first = store.save(checkpoint())
    second = fit_checkpoint(examples(100), contract(), first)
    with monkeypatch.context() as m:
        m.setattr(module.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("interrupted fixture write")))
        with pytest.raises(OSError):
            store.save(second)
    assert store.latest(contract())["id"] == first["id"]
    assert not list((tmp_path / "checkpoints").glob(".pending-*"))
    tampered = copy.deepcopy(first)
    tampered["model"]["weights"][0] += 1
    with pytest.raises(ValueError, match="integrity"):
        validate_checkpoint(tampered)
    tampered["model"]["scale"][0] = 0
    tampered["id"] = "checkpoint-" + _digest({k: v for k, v in tampered.items() if k != "id"})
    with pytest.raises(ValueError, match="coefficients"):
        store.save(tampered)
    (tmp_path / "checkpoints" / (first["id"] + ".json")).write_text("{}")
    assert store.latest(contract()) is None
    assert store.summaries()["invalid_checkpoint_ids"] == [first["id"]]
    with pytest.raises(ValueError):
        store.load("../../model")


def test_bounded_replay_and_check_data_rejection():
    old = checkpoint()
    pool = examples(count=200) + examples(1000, count=200)
    batch = training_batch(pool, old)
    assert len(batch) == 128
    assert training_batch(list(reversed(pool)), old) == batch
    assert any(e["created_ns"] > 1000 for e in batch)
    bad = examples()
    bad[0]["partition"] = "checking"
    with pytest.raises(ValueError, match="learning_only"):
        fit_checkpoint(bad, contract())
    bad = examples(count=19)
    with pytest.raises(ValueError, match="twenty"):
        fit_checkpoint(bad, contract())
