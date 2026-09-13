"""Independent formulas and scope mutations; synthetic tests are not Blender proof."""
import copy
import json
import math
from pathlib import Path

import pytest

from modules.blender.production.backend_calibration import (
    ANALYTIC, DRIVEN, compare_mechanics, derive_analytic_calibration,
    derive_driven_calibration, measure_bounce, measure_driven_control,
    verify_analytic_scope, verify_driven_scope,
)
from modules.blender.production.validation import _calibration_scope_matches


def pose(x=0, z=0):
    return {"position_m": [x, 0, z], "quaternion_xyzw": [0, 0, 0, 1], "scale": [1, 1, 1]}


def analytic_fixture(e=1):
    conf = {"recipe_id": "bounce", "objects": [
        {"object_id": "bounce:floor", "mode": "passive", "shape": "box", "half_extents_m": [5, 5, .1], "restitution": 1},
        {"object_id": "bounce:ball", "mode": "dynamic", "shape": "sphere", "radius_m": .25, "restitution": e,
         "friction": 0, "mass_kg": 1, "rolling_resistance": .02, "motion_backend": ANALYTIC, "blender_kinematic_replay": True}],
        "duration_s": 1, "physics_hz": 240, "gravity_m_s2": [0, 0, -9.81], "motion_mode": ANALYTIC,
        "mechanics": {"model_version": ANALYTIC, "substeps": 32, "rolling_resistance": .02},
        "config": {"parameters": {"analytic_substeps": 32}},
        "code_hashes": {"modules/blender/production/analytic.py": "modelhash"}}
    hit = math.sqrt(2*1.75/9.81)
    rows = []
    for tick in range(241):
        t = tick/240
        z = 2-.5*9.81*t*t if t <= hit else .25+e*9.81*hit*(t-hit)-.5*9.81*(t-hit)**2
        rows.append({"tick": tick, "time_s": t, "objects": {"bounce:floor": pose(z=-.1), "bounce:ball": pose(z=z)}})
    tracks = {"bounce:ball": {"obstacle_ids": ["bounce:floor"], "samples": [dict(tick=r["tick"], time_s=r["time_s"], **r["objects"]["bounce:ball"]) for r in rows]}}
    return conf, rows, tracks


@pytest.mark.parametrize("e", [1, .55])
def test_exact_bounce_matches_gravity_response_and_energy(e):
    conf, rows, tracks = analytic_fixture(e)
    result = measure_bounce(conf, rows, e)
    assert result["status"] == "PASSED", result
    assert result["outgoing_speed_m_s"] == pytest.approx(e*result["incoming_speed_m_s"], abs=1e-10)
    assert result["kinetic_energy_at_impact_after_j"] == pytest.approx(e*e*result["kinetic_energy_at_impact_before_j"], abs=1e-10)
    assert verify_analytic_scope(conf, rows, tracks)["model_position_error_m"] == 0


def test_advertised_pass_and_velocity_do_not_hide_wrong_bounce():
    conf, rows, _ = analytic_fixture(.4)
    conf["objects"][1]["restitution"] = .55
    conf["status"] = "PASSED"
    for row in rows:
        row["objects"]["bounce:ball"]["velocity_m_s"] = [0, 0, 999]
    assert measure_bounce(conf, rows, .55)["status"] == "FAILED"


@pytest.mark.parametrize("mutation", ["native", "second_body", "moving_support", "missing_collider", "stale_track", "mass", "resolution"])
def test_analytic_scope_rejects_unsupported_or_changed_inputs(mutation):
    conf, rows, tracks = analytic_fixture()
    if mutation == "native":
        conf["motion_mode"] = "Bullet dynamics"
    elif mutation == "second_body":
        conf["objects"][0]["mode"] = "dynamic"
    elif mutation == "moving_support":
        rows[-1]["objects"]["bounce:floor"]["position_m"][0] = .01
    elif mutation == "missing_collider":
        tracks["bounce:ball"]["obstacle_ids"] = []
    elif mutation == "stale_track":
        rows[-1]["objects"]["bounce:ball"] = pose(z=99)
    elif mutation == "mass":
        conf["objects"][1]["mass_kg"] = 2
    elif mutation == "resolution":
        conf["mechanics"]["substeps"] = 64
    with pytest.raises(ValueError):
        verify_analytic_scope(conf, rows, tracks)


def test_mechanics_resolution_is_independent_of_bullet_and_sampling():
    conf, rows, _ = analytic_fixture()
    a = {"config": conf, "rows": rows}
    b = copy.deepcopy(a)
    # Changing Bullet resolution alone cannot establish analytic convergence.
    b["config"]["solver"] = {"substeps_per_frame": 999}
    assert compare_mechanics(a, b)["status"] == "FAILED"
    b["config"]["mechanics"]["substeps"] = 64
    b["config"]["config"]["parameters"]["analytic_substeps"] = 64
    assert compare_mechanics(a, b)["status"] == "PASSED"
    b["rows"][-1]["objects"]["bounce:ball"]["position_m"][0] += .006
    assert compare_mechanics(a, b)["status"] == "FAILED"


