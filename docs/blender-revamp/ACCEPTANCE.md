# Blender revamp independent acceptance ledger

Authority: the user's implementation instruction and patched DAG 03/05. Canonical
contract 0.1 is unchanged. Numerical checks here do not certify aesthetics,
continuous-motion perception, audio audition or human approval.

Current execution results are in [DELIVERY.md](../../reports/blender-revamp/DELIVERY.md). The initial worker ledger below is retained as provenance; later actual controls and mutation runs are reported separately. Frozen thresholds are unchanged.

## Frozen numerical policy

Policy `production-tolerances-1`, fixed before reading a new production candidate:

- Per collider penetration cap is `min(0.005 m, 0.01 * smallest full collision dimension)`.
  Pair cap is the smaller collider cap. Dimensions below the `1e-5 m` arithmetic
  floor are unsupported, not granted a larger relative tolerance.
- Full world scale drift ≤`1e-5`; quaternion norm error ≤`1e-4`.
- A 0.25 s rest window requires speed ≤0.02 m/s and angular speed ≤0.05 rad/s.
  Geometric support must connect downward to a passive/driven collider. This
  establishes geometric support, not a force/friction-capacity certificate.
- Undisturbed target displacement ≤0.005 m and rotation ≤0.01 rad.
- Contact-free declared free flight: central-difference acceleration residual
  ≤0.5 m/s² relative to specified gravity/forces. Constant horizontal ballistic
  speed is valid. Damped/driven motion must not be annotated as unpowered flight.
- Fresh replay: every audit sample, position residual ≤`1e-5 m`, shortest quaternion
  angle residual ≤`1e-4 rad`, scale residual ≤`1e-5`.
- Analytical fixtures use `1e-8` for closed-form arithmetic only. Their tolerance
  never substitutes for solver calibration. Actual solver calibration is PENDING.

The OBB check uses all 15 normalized separating axes, including cross products;
positive OBB gap is a separating-axis lower bound rather than Euclidean distance.
Negative gap is separating translation depth and correctly detects containment.
Sphere/OBB uses exact point-to-oriented-box signed distance minus radius. Boxes
are evaluated world orientations with local collision dimensions and world scale;
uniform sphere scale is required. This supports evaluated sphere/box colliders,
not arbitrary meshes disguised as primitive metadata.

Each pair is sampled at 240 Hz. Fast intervals with separated endpoints also
check the declared linear relative path; changing orientations use bounded
interior samples (at most 129). Any interior penetration rejects that interpolation
and requests denser actual sampling. No global continuous-time claim follows.
Passive/passive pairs are excluded as joined structure; nondynamic members of
one explicit `collision_group` are also excluded. Dynamic pairs are never excluded
by a group label. All exclusions are listed in each report.

## Production supplements and entrypoints

`modules.blender.production.validation.gap(a_spec,a_state,b_spec,b_state)` returns
signed metres. `validate_candidate(directory)` returns JSON-safe `status`, `gates`,
`metrics`, `issues`, input hashes and limitations. CLI:

```sh
.venv/bin/python -m modules.blender.production.validation PATH_TO_CANDIDATE
```

A failed gate gives exit 1. Missing evidence returns `NOT_RUN`, exit 0; callers
must inspect status, not infer acceptance from process exit. Overall physical
status requires asset integrity, geometry, motion, fresh replay and calibrated
solver evidence. Rendered temporal and perceptual gates remain separately
`NOT_RUN` until their owners run them. Failures override pending dependencies.

Required `production.json`/`physics_states.jsonl` fields match the coordinator's
`reports/blender-revamp/EXECUTION.md` interchange. Samples must include all
colliders, every integer tick and the audit right endpoint. World scale must be
explicit. `collision_enabled:false` is rejected. Optional fields:

- `require_settled_end:true` enforces supported, slow final dynamic bodies. Use for
  hero/control/catalogue endpoints; leave false only for diagnostic clips that
  intentionally finish in motion. Unsupported stationary intervals ≥0.25 s fail
  regardless of that flag.
- `lineage:{source_fingerprint,bake_source_fingerprint,states_sha256,artifacts}`.
  Source fingerprints equal the production source fingerprint. `artifacts` maps
  candidate-relative paths to exact SHA-256, including the saved `.blend` files.
  Missing lineage is pending; stale hashes/fingerprints fail.
- `validation_cases:[...]` selects independently justified intervals. Supported
  kinds: `free_flight`, `stable_target`, `supported_rest`, `release`, `near_miss`.
  Use `object_id` or `object_ids`, optional `start_s/end_s`. Free flight defaults
  to declared gravity. A kinematic `release` needs `release_time_s` and independently
  expected `expected_velocity_m_s` (default tolerance 0.1 m/s); do not invent a
  kinematic handoff for the always-dynamic mechanically launched hero. Identify
  its last paddle contact, ensuing separation and free-flight window instead.
