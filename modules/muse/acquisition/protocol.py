"""Foreground, consented collection with explicit session/refit/split provenance."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from modules.muse.acquisition.live import capture_lsl
from modules.muse.acquisition.store import atomic, encoded, manifest, replay
from modules.muse.annotation.workflow import append, cue_schedule


def validate_protocol(protocol):
    if protocol.get("format") != "scenescore.collection-protocol/1":
        raise ValueError("collection_protocol_format_required")
    for key in ("participant_id", "refit_id", "consent_ref", "consent_words", "retention_until", "recorded_at_utc"):
        if not isinstance(protocol.get(key), str) or not protocol[key].strip():
            raise ValueError("participant_supplied_protocol_field_required:" + key)
    if protocol.get("role") not in {"train", "development", "final_test"}:
        raise ValueError("assign_session_role_before_collection")
    consent = protocol.get("consent", {})
    for key in ("frontal_eeg_and_timestamps", "local_storage_only", "retention_understood", "stop_and_delete_anytime"):
        if consent.get(key) is not True:
            raise ValueError("explicit_collection_consent_required:" + key)
    if protocol.get("mode") not in {"natural_activity", "randomized_instructed", "self_paced"}:
        raise ValueError("collection_mode_required")
    if not isinstance(protocol.get("headset_removed_and_refitted"), bool):
        raise ValueError("explicit_refit_history_required")
    return protocol


def collect_session(path, metadata, *, protocol, source_id, seconds, explicitly_started,
                    stop=None, report=print):
    """Cues are instructions only. No detector/prediction runs in collection."""
    validate_protocol(protocol)
    if not explicitly_started or not math.isfinite(seconds) or not 1 <= seconds <= 600:
        raise ValueError("explicit_start_and_1_to_600_second_budget_required")
    path = Path(path)
    planned = cue_schedule(mode=protocol["mode"], seed=protocol.get("seed", 0), count=100)
    planned = [cue for cue in planned if cue["scheduled_protocol_s"] < seconds]
    pending = list(planned)
    started = False
    report({"about_to": "record local real-device training session", "path": str(path),
            "mode": protocol["mode"], "role": protocol["role"], "refit_id": protocol["refit_id"],
            "seconds_limit": seconds, "controls": "DISARMED", "predictions": "OFF",
            "instructions": "Stop with Ctrl-C at any time. Confirm after recording; cues are never truth labels."})

    def progress(value):
        nonlocal started
        if not started:
            # capture_lsl creates the exclusive raw store before its first progress callback.
            atomic(path / "protocol.json", {**protocol, "session_id": metadata["session_id"],
                                           "protocol_sha256": hashlib.sha256(encoded(protocol)).hexdigest(),
                                           "publication_consent": False, "prediction_state": "OFF"})
            started = True
        if isinstance(value, dict):
            while pending and pending[0]["scheduled_protocol_s"] <= value["elapsed_s"]:
                cue = pending.pop(0)
                cue.update(displayed_protocol_s=value["elapsed_s"],
                           observed_source_s=value["source_s"],
                           observation_note="Latest batch source time, not a synchronized cue-to-device clock mapping")
                append(path, "cues", cue)
                report({"cue": cue["requested_intent"], "cue_id": cue["id"], "is_ground_truth": False})
            # Avoid broadcasting raw samples to the feedback surface or logs.
            report({k: v for k, v in value.items() if k != "raw_channels"})
        else:
            report(value)

    result = capture_lsl(path, metadata, source_id=source_id, seconds=seconds,
                         consent=True, stop=stop, report=progress)
    summary = review_session(path)
    atomic(path / "collection-summary.json", summary)
    report({"recorded": summary, "path": str(path), "next": "Review raw trace and append independent delayed labels"})
    return {**result, "session_path": str(path), "summary": summary}


def review_session(path):
    value = manifest(path)
    total, dropped = 0, 0
    segments = []
    for chunk in replay(path):
        total += len(chunk["samples"])
        dropped += chunk["dropped_samples_before"]
        if not segments or segments[-1]["epoch"] != chunk["device_epoch"]:
            segments.append({"epoch": chunk["device_epoch"], "start_s": chunk["device_times_s"][0]})
        segments[-1]["end_s"] = chunk["device_times_s"][-1]
    rate = value["metadata"]["sample_rate_hz"]
    return {"session_id": value["metadata"]["session_id"], "source_mode": value["metadata"]["provenance"]["source_mode"],
            "status": value["status"], "samples": total, "estimated_dropped_samples": dropped,
            "elapsed_monitored_s": sum(s["end_s"] - s["start_s"] + 1 / rate for s in segments) if segments else None,
            "sampled_exposure_s": total / rate, "armed_exposure_s": 0.0,
            "negative_activity_semantics": "Protocol assignment only; independent labels establish actual activity",
            "source_segments": segments,
            "quality": "unverified", "hardware_performance": "NOT_RUN"}
