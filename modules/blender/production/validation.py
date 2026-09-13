"""Independent sampled-physics checks; never imports production recipes or Blender.

``gap`` is exact sphere distance or a normalized 15-axis OBB separation gap.
For disjoint boxes it is a separating-axis lower bound, not Euclidean distance.
Negative values are minimum separating translation depths, including containment.
Candidate success concerns numerical evidence only, never perception or approval.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any

VERSION = "blender-independent-validation-1"
TOLERANCE_POLICY = {
    "version": "production-tolerances-1",
    "penetration_absolute_cap_m": 0.005,
    "penetration_dimension_fraction": 0.01,
    "arithmetic_floor_m": 1e-5,
    "scale_drift": 1e-5,
    "quaternion_norm_error": 1e-4,
    "rest_speed_m_s": 0.02,
    "rest_angular_speed_rad_s": 0.05,
    "rest_window_s": 0.25,
    "free_flight_acceleration_error_m_s2": 0.5,
    "stable_target_translation_m": 0.005,
    "stable_target_rotation_rad": 0.01,
    "replay_position_m": 1e-5,
    "replay_rotation_rad": 1e-4,
    "calibration_status": "ANALYTICAL_ONLY_SOLVER_CALIBRATION_PENDING",
}
Vec = list[float] | tuple[float, ...]


def _dot(a: Vec, b: Vec) -> float:
    return sum(x*y for x, y in zip(a, b))


def _sub(a: Vec, b: Vec) -> list[float]:
    return [x-y for x, y in zip(a, b)]


def _norm(a: Vec) -> float:
    return math.sqrt(_dot(a, a))


def _cross(a: Vec, b: Vec) -> list[float]:
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def _unit(a: Vec) -> list[float]:
    length = _norm(a)
    if length < 1e-12:
        raise ValueError("zero direction/quaternion")
    return [x/length for x in a]


def _axes(state: dict) -> list[list[float]]:
    x, y, z, w = _unit(state["quaternion_xyzw"])
    # Columns of the local-to-world rotation matrix.
    return [[1-2*(y*y+z*z), 2*(x*y+z*w), 2*(x*z-y*w)],
            [2*(x*y-z*w), 1-2*(x*x+z*z), 2*(y*z+x*w)],
            [2*(x*z+y*w), 2*(y*z-x*w), 1-2*(x*x+y*y)]]


def _half(spec: dict, state: dict) -> list[float]:
    return [h*abs(s) for h, s in zip(spec["half_extents_m"], state.get("scale", [1, 1, 1]))]


def _radius(spec: dict, state: dict) -> float:
    scale = state.get("scale", [1, 1, 1])
    spread = max(scale)-min(scale)
    # Matrix decomposition introduces sub-micro float differences even when the
    # underlying rigid sphere is uniform. Honour the frozen scale tolerance and
    # separately bound geometric distortion in metres for very large spheres.
    if spread > TOLERANCE_POLICY["scale_drift"] or spec["radius_m"]*spread > TOLERANCE_POLICY["arithmetic_floor_m"]:
        raise ValueError("nonuniform sphere scale requires an ellipsoid collider")
    return spec["radius_m"]*(sum(abs(s) for s in scale)/3)


def _dimension(spec: dict, state: dict) -> float:
    return 2*(_radius(spec, state) if spec["shape"] == "sphere" else min(_half(spec, state)))


def tolerance(spec: dict, state: dict) -> float:
    """Frozen cap. Shapes too small for arithmetic resolution are rejected."""
    cap = min(0.005, 0.01*_dimension(spec, state))
    if cap < 1e-5:
        raise ValueError("collision dimension too small for frozen arithmetic floor")
    return cap


def _box_axes(a_state: dict, b_state: dict) -> list[list[float]]:
    aa, bb = _axes(a_state), _axes(b_state)
    candidates = aa+bb+[_cross(a, b) for a in aa for b in bb]
    return [_unit(x) for x in candidates if _norm(x) > 1e-10]


def _projection(spec: dict, state: dict, axis: Vec) -> float:
    if spec["shape"] == "sphere":
        return _radius(spec, state)
    return sum(h*abs(_dot(a, axis)) for h, a in zip(_half(spec, state), _axes(state)))


def gap(a_spec: dict, a_state: dict, b_spec: dict, b_state: dict) -> float:
    """Signed metres; shape dimensions are local metres before state scale."""
    ap, bp = a_state["position_m"], b_state["position_m"]
    if a_spec["shape"] == b_spec["shape"] == "sphere":
        return _norm(_sub(bp, ap))-_radius(a_spec, a_state)-_radius(b_spec, b_state)
    if a_spec["shape"] == "box" and b_spec["shape"] == "sphere":
        return gap(b_spec, b_state, a_spec, a_state)
    if a_spec["shape"] == "sphere" and b_spec["shape"] == "box":
        local = [_dot(_sub(ap, bp), axis) for axis in _axes(b_state)]
        d = [abs(x)-h for x, h in zip(local, _half(b_spec, b_state))]
        signed_point_distance = _norm([max(0, x) for x in d])+min(max(d), 0)
        return signed_point_distance-_radius(a_spec, a_state)
    if a_spec["shape"] != "box" or b_spec["shape"] != "box":
        raise ValueError("only evaluated spheres and boxes are supported")
    delta = _sub(bp, ap)
    return max(abs(_dot(delta, axis))-_projection(a_spec, a_state, axis)
               -_projection(b_spec, b_state, axis) for axis in _box_axes(a_state, b_state))


def angular_distance(a: Vec, b: Vec) -> float:
    return 2*math.acos(min(1.0, abs(_dot(_unit(a), _unit(b)))))


def _interpolate(a: dict, b: dict, t: float) -> dict:
    qa, qb = _unit(a["quaternion_xyzw"]), _unit(b["quaternion_xyzw"])
    if _dot(qa, qb) < 0:
        qb = [-x for x in qb]
    return {"position_m": [x+t*(y-x) for x, y in zip(a["position_m"], b["position_m"])],
            "quaternion_xyzw": _unit([x+t*(y-x) for x, y in zip(qa, qb)]),
            "scale": [x+t*(y-x) for x, y in zip(a.get("scale", [1]*3), b.get("scale", [1]*3))]}


def swept_gap(a_spec: dict, a0: dict, a1: dict, b_spec: dict, b0: dict, b1: dict) -> dict:
    """Check the declared linear interpolation, never claim true continuous motion.

    Constant-orientation sphere/sphere and sphere/box minima are continuous on
    that interpolation. Changing OBB orientation uses bounded interior samples.
    """
    rotation = max(angular_distance(a0["quaternion_xyzw"], a1["quaternion_xyzw"]),
                   angular_distance(b0["quaternion_xyzw"], b1["quaternion_xyzw"]))
    def at(t):
        return gap(a_spec, _interpolate(a0, a1, t), b_spec, _interpolate(b0, b1, t))
    if a_spec["shape"] == b_spec["shape"] == "sphere":
        p = _sub(a0["position_m"], b0["position_m"])
        v = _sub(_sub(a1["position_m"], b1["position_m"]), p)
        u = max(0.0, min(1.0, -_dot(p, v)/_dot(v, v))) if _dot(v, v) else 0.0
        return {"gap_m": at(u), "fraction": u, "method": "linear_relative_sphere_sweep", "samples": None}
    if "sphere" in (a_spec["shape"], b_spec["shape"]) and rotation < 1e-9:
        # Distance to a convex box is convex along a line outside the box.
        # Minimise unsigned distance, then evaluate the signed gap at the argmin.
        lo, hi = 0.0, 1.0
        for _ in range(48):
            left, right = (2*lo+hi)/3, (lo+2*hi)/3
            if at(left) < at(right):
                hi = right
            else:
                lo = left
        candidates = [(at(u), u) for u in [0.0, (lo+hi)/2, 1.0]]
        value, u = min(candidates)
        return {"gap_m": value, "fraction": u, "method": "linear_sphere_OBB_distance_minimum", "samples": None}
    travel = _norm(_sub(a1["position_m"], a0["position_m"]))+_norm(_sub(b1["position_m"], b0["position_m"]))
    dimension = min(_dimension(a_spec, a0), _dimension(b_spec, b0))
    count = min(128, max(4, math.ceil(travel/(dimension/4)), math.ceil(rotation/0.025)))
    value, u = min((at(i/count), i/count) for i in range(count+1))
    return {"gap_m": value, "fraction": u, "method": "linear_translation_nlerp_rotation_interior_samples",
            "samples": count+1, "coverage_limit": "not a continuous solid guarantee"}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_vector(value: Any, size: int) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == size and all(
        isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in value)


def _issue(code: str, gate: str, **details) -> dict:
    return {"code": code, "gate": gate, **details}


def _state_speed(rows: list[dict], oid: str, index: int) -> tuple[float, float]:
    left, right = max(0, index-1), min(len(rows)-1, index+1)
    dt = rows[right]["time_s"]-rows[left]["time_s"]
    a, b = rows[left]["objects"][oid], rows[right]["objects"][oid]
    if dt <= 0:
        return math.inf, math.inf
    return (_norm(_sub(b["position_m"], a["position_m"]))/dt,
            angular_distance(a["quaternion_xyzw"], b["quaternion_xyzw"])/dt)


def _supports(a_spec: dict, a: dict, b_spec: dict, b: dict, tol: float) -> bool:
    """Geometric downward support edge; force/friction capacity is not certified."""
    if b["position_m"][2] >= a["position_m"][2]-1e-7 or abs(gap(a_spec, a, b_spec, b)) > tol:
        return False
    if a_spec["shape"] == "sphere" and b_spec["shape"] == "sphere":
        return _unit(_sub(a["position_m"], b["position_m"]))[2] > 0.25
    if a_spec["shape"] == "sphere" and b_spec["shape"] == "box":
        axes = _axes(b)
        local = [_dot(_sub(a["position_m"], b["position_m"]), axis) for axis in axes]
        half = _half(b_spec, b)
        normal_local = [x-max(-h, min(h, x)) for x, h in zip(local, half)]
        normal = [sum(normal_local[j]*axes[j][i] for j in range(3)) for i in range(3)]
        return _norm(normal) > 1e-9 and _unit(normal)[2] > 0.25
    if a_spec["shape"] == "box" and b_spec["shape"] == "sphere":
        return _supports(b_spec, b, a_spec, a, tol) if a["position_m"][2] < b["position_m"][2] else (
            abs(a["position_m"][2]-_projection(a_spec, a, [0, 0, 1])
                -(b["position_m"][2]+_radius(b_spec, b))) <= tol)
    delta = _sub(a["position_m"], b["position_m"])
    axes = _box_axes(a, b)
    axis = max(axes, key=lambda v: abs(_dot(delta, v))-_projection(a_spec, a, v)-_projection(b_spec, b, v))
    return abs(axis[2]) > 0.25


def supported_objects(specs: dict[str, dict], states: dict[str, dict]) -> set[str]:
    supported = {oid for oid, spec in specs.items() if spec["mode"] in {"passive", "driven"}}
    for _ in range(len(specs)):
        previous = len(supported)
        for oid, spec in specs.items():
            if oid in supported:
                continue
            for other in supported.copy():
                tol = min(tolerance(spec, states[oid]), tolerance(specs[other], states[other]))
                if _supports(spec, states[oid], specs[other], states[other], tol):
                    supported.add(oid)
                    break
        if len(supported) == previous:
            break
    return supported


def assess_reference_case(case: dict) -> dict:
    """Analytical fixture oracle. These outputs certify only exact-model numbers."""
    kind, tol = case["kind"], case.get("analytic_tolerance", 1e-8)
    metrics = {}
    if kind == "constant_acceleration":
        initial = case["initial"]
        residuals = [abs(actual-(p+v*row["t_s"]+acc*row["t_s"]**2/2))
                     for row in case["samples"] for actual, p, v, acc in
                     zip(row["p_m"], initial["p_m"], initial["v_m_s"], initial["a_m_s2"])]
        metrics["max_position_residual_m"] = max(residuals)
        accepted = max(residuals) <= tol
    elif kind == "isolated_1d_collision":
        masses, incoming, outgoing = case["masses_kg"], case["incoming_m_s"], case["outgoing_m_s"]
        dp = _dot(masses, outgoing)-_dot(masses, incoming)
        before = sum(m*v*v/2 for m, v in zip(masses, incoming))
        after = sum(m*v*v/2 for m, v in zip(masses, outgoing))
        restitution_error = abs(outgoing[1]-outgoing[0]-case["effective_restitution"]*(incoming[0]-incoming[1]))
        metrics = {"momentum_residual_kg_m_s": dp, "energy_before_j": before,
                   "energy_after_j": after, "restitution_residual_m_s": restitution_error}
        accepted = abs(dp) <= tol and after <= before+tol and restitution_error <= tol
    elif kind == "fixed_wall_collision":
        residual = abs(case["outgoing_normal_m_s"]+case["effective_restitution"]*case["incoming_normal_m_s"])
        metrics["restitution_residual_m_s"] = residual
        accepted = residual <= tol
    elif kind == "box_nonpenetration":
        converted = []
        for box in case["boxes"]:
            radians = math.radians(box["rotation_z_deg"])
            converted.append(({"shape": "box", "half_extents_m": box["half_extents_m"]},
                              {"position_m": box["centre_m"], "scale": [1, 1, 1],
                               "quaternion_xyzw": [0, 0, math.sin(radians/2), math.cos(radians/2)]}))
        value = gap(*converted[0], *converted[1])
        metrics["signed_gap_m"] = value
        accepted = value >= -tol
    elif kind == "rigid_scale":
        first = case["world_scale_samples"][0]
        drift = max(abs(x-y) for row in case["world_scale_samples"] for x, y in zip(first, row))
        metrics["max_scale_drift"] = drift
        accepted = drift <= tol
    elif kind == "undisturbed_target":
        delta = max(_norm(_sub(p, case["initial_position_m"])) for p in case["positions_m"])
        metrics["max_displacement_m"] = delta
        accepted = delta <= tol
    else:
        raise ValueError("unknown analytical case: "+kind)
    return {"id": case.get("id"), "accepted": accepted, "metrics": metrics,
            "tolerance": tol, "scope": "synthetic_analytical_reference_only"}


def validate_motion_case(case: dict, specs: dict[str, dict], rows: list[dict], gravity: Vec) -> dict:
    """Optional explicit case annotations select windows; samples remain evidence."""
    subset = [row for row in rows if case.get("start_s", 0) <= row["time_s"] <= case.get("end_s", math.inf)]
    kind, oid = case["kind"], case.get("object_id")
    result = {"kind": kind, "id": case.get("id"), "status": "NOT_RUN", "metrics": {}, "issues": []}
    if len(subset) < 3:
        result["reason"] = "at least three evaluated samples required"
        return result
    if kind == "free_flight":
        expected = case.get("expected_acceleration_m_s2", gravity)
        errors = []
        for i in range(1, len(subset)-1):
            a, b, c = subset[i-1:i+2]
            dt1, dt2 = b["time_s"]-a["time_s"], c["time_s"]-b["time_s"]
            v1 = [x/dt1 for x in _sub(b["objects"][oid]["position_m"], a["objects"][oid]["position_m"])]
            v2 = [x/dt2 for x in _sub(c["objects"][oid]["position_m"], b["objects"][oid]["position_m"])]
            acc = [2*x/(dt1+dt2) for x in _sub(v2, v1)]
            errors.append((_norm(_sub(acc, expected)), b["time_s"]))
        error, time = max(errors)
        tol = TOLERANCE_POLICY["free_flight_acceleration_error_m_s2"]
        result["metrics"] = {"max_acceleration_error_m_s2": error, "time_s": time, "tolerance_m_s2": tol,
                             "expected_acceleration_m_s2": expected}
        result["status"] = "PASSED" if error <= tol else "FAILED"
    elif kind == "fixed_wall_restitution":
        normal = _unit(case["normal_toward_wall"])
        contact_time = case["contact_time_s"]
        wall = case["wall_object_id"]
        if specs[wall]["mode"] != "passive":
            result["reason"] = "fixed-wall system requires a passive wall"
            return result
        velocities, raw_velocities, contact_free, sustained_contact = [], [], [], []
        for window_key in ("incoming_window_s", "outgoing_window_s"):
            start, end = case[window_key]
            samples = [r for r in rows if start-1e-10 <= r["time_s"] <= end+1e-10]
            if len(samples) < 3:
                result["reason"] = "velocity window requires at least three evaluated samples"
                return result
            times = [r["time_s"] for r in samples]
            centre = sum(times)/len(times)
            projected = [_dot(r["objects"][oid]["position_m"], normal) for r in samples]
            mean_position = sum(projected)/len(projected)
            denominator = sum((t-centre)**2 for t in times)
            measured_velocity = sum((t-centre)*(p-mean_position) for t, p in zip(times, projected))/denominator
            # Extrapolate each contact-free regression to one contact time under
            # declared gravity; do not silently assume the wall shares gravity.
            clear = all(gap(specs[oid], r["objects"][oid], specs[wall], r["objects"][wall]) >
                        min(tolerance(specs[oid], r["objects"][oid]), tolerance(specs[wall], r["objects"][wall]))
                        for r in samples)
            impact_velocity = measured_velocity+_dot(gravity, normal)*(contact_time-centre) if clear else None
            velocities.append(impact_velocity)
            raw_velocities.append(measured_velocity)
            contact_free.append(clear)
            sustained_contact.append(all(abs(gap(specs[oid], r["objects"][oid], specs[wall], r["objects"][wall])) <=
                min(tolerance(specs[oid], r["objects"][oid]), tolerance(specs[wall], r["objects"][wall])) for r in samples))
        incoming, outgoing = velocities
        threshold = case.get("tolerance_m_s", .1)
        supported_inelastic = (case["effective_restitution"] == 0 and incoming is not None and incoming > 0
                               and sustained_contact[1] and abs(raw_velocities[1]) <= threshold)
        if supported_inelastic:
            # A perfectly inelastic impact may remain in contact. Gravity is
            # balanced by support afterward, so use its observed normal velocity
            # without extrapolating gravity through a sustained contact window.
            outgoing = raw_velocities[1]
        residual = abs(outgoing+case["effective_restitution"]*incoming) if incoming is not None and outgoing is not None else None
        result["metrics"] = {"incoming_normal_m_s": incoming, "outgoing_normal_m_s": outgoing,
                             "raw_window_normal_velocities_m_s": raw_velocities,
                             "contact_free_windows": contact_free,
                             "effective_restitution_measured": -outgoing/incoming if incoming is not None and incoming > 0 and outgoing is not None else None,
                             "effective_restitution_expected": case["effective_restitution"],
                             "normal_velocity_residual_m_s": residual, "tolerance_m_s": threshold,
                             "contact_time_s": contact_time,
                             "postimpact_response": "supported_inelastic_contact" if supported_inelastic else "free_flight" if contact_free[1] else "unresolved_contact",
                             "unavailable_reason": None if all(contact_free) or supported_inelastic else "no valid contact-free pre/post impact velocity window",
                             "system_boundary": "dynamic body versus passive wall; gravity correction only in contact-free windows"}
        result["status"] = "PASSED" if incoming is not None and incoming > 0 and residual is not None and residual <= threshold else "FAILED"
    elif kind == "stable_target":
        targets = case.get("object_ids", [oid])
        position_error, rotation_error = 0.0, 0.0
        for target in targets:
            initial = subset[0]["objects"][target]
            position_error = max(position_error, max(_norm(_sub(r["objects"][target]["position_m"],
                                                                  initial["position_m"])) for r in subset))
            rotation_error = max(rotation_error, max(angular_distance(r["objects"][target]["quaternion_xyzw"],
                                                                        initial["quaternion_xyzw"]) for r in subset))
        result["metrics"] = {"max_position_error_m": position_error, "max_rotation_error_rad": rotation_error}
        result["status"] = "PASSED" if position_error <= .005 and rotation_error <= .01 else "FAILED"
    elif kind == "supported_rest":
        bad = [r["time_s"] for r in subset if oid not in supported_objects(specs, r["objects"])]
        speeds = [_state_speed(subset, oid, i) for i in range(len(subset))]
        result["metrics"] = {"unsupported_samples": len(bad), "first_unsupported_s": bad[0] if bad else None,
                             "max_speed_m_s": max(x[0] for x in speeds),
                             "max_angular_speed_rad_s": max(x[1] for x in speeds)}
        result["status"] = "PASSED" if not bad and max(x[0] for x in speeds) <= .02 and max(x[1] for x in speeds) <= .05 else "FAILED"
    elif kind == "release":
        time = case["release_time_s"]
        i = min(range(len(rows)), key=lambda j: abs(rows[j]["time_s"]-time))
        if not 1 <= i < len(rows)-1 or "expected_velocity_m_s" not in case:
            result["reason"] = "release requires neighbours and independently expected velocity"
            return result
        dt = rows[i+1]["time_s"]-rows[i]["time_s"]
        observed = [x/dt for x in _sub(rows[i+1]["objects"][oid]["position_m"], rows[i]["objects"][oid]["position_m"])]
        error = _norm(_sub(observed, case["expected_velocity_m_s"]))
        tol = case.get("tolerance_m_s", .1)
        result["metrics"] = {"outgoing_velocity_m_s": observed, "velocity_error_m_s": error, "tolerance_m_s": tol}
        result["status"] = "PASSED" if error <= tol else "FAILED"
    elif kind == "near_miss":
        a, b = case["object_ids"]
        value, time = min((gap(specs[a], r["objects"][a], specs[b], r["objects"][b]), r["time_s"]) for r in subset)
        tol = min(tolerance(specs[a], subset[0]["objects"][a]), tolerance(specs[b], subset[0]["objects"][b]))
        result["metrics"] = {"minimum_sampled_gap_m": value, "time_s": time, "uncertainty_m": tol}
        result["status"] = "PASSED" if value > tol else "FAILED"
    else:
        result["reason"] = "unknown or externally measured case kind"
    if result["status"] == "FAILED":
        result["issues"].append({"code": "case_"+kind, "object_id": oid, "object_ids": case.get("object_ids"),
                                 "interval_s": [subset[0]["time_s"], subset[-1]["time_s"]], **result["metrics"]})
    return result


def _read(path: Path) -> dict:
    return json.loads(path.read_text())


def validate_candidate(directory: str | Path, *, check_calibration: bool = True) -> dict:
    root = Path(directory).resolve()
    result = {"version": VERSION, "candidate": str(root), "status": "NOT_RUN", "gates": {}, "metrics": {},
              "issues": [], "tolerance_policy": TOLERANCE_POLICY.copy(), "limitations": [
                  "Sampled evaluated solids; no global continuous-time guarantee.",
                  "Copied metadata does not establish Blender provenance; fresh asset evidence is a separate gate.",
                  "No motion-perception, soundtrack audition or human approval is implied."]}
    gates, issues, metrics = result["gates"], result["issues"], result["metrics"]
    for name in ["asset_integrity", "geometric_contact", "physical_motion", "fresh_process_replay",
                 "solver_calibration", "rendered_temporal", "perceptual_story_appearance"]:
        gates[name] = {"status": "NOT_RUN"}
    try:
        config = _read(root/"production.json")
        rows = [_read_line(line) for line in (root/"physics_states.jsonl").read_text().splitlines() if line.strip()]
        raw_objects = config["objects"]
        specs = raw_objects if isinstance(raw_objects, dict) else {s["object_id"]: s for s in raw_objects}
        if not isinstance(raw_objects, dict) and len(specs) != len(raw_objects):
            raise ValueError("duplicate object IDs")
        if config["version"] != "blender-production-1" or not specs or len(rows) < 3:
            raise ValueError("unsupported production version or incomplete candidate")
        hz, duration = config["physics_hz"], config["duration_s"]
        if not isinstance(hz, int) or hz < 240 or hz % 30 or config["render_fps"] != 30 or duration <= 0:
            raise ValueError("production clock must be an integer >=240 Hz divisible by 30, with native 30 fps and positive duration")
        if abs(duration*hz-round(duration*hz)) > 1e-7 or len(rows) != round(duration*hz)+1:
            raise ValueError("states must cover the inclusive right endpoint at every physics tick")
        if not _finite_vector(config["gravity_m_s2"], 3):
            raise ValueError("invalid gravity")
        for oid, spec in specs.items():
            if spec["shape"] not in {"sphere", "box"} or spec["mode"] not in {"dynamic", "passive", "driven"}:
                raise ValueError("unsupported collider shape or mode: "+oid)
            dims = [spec["radius_m"]] if spec["shape"] == "sphere" else spec["half_extents_m"]
            if not _finite_vector(dims, 1 if spec["shape"] == "sphere" else 3) or min(dims) <= 0:
                raise ValueError("invalid collision dimensions: "+oid)
            if spec.get("collision_enabled") is False:
                issues.append(_issue("disabled_consequential_collider", "asset_integrity", object_id=oid))
        for i, row in enumerate(rows):
            if row["tick"] != i or abs(row["time_s"]-i/hz) > 1e-8 or set(row["objects"]) != set(specs):
                raise ValueError("nonuniform clock, missing collider or stale sample at row "+str(i))
            for oid, state in row["objects"].items():
                if not all(_finite_vector(state.get(k), n) for k, n in
                           [("position_m", 3), ("quaternion_xyzw", 4), ("scale", 3)]):
                    raise ValueError("invalid or incomplete world transform: "+oid)
                if min(state["scale"]) <= 0 or abs(_norm(state["quaternion_xyzw"])-1) > 1e-4:
                    raise ValueError("invalid world scale or quaternion: "+oid)
                tolerance(specs[oid], state)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        issues.append(_issue("invalid_candidate_data", "asset_integrity", reason=str(exc)))
        gates["asset_integrity"]["status"] = "FAILED"
        result["status"] = "FAILED"
        return result
    metrics["samples"] = len(rows)
    metrics["objects"] = len(specs)
    result["inputs"] = {"production.json": _hash(root/"production.json"),
                        "physics_states.jsonl": _hash(root/"physics_states.jsonl")}
    if (root/"production_events.json").is_file():
        result["inputs"]["production_events.json"] = _hash(root/"production_events.json")
    lineage = config.get("lineage", {})
    if lineage:
        if lineage.get("source_fingerprint") != config.get("source_fingerprint") or lineage.get("bake_source_fingerprint") != config.get("source_fingerprint"):
            issues.append(_issue("stale_bake_source", "asset_integrity"))
        if lineage.get("states_sha256") != result["inputs"]["physics_states.jsonl"]:
            issues.append(_issue("stale_state_digest", "asset_integrity"))
        artifacts = lineage.get("artifacts", {})
        for rel, expected in artifacts.items():
            path = (root/rel).resolve()
            if not path.is_relative_to(root) or not path.is_file() or _hash(path) != expected:
                issues.append(_issue("artifact_hash_mismatch", "asset_integrity", artifact=rel))
        if not artifacts or not any(p.endswith(".blend") for p in artifacts):
            gates["asset_integrity"]["reason"] = "source/cache blend artifact identities missing"
        else:
            gates["asset_integrity"]["status"] = "PASSED"
    else:
        gates["asset_integrity"]["reason"] = "lineage not supplied"
    _validate_geometry(config, specs, rows, gates, issues, metrics)
    _validate_motion(config, specs, rows, gates, issues, metrics)
    _validate_events(root, specs, rows, issues, metrics)
    _validate_replay(root, result, config, rows)
    calibration_path = root/"solver_calibration.json"
    if check_calibration and calibration_path.is_file():
        calibration = _read(calibration_path)
        gates["solver_calibration"] = {"status": "NOT_RUN", "evidence": str(calibration_path)}
        if calibration.get("status") == "FAILED":
            issues.append(_issue("solver_calibration_failed", "solver_calibration"))
        else:
            controls, convergence = calibration.get("controls", []), calibration.get("convergence", {})
            artifacts = calibration.get("artifacts", {})
            evidence_valid = bool(artifacts)
            for relative, expected in artifacts.items():
                evidence = (root/relative).resolve()
                if not evidence.is_file() or _hash(evidence) != expected:
                    issues.append(_issue("calibration_evidence_hash_mismatch", "solver_calibration", artifact=relative))
                    evidence_valid = False
            checks_valid = bool(controls) and all(c.get("status") == "PASSED" for c in controls)
            checks_valid &= isinstance(convergence, dict) and convergence.get("status") == "PASSED"
            settings_valid = _calibration_scope_matches(calibration, config, result["inputs"], root)
            if not settings_valid:
                issues.append(_issue("calibration_scope_mismatch", "solver_calibration"))
            if calibration.get("status") == "PASSED" and calibration.get("source_mode") == "blender_controls" and checks_valid and settings_valid and evidence_valid:
                gates["solver_calibration"]["status"] = "PASSED"
                result["tolerance_policy"]["calibration_status"] = "BLENDER_CONTROLS_REPORTED_WITH_HASHED_EVIDENCE"
            else:
                gates["solver_calibration"]["reason"] = "passing actual controls/convergence, matching backend/candidate scope and hashed artifacts required"
    for issue in issues:
        gates[issue["gate"]]["status"] = "FAILED"
    physical_names = ["asset_integrity", "geometric_contact", "physical_motion", "fresh_process_replay", "solver_calibration"]
    statuses = [gates[name]["status"] for name in physical_names]
    result["status"] = "FAILED" if "FAILED" in statuses else "PASSED" if all(s == "PASSED" for s in statuses) else "NOT_RUN"
    gates["physical_candidate"] = {"status": result["status"], "requires": physical_names}
    return result



def _calibration_scope_matches(report: dict, config: dict, inputs: dict, root: Path) -> bool:
    """Disjoint backends: a Bullet settings match never certifies mechanics.

    Alternate/driven proofs bind the exact candidate bytes and their model source.
    Helpers use check_calibration=False while deriving controls, so a previously
    installed report cannot certify itself through a validate/derive recursion.
    """
    objects = config["objects"]
    specs = list(objects.values()) if isinstance(objects, dict) else objects
    mechanics = config.get("mechanics")
    is_mechanics = bool(mechanics) or (root/"mechanics_states.json").is_file()
    has_dynamic = any(s["mode"] == "dynamic" for s in specs)
    backend = report.get("backend")
    if is_mechanics or not has_dynamic:
        expected = dict(inputs)
        expected.pop("production_events.json", None)  # Events retain their independent exact-byte gate.
        if is_mechanics:
            expected["mechanics_states.json"] = _hash(root/"mechanics_states.json") if (root/"mechanics_states.json").is_file() else None
        if report.get("candidate_inputs") != expected:
            return False
        if report.get("version") != "scoped-backend-calibration-1" or report.get("physics_hz") != config["physics_hz"]:
            return False
        if is_mechanics:
            profile = {k: v for k, v in (mechanics or {}).items() if k != "states_sha256"}
            dynamic = [s for s in specs if s["mode"] == "dynamic"]
            return (backend == "fixed-obb-sphere-mechanics-1" and config.get("motion_mode") == backend
                    and report.get("mechanics") == profile and profile.get("model_version") == backend
                    and len(dynamic) == 1 and dynamic[0].get("motion_backend") == backend
                    and dynamic[0]["shape"] == "sphere" and dynamic[0].get("blender_kinematic_replay") is True
                    and all(s["mode"] == "passive" and s["shape"] == "box" for s in specs if s is not dynamic[0])
                    and bool(report.get("model_source_sha256"))
                    and report["model_source_sha256"] == config.get("code_hashes", {}).get("modules/blender/production/analytic.py"))
        return (backend == "prescribed-mechanism-1" and any(s["mode"] == "driven" for s in specs)
                and report.get("mechanics") is None
                and report.get("mechanism_source_sha256") == config.get("code_hashes", {}).get("modules/blender/production/scenes.py")
                and bool(report.get("mechanism_source_sha256")))
    return (backend not in {"fixed-obb-sphere-mechanics-1", "prescribed-mechanism-1"}
            and "Bullet" in config.get("motion_mode", "")
            and report.get("version") == "bullet-inelastic-calibration-1"
            and report.get("scope", {}).get("native_material_restitution") == 0
            and all(s.get("restitution") == 0 for s in specs)
            and report.get("physics_hz") == config.get("physics_hz")
            and report.get("solver") == config.get("solver") and bool(config.get("solver")))

def _read_line(line: str) -> dict:
    return json.loads(line)


def _validate_geometry(config, specs, rows, gates, issues, metrics):
    pairs, excluded = [], []
    for a, b in itertools.combinations(specs, 2):
        sa, sb = specs[a], specs[b]
        if sa["mode"] == sb["mode"] == "passive":
            excluded.append({"pair": [a, b], "reason": "both passive structural colliders"})
        elif sa["mode"] != "dynamic" and sb["mode"] != "dynamic" and sa.get("collision_group") and sa.get("collision_group") == sb.get("collision_group"):
            excluded.append({"pair": [a, b], "reason": "declared joined nondynamic mechanism"})
        else:
            pairs.append((a, b))
    pair_metrics = []
    for a, b in pairs:
        sa, sb = specs[a], specs[b]
        minimum, when, min_tick = math.inf, None, None
        prior = None
        swept_worst = None
        for i, row in enumerate(rows):
            aa, bb = row["objects"][a], row["objects"][b]
            value = gap(sa, aa, sb, bb)
            if value < minimum:
                minimum, when, min_tick = value, row["time_s"], row["tick"]
            tol = min(tolerance(sa, aa), tolerance(sb, bb))
            if prior and value > tol and prior["gap_m"] > tol:
                pa, pb = prior["a"], prior["b"]
                travel = _norm(_sub(aa["position_m"], pa["position_m"]))+_norm(_sub(bb["position_m"], pb["position_m"]))
                rotation = angular_distance(aa["quaternion_xyzw"], pa["quaternion_xyzw"])+angular_distance(bb["quaternion_xyzw"], pb["quaternion_xyzw"])
                # A movement bound cheaply excludes most intervals; rotating long
                # boxes include swept bounding radii rather than only thickness.
                bound_a = _radius(sa, aa) if sa["shape"] == "sphere" else _norm(_half(sa, aa))
                bound_b = _radius(sb, bb) if sb["shape"] == "sphere" else _norm(_half(sb, bb))
                if travel+rotation*max(bound_a, bound_b) >= min(value, prior["gap_m"]):
                    swept = swept_gap(sa, pa, aa, sb, pb, bb)
                    if swept["gap_m"] < -tol and (swept_worst is None or swept["gap_m"] < swept_worst["gap_m"]):
                        swept_worst = {**swept, "interval_s": [rows[i-1]["time_s"], row["time_s"]]}
            prior = {"a": aa, "b": bb, "gap_m": value}
        tol = min(tolerance(sa, rows[0]["objects"][a]), tolerance(sb, rows[0]["objects"][b]))
        pair_metrics.append({"pair": [a, b], "minimum_sampled_gap_m": minimum, "time_s": when, "tick": min_tick,
                             "penetration_tolerance_m": tol, "swept_interpolation": swept_worst})
        if minimum < -tol:
            issues.append(_issue("solid_penetration", "geometric_contact", pair=[a, b], time_s=when,
                                 tick=min_tick, actual_m=minimum, tolerance_m=tol,
                                 evidence=f"physics_states.jsonl:{min_tick+1}"))
        if swept_worst:
            issues.append(_issue("between_sample_crossing", "geometric_contact", pair=[a, b], tolerance_m=tol,
                                 **swept_worst, uncertainty="linear/nlerp path assumption; rerun denser actual samples"))
    metrics["pairs"] = pair_metrics
    metrics["excluded_pairs"] = excluded
    gates["geometric_contact"]["status"] = "PASSED"


def _validate_motion(config, specs, rows, gates, issues, metrics):
    drift, rest = {}, {}
    held_motion = {}
    for oid, spec in specs.items():
        initial = rows[0]["objects"][oid]
        value, tick = max((max(abs(x-y) for x, y in zip(r["objects"][oid]["scale"], initial["scale"])), r["tick"]) for r in rows)
        drift[oid] = value
        if value > 1e-5:
            issues.append(_issue("rigid_scale_drift", "physical_motion", object_id=oid, tick=tick,
                                 time_s=rows[tick]["time_s"], actual=value, tolerance=1e-5))
        if spec["mode"] != "dynamic":
            continue
        # A 30 Hz track duplicated onto a 240 Hz clock contains repeated short
        # holds between active jumps. Initial support and a settled ending are
        # long holds, not evidence of low native cadence. Require a pattern.
        runs=[]
        start=0
        for i in range(1,len(rows)+1):
            if i<len(rows) and rows[i]['objects'][oid]==rows[start]['objects'][oid]:
                continue
            length=i-start
            if 2<=length<=config['physics_hz']//30 and start>0 and i<len(rows):
                before=rows[start-1]['objects'][oid]['position_m']
                at=rows[start]['objects'][oid]['position_m']
                after=rows[i]['objects'][oid]['position_m']
                if min(_norm(_sub(at,before)),_norm(_sub(after,at)))*config['physics_hz']>.02:
                    runs.append({'tick':start,'samples':length,'time_s':rows[start]['time_s']})
            start=i
        patterns={n:sum(r['samples']==n for r in runs) for n in {r['samples'] for r in runs}}
        held_motion[oid]={'short_active_holds':runs,'counts_by_length':patterns}
        if any(count>=3 for count in patterns.values()):
            issues.append(_issue('duplicated_low_rate_motion','physical_motion',object_id=oid,
                                 evidence='physics_states.jsonl repeated active hold pattern',counts_by_length=patterns))
        window_count = max(3, round(.25*config["physics_hz"]))
        tail = rows[-window_count:]
        max_speed = max(_state_speed(tail, oid, i)[0] for i in range(len(tail)))
        max_rotation = max(_state_speed(tail, oid, i)[1] for i in range(len(tail)))
        supported = oid in supported_objects(specs, rows[-1]["objects"])
        rest[oid] = {"max_final_speed_m_s": max_speed, "max_final_angular_speed_rad_s": max_rotation,
                     "supported_at_end": supported, "window_s": [tail[0]["time_s"], tail[-1]["time_s"]]}
        if max_speed <= .02 and max_rotation <= .05 and not supported:
            issues.append(_issue("unsupported_rest", "physical_motion", object_id=oid,
                                 time_s=rows[-1]["time_s"], evidence="physics_states.jsonl final rest window"))
        if config.get("require_settled_end", False) and (max_speed > .02 or max_rotation > .05):
            issues.append(_issue("unsettled_end", "physical_motion", object_id=oid, **rest[oid]))
        # Search the complete sequence for frozen unsupported intervals. The
        # coarse scan is only a resting-state detector, not collision coverage.
        stalled_start = None
        unsupported_interval = None
        for i in range(0, len(rows), config["physics_hz"]//30):
            speed, rotation = _state_speed(rows, oid, i)
            if speed <= .02 and rotation <= .05 and oid not in supported_objects(specs, rows[i]["objects"]):
                if stalled_start is None:
                    stalled_start = rows[i]["time_s"]
                if rows[i]["time_s"]-stalled_start >= .25:
                    unsupported_interval = [stalled_start, rows[i]["time_s"]]
                    break
            else:
                stalled_start = None
        if unsupported_interval and not any(i["code"] == "unsupported_rest" and i.get("object_id") == oid for i in issues):
            issues.append(_issue("unsupported_rest", "physical_motion", object_id=oid,
                                 interval_s=unsupported_interval, scan_hz=30,
                                 evidence="physics_states.jsonl stationary samples"))
    cases = []
    for case in config.get("validation_cases", []):
        try:
            cases.append(validate_motion_case(case, specs, rows, config["gravity_m_s2"]))
        except (KeyError, ValueError, TypeError, IndexError, ZeroDivisionError) as exc:
            issues.append(_issue("invalid_motion_case", "asset_integrity", case=case, reason=str(exc)))
    for case in cases:
        for issue in case["issues"]:
            details = {k: v for k, v in issue.items() if k != "code"}
            issues.append(_issue(issue["code"], "physical_motion", **details))
    metrics["maximum_scale_drift"] = drift
    metrics['native_motion_holds']=held_motion
    metrics["rest"] = rest
    metrics["cases"] = cases
    # Shape and support checks alone cannot establish actual gravity, release or
    # material response. Each production recipe supplies applicable case windows.
    gates["physical_motion"]["status"] = "PASSED" if cases and all(c["status"] == "PASSED" for c in cases) else "NOT_RUN"
    if not cases:
        gates["physical_motion"]["reason"] = "case-specific force/causality checks not supplied"


def _validate_events(root, specs, rows, issues, metrics):
    """Optional production event supplement. Check geometry independently."""
    path = root/"production_events.json"
    if not path.exists():
        metrics["event_validation"] = {"status": "NOT_RUN", "reason": "production_events.json absent"}
        return
    events = _read(path)
    events = events.get("events", []) if isinstance(events, dict) else events
    checked, measurements = 0, []
    for event in events:
        kind = event.get("type", event.get("event_type"))
        if kind not in {"contact", "impact", "near_miss", "foley"}:
            continue
        pair = event.get("object_ids", event.get("pair"))
        if not pair or len(pair) != 2 or any(oid not in specs for oid in pair):
            issues.append(_issue("invalid_event_pair", "asset_integrity", event_id=event.get("id")))
            continue
        a, b = pair
        time = event.get("time_s", event.get("onset_s"))
        if not isinstance(time, (int, float)) or not 0 <= time <= rows[-1]["time_s"]:
            issues.append(_issue("invalid_event_time", "asset_integrity", event_id=event.get("id")))
            continue
        index = min(range(len(rows)), key=lambda i: abs(rows[i]["time_s"]-time))
        neighbours = rows[max(0, index-1):min(len(rows), index+2)]
        measured = min(gap(specs[a], r["objects"][a], specs[b], r["objects"][b]) for r in neighbours)
        tol = min(tolerance(specs[a], rows[index]["objects"][a]), tolerance(specs[b], rows[index]["objects"][b]))
        margins = [specs[oid].get("collision_margin_m", 0) for oid in pair]
        if any(not isinstance(m, (int, float)) or not math.isfinite(m) or m < 0 for m in margins):
            issues.append(_issue("invalid_collision_margin", "asset_integrity", event_id=event.get("id"), pair=pair))
            continue
        uncertainty = tol+sum(margins)
        invalid = measured <= uncertainty if kind == "near_miss" else measured > uncertainty
        if invalid:
            issues.append(_issue("spurious_"+kind, "physical_motion", event_id=event.get("id"), pair=pair,
                                 time_s=time, actual_gap_m=measured, tolerance_m=tol,
                                 geometric_uncertainty_m=uncertainty, collision_margins_m=margins))
        measurements.append({"event_id": event.get("id"), "type": kind, "pair": pair, "time_s": time,
                             "actual_signed_gap_m": measured, "geometric_uncertainty_m": uncertainty,
                             "collision_margins_m": margins, "status": "FAILED" if invalid else "PASSED"})
        checked += 1
    metrics["event_validation"] = {"status": "CHECKED", "events_checked": checked,
                                   "measurements": measurements,
                                   "scope": "geometry within declared margin uncertainty; no measured impulse or audio verification"}


def _validate_replay(root, result, config, rows):
    path = root/"replay_validation.json"
    if not path.exists():
        result["gates"]["fresh_process_replay"]["reason"] = "fresh Blender process report absent"
        return
    try:
        report = _read(path)
        required = {"status": "PASSED", "mode": "fresh_blender_process",
                    "source_states_sha256": result["inputs"]["physics_states.jsonl"]}
        valid = all(report.get(k) == v for k, v in required.items())
        valid &= report.get("samples_checked", 0) == len(rows)
        for key, cap in [("max_position_error_m", 1e-5), ("max_rotation_error_rad", 1e-4), ("max_scale_error", 1e-5)]:
            value = report.get(key)
            valid &= isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= cap
        # Recompute from the actual fresh-reopened state file. A report whose
        # status/metrics were copied from an earlier run cannot pass on its own.
        replay_path = root/"replay_states.jsonl"
        if not replay_path.is_file() or report.get("replay_states_sha256") != _hash(replay_path):
            valid = False
        if not (root/"scene.blend").is_file() or report.get("source_hash") != _hash(root/"scene.blend"):
            valid = False
        maxima = {"max_position_error_m": 0., "max_rotation_error_rad": 0., "max_scale_error": 0.}
        if valid:
            actual_rows = [_read_line(line) for line in replay_path.read_text().splitlines() if line.strip()]
            valid &= len(actual_rows) == len(rows)
            for actual, wanted in zip(actual_rows, rows):
                valid &= actual["tick"] == wanted["tick"] and abs(actual["time_s"]-wanted["time_s"]) <= 1e-8
                valid &= set(actual["objects"]) == set(wanted["objects"])
                for oid, wanted_state in wanted["objects"].items():
                    actual_state = actual["objects"][oid]
                    if not all(_finite_vector(actual_state.get(k), n) for k, n in
                               [("position_m", 3), ("quaternion_xyzw", 4), ("scale", 3)]):
                        raise ValueError("invalid replay transform: "+oid)
                    maxima["max_position_error_m"] = max(maxima["max_position_error_m"],
                        _norm(_sub(wanted_state["position_m"], actual_state["position_m"])))
                    maxima["max_rotation_error_rad"] = max(maxima["max_rotation_error_rad"],
                        angular_distance(wanted_state["quaternion_xyzw"], actual_state["quaternion_xyzw"]))
                    maxima["max_scale_error"] = max(maxima["max_scale_error"],
                        _norm(_sub(wanted_state["scale"], actual_state["scale"])))
            for key, cap in [("max_position_error_m", 1e-5), ("max_rotation_error_rad", 1e-4), ("max_scale_error", 1e-5)]:
                valid &= maxima[key] <= cap
                valid &= abs(maxima[key]-report[key]) <= 1e-7
        if not valid:
            result["issues"].append(_issue("replay_evidence_mismatch", "fresh_process_replay", evidence=str(path),
                                          independently_computed=maxima))
        else:
            result["gates"]["fresh_process_replay"] = {"status": "PASSED", "evidence": str(path),
                "sha256": _hash(path), "independently_computed": maxima,
                "replay_states_sha256": _hash(replay_path), "scene_sha256": _hash(root/"scene.blend")}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        result["issues"].append(_issue("replay_evidence_mismatch", "fresh_process_replay", evidence=str(path), reason=str(exc)))


def check_rendered_cadence(frame_pts_s: list[float], expected_fps: int, expected_frames: int,
                           decoded_hashes: list[str] | None = None,
                           expected_motion_frames: set[int] | None = None) -> dict:
    """PTS plus decoded-pixel identities; duplicate detection only where motion is expected."""
    issues = []
    if len(frame_pts_s) != expected_frames or any(not math.isfinite(x) for x in frame_pts_s):
        issues.append("frame_count_or_nonfinite_pts")
    if frame_pts_s and abs(frame_pts_s[0]) > 1e-4:
        issues.append("nonzero_video_origin")
    if any(abs((b-a)-1/expected_fps) > 1e-4 for a, b in zip(frame_pts_s, frame_pts_s[1:])):
        issues.append("non_native_presentation_cadence")
    duplicates = []
    if decoded_hashes is not None:
        if len(decoded_hashes) != len(frame_pts_s):
            issues.append("decoded_hash_count")
        duplicates = [i for i in range(1, len(decoded_hashes)) if decoded_hashes[i] == decoded_hashes[i-1]
                      and expected_motion_frames is not None and i in expected_motion_frames]
        if duplicates:
            issues.append("duplicate_frames_during_expected_motion")
    return {"status": "FAILED" if issues else "PASSED" if decoded_hashes is not None and expected_motion_frames is not None else "NOT_RUN",
            "issues": issues, "duplicate_motion_frames": duplicates,
            "scope": "decoded timing and explicit motion windows; stillness may validly duplicate frames"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = validate_candidate(args.directory)
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(1 if result["status"] == "FAILED" else 0)


if __name__ == "__main__":
    main()
