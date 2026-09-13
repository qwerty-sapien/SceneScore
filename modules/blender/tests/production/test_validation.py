"""Independent analytical controls; production asset mutations run separately."""
import hashlib
import json
import math
from pathlib import Path

import pytest

from modules.blender.production.validation import (
    TOLERANCE_POLICY,
    _axes,
    _dot,
    _projection,
    assess_reference_case,
    check_rendered_cadence,
    gap,
    supported_objects,
    swept_gap,
    tolerance,
    validate_candidate,
    validate_motion_case,
)

FIXTURES = json.loads(Path(__file__).with_name("analytic_cases.json").read_text())


def state(position=(0, 0, 0), quaternion=(0, 0, 0, 1), scale=(1, 1, 1)):
    return {"position_m": list(position), "quaternion_xyzw": list(quaternion), "scale": list(scale)}


def sphere(radius=.2, mode="dynamic", object_id="ball"):
    return {"object_id": object_id, "sonic_identity_id": object_id, "shape": "sphere", "radius_m": radius,
            "mode": mode, "role": "physical_participant", "scored": mode == "dynamic"}


def box(half=(.5, .5, .5), mode="passive", object_id="box"):
    return {"object_id": object_id, "sonic_identity_id": object_id, "shape": "box", "half_extents_m": list(half),
            "mode": mode, "role": "silent_support", "scored": False}


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=lambda c: c["id"])
def test_independently_derived_reference_cases(case):
    result = assess_reference_case(case)
    assert result["accepted"] == case["expected_accept"], result


def test_reference_count_and_scope():
    results = [assess_reference_case(c) for c in FIXTURES["cases"]]
    assert sum(r["accepted"] for r in results) == 9
    assert sum(not r["accepted"] for r in results) == 9
    assert all(r["scope"] == "synthetic_analytical_reference_only" for r in results)


def test_sphere_box_containment_and_rotated_corner():
    assert gap(sphere(.2), state(), box(), state()) == pytest.approx(-.7)
    q = (0, 0, math.sin(math.pi/8), math.cos(math.pi/8))
    # Local x=.7 along a box axis places a .2m sphere exactly on the face.
    position = (.7/math.sqrt(2), .7/math.sqrt(2), 0)
    assert gap(sphere(.2), state(position), box(), state(quaternion=q)) == pytest.approx(0, abs=1e-12)
    # Corner distance must be Euclidean, not a maximum-axis AABB gap.
    assert gap(sphere(.2), state((.7, .7, 0)), box(), state()) == pytest.approx(math.sqrt(.08)-.2)


def test_contained_boxes_require_full_separating_translation():
    assert gap(box((1, 1, 1)), state(), box((.1, .1, .1)), state()) == pytest.approx(-1.1)
    assert gap(box((1, 1, 1)), state(), box((.1, .1, .1)), state((.8, 0, 0))) == pytest.approx(-.3)


def euler_quaternion(roll, pitch, yaw):
    cr, sr = math.cos(roll/2), math.sin(roll/2)
    cp, sp = math.cos(pitch/2), math.sin(pitch/2)
    cy, sy = math.cos(yaw/2), math.sin(yaw/2)
    return (sr*cp*cy-cr*sp*sy, cr*sp*cy+sr*cp*sy, cr*cp*sy-sr*sp*cy, cr*cp*cy+sr*sp*sy)


def test_cross_product_axes_are_required_for_skew_rods():
    rod = box((2, .1, .1))
    a = state()
    q = euler_quaternion(math.pi/4, -math.asin(1/math.sqrt(3)), math.pi/4)
    b = state((0, -.5/math.sqrt(2), .5/math.sqrt(2)), q)
    face_only_gap = max(abs(_dot(b["position_m"], axis))-_projection(rod, a, axis)-_projection(rod, b, axis)
                        for axis in _axes(a)+_axes(b))
    assert face_only_gap < 0  # Six face normals would falsely report overlap.
    assert gap(rod, a, rod, b) > .20


def test_gap_rotation_and_translation_invariant():
    a, b = sphere(.2), box((.3, .5, .7))
    base = gap(a, state((.8, 0, 0)), b, state())
    q = (0, 0, math.sin(.43/2), math.cos(.43/2))
    moved = (.8*math.cos(.43)+6, .8*math.sin(.43)-3, 9)
    assert gap(a, state(moved, q), b, state((6, -3, 9), q)) == pytest.approx(base)


