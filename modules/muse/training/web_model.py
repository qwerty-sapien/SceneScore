"""Personal reviewed-window research model. No control or automatic labels.

Only two seconds of EEG at/before the requested endpoint enter the features.
Cue, keyboard, reviewer, session and label fields never enter a feature vector.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics


FORMAT = "scenescore.personal-blink-window/1"
FEATURES = ("peak_count", "two_peak_structure", "third_peak_present", "peak_gap_s",
            "second_peak_ratio", "mean_peak_width_s", "active_fraction",
            "bilateral_correlation", "bilateral_peak_ratio", "difference_rms_ratio",
            "roughness_ratio", "slow_drift_ratio", "log_signal_rms", "noise_floor_ratio")
CLASSES = {"double", "single", "triple", "natural", "artifact", "keypress_only"}
CONFIG = {"window_s": 2.0, "steps": 200, "learning_rate": .08, "l2": .05,
          "threshold": .5, "smooth_s": .035, "peak_threshold_fraction": .32,
          "minimum_peak_width_s": .035, "minimum_peak_gap_s": .10,
          "max_examples": 256, "max_total_samples": 1_000_000,
          "sample_rate_min_hz": 32, "sample_rate_max_hz": 2048,
          "maximum_gap_periods": 1.5, "feature_version": "past-eeg-shape-1"}


def _digest(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False) + "\n").encode()).hexdigest()


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _window(times_s, samples, rate, *, end_s=None):
    if (not _number(rate) or not CONFIG["sample_rate_min_hz"] <= rate <= CONFIG["sample_rate_max_hz"]
            or not isinstance(times_s, (list, tuple)) or not isinstance(samples, (list, tuple))
            or not 2 <= len(times_s) == len(samples) <= 16384):
        raise ValueError("bounded_two_column_window_required")
    if any(not _number(t) or t < 0 for t in times_s):
        raise ValueError("finite_nonnegative_device_times_required")
    if any(b <= a for a, b in zip(times_s, times_s[1:])):
        raise ValueError("nonmonotonic_window_times")
    end = times_s[-1] if end_s is None else end_s
    if not _number(end) or end < 0:
        raise ValueError("invalid_window_endpoint")
    start = end - CONFIG["window_s"]
    indices = [i for i, t in enumerate(times_s) if start - 1e-9 <= t <= end + 1e-9]
    if (len(indices) < math.floor(CONFIG["window_s"] * rate) - 1
            or len(indices) > math.ceil(CONFIG["window_s"] * rate) + 2):
        raise ValueError("two_seconds_of_preceding_coverage_required")
    times, rows = [times_s[i] for i in indices], [samples[i] for i in indices]
    if times[0] > start + 1.1 / rate or end - times[-1] > 1.1 / rate:
        raise ValueError("two_seconds_of_preceding_coverage_required")
    if any(not .5 / rate <= b - a <= CONFIG["maximum_gap_periods"] / rate for a, b in zip(times, times[1:])):
        raise ValueError("gapped_or_rate_inconsistent_window")
    if any(not isinstance(row, (list, tuple)) or len(row) != 2
           or any(not _number(v) or abs(v) > 1e9 for v in row) for row in rows):
        raise ValueError("finite_two_frontal_columns_required")
    # Samples outside the past window are never read or used for normalization.
    return times, rows


def _features(times_s, samples, rate, *, end_s=None):
    times, rows = _window(times_s, samples, rate, end_s=end_s)
    columns = [[row[i] for row in rows] for i in range(2)]
    centers = [statistics.median(column) for column in columns]
    centered = [[v - center for v in column] for column, center in zip(columns, centers)]
    rms = [math.sqrt(statistics.fmean(v * v for v in column)) for column in centered]
    if min(rms) < 1e-9:
        raise ValueError("flat_frontal_window")
    common = [(abs(a) + abs(b)) / 2 for a, b in zip(*centered)]
    alpha = 1 - math.exp(-1 / (rate * CONFIG["smooth_s"]))
    smoothed = [common[0]]
    for value in common[1:]:
        smoothed.append(smoothed[-1] + alpha * (value - smoothed[-1]))
    floor = statistics.median(smoothed)
    mad = statistics.median(abs(v - floor) for v in smoothed)
    peak = max(smoothed)
    threshold = max(peak * CONFIG["peak_threshold_fraction"], floor + 2 * mad)
    spans, opened = [], None
    for i, value in enumerate(smoothed + [-1]):
        if value > threshold and opened is None:
            opened = i
        elif value <= threshold and opened is not None:
            if (i - opened) / rate >= CONFIG["minimum_peak_width_s"]:
                at = max(range(opened, i), key=smoothed.__getitem__)
                span = (at, smoothed[at], (i - opened) / rate)
                if spans and (at - spans[-1][0]) / rate < CONFIG["minimum_peak_gap_s"]:
                    if span[1] > spans[-1][1]:
                        spans[-1] = span
                else:
                    spans.append(span)
            opened = None
    strongest = sorted(spans, key=lambda s: (-s[1], s[0]))[:2]
    gap = abs(strongest[0][0] - strongest[1][0]) / rate if len(strongest) == 2 else 0.0
    ratio = strongest[1][1] / strongest[0][1] if len(strongest) == 2 else 0.0
    correlation = statistics.fmean(a * b for a, b in zip(*centered)) / (rms[0] * rms[1])
    difference = math.sqrt(statistics.fmean((a - b) ** 2 for a, b in zip(*centered))) / sum(rms)
    roughness = statistics.fmean(math.sqrt(statistics.fmean((b - a) ** 2 for a, b in zip(c, c[1:]))) / r
                                for c, r in zip(centered, rms))
    means = [statistics.fmean(common[i * len(common) // 4:(i + 1) * len(common) // 4]) for i in range(4)]
    result = [min(len(spans), 4), int(len(spans) == 2), int(len(spans) >= 3), gap, ratio,
              statistics.fmean(s[2] for s in spans) if spans else 0.0,
              sum(v > threshold for v in smoothed) / len(smoothed), max(-1, min(1, correlation)),
              min(max(abs(v) for v in c) for c in centered) / max(max(abs(v) for v in c) for c in centered),
              difference, roughness, (max(means) - min(means)) / statistics.fmean(rms),
              math.log1p(statistics.fmean(rms)), floor / peak]
    if not all(math.isfinite(v) for v in result):
        raise ValueError("nonfinite_window_features")
    return result, times, rows


def _sigmoid(value):
    return 1 / (1 + math.exp(-max(-40, min(40, value))))


def _normalized(vector, mean, scale):
    return [max(-12, min(12, (v - m) / s)) for v, m, s in zip(vector, mean, scale)]


def _window_metrics(rows, scores):
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    for row, score in zip(rows, scores):
        positive, predicted = row["label"] == 1, score >= CONFIG["threshold"]
        counts["tp" if positive and predicted else "fn" if positive else "fp" if predicted else "tn"] += 1
    tp, tn, fp, fn = (counts[k] for k in ("tp", "tn", "fp", "fn"))
    return {"semantics": "whole_development_session_window_metrics_not_event_accuracy",
            "windows": len(rows), "positive_windows": tp + fn, "negative_windows": tn + fp,
            **counts, "window_recall": tp / (tp + fn) if tp + fn else None,
            "window_precision": tp / (tp + fp) if tp + fp else None,
            "window_specificity": tn / (tn + fp) if tn + fp else None,
            "threshold": CONFIG["threshold"], "calibration": "uncalibrated_score"}


def train_model(examples):
    """Fit a bounded personal model from reviewed, nonoverlapping TRAIN windows.

    Backend supplies verified channel order/units and epoch continuity. It must
    not assemble final-test data for this endpoint; any final_test entry fails
    immediately, before waveform validation/feature extraction.
    """
    if (not isinstance(examples, list) or not 1 <= len(examples) <= CONFIG["max_examples"]
            or any(not isinstance(example, dict) for example in examples)):
        raise ValueError("reviewed_training_examples_required")
    if any(example.get("role") == "final_test" for example in examples):
        raise ValueError("final_test_consumption_forbidden")
    sessions, refits, identifiers, modes, participants = {}, {}, set(), set(), set()
    excluded, prepared, total_samples = [], [], 0
    for example in examples:
        for key in ("session_id", "participant_id", "refit_id", "review_id"):
            if not isinstance(example.get(key), str) or not 1 <= len(example[key]) <= 160:
                raise ValueError("bounded_example_identity_required")
        if example.get("role") not in {"train", "development"}:
            raise ValueError("whole_train_or_development_session_required")
        if example.get("source_mode") not in {"synthetic", "real_device"}:
            raise ValueError("explicit_real_or_synthetic_source_required")
        if example.get("class_name") not in CLASSES or example.get("certainty") not in {"reviewed", "uncertain"}:
            raise ValueError("reviewed_class_or_uncertain_required")
        total_samples += len(example.get("times_s", [])) if isinstance(example.get("times_s", []), (list, tuple)) else 0
        if total_samples > CONFIG["max_total_samples"]:
            raise ValueError("training_sample_budget")
        if example["review_id"] in identifiers:
            raise ValueError("duplicate_review_id")
        identifiers.add(example["review_id"])
        modes.add(example["source_mode"])
        participants.add(example["participant_id"])
        identity = (example["participant_id"], example["refit_id"], example["role"], example["source_mode"])
        if example["session_id"] in sessions and sessions[example["session_id"]] != identity:
            raise ValueError("session_identity_or_role_leakage")
        sessions[example["session_id"]] = identity
        group = (example["participant_id"], example["refit_id"])
        if group in refits and refits[group] != example["role"]:
            raise ValueError("refit_role_leakage")
        refits[group] = example["role"]
        if example["certainty"] == "uncertain":
            excluded.append({"session_id": example["session_id"], "review_id": example["review_id"],
                             "reason": "uncertain_review_excluded"})
            continue
        if (not _number(example.get("start_s")) or not _number(example.get("end_s"))
                or not 0 <= example["start_s"] < example["end_s"]):
            raise ValueError("invalid_review_interval")
        if any(key not in example for key in ("times_s", "samples", "sample_rate_hz")):
            raise ValueError("reviewed_window_samples_required")
        features, times, samples = _features(example["times_s"], example["samples"], example["sample_rate_hz"],
                                             end_s=example["end_s"])
        prepared.append({"example": example, "features": features, "times": times, "samples": samples,
                         "label": int(example["class_name"] == "double")})
    if len(modes) != 1:
        raise ValueError("mixed_source_modes_forbidden")
    if len(participants) != 1:
        raise ValueError("personal_model_requires_one_participant")
    rates = {row["example"]["sample_rate_hz"] for row in prepared}
    if len(rates) != 1:
        raise ValueError("consistent_sample_rate_required")
    # Overlapping labels or causal feature windows within a recording are not
    # independent examples. Copied signal windows or consecutive waveform runs
    # are caught even when recording IDs or numeric clocks have been changed.
    seen_windows, sample_owners = {}, {}
    by_session = {}
    for row in sorted(prepared, key=lambda r: (r["example"]["session_id"], r["example"]["end_s"], r["example"]["review_id"])):
        e = row["example"]
        start, end = e["end_s"] - CONFIG["window_s"], e["end_s"]
        for previous in by_session.setdefault(e["session_id"], []):
            p = previous["example"]
            if max(start, p["end_s"] - CONFIG["window_s"]) < min(end, p["end_s"]) - 1e-9:
                raise ValueError("overlapping_causal_training_windows")
            if max(e["start_s"], p["start_s"]) < min(e["end_s"], p["end_s"]) - 1e-9:
                raise ValueError("overlapping_review_intervals")
        by_session[e["session_id"]].append(row)
        fingerprint = _digest(row["samples"])
        if fingerprint in seen_windows:
            raise ValueError("duplicate_signal_window_across_reviews_or_sessions")
        seen_windows[fingerprint] = e["review_id"]
        # Require a consecutive shared run, not isolated equal quantized values.
        # Do not assume separate recording clocks share an epoch.
        shared_run, previous_match = 0, None
        for index, values in enumerate(row["samples"]):
            token = (values[0], values[1])
            owner = sample_owners.get(token)
            if owner and owner[0] != e["review_id"]:
                shared_run = shared_run + 1 if previous_match == (owner[0], owner[1] - 1) else 1
                previous_match = owner
            else:
                shared_run, previous_match = 0, None
            if shared_run >= max(4, math.ceil(.1 * e["sample_rate_hz"])):
                raise ValueError("overlapping_raw_samples_across_sessions")
            sample_owners[token] = (e["review_id"], index)
    train = sorted((r for r in prepared if r["example"]["role"] == "train"),
                   key=lambda r: (r["example"]["session_id"], r["example"]["review_id"]))
    dev = sorted((r for r in prepared if r["example"]["role"] == "development"),
                 key=lambda r: (r["example"]["session_id"], r["example"]["review_id"]))
    positives, negatives = sum(r["label"] for r in train), sum(1 - r["label"] for r in train)
    if positives < 3 or negatives < 3:
        raise ValueError("three_positive_and_three_negative_reviewed_train_windows_required")
    vectors = [r["features"] for r in train]
    mean = [statistics.fmean(v[i] for v in vectors) for i in range(len(FEATURES))]
    scale = [max(1e-6, math.sqrt(statistics.fmean((v[i] - mean[i]) ** 2 for v in vectors))) for i in range(len(FEATURES))]
    normalized = [_normalized(v, mean, scale) for v in vectors]
    weights, bias = [0.0] * len(FEATURES), 0.0
    for _ in range(CONFIG["steps"]):
        errors = [(_sigmoid(sum(w * v for w, v in zip(weights, x)) + bias) - r["label"])
                  * len(train) / (2 * (positives if r["label"] else negatives)) for x, r in zip(normalized, train)]
        gradient = [statistics.fmean(err * x[i] for err, x in zip(errors, normalized)) + CONFIG["l2"] * weights[i]
                    for i in range(len(FEATURES))]
        weights = [w - CONFIG["learning_rate"] * g for w, g in zip(weights, gradient)]
        bias -= CONFIG["learning_rate"] * statistics.fmean(errors)
    mode = next(iter(modes))
    core = {"format": FORMAT, "model_kind": "personal_causal_window_logistic",
            "status": "PIPELINE_TESTED_ONLY" if mode == "synthetic" else "REAL_DATA_EXPLORATORY",
            "source_mode": mode, "control_authority": False, "window_s": CONFIG["window_s"],
            "sample_rate_hz": next(iter(rates)), "feature_names": list(FEATURES),
            "mean": mean, "scale": scale, "weights": weights, "bias": bias,
            "threshold": CONFIG["threshold"], "calibration": "uncalibrated_window_score",
            "config": dict(CONFIG), "config_sha256": _digest(CONFIG),
            "training_data_sha256": _digest([r["example"] for r in train]),
            "positive_examples": positives, "negative_examples": negatives,
            "example_manifest": [{"session_id": r["example"]["session_id"], "review_id": r["example"]["review_id"],
                                   "class_name": r["example"]["class_name"], "sha256": _digest(r["example"])} for r in train]}
    model = {**core, "id": "web-blink-" + _digest(core)[:24], "held_out": None}
    if dev:
        model["held_out"] = _window_metrics(dev, [_sigmoid(sum(w * v for w, v in zip(weights, _normalized(r["features"], mean, scale))) + bias) for r in dev])
    report = {"version": "personal-blink-window-report-1", "status": model["status"], "source_mode": mode,
              "control_authority": False, "train_windows": len(train), "development_windows": len(dev),
              "train_sessions": len({r["example"]["session_id"] for r in train}),
              "development_sessions": len({r["example"]["session_id"] for r in dev}),
              "positive_examples": positives, "negative_examples": negatives,
              "negative_class_counts": {k: sum(r["example"]["class_name"] == k for r in train) for k in sorted(CLASSES - {"double"})},
              "excluded": excluded, "held_out": model["held_out"],
              "held_out_unavailable_reason": None if dev else "no_reviewed_whole_development_sessions",
              "training_accuracy": None, "training_accuracy_reason": "resubstitution_is_not_validation",
              "event_accuracy": None, "event_accuracy_reason": "window_model_has_no_event_or_music_authority",
              "input_data_sha256": _digest(sorted(examples, key=lambda e: (e["session_id"], e["review_id"]))),
              "training_data_sha256": core["training_data_sha256"], "config_sha256": core["config_sha256"],
              "final_test_consumed": False}
    return {"model": model, "report": report}


def predict_window(model, times_s, samples, sample_rate_hz):
    if (model.get("format") != FORMAT or model.get("model_kind") != "personal_causal_window_logistic"
            or model.get("control_authority") is not False or model.get("feature_names") != list(FEATURES)
            or model.get("config_sha256") != _digest(CONFIG) or model.get("config") != CONFIG
            or not _number(sample_rate_hz) or sample_rate_hz != model.get("sample_rate_hz")):
        raise ValueError("incompatible_personal_window_model")
    if (any(not isinstance(model.get(k), list) or len(model[k]) != len(FEATURES)
            or any(not _number(v) for v in model[k]) for k in ("mean", "scale", "weights"))
            or any(v <= 0 for v in model["scale"]) or not _number(model.get("bias"))):
        raise ValueError("invalid_personal_window_coefficients")
    features, _, _ = _features(times_s, samples, sample_rate_hz)
    return _sigmoid(sum(w * v for w, v in zip(model["weights"], _normalized(features, model["mean"], model["scale"]))) + model["bias"])
