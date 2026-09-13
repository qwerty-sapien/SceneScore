# Actual Blender negative-scene audit

Prepared implementation; **actual Blender execution NOT_RUN at handoff**. These
focused wrapper tests are mock/API tests and cannot establish real physics fault
detection. The coordinator owns serial job authorization and the final audit run.
No production driver or independent validator source is edited by this helper.

Run from the live repository, after copying the owned helper and tests:

```sh
.venv/bin/python tools/blender_scene_mutations.py plan --out artifacts/blender/revamp/blender-scene-mutations-1 --include-low-rate
.venv/bin/python tools/blender_scene_mutations.py run --out artifacts/blender/revamp/blender-scene-mutations-1 --include-low-rate --timeout 1800
```

`plan` emits all commands and creates no files or processes. `run` refuses an
existing nonempty output and requires a directory beneath the revamp artifact
root. It builds fresh native e=0 `control_drop` and prescribed `control_driven`
baselines; no prior candidate is copied or modified. The command uses the current
installed Blender path unless `--blender`/`BLENDER_BIN` explicitly supplies it.

| Actual mutation | Required new independent evidence | Scope |
| --- | --- | --- |
| Remove the floor rigid body with `bpy.ops.rigidbody.object_remove` | `solid_penetration` from evaluated ball/floor states | A recorded `collision_enabled:false` alone receives no credit. |
| Set the initial actual sphere centre to z=0.10 m, radius 0.25 m | `solid_penetration` | Fresh initial condition is saved before bake. |
| Set the actual ball rigid body to kinematic while its intended role remains dynamic | `unsupported_rest` or failed free flight | Actual properties and intended declaration are both preserved. |
| Add real uniform scale F-curves from 1.0 to 1.4 | `rigid_scale_drift` | If Blender ignores the animation, report `NOT_DETECTED`; do not manufacture states. |
| Replace actual playback carriage F-curves with 30 Hz constant keys | Failed fresh replay plus independently measured complete trajectory mismatch | Original 240 Hz physical samples remain intact. Not an actual low-rate simulation claim. |

Every case calls the existing build, bake, replay and fresh verify operations
through the wrapper. Each build mutation occurs on real `bpy` objects before the
simulation is saved and baked. The optional replay fault occurs on actual saved
playback keys after a valid bake/reopen. Evaluated states come from the driver;
the helper never substitutes synthetic `physics_states.jsonl` trajectories.

The saved `scene_mutation.json` records actual before/after properties. Production
lineage binds the mutator source and fault identity to the original source
fingerprint, then binds the saved simulation, playback, bake, mutator and mutation
record. The audit freezes/captures the independent validator source and records
hashes of every candidate artifact. Production and validator source changes stop
further jobs. Source capture describes provenance; it does not imply acceptance.

A baseline must pass asset, geometry, motion and fresh replay gates and all its
commands must succeed. The native material calibration may remain `NOT_RUN` and
is never waived or credited as a positive pass. A fault is `DETECTED` only when
its mutation was observed and its expected independent gate reports a new
relevant error absent from the corresponding baseline. A generic inherited
calibration failure, metadata-only failure, or changed status flag is insufficient.
For the replay fault, the helper independently compares the complete hashed
fresh-reopened state file with the physics state file even when Blender's
verification report already says `FAILED`.

`audit.json` reports all commands, PID/PGID, job outcomes and verified group exit.
All five child operations, including independent validation, use the existing
bounded runner. Blender receives `--threads 2`, `--disable-autoexec` and an
individual limit at or below 1,800 seconds. Jobs run serially. Before each child,
the helper checks the existing revamp cumulative four-hour compute and 20 GiB
artifact limits plus 3 GiB free space. With both controls and five faults, the
maximum planned work is **28 Blender child jobs and seven validation jobs**.
Cancellation, timeout or evidence/cleanup failure aborts subsequent jobs. A
normal fault-driven verify failure preserves its files and continues to independent
validation. The overall audit passes only if both baselines and all requested
fault detections pass; `approval` remains null.

This audit does **not** claim causal launcher/release impulse mutation coverage,
actual stale-cache replay mutation coverage, fabricated-event Blender fault
coverage, renders, continuous-motion review, audio validation or human approval.
Those coverage gaps remain explicit beside the separate sidecar mutation audit.
It does not turn blocked native material calibration into an accepted hero.

Preparation verification, actually run in the separate worktree:

```sh
/Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest -q tests/test_blender_scene_mutations.py
/Users/agent/Desktop/SceneScore/.venv/bin/ruff check tools/blender_scene_mutations.py tests/test_blender_scene_mutations.py
```

The focused tests cover safe planning/output scope, actual object API mutations,
strict differential classification, complete replay comparison, source/evidence
handling and cancellation/cleanup control flow. No Blender process is launched by
these tests. Final actual execution results belong in the generated audit.
