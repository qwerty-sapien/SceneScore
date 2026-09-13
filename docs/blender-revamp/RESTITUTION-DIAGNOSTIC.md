# Restitution diagnostic — installed Blender 5.2.1 LTS

Status: **cause strongly evidenced; no supported Blender RNA configuration fix verified**.
No production files, acceptance criteria, vendor source or caches were changed.
Investigation began 2026-09-12 17:58 UTC and was bounded to ten minutes.

## Finding

The missing bounce is consistent with Bullet solving a contact while the sphere
still has a positive geometric gap. The solver subtracts `gap / timestep` from
the restitution velocity target. Increasing simulation frequency changes which
positive gap is encountered first, so a stored restitution of 1 does not preserve
the measured outgoing speed in this setup. This explanation predicts both the
480 Hz and 960 Hz results to the precision of the exported states.

Setting restitution after `bpy.ops.rigidbody.object_add()` is not an evidenced
initialization bug: the installed revision's RNA setter updates both the stored
value and an existing physics body. Body creation copies the stored value into a
new Bullet object. Existing build and bake stages already use separate Blender
processes. See matching-build [RNA setter](https://github.com/blender/blender/blob/9e2066aef7ef/source/blender/makesrna/intern/rna_rigidbody.cc#L296)
and [body creation](https://github.com/blender/blender/blob/9e2066aef7ef/source/blender/blenkernel/intern/rigidbody.cc).

## Independent observations

A fresh read-only Blender process opened `bounce-base/simulation.blend` and
`bounce-split960/simulation.blend` beneath `artifacts/blender/revamp/controls`.
Both stored ball and floor restitution as 1. Ball: ACTIVE, enabled, nonkinematic,
unit object scale, diameter approximately 0.5 m, zero linear/angular damping,
deactivation disabled. Floor: PASSIVE, enabled, unit scale, dimensions 14×8×0.3 m.
Both margins were 0.0005 m. Gravity was approximately −9.81 m/s² and time scale 1.
Both files had baked caches. Base was 240 fps / 10 substeps / 60 iterations;
split960 was 960 fps / 1 substep / 60 iterations, split impulse enabled.

The binary reported build `9e2066aef7ef`, version `5.2.1 LTS`. Exact command and
probe output: `/private/tmp/scenescore-restitution-properties.job.json` and
`/private/tmp/scenescore-restitution-properties.log`. It used background,
factory-startup, disabled autoexec, two threads and a 60-second limit; no frame
advancement, rebake or save occurred. PID/PGID **24350**, exit 0, elapsed **1.089 s**,
owned process group verified absent.

Separately, existing `physics_states.jsonl` files were read with Python. The table
uses adjacent exported position differences, not an unavailable direct Bullet
velocity API. Each first response begins at scene time 0.595833333 s:

| Candidate | Gap at response start (m) | Incoming speed (m/s) | Outgoing displacement velocity (m/s) |
|---|---:|---:|---:|
| bounce-single, 240 Hz × 1 | −0.003537759 | 5.845123529 | 6.014939547 |
| bounce-split240, 240 Hz × 1 | −0.003537759 | 5.845123529 | 6.014939547 |
| bounce-split480, 480 Hz × 1 | +0.002550900 | 5.845127106 | 4.620695114 |
| bounce-split960, 960 Hz × 1 | +0.005595237 | 5.845127106 | 0.473699570 |

For 480 Hz, `5.845127106 − 0.00255089998 × 480 = 4.620695114`.
For 960 Hz, `5.845127106 − 0.00559523702 × 960 = 0.473699570`.
The 240 Hz penetrating case instead matches the positional ERP term:
`5.845123529 + 0.00353775918 × 0.2 × 240 = 6.014935970`, within
0.000004 m/s of the observed finite-difference velocity.

The base 240 Hz × 10 run first slows while the exported gap is still +0.007422 m,
then reaches supported rest without a rebound. Its output averages ten internal
substeps, so the single-step formula above is not applied to that averaged row.

## Matching-build source mechanism

The exact binary revision was read from primary Blender sources using system
curl with ordinary TLS verification. No downloaded source was executed.
Python urllib first failed local certificate verification; security checks were
not disabled. System curl then fetched the relevant files successfully.

- The [sphere-box algorithm](https://github.com/blender/blender/blob/9e2066aef7ef/extern/bullet2/src/BulletCollision/CollisionDispatch/btSphereBoxCollisionAlgorithm.cpp#L66)
  permits a contact within the manifold's contact-breaking distance, including
  positive separation.
- The [constraint solver](https://github.com/blender/blender/blob/9e2066aef7ef/extern/bullet2/src/BulletDynamics/ConstraintSolver/btSequentialImpulseConstraintSolver.cpp#L953)
  subtracts positive distance divided by the step duration from the velocity
  target. For negative distance it adds positional correction. This provides the
  quantitative predictions above; it is stronger evidence than a flag check.
- The [solver defaults](https://github.com/blender/blender/blob/9e2066aef7ef/extern/bullet2/src/BulletDynamics/ConstraintSolver/btContactSolverInfo.h#L96)
  set split-impulse penetration threshold to −0.04 and restitution velocity
  threshold to 0.2. Thus merely enabling split impulse does not route this
  roughly 3.54 mm penetration through the split branch. The saved RNA inventory
  exposes the boolean but neither numeric threshold.

## Uniform unit scaling is not a verified remedy

The matching-build [dispatcher](https://github.com/blender/blender/blob/9e2066aef7ef/extern/bullet2/src/BulletCollision/CollisionDispatch/btCollisionDispatcher.cpp#L32)
defaults to relative contact-breaking thresholds. Its manifold threshold uses the
minimum of the two shapes' thresholds. The [shape implementation](https://github.com/blender/blender/blob/9e2066aef7ef/extern/bullet2/src/BulletCollision/CollisionShapes/btCollisionShape.cpp#L42)
multiplies the default threshold by the shape's angular-motion radius.
The matching-build [Blender wrapper](https://github.com/blender/blender/blob/9e2066aef7ef/intern/rigidbody/rb_bullet_api.cpp)
contains no dispatcher-flag override.

Consequently, uniformly enlarging geometry by 1000 also enlarges this contact
region by 1000. On conversion back to metres it does not generally become a
0.00002 m region. Scaling would change the interpretation of the *absolute*
split-impulse and low-speed restitution thresholds, but must not be presented as
a known repair for the positive-gap loss. Any such trial must pass the unchanged
physical and units-invariance gates; this diagnostic did not perform that trial.

## Minimal actionable disposition

Do not spend another repair on resetting restitution, raising iteration count,
or assuming that more substeps or unit scaling repairs this contact behavior.
Keep the current controls failed. Preserve the animation clock and metre-based
acceptance tolerances.

The relevant low-level contact-processing and solver thresholds are absent from
the installed `RigidBodyWorld` and `RigidBodyObject` RNA inventories. No supported
configuration-only fix was established in this bounded investigation. A change
to contact handling, collision representation or backend needs independently
reviewed implementation and fresh controls; it cannot be claimed equivalent from
flags alone. No ctypes access, unreviewed vendor patch or replacement simulator
was attempted. This is an honest production blocker until a candidate passes the
existing gates, not permission to relax them.

## Authorized follow-up: transparent fixed-obstacle sphere mechanics

A later coordinator assignment authorized a scoped alternative for the staircase
and isolated high-bounce control. `modules/blender/production/analytic.py` now
implements `simulate_sphere(...)` as **fixed-obb-sphere-mechanics-1**. This does
not change or repair native Bullet, and the original unsupported elastic-Bullet
control remains failed.

The function accepts an SI sphere state, fixed oriented boxes and a duration
that has an integral number of output ticks. It returns tick-zero through the
exact endpoint, including position/velocity, normalized orientation quaternion,
world angular velocity and contact indices. The default output rate is 240 Hz
with 32 constant internal substeps; 64 is the independent resolution comparison.
All bodies are represented in metres and seconds. The fixed-obstacle equations
use unit mass because mass cancels from the sphere's motion in this model.

Free-flight segments integrate constant gravity exactly. Newly crossed box
surfaces are located by bisection on that segment before an impulse is applied.
Sphere/OBB distance and normals include box rotation and contained centres; deep
initial overlap is rejected instead of corrected by a teleport. Motion that
exceeds radius/4 per internal step fails closed, as does an unresolved step with
more than twelve impacts. This bounded discrete collision search is not claimed
to certify arbitrary extreme grazing trajectories or moving-solid coupling.

Restitution combines the two declared coefficients by multiplication. Coulomb
friction caps the contact impulse and uses solid-sphere inertia `I=2/5 mr²` for
translation/rotation coupling. Supported rolling resistance is an explicit
`rolling_resistance` argument, default **0.02**, implemented as a bounded angular
impulse opposing rolling spin. It only removes energy. The integrator must
record this argument, restitution/friction coefficients, 240 Hz, substeps and
model/source hashes in production provenance, even when defaults are used.

A supported contact removes only its inward gravity component. To terminate the
inelastic infinite-bounce limit at finite numerical resolution, supported normal
speeds no larger than `|g| / (hz * substeps)` are removed; actual outward elastic
rebounds are preserved. This numerical settling rule and the scale-aware
micrometre correction bound are explicit model limitations, not hidden easing.

`contacts` at tick N is the union of obstacles touched during the preceding
output interval; tick zero describes initial contact. A one-tick interval is
therefore the contact-time uncertainty unless a separate exact-event export is
added. This prevents a short between-tick impact from disappearing from output.
Every physically consequential floor, step, ramp, wall and backstop must be
included. An initial smoke without a backstop correctly left the finite floor;
a subsequent fixed-backstop case visited the ramp, all four steps, floor and
backstop and reached supported rest.

Independent tests in `modules/blender/tests/test_analytic_sphere.py` import no
recipe or production-validator functions. They compare freefall and elastic
bounce against closed-form equations, test restitution products, derive the
solid-sphere friction impulse and its Coulomb cap independently, test a rotated
plane's normal impulse and energy, verify rolling resistance dissipates energy,
and exercise missing-floor, containment and excessive-speed negative cases.
They also check quaternion norms, immutable inputs, exact tick/end counts,
32/64-substep convergence and an eight-second staircase/backstop case. The
staircase smoke before the final contact-reporting refinement measured maximum
paired position distance **0.0004371 m**, with terminal difference **2.25e-9 m**;
those smoke measurements are not substitutes for the production candidate gate.

Executed focused command:

```sh
/Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest \
  modules/blender/tests/test_analytic_sphere.py -q
```

The initial twelve tests passed in 1.66 s. The final thirteen-test suite passed
in **24.56 s**; Ruff and `git diff --check` also passed. No Blender job, external simulator, vendor patch or acceptance
change was performed for this alternative. Source implementation alone does not
approve its eventual production replay or visual result; the coordinator must
run the existing independent physical, replay, geometry and cadence gates.
