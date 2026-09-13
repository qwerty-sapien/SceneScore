"""Local immutable personal checkpoints. Evaluation is advisory, never a load gate."""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import re
import statistics
import tempfile
import time

from .web_model import CONFIG, FEATURES, FORMAT, _digest, _normalized, _sigmoid

DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "private_data/02A/training-web/automatic"
CHECKPOINT_FORMAT = "scenescore.personal-blink-checkpoint/1"
MAX_FILE = 2 * 1024 * 1024


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError("symlink_artifact")
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    if len(payload) > MAX_FILE:
        raise ValueError("artifact_size_limit")
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError("invalid_artifact_file")
    return json.loads(path.read_text())


def validate_model(model):
    if (model.get("format") != FORMAT or model.get("model_kind") != "personal_causal_window_logistic"
            or model.get("control_authority") is not False or model.get("feature_names") != list(FEATURES)
            or model.get("config") != CONFIG or model.get("config_sha256") != _digest(CONFIG)
            or model.get("source_mode") not in {"synthetic", "real_device"}
            or model.get("threshold") != CONFIG["threshold"]):
        raise ValueError("incompatible_checkpoint_model")
    for key in ("mean", "scale", "weights"):
        values = model.get(key)
        if (not isinstance(values, list) or len(values) != len(FEATURES)
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values)):
            raise ValueError("invalid_checkpoint_coefficients")
    if (any(v <= 0 for v in model["scale"]) or not isinstance(model.get("bias"), (int, float))
            or not math.isfinite(model["bias"]) or isinstance(model["bias"], bool)):
        raise ValueError("invalid_checkpoint_coefficients")
    rate = model.get("sample_rate_hz")
    if (not isinstance(rate, (int, float)) or isinstance(rate, bool) or not math.isfinite(rate)
            or not CONFIG["sample_rate_min_hz"] <= rate <= CONFIG["sample_rate_max_hz"]):
        raise ValueError("invalid_checkpoint_rate")
    channels = model.get("channel_contract")
    if channels not in ([["AF7", "uV"], ["AF8", "uV"]], [["FP1", "uV"], ["FP2", "uV"]]):
        raise ValueError("invalid_checkpoint_channels")


def fit_checkpoint(examples, contract, parent=None):
    """Bounded warm start; all inputs are explicitly learning-only EEG features."""
    if not 1 <= len(examples) <= 128 or len({e["id"] for e in examples}) != len(examples):
        raise ValueError("bounded_distinct_learning_examples_required")
    for e in examples:
        if (e.get("partition") != "learning" or e.get("label") not in {0, 1}
                or len(e.get("features", [])) != len(FEATURES)
                or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in e["features"])):
            raise ValueError("learning_only_finite_features_required")
        if e.get("contract") != contract:
            raise ValueError("example_contract_mismatch")
    positives = sum(e["label"] for e in examples)
    negatives = len(examples) - positives
    if min(positives, negatives) < 20:
        raise ValueError("twenty_positive_and_background_examples_required")
    vectors = [e["features"] for e in examples]
    if parent is not None:
        validate_checkpoint(parent)
        old = parent["model"]
        if model_contract(old) != contract:
            raise ValueError("incompatible_parent_checkpoint")
        mean, scale = old["mean"][:], old["scale"][:]
        weights, bias = old["weights"][:], old["bias"]
    else:
        mean = [statistics.fmean(v[i] for v in vectors) for i in range(len(FEATURES))]
        scale = [max(1e-6, math.sqrt(statistics.fmean((v[i] - mean[i]) ** 2 for v in vectors)))
                 for i in range(len(FEATURES))]
        weights, bias = [0.0] * len(FEATURES), 0.0
    normalized = [_normalized(v, mean, scale) for v in vectors]
    for _ in range(CONFIG["steps"]):
        errors = [(_sigmoid(sum(w * v for w, v in zip(weights, x)) + bias) - e["label"])
                  * len(examples) / (2 * (positives if e["label"] else negatives))
                  for x, e in zip(normalized, examples)]
        gradients = [statistics.fmean(err * x[i] for err, x in zip(errors, normalized))
                     + CONFIG["l2"] * weights[i] for i in range(len(FEATURES))]
        weights = [w - CONFIG["learning_rate"] * g for w, g in zip(weights, gradients)]
        bias -= CONFIG["learning_rate"] * statistics.fmean(errors)
    model = {"format": FORMAT, "model_kind": "personal_causal_window_logistic", "control_authority": False,
             "feature_names": list(FEATURES), "config": dict(CONFIG), "config_sha256": _digest(CONFIG),
             "mean": mean, "scale": scale, "weights": weights, "bias": bias, "threshold": CONFIG["threshold"],
             "window_s": 2.0, "source_mode": contract["source_mode"], "sample_rate_hz": contract["sample_rate_hz"],
             "channel_contract": contract["channels"], "positive_examples": positives, "negative_examples": negatives}
    result = {"format": CHECKPOINT_FORMAT, "created_ns": time.time_ns(), "model": model,
              "parent_id": parent["id"] if parent else None,
              "training_steps": (parent["training_steps"] if parent else 0) + CONFIG["steps"],
              "training_data_sha256": _digest(examples), "examples": [e["id"] for e in examples],
              "label_semantics": "human_B_reports_and_assumed_background_not_independent_truth",
              "evaluation": None}
    result["id"] = "checkpoint-" + _digest(result)
    validate_checkpoint(result)
    return result


