"""Bounded, causal, grouped blink-model research primitives. No automatic capture."""

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import statistics

FEATURES = ("peak_z", "bilateral_ratio", "duration_ms", "rise_slope", "fall_slope", "imu_rms")
ROLES = ("train", "development", "final_test")


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def causal_features(samples, *, sample_rate_hz, noise_uv, imu=()):
    """Only supplied past window; no future normalization/annotation fields accepted."""
    if (
        not 0 < sample_rate_hz <= 2048
        or not math.isfinite(noise_uv)
        or not 0 < noise_uv
        or not 2 <= len(samples) <= 4096
    ):
        raise ValueError("causal_window_preconditions")
    if any(not math.isfinite(v) for v in imu):
        raise ValueError("non_finite_motion")
    if any(len(row) != 2 or any(not math.isfinite(v) for v in row) for row in samples):
        raise ValueError("two_verified_frontal_channels_required")
    left = [abs(s[0]) for s in samples]
    right = [abs(s[1]) for s in samples]
    signal = [(a + b) / 2 for a, b in zip(left, right)]
    peak = max(signal)
    i = signal.index(peak)
    return {
        "peak_z": peak / noise_uv,
        "bilateral_ratio": min(max(left), max(right)) / max(1e-9, max(max(left), max(right))),
        "duration_ms": 1000 * sum(v >= peak / 2 for v in signal) / sample_rate_hz,
        "rise_slope": (peak - signal[0]) / max(1 / sample_rate_hz, i / sample_rate_hz) / noise_uv,
        "fall_slope": (signal[-1] - peak) / max(1 / sample_rate_hz, (len(signal) - 1 - i) / sample_rate_hz) / noise_uv,
        "imu_rms": math.sqrt(sum(v * v for v in imu) / len(imu)) if imu else 0.0,
    }


def feature_vector(values):
    if set(values) != set(FEATURES):
        raise ValueError("feature_whitelist_violation")
    vector = [float(values[k]) for k in FEATURES]
    if any(not math.isfinite(v) for v in vector):
        raise ValueError("non_finite_features")
    return vector


def validate_split(sessions):
    if not sessions or len(sessions) > 1000:
        raise ValueError("bounded_sessions_required")
    ids = set()
    refits = {}
    participants = set()
    for s in sessions:
        if s["role"] not in ROLES or s["session_id"] in ids:
            raise ValueError("split_or_duplicate_session")
        if any(not s[k] for k in ("session_id", "participant_id", "refit_id")):
            raise ValueError("group_identity_required")
        ids.add(s["session_id"])
        participants.add(s["participant_id"])
        group = (s["participant_id"], s["refit_id"])
        if group in refits and refits[group] != s["role"]:
            raise ValueError("refit_split_leakage")
        refits[group] = s["role"]
    if set(s["role"] for s in sessions) != set(ROLES):
        raise ValueError("all_three_split_roles_required")
    return {
        "split_hash": digest(sessions),
        "participants": len(participants),
        "generalization_scope": "within_person_only"
        if len(participants) == 1
        else "multi_participant_exploratory_no_cross_person_claim",
        "groups": len(refits),
    }


