#!/usr/bin/env python3
"""Lint an authoring intent. This is NOT a motion, physics or acceptance validator."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

KINDS = frozenset({"collision", "bounce", "near_miss", "graze", "acceleration", "deceleration", "merge"})
BACKENDS = frozenset({"fixed-obb-sphere-mechanics-1", "native_bullet", "prescribed_mechanism", "other_explicit"})


def number(value: Any) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def validate_plan(plan: Any) -> list[str]:
    """Return all discoverable intent errors, never physical correctness claims."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    if plan.get("schema_version") != "scene-intent-1":
        errors.append("schema_version must be scene-intent-1 (not canonical SceneScore 0.1)")
    if plan.get("status") != "DESIGN_INTENT_NOT_MEASURED":
        errors.append("status must explicitly identify unmeasured design intent")
    duration = plan.get("duration_s")
    if not number(duration) or not 0 < duration <= 30:
        errors.append("duration_s must be finite and in (0, 30]")
        duration = 0
    policy = plan.get("salience_policy", {})
    if not isinstance(policy, dict):
        errors.append("salience_policy must be an object")
        policy = {}
    gap = policy.get("minimum_gap_s")
    duty = policy.get("maximum_duty_cycle")
    max_beats = policy.get("maximum_beats")
    if not number(gap) or gap < 0:
        errors.append("minimum_gap_s must be finite and nonnegative")
        gap = 0
    if not number(duty) or not 0 < duty <= 1:
        errors.append("maximum_duty_cycle must be in (0, 1]")
        duty = 1
    if type(max_beats) is not int or max_beats < 2:
        errors.append("maximum_beats must be an integer >= 2")
        max_beats = 2
    if policy.get("maximum_simultaneous_salient_beats") != 1 or isinstance(policy.get("maximum_simultaneous_salient_beats"), bool):
        errors.append("maximum_simultaneous_salient_beats must be 1")
    if policy.get("support_contact_policy") != "retain_raw_do_not_count_as_salient":
        errors.append("retain continuous support contacts in raw evidence without counting them as salient beats")
    objects = plan.get("objects")
    if not isinstance(objects, list) or not objects:
        return errors + ["objects must be a nonempty array"]
    ids: set[str] = set()
    for obj in objects:
        if not isinstance(obj, dict):
            errors.append("each object must be an object")
            continue
        oid = obj.get("id")
        if not isinstance(oid, str) or not oid or oid in ids:
            errors.append("object IDs must be unique nonempty strings")
            continue
        ids.add(oid)
        if type(obj.get("scored")) is not bool:
            errors.append(f"{oid}: scored must be boolean")
        if obj.get("role") == "silent_support" and obj.get("scored") is True:
            errors.append(f"{oid}: silent supports cannot own musical voices")
        if obj.get("motion") not in ("dynamic", "fixed", "prescribed"):
            errors.append(f"{oid}: motion must be dynamic, fixed or prescribed")
    backend = plan.get("physics_backend")
    if not isinstance(backend, str) or backend not in BACKENDS:
        errors.append("physics_backend must be explicit")
    if backend == "fixed-obb-sphere-mechanics-1":
        moving = [o for o in objects if isinstance(o, dict) and o.get("motion") != "fixed"]
        if len(moving) != 1 or moving[0].get("shape") != "sphere" or moving[0].get("motion") != "dynamic":
            errors.append("fixed-obb backend requires exactly one moving dynamic sphere")
        if any(isinstance(o, dict) and o.get("motion") == "fixed" and o.get("collision_enabled", True) and o.get("shape") != "obb" for o in objects):
            errors.append("fixed-obb backend requires fixed OBB colliders")
    beats = plan.get("beats")
    if not isinstance(beats, list):
        return errors + ["beats must be an array"]
    if not 2 <= len(beats) <= max_beats:
        errors.append(f"require 2..{max_beats} salient beats; one rebound is one beat")
    beat_ids: set[str] = set()
    kinds: set[str] = set()
    intervals: list[tuple[float, float, str]] = []
    for beat in beats:
        if not isinstance(beat, dict):
            errors.append("each beat must be an object")
            continue
        bid = beat.get("id")
        if not isinstance(bid, str) or not bid or bid in beat_ids:
            errors.append("beat IDs must be unique nonempty strings")
            continue
        beat_ids.add(bid)
        kind = beat.get("primary_kind")
        if not isinstance(kind, str) or kind not in KINDS:
            errors.append(f"{bid}: one valid primary_kind required")
            kind = None
        else:
            kinds.add(kind)
        actors = beat.get("object_ids")
        if not isinstance(actors, list) or not actors or any(not isinstance(o, str) or o not in ids for o in actors):
            errors.append(f"{bid}: valid object_ids required")
        elif len(set(actors)) != len(actors):
            errors.append(f"{bid}: object_ids must not repeat")
        elif kind in {"collision", "bounce", "near_miss", "graze", "merge"} and len(actors) < 2:
            errors.append(f"{bid}: interaction needs at least two objects")
        window = beat.get("target_window_s")
        if not isinstance(window, list) or len(window) != 2 or not all(number(v) for v in window):
            errors.append(f"{bid}: target_window_s must have two finite numbers")
        elif not 0 <= window[0] < window[1] <= duration:
            errors.append(f"{bid}: target window must be ordered and inside duration")
        else:
            intervals.append((float(window[0]), float(window[1]), bid))
        for field in ("physical_cause", "measurement_required"):
            if not isinstance(beat.get(field), str) or not beat[field].strip():
                errors.append(f"{bid}: {field} must be explicit")
        if kind == "merge" and backend != "other_explicit":
            errors.append(f"{bid}: merge requires a separate explicit adhesion/deformation model")
        if kind == "near_miss" and beat.get("requires_positive_surface_gap") is not True:
            errors.append(f"{bid}: near miss needs a positive surface-gap certificate")
    if len(kinds) < 2:
        errors.append("require at least two distinct primary event kinds")
    if not kinds.intersection({"collision", "bounce", "near_miss", "graze", "merge"}):
        errors.append("require at least one interaction, not only changes in speed")
    intervals.sort()
    for previous, current in zip(intervals, intervals[1:]):
        if current[0] - previous[1] < gap - 1e-9:
            errors.append(f"{previous[2]} -> {current[2]} violates separation/non-overlap policy")
    if duration and sum(end-start for start, end, _ in intervals)/duration > duty + 1e-9:
        errors.append("salient-event duty cycle exceeds the declared policy")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    try:
        errors = validate_plan(json.loads(args.plan.read_text()))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}))
        return 2
    print(json.dumps({"status": "PLAN_INVALID" if errors else "PLAN_VALID_NOT_PHYSICS_VALIDATED", "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
