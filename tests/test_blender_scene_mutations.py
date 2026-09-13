"""Wrapper/control-flow tests; these do not claim that Blender faults were run."""
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from tools import blender_scene_mutations as audit


def validation(*, code=None, gate=None, baseline_failure=None):
    gates = {g: {"status": "PASSED"} for g in audit.NUMERICAL}
    gates["solver_calibration"] = {"status": "NOT_RUN"}
    issues = []
    if code:
        gates[gate] = {"status": "FAILED"}
        issues.append({"code": code, "gate": gate})
    if baseline_failure:
        gates[baseline_failure] = {"status": "FAILED"}
    return {"status": "FAILED" if code or baseline_failure else "NOT_RUN", "gates": gates, "issues": issues}


def test_plan_has_no_execution_or_file_creation(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(audit, "run_audit", lambda *a, **k: pytest.fail("plan ran audit"))
    out = tmp_path/"artifacts/blender/revamp/new"
    assert audit.main(["plan", "--repo", str(tmp_path), "--out", str(out), "--include-low-rate"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "NOT_RUN" and data["blender_jobs_started"] == 0
    assert len(data["cases"]) == 7 and not out.exists()
    for case in data["cases"]:
        assert len(case["commands"]) == 5
        for command in case["commands"][:-1]:
            assert command[command.index("--threads")+1] == "2"
            assert "--disable-autoexec" in command and "--background" in command
        assert "--background" not in case["commands"][-1]


def test_output_restricts_scope_and_preserves_existing(tmp_path):
    with pytest.raises(ValueError):
        audit.validate_output(tmp_path, tmp_path/"outside")
    out = tmp_path/"artifacts/blender/revamp/audit"
    out.mkdir(parents=True)
    (out/"evidence.json").write_text("preserve")
    with pytest.raises(ValueError):
        audit.validate_output(tmp_path, out)
    assert (out/"evidence.json").read_text() == "preserve"
    symlink = tmp_path/"artifacts/blender/revamp/link"
    symlink.symlink_to(tmp_path)
    with pytest.raises(ValueError):
        audit.validate_output(tmp_path, symlink/"outside")


def test_fault_credit_requires_new_relevant_gate_and_actual_application():
    good = validation()
    bad = validation(code="solid_penetration", gate="geometric_contact")
    result = audit.classify_fault("disabled_floor", good, bad, True)
    assert result["status"] == "DETECTED" and result["baseline_full_status"] == "NOT_RUN"
    assert result["native_material_calibration_not_credited"]
    assert audit.classify_fault("disabled_floor", good, bad, False)["status"] == "NOT_DETECTED"
    assert audit.classify_fault("disabled_floor", bad, bad, True)["status"] == "BLOCKED"
    metadata_only = validation(code="disabled_consequential_collider", gate="asset_integrity")
    assert audit.classify_fault("disabled_floor", good, metadata_only, True)["status"] == "NOT_DETECTED"
    wrong_gate = validation(code="solid_penetration", gate="asset_integrity")
    assert audit.classify_fault("disabled_floor", good, wrong_gate, True)["status"] == "NOT_DETECTED"


def test_low_rate_needs_independent_complete_trajectory_difference():
    candidate = validation(code="replay_evidence_mismatch", gate="fresh_process_replay")
    assert audit.classify_fault("low_rate_replay", validation(), candidate, True)["status"] == "NOT_DETECTED"
    assert audit.classify_fault("low_rate_replay", validation(), candidate, True,
                                {"status": "UNVERIFIED"})["status"] == "NOT_DETECTED"
    assert audit.classify_fault("low_rate_replay", validation(), candidate, True,
                                {"status": "MISMATCH"})["status"] == "DETECTED"


class Vector(list):
    z = property(lambda s: s[2], lambda s, v: s.__setitem__(2, v))


class Object:
    def __init__(self, name):
        self.name = name
        self.location = Vector([0, 0, 2])
        self.scale = [1, 1, 1]
        self.rigid_body = NS(type="ACTIVE", kinematic=False, collision_shape="SPHERE", mass=1)
        self.animation_data = None
        self.curves = []
        self.inserted = []

    def select_set(self, value):
        self.selected = value

    def keyframe_insert(self, data_path, frame):
        if not self.animation_data:
            bag = NS(fcurves=self.curves)
            action = NS(layers=[NS(strips=[NS(channelbag=lambda slot: bag)])])
            self.animation_data = NS(action=action, action_slot=None)
        self.inserted.append((data_path, frame))
        self.curves.append(NS(keyframe_points=[NS(interpolation="BEZIER")]))

    def animation_data_clear(self):
        self.curves = []
        self.animation_data = None
        self.inserted = []


def fake_bpy():
    ball, floor = Object("control_drop:ball"), Object("control_drop:floor")
    objects = {o.name: o for o in (ball, floor)}
    view = NS(objects=NS(active=None), update=lambda: None)

    def remove():
        view.objects.active.rigid_body = None

    bpy = NS(data=NS(objects=objects), context=NS(scene=NS(frame_set=lambda *a, **k: None), view_layer=view),
             ops=NS(object=NS(select_all=lambda **k: None), rigidbody=NS(object_remove=remove)))
    production = {"recipe_id": "control_drop", "physics_hz": 240, "duration_s": 1.5,
                  "objects": [{"object_id": oid, "mode": "dynamic" if "ball" in oid else "passive"} for oid in objects]}
    return bpy, production


@pytest.mark.parametrize("fault", ["disabled_floor", "initial_penetration", "kinematic_hover", "animated_scale"])
def test_actual_object_mutation_api_is_used(fault):
    bpy, production = fake_bpy()
    result = audit.apply_build_fault(bpy, fault, production)
    ball = bpy.data.objects["control_drop:ball"]
    assert result["observed_mutation_applied"]
    assert production["objects"][0]["mode"] == "dynamic"
    if fault == "disabled_floor":
        assert bpy.data.objects["control_drop:floor"].rigid_body is None
        assert production["objects"][1]["collision_enabled"] is False
    elif fault == "initial_penetration":
        assert ball.location.z == .10
    elif fault == "kinematic_hover":
        assert ball.rigid_body.kinematic and ball.location.z == 2
    else:
        assert ball.inserted == [("scale", 1), ("scale", 37), ("scale", 97), ("scale", 361)]
        assert all(k.interpolation == "LINEAR" for c in ball.curves for k in c.keyframe_points)


def test_low_rate_mutates_real_animation_api_not_input_samples():
    bpy, production = fake_bpy()
    carriage = Object("control_driven:carriage")
    bpy.data.objects[carriage.name] = carriage
    rows = [{"tick": i, "objects": {carriage.name: {"position_m": [i/240, 0, .5],
                                                    "quaternion_xyzw": [0, 0, 0, 1]}}} for i in range(17)]
    original = json.dumps(rows)
    result = audit.apply_low_rate_replay(bpy, production, rows)
    assert json.dumps(rows) == original
    assert result["observed_mutation_applied"] and result["new_native_frame_key_times"] == 3
    assert [frame for kind, frame in carriage.inserted if kind == "location"] == [1, 2, 3]
    assert all(k.interpolation == "CONSTANT" for c in carriage.curves for k in c.keyframe_points)


def replay_fixture(out, *, delta=0):
    out.mkdir(exist_ok=True)
    audit.dump(out/"production.json", {"physics_hz": 240, "duration_s": 2/240})
    rows = [{"tick": i, "time_s": i/240, "objects": {"body": {"position_m": [i/240, 0, 0]}}} for i in range(3)]
    (out/"physics_states.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    rows[1]["objects"]["body"]["position_m"][0] += delta
    (out/"replay_states.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (out/"scene.blend").write_bytes(b"mock only; no Blender run claimed")
    report = {"status": "FAILED" if delta else "PASSED", "mode": "fresh_blender_process", "fresh_process": True,
              "samples_checked": 3, "source_states_sha256": audit.digest(out/"physics_states.jsonl"),
              "replay_states_sha256": audit.digest(out/"replay_states.jsonl"), "source_hash": audit.digest(out/"scene.blend")}
    audit.dump(out/"replay_validation.json", report)
    return report


def test_failure_report_compares_actual_rows_and_rejects_stale_hashes(tmp_path):
    report = replay_fixture(tmp_path, delta=.03)
    result = audit.replay_position_difference(tmp_path)
    assert result["status"] == "MISMATCH" and result["maximum_position_error_m"] == pytest.approx(.03)
    report["replay_states_sha256"] = "stale"
    audit.dump(tmp_path/"replay_validation.json", report)
    assert audit.replay_position_difference(tmp_path)["status"] == "UNVERIFIED"


def test_report_flag_alone_cannot_fabricate_replay_difference(tmp_path):
    report = replay_fixture(tmp_path)
    report["status"] = "FAILED"
    report["max_position_error_m"] = 99
    audit.dump(tmp_path/"replay_validation.json", report)
    assert audit.replay_position_difference(tmp_path)["status"] == "MATCH"
    (tmp_path/"replay_states.jsonl").write_text("")
    assert audit.replay_position_difference(tmp_path)["status"] == "UNVERIFIED"


@pytest.mark.parametrize("failure", ["timeout", "cancelled", "live_group", "infrastructure"])
def test_orchestrator_aborts_further_jobs_and_records_exit_evidence(tmp_path, monkeypatch, failure):
    helper = tmp_path/"tools/blender_scene_mutations.py"
    helper.parent.mkdir()
    helper.write_text("mock mutator")
    validator = tmp_path/"modules/blender/production/validation.py"
    validator.parent.mkdir(parents=True)
    validator.write_text("mock independent validator")
    blender = tmp_path/"mock-blender"
    blender.touch()
    calls = []

    def bounded(command, log, timeout):
        calls.append(command)
        result = {"status": "failed", "pid": 123, "pgid": 123, "process_group_absent": True}
        if failure in ("timeout", "cancelled"):
            result["status"] = failure
        elif failure == "live_group":
            result["process_group_absent"] = False
        else:
            result["evidence_write_error"] = "mock"
        return result

    monkeypatch.setattr(audit, "_runtime", lambda repo: (bounded, lambda: {"mock": "hash"}))
    monkeypatch.setattr(audit, "budget", lambda repo, timeout: timeout)
    result = audit.run_audit(tmp_path, tmp_path/"artifacts/blender/revamp/run", blender)
    assert result["status"] == "FAILED" and len(calls) == 1
    assert result["blender_jobs_started"] == 1
    assert result["all_owned_process_groups_absent"] is (failure != "live_group")
    assert (tmp_path/"artifacts/blender/revamp/run/audit.json").is_file()


def test_expected_verify_failure_continues_to_independent_validation(tmp_path, monkeypatch):
    helper = tmp_path/"tools/blender_scene_mutations.py"
    helper.parent.mkdir()
    helper.write_text("mock mutator")
    validator = tmp_path/"modules/blender/production/validation.py"
    validator.parent.mkdir(parents=True)
    validator.write_text("mock independent validator")
    blender = tmp_path/"mock-blender"
    blender.touch()
    seen = []

    def bounded(command, log, timeout):
        stage = command[command.index("--stage")+1]
        out = Path(command[command.index("--out")+1])
        seen.append(stage)
        if stage == "validate":
            audit.dump(out/"physical-validation.json", validation())
        return {"status": "failed" if stage == "verify-replay" else "passed", "pid": 123,
                "process_group_absent": True}

    monkeypatch.setattr(audit, "_runtime", lambda repo: (bounded, lambda: {"mock": "hash"}))
    monkeypatch.setattr(audit, "budget", lambda repo, timeout: timeout)
    original_plan = audit.candidate_plan
    monkeypatch.setattr(audit, "candidate_plan", lambda out, include: original_plan(out)[:1])
    result = audit.run_audit(tmp_path, tmp_path/"artifacts/blender/revamp/run", blender)
    assert seen == list(audit.STAGES)
    assert result["blender_jobs_started"] == 4
    assert result["cases"][0]["outcome"]["status"] == "BASELINE_FAILED"
    assert result["status"] == "FAILED"
