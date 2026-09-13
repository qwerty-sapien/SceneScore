# Directions 06 / 08 — mechanics handoff

Machine checks: **GO**. Independent source review by `/root/gate` found no remaining
mechanical blocker after the unilateral receiver, support and refinement fixes.
Human visual review and evaluated Blender replay remain **NOT_RUN** by this worker.
The integrator owns the actual 240 Hz Blender evaluation and fresh 30 fps replay.

## Exact integration boundary

Worktree: `/private/tmp/scenescore-directions-rolling`, base `a397f3f`.
Copy only these owned files; no commit or merge was made:

- `modules/blender/production/directions/rolling.py`
- `modules/blender/tests/directions/test_rolling.py`
- `handoffs/directions-rolling.md`

Final source SHA256:
`917ba072dd29f420d8e27de7666667364c1293853fc9005bf0a9db3c8c121427`

Final test SHA256:
`b5d0e6dd945c28635f72fb743d51048e349cdc382f1b4d4b80bb5fd6414546c2`

One coordination message mistakenly called this source hash pre-unilateral.
That message was corrected: the hash above is the reviewed final unilateral
source, verified by both worker and reviewer.

## API and rendering

`build_direction(identifier, hz=240, substeps=8) -> dict`, identifiers `06` / `08`.
Each packet contains `id`, `title`, `duration_s=30`, `hz`, `backend`, `seed=42`,
`actors`, `geometry`, `states`, `events`, `validation`, and `camera`.
There are exactly `30*hz+1` output states, including both endpoints. Each state
contains integer `tick`, `time_s=tick/hz`, and every actor's `position_m`,
`quaternion_xyzw`, `scale`, and `velocity_m_s`. Body states additionally expose
velocity, energy, support/reaction, receiver force, gap, compression and contact
status. Coil/plunger motion is derived from the actual receiver compression.

06 has nine actors: sphere, cylinder, finite torus hoop and their three plunger /
coil pairs. 08 has three: bead plus plunger / coil. Static geometry contains the
actual track surfaces, walls, load-bearing posts/caps, grounded base, receiver
backstops, and (08) supported stationary central orb and top capture rail.

Cylinder and torus local Z becomes the world Y axle. Hoop outer radius is .24 m,
tube radius .025 m; its finite-torus inertia ratio is
`((.24-.025)**2 + .75*.025**2)/.24**2`, matching the rendered torus.
The bead is `zero_spin=true`, `material='glow'`: its physical sphere inertia is
.4 mr², but there is zero rotational energy and no rolling coupling. Do not add
an orientation stripe that suggests rolling.

Coils use `shape='coil'`, local X, `deformable=true`; local X scale is physical
spring length. Preserve the supplied narrow radii / half extents, particularly
inside the hoop's narrow guide. Mesh vertices are world coordinates with zero
object translation. Root may add causal electrical checkpoint lamps from events.

## Declared mechanics and story adaptations

These are ideal constrained guide models, not Bullet contact simulations.
The physical generalized coordinate is integrated using analytic path derivatives
and RK4. Neither positions nor event times are authored against the movie clock.
Physical course parameters determine timings; there is no retiming.

06 has an identical low-loss initial slope, then three different planar profiles
and lengths. There is no yaw steering. The support surface is the exact radius
offset of the center path; angular speed is signed arc speed / radius. With
`k=I/(mr²)`, `(1+k)*a = -g*t_z - c*v - F_receiver`. The declared viscoelastic
rolling torque rises from zero after the initial metre to `-0.3*r*v` N m.
Static contact friction is `-k*a-c*v`, checked against the .8 static coefficient.
Normal support is `g*n_z + curvature_normal*v²`. The banked detour, elevated
crossovers and mechanical finish flag become distinct planar profiles and causal
checkpoint indicators. This retains a three-body inertia race without unsupported
hoop steering.

08 is a polished sliding bead in a visible fitted groove. Its upper spiral,
descending crossover, opposite lower spiral and central receiver chute join C2.
There is no attractive central force, unsupported jump, or inferred 3D rolling.
Guide forces pass through the center and do zero work. The narrow 7 cm top strip
at `p+r*n`, supported by sparse transverse braces, supplies the measured downward
reaction; it is physically required and must not be removed for camera visibility.
The open sides of the view leave most of the .48 m bead visible. The scripted
short drop / bowl become supported continuous guide segments.