def test_scale_policy_caps_and_unsupported_ellipsoid():
    assert tolerance(sphere(.2), state()) == .004
    assert tolerance(box(), state()) == .005
    assert TOLERANCE_POLICY["arithmetic_floor_m"] == 1e-5
    with pytest.raises(ValueError, match="too small"):
        tolerance(sphere(.0001), state())
    with pytest.raises(ValueError, match="ellipsoid"):
        gap(sphere(), state(scale=(1, 2, 1)), box(), state())


def test_fast_sphere_crossing_and_valid_corner_miss():
    moving, fixed = sphere(.1), box((.1, .5, .5))
    a0, a1 = state((-2, 0, 0)), state((2, 0, 0))
    assert gap(moving, a0, fixed, state()) > 0 and gap(moving, a1, fixed, state()) > 0
    sweep = swept_gap(moving, a0, a1, fixed, state(), state())
    assert sweep["gap_m"] == pytest.approx(-.2, abs=1e-7)
    assert sweep["fraction"] == pytest.approx(.5, abs=1e-7)
    # Minkowski AABB inflation alone would falsely reject this corner passage.
    miss = swept_gap(moving, state((-2, .59, .59)), state((2, .59, .59)), fixed, state(), state())
    assert miss["gap_m"] > 0


def test_fast_sphere_pair_crossing():
    shape = sphere(.1)
    result = swept_gap(shape, state((-2, 0, 0)), state((2, 0, 0)), shape, state(), state())
    assert result["gap_m"] == pytest.approx(-.2)
    assert result["fraction"] == .5


def test_supported_stack_and_side_contact_is_not_support():
    specs = {"floor": box((2, 2, .1), object_id="floor"), "box": box(mode="dynamic"), "ball": sphere(.2)}
    states = {"floor": state((0, 0, -.1)), "box": state((0, 0, .5)), "ball": state((0, 0, 1.2))}
    assert supported_objects(specs, states) == set(specs)
    states["ball"] = state((.7, 0, .8))
    assert "ball" not in supported_objects(specs, states)


def make_candidate(root):
    root.mkdir(parents=True, exist_ok=True)
    (root/"simulation.blend").write_bytes(b"synthetic-test-marker-NOT-BLENDER")
    specs = [box((2, 2, .1), object_id="floor"), sphere(.2)]
    rows = [{"tick": i, "time_s": i/240, "objects": {"floor": state((0, 0, -.1)), "ball": state((0, 0, .2))}}
            for i in range(121)]
    config = {"version": "blender-production-1", "physics_hz": 240, "render_fps": 30, "duration_s": .5,
              "gravity_m_s2": [0, 0, -9.81], "objects": specs, "source_fingerprint": "synthetic-fixture",
              "validation_cases": [{"kind": "supported_rest", "object_id": "ball", "start_s": .25, "end_s": .5}]}
    save_candidate(root, config, rows)
    return config, rows


