"""Canonical JSON Schema plus cross-field semantic validation."""
import hashlib
import json
import math
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "contracts/0.1/schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def load_json(path):
    def invalid(value):
        raise ValueError(f"Non-finite JSON constant: {value}")
    return json.loads(Path(path).read_text(), parse_constant=invalid)


def content_hash(payload: bytes) -> str:
    """Hash persisted UTF-8 payload bytes, not a reserialized floating-point object."""
    return hashlib.sha256(payload).hexdigest()


def approved_payload(payload: bytes, approval: dict, input_hashes: list[str]) -> dict:
    validate(approval)
    plan = json.loads(payload)
    validate(plan)
    if (plan["kind"] != "ArrangementPlan" or approval["decision"] != "approved"
            or approval["plan_id"] != plan["id"]
            or approval["approved_payload_sha256"] != content_hash(payload)
            or approval["input_hashes"] != input_hashes
            or input_hashes != [plan["scene_hash"], plan["composition_hash"]]):
        raise ValueError("stale_or_unapproved_plan")
    return plan


def validate(data):
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non_finite")
        if isinstance(value, dict):
            for x in value.values():
                finite(x)
        if isinstance(value, list):
            for x in value:
                finite(x)
    finite(data)
    errors = list(VALIDATOR.iter_errors(data))
    if errors:
        raise ValueError("schema_invalid: " + errors[0].message[:200])
    semantic(data)
    return data