def audit_real(root: Path, index):
    """No absent data can become a model. All bytes/labels are frozen before fitting."""
    from modules.muse.acquisition.store import manifest, replay
    from modules.muse.acquisition.protocol import validate_protocol

    validate_split(index["sessions"])
    results = []
    for item in index["sessions"]:
        unresolved = root / item["path"]
        path = unresolved.resolve()
        if not path.is_relative_to(root.resolve()) or unresolved.is_symlink():
            raise ValueError("session_outside_scope")
        m = manifest(path)
        meta = m["metadata"]
        if (
            meta["session_id"] != item["session_id"]
            or not meta["hardware_verified"]
            or meta["provenance"]["source_mode"] != "real_device"
        ):
            raise ValueError("genuine_verified_session_required")
        if not item.get("consent_ref"):
            raise ValueError("consent_reference_required")
        protocol_path = path / "protocol.json"
        if not protocol_path.is_file() or protocol_path.is_symlink():
            raise ValueError("recorded_participant_consent_protocol_required")
        protocol = validate_protocol(json.loads(protocol_path.read_text()))
        if any(protocol[key] != item[key] for key in ("participant_id", "refit_id", "role", "consent_ref")):
            raise ValueError("split_differs_from_precollection_assignment")
        if item.get("protocol_sha256") != hashlib.sha256(protocol_path.read_bytes()).hexdigest():
            raise ValueError("changed_frozen_protocol")
        labels_path = path / "labels.jsonl"
        if not labels_path.is_file():
            raise ValueError("independent_labels_missing")
        labels = [json.loads(line) for line in labels_path.read_text().splitlines()]
        if not labels or any(
            label["source"] not in ("independent_observation", "consented_local_video", "independent_review")
            or not label.get("reviewer")
            or not label.get("evidence_ref")
            or label.get("source_mode") != "real_device"
            for label in labels
        ):
            raise ValueError("independent_labels_required")
        chunks = list(replay(path))
        if not chunks:
            raise ValueError("empty_session")
        content = {"metadata": meta, "chunks": chunks, "labels": labels}
        if digest(content) != item["content_sha256"]:
            raise ValueError("changed_frozen_session")
        results.append(
            {
                "session_id": item["session_id"],
                "role": item["role"],
                "chunks": len(chunks),
                "labels": len(resolve_labels(labels)),
                "content_sha256": item["content_sha256"],
            }
        )
    return results


def resolve_labels(labels):
    """Append-only supersession is resolved before locking, not by detector score."""
    by_id = {}
    superseded = set()
    for label in labels:
        if label["id"] in by_id:
            raise ValueError("duplicate_label")
        old = label.get("supersedes")
        if old:
            if old not in by_id or old in superseded:
                raise ValueError("ambiguous_label_supersession")
            superseded.add(old)
        by_id[label["id"]] = label
    return [label for key, label in by_id.items() if key not in superseded]


def fit_scaler(rows):
    if not rows or len(rows) > 10000:
        raise ValueError("training_row_budget")
    if any(r["role"] != "train" for r in rows):
        raise ValueError("training_only_fit")
    vectors = [feature_vector(r["features"]) for r in rows]
    mean = [statistics.fmean(v[i] for v in vectors) for i in range(len(FEATURES))]
    scale = [
        max(1e-6, math.sqrt(statistics.fmean((v[i] - mean[i]) ** 2 for v in vectors))) for i in range(len(FEATURES))
    ]
    return mean, scale


def normalize(values, mean, scale):
    return [(v - m) / s for v, m, s in zip(feature_vector(values), mean, scale)]


def sigmoid(value):
    return 1 / (1 + math.exp(-max(-40, min(40, value))))


def fit_logistic(rows, *, steps=200, l2=0.1, rate=0.05):
    if not 1 <= steps <= 500 or not 0.0001 <= l2 <= 10 or not 0.0001 <= rate <= 0.2:
        raise ValueError("fit_budget")
    if any(r.get("label") not in (0, 1) for r in rows):
        raise ValueError("independent_binary_labels_required")
    if {r["label"] for r in rows} != {0, 1}:
        raise ValueError("both_label_classes_required")
    mean, scale = fit_scaler(rows)
    vectors = [normalize(r["features"], mean, scale) for r in rows]
    w = [0.0] * len(FEATURES)
    bias = 0.0
    for _ in range(steps):
        errors = [sigmoid(sum(a * b for a, b in zip(w, x)) + bias) - r["label"] for x, r in zip(vectors, rows)]
        for i in range(len(w)):
            w[i] -= rate * (statistics.fmean(e * x[i] for e, x in zip(errors, vectors)) + l2 * w[i])
        bias -= rate * statistics.fmean(errors)
    return {
        "format": "scenescore.detector/1",
        "kind": "regularized_logistic",
        "feature_names": list(FEATURES),
        "mean": mean,
        "scale": scale,
        "weights": w,
        "bias": bias,
        "training_hash": digest(rows),
        "calibration": "uncalibrated_score",
        "steps": steps,
        "l2": l2,
        "online_adaptation": False,
    }


