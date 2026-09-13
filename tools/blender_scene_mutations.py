"""Bounded real-Blender negative-scene audit. Default planning never starts Blender.

Run only when the coordinator has released the serial Blender queue. Mutations
operate on bpy objects in fresh control scenes, before bake (or on saved playback
for the explicit low-rate replay fault). Observed property records are evidence,
not substitutes for independently rejected evaluated trajectories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
VERSION = "actual-blender-scene-mutations-1"
FAULTS = {
    "disabled_floor": {"recipe": "control_drop", "stage": "build", "gate": "geometric_contact", "codes": ["solid_penetration"]},
    "initial_penetration": {"recipe": "control_drop", "stage": "build", "gate": "geometric_contact", "codes": ["solid_penetration"]},
    "kinematic_hover": {"recipe": "control_drop", "stage": "build", "gate": "physical_motion", "codes": ["unsupported_rest", "case_free_flight"]},
    "animated_scale": {"recipe": "control_drop", "stage": "build", "gate": "physical_motion", "codes": ["rigid_scale_drift"]},
    "low_rate_replay": {"recipe": "control_driven", "stage": "replay", "gate": "fresh_process_replay", "codes": ["replay_evidence_mismatch"]},
}
STAGES = ("build", "bake", "replay", "verify-replay", "validate")
NUMERICAL = ("asset_integrity", "geometric_contact", "physical_motion", "fresh_process_replay")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+"\n")


def read(path):
    return json.loads(Path(path).read_text())


def candidate_plan(out, include_low_rate=False):
    plan = [{"name": "baseline_drop", "fault": None, "recipe": "control_drop", "seconds": 1.5}]
    plan += [{"name": name, "fault": name, "recipe": item["recipe"], "seconds": 1.5}
             for name, item in FAULTS.items() if name != "low_rate_replay"]
    if include_low_rate:
        plan += [{"name": "baseline_driven", "fault": None, "recipe": "control_driven", "seconds": 4},
                 {"name": "low_rate_replay", "fault": "low_rate_replay", "recipe": "control_driven", "seconds": 4}]
    return [{**case, "out": str(Path(out)/case["name"])} for case in plan]


def stage_command(repo, case, stage, blender, python=sys.executable):
    helper = Path(repo)/"tools/blender_scene_mutations.py"
    args = [str(helper), "_stage", "--repo", str(repo), "--out", case["out"],
            "--stage", stage, "--recipe", case["recipe"], "--seconds", str(case["seconds"])]
    if case["fault"]:
        args += ["--fault", case["fault"]]
    if stage == "validate":
        return [python, *args]
    return [blender, "--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1",
            "--threads", "2", "--python", str(helper), "--", *args[1:]]


def validate_output(repo, out, *, require_new=True):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    allowed = (repo/"artifacts/blender/revamp").resolve()
    if not out.is_relative_to(allowed) or out == allowed:
        raise ValueError("new audit directory beneath artifacts/blender/revamp required")
    if require_new and out.exists() and any(out.iterdir()):
        raise ValueError("refusing to overwrite an existing audit or candidate")
    return out


def _snapshot(obj):
    rb = obj.rigid_body
    return {"name": obj.name, "location": list(obj.location), "scale": list(obj.scale),
            "rigid_body": None if rb is None else {"type": rb.type, "kinematic": rb.kinematic,
                "collision_shape": rb.collision_shape, "mass": rb.mass},
            "animation_action_present": bool(obj.animation_data and obj.animation_data.action)}


def _curves(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    for layer in obj.animation_data.action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(obj.animation_data.action_slot)
            if bag:
                yield from bag.fcurves


def apply_build_fault(bpy, fault, production):
    """Mutate actual Blender data; declarations keep the intended dynamic role."""
    rid = production["recipe_id"]
    oid = rid+(":floor" if fault == "disabled_floor" else ":ball")
    obj = bpy.data.objects[oid]
    before = _snapshot(obj)
    scene = bpy.context.scene
    scene.frame_set(1)
    if fault == "disabled_floor":
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.rigidbody.object_remove()
        if obj.rigid_body is not None:
            raise RuntimeError("actual floor rigid body was not removed")
        # Explicitly record the observed missing collider. Physical rejection
        # still requires actual penetration in the independently evaluated states.
        next(s for s in production["objects"] if s["object_id"] == oid)["collision_enabled"] = False
    elif fault == "initial_penetration":
        obj.location.z = .10  # Actual radius .25 m; floor top is z=0.
    elif fault == "kinematic_hover":
        obj.rigid_body.kinematic = True
        obj.location.z = 2.
    elif fault == "animated_scale":
        hz = production["physics_hz"]
        for time, value in ((0, 1.), (.15, 1.), (.4, 1.4), (production["duration_s"], 1.4)):
            obj.scale = (value, value, value)
            obj.keyframe_insert(data_path="scale", frame=1+round(time*hz))
        for curve in _curves(obj):
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
        scene.frame_set(1)
    else:
        raise ValueError("unsupported build mutation")
    bpy.context.view_layer.update()
    after = _snapshot(obj)
    return {"object_id": oid, "before": before, "after": after,
            "observed_mutation_applied": before != after,
            "declaration_policy": "production dynamic/passive roles retain the intended baseline; actual faulty bpy properties recorded separately"}


def apply_low_rate_replay(bpy, production, samples):
    oid = "control_driven:carriage"
    obj = bpy.data.objects[oid]
    before = _snapshot(obj)
    original_keys = sum(len(c.keyframe_points) for c in _curves(obj))
    obj.animation_data_clear()
    obj.rotation_mode = "QUATERNION"
    stride = production["physics_hz"]//30
    inserted = 0
    for sample in samples:
        if sample["tick"] % stride:
            continue
        state = sample["objects"][oid]
        obj.location = state["position_m"]
        q = state["quaternion_xyzw"]
        obj.rotation_quaternion = (q[3], *q[:3])
        frame = 1+sample["tick"]/stride
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        inserted += 1
    for curve in _curves(obj):
        for key in curve.keyframe_points:
            key.interpolation = "CONSTANT"
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    actual_curves = list(_curves(obj))
    return {"object_id": oid, "before": before, "after": _snapshot(obj),
            "original_scalar_key_count": original_keys, "new_native_frame_key_times": inserted,
            "interpolation": "CONSTANT", "source_sample_stride": stride,
            "observed_mutation_applied": inserted > 1 and bool(actual_curves) and all(k.interpolation == "CONSTANT" for c in actual_curves for k in c.keyframe_points),
            "declaration_policy": "actual saved Blender playback keys changed; original physics states and declared native clock retained"}


def _record_artifacts(out, production):
    if "lineage" not in production:
        return
    production["lineage"]["artifacts"].update({
        "scene_mutation.json": digest(out/"scene_mutation.json"),
        "generation_source/tools/blender_scene_mutations.py": digest(out/"generation_source/tools/blender_scene_mutations.py"),
        "scene.blend": digest(out/"scene.blend"),
    })
    dump(out/"production.json", production)


def blender_stage(args):
    sys.path.insert(0, str(args.repo))
    if args.stage == "validate":
        from modules.blender.production.validation import validate_candidate
        report = validate_candidate(args.out)
        dump(args.out/"physical-validation.json", report)
        print(json.dumps({"status": report["status"], "issues": report["issues"]}), flush=True)
        return int(report["status"] == "FAILED")
    import bpy
    from modules.blender.production import driver
    from modules.blender.production.common import data_hash
    driver_args = SimpleNamespace(stage=args.stage, out=args.out, recipe=args.recipe, variant="default",
        seconds=args.seconds, physics_hz=240, solver_substeps=10, solver_iterations=60, seed=42,
        profile="diagnostic", camera="beauty", first=1, last=None, parameters=args.out/"parameters.json")
    if args.stage == "build":
        driver.build(driver_args)
        production = read(args.out/"production.json")
        evidence = {"version": VERSION, "fault": args.fault, "scope": "actual Blender scene mutation",
                    "mutator_sha256": digest(__file__), "blender_build_hash": bpy.app.build_hash.decode(),
                    "stage": "baseline" if args.fault is None else FAULTS[args.fault]["stage"],
                    "observed_mutation_applied": False}
        if args.fault and FAULTS[args.fault]["stage"] == "build":
            evidence.update(apply_build_fault(bpy, args.fault, production))
        captured = args.out/"generation_source/tools/blender_scene_mutations.py"
        captured.parent.mkdir(parents=True, exist_ok=True)
        captured.write_bytes(Path(__file__).read_bytes())
        production["scene_fault"] = {"name": args.fault, "mutator_sha256": evidence["mutator_sha256"],
                                     "base_source_fingerprint": production["source_fingerprint"]}
        production["source_fingerprint"] = data_hash(production["scene_fault"])
        dump(args.out/"scene_mutation.json", evidence)
        dump(args.out/"production.json", production)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.out/"simulation.blend"), check_existing=False)
    elif args.stage == "bake":
        driver.bake(driver_args)
    elif args.stage == "replay":
        driver.replay(driver_args)
        production = read(args.out/"production.json")
        if args.fault == "low_rate_replay":
            evidence = read(args.out/"scene_mutation.json")
            samples = [json.loads(s) for s in (args.out/"physics_states.jsonl").read_text().splitlines() if s.strip()]
            evidence.update(apply_low_rate_replay(bpy, production, samples))
            dump(args.out/"scene_mutation.json", evidence)
            bpy.ops.wm.save_as_mainfile(filepath=str(args.out/"scene.blend"), check_existing=False)
        _record_artifacts(args.out, production)
    elif args.stage == "verify-replay":
        driver.verify(driver_args)
    else:
        raise ValueError("unsupported stage")
    return 0


def replay_position_difference(out):
    """Independently compare complete fresh-reopened rows, including failure reports."""
    out = Path(out)
    try:
        report = read(out/"replay_validation.json")
        production = read(out/"production.json")
        wanted = [json.loads(line) for line in (out/"physics_states.jsonl").read_text().splitlines() if line.strip()]
        actual = [json.loads(line) for line in (out/"replay_states.jsonl").read_text().splitlines() if line.strip()]
        count = round(production["duration_s"]*production["physics_hz"])+1
        if report.get("mode") != "fresh_blender_process" or not report.get("fresh_process"):
            raise ValueError("fresh Blender process provenance absent")
        for key, name in (("source_states_sha256", "physics_states.jsonl"),
                          ("replay_states_sha256", "replay_states.jsonl"), ("source_hash", "scene.blend")):
            if report.get(key) != digest(out/name):
                raise ValueError("replay evidence hash mismatch: "+name)
        if len(wanted) != count or len(actual) != count or report.get("samples_checked") != count:
            raise ValueError("incomplete replay clock")
        maximum = 0.
        at = None
        for tick, (a, b) in enumerate(zip(actual, wanted)):
            time = tick/production["physics_hz"]
            if (a["tick"] != tick or b["tick"] != tick or abs(a["time_s"]-time) > 1e-8
                    or abs(b["time_s"]-time) > 1e-8 or set(a["objects"]) != set(b["objects"])):
                raise ValueError("replay clock or participant mismatch")
            for oid, state in b["objects"].items():
                positions = [state["position_m"], a["objects"][oid]["position_m"]]
                if any(len(v) != 3 or not all(math.isfinite(x) for x in v) for v in positions):
                    raise ValueError("invalid replay position")
                delta = math.dist(*positions)
                if delta > maximum:
                    maximum, at = delta, {"tick": tick, "time_s": time, "object_id": oid}
        return {"status": "MISMATCH" if maximum > 1e-5 else "MATCH", "samples_compared": count,
                "maximum_position_error_m": maximum, "tolerance_m": 1e-5, "at": at,
                "inputs": {name: digest(out/name) for name in
                           ("production.json", "physics_states.jsonl", "replay_states.jsonl", "scene.blend", "replay_validation.json")}}
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"status": "UNVERIFIED", "reason": str(error)}


def classify_fault(fault, baseline, candidate, applied, replay_difference=None):
    expected = FAULTS[fault]
    prior = {x["code"] for x in baseline.get("issues", [])}
    new = {x["code"] for x in candidate.get("issues", [])}-prior
    baseline_ok = all(baseline.get("gates", {}).get(g, {}).get("status") == "PASSED" for g in NUMERICAL)
    relevant = bool(new.intersection(expected["codes"])) and candidate.get("gates", {}).get(expected["gate"], {}).get("status") == "FAILED"
    if fault == "low_rate_replay":
        relevant &= bool(replay_difference and replay_difference.get("status") == "MISMATCH")
    return {"status": "DETECTED" if baseline_ok and applied and relevant else "BLOCKED" if not baseline_ok else "NOT_DETECTED",
            "expected_gate": expected["gate"], "expected_new_codes": expected["codes"], "new_issue_codes": sorted(new),
            "actual_mutation_observed": applied, "baseline_numerical_gates_passed": baseline_ok,
            "baseline_full_status": baseline.get("status"), "candidate_full_status": candidate.get("status"),
            "independent_relevant_fault_detected": relevant, "independent_replay_comparison": replay_difference,
            "native_material_calibration_not_credited": True}


def budget(repo, timeout):
    artifact_root = Path(repo)/"artifacts/blender/revamp"
    cumulative = sum(read(p).get("duration_s", 0) for p in artifact_root.rglob("*.job.json"))
    size = sum(p.stat().st_size for p in artifact_root.rglob("*") if p.is_file())
    if cumulative >= 14400 or size >= 20*1024**3 or shutil.disk_usage(repo).free < 3*1024**3:
        raise RuntimeError("existing production compute/artifact/free-space budget exhausted")
    return min(timeout, max(1, int(14400-cumulative)))


def _runtime(repo):
    sys.path.insert(0, str(repo))
    from modules.blender.batch import bounded
    from modules.blender.production.common import source_hashes
    return bounded, source_hashes


def run_audit(repo, out, blender, include_low_rate=False, timeout=1800):
    out = validate_output(repo, out)
    if not 1 <= timeout <= 1800 or not Path(blender).is_file():
        raise ValueError("installed Blender and timeout 1..1800 required")
    bounded, source_hashes = _runtime(repo)
    frozen = source_hashes()
    validator_path = Path(repo)/"modules/blender/production/validation.py"
    validator_hash = digest(validator_path)
    helper_hash = digest(Path(repo)/"tools/blender_scene_mutations.py")
    out.mkdir(parents=True, exist_ok=True)
    (out/"validator_source.py").write_bytes(validator_path.read_bytes())
    if digest(out/"validator_source.py") != validator_hash:
        raise RuntimeError("validator source changed during capture")
    audit = {"version": VERSION, "status": "RUNNING", "approval": None,
             "scope": "actual Blender object mutations, evaluated bake and fresh replay",
             "source_hashes": frozen, "validator_sha256": validator_hash, "mutator_sha256": helper_hash, "cases": [], "blender_jobs_started": 0,
             "remaining_unperformed": ["causal release impulse calibration mutation", "stale-cache replay as a Blender-scene fault", "fabricated-event fault is separately a sidecar/integration case"],
             "limitations": ["Negative tests do not convert the blocked native material calibration into a positive acceptance.",
                             "Scale animation may be ignored by a native rigid-body solver; if so this fault is NOT_DETECTED, never fabricated.",
                             "No render, visual, continuous-motion, audio or human acceptance is performed."]}
    try:
        baselines = {}
        for case in candidate_plan(out, include_low_rate):
            path = Path(case["out"])
            path.mkdir()
            dump(path/"parameters.json", {"native_restitution": 0})
            item = {"name": case["name"], "fault": case["fault"], "candidate": str(path), "jobs": []}
            audit["cases"].append(item)
            stage_failure = None
            for stage in STAGES:
                if (source_hashes() != frozen or digest(Path(repo)/"tools/blender_scene_mutations.py") != helper_hash
                        or digest(validator_path) != validator_hash):
                    raise RuntimeError("production or mutator source changed during audit")
                timeout_now = budget(repo, timeout)
                command = stage_command(repo, case, stage, blender)
                result = bounded(command, path/"jobs"/(stage+".log"), timeout=timeout_now)
                if stage != "validate" and result.get("pid"):
                    audit["blender_jobs_started"] += 1
                item["jobs"].append({"stage": stage, **result})
                dump(out/"audit.json", audit)
                if not result.get("process_group_absent"):
                    raise RuntimeError("owned process group remains; abort further jobs")
                if result["status"] in ("cancelled", "timeout"):
                    raise RuntimeError("owned job "+result["status"]+"; abort further jobs")
                if any(key in result for key in ("error", "cleanup_error", "log_close_error", "evidence_write_error")):
                    raise RuntimeError("job infrastructure failed; abort further jobs")
                if result["status"] != "passed" and stage not in ("verify-replay", "validate"):
                    stage_failure = stage
                    break
            if (path/"physical-validation.json").is_file():
                report = read(path/"physical-validation.json")
                item["validation"] = report
                if not case["fault"]:
                    baselines[case["recipe"]] = report
                    item["outcome"] = {"status": "BASELINE_NUMERICAL_PASSED" if all(report["gates"][g]["status"] == "PASSED" for g in NUMERICAL)
                                       and all(job["status"] == "passed" for job in item["jobs"]) else "BASELINE_FAILED",
                                       "full_status": report["status"]}
                else:
                    mutation = read(path/"scene_mutation.json")
                    replay_difference = replay_position_difference(path) if case["fault"] == "low_rate_replay" else None
                    item["outcome"] = classify_fault(case["fault"], baselines.get(case["recipe"], {}), report,
                                                     mutation.get("observed_mutation_applied", False), replay_difference)
            else:
                item["outcome"] = {"status": "BLOCKED", "reason": "production stage failed before complete evaluated evidence", "stage": stage_failure}
            item["artifacts"] = {str(p.relative_to(path)): {"sha256": digest(p), "size_bytes": p.stat().st_size}
                for p in sorted(path.rglob("*")) if p.is_file() and "jobs" not in p.parts}
            dump(out/"audit.json", audit)
            if not case["fault"] and item["outcome"]["status"] != "BASELINE_NUMERICAL_PASSED":
                raise RuntimeError("control baseline failed applicable numerical gates; no fault credit or further jobs")
        audit["status"] = "PASSED" if all(x["outcome"]["status"] in {"DETECTED", "BASELINE_NUMERICAL_PASSED"} for x in audit["cases"]) else "FAILED"
    except BaseException as exc:
        audit.update(status="FAILED", error=f"{type(exc).__name__}: {exc}")
    finally:
        audit["all_owned_process_groups_absent"] = all(j.get("process_group_absent", False) for c in audit["cases"] for j in c["jobs"])
        if not audit["all_owned_process_groups_absent"]:
            audit["status"] = "FAILED"
        dump(out/"audit.json", audit)
    return audit


def main(argv=None):
    argv = sys.argv[sys.argv.index("--")+1:] if argv is None and "--" in sys.argv else argv
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = sub.add_parser(name)
        command.add_argument("--repo", type=Path, default=ROOT)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--blender", default=os.environ.get("BLENDER_BIN", "/Applications/Blender.app/Contents/MacOS/Blender"))
        command.add_argument("--include-low-rate", action="store_true")
        command.add_argument("--timeout", type=int, default=1800)
    internal = sub.add_parser("_stage")
    internal.add_argument("--repo", type=Path, required=True)
    internal.add_argument("--out", type=Path, required=True)
    internal.add_argument("--stage", choices=STAGES, required=True)
    internal.add_argument("--recipe", choices=("control_drop", "control_driven"), required=True)
    internal.add_argument("--seconds", type=float, required=True)
    internal.add_argument("--fault", choices=FAULTS)
    args = parser.parse_args(argv)
    args.repo = args.repo.resolve()
    if args.command == "_stage":
        args.out = validate_output(args.repo, args.out, require_new=False)
        return blender_stage(args)
    args.out = validate_output(args.repo, args.out)
    if args.command == "plan":
        plan = candidate_plan(args.out, args.include_low_rate)
        print(json.dumps({"status": "NOT_RUN", "blender_jobs_started": 0,
            "cases": [{**c, "commands": [stage_command(args.repo, c, s, args.blender) for s in STAGES]} for c in plan]}, indent=2))
        return 0
    report = run_audit(args.repo, args.out, args.blender, args.include_low_rate, args.timeout)
    print(json.dumps({"status": report["status"], "audit": str(args.out/"audit.json"), "blender_jobs_started": report["blender_jobs_started"]}))
    return int(report["status"] != "PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