def save_candidate(root, config, rows, update_lineage=True):
    (root/"physics_states.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    if update_lineage:
        config["lineage"] = {"source_fingerprint": config["source_fingerprint"],
                             "bake_source_fingerprint": config["source_fingerprint"],
                             "states_sha256": hashlib.sha256((root/"physics_states.jsonl").read_bytes()).hexdigest(),
                             "artifacts": {"simulation.blend": hashlib.sha256((root/"simulation.blend").read_bytes()).hexdigest()}}
    (root/"production.json").write_text(json.dumps(config))


def test_numerical_pass_does_not_certify_missing_blender_or_render(tmp_path):
    make_candidate(tmp_path)
    result = validate_candidate(tmp_path)
    assert result["gates"]["geometric_contact"]["status"] == "PASSED"
    assert result["gates"]["physical_motion"]["status"] == "PASSED"
    assert result["status"] == "NOT_RUN"
    assert result["gates"]["solver_calibration"]["status"] == "NOT_RUN"
    assert result["gates"]["fresh_process_replay"]["status"] == "NOT_RUN"
    assert result["gates"]["rendered_temporal"]["status"] == "NOT_RUN"
    assert result["gates"]["perceptual_story_appearance"]["status"] == "NOT_RUN"


@pytest.mark.parametrize("mutation,expected_code", [
    ("disable_collider", "disabled_consequential_collider"),
    ("penetrate", "solid_penetration"),
    ("hover", "unsupported_rest"),
    ("scale_parent", "rigid_scale_drift"),
    ("stale_bake", "stale_bake_source"),
    ("stale_states", "stale_state_digest"),
    ("spurious_contact", "spurious_contact"),
    ("spurious_foley", "spurious_foley"),
])
def test_synthetic_pipeline_mutations_reject_even_with_plausible_names(tmp_path, mutation, expected_code):
    config, rows = make_candidate(tmp_path)
    if mutation == "disable_collider":
        config["objects"][0]["collision_enabled"] = False
    if mutation == "penetrate":
        rows[50]["objects"]["ball"]["position_m"][2] = .1
    if mutation == "hover":
        for row in rows:
            row["objects"]["ball"]["position_m"][2] += .5
    if mutation == "scale_parent":
        rows[50]["objects"]["ball"]["scale"] = [.9, .9, .9]
    if mutation == "stale_bake":
        config["source_fingerprint"] = "changed-physics"
    if mutation == "stale_states":
        rows[50]["objects"]["ball"]["position_m"][0] += .1
    if mutation in {"spurious_contact", "spurious_foley"}:
        for row in rows:
            row["objects"]["ball"]["position_m"][2] = .7
        (tmp_path/"production_events.json").write_text(json.dumps([
            {"id": "plausible-event", "type": mutation.removeprefix("spurious_"), "time_s": .3, "object_ids": ["ball", "floor"]}]))
    save_candidate(tmp_path, config, rows, update_lineage=mutation not in {"stale_bake", "stale_states"})
    result = validate_candidate(tmp_path)
    assert result["status"] == "FAILED", result
    assert expected_code in {i["code"] for i in result["issues"]}, result


def test_interpolated_crossing_rejected_when_endpoints_are_clear(tmp_path):
    config, rows = make_candidate(tmp_path)
    config["objects"][0] = box((.01, 2, 2), object_id="floor")
    config["objects"][1]["radius_m"] = .05
    for row in rows:
        row["objects"]["floor"] = state()
        row["objects"]["ball"] = state((-1 if row["tick"] < 60 else 1, 0, 0))
    save_candidate(tmp_path, config, rows)
    result = validate_candidate(tmp_path)
    assert "between_sample_crossing" in {i["code"] for i in result["issues"]}
    crossing = next(i for i in result["issues"] if i["code"] == "between_sample_crossing")
    assert crossing["interval_s"] == [59/240, 60/240]
    assert "linear" in crossing["uncertainty"]


def test_dropped_release_velocity_fails_sample_case(tmp_path):
    config, rows = make_candidate(tmp_path)
    specs = {s["object_id"]: s for s in config["objects"]}
    case = {"kind": "release", "object_id": "ball", "release_time_s": .2,
            "expected_velocity_m_s": [2, 0, 0]}
    result = validate_motion_case(case, specs, rows, config["gravity_m_s2"])
    assert result["status"] == "FAILED"
    assert result["metrics"]["velocity_error_m_s"] == 2


def test_sampled_gravity_checks_accept_ballistic_horizontal_constant_speed():
    rows = [{"tick": i, "time_s": i/240, "objects": {"ball": state((3*i/240, 0, 2-4.905*(i/240)**2))}}
            for i in range(121)]
    case = {"kind": "free_flight", "object_id": "ball"}
    good = validate_motion_case(case, {"ball": sphere()}, rows, [0, 0, -9.81])
    assert good["status"] == "PASSED", good
    for row in rows:
        row["objects"]["ball"]["position_m"][2] = 2
    bad = validate_motion_case(case, {"ball": sphere()}, rows, [0, 0, -9.81])
    assert bad["status"] == "FAILED"


def test_incomplete_replay_report_is_failure_not_success(tmp_path):
    make_candidate(tmp_path)
    (tmp_path/"replay_validation.json").write_text(json.dumps({"status": "PASSED", "mode": "fresh_blender_process"}))
    result = validate_candidate(tmp_path)
    assert result["gates"]["fresh_process_replay"]["status"] == "FAILED"


def test_duplicate_low_cadence_frames_rejected_but_stillness_allowed():
    pts = [i/30 for i in range(30)]
    hashes = [str(i//3) for i in range(30)]
    bad = check_rendered_cadence(pts, 30, 30, hashes, set(range(1, 30)))
    assert bad["status"] == "FAILED"
    assert len(bad["duplicate_motion_frames"]) == 20
    assert check_rendered_cadence(pts, 30, 30, ["same"]*30, set())["status"] == "PASSED"
    assert check_rendered_cadence(pts, 30, 30)["status"] == "NOT_RUN"
    assert check_rendered_cadence([i/8 for i in range(8)], 30, 30, [str(i) for i in range(8)], set())["status"] == "FAILED"


def test_missing_and_nonfinite_candidate_data_fail(tmp_path):
    assert validate_candidate(tmp_path)["status"] == "FAILED"
    config, rows = make_candidate(tmp_path)
    rows[50]["objects"]["ball"]["position_m"][0] = float("nan")
    save_candidate(tmp_path, config, rows)
    assert validate_candidate(tmp_path)["status"] == "FAILED"


def test_dynamic_collision_group_never_excludes_solid_contact(tmp_path):
    config, rows = make_candidate(tmp_path)
    for obj in config["objects"]:
        obj["collision_group"] = "same-structure"
    rows[50]["objects"]["ball"]["position_m"][2] = 0
    save_candidate(tmp_path, config, rows)
    result = validate_candidate(tmp_path)
    assert "solid_penetration" in {i["code"] for i in result["issues"]}


def test_unsupported_hold_in_middle_is_not_hidden_by_supported_finale(tmp_path):
    config, rows = make_candidate(tmp_path)
    for row in rows[5:100]:
        row["objects"]["ball"]["position_m"][2] += .5
    save_candidate(tmp_path, config, rows)
    report = validate_candidate(tmp_path)
    assert "unsupported_rest" in {i["code"] for i in report["issues"]}


def add_replay_fixture(path, rows):
    import shutil
    shutil.copyfile(path/"simulation.blend", path/"scene.blend")
    (path/"replay_states.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    def digest(name):
        return hashlib.sha256((path/name).read_bytes()).hexdigest()
    report = {"status": "PASSED", "mode": "fresh_blender_process", "samples_checked": len(rows),
              "source_states_sha256": digest("physics_states.jsonl"), "source_hash": digest("scene.blend"),
              "replay_states_sha256": digest("replay_states.jsonl"), "max_position_error_m": 0,
              "max_rotation_error_rad": 0, "max_scale_error": 0}
    (path/"replay_validation.json").write_text(json.dumps(report))


def test_actual_replay_rows_independently_checked_even_if_report_claims_success(tmp_path):
    config, rows = make_candidate(tmp_path)
    add_replay_fixture(tmp_path, rows)
    assert validate_candidate(tmp_path)["gates"]["fresh_process_replay"]["status"] == "PASSED"
    rows[90]["objects"]["ball"]["position_m"][0] += .01
    # This updates all advertised report hashes, while its false metrics remain 0.
    add_replay_fixture(tmp_path, rows)
    result = validate_candidate(tmp_path)
    assert result["gates"]["fresh_process_replay"]["status"] == "FAILED"
    issue = next(i for i in result["issues"] if i["code"] == "replay_evidence_mismatch")
    assert issue["independently_computed"]["max_position_error_m"] == pytest.approx(.01)


def test_measured_restitution_catches_high_elasticity_freeze_and_accepts_rebound():
    contact = .6
    speed = 5.0
    rows = []
    for i in range(241):
        time = i/240
        elapsed = time-contact
        z = .2 + (-speed*elapsed if elapsed < 0 else speed*elapsed) - 4.905*elapsed**2
        rows.append({"tick": i, "time_s": time, "objects": {"ball": state((0, 0, z)), "floor": state((0, 0, -.1))}})
    specs = {"ball": sphere(.2), "floor": box((2, 2, .1), object_id="floor")}
    case = {"kind": "fixed_wall_restitution", "object_id": "ball", "wall_object_id": "floor",
            "normal_toward_wall": [0, 0, -1], "contact_time_s": contact, "effective_restitution": 1,
            "incoming_window_s": [.55, .59], "outgoing_window_s": [.61, .65]}
    good = validate_motion_case(case, specs, rows, [0, 0, -9.81])
    assert good["status"] == "PASSED", good
    assert good["metrics"]["effective_restitution_measured"] == pytest.approx(1)
    for row in rows:
        if row["time_s"] >= contact:
            row["objects"]["ball"]["position_m"][2] = .2
    bad = validate_motion_case(case, specs, rows, [0, 0, -9.81])
    assert bad["status"] == "FAILED"
    assert bad["metrics"]["normal_velocity_residual_m_s"] is None
    assert bad["metrics"]["contact_free_windows"] == [True, False]
    assert bad["metrics"]["raw_window_normal_velocities_m_s"][1] == 0


def test_higher_native_audit_rate_supports_convergence_without_relaxing_caps(tmp_path):
    config, base_rows = make_candidate(tmp_path)
    config["physics_hz"] = 480
    rows = [{"tick": i, "time_s": i/480, "objects": base_rows[0]["objects"]} for i in range(241)]
    save_candidate(tmp_path, config, rows)
    report = validate_candidate(tmp_path)
    assert report["gates"]["asset_integrity"]["status"] == "PASSED"
    assert report["gates"]["geometric_contact"]["status"] == "PASSED"
    assert report["metrics"]["pairs"][0]["penetration_tolerance_m"] == .002


def test_sphere_float_decomposition_uses_frozen_scale_and_absolute_geometry_bound():
    rounded = state(scale=(1., .9999995231628418, 1.0000000596046448))
    assert abs(gap(sphere(.28), rounded, box(), state((2, 0, 0)))-1.22) < 1e-6
    with pytest.raises(ValueError, match="ellipsoid"):
        gap(sphere(.28), state(scale=(1, .999, 1)), box(), state((2, 0, 0)))
    with pytest.raises(ValueError, match="ellipsoid"):
        gap(sphere(100), state(scale=(1, 1.000001, 1)), box(), state((200, 0, 0)))


def test_measured_inelastic_rest_uses_supported_velocity_without_fictitious_gravity():
    contact = .6
    rows = []
    for i in range(241):
        elapsed = i/240-contact
        z = .2-5*elapsed-4.905*elapsed**2 if elapsed < 0 else .2
        rows.append({"tick": i, "time_s": i/240, "objects": {"ball": state((0, 0, z)), "floor": state((0, 0, -.1))}})
    case = {"kind": "fixed_wall_restitution", "object_id": "ball", "wall_object_id": "floor",
            "normal_toward_wall": [0, 0, -1], "contact_time_s": contact, "effective_restitution": 0,
            "incoming_window_s": [.55, .59], "outgoing_window_s": [.61, .65]}
    result = validate_motion_case(case, {"ball": sphere(.2), "floor": box((2, 2, .1))}, rows, [0, 0, -9.81])
    assert result["status"] == "PASSED", result
    assert result["metrics"]["outgoing_normal_m_s"] == 0
    assert result["metrics"]["postimpact_response"] == "supported_inelastic_contact"


def test_event_hash_and_margin_uncertainty_do_not_change_penetration_cap(tmp_path):
    config, rows = make_candidate(tmp_path)
    for spec in config["objects"]:
        spec["collision_margin_m"] = .0005
    # Pair penetration cap is .002m; positive .0025 gap remains in the explicit
    # combined .003m uncertainty envelope without becoming a zero surface gap.
    for row in rows:
        row["objects"]["ball"]["position_m"][2] += .0025
    save_candidate(tmp_path, config, rows)
    event = {"id": "contact-margin", "type": "contact", "time_s": .3, "object_ids": ["ball", "floor"]}
    path = tmp_path/"production_events.json"
    path.write_text(json.dumps([event]))
    report = validate_candidate(tmp_path)
    assert report["inputs"]["production_events.json"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert not any(i["code"] == "spurious_contact" for i in report["issues"])
    measurement = report["metrics"]["event_validation"]["measurements"][0]
    assert measurement["actual_signed_gap_m"] == pytest.approx(.0025)
    assert measurement["geometric_uncertainty_m"] == .003
    assert report["metrics"]["pairs"][0]["penetration_tolerance_m"] == .002
    event["type"] = "near_miss"
    path.write_text(json.dumps([event]))
    assert any(i["code"] == "spurious_near_miss" for i in validate_candidate(tmp_path)["issues"])
    for row in rows:
        row["objects"]["ball"]["position_m"][2] = .199
    save_candidate(tmp_path, config, rows)
    assert any(i["code"] == "spurious_near_miss" for i in validate_candidate(tmp_path)["issues"])
