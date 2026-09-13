"""Software fixtures only; no recording, human label or device claim."""
from copy import deepcopy
import math
import random

import pytest

from modules.muse.training.web_model import FEATURES, _features, predict_window, train_model


def example(index, kind="double", role="train", *, rate=128):
    rng = random.Random(913 + index)
    onset = 3 + index * 3
    times = [onset + i / rate for i in range(2 * rate + 1)]
    peaks = {"double": [.60, 1.10], "single": [.90], "triple": [.50, 1.0, 1.5]}.get(kind, [])
    samples = []
    for i, _ in enumerate(times):
        t = i / rate
        blink = sum((65 + index % 5) * math.exp(-((t - p - .006 * (index % 4)) / .065) ** 2) for p in peaks)
        a, b = rng.gauss(0, 1.0), rng.gauss(0, 1.0)
        if kind == "artifact":
            a += 25 * math.sin(2 * math.pi * 18 * t)
            b += 25 * math.cos(2 * math.pi * 15 * t)
        elif kind == "keypress_only":
            a += 9 * math.exp(-((t - .75) / .35) ** 2)
            b += 2 * math.exp(-((t - .90) / .40) ** 2)
        samples.append([a + blink, b + .95 * blink])
    return {"session_id": "fixture-train" if role == "train" else "fixture-development",
            "participant_id": "synthetic-fixture-person", "refit_id": "fit-a" if role == "train" else "fit-b",
            "role": role, "source_mode": "synthetic", "review_id": f"fixture-review-{index}",
            "certainty": "reviewed", "class_name": kind, "times_s": times, "samples": samples,
            "sample_rate_hz": rate, "start_s": onset + .35, "end_s": times[-1]}


def training():
    kinds = ["double"] * 4 + ["single", "natural", "artifact", "keypress_only", "triple"]
    return [example(i, kind) for i, kind in enumerate(kinds)]


def test_meaningful_double_and_negative_shape_fixtures():
    kinds = ("double", "double", "single", "natural", "artifact", "keypress_only", "triple")
    rows = training() + [example(i, kind, "development") for i, kind in enumerate(kinds, start=20)]
    result = train_model(rows)
    model, report = result["model"], result["report"]
    assert model["control_authority"] is False
    assert model["status"] == "PIPELINE_TESTED_ONLY" and model["source_mode"] == "synthetic"
    assert model["positive_examples"] == 4 and model["negative_examples"] == 5
    assert model["feature_names"] == list(FEATURES)
    assert report["held_out"]["windows"] == 7
    assert report["held_out"]["tp"] == 2 and report["held_out"]["tn"] == 5
    assert report["held_out"]["fp"] == 0 and report["held_out"]["fn"] == 0
    assert report["training_accuracy"] is None and report["event_accuracy"] is None
    assert model["config"]["steps"] == 200
    positive, negative = example(40), example(41, "single")
    assert predict_window(model, positive["times_s"], positive["samples"], 128) > .65
    assert predict_window(model, negative["times_s"], negative["samples"], 128) < .35


def test_deterministic_input_order_and_honest_missing_development():
    rows = training()
    a, b = train_model(rows), train_model(list(reversed(rows)))
    assert a == b
    assert len(a["model"]["training_data_sha256"]) == 64
    assert a["report"]["held_out"] is None
    assert a["report"]["held_out_unavailable_reason"] == "no_reviewed_whole_development_sessions"


def test_marker_and_review_start_metadata_never_predictive():
    original = train_model(training())["model"]
    changed = training()
    for row in changed:
        row.update(client_ms=900000, cue_s=1, key_code="B", marker_id="never-a-feature")
        row["start_s"] += .07
    altered = train_model(changed)["model"]
    for key in ("weights", "bias", "mean", "scale"):
        assert original[key] == altered[key]
    assert original["training_data_sha256"] != altered["training_data_sha256"]


def test_future_samples_do_not_enter_fixed_endpoint_features():
    original, changed = training(), training()
    for row in changed:
        row["times_s"] += [row["end_s"] + (i + 1) / 128 for i in range(128)]
        row["samples"] += [[1e8, -1e8] for _ in range(128)]
    a, b = train_model(original)["model"], train_model(changed)["model"]
    assert a["weights"] == b["weights"] and a["mean"] == b["mean"] and a["scale"] == b["scale"]
    before, _, _ = _features(original[0]["times_s"], original[0]["samples"], 128, end_s=original[0]["end_s"])
    after, _, _ = _features(changed[0]["times_s"], changed[0]["samples"], 128, end_s=original[0]["end_s"])
    assert before == after


