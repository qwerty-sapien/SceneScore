# Directions 06 / 08 — mechanics handoff

The mechanics trace remains unchanged. The original evaluated 08 skin failed an
independent triangle audit; the adaptive geometry repair and its separate gates
are recorded below. The integrator owns fresh Blender evaluation and replay.

## Exact integration boundary

Worktree: `/private/tmp/scenescore-directions-rolling`, base `a397f3f`.
Copy only these owned files; no commit or merge was made:

- `modules/blender/production/directions/rolling.py`
- `modules/blender/tests/directions/test_rolling.py`
- `handoffs/directions-rolling.md`

Final source SHA256:
`5d8741f0116ded2c628461a08efffd4ae81a9267795e62fc4b3a5ea337f054fa`

Final test SHA256:
`17ca8f153a4fb3c741354e274d11da7cdb01cedec43fd78c596edc989bc9e333`

The initial mechanics source was `917ba072...c121427`. It is retained only as
historical provenance; integrate the complete current source identified above.

## Adaptive geometry repair: current candidate

Raw packet: `/private/tmp/rolling-skin-v5-08.json`, SHA256
`80fa90ba477c25610176377ad315b0e8737de5633b60ad4f988ca6cb11ea4b53`.
Independent raw facet gate: **PASSED**. Fresh evaluated Blender gate and media
review: **NOT_RUN for this repaired 08 candidate**. The separately frozen 06
movie is rendering from its previously evaluated root snapshot; this handoff
does not replace that artifact or its provenance.

The V1 evaluated left-wall triangle intruded 31.015 mm at approximately 20.470 s.
Checking smooth centerline support and mesh vertices did not detect the long
diagonal through a twisted wall quad. The first adaptive raw repair removed that
large defect, but the unchanged linear interpolation between two 240 Hz samples
still produced 0.227643 mm capture-rail overlap. That failed the 0.2 mm gate.
Both rejected witnesses are preserved as negative controls; no threshold changed.

The current repair:

- Uses 4,759 stations chosen from world arc bounds, frame turn, analytic
  centerline chord bounds, observed surface chord error, and triangle-plane
  error, including cross-profile twist. Parameter sampling is adaptive.
- Emits explicit triangles for every contact skin. It divides the floor across
  its contact centerline, replaces tall wall quads with 36 mm high contact bands,
  and gives those bands 24 mm outward thickness. Uprights and feet stay outside
  the contact surface. The 70 mm wide roof strip has 25 mm outward thickness and
  receives its braces from outside, so flat braces do not touch the bead.
- Names the side skins `<course>-left-contact-rail` / `-right-contact-rail`,
  bypassing the root renderer's older `-guide-left` / `-guide-right` replacement.
  Render these source triangles unchanged; do not apply that old conversion.
- Records an explicit **60 micrometre outward contact-skin allowance**, approved
  as a finite mesh/replay proxy tolerance. It does not enter any dynamics or
  change the 0.2 mm independent intrusion limit. The allowance is not spent on
  coarser contact facets.
- Retains a <=19.995 micrometre analytic centerline-to-chord bound, <=24.935
  micrometre observed surface chord error, and <=29.993 micrometre observed
  contact triangle-plane error. The second-derivative bound uses the exact
  cubic Bernstein hull for quintic pieces and analytic spiral/ramp bounds.
  These local tessellation checks complement the independent full-facet audit;
  they are not a substitute for it.

All body, plunger, coil, velocity, orientation, energy and contact rows, plus all
events, remain byte-identical under canonical JSON serialization. Baseline hashes:

| Direction | States SHA256 | Events SHA256 |
|---|---|---|
| 06 | `6d4463bb50a08448d3a737847a659f5cc84d14d6cef617d654e43560b486b233` | `a24d23d30f40c4f03a800aee6df3c2e7513c16f19fe085d005bb4a4487d0d145` |
| 08 | `338562a90757e83476e82b26fd2d1919e7a6906976a0ec8d5582df58442a9f81` | `5ee8f5ee58f08d07ccda5c8a8f0e027c7c3e91411282b5f5d9f7880dee99d819` |

The isolated worker launches no Blender process. Geometry tests additionally
round candidate vertices to float32 and check both the 31 mm evaluated witness
and the narrower 0.228 mm replay-chord witness against the fixed 0.2 mm limit.

Independent `/root/gate` result for this exact raw packet:

- All 7,201 sampled centers: guide gaps at least **+0.039296 mm**.
- All 7,200 swept replay intervals: worst intrusion **0.168644 mm**, including
  an additional **1 micrometre radius reserve**, below the unchanged 0.2 mm limit.
- Worst case: capture-rail face 54542 at 22.623056516 s.
- All remaining static shapes: swept clearance at least **23.856793 mm**;
  no shapes omitted, including outward uprights, feet and braces.
- Exact state/event equality to the V1 packet independently verified.
- Report: `/Users/agent/Desktop/SceneScore/reports/animation-directions-06-08-18/gate-evaluated/RAW-08-repaired-v5.json`.
- The first complete-audit attempt exceeded its 150 s runtime cap under concurrent
  rendering; the same calculation completed in 257.009 s under a 300 s cap.
  No geometric threshold or sample count changed. This raw audit does not replace
  the integrator's subsequent actual evaluated-mesh audit.

Final repair checks actually run:

- Full `pytest modules/blender/tests/directions/test_rolling.py -q` on the strict
  60 micrometre source: **19 passed in 639.83 s** under concurrent rendering.
- Then the second preserved witness was added; focused
  `pytest modules/blender/tests/directions/test_rolling.py -q -k evaluated_skin_failure`:
  **2 passed, 18 deselected in 106.94 s**. The current file has 20 cases; the
  unchanged cases were covered by the full run and both witness cases by this run.
- Final Ruff and `git diff --check`: passed.
- State/event byte regressions passed for both 06 and 08.

All worker-owned repair jobs exited: final raw generation session 59441,
full tests 28210, witness tests 26988, and final lint 91003. Earlier raw generations
and the superseded strictness experiment also exited. No Blender, server or
persistent process was started by this worker.

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

## Initial mechanics checks actually run

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
