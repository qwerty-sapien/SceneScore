"""Synthetic exact trajectories challenge certificates; not Blender validation."""
import copy
import hashlib
import json
import math

import pytest

from modules.blender.production import contact_intervals as ci
from modules.blender.tests.production.test_backend_calibration import analytic_fixture


@pytest.mark.parametrize("e", [1, .55])
def test_fast_between_tick_bounce_has_independent_root_and_response(e):
    conf, rows, _ = analytic_fixture(e)
    for row in rows:
        row["objects"]["bounce:ball"].update(contacts=[], velocity_m_s=[999, 999, 999])
    r = ci.detect_contact_intervals(conf, rows)
    assert len(r["contacts"]) == 1, r
    c = r["contacts"][0]
    assert c["numerical_status"] == "PASSED"
    assert c["validated"] is False
    assert c["physical_time_estimate_s"] == pytest.approx(math.sqrt(3.5/9.81), abs=1e-9)
    assert c["effective_restitution_measured"] == pytest.approx(e, abs=1e-9)
    assert c["time_uncertainty_s"] == pytest.approx(1/240)
    assert c["confirmation_time_s"] > c["time_interval_s"][1]
    assert len(c["pre_fit"]["ticks"]) >= 3 and len(c["post_fit"]["ticks"]) >= 3
    assert c["combined_fit_max_position_residual_m"] < 1e-12
    assert len(c["pre_fit"]["source_rows_sha256"]) == 64


def test_oriented_box_uses_face_normal_not_world_vertical():
    conf, rows, _ = analytic_fixture(.55)
    angle = math.pi/6
    n = [math.sin(angle), 0, math.cos(angle)]
    conf["objects"][0]["half_extents_m"] = [5, 5, .1]
    hit = math.sqrt(3.5/(9.81*n[2]))
    p0 = [2*v for v in n]
    incoming = [0, 0, -9.81*hit]
    vn = sum(a*b for a, b in zip(incoming, n))
    outgoing = [v-1.55*vn*a for v, a in zip(incoming, n)]
    point = [p0[0], 0, p0[2]-.5*9.81*hit*hit]
    for row in rows:
        t = row["time_s"]
        floor = row["objects"]["bounce:floor"]
        floor["position_m"] = [-.1*v for v in n]
        floor["quaternion_xyzw"] = [0, math.sin(angle/2), 0, math.cos(angle/2)]
        p = [p0[0], 0, p0[2]-.5*9.81*t*t] if t <= hit else [point[0]+outgoing[0]*(t-hit), 0, point[2]+outgoing[2]*(t-hit)-.5*9.81*(t-hit)**2]
        row["objects"]["bounce:ball"]["position_m"] = p
    result = ci.detect_contact_intervals(conf, rows)
    assert len(result["contacts"]) == 1, result
    c = result["contacts"][0]
    assert c["outward_normal"] == pytest.approx(n, abs=1e-10)
    assert c["physical_time_estimate_s"] == pytest.approx(hit, abs=1e-9)
    assert c["effective_restitution_measured"] == pytest.approx(.55, abs=1e-9)


@pytest.mark.parametrize("mutation", ["teleport", "wrong_material", "no_surface", "multiple", "edge"])
def test_unexplained_contact_claims_are_withheld(mutation):
    conf, rows, _ = analytic_fixture(.55)
    if mutation == "wrong_material":
        conf["objects"][1]["restitution"] = 1
    if mutation == "no_surface":
        for row in rows:
            row["objects"]["bounce:floor"]["position_m"][2] -= 10
    if mutation == "teleport":
        for row in rows:
            if row["time_s"] > math.sqrt(3.5/9.81):
                row["objects"]["bounce:ball"]["position_m"][0] += .01
    if mutation == "multiple":
        other = copy.deepcopy(conf["objects"][0])
        other["object_id"] = "bounce:second_floor"
        conf["objects"].append(other)
        for row in rows:
            row["objects"][other["object_id"]] = copy.deepcopy(row["objects"]["bounce:floor"])
    if mutation == "edge":
        for row in rows:
            row["objects"]["bounce:ball"]["position_m"][0] = 5
    result = ci.detect_contact_intervals(conf, rows)
    assert result["contacts"] == [], result
    assert result["unverified"]
    assert all(item["time_estimate_s"] is None for item in result["unverified"])


def test_sustained_rest_after_impact_is_not_a_ballistic_rebound_certificate():
    conf, rows, _ = analytic_fixture(0)
    for row in rows:
        row["objects"]["bounce:ball"]["position_m"][2] = max(.25, 2-.5*9.81*row["time_s"]**2)
    result = ci.detect_contact_intervals(conf, rows)
    assert result["contacts"] == []
    assert any("insufficient" in reason for item in result["unverified"] for reason in item["reasons"])


def test_fixed_scope_rejects_moving_collider_or_native_backend():
    conf, rows, _ = analytic_fixture()
    rows[-1]["objects"]["bounce:floor"]["position_m"][0] += .01
    with pytest.raises(ValueError, match="static"):
        ci.detect_contact_intervals(conf, rows)
    conf["motion_mode"] = "Bullet dynamics"
    with pytest.raises(ValueError, match="only"):
        ci.detect_contact_intervals(conf, rows)


