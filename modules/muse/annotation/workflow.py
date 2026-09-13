"""Independent annotations and intent cues. Predictions can never become truth."""
import json
import math
import os
from pathlib import Path
import random
import uuid
from modules.muse.acquisition.store import encoded, manifest, replay

ACTIVITIES = ["quiet_rest", "reading", "watching_animation", "speaking", "smiling", "looking_around",
              "head_turns", "jaw_activity", "gentle_adjustment", "ordinary_blinking"]


def append(path, stream, value):
    manifest(path)
    if stream not in {"cues", "responses", "labels"}:
        raise ValueError("separate_annotation_stream_required")
    target = Path(path) / (stream + ".jsonl")
    if target.is_symlink():
        raise ValueError("symlink_annotation")
    with target.open("ab") as handle:
        os.chmod(target, 0o600)
        handle.write(encoded(value))
        handle.flush()
        os.fsync(handle.fileno())
    return value


def cue_schedule(*, mode, seed=0, count=10, start_s=0):
    if mode not in {"natural_activity", "randomized_instructed", "self_paced"} or not 1 <= count <= 100:
        raise ValueError("bounded_protocol_required")
    rng, result, now = random.Random(seed), [], start_s
    for number in range(count):
        now += rng.uniform(5, 12)
        cue = {"format": "scenescore.cue/1", "id": str(uuid.uuid4()), "index": number,
               "mode": mode, "scheduled_protocol_s": now, "seed": seed,
               "requested_intent": rng.choice(ACTIVITIES) if mode == "natural_activity" else
               "comfortable_double_blink" if mode == "randomized_instructed" else "self_paced_if_comfortable",
               "is_ground_truth": False}
        result.append(cue)
    return result


def cues(path, *, mode, seed=0, count=10, start_s=0):
    return [append(path, "cues", cue) for cue in
            cue_schedule(mode=mode, seed=seed, count=count, start_s=start_s)]


def confirm(path, cue_id, *, performed, confirmation_s):
    if manifest(path)["status"] == "recording":
        raise ValueError("confirmation_must_wait_until_recording_stops")
    if performed not in {"performed", "missed", "uncertain"} or not math.isfinite(confirmation_s):
        raise ValueError("invalid_delayed_response")
    cue_records = Path(path) / "cues.jsonl"
    if not cue_records.exists() or not any(json.loads(line)["id"] == cue_id for line in cue_records.open()):
        raise ValueError("unknown_cue")
    return append(path, "responses", {"format": "scenescore.response/1", "cue_id": cue_id,
                  "performed": performed, "delayed_confirmation_s": confirmation_s, "is_ground_truth": False})


def label(path, *, reviewer, source, evidence_ref, epoch, onset_s, end_s, final_blink_s,
          gesture_count, intent, certainty, supersedes=None):
    if manifest(path)["status"] == "recording":
        raise ValueError("independent_review_must_wait_until_recording_stops")
    if source not in {"independent_observation", "consented_local_video", "independent_review"}:
        raise ValueError("independent_label_source_required")
    if not all(math.isfinite(v) for v in (onset_s, end_s, final_blink_s)):
        raise ValueError("finite_label_times_required")
    if not reviewer or not evidence_ref or not epoch or not 0 <= onset_s <= final_blink_s <= end_s:
        raise ValueError("label_evidence_and_order_required")
    if (gesture_count not in {0, 1, 2, 3} or intent not in {"deliberate", "natural", "ambiguous"}
            or certainty not in {"verified", "uncertain", "disagreement"}):
        raise ValueError("label_class_required")
    session_meta = manifest(path)["metadata"]
    bounds = None
    for chunk in replay(path):
        if chunk["device_epoch"] == epoch:
            bounds = (chunk["device_times_s"][0] if bounds is None else bounds[0], chunk["device_times_s"][-1])
    if bounds is None or onset_s < bounds[0] or end_s > bounds[1]:
        raise ValueError("label_outside_recorded_epoch")
    if supersedes:
        labels = Path(path) / "labels.jsonl"
        if not labels.exists() or not any(json.loads(line)["id"] == supersedes for line in labels.open()):
            raise ValueError("unknown_superseded_label")
    return append(path, "labels", {"format": "scenescore.label/1", "id": str(uuid.uuid4()),
                  "reviewer": reviewer, "source": source, "evidence_ref": evidence_ref,
                  "clock": "device", "epoch": epoch, "onset_s": onset_s, "end_s": end_s,
                  "final_blink_s": final_blink_s, "gesture_count": gesture_count, "intent": intent,
                  "certainty": certainty, "supersedes": supersedes,
                  "source_mode": session_meta["provenance"]["source_mode"],
                  "is_ground_truth": certainty == "verified" and session_meta["provenance"]["source_mode"] == "real_device"})
