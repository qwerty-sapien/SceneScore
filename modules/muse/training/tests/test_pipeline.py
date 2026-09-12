import json
import math

import pytest

from modules.muse.training.pipeline import (
    FEATURES,
    FinalTestLock,
    causal_features,
    choose_development,
    feature_vector,
    fit_anomaly,
    fit_logistic,
    fit_scaler,
    resolve_labels,
    save_deployment,
    score,
    self_train,
    validate_split,
)


def rows():
    return [
        {"role": "train", "label": i % 2, "features": {k: float(i % 2) * 4 + i / 100 for k in FEATURES}}
        for i in range(20)
    ]


def test_train_only_and_feature_whitelist():
    data = rows()
    model = fit_logistic(data)
    assert model == fit_logistic(data)
    assert score(model, data[1]["features"]) > score(model, data[0]["features"])
    assert model["calibration"] == "uncalibrated_score"
    assert not model["online_adaptation"]
    for role in ("development", "final_test"):
        with pytest.raises(ValueError, match="training_only"):
            fit_scaler([dict(data[0], role=role)])
    with pytest.raises(ValueError, match="whitelist"):
        feature_vector(dict(data[0]["features"], cue_time=1))
    anomaly = fit_anomaly(data)
    assert anomaly["semantics"] == "novelty_not_blink_intent"
    assert math.isfinite(score(anomaly, data[0]["features"]))


def test_causal_window_is_independent_of_future_and_rejects_invalid():
    past = [[0, 0], [1, 2], [4, 5], [1, 1]]
    before = causal_features(past, sample_rate_hz=256, noise_uv=1)
    full = past + [[1000, 1000]]
    assert before == causal_features(full[:4], sample_rate_hz=256, noise_uv=1)
    with pytest.raises(ValueError):
        causal_features(past, sample_rate_hz=256, noise_uv=float("nan"))
    with pytest.raises(ValueError):
        causal_features(past, sample_rate_hz=256, noise_uv=1, imu=[float("nan")])


def test_group_split_lock_and_label_resolution(tmp_path):
    sessions = [
        dict(session_id=str(i), participant_id="p", refit_id=str(i), role=role)
        for i, role in enumerate(("train", "development", "final_test"))
    ]
    assert validate_split(sessions)["generalization_scope"] == "within_person_only"
    sessions[1]["refit_id"] = "0"
    with pytest.raises(ValueError, match="leakage"):
        validate_split(sessions)
    lock = FinalTestLock("modelhash", "splithash", "matcherhash")
    lock.claim(tmp_path / "final.json")
    with pytest.raises(FileExistsError):
        lock.claim(tmp_path / "final.json")
    assert json.loads((tmp_path / "final.json").read_text())["model_hash"] == "modelhash"
    labels = [{"id": "a"}, {"id": "b", "supersedes": "a"}]
    assert resolve_labels(labels) == [labels[1]]
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_labels(labels + [{"id": "c", "supersedes": "a"}])


def test_real_deployment_and_pseudo_labels_are_gated(tmp_path):
    with pytest.raises(ValueError, match="calibration"):
        self_train(rows(), rows(), calibration_evidence={})
    with pytest.raises(ValueError, match="leakage"):
        self_train(
            rows(),
            [dict(rows()[0], role="final_test")],
            calibration_evidence={"partition": "development", "validated": True, "report_hash": "fixture"},
        )
    with pytest.raises(ValueError, match="real_data"):
        save_deployment(
            tmp_path / "model.json", fit_logistic(rows()), real_audit=[], selection={}, grammar={}, channel_contract={}
        )
    assert not (tmp_path / "model.json").exists()


def test_selection_is_constrained_and_never_uses_final_test():
    good = dict(
        partition="development",
        recall=0.98,
        latency_p95_s=0.5,
        availability=0.99,
        fp_per_armed_hour=0.2,
        model_id="baseline",
    )
    poor = dict(good, recall=0.5, fp_per_armed_hour=0, model_id="poor")
    assert choose_development([poor, good]) == good
    with pytest.raises(ValueError, match="forbidden"):
        choose_development([dict(good, partition="final_test")])