Receivers are unilateral massless Kelvin–Voigt plungers. During contact,
`F=K*c+C*c_dot >= 0`; when that force reaches zero the body separates and the
plunger retracts independently via `c_dot=-K*c/C`. A gap crossing may cause a
recontact. Every force/gap crossing is bisected within the integration step; no
body projection, tensile force, latch, magnetic capture or pose freeze is used.
The spring energy is `.5*K*c²`, and the dashpot sink is integrated as `C*c_dot²`,
including detached plunger retraction. 06 uses K=8 N/m, C=1.3 N s/m; 08 uses
K=32 N/m, C=5 N s/m. Visible coil, plunger and backstop agree with this model.

## Actual 240 Hz, eight-substep evidence

| Measurement | 06 | 08 |
|---|---:|---:|
| Equal-slope exits | 7.204 / 7.458 / 8.196 s | — |
| Receiver arrivals | 14.579 / 15.138 / 16.475 s | 22.750 s |
| Outer / crossover / lower completed | — | 20.008 / 20.717 / 22.396 s |
| Last speed above .01 m/s, latest body | 29.942 s | 28.725 s |
| Max energy residual | 1.53e-13 J | 1.21e-5 J |
| Minimum floor reaction | 9.5564 N | -33.5423 N; supplied by top capture |
| Maximum total guide reaction | 9.9503 N | 126.366 N |
| Max required static coefficient | .13690 | frictionless sliding |
| Maximum receiver compression | .41825 m | .76590 m |
| Receiver contact episodes | 2 / 3 / 3 | 3 |
| Worst receiver gap numerical error | 1.42e-11 m | 1.07e-10 m |
| Maximum output displacement / radius | .02002 | .12843 |
| Maximum guide work | 4.45e-16 W | 1.28e-13 W |

Initial mechanical energies are 21.582 J for each race body and 32.373 J for
the bead. Dissipated energies at 30 s are 2.07961 / 2.21205 / 2.34437 J and
27.37654 J respectively. Final body speeds are .000444 / -.000570 / -.008790 m/s
and .0002895 m/s. Small residual natural motion is retained.

The sampled full guide envelope has a positive minimum local offset Jacobian
.1372, including the 4 cm deck and capture braces. The nonlocal centerline minimum
is .74146 m; the test reserves the full guide footprint plus bead radius and a
margin. Minimum bead-to-central-orb center distance is 1.39987 m versus .72 m
combined radii. Sloped support caps join posts to the deck; every 240 Hz body row
is checked against posts with a whole output-step travel margin.

## Checks actually run

- `PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest modules/blender/tests/directions/test_rolling.py -q`
  — **15 passed in 37.57 s**, final source.
- `/Users/agent/Desktop/SceneScore/.venv/bin/ruff check modules/blender/production/directions/rolling.py modules/blender/tests/directions/test_rolling.py`
  — **all checks passed**.
- `git diff --check` — passed.
- Separate actual 240 Hz / eight-substep packet generation printed the measurements
  above; all commands exited successfully.

The tests independently derive constant-ramp acceleration, rotational friction
and energy; include a no-slope negative motion control; check C2 joins and local
offset regularity; verify nonlocal/orb/post clearance; prove receiver separation,
positive force/gap, retraction and dissipation; and compare the actual 240 Hz
eight-versus-sixteen-substep output for **every** actor position, velocity,
quaternion, coil extent, ordered event identity and event time. Position tolerance
is .2 mm, velocity tolerance 1 mm/s, angular tolerance .002 rad, extent tolerance
.2 mm, and event timing tolerance one 240 Hz tick. Deterministic repeat passes.

Earlier diagnostic failures were corrected, not waived: terminal-speed creeping,
unrepresented bilateral receiver tension, sharp/folded crossover offsets,
axis-aligned post intrusion, and unbisected receiver arrival refinement error.

## Resource teardown

No Blender process, server, browser, dependency install or detached job was started.
All task-owned diagnostic, test and lint sessions returned an exit code, including
final pytest session 89001, Ruff 17189 and metric generation 22977. No task-owned
persistent process remains. Root integration, renderer review, evaluated Blender
sampling and fresh replay acceptance remain separate required gates.
