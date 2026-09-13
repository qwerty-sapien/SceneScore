"""Versioned grouped index freeze and honest no-data readiness reporting."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
from pathlib import Path

from modules.muse.acquisition.protocol import validate_protocol
from modules.muse.acquisition.store import manifest, read_json, replay
from modules.muse.baseline.causal import Config
from modules.muse.training.pipeline import audit_real, digest, encoded, validate_split


def freeze_index(root, assignments, output):
    """User-declared whole-session groups are locked before feature extraction."""
    root, output = Path(root).resolve(), Path(output)
    validate_split(assignments)
    sessions = []
    for item in assignments:
        relative = Path(item["path"])
        path = root / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("session_outside_scope")
        value = manifest(path)
        if value["status"] != "closed":
            raise ValueError("closed_session_required_before_split_freeze")
        protocol = validate_protocol(read_json(path / "protocol.json"))
        for key in ("participant_id", "refit_id", "role", "consent_ref"):
            if protocol[key] != item[key]:
                raise ValueError("assignment_differs_from_precollection_protocol:" + key)
        labels_path = path / "labels.jsonl"
        if not labels_path.is_file() or labels_path.is_symlink():
            raise ValueError("independent_labels_missing")
        import json
        labels = [json.loads(line) for line in labels_path.read_text().splitlines()]
        chunks = list(replay(path))
        content = {"metadata": value["metadata"], "chunks": chunks, "labels": labels}
        sessions.append({**item, "content_sha256": digest(content),
                         "protocol_sha256": hashlib.sha256((path / "protocol.json").read_bytes()).hexdigest()})
    index = {"format": "scenescore.frozen-session-index/2", "sessions": sessions,
             "split": validate_split(sessions), "final_test_reuse": "forbidden_after_FinalTestLock",
             "prediction_features": "raw EEG-derived whitelist only; cues/responses/labels are excluded"}
    audit_real(root, index)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(encoded(index))
    return {"status": "FROZEN", "path": str(output), "index_sha256": digest(index),
            "sessions": len(sessions), "split": index["split"]}


def readiness_report(data_root, *, index=None):
    config = Config()
    blockers = []
    sessions = []
    if index is None:
        blockers.append("No frozen index of consented verified real sessions with independent labels and complete refit splits")
    else:
        sessions = audit_real(Path(data_root), index)
    if not sessions:
        blockers.extend(["No measured hardware/channel/unit/rate/quality verification in an eligible session",
                         "No train/development/final-test real replay comparison",
                         "Matcher tolerance and calibration segment require preregistration on independent development data"])
    measured = {key: None for key in ("tp", "fn", "fp", "recall", "precision", "fp_per_armed_hour",
                                     "fp_per_elapsed_monitored_hour", "armed_hours", "elapsed_monitored_hours",
                                     "candidate_coverage", "ambiguous_label_count", "decision_latency_p50_ms",
                                     "decision_latency_p95_ms", "decision_latency_max_ms", "armed_availability",
                                     "recall_lower_95", "false_activation_upper_95_per_armed_hour")}
    source_files = [Path(__file__), Path(__file__).with_name("pipeline.py"),
                    Path(__file__).parents[1] / "baseline" / "causal.py",
                    Path(__file__).parents[1] / "baseline" / "ragtm.py"]
    return {"format": "scenescore.detector-readiness/1",
            "status": "REAL_DATA_AUDITED_NOT_TRAINED" if sessions else "INSUFFICIENT_REAL_DATA",
            "release_status": "PIPELINE_TESTED_ONLY", "trained_real_models": 0,
            "real_evaluation": "NOT_RUN", "metrics": measured,
            "null_reason": "No eligible real held-out evaluation was run; zero denominators are not perfect metrics",
            "per_session": [], "per_refit": [], "misses_by_cause": None,
            "audited_sessions": sessions, "blockers": blockers,
            "config": asdict(config), "config_sha256": config.digest,
            "code_sha256": {str(p.relative_to(Path(__file__).parents[3])): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in source_files},
            "data_sha256": digest(index) if index else None, "model_sha256": None,
            "matcher": {"status": "NOT_LOCKED", "tolerance_s": None,
                        "tie_rule": "nearest final blink, earliest final blink, lexical label ID",
                        "matching": "chronological one-to-one; full pipeline misses include quality and cooldown",
                        "numerical_tolerance": None},
            "ladder": [{"rung": "A", "kind": "attributed_RAGTM_candidate_port", "control_authority": False,
                        "real_comparison": "NOT_RUN"},
                       {"rung": "B", "kind": "causal_median_MAD_and_double_only_grammar", "candidate": True,
                        "real_comparison": "NOT_RUN"},
                       {"rung": "C", "kind": "regularized_logistic_bounded_causal_features", "candidate": False,
                        "real_comparison": "NOT_RUN", "calibration": "uncalibrated_score"}],
            "closure_floor_ms": 1000 * config.max_gap_s,
            "grammar_semantics": "end-to-next-onset gaps, strict time-after-end-plus-max-gap closure; pack onset-gap examples differ",
            "rollback": "python -m modules.muse.acquisition replay SESSION --detect --arm-after-s 1.0 (omit learned model; default causal baseline)",
            "next_status_requires": "Consented, independently labelled verified Muse sessions across separate refits with a frozen split and matcher, followed by causal real replay evaluation"}