def fit_anomaly(rows):
    """Training-only one-component PCA plus two-centre distance. Novelty, not intent."""
    mean, scale = fit_scaler(rows)
    vectors = [normalize(r["features"], mean, scale) for r in rows]
    axis = [1 / math.sqrt(len(FEATURES))] * len(FEATURES)
    for _ in range(25):
        y = [statistics.fmean(x[i] * sum(a * b for a, b in zip(x, axis)) for x in vectors) for i in range(len(axis))]
        norm = math.sqrt(sum(v * v for v in y))
        axis = [v / max(norm, 1e-9) for v in y]
    projections = [sum(a * b for a, b in zip(x, axis)) for x in vectors]
    centres = [min(projections), max(projections)]
    for _ in range(25):
        groups = [[], []]
        for v in projections:
            groups[int(abs(v - centres[1]) < abs(v - centres[0]))].append(v)
        centres = [statistics.fmean(g) if g else old for g, old in zip(groups, centres)]
    return {
        "format": "scenescore.detector/1",
        "kind": "pca_two_cluster_novelty",
        "feature_names": list(FEATURES),
        "mean": mean,
        "scale": scale,
        "axis": axis,
        "centres": centres,
        "training_hash": digest(rows),
        "semantics": "novelty_not_blink_intent",
        "online_adaptation": False,
    }


def score(model, features):
    x = normalize(features, model["mean"], model["scale"])
    if model["kind"] == "regularized_logistic":
        return sigmoid(sum(a * b for a, b in zip(x, model["weights"])) + model["bias"])
    if model["kind"] == "pca_two_cluster_novelty":
        projection = sum(a * b for a, b in zip(x, model["axis"]))
        return min(abs(projection - c) for c in model["centres"])
    raise ValueError("unknown_safe_model_kind")


def self_train(labelled, unlabelled, *, calibration_evidence):
    if (
        calibration_evidence.get("partition") != "development"
        or calibration_evidence.get("validated") is not True
        or not calibration_evidence.get("report_hash")
    ):
        raise ValueError("independent_development_calibration_required")
    if any(r["role"] != "train" for r in unlabelled):
        raise ValueError("unlabelled_test_leakage")
    base = fit_logistic(labelled)
    pseudo = []
    for r in unlabelled:
        value = score(base, r["features"])
        if value >= 0.95 or value <= 0.05:
            pseudo.append({**r, "label": int(value >= 0.95), "label_origin": "pseudo_train_only"})
    limit = min(len(labelled) // 2, 500)
    pseudo = pseudo[:limit]
    # Avoid pseudo-class collapse; no ambiguous examples are promoted to truth.
    if not pseudo or {r["label"] for r in pseudo} != {0, 1}:
        raise ValueError("pseudo_balance_gate")
    model = fit_logistic(labelled + pseudo)
    model["pseudo_count"] = len(pseudo)
    model["calibration_evidence"] = calibration_evidence
    return model


def choose_development(candidates, recall_floor=0.95, max_latency_s=0.75, min_availability=0.95):
    if any(c["partition"] != "development" for c in candidates):
        raise ValueError("final_test_selection_forbidden")
    eligible = [
        c
        for c in candidates
        if c["recall"] >= recall_floor and c["latency_p95_s"] <= max_latency_s and c["availability"] >= min_availability
    ]
    return (
        min(eligible, key=lambda c: (c["fp_per_armed_hour"], c["latency_p95_s"], c["model_id"])) if eligible else None
    )


def save_deployment(path: Path, model, *, real_audit, selection, grammar, channel_contract):
    if not real_audit or not selection or selection.get("partition") != "development":
        raise ValueError("real_data_and_development_selection_required")
    if not grammar or not channel_contract:
        raise ValueError("deployment_contract_missing")
    artifact = {
        "format": "scenescore.deployment/1",
        "model": model,
        "grammar": grammar,
        "channel_contract": channel_contract,
        "calibration": "frozen_separate_segment_only",
        "real_audit": real_audit,
        "selection": selection,
        "online_adaptation": False,
        "rollback": "modules.muse.baseline.causal",
        "status": "REAL_DATA_EXPLORATORY",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded(artifact))
    return digest(artifact)


@dataclass(frozen=True)
class FinalTestLock:
    model_hash: str
    split_hash: str
    matcher_hash: str

    def claim(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(encoded(self.__dict__))