def driven_fixture():
    conf = {"recipe_id": "control_driven", "duration_s": 4, "physics_hz": 240,
            "mechanics": None, "code_hashes": {"modules/blender/production/scenes.py": "sourcehash"},
            "objects": [{"object_id": "control_driven:carriage", "mode": "driven", "shape": "box", "half_extents_m": [.25, .25, .2]},
                        {"object_id": "control_driven:rail", "mode": "passive", "shape": "box", "half_extents_m": [2, .4, .15]}]}
    rows = [{"tick": i, "time_s": i/240, "objects": {"control_driven:rail": pose(z=.15),
             "control_driven:carriage": pose(x=max(-1, min(1, i/240-2)), z=.5)}} for i in range(961)]
    return conf, rows


def test_known_driven_positions_velocity_and_stationary_windows():
    conf, rows = driven_fixture()
    assert verify_driven_scope(conf, rows)["dynamic_actor_count"] == 0
    result = measure_driven_control(conf, rows)
    assert result["status"] == "PASSED"
    assert result["measured_active_velocity_m_s"] == pytest.approx([1, 0, 0], abs=1e-10)


def test_driven_control_rejects_low_rate_duplicates_even_with_correct_endpoints():
    conf, rows = driven_fixture()
    for row in rows:
        row["objects"]["control_driven:carriage"]["position_m"][0] = max(-1, min(1, math.floor(row["time_s"]*30)/30-2))
    assert measure_driven_control(conf, rows)["status"] == "FAILED"


def test_driven_does_not_waive_dynamic_or_analytic_calibration():
    conf, rows = driven_fixture()
    conf["objects"][0]["mode"] = "dynamic"
    with pytest.raises(ValueError, match="no dynamic"):
        verify_driven_scope(conf, rows)
    conf["objects"][0]["mode"] = "driven"
    conf["mechanics"] = {"model_version": ANALYTIC}
    with pytest.raises(ValueError):
        verify_driven_scope(conf, rows)


def test_matching_irrelevant_bullet_solver_cannot_bless_analytic_candidate(tmp_path):
    conf, _, _ = analytic_fixture()
    conf["solver"] = {"substeps_per_frame": 10}
    assert not _calibration_scope_matches({"solver": conf["solver"]}, conf, {}, tmp_path)


def test_backend_report_is_bound_to_exact_candidate_and_model_bytes(tmp_path):
    conf, _, _ = analytic_fixture()
    (tmp_path/"mechanics_states.json").write_text("{}")
    from modules.blender.production.calibration import digest
    inputs = {"production.json": "p", "physics_states.jsonl": "s"}
    report = {"version": "scoped-backend-calibration-1", "backend": ANALYTIC,
              "physics_hz": 240, "mechanics": conf["mechanics"], "model_source_sha256": "modelhash",
              "candidate_inputs": {**inputs, "mechanics_states.json": digest(tmp_path/"mechanics_states.json")}}
    assert _calibration_scope_matches(report, conf, inputs, tmp_path)
    assert not _calibration_scope_matches(report, conf, {**inputs, "physics_states.jsonl": "changed"}, tmp_path)
    report["model_source_sha256"] = "changed"
    assert not _calibration_scope_matches(report, conf, inputs, tmp_path)


def test_missing_actual_controls_do_not_create_a_pass_or_write_files(tmp_path):
    result = derive_analytic_calibration(*([tmp_path/"missing"]*6), output_directory=tmp_path)
    assert result["status"] == "FAILED"
    assert result["candidate_inputs"] == {}
    assert result["artifacts"] == {}
    assert all(x["status"] == "FAILED" for x in result["controls"])
    result = derive_driven_calibration(tmp_path/"missing", tmp_path/"missing")
    assert result["status"] == "FAILED"
    assert result["backend"] == DRIVEN
    assert list(tmp_path.iterdir()) == []
    assert json.loads(json.dumps(result))["status"] == "FAILED"
    assert Path(__file__).is_file()


def test_calibration_derivation_does_not_consume_installed_report(tmp_path):
    from modules.blender.tests.production.test_validation import make_candidate
    from modules.blender.production.validation import validate_candidate
    make_candidate(tmp_path)
    (tmp_path/"solver_calibration.json").write_text(json.dumps({"status": "FAILED"}))
    assert validate_candidate(tmp_path)["gates"]["solver_calibration"]["status"] == "FAILED"
    result = validate_candidate(tmp_path, check_calibration=False)
    assert result["gates"]["solver_calibration"]["status"] == "NOT_RUN"
    assert result["gates"]["physical_motion"]["status"] == "PASSED"


def test_native_inelastic_report_does_not_certify_other_material(tmp_path):
    conf = {"objects": [{"mode": "dynamic", "restitution": 0}], "motion_mode": "Bullet dynamics",
            "solver": {"substeps_per_frame": 10}, "physics_hz": 240}
    report = {"version": "bullet-inelastic-calibration-1", "scope": {"native_material_restitution": 0},
              "solver": conf["solver"], "physics_hz": 240}
    assert _calibration_scope_matches(report, conf, {}, tmp_path)
    conf["objects"][0]["restitution"] = 1
    assert not _calibration_scope_matches(report, conf, {}, tmp_path)
    conf["objects"][0]["restitution"] = 0
    report["backend"] = DRIVEN
    assert not _calibration_scope_matches(report, conf, {}, tmp_path)