def test_development_never_changes_scaler_or_fit():
    a = train_model(training())["model"]
    b = train_model(training() + [example(20, "artifact", "development")])["model"]
    for key in ("id", "weights", "bias", "mean", "scale", "training_data_sha256"):
        assert a[key] == b[key]
    assert b["held_out"]["windows"] == 1


def test_uncertain_exclusion_visible_and_final_test_never_read():
    uncertain = example(30)
    uncertain.update(certainty="uncertain", samples=[])
    result = train_model(training() + [uncertain])
    assert result["report"]["train_windows"] == 9
    assert result["report"]["excluded"][0]["reason"] == "uncertain_review_excluded"
    with pytest.raises(ValueError, match="final_test_consumption_forbidden"):
        train_model(training() + [{"role": "final_test", "samples": object()}])


@pytest.mark.parametrize("fault", ["source", "role", "refit", "person", "review", "duplicate_signal", "window_overlap", "sample_overlap"])
def test_identity_split_overlap_duplicate_gates(fault):
    rows = training()
    if fault == "source":
        rows[0]["source_mode"] = "real_device"
        match = "session_identity_or_role_leakage|mixed_source"
    elif fault == "role":
        rows[0]["role"] = "development"
        match = "session_identity_or_role_leakage|refit_role_leakage"
    elif fault == "refit":
        rows += [example(20, "single", "development")]
        rows[-1]["refit_id"] = "fit-a"
        match = "refit_role_leakage"
    elif fault == "person":
        rows += [example(20, "single", "development")]
        rows[-1]["participant_id"] = "other-person"
        match = "personal_model_requires_one_participant"
    elif fault == "review":
        rows[1]["review_id"] = rows[0]["review_id"]
        match = "duplicate_review_id"
    elif fault == "duplicate_signal":
        rows[1]["samples"] = deepcopy(rows[0]["samples"])
        rows[1]["session_id"] = "copied-recording"
        match = "duplicate_signal_window"
    elif fault == "window_overlap":
        rows[1]["times_s"] = [t - 2 for t in rows[1]["times_s"]]
        rows[1]["start_s"] -= 2
        rows[1]["end_s"] -= 2
        match = "overlapping_causal_training_windows"
    else:
        rows[1]["session_id"] = "copied-recording"
        rows[1]["samples"][20:60] = deepcopy(rows[0]["samples"][20:60])
        match = "overlapping_raw_samples_across_sessions"
    with pytest.raises(ValueError, match=match):
        train_model(rows)


@pytest.mark.parametrize("fault", ["short", "gap", "nan", "column", "duplicate_time", "wrong_rate", "flat", "backwards"])
def test_invalid_window_cannot_fit_or_predict(fault):
    model, row = train_model(training())["model"], example(60)
    if fault == "short":
        row["times_s"], row["samples"] = row["times_s"][100:], row["samples"][100:]
    elif fault == "gap":
        del row["times_s"][50:53]
        del row["samples"][50:53]
    elif fault == "nan":
        row["samples"][10][0] = float("nan")
    elif fault == "column":
        row["samples"][20].append(1)
    elif fault == "duplicate_time":
        row["times_s"][10] = row["times_s"][9]
    elif fault == "wrong_rate":
        row["sample_rate_hz"] = 256
    elif fault == "flat":
        row["samples"] = [[0, 0] for _ in row["samples"]]
    else:
        row["times_s"].reverse()
    with pytest.raises(ValueError):
        predict_window(model, row["times_s"], row["samples"], row["sample_rate_hz"])
    with pytest.raises(ValueError):
        train_model(training() + [row])


def test_minimum_class_counts_empty_data_and_coefficients_fail_closed():
    for rows in ([], [None], training()[:5], training()[4:]):
        with pytest.raises(ValueError):
            train_model(rows)
    model, row = train_model(training())["model"], example(60)
    model["weights"][0] = float("nan")
    with pytest.raises(ValueError, match="invalid_personal_window_coefficients"):
        predict_window(model, row["times_s"], row["samples"], 128)
