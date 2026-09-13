"""Recompute narrowly scoped mechanics/driven calibration from actual Blender files.

Never imports a recipe, runs Blender, or trusts advertised control pass flags.
Every report is bound to one candidate's bytes. Analytic proof requires that
candidate's own doubled-resolution comparison plus isolated e=1 and e=.55 drops.
Driven proof establishes prescribed-transform playback only, never dynamics.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path

from modules.blender.production.calibration import REQUIRED, digest, velocity
from modules.blender.production.validation import (
    TOLERANCE_POLICY, angular_distance, gap, tolerance, validate_candidate, validate_motion_case,
)

VERSION = "scoped-backend-calibration-1"
ANALYTIC = "fixed-obb-sphere-mechanics-1"
DRIVEN = "prescribed-mechanism-1"
NUMERICAL_GATES = ("asset_integrity", "geometric_contact", "physical_motion", "fresh_process_replay")
POLICY = {
    "position_convergence_m": TOLERANCE_POLICY["stable_target_translation_m"],
    "rotation_convergence_rad": TOLERANCE_POLICY["stable_target_rotation_rad"],
    "contact_time_convergence_ticks": 1,
    "response_velocity_tolerance_m_s": .1,
    "control_position_tolerance_m": TOLERANCE_POLICY["replay_position_m"],
    "control_rotation_tolerance_rad": TOLERANCE_POLICY["replay_rotation_rad"],
    "policy_source": "frozen geometry, stable-state, replay and restitution-case tolerances",
}


def _specs(config):
    raw = config["objects"]
    return raw if isinstance(raw, dict) else {s["object_id"]: s for s in raw}


def _profile(config):
    return {k: v for k, v in config.get("mechanics", {}).items() if k != "states_sha256"}


def _binding(path, analytic=False):
    return {name: digest(path/name) for name in
            ("production.json", "physics_states.jsonl", "mechanics_states.json") if analytic or name != "mechanics_states.json"}


def _load(path, backend):
    path = Path(path).resolve()
    config = json.loads((path/"production.json").read_text())
    rows = [json.loads(s) for s in (path/"physics_states.jsonl").read_text().splitlines() if s.strip()]
    if backend == DRIVEN and (path/"mechanics_states.json").exists():
        raise ValueError("mechanics state file prevents a prescribed-only proof")
    names = (*REQUIRED, "mechanics_states.json") if backend == ANALYTIC else REQUIRED
    for name in names:
        if not (path/name).is_file():
            raise ValueError("missing actual artifact "+name)
    # This deliberately does not consume a previously installed calibration.
    checked = validate_candidate(path, check_calibration=False)
    failures = [g for g in NUMERICAL_GATES if checked["gates"][g]["status"] != "PASSED"]
    scope = verify_analytic_scope(config, rows, json.loads((path/"mechanics_states.json").read_text())) if backend == ANALYTIC else verify_driven_scope(config, rows)
    if backend == ANALYTIC and config["mechanics"]["states_sha256"] != digest(path/"mechanics_states.json"):
        failures.append("mechanics source-state hash differs")
    return {"path": path, "config": config, "rows": rows, "files": names,
            "scope": scope, "issues": failures, "status": "FAILED" if failures else "PASSED",
            "gates": {g: checked["gates"][g] for g in NUMERICAL_GATES}}


def verify_analytic_scope(config, rows, tracks):
    """Check actual fixed supports and replay against independent model tracks."""
    specs = _specs(config)
    dynamic = [s for s in specs.values() if s["mode"] == "dynamic"]
    if (config.get("motion_mode") != ANALYTIC or config.get("mechanics", {}).get("model_version") != ANALYTIC
            or len(dynamic) != 1 or dynamic[0]["shape"] != "sphere"
            or dynamic[0].get("motion_backend") != ANALYTIC or dynamic[0].get("blender_kinematic_replay") is not True):
        raise ValueError("analytic scope requires exactly one model sphere in kinematic Blender replay")
    actor = dynamic[0]
    oid = actor["object_id"]
    obstacles = {o for o in specs if o != oid}
    if (actor.get("mass_kg") != 1 or config["gravity_m_s2"] != [0, 0, -9.81]
            or any(specs[o]["mode"] != "passive" or specs[o]["shape"] != "box" for o in obstacles)):
        raise ValueError("unit-mass sphere, fixed OBBs and declared model gravity required")
    substeps = config["mechanics"].get("substeps")
    if not isinstance(substeps, int) or not 1 <= substeps <= 256:
        raise ValueError("independent mechanics substeps missing or invalid")
    if config.get("config", {}).get("parameters", {}).get("analytic_substeps", 32) != substeps:
        raise ValueError("mechanics substeps differ from captured generation parameters")
    if (not config.get("code_hashes", {}).get("modules/blender/production/analytic.py")
            or actor.get("rolling_resistance") != config["mechanics"].get("rolling_resistance")):
        raise ValueError("model source identity or matching rolling resistance missing")
    if set(tracks) != {oid} or set(tracks[oid]["obstacle_ids"]) != obstacles:
        raise ValueError("model track omits or invents a consequential collider")
    samples = tracks[oid]["samples"]
    if len(samples) != len(rows):
        raise ValueError("model/evaluated sample counts differ")
    position_error = rotation_error = support_position = support_rotation = 0.
    for row, model in zip(rows, samples):
        if row["tick"] != model["tick"] or abs(row["time_s"]-model["time_s"]) > 1e-10:
            raise ValueError("model and evaluated clocks differ")
        state = row["objects"][oid]
        position_error = max(position_error, math.dist(state["position_m"], model["position_m"]))
        rotation_error = max(rotation_error, angular_distance(state["quaternion_xyzw"], model["quaternion_xyzw"]))
        for other in obstacles:
            a, b = row["objects"][other], rows[0]["objects"][other]
            support_position = max(support_position, math.dist(a["position_m"], b["position_m"]))
            support_rotation = max(support_rotation, angular_distance(a["quaternion_xyzw"], b["quaternion_xyzw"]))
    if (max(position_error, support_position) > POLICY["control_position_tolerance_m"]
            or max(rotation_error, support_rotation) > POLICY["control_rotation_tolerance_rad"]):
        raise ValueError("model replay or fixed-obstacle transform mismatch")
    return {"actor": oid, "model_position_error_m": position_error, "model_rotation_error_rad": rotation_error,
            "fixed_support_position_drift_m": support_position, "fixed_support_rotation_drift_rad": support_rotation}


def verify_driven_scope(config, rows):
    specs = _specs(config)
    if (config.get("mechanics") or any(s["mode"] not in {"driven", "passive"} for s in specs.values())
            or not any(s["mode"] == "driven" for s in specs.values())):
        raise ValueError("prescribed proof requires driven/passive objects only; no dynamic or analytic actors")
    if not config.get("code_hashes", {}).get("modules/blender/production/scenes.py"):
        raise ValueError("mechanism generation source identity missing")
    worst = 0.
    rotation = 0.
    for oid, spec in specs.items():
        if spec["mode"] == "passive":
            first = rows[0]["objects"][oid]
            for row in rows:
                current = row["objects"][oid]
                worst = max(worst, math.dist(first["position_m"], current["position_m"]))
                rotation = max(rotation, angular_distance(first["quaternion_xyzw"], current["quaternion_xyzw"]))
    if worst > POLICY["control_position_tolerance_m"] or rotation > POLICY["control_rotation_tolerance_rad"]:
        raise ValueError("declared passive mechanism support moves")
    return {"dynamic_actor_count": 0, "passive_position_drift_m": worst, "passive_rotation_drift_rad": rotation}


def measure_bounce(config, rows, expected_restitution):
    """Isolated known drop: infer response from evaluated positions, never track v."""
    specs = _specs(config)
    balls = [o for o in specs if specs[o]["mode"] == "dynamic"]
    if len(balls) != 1:
        raise ValueError("isolated bounce needs one dynamic sphere")
    oid = balls[0]
    floor = next(o for o in specs if o.endswith(":floor"))
    ball, slab = specs[oid], specs[floor]
    first = rows[0]["objects"]
    if angular_distance(first[floor]["quaternion_xyzw"], [0, 0, 0, 1]) > 1e-5:
        raise ValueError("calibration floor must be horizontal")
    nominal = ball["restitution"]*slab["restitution"]
    if abs(nominal-expected_restitution) > 1e-10 or ball["friction"] != 0:
        raise ValueError("isolated control restitution/friction differs from frozen test")
    roof = first[floor]["position_m"][2]+slab["half_extents_m"][2]*first[floor]["scale"][2]
    drop = first[oid]["position_m"][2]-roof-ball["radius_m"]
    if drop <= .1 or config["gravity_m_s2"] != [0, 0, -9.81]:
        raise ValueError("known positive drop and model gravity required")
    contact_time = math.sqrt(2*drop/9.81)
    before, after = [contact_time-.08, contact_time-.025], [contact_time+.025, contact_time+.08]
    response = validate_motion_case({"kind": "fixed_wall_restitution", "object_id": oid,
        "wall_object_id": floor, "normal_toward_wall": [0, 0, -1], "contact_time_s": contact_time,
        "effective_restitution": expected_restitution, "incoming_window_s": before,
        "outgoing_window_s": after, "tolerance_m_s": POLICY["response_velocity_tolerance_m_s"]}, specs, rows, config["gravity_m_s2"])
    flight_rows = [r for r in rows if .05 <= r["time_s"] <= before[1]]
    flight = validate_motion_case({"kind": "free_flight", "object_id": oid}, specs, flight_rows, config["gravity_m_s2"])
    residual = max(math.dist(r["objects"][oid]["position_m"],
        [first[oid]["position_m"][0], first[oid]["position_m"][1], first[oid]["position_m"][2]-.5*9.81*r["time_s"]**2]) for r in flight_rows)
    confounds = []
    for row in rows:
        if before[0] <= row["time_s"] <= after[1]:
            for other in specs:
                if other in {oid, floor}:
                    continue
                d = gap(ball, row["objects"][oid], specs[other], row["objects"][other])
                cap = min(tolerance(ball, row["objects"][oid]), tolerance(specs[other], row["objects"][other]))
                if d <= cap:
                    confounds.append({"object_id": other, "time_s": row["time_s"], "gap_m": d})
    centres = []
    for start, end in (before, after):
        times = [r["time_s"] for r in rows if start-1e-10 <= r["time_s"] <= end+1e-10]
        centres.append(sum(times)/len(times))
    v_in = -velocity(rows, oid, before)[2]+9.81*(contact_time-centres[0])
    v_out = velocity(rows, oid, after)[2]+9.81*(centres[1]-contact_time)
    before_energy, after_energy = .5*v_in**2, .5*v_out**2
    energy_expected = expected_restitution**2*before_energy
    # Propagation of the already frozen 0.1 m/s response cap into kinetic energy.
    ecap = abs(expected_restitution*v_in)*POLICY["response_velocity_tolerance_m_s"]+.5*POLICY["response_velocity_tolerance_m_s"]**2
    good = (response["status"] == flight["status"] == "PASSED" and not confounds
            and residual <= POLICY["control_position_tolerance_m"] and v_in > 0 and v_out > 0
            and abs(after_energy-energy_expected) <= ecap)
    return {"status": "PASSED" if good else "FAILED", "kind": "isolated_fixed_floor_bounce",
            "effective_restitution": expected_restitution, "ballistic_contact_time_s": contact_time,
            "contact_time_basis": "known zero-speed drop; independently checked preimpact positions",
            "measurement_windows_s": [before, after], "response": response, "gravity": flight,
            "max_closed_form_flight_residual_m": residual, "incoming_speed_m_s": v_in,
            "outgoing_speed_m_s": v_out, "kinetic_energy_at_impact_before_j": before_energy,
            "kinetic_energy_at_impact_after_j": after_energy, "expected_after_j": energy_expected,
            "energy_tolerance_j": ecap, "external_contact_confounds": confounds}


def compare_mechanics(base, fine):
    a, b = base["config"], fine["config"]
    ap, bp = _profile(a), _profile(b)
    steps, fine_steps = ap.pop("substeps", 0), bp.pop("substeps", 0)
    ac, bc = copy.deepcopy(a.get("config", {})), copy.deepcopy(b.get("config", {}))
    for conf in (ac, bc):
        conf.setdefault("parameters", {}).pop("analytic_substeps", None)
    model_key = "modules/blender/production/analytic.py"
    if (ap != bp or fine_steps != 2*steps or ac != bc or a["objects"] != b["objects"]
            or a["physics_hz"] != b["physics_hz"] or a["duration_s"] != b["duration_s"]
            or a["gravity_m_s2"] != b["gravity_m_s2"] or a["code_hashes"].get(model_key) != b["code_hashes"].get(model_key)
            or len(base["rows"]) != len(fine["rows"])):
        return {"status": "FAILED", "reason": "matched physical model with exactly doubled mechanics steps at fixed sampling required"}
    worst = rotation = 0.
    when = oid_worst = None
    contacts = []
    specs = _specs(a)
    actor = next(o for o in specs if specs[o]["mode"] == "dynamic")
    for control in (base, fine):
        proximity = {}
        for row in control["rows"]:
            for oid, spec in specs.items():
                if oid == actor:
                    continue
                d = gap(specs[actor], row["objects"][actor], spec, row["objects"][oid])
                cap = min(tolerance(specs[actor], row["objects"][actor]), tolerance(spec, row["objects"][oid]))
                if d <= cap:
                    proximity.setdefault(oid, row["time_s"])
        contacts.append(proximity)
    for ar, br in zip(base["rows"], fine["rows"]):
        if ar["tick"] != br["tick"] or ar["time_s"] != br["time_s"]:
            return {"status": "FAILED", "reason": "sample clocks differ"}
        for oid, state in ar["objects"].items():
            other = br["objects"][oid]
            delta = math.dist(state["position_m"], other["position_m"])
            if delta > worst:
                worst, when, oid_worst = delta, ar["time_s"], oid
            rotation = max(rotation, angular_distance(state["quaternion_xyzw"], other["quaternion_xyzw"]))
    same_contacts = set(contacts[0]) == set(contacts[1])
    shift = max([abs(contacts[0][o]-contacts[1][o]) for o in contacts[0] if o in contacts[1]], default=0.)
    good = (worst <= POLICY["position_convergence_m"] and rotation <= POLICY["rotation_convergence_rad"]
            and same_contacts and shift <= POLICY["contact_time_convergence_ticks"]/a["physics_hz"]+1e-10)
    return {"status": "PASSED" if good else "FAILED", "mechanics_substeps": [steps, fine_steps],
            "physics_hz_unchanged": a["physics_hz"], "maximum_position_difference_m": worst,
            "position_difference_time_s": when, "position_difference_object": oid_worst,
            "maximum_rotation_difference_rad": rotation, "first_proximity_shift_s": shift,
            "same_sampled_contact_set": same_contacts, "sampled_first_proximity_times_s": contacts,
            "position_tolerance_m": POLICY["position_convergence_m"],
            "contact_limitation": "sampled proximity only; between-tick impulses are measured in isolated bounce windows"}


def measure_driven_control(config, rows):
    specs = _specs(config)
    oid, rail = "control_driven:carriage", "control_driven:rail"
    if (config.get("recipe_id") != "control_driven" or config["duration_s"] != 4
            or oid not in specs or rail not in specs or specs[oid]["mode"] != "driven"
            or specs[oid].get("half_extents_m") != [.25, .25, .2]
            or specs[rail].get("half_extents_m") != [2, .4, .15]):
        raise ValueError("known four-second rail/carriage control geometry required")
    if any(s["mode"] == "driven" and o != oid for o, s in specs.items()):
        raise ValueError("isolated mechanism control permits exactly one driven carriage")
    worst = rotation = scale = rail_error = 0.
    for row in rows:
        t = row["time_s"]
        expected_x = -1 if t <= 1 else t-2 if t < 3 else 1
        state, support = row["objects"][oid], row["objects"][rail]
        worst = max(worst, math.dist(state["position_m"], [expected_x, 0, .5]))
        rotation = max(rotation, angular_distance(state["quaternion_xyzw"], [0, 0, 0, 1]))
        scale = max(scale, *(abs(x-1) for x in state["scale"]))
        rail_error = max(rail_error, math.dist(support["position_m"], [0, 0, .15]))
    measured = velocity(rows, oid, [1.1, 2.9])
    endpoints = [velocity(rows, oid, [.1, .9]), velocity(rows, oid, [3.1, 3.9])]
    velocity_error = math.dist(measured, [1, 0, 0])
    rest_error = max(math.sqrt(sum(v*v for v in item)) for item in endpoints)
    good = (max(worst, rail_error) <= POLICY["control_position_tolerance_m"]
            and rotation <= POLICY["control_rotation_tolerance_rad"] and scale <= TOLERANCE_POLICY["scale_drift"]
            and velocity_error <= POLICY["control_position_tolerance_m"]
            and rest_error <= POLICY["control_position_tolerance_m"])
    return {"status": "PASSED" if good else "FAILED", "kind": "known_affine_rail_carriage",
            "interval_s": [1, 3], "max_position_error_m": worst, "max_rotation_error_rad": rotation,
            "max_scale_error": scale, "rail_position_error_m": rail_error,
            "measured_active_velocity_m_s": measured, "stationary_window_velocities_m_s": endpoints,
            "scope": "prescribed coordinate, orientation, scale and endpoint hold; no dynamic response claimed"}


def _derive(paths, backend, output_directory):
    loaded, controls, artifacts = {}, [], {}
    for label, path in paths.items():
        try:
            item = _load(path, backend)
            loaded[label] = item
            public_gates = copy.deepcopy(item["gates"])
            for gate in public_gates.values():
                if "evidence" in gate:
                    gate["evidence"] = os.path.relpath(gate["evidence"], output_directory)
            controls.append({"id": label, "status": item["status"], "issues": item["issues"],
                             "gates": public_gates, "scope": item["scope"]})
            for name in item["files"]:
                artifacts[os.path.relpath(item["path"]/name, output_directory)] = digest(item["path"]/name)
        except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
            controls.append({"id": label, "status": "FAILED", "issues": [str(exc)]})
    candidate = loaded.get("candidate")
    config = candidate["config"] if candidate else {}
    report = {"version": VERSION, "backend": backend, "status": "FAILED", "source_mode": "blender_controls",
              "controls": controls, "artifacts": artifacts, "policy": POLICY,
              "candidate_inputs": _binding(candidate["path"], backend == ANALYTIC) if candidate else {},
              "physics_hz": config.get("physics_hz"), "mechanics": _profile(config) if backend == ANALYTIC and candidate else None,
              "model_source_sha256": config.get("code_hashes", {}).get("modules/blender/production/analytic.py") if backend == ANALYTIC else None,
              "mechanism_source_sha256": config.get("code_hashes", {}).get("modules/blender/production/scenes.py") if backend == DRIVEN else None,
              "implementation": {"helper_sha256": digest(Path(__file__)), "validator_sha256": digest(Path(__file__).with_name("validation.py"))},
              "scope": {"candidate_bound": True, "certifies": "only numerical mechanics/replay for the exact candidate inputs",
                        "excludes": ["native Bullet material calibration", "other candidate hashes", "human approval", "motion perception or visual quality"]}}
    return loaded, report


def derive_analytic_calibration(elastic, elastic_fine, dissipative, dissipative_fine, candidate, candidate_fine, output_directory=None):
    paths = dict(elastic=elastic, elastic_fine=elastic_fine, dissipative=dissipative,
                 dissipative_fine=dissipative_fine, candidate=candidate, candidate_fine=candidate_fine)
    loaded, report = _derive(paths, ANALYTIC, Path(output_directory or Path.cwd()).resolve())
    for label, expected in (("elastic", 1.), ("elastic_fine", 1.), ("dissipative", .55), ("dissipative_fine", .55)):
        entry = next(c for c in report["controls"] if c["id"] == label)
        if label in loaded:
            try:
                measured = measure_bounce(loaded[label]["config"], loaded[label]["rows"], expected)
                entry["measurements"] = measured
                if measured["status"] != "PASSED":
                    entry["status"] = "FAILED"
            except (ValueError, KeyError, IndexError, StopIteration) as exc:
                entry["status"] = "FAILED"
                entry["issues"].append(str(exc))
    comparisons = {label: compare_mechanics(loaded[label], loaded[label+"_fine"])
                   if label in loaded and label+"_fine" in loaded else {"status": "FAILED", "reason": "actual comparison missing"}
                   for label in ("elastic", "dissipative", "candidate")}
    # Different model bytes, integration profiles or Blender builds cannot be pooled.
    signatures = {(json.dumps({k: v for k, v in _profile(c["config"]).items() if k != "substeps"}, sort_keys=True),
                   c["config"]["physics_hz"], c["config"].get("blender_build_hash"),
                   c["config"]["code_hashes"].get("modules/blender/production/analytic.py")) for c in loaded.values()}
    steps = [loaded[k]["config"]["mechanics"]["substeps"] for k in ("elastic", "dissipative", "candidate") if k in loaded]
    compatible = len(loaded) == 6 and len(signatures) == 1 and len(set(steps)) == 1
    comparisons["suite_profile"] = {"status": "PASSED" if compatible else "FAILED", "reason": "matching model bytes/build/profile and base mechanics resolution required"}
    report["convergence"] = {"status": "PASSED" if all(c["status"] == "PASSED" for c in comparisons.values()) else "FAILED", "comparisons": comparisons}
    if all(c["status"] == "PASSED" for c in report["controls"]) and report["convergence"]["status"] == "PASSED":
        report["status"] = "PASSED"
    return report


def derive_driven_calibration(control, candidate, output_directory=None):
    loaded, report = _derive(dict(control=control, candidate=candidate), DRIVEN, Path(output_directory or Path.cwd()).resolve())
    entry = report["controls"][0]
    if "control" in loaded:
        try:
            measured = measure_driven_control(loaded["control"]["config"], loaded["control"]["rows"])
            entry["measurements"] = measured
            if measured["status"] != "PASSED":
                entry["status"] = "FAILED"
        except (ValueError, KeyError, IndexError) as exc:
            entry["status"] = "FAILED"
            entry["issues"].append(str(exc))
    compatible = False
    if len(loaded) == 2:
        a, b = (loaded[k]["config"] for k in ("control", "candidate"))
        compatible = (a["physics_hz"] == b["physics_hz"] and a.get("blender_build_hash") == b.get("blender_build_hash")
                      and a["code_hashes"].get("modules/blender/production/scenes.py") == b["code_hashes"].get("modules/blender/production/scenes.py"))
    report["convergence"] = {"status": "PASSED" if compatible else "FAILED",
        "kind": "prescribed_transform_control", "native_solver_resolution": "NOT_APPLICABLE_NO_DYNAMIC_ACTORS",
        "reason": "known transform accuracy and fresh replay at the same clock, build and mechanism source"}
    if compatible and all(c["status"] == "PASSED" for c in report["controls"]):
        report["status"] = "PASSED"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="backend", required=True)
    analytic = sub.add_parser("analytic")
    for flag in ("elastic", "elastic-fine", "dissipative", "dissipative-fine", "candidate", "candidate-fine"):
        analytic.add_argument("--"+flag, required=True, type=Path)
    driven = sub.add_parser("driven")
    for flag in ("control", "candidate"):
        driven.add_argument("--"+flag, required=True, type=Path)
    for command in (analytic, driven):
        command.add_argument("--out", type=Path)
    args = vars(parser.parse_args())
    backend, out = args.pop("backend"), args.pop("out")
    result = (derive_analytic_calibration if backend == "analytic" else derive_driven_calibration)(**args, output_directory=out.parent if out else Path.cwd())
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n"
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered)
        print(json.dumps({"status": result["status"], "path": str(out), "sha256": digest(out)}))
    else:
        print(rendered, end="")
    raise SystemExit(0 if result["status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