def model_contract(model):
    return {"source_mode": model["source_mode"], "sample_rate_hz": model["sample_rate_hz"],
            "channels": model["channel_contract"]}


def validate_checkpoint(value):
    if not isinstance(value, dict) or value.get("format") != CHECKPOINT_FORMAT:
        raise ValueError("invalid_checkpoint_format")
    core = {k: v for k, v in value.items() if k != "id"}
    if value.get("id") != "checkpoint-" + _digest(core):
        raise ValueError("checkpoint_integrity_mismatch")
    validate_model(value["model"])


def training_batch(examples, parent=None):
    """At most 64 per class: latest unseen examples plus reproducible historical replay."""
    seen = set(parent["examples"]) if parent else set()
    selected = []
    for label in (0, 1):
        rows = sorted((e for e in examples if e["label"] == label), key=lambda e: (e["created_ns"], e["id"]))
        fresh = [e for e in rows if e["id"] not in seen][-32:]
        fresh_ids = {e["id"] for e in fresh}
        history = sorted((e for e in rows if e["id"] not in fresh_ids), key=lambda e: _digest(e["id"]))
        selected.extend(fresh + history[:64 - len(fresh)])
    return sorted(selected, key=lambda e: e["id"])


class CheckpointStore:
    def __init__(self, root=DEFAULT_ROOT):
        self.root = Path(root)

    def load(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r"checkpoint-[0-9a-f]{64}", identifier):
            raise ValueError("invalid_checkpoint_id")
        value = read_json(self.root / "checkpoints" / (identifier + ".json"))
        validate_checkpoint(value)
        if value["id"] != identifier:
            raise ValueError("checkpoint_filename_mismatch")
        return value

    def save(self, checkpoint):
        validate_checkpoint(checkpoint)
        path = self.root / "checkpoints" / (checkpoint["id"] + ".json")
        if path.exists():
            if self.load(checkpoint["id"]) != checkpoint:
                raise ValueError("immutable_checkpoint_conflict")
        else:
            atomic_json(path, checkpoint)
        return checkpoint

    def evaluation(self, identifier):
        path = self.root / "evaluations" / (identifier + ".json")
        if not path.exists():
            return None
        value = read_json(path)
        if value.get("checkpoint_id") != identifier:
            raise ValueError("evaluation_checkpoint_mismatch")
        return value

    def save_evaluation(self, identifier, report):
        self.load(identifier)
        atomic_json(self.root / "evaluations" / (identifier + ".json"), {**report, "checkpoint_id": identifier})

    def catalog(self, contract=None):
        paths = sorted((self.root / "checkpoints").glob("checkpoint-*.json"))
        if len(paths) > 4096:
            raise ValueError("checkpoint_catalog_capacity")
        valid, invalid = [], []
        for path in paths:
            try:
                checkpoint = self.load(path.stem)
                if contract is None or model_contract(checkpoint["model"]) == contract:
                    valid.append(checkpoint)
            except (ValueError, KeyError, TypeError, OSError):
                invalid.append(path.stem)
        return sorted(valid, key=lambda v: (v["created_ns"], v["id"]), reverse=True), invalid

    def latest(self, contract):
        values, _ = self.catalog(contract)
        return copy.deepcopy(values[0]) if values else None

    def summaries(self, contract=None):
        values, invalid = self.catalog(contract)
        rows = []
        for cp in values:
            try:
                evaluation = self.evaluation(cp["id"])
            except (ValueError, OSError, KeyError):
                evaluation = None
            rows.append({"id": cp["id"], "created_ns": cp["created_ns"], "parent_id": cp["parent_id"],
                         "training_steps": cp["training_steps"], "source_mode": cp["model"]["source_mode"],
                         "evaluation": evaluation})
        return {"checkpoints": rows, "invalid_checkpoint_ids": invalid}
