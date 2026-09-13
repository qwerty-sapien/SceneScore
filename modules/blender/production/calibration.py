"""Derive narrowly scoped Bullet restitution-zero calibration from actual controls.

This module imports no recipe functions and never runs Blender. Reports contain
recomputed measurements and exact artifact identities, including failed controls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from modules.blender.production.validation import (
    TOLERANCE_POLICY,
    angular_distance,
    gap,
    tolerance,
    validate_candidate,
    validate_motion_case,
)

VERSION = "bullet-inelastic-calibration-1"
POLICY = {
    "response_velocity_tolerance_m_s": 0.1,
    "trajectory_convergence_m": TOLERANCE_POLICY["stable_target_translation_m"],
    "rotation_convergence_rad": TOLERANCE_POLICY["stable_target_rotation_rad"],
    "contact_time_convergence_ticks": 1,
    "energy_relative_arithmetic_tolerance": 1e-5,
    "policy_source": "frozen restitution-case velocity tolerance and stable-state displacement/rotation caps",
}
REQUIRED = ("production.json", "physics_states.jsonl", "simulation.blend", "scene.blend", "bake.json",
            "bake-reopen.json", "replay_states.jsonl", "replay_validation.json", "evaluated_geometry.json")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _sub(a, b):
    return [x-y for x, y in zip(a, b)]


def _unit(v):
    length = math.sqrt(_dot(v, v))
    if length <= 1e-12:
        raise ValueError("coincident control centres")
    return [x/length for x in v]


def velocity(rows: list[dict], oid: str, interval: list[float]) -> list[float]:
    """Least-squares slope of independently evaluated positions, per SI axis."""
    selected = [r for r in rows if interval[0]-1e-10 <= r["time_s"] <= interval[1]+1e-10]
    if len(selected) < 3:
        raise ValueError("velocity window needs at least three samples")
    centre = sum(r["time_s"] for r in selected)/len(selected)
    denominator = sum((r["time_s"]-centre)**2 for r in selected)
    return [sum((r["time_s"]-centre)*r["objects"][oid]["position_m"][j] for r in selected)/denominator
            for j in range(3)]


def _contact(rows, specs, a, b):
    values = [gap(specs[a], r["objects"][a], specs[b], r["objects"][b]) for r in rows]
    cap = min(tolerance(specs[a], rows[0]["objects"][a]), tolerance(specs[b], rows[0]["objects"][b]))
    contact = next((i for i, value in enumerate(values) if value <= cap), None)
    worst = min(range(len(values)), key=values.__getitem__)
    return {"first_proximity_s": rows[contact]["time_s"] if contact is not None else None,
            "first_proximity_tick": contact, "minimum_signed_gap_m": values[worst],
            "minimum_time_s": rows[worst]["time_s"], "penetration_cap_m": cap}


def measure_drop(config: dict, rows: list[dict]) -> dict:
    specs = {s["object_id"]: s for s in config["objects"]}
    balls = [o for o, s in specs.items() if s["mode"] == "dynamic" and s["shape"] == "sphere"]
    if len(balls) != 1:
        raise ValueError("drop control must have exactly one dynamic sphere")
    oid = balls[0]
    floor = next(o for o in specs if o.endswith(":floor"))
    contact = _contact(rows, specs, oid, floor)
    time = contact["first_proximity_s"]
    if time is None or time < .1:
        raise ValueError("drop control has no distinct flight/contact interval")
    case = {"kind": "fixed_wall_restitution", "object_id": oid, "wall_object_id": floor,
            "normal_toward_wall": [0, 0, -1], "contact_time_s": time, "effective_restitution": 0,
            "incoming_window_s": [time-.08, time-.025], "outgoing_window_s": [time+.025, time+.08],
            "tolerance_m_s": POLICY["response_velocity_tolerance_m_s"]}
    result = validate_motion_case(case, specs, rows, config["gravity_m_s2"])
    after = [r for r in rows if r["time_s"] >= time+.025]
    floor_state = rows[0]["objects"][floor]
    # The calibration control is a horizontal fixed floor, not arbitrary terrain.
    if angular_distance(floor_state["quaternion_xyzw"], [0, 0, 0, 1]) > 1e-5:
        raise ValueError("drop control floor must be horizontal")
    roof = floor_state["position_m"][2]+specs[floor]["half_extents_m"][2]*floor_state["scale"][2]
    settled_height = roof+specs[oid]["radius_m"]
    excess = max(r["objects"][oid]["position_m"][2]-settled_height for r in after)
    valid = result["status"] == "PASSED" and excess <= contact["penetration_cap_m"]
    return {"kind": "inelastic_drop", "status": "PASSED" if valid else "FAILED", "object_id": oid,
            "contact": contact, "response": result, "max_postimpact_height_above_support_m": excess,
            "system_boundary": "one sphere with gravity, passive horizontal support, nominal restitution zero"}


def measure_transfer(config: dict, rows: list[dict]) -> dict:
    specs = {s["object_id"]: s for s in config["objects"]}
    bodies = sorted(o for o, s in specs.items() if s["mode"] == "dynamic" and s["shape"] == "sphere")
    if len(bodies) != 2:
        raise ValueError("transfer control needs exactly two dynamic spheres")
    a, b = bodies
    direction = _unit(_sub(rows[0]["objects"][b]["position_m"], rows[0]["objects"][a]["position_m"]))
    if abs(_dot(config["gravity_m_s2"], direction)) > 1e-7:
        raise ValueError("transfer momentum axis must be perpendicular to gravity")
    floor = next(o for o in specs if o.endswith(":floor"))
    if any(specs[o].get("friction") != 0 or specs[o].get("linear_damping") != 0 for o in [a, b, floor]):
        raise ValueError("horizontal system requires frictionless support and no linear damping")
    contact = _contact(rows, specs, a, b)
    time = contact["first_proximity_s"]
    if time is None:
        raise ValueError("transfer control has no contact")
    windows = [[time-.08, time-.025], [time+.025, time+.08]]
    velocities = [[_dot(velocity(rows, o, window), direction) for o in bodies] for window in windows]
    incoming, outgoing = velocities
    masses = [specs[o]["mass_kg"] for o in bodies]
    if any(not math.isfinite(m) or m <= 0 for m in masses):
        raise ValueError("invalid masses")
    # A paddle or side-wall impulse inside these windows invalidates isolation.
    exclusions = []
    for row in rows:
        if windows[0][0] <= row["time_s"] <= windows[1][1]:
            for oid in bodies:
                for other in specs:
                    if other in (*bodies, floor):
                        continue
                    distance = gap(specs[oid], row["objects"][oid], specs[other], row["objects"][other])
                    cap = min(tolerance(specs[oid], row["objects"][oid]), tolerance(specs[other], row["objects"][other]))
                    cap += max(0, specs[oid].get("collision_margin_m", 0))+max(0, specs[other].get("collision_margin_m", 0))
                    if distance <= cap:
                        exclusions.append({"object_id": oid, "external_collider": other, "time_s": row["time_s"], "gap_m": distance})
    momentum_error = abs(_dot(masses, outgoing)-_dot(masses, incoming))
    before = sum(m*v*v/2 for m, v in zip(masses, incoming))
    after = sum(m*v*v/2 for m, v in zip(masses, outgoing))
    expected = _dot(masses, incoming)/sum(masses)
    velocity_residual = abs(outgoing[1]-outgoing[0])
    relative_incoming = incoming[0]-incoming[1]
    limit = POLICY["response_velocity_tolerance_m_s"]
    valid = (not exclusions and relative_incoming > 0 and velocity_residual <= limit
             and momentum_error <= sum(masses)*limit
             and after <= before+POLICY["energy_relative_arithmetic_tolerance"]*max(1, before))
    return {"kind": "inelastic_transfer", "status": "PASSED" if valid else "FAILED", "object_ids": bodies,
            "contact": contact, "measurement_windows_s": windows, "incoming_normal_m_s": incoming,
            "outgoing_normal_m_s": outgoing, "expected_common_velocity_m_s": expected,
            "zero_restitution_velocity_residual_m_s": velocity_residual,
            "velocity_tolerance_m_s": limit,
            "effective_restitution_measured": (outgoing[1]-outgoing[0])/relative_incoming if relative_incoming > 0 else None,
            "momentum_residual_kg_m_s": momentum_error, "kinetic_energy_before_j": before,
            "kinetic_energy_after_j": after, "external_contact_confounds": exclusions,
            "system_boundary": "two spheres on frictionless horizontal support, after paddle separation; horizontal momentum only"}


def compare_resolution(coarse: dict, fine: dict) -> dict:
    a, b = coarse["config"], fine["config"]
    ar, br = coarse["rows"], fine["rows"]
    same_model = (a["objects"] == b["objects"] and a["gravity_m_s2"] == b["gravity_m_s2"]
                  and a["physics_hz"] == b["physics_hz"] and a["duration_s"] == b["duration_s"])
    same_config = dict(a.get("config", {})), dict(b.get("config", {}))
    for conf in same_config:
        conf.pop("solver_substeps", None)
        conf.pop("solver_iterations", None)
    same_model &= same_config[0] == same_config[1]
    cs, fs = a["solver"], b["solver"]
    finer = (fs["substeps_per_frame"] >= cs["substeps_per_frame"]
             and fs["solver_iterations"] >= cs["solver_iterations"]
             and (fs["substeps_per_frame"] >= 2*cs["substeps_per_frame"]
                  or fs["solver_iterations"] >= 2*cs["solver_iterations"])
             and fs.get("use_split_impulse", False) == cs.get("use_split_impulse", False))
    if not same_model or not finer or len(ar) != len(br):
        return {"status": "FAILED", "reason": "matched physical model and doubled solver resolution required at fixed sampling rate"}
    worst_position = (0., None, None)
    rotation = 0.
    for ra, rb in zip(ar, br):
        if ra["tick"] != rb["tick"] or ra["time_s"] != rb["time_s"]:
            return {"status": "FAILED", "reason": "sample clocks differ"}
        for oid, state in ra["objects"].items():
            distance = math.dist(state["position_m"], rb["objects"][oid]["position_m"])
            if distance > worst_position[0]:
                worst_position = distance, ra["time_s"], oid
            rotation = max(rotation, angular_distance(state["quaternion_xyzw"], rb["objects"][oid]["quaternion_xyzw"]))
    ac, bc = coarse["measurements"]["contact"], fine["measurements"]["contact"]
    contact_shift = abs(ac["first_proximity_s"]-bc["first_proximity_s"])
    cap = POLICY["trajectory_convergence_m"]
    status = (worst_position[0] <= cap and rotation <= POLICY["rotation_convergence_rad"]
              and contact_shift <= POLICY["contact_time_convergence_ticks"]/a["physics_hz"]+1e-10)
    return {"status": "PASSED" if status else "FAILED", "coarse_solver": cs, "fine_solver": fs,
            "physics_hz_unchanged": a["physics_hz"], "maximum_position_difference_m": worst_position[0],
            "position_difference_time_s": worst_position[1], "position_difference_object": worst_position[2],
            "position_tolerance_m": cap, "maximum_rotation_difference_rad": rotation,
            "first_contact_shift_s": contact_shift, "coarse_penetration_m": max(0, -ac["minimum_signed_gap_m"]),
            "fine_penetration_m": max(0, -bc["minimum_signed_gap_m"])}


def load_control(path: Path, kind: str) -> dict:
    config = json.loads((path/"production.json").read_text())
    rows = [json.loads(line) for line in (path/"physics_states.jsonl").read_text().splitlines() if line.strip()]
    issues = []
    if any(s.get("restitution") != 0 for s in config["objects"]):
        issues.append("native material outside explicit restitution-zero calibration scope")
    for name in REQUIRED:
        if not (path/name).is_file():
            issues.append("missing artifact "+name)
    checked = validate_candidate(path)
    numerical = ["asset_integrity", "geometric_contact", "physical_motion", "fresh_process_replay"]
    if any(checked["gates"][g]["status"] != "PASSED" for g in numerical):
        issues.append("required independent numerical control gate did not pass")
    measured = measure_drop(config, rows) if kind == "drop" else measure_transfer(config, rows)
    if measured["status"] != "PASSED":
        issues.append("measured inelastic response failed")
    return {"path": path, "config": config, "rows": rows, "status": "FAILED" if issues else "PASSED",
            "issues": issues, "measurements": measured, "gates": {g: checked["gates"][g] for g in numerical}}


def derive_calibration(drop: Path, drop_fine: Path, transfer: Path, transfer_fine: Path,
                       output_directory: Path | None = None) -> dict:
    inputs = [("drop_base", drop, "drop"), ("drop_fine", drop_fine, "drop"),
              ("transfer_base", transfer, "transfer"), ("transfer_fine", transfer_fine, "transfer")]
    output_directory = (output_directory or Path.cwd()).resolve()
    loaded, public, artifacts = {}, [], {}
    for label, path, kind in inputs:
        path = Path(path).resolve()
        try:
            control = load_control(path, kind)
            loaded[label] = control
            public.append({"id": label, "candidate": str(path), "status": control["status"],
                           "issues": control["issues"], "measurements": control["measurements"], "gates": control["gates"]})
            for name in REQUIRED:
                if (path/name).is_file():
                    artifacts[os.path.relpath(path/name, output_directory)] = digest(path/name)
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            public.append({"id": label, "candidate": str(path), "status": "FAILED", "issues": [str(exc)]})
    comparisons = {}
    for kind in ("drop", "transfer"):
        if kind+"_base" in loaded and kind+"_fine" in loaded:
            comparisons[kind] = compare_resolution(loaded[kind+"_base"], loaded[kind+"_fine"])
        else:
            comparisons[kind] = {"status": "FAILED", "reason": "control unavailable"}
    passed = all(c["status"] == "PASSED" for c in public) and all(c["status"] == "PASSED" for c in comparisons.values())
    base = loaded.get("drop_base")
    return {"version": VERSION, "status": "PASSED" if passed else "FAILED", "source_mode": "blender_controls",
            "scope": {"engine": "Blender Bullet", "native_material_restitution": 0,
                      "certifies": "tested drop and frictionless supported transfer at declared solver settings",
                      "does_not_certify": ["native elastic materials", "arbitrary body shapes/masses/velocities", "visual or audio review", "analytic mechanics backend"]},
            "solver": base["config"]["solver"] if base else None,
            "physics_hz": base["config"]["physics_hz"] if base else None,
            "policy": POLICY, "controls": public,
            "convergence": {"status": "PASSED" if all(c["status"] == "PASSED" for c in comparisons.values()) else "FAILED", "comparisons": comparisons},
            "artifacts": artifacts, "implementation": {"calibration_sha256": digest(Path(__file__)),
                "validator_sha256": digest(Path(__file__).with_name("validation.py"))},
            "limitations": ["Input transforms came from actual independently reopened Blender assets; model claims remain restricted to these controls.",
                            "A passing input filename or advertised PASSED value is not accepted as measured material response.",
                            "Convergence measures solver changes at fixed output sampling; sampling convergence remains separate."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drop", required=True, type=Path)
    parser.add_argument("--drop-fine", required=True, type=Path)
    parser.add_argument("--transfer", required=True, type=Path)
    parser.add_argument("--transfer-fine", required=True, type=Path)
    parser.add_argument("--out", type=Path, help="write exact JSON; default stdout without writing candidate files")
    args = parser.parse_args()
    result = derive_calibration(args.drop, args.drop_fine, args.transfer, args.transfer_fine,
                                args.out.parent if args.out else Path.cwd())
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
        print(json.dumps({"status": result["status"], "path": str(args.out), "sha256": digest(args.out)}))
    else:
        print(rendered, end="")
    raise SystemExit(0 if result["status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