def semantic(d):
    k = d["kind"]
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)
    def unique(values):
        return len(set(values)) == len(values)
    def increasing(values):
        return all(a < b for a, b in zip(values, values[1:]))
    def times(names):
        ts = [d[n] for n in names]
        require(len({(t["clock"], t["epoch"]) for t in ts}) == 1, "mixed_clock_or_epoch")
        require(all(a["seconds"] <= b["seconds"] for a, b in zip(ts, ts[1:])), "time_reversal")
    if k in ("AcquisitionMetadata", "EEGChunk"):
        require(unique([c["name"] for c in d["channels"]]), "duplicate_channels")
    if k == "AcquisitionMetadata" and d["provenance"]["source_mode"] == "real_device":
        require(d["hardware_verified"], "unverified_real_device")
    if k == "EEGChunk":
        require(len(d["samples"]) == len(d["device_times_s"]), "sample_time_length")
        require(all(len(row) == len(d["channels"]) for row in d["samples"]), "channel_dimension")
        require(increasing(d["device_times_s"]), "nonmonotonic_samples")
        require(d["host_receipt"]["clock"] == "host_monotonic", "receipt_clock")
        if d["imu"] is not None:
            require(len(d["imu"]["samples"]) == len(d["samples"]), "imu_dimension")
    if k == "BlinkCandidate":
        times(["start", "end"])
        if d["score_type"] == "calibrated_probability":
            require(0 <= d["score"] <= 1, "probability_range")
    if k == "GestureEvent":
        times(["start", "end", "final_blink", "decision"])
        require(len(d["candidate_ids"]) == d["gesture_count"], "candidate_count")
        require(abs(d["decision"]["seconds"] - d["final_blink"]["seconds"] - d["closure_delay_s"]) < 1e-9, "closure_delay")
        require(d["status"] != "rejected" or bool(d["reason"]), "missing_rejection_reason")
    if k == "ControlAction":
        times(["request", "expires"])
        active = d["status"] != "suppressed"
        require(active or bool(d["reason"]), "missing_suppression_reason")
        if active:
            require(d["quality"]["state"] == "good", "quality_gate")
            require(d["approved_plan_hash"] is not None, "approval_required")
            require(d["action"] != "none", "active_noop")
        if d["action"] == "request_modulation":
            require(d["gesture_count"] == 2 and d["signed_semitones"] in (-2, 2), "double_only_modulation")
            require(d["before"] == d["after"], "unrelated_lane_change")
            require(d["boundary"] == "next_approved_bar_or_phrase" and d["scene_policy_id"] is not None, "modulation_policy")
        if d["action"] == "toggle_approved_expression_preset":
            require(d["profile"] == "multi_count_expression_experiment" and d["gesture_count"] == 3, "experimental_only")
            require(abs(d["after"]["master_gain_db"]-d["before"]["master_gain_db"]) <= 3, "expression_gain_bound")
        if d["profile"] == "double_modulate_mvp" and d["gesture_count"] != 2:
            require(d["action"] == "none" and not active, "default_single_triple_noop")
    if k == "SceneManifest":
        require(unique([o["object_id"] for o in d["objects"]]), "duplicate_object")
    if k in ("ObjectState", "SceneManifest"):
        transform = d["transform"] if k == "ObjectState" else d["camera"]["transform"]
        require(abs(sum(x*x for x in transform["quaternion_xyzw"]) - 1) < 1e-5, "quaternion_norm")
    if k == "ObjectState":
        require(all(a <= b for a,b in zip(d["bounds_min_m"],d["bounds_max_m"])), "bounds_inverted")
        if any(d[n] is None for n in ["velocity_m_s", "acceleration_m_s2", "volume_m3"]):
            require(bool(d["unavailable_reason"]), "null_measure_reason")
    if k == "InteractionEvent":
        require(d["pair"] == sorted(d["pair"]) and d["pair_id"] == "|".join(d["pair"]), "pair_identity")
        require(not d["physical_impact"] or (d["method"] != "heuristic" and d["event_type"] in ("collision", "contact_onset")), "unsupported_impact")
        if d["event_type"] == "near_miss":
            require(d["surface_gap_m"] > d["uncertainty_m"] and not d["physical_impact"], "unproven_near_miss")
    if k in ("CompositionSpec", "BrushGroove"):
        notes = d["notes"] if k == "CompositionSpec" else d["events"]
        require(all(n["start_tick"] + n["duration_ticks"] <= d["length_ticks"] for n in notes), "event_outside_form")
        bar = d["ppq"] * 4 * d["meter"][0] / d["meter"][1]
        require(d["length_ticks"] % bar == 0, "partial_bar")
    if k == "CompositionSpec":
        for name in ["tempo_map", "key_map"]:
            ticks = [t["tick"] for t in d[name]]
            require(ticks[0] == 0 and increasing(ticks) and ticks[-1] < d["length_ticks"], "map_order")
        end = 0
        for chord in d["harmony"]:
            require(chord["start_tick"] == end, "harmony_gap_overlap")
            end += chord["duration_ticks"]
        require(end == d["length_ticks"], "harmony_length")
    if k == "ScoreEvent":
        require(d["swing_applied"] == (d["swing_application_count"] == 1), "swing_state")
        if d["event_type"] == "note":
            require(d["midi_pitch"] is not None and d["start_tick"] is not None and d["duration_ticks"] is not None, "note_fields")
        else:
            require(d["midi_pitch"] is None, "unpitched_transposition")
        if d["event_type"] == "foley":
            require(d["scene_time_s"] is not None and d["resolved_time_s"] == d["scene_time_s"] and d["start_tick"] is None and not d["swing_applied"], "foley_scene_time")
    if k == "ArrangementPlan":
        require(d["register_min"] <= d["register_max"], "register_bounds")
        for t in d["transitions"]:
            require((t["from_pc"] + t["signed_semitones"]) % 12 == t["to_pc"], "signed_transition")
        for m in d["mappings"]:
            require(m["input_min"] < m["input_max"] and m["output_min"] <= m["output_max"], "mapping_bounds")
        require(unique([m["object_id"] for m in d["motif_owners"]]), "motif_owner_conflict")
    if k == "ClockMapping":
        require(d["valid_from_s"] < d["valid_until_s"], "clock_validity")
    if k == "RunManifest":
        groups = list(d["split"].values())
        require(unique([s for group in groups for s in group]), "split_leakage")
    if k == "EvaluationReport":
        m = d["metrics"]
        require(m["armed_hours"] <= m["elapsed_hours"], "exposure_range")
        if d["data_mode"] == "synthetic":
            require(d["release_status"] in ("PIPELINE_TESTED_ONLY", "NOT_READY"), "synthetic_performance_claim")
    if k in ("RunManifest", "EvaluationReport"):
        for result in d["results"]:
            require(result["status"] != "passed" or bool(result["evidence_paths"]), "passed_without_evidence")


def validate_bundle(records):
    """Referential conformance for public scene/music fixtures; no arrangement generation."""
    for record in records:
        validate(record)
    by_id = {r["id"]: r for r in records}
    if len(by_id) != len(records):
        raise ValueError("duplicate_record_id")
    def lookup(ident, kind):
        if ident not in by_id or by_id[ident]["kind"] != kind:
            raise ValueError("unknown_reference")
        return by_id[ident]
    for record in records:
        kind = record["kind"]
        if kind in ("ObjectState", "InteractionEvent"):
            scene = lookup(record["scene_id"], "SceneManifest")
            object_ids = {o["object_id"] for o in scene["objects"]}
            refs = [record["object_id"]] if kind == "ObjectState" else record["pair"]
            if not set(refs) <= object_ids:
                raise ValueError("unknown_object")
        if kind in ("CompositionSpec", "ArrangementPlan"):
            groove = lookup(record["groove_id"], "BrushGroove")
            if groove["catalog_version"] != record["groove_version"]:
                raise ValueError("groove_version")
        if kind == "ScoreEvent":
            plan = lookup(record["plan_id"], "ArrangementPlan")
            if record["instrument_id"] not in plan["palette_ids"]:
                raise ValueError("unknown_instrument")
    return records
