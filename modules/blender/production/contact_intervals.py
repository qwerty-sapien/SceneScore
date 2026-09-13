"""Independent between-tick contact certificates for fixed sphere/OBB mechanics.

Only evaluated world transforms are fitted. No analytic implementation or model
contact/velocity flags are consumed. Narrow face impacts need contact-free flight
on both sides; edges, simultaneous contacts and sustained support remain unknown.
A numerical certificate is not eligible for integration until the entire current
candidate independently passes its physical gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from modules.blender.production.validation import (
    TOLERANCE_POLICY, angular_distance, gap, tolerance, validate_candidate,
)

VERSION = "evaluated-ballistic-contact-intervals-1"
BACKEND = "fixed-obb-sphere-mechanics-1"
POLICY = {
    "fit_position_residual_m": .0001,
    "contact_continuity_m": .001,
    "normal_response_residual_m_s": .1,
    "minimum_velocity_discontinuity_m_s": .1,
    "minimum_fit_samples": 3,
    "preferred_fit_samples": 5,
    "maximum_fit_offset_ticks": 6,
    "root_subdivisions": 64,
    "release_support_gap_m": TOLERANCE_POLICY["arithmetic_floor_m"],
    "release_velocity_continuity_m_s": .1,
    "release_minimum_support_samples": 5,
    "scope": "one unit-mass sphere, static OBBs, contact-free constant-gravity windows and unambiguous face impact",
}


def _hash(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024*1024), b""):
            value.update(part)
    return value.hexdigest()


def _json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _sub(a, b):
    return [x-y for x, y in zip(a, b)]


def _norm(v):
    return math.sqrt(_dot(v, v))


def _axes(q):
    x, y, z, w = (v/_norm(q) for v in q)
    return [[1-2*(y*y+z*z), 2*(x*y+z*w), 2*(x*z-y*w)],
            [2*(x*y-z*w), 1-2*(x*x+z*z), 2*(y*z+x*w)],
            [2*(x*z+y*w), 2*(y*z-x*w), 1-2*(x*x+y*y)]]


def _pose(position, reference):
    return {**reference, "position_m": position}


def fit_ballistic(rows, oid, gravity):
    """Fit p(t)=p0+v0*(t-centre)+g*(t-centre)^2/2 in SI units."""
    if len(rows) < POLICY["minimum_fit_samples"]:
        raise ValueError("at least three measured samples required")
    centre = sum(r["time_s"] for r in rows)/len(rows)
    dt = [r["time_s"]-centre for r in rows]
    denominator = sum(t*t for t in dt)
    if denominator <= 0:
        raise ValueError("distinct sample times required")
    p0, v0 = [], []
    for axis in range(3):
        adjusted = [r["objects"][oid]["position_m"][axis]-.5*gravity[axis]*t*t for r, t in zip(rows, dt)]
        mean = sum(adjusted)/len(adjusted)
        p0.append(mean)
        v0.append(sum(t*(p-mean) for p, t in zip(adjusted, dt))/denominator)
    fit = {"centre_time_s": centre, "position_at_centre_m": p0, "velocity_at_centre_m_s": v0,
           "gravity_m_s2": list(gravity), "ticks": [r["tick"] for r in rows],
           "time_interval_s": [rows[0]["time_s"], rows[-1]["time_s"]],
           "source_rows_sha256": _json_hash([{k: r[k] for k in ("tick", "time_s", "objects")} for r in rows])}
    fit["max_position_residual_m"] = max(math.dist(evaluate_fit(fit, r["time_s"])[0], r["objects"][oid]["position_m"]) for r in rows)
    fit["fit_sha256"] = _json_hash(fit)
    return fit


def evaluate_fit(fit, time):
    dt = time-fit["centre_time_s"]
    acceleration = fit["acceleration_m_s2"] if "acceleration_m_s2" in fit else fit["gravity_m_s2"]
    return ([p+v*dt+.5*g*dt*dt for p, v, g in zip(fit["position_at_centre_m"], fit["velocity_at_centre_m_s"], acceleration)],
            [v+g*dt for v, g in zip(fit["velocity_at_centre_m_s"], acceleration)])


def _first_root(fit, sphere, sphere_pose, box, box_pose, interval):
    def distance(time):
        return gap(sphere, _pose(evaluate_fit(fit, time)[0], sphere_pose), box, box_pose)
    start, end = interval
    maximum_speed = max(_norm(evaluate_fit(fit, t)[1]) for t in interval)
    radius = sphere["radius_m"]*min(sphere_pose["scale"])
    if maximum_speed*(end-start)/POLICY["root_subdivisions"] > radius/8:
        return None  # Unsupported fast crossing stays unverified, never inferred.
    prior_time, prior_gap = start, distance(start)
    if prior_gap < -1e-8:
        return None
    # Bounded root search. A tangent touch without a signed crossing is not proof.
    for step in range(1, POLICY["root_subdivisions"]+1):
        time = start+(end-start)*step/POLICY["root_subdivisions"]
        value = distance(time)
        if prior_gap >= 0 and value < 0:
            lo, hi = prior_time, time
            for _ in range(45):
                middle = (lo+hi)/2
                if distance(middle) >= 0:
                    lo = middle
                else:
                    hi = middle
            return (lo+hi)/2
        prior_time, prior_gap = time, value
    return None


def _face_normal(position, spec, state):
    axes = _axes(state["quaternion_xyzw"])
    local = [_dot(_sub(position, state["position_m"]), axis) for axis in axes]
    half = [h*s for h, s in zip(spec["half_extents_m"], state["scale"])]
    outside = [i for i, (x, h) in enumerate(zip(local, half)) if abs(x) > h+1e-8]
    if len(outside) != 1:
        return None
    axis = outside[0]
    # Near an edge the uncertainty can change the face or create two contacts.
    if any(half[i]-abs(local[i]) <= POLICY["contact_continuity_m"] for i in range(3) if i != axis):
        return None
    return [v*(1 if local[axis] >= 0 else -1) for v in axes[axis]]


def _scope(config, rows):
    raw = config["objects"]
    specs = raw if isinstance(raw, dict) else {s["object_id"]: s for s in raw}
    active = [o for o in specs if specs[o]["mode"] == "dynamic"]
    if (config.get("motion_mode") != BACKEND or (config.get("mechanics") or {}).get("model_version") != BACKEND
            or len(active) != 1 or specs[active[0]]["shape"] != "sphere"
            or specs[active[0]].get("motion_backend") != BACKEND or specs[active[0]].get("mass_kg") != 1):
        raise ValueError("only the explicit one-sphere fixed-OBB mechanics backend is eligible")
    oid = active[0]
    if any(specs[o]["mode"] != "passive" or specs[o]["shape"] != "box" for o in specs if o != oid):
        raise ValueError("moving or non-box obstacles are unsupported")
    hz = config["physics_hz"]
    if not isinstance(hz, int) or hz < 240 or len(rows) < 8:
        raise ValueError("native high-rate evaluated trajectory required")
    if len(config["gravity_m_s2"]) != 3 or any(not math.isfinite(v) for v in config["gravity_m_s2"]):
        raise ValueError("finite declared gravity required")
    for i, row in enumerate(rows):
        if row["tick"] != i or abs(row["time_s"]-i/hz) > 1e-10 or set(row["objects"]) != set(specs):
            raise ValueError("evaluated clock or collider coverage mismatch")
        for other in specs:
            a, b = row["objects"][other], rows[0]["objects"][other]
            if any(not math.isfinite(v) for key in ("position_m", "quaternion_xyzw", "scale") for v in a[key]):
                raise ValueError("nonfinite evaluated transform")
            if min(a["scale"]) <= 0 or abs(_norm(a["quaternion_xyzw"])-1) > TOLERANCE_POLICY["quaternion_norm_error"]:
                raise ValueError("invalid rigid transform scale or quaternion")
            tolerance(specs[other], a)
            if max(abs(x-y) for x, y in zip(a["scale"], b["scale"])) > TOLERANCE_POLICY["scale_drift"]:
                raise ValueError("rigid shape scale changed")
            if other != oid and (math.dist(a["position_m"], b["position_m"]) > 1e-5
                    or angular_distance(a["quaternion_xyzw"], b["quaternion_xyzw"]) > 1e-4):
                raise ValueError("declared static OBB moved")
    return specs, oid


def _window_fits(rows, indices, oid, specs, gravity, cache):
    fits = []
    for start, stop in indices:
        if start < 0 or stop > len(rows):
            continue
        key = start, stop
        if key not in cache:
            selected = rows[start:stop]
            clear = all(gap(specs[oid], row["objects"][oid], specs[o], row["objects"][o]) >
                        min(tolerance(specs[oid], row["objects"][oid]), tolerance(specs[o], row["objects"][o]))
                        for row in selected for o in specs if o != oid)
            fit = fit_ballistic(selected, oid, gravity) if clear else None
            cache[key] = fit if fit and fit["max_position_residual_m"] <= POLICY["fit_position_residual_m"] else None
        if cache[key]:
            fits.append(cache[key])
    return fits


def _certify_pair(specs, oid, other, rows, tick, pre, post, root=None):
    interval = [rows[tick]["time_s"], rows[tick+1]["time_s"]]
    first = rows[0]["objects"]
    if root is None:
        root = _first_root(pre, specs[oid], first[oid], specs[other], first[other], interval)
    if root is None:
        return None, "no independently fitted first crossing in tick interval"
    p, incoming = evaluate_fit(pre, root)
    p2, outgoing = evaluate_fit(post, root)
    continuity = math.dist(p, p2)
    if continuity > POLICY["contact_continuity_m"]:
        return None, "pre/post contact position discontinuity"
    normal = _face_normal(p, specs[other], first[other])
    if normal is None:
        return None, "edge or corner contact is ambiguous"
    others = [o for o in specs if o not in {oid, other}]
    if any(gap(specs[oid], _pose(p, first[oid]), specs[o], first[o]) <= POLICY["contact_continuity_m"] for o in others):
        return None, "multiple nearby obstacle contacts are ambiguous"
    vin, vout = _dot(incoming, normal), _dot(outgoing, normal)
    e = specs[oid]["restitution"]*specs[other]["restitution"]
    if not math.isfinite(e) or not 0 <= e <= 1:
        return None, "declared restitution outside model scope"
    response = abs(vout+e*vin)
    if vin >= 0 or vout <= 0 or response > POLICY["normal_response_residual_m_s"]:
        return None, "incoming/outgoing normal response does not certify a rebound"
    # Every raw sample across both fit windows must agree with the same two
    # segments. This blocks a hidden teleport or intervening impulse in a gap.
    combined = rows[pre["ticks"][0]:post["ticks"][-1]+1]
    residual = max(math.dist(evaluate_fit(pre if r["time_s"] <= root else post, r["time_s"])[0],
                             r["objects"][oid]["position_m"]) for r in combined)
    if residual > POLICY["fit_position_residual_m"]:
        return None, "intervening samples disagree with two continuous ballistic segments"
    # Inspect the fitted path up to/from contact for another collider crossing.
    for fit, start, end in ((pre, pre["time_interval_s"][1], root), (post, root, post["time_interval_s"][0])):
        for step in range(17):
            pos = evaluate_fit(fit, start+(end-start)*step/16)[0]
            state = _pose(pos, first[oid])
            if any(gap(specs[oid], state, specs[o], first[o]) < -POLICY["fit_position_residual_m"] for o in specs if o != oid):
                return None, "fitted flight crosses an intervening collider"
    physical_uncertainty = rows[1]["time_s"]-rows[0]["time_s"]
    certificate = {"numerical_status": "PASSED", "validated": False,
        "object_ids": sorted([oid, other]), "sphere_id": oid, "obstacle_id": other,
        "tick_interval": [tick, tick+1], "time_interval_s": interval,
        "physical_time_estimate_s": root, "time_uncertainty_s": physical_uncertainty,
        "confirmation_time_s": post["time_interval_s"][1],
        "position_at_contact_m": p, "outward_normal": normal,
        "incoming_normal_m_s": vin, "outgoing_normal_m_s": vout,
        "effective_restitution_expected": e, "effective_restitution_measured": -vout/vin,
        "normal_response_residual_m_s": response, "contact_position_continuity_m": continuity,
        "combined_fit_max_position_residual_m": residual,
        "pre_fit": pre, "post_fit": post,
        "reason": "overall candidate physical pass required before integration"}
    certificate["fit_pair_sha256"] = _json_hash({"pre": pre, "post": post, "pair": certificate["object_ids"], "time_s": root})
    return certificate, None



def fit_measured_acceleration(rows, oid):
    """Separate pre-release fit: acceleration is measured, never set to gravity."""
    if len(rows) < POLICY["release_minimum_support_samples"]:
        raise ValueError("at least five supported samples required for measured pre-release acceleration")
    centre = sum(r["time_s"] for r in rows)/len(rows)
    times = [r["time_s"]-centre for r in rows]
    mean_square = sum(t*t for t in times)/len(times)
    square_variance = sum((t*t-mean_square)**2 for t in times)
    if square_variance <= 0:
        raise ValueError("distinct support times required")
    # Native uniform, centred sample times make odd/even polynomial columns
    # orthogonal. That clock is checked before this fit is called.
    acceleration = [2*sum((t*t-mean_square)*r["objects"][oid]["position_m"][j] for r, t in zip(rows, times))/square_variance for j in range(3)]
    fit = fit_ballistic(rows, oid, acceleration)
    fit["acceleration_m_s2"] = fit.pop("gravity_m_s2")
    fit["acceleration_basis"] = "independent least-squares quadratic fit of prior supported positions"
    fit["measured_acceleration_m_s2"] = acceleration
    fit["fit_sha256"] = _json_hash({k: v for k, v in fit.items() if k != "fit_sha256"})
    return fit


def _gravity_residual(rows, oid, gravity):
    errors = []
    for a, b, c in zip(rows, rows[1:], rows[2:]):
        dt = b["time_s"]-a["time_s"]
        actual = [(c["objects"][oid]["position_m"][j]-2*b["objects"][oid]["position_m"][j]+a["objects"][oid]["position_m"][j])/(dt*dt) for j in range(3)]
        errors.append(_norm(_sub(actual, gravity)))
    return max(errors, default=math.inf)


def detect_supported_releases(config, rows):
    """Constraint departures, not calibrated launcher impulses or kinematic handoffs.

    Prior face support and subsequent separated ballistic samples are disjoint
    measured windows. Their independently fitted velocities/positions must meet
    within the observed one-tick departure bracket. Edge departure is allowed;
    simultaneous new contact or an unresolvable join remains unverified.
    """
    specs, oid = _scope(config, rows)
    gravity = config["gravity_m_s2"]
    gravity_length = _norm(gravity)
    if gravity_length <= 1e-9:
        return {"releases": [], "unverified_releases": [{"physical_time_estimate_s": None, "reason": "support-to-gravity release undefined at zero gravity"}]}
    supports = []
    for row in rows:
        found = set()
        sphere_state = row["objects"][oid]
        for other, spec in specs.items():
            if other == oid:
                continue
            state = row["objects"][other]
            distance = gap(specs[oid], sphere_state, spec, state)
            normal = _face_normal(sphere_state["position_m"], spec, state)
            if (abs(distance) <= POLICY["release_support_gap_m"] and normal is not None
                    and _dot(normal, gravity) < -.05*gravity_length):
                found.add(other)
        supports.append(found)
    releases, unknown, cache = [], [], {}
    count = POLICY["release_minimum_support_samples"]
    for tick in range(count, len(rows)-count):
        if len(supports[tick-1]) > 1 and supports[tick] != supports[tick-1]:
            unknown.append({"sphere_id": oid, "support_ids": sorted(supports[tick-1]),
                            "tick_interval": [tick-1, tick], "physical_time_estimate_s": None,
                            "reasons": ["multiple prior supports make release ownership ambiguous"]})
        if len(supports[tick-1]) != 1:
            continue
        other = next(iter(supports[tick-1]))
        if other in supports[tick] or not all(s == {other} for s in supports[tick-count:tick]):
            continue
        interval = [rows[tick-1]["time_s"], rows[tick]["time_s"]]
        reasons, candidates = set(), []
        if supports[tick]:
            reasons.add("new or simultaneous support at constraint departure")
        else:
            pre = fit_measured_acceleration(rows[tick-count:tick], oid)
            indices = [(tick+offset, tick+offset+n) for n in (7, 5)
                       for offset in range(POLICY["maximum_fit_offset_ticks"]+1)]
            posts = _window_fits(rows, indices, oid, specs, gravity, cache)
            if not posts:
                reasons.add("no sustained contact-free post-release gravity window")
            for post in posts:
                selected = rows[post["ticks"][0]:post["ticks"][-1]+1]
                gravity_error = _gravity_residual(selected, oid, gravity)
                if gravity_error > TOLERANCE_POLICY["free_flight_acceleration_error_m_s2"]:
                    reasons.add("post-release acceleration differs from gravity")
                    continue
                reference = interval[0]
                pre_velocity = evaluate_fit(pre, reference)[1]
                post_velocity = evaluate_fit(post, reference)[1]
                delta_acceleration = _sub(pre["acceleration_m_s2"], post["gravity_m_s2"])
                denominator = _dot(delta_acceleration, delta_acceleration)
                if denominator <= 1e-8:
                    reasons.add("constraint change time cannot be resolved from measured accelerations")
                    continue
                join = reference-_dot(_sub(pre_velocity, post_velocity), delta_acceleration)/denominator
                if not interval[0]-1e-8 <= join <= interval[1]+1e-8:
                    reasons.add("independent velocity join lies outside the observed departure tick")
                    continue
                p0, v0 = evaluate_fit(pre, join)
                p1, v1 = evaluate_fit(post, join)
                position_error, velocity_error = math.dist(p0, p1), math.dist(v0, v1)
                combined = rows[pre["ticks"][0]:post["ticks"][-1]+1]
                residual = max(math.dist(evaluate_fit(pre if r["time_s"] <= join else post, r["time_s"])[0], r["objects"][oid]["position_m"]) for r in combined)
                if (position_error > POLICY["contact_continuity_m"] or velocity_error > POLICY["release_velocity_continuity_m_s"]
                        or residual > POLICY["fit_position_residual_m"] or pre["max_position_residual_m"] > POLICY["fit_position_residual_m"]):
                    reasons.add("independent pre-support/post-flight trajectories have an unexplained position or velocity discontinuity")
                    continue
                if any(gap(specs[oid], row["objects"][oid], specs[o], row["objects"][o]) <=
                       min(tolerance(specs[oid], row["objects"][oid]), tolerance(specs[o], row["objects"][o]))
                       for row in rows[tick-1:post["ticks"][-1]+1] for o in specs if o not in {oid, other}):
                    reasons.add("another collider is near the release and its impulse cannot be excluded")
                    continue
                episode_start = tick-count
                while episode_start > 0 and supports[episode_start-1] == {other}:
                    episode_start -= 1
                item = {"numerical_status": "PASSED", "validated": False,
                        "kind": "supported_release", "sphere_id": oid, "support_id": other,
                        "object_ids": sorted([oid, other]), "tick_interval": [tick-1, tick],
                        "time_interval_s": interval, "physical_time_estimate_s": join,
                        "time_uncertainty_s": 1/config["physics_hz"], "confirmation_time_s": post["time_interval_s"][1],
                        "support_episode_tick_interval": [episode_start, tick-1],
                        "position_continuity_m": position_error, "velocity_continuity_m_s": velocity_error,
                        "combined_fit_max_position_residual_m": residual, "post_flight_gravity_residual_m_s2": gravity_error,
                        "pre_support_fit": pre, "post_flight_fit": post,
                        "checked": "prior finite-face support, subsequent separated gravity flight, and independently fitted position/velocity continuity",
                        "not_checked": "no independent launcher impulse or expected launch velocity calibration",
                        "reason": "overall candidate physical pass required before integration"}
                item["fit_pair_sha256"] = _json_hash({"pre": pre, "post": post, "pair": item["object_ids"], "time_s": join})
                candidates.append(item)
        if candidates:
            releases.append(min(candidates, key=lambda c: (c["combined_fit_max_position_residual_m"], c["velocity_continuity_m_s"], c["confirmation_time_s"])))
        else:
            unknown.append({"sphere_id": oid, "support_id": other, "tick_interval": [tick-1, tick],
                            "physical_time_estimate_s": None, "reasons": sorted(reasons)})
    return {"releases": releases, "unverified_releases": unknown}

def detect_contact_intervals(config, rows):
    """Return numerical evidence and unknowns; never asserts overall validation."""
    specs, oid = _scope(config, rows)
    gravity = config["gravity_m_s2"]
    certificates, unknown, cache, candidates = [], [], {}, 0
    for tick in range(2, len(rows)-3):
        a, b, c, d = rows[tick-1:tick+3]
        dt = b["time_s"]-a["time_s"]
        before = [v/dt for v in _sub(b["objects"][oid]["position_m"], a["objects"][oid]["position_m"])]
        after = [v/dt for v in _sub(d["objects"][oid]["position_m"], c["objects"][oid]["position_m"])]
        impulse = _norm([v-u-2*g*dt for u, v, g in zip(before, after, gravity)])
        if impulse < POLICY["minimum_velocity_discontinuity_m_s"]:
            continue
        candidates += 1
        pre_indices, post_indices = [], []
        for count in (POLICY["preferred_fit_samples"], POLICY["minimum_fit_samples"]):
            for offset in range(POLICY["maximum_fit_offset_ticks"]+1):
                pre_indices.append((tick-offset-count+1, tick-offset+1))
                post_indices.append((tick+1+offset, tick+1+offset+count))
        pres = _window_fits(rows, pre_indices, oid, specs, gravity, cache)
        posts = _window_fits(rows, post_indices, oid, specs, gravity, cache)
        reasons, found = set(), []
        if not pres or not posts:
            reasons.add("insufficient contact-free ballistic samples before or after discontinuity")
        for pre in pres:
            for other in specs:
                if other == oid:
                    continue
                first = rows[0]["objects"]
                root = _first_root(pre, specs[oid], first[oid], specs[other], first[other], [rows[tick]["time_s"], rows[tick+1]["time_s"]])
                if root is None:
                    reasons.add("no independently fitted first crossing in tick interval")
                    continue
                for post in posts:
                    certificate, reason = _certify_pair(specs, oid, other, rows, tick, pre, post, root)
                    if certificate:
                        found.append(certificate)
                    else:
                        reasons.add(reason)
        if found:
            pairs = {tuple(c["object_ids"]) for c in found}
            if len(pairs) != 1:
                reasons.add("more than one obstacle explains the discontinuity")
            else:
                best = min(found, key=lambda c: (c["combined_fit_max_position_residual_m"],
                            c["contact_position_continuity_m"], c["confirmation_time_s"]))
                if not any(c["object_ids"] == best["object_ids"] and abs(c["physical_time_estimate_s"]-best["physical_time_estimate_s"]) < dt for c in certificates):
                    certificates.append(best)
                continue
        unknown.append({"sphere_id": oid, "obstacle_id": None,
                        "tick_interval": [tick, tick+1], "time_estimate_s": None,
                        "velocity_discontinuity_m_s": impulse, "reasons": sorted(reasons)})
    # Adjacent finite-difference windows can flag the same impulse. Do not count
    # their unsuccessful bracketing attempts as separate unresolved contacts.
    unknown = [u for u in unknown if not any(abs(u["tick_interval"][0]-c["tick_interval"][0]) <= 1 for c in certificates)]
    release_evidence = detect_supported_releases(config, rows)
    return {"version": VERSION, "backend": BACKEND, "policy": POLICY, **release_evidence,
            "status_scope": "eligibility of the certified subset, not completeness of contact detection",
            "status": "NUMERICAL_EVIDENCE_ONLY", "contacts": certificates, "unverified": unknown,
            "coverage": {"complete": False, "velocity_discontinuity_intervals": candidates, "certified_onsets": len(certificates),
                         "unverified_intervals": len(unknown), "certified_releases": len(release_evidence["releases"]),
                         "unverified_release_transitions": len(release_evidence["unverified_releases"])},
            "limitations": ["No claim of complete contact coverage; low impulses and sustained support may have no eligible free-flight windows.",
                            "Time uncertainty is one evaluated tick, not the smaller root-finding arithmetic error.",
                            "Tangential friction, force and impulse magnitude are not independently certified here."]}


def certify_candidate(directory):
    root = Path(directory).resolve()
    config = json.loads((root/"production.json").read_text())
    rows = [json.loads(line) for line in (root/"physics_states.jsonl").read_text().splitlines() if line.strip()]
    report = detect_contact_intervals(config, rows)
    physical = validate_candidate(root)
    inputs = {name: _hash(root/name) for name in ("production.json", "physics_states.jsonl")}
    for name in ("physical-validation.json", "solver_calibration.json", "replay_validation.json"):
        if (root/name).is_file():
            inputs[name] = _hash(root/name)
    valid = (physical["status"] == "PASSED" and not physical["issues"]
             and all(physical.get("inputs", {}).get(name) == inputs[name] for name in ("production.json", "physics_states.jsonl")))
    report["source_hashes"] = inputs
    report["implementation_sha256"] = _hash(Path(__file__))
    report["physical_evidence"] = {"recomputed_status": physical["status"], "recomputed_sha256": _json_hash(physical),
        "gates": physical["gates"], "issues": physical["issues"], "eligible": valid}
    report["status"] = "PASSED" if valid else "UNVERIFIED_PHYSICAL_CANDIDATE"
    for kind, markers in (("ballistic-contact", report["contacts"]), ("supported-release", report["releases"])):
        for index, certificate in enumerate(markers):
            certificate["id"] = f"{kind}-{index:04d}"
            certificate["validated"] = valid
            certificate["source_hashes"] = {"production.json": inputs["production.json"], "physics_states.jsonl": inputs["physics_states.jsonl"]}
            certificate["reason"] = None if valid else "overall candidate physical gate did not pass"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = certify_candidate(args.candidate)
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
        print(json.dumps({"status": result["status"], "path": str(args.out), "sha256": _hash(args.out), "coverage": result["coverage"]}))
    else:
        print(rendered, end="")
    raise SystemExit(0 if result["status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