def test_fits_ignore_advertised_derivatives_and_reject_curved_nonballistic_motion():
    conf, rows, _ = analytic_fixture()
    window = rows[30:35]
    fit = ci.fit_ballistic(window, "bounce:ball", conf["gravity_m_s2"])
    assert fit["max_position_residual_m"] < 1e-12
    window[2]["objects"]["bounce:ball"]["position_m"][0] += .01
    fit = ci.fit_ballistic(window, "bounce:ball", conf["gravity_m_s2"])
    assert fit["max_position_residual_m"] > ci.POLICY["fit_position_residual_m"]


def test_claimed_physical_pass_does_not_override_independent_failed_candidate(tmp_path, monkeypatch):
    conf, rows, _ = analytic_fixture()
    (tmp_path/"production.json").write_text(json.dumps(conf))
    (tmp_path/"physics_states.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows))
    (tmp_path/"physical-validation.json").write_text(json.dumps({"status": "PASSED"}))
    monkeypatch.setattr(ci, "validate_candidate", lambda _: {"status": "FAILED", "issues": [{"code": "stale_bake"}], "gates": {}})
    result = ci.certify_candidate(tmp_path)
    assert result["status"] == "UNVERIFIED_PHYSICAL_CANDIDATE"
    assert result["contacts"] and all(c["validated"] is False for c in result["contacts"])
    assert result["source_hashes"]["physics_states.jsonl"] == hashlib.sha256((tmp_path/"physics_states.jsonl").read_bytes()).hexdigest()


def release_fixture():
    conf, _, _ = analytic_fixture(.55)
    conf["duration_s"] = .6
    conf["objects"][0]["half_extents_m"] = [1, 1, .02]
    departure = .40317
    rows = []
    for tick in range(145):
        t = tick/240
        rows.append({"tick": tick, "time_s": t, "objects": {
            "bounce:floor": {"position_m": [-1, 0, -.02], "quaternion_xyzw": [0, 0, 0, 1], "scale": [1, 1, 1]},
            "bounce:ball": {"position_m": [2*(t-departure), 0, .25 if t <= departure else .25-.5*9.81*(t-departure)**2],
                            "quaternion_xyzw": [0, 0, 0, 1], "scale": [1, 1, 1]}}})
    return conf, rows, departure


def test_supported_release_uses_separate_measured_windows_and_gravity():
    conf, rows, departure = release_fixture()
    result = ci.detect_supported_releases(conf, rows)
    assert len(result["releases"]) == 1, result
    release = result["releases"][0]
    assert release["physical_time_estimate_s"] == pytest.approx(departure, abs=1e-9)
    assert release["position_continuity_m"] < 1e-10
    assert release["velocity_continuity_m_s"] < 1e-9
    assert release["post_flight_gravity_residual_m_s2"] < 1e-9
    assert release["time_uncertainty_s"] == 1/240
    pre, post = release["pre_support_fit"], release["post_flight_fit"]
    assert max(pre["ticks"]) < min(post["ticks"])
    assert "gravity_m_s2" not in pre
    assert pre["measured_acceleration_m_s2"] == pytest.approx([0, 0, 0], abs=1e-9)
    assert post["gravity_m_s2"] == conf["gravity_m_s2"]
    assert pre["source_rows_sha256"] != post["source_rows_sha256"]
    assert release["validated"] is False
    assert "no independent launcher impulse" in release["not_checked"]


@pytest.mark.parametrize("mutation", ["position_jump", "velocity_jump", "lost_velocity", "no_gravity"])
def test_release_continuity_rejects_unexplained_trajectory_change(mutation):
    conf, rows, departure = release_fixture()
    for row in rows:
        if row["time_s"] <= departure:
            continue
        p = row["objects"]["bounce:ball"]["position_m"]
        if mutation == "position_jump":
            p[0] += .01
        elif mutation == "velocity_jump":
            p[0] += row["time_s"]-departure
        elif mutation == "lost_velocity":
            p[0] = 0
        elif mutation == "no_gravity":
            p[2] = .25
    result = ci.detect_supported_releases(conf, rows)
    assert result["releases"] == [], result
    assert result["unverified_releases"]
    assert all(r["physical_time_estimate_s"] is None for r in result["unverified_releases"])


def test_simultaneous_support_cannot_claim_unique_release_owner():
    conf, rows, _ = release_fixture()
    support = copy.deepcopy(conf["objects"][0])
    support["object_id"] = "bounce:second_support"
    conf["objects"].append(support)
    for row in rows:
        row["objects"][support["object_id"]] = copy.deepcopy(row["objects"]["bounce:floor"])
    result = ci.detect_supported_releases(conf, rows)
    assert result["releases"] == []
    assert any("multiple prior supports" in reason for r in result["unverified_releases"] for reason in r["reasons"])


def test_supported_release_marker_needs_full_physical_gate(tmp_path, monkeypatch):
    conf, rows, _ = release_fixture()
    (tmp_path/"production.json").write_text(json.dumps(conf))
    (tmp_path/"physics_states.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows))
    monkeypatch.setattr(ci, "validate_candidate", lambda _: {"status": "NOT_RUN", "issues": [], "gates": {}})
    result = ci.certify_candidate(tmp_path)
    assert result["status"] == "UNVERIFIED_PHYSICAL_CANDIDATE"
    assert len(result["releases"]) == 1
    assert result["releases"][0]["validated"] is False
    assert result["releases"][0]["id"] == "supported-release-0000"
    assert result["coverage"]["certified_releases"] == 1
