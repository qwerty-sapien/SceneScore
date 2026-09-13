"""Closed-form independent expectations for the calibration measurement helper."""
import copy
from pathlib import Path

import pytest

from modules.blender.production.calibration import (
    POLICY,
    compare_resolution,
    derive_calibration,
    measure_drop,
    measure_transfer,
    velocity,
)


def state(x, z=.2):
    return {"position_m": [x, 0, z], "quaternion_xyzw": [0, 0, 0, 1], "scale": [1, 1, 1]}


def config():
    return {"objects": [
        {"object_id": "test:floor", "shape": "box", "half_extents_m": [10, 10, .1], "mode": "passive", "friction": 0, "linear_damping": 0, "restitution": 0},
        *[{"object_id": "test:"+name, "shape": "sphere", "radius_m": .2, "mode": "dynamic", "friction": 0, "linear_damping": 0, "restitution": 0, "mass_kg": 1} for name in ["left", "right"]]],
        "gravity_m_s2": [0, 0, -9.81], "physics_hz": 240, "duration_s": 1,
        "solver": {"substeps_per_frame": 10, "solver_iterations": 60},
        "config": {"physics_hz": 240, "solver_substeps": 10, "solver_iterations": 60}}


def transfer_rows(outgoing=(1, 1)):
    rows = []
    for tick in range(241):
        time = tick/240
        if time < .4:
            left, right = -1.2+2*time, 0
        else:
            left, right = -.4+outgoing[0]*(time-.4), outgoing[1]*(time-.4)
        rows.append({"tick": tick, "time_s": time, "objects": {"test:floor": state(0, -.1), "test:left": state(left), "test:right": state(right)}})
    return rows


def test_perfectly_inelastic_transfer_momentum_and_energy():
    report = measure_transfer(config(), transfer_rows())
    assert report["status"] == "PASSED", report
    assert report["incoming_normal_m_s"] == pytest.approx([2, 0])
    assert report["outgoing_normal_m_s"] == pytest.approx([1, 1])
    assert report["kinetic_energy_before_j"] == pytest.approx(2)
    assert report["kinetic_energy_after_j"] == pytest.approx(1)
    assert report["momentum_residual_kg_m_s"] < 1e-10


@pytest.mark.parametrize("outgoing", [(0, 0), (.94, 1.06), (-1, 3)])
def test_transfer_rejects_missing_momentum_nonzero_restitution_and_energy_creation(outgoing):
    assert measure_transfer(config(), transfer_rows(outgoing))["status"] == "FAILED"


def test_velocity_fit_does_not_read_advertised_velocity():
    rows = transfer_rows()
    for row in rows:
        row["objects"]["test:left"]["velocity_m_s"] = [999, 999, 999]
    assert velocity(rows, "test:left", [.1, .3]) == pytest.approx([2, 0, 0], abs=1e-12)


def test_transfer_refuses_gravity_or_friction_confounded_momentum_boundary():
    conf = config()
    conf["objects"][0]["friction"] = .5
    with pytest.raises(ValueError, match="frictionless"):
        measure_transfer(conf, transfer_rows())


def test_matched_solver_comparison_rejects_actual_trajectory_difference():
    conf = config()
    rows = transfer_rows()
    a = {"config": conf, "rows": rows, "measurements": measure_transfer(conf, rows)}
    b = copy.deepcopy(a)
    b["config"]["solver"]["substeps_per_frame"] = 20
    b["config"]["config"]["solver_substeps"] = 20
    good = compare_resolution(a, b)
    assert good["status"] == "PASSED", good
    b["rows"][-1]["objects"]["test:right"]["position_m"][0] += .1
    bad = compare_resolution(a, b)
    assert bad["status"] == "FAILED"
    assert bad["maximum_position_difference_m"] == pytest.approx(.1)
    assert bad["position_tolerance_m"] == POLICY["trajectory_convergence_m"] == .005


def test_solver_comparison_refuses_changed_geometry_or_sampling():
    conf, rows = config(), transfer_rows()
    a = {"config": conf, "rows": rows, "measurements": measure_transfer(conf, rows)}
    b = copy.deepcopy(a)
    b["config"]["solver"]["substeps_per_frame"] = 20
    b["config"]["objects"][1]["radius_m"] = .25
    assert compare_resolution(a, b)["status"] == "FAILED"


def test_drop_zero_restitution_measures_supported_rest():
    conf = config()
    conf["objects"] = conf["objects"][:2]
    rows = []
    start_height = .2+.5*9.81*.6**2
    for tick in range(241):
        t = tick/240
        rows.append({"tick": tick, "time_s": t, "objects": {"test:floor": state(0, -.1), "test:left": state(0, max(.2, start_height-.5*9.81*t*t))}})
    result = measure_drop(conf, rows)
    assert result["status"] == "PASSED", result
    assert result["response"]["metrics"]["outgoing_normal_m_s"] == 0


def test_missing_actual_controls_fail_without_fabricating_pass(tmp_path):
    r = derive_calibration(*(tmp_path/name for name in ["a", "b", "c", "d"]), output_directory=tmp_path)
    assert r["status"] == "FAILED"
    assert all(c["status"] == "FAILED" for c in r["controls"])
    assert r["artifacts"] == {}
    assert r["solver"] is None
    assert not list(tmp_path.iterdir())
    assert Path(__file__).is_file()