- Optional `production_events.json`: list or `{events:[...]}` with
  `{id,type,time_s,object_ids:[a,b]}`. Contact/impact/Foley requires surface proximity
  within ±1 audit tick; near miss requires positive gap beyond numerical tolerance.
  These are geometry checks, not impulse or audio measurements. Missing event
  supplement is explicitly reported.

`replay_validation.json` requires `status:"PASSED"`,
`mode:"fresh_blender_process"`, `source_states_sha256`, `samples_checked` equal to
the complete audit count, `max_position_error_m`, `max_rotation_error_rad`, and
`max_scale_error` within frozen limits. The coordinator must generate it by
independently reopening the finalized actual asset; this reader cannot attest
that a report came from Blender merely because it says so.

`solver_calibration.json` requires `source_mode:"blender_controls"`, passing
`status`, nonempty `controls` (each `status:"PASSED"` meaning correct classification,
including expected rejection for negative controls), `convergence:{status:"PASSED",...}`,
`solver` equal to the production solver settings and nonempty `artifacts` mapping
paths to SHA-256. Paths resolve from the candidate; sibling control bundles may
be referenced. All hashes are recomputed. Reports preserve measured values,
thresholds, run commands and source identities; a truthy flag alone is insufficient.

The independent `check_rendered_cadence` interface consumes decoded PTS, expected
fps/count, decoded image hashes and explicitly expected moving frames. Wrong
cadence/count or duplicate images during expected motion fail. Static endings
may legitimately repeat frames. Without decoded hashes and motion windows,
status remains pending. Actual FFmpeg decoding is the production owner's task.

## Actual checks and pending Blender controls

Executed in `/private/tmp/scenescore-revamp-validation` using the primary `.venv`:

```sh
/Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest modules/blender/tests/production -q
/Users/agent/Desktop/SceneScore/.venv/bin/python -m ruff check modules/blender/production/validation.py modules/blender/tests/production
```

Result: **46 tests passed**; Ruff passed. The supplied analytical reference is
copied into the owned tests unchanged: nine positives accepted and nine negatives
rejected. Additional independent controls cover full 3D skew rods requiring a
cross-product SAT axis, contained solids, oriented sphere contact, rotation and
translation invariance, fast crossings, corner near miss, scale and support.

The actual historical sidecar was read with pinned SHA-256
`a5b02fe89fee3728babf8a5b76b5583356006e9ebcfebed0bac1d62ca193a3ab`.
New solid geometry independently rejects tower-0/tower-1 overlap
**0.533744693 m at 20.28125 s**. Final towers and projectile have no support path
to the frozen source-audited floor at z=-1.1 m; projectile clearance is 1.6 m.
This is actual frozen export evidence, not a fresh historical Blender inspection.
Absent historical input skips explicitly rather than inventing a passing run.

Blender-dependent regression-scene ledger (all **NOT_RUN by this worker**):

| Control | Independent expected observation | Failure mutation |
|---|---|---|
| Drop/bounce | z follows gravity before contact; measured normal restitution thereafter | Held/frozen fall; wrong restitution |
| Stable contact/stack | Supported initial/rest state, no spontaneous target motion | Disable ground; unsupported hold |
| Rotated solids | Full OBB separation/penetration, invariant rigid shape | Rotate into overlap; scale parent |
| Fast pass-through | Actual high-rate trajectory catches crossing | Keyframe through thin solid |
| Mechanical release | Paddle contact transfers motion; continuous ball motion after separation | Remove launch impulse/release speed |
| Tower impact | Contact precedes response/support loss; launch-disabled stack stable | Scheduled collapse without contact |
| Matched miss | Positive ball-target gap and stable target; valid ground contacts separate | Fake target contact/Foley |
| Fresh cache/replay | Source settings and motion hashes agree across new process | Reuse stale bake |
| Native rendered cadence | Decode every 30 fps frame; motion present at source cadence | Duplicate low-rate images |

These failures already have synthetic pipeline unit checks; production-output
and actual Blender-scene mutation execution is **PENDING** and must be recorded
separately. Real runs may expose missing checks and require narrow follow-up.

Freeze calibration before judging the hero: run controls at the baseline solver,
then raise Bullet substeps/iterations while keeping 240 Hz extraction fixed;
compare contact times, penetration and resting drift. Independently increase
extraction rate on fast/marginal contacts so sample density is not mistaken for
solver accuracy. Publish measured convergence and retain each candidate/cache.
Do not loosen thresholds after a failed hero. Report exact pair, time interval,
actual value, tolerance, hashes and minimal repair. Isolated momentum/energy
checks require an explicitly isolated system; supported targets and floors
exchange external impulse, and zero projectile recoil may be physically valid.
