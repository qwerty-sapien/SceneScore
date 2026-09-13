# 04 — Crossing Orbits: authoring source plan

`status: DESIGN_INTENT_NOT_MEASURED` · `id: 04_crossing_orbits` · `seed: 404271` · `duration_s: 10.2` · `clock: scene_seconds_zero_at_start` · `render: 9:16, 30 fps (proxy 540×960; final 1080×1920)`

This is a construction plan only. It uses an original two-route composition and the supplied reference notes' lesson of legible elevation and curved routing; it is not a recreated reference or a validated bake.

## Declared mechanics

- **Model:** `native_bullet`, proposed model version `native-bullet-two-sphere-curved-rail-1`, 240 Hz. Both heroes are active rigid spheres on passive segmented curved channels. Sphere B is retained by a visibly actuated, kinematic latch until its planned release; all other travel surfaces are fixed.
- **Scope boundary:** A4 certifies exactly one dynamic sphere against fixed OBBs, so it cannot certify this two-active-body candidate. Historical native controls also failed calibration. A candidate-specific native material/convergence calibration, a pairwise swept positive-gap certificate, replay, and visual review are prerequisites—not statuses this plan asserts.
- **World/solver:** gravity `(0, 0, -9.81) m/s²`; candidate substeps `50`, solver iterations `20`, collision margin `0.0015 m`; use 100 substeps only for the predeclared comparison. Sphere-to-sphere collision remains enabled: the plan succeeds only if geometry and timing maintain a positive gap, not if a collision mask hides a contact.
- **Materials/mechanics:** both radii `0.155 m`; A mass `0.43 kg`, cobalt glass-ceramic finish, friction `0.33`; B mass `0.47 kg`, warm orange matte ceramic finish, friction `0.36`; all restitutions `0.00`. White ceramic rails have friction `0.42`; steel supports/latch have friction `0.30`. The B-latch retracts along its own rail normal from `t=2.10–2.28`, with an exposed brass crank; it must not give the sphere a scripted velocity.

## Actors, spatial route, and palette

| ID | role and motion | collision/visual identity |
| --- | --- | --- |
| `orbit-sphere-a` | hero actor, dynamic, scored | cobalt blue, `voice:orbit-a` |
| `orbit-sphere-b` | hero actor, dynamic, scored | burnt orange, `voice:orbit-b` |
| `route-a` / `route-b` | silent supports, passive | independent white ceramic segmented curved channels with dark-blue undersides |
| `b-release-latch` | visible actuator, kinematic/driven | short brass fork, crank, and bracket; collision stays enabled through release |
| `catch-a` / `catch-b` | silent supports, passive | separate low graphite/ceramic catching trays |
| `orbit-frame` | silent support, passive | slim charcoal lattice, deliberately set behind the paths |

Routes cross in view but occupy distinct 3D offsets. Sphere-centre anchors (metres) are proposed design targets:

| actor/time | anchor | route meaning |
| --- | --- | --- |
| A 0.00 | `(-2.65, -1.15, 3.82)` | immediate release from the upper-left cradle |
| A 2.00 | `(-1.40, -0.55, 3.08)` | first descending curve, foreground-left |
| A 4.54 | `(-0.06, 0.02, 2.10)` | crossing side of the near miss |
| A 6.00 | `(1.25, 0.70, 1.28)` | diverging lower-right curve |
| A 7.55 | `(2.10, 1.20, 0.72)` | own catch tray |
| B 2.10 | `(2.35, -1.70, 3.36)` | retained right-rear cradle, then latch release |
| B 3.30 | `(1.25, -0.95, 2.80)` | descending curve into the shared visual volume |
| B 4.58 | `(0.26, 0.26, 2.14)` | closest planned companion position |
| B 6.00 | `(-1.20, 0.86, 1.30)` | diverging lower-left curve |
| B 8.05 | `(-2.15, 1.30, 0.72)` | own catch tray |

The planned closest centre separation is about `0.370 m`; with `0.310 m` summed radii this targets a visible `0.060 m` surface gap. Curves must preserve that vertical/depth offset at entry and exit, rather than using two coplanar splines. The frame and trays establish at least three elevation levels while keeping both balls uncluttered at the centre.

## Camera and event contract

Use a single elevated wide convergence composition: `52 mm`, camera `(8.5, -10.8, 8.2)`, target `(0.0, 0.0, 2.05)`. A modest 4% dolly-in from `t=2.5–5.2` is permitted; no pan/cut over the near miss. Keep A, B, both rails, and both final trays visible at the crossing. Key from camera-left, cool fill from high rear, soft shadows on a charcoal floor.

| window | salient event and physical cause | required measurement / falsifier |
| --- | --- | --- |
| 2.10–2.28 | `b-mechanical-release`: the driven fork withdraws and sphere B becomes gravity-driven from rest while A is already in flight. | B must be supported before release and unsupported afterwards; its post-release position/velocity must come from the solver. Fail if B moves before latch withdrawal, is spawned late, or receives a transform/velocity impulse. |
| 4.40–4.72 | `crossing-near-miss`: the two independently dynamic trajectories enter the same visual volume, pass with offset, then separate. | Pairwise swept surface gap across `4.20–4.95 s`: min `0.045 m`, max `0.080 m`, target `0.060 m`; no contact in that interval or outside a declared contact exception (none exists). Fail if either sphere is offscreen at closest approach, collision filtering is used, or the interval is inferred from centre points alone. |
| 7.55–8.35 | `dual-supported-ending`: each sphere independently reaches its own passive tray and remains visible as the paired orbit resolves. | Both trays must show physical contact; each terminal linear speed ≤`0.030 m/s` and angular speed ≤`0.080 rad/s` for ≥`1.2 s`. Fail if the bodies touch each other, share a final pile, leave the frame, or are forced still. |

The initial A release is the scene's starting condition, not a delayed empty beat. The three salient windows are separated by at least `1.0 s`; duty is `1.25/10.2 = 12.3%`. Rail rolling remains continuous support evidence rather than a stream of artificial collision beats.

## Construction notes and acceptance prerequisites

- Build each route from independently attached `CurvedChannel`/`StraightChannel`-style fixed OBB segments, with a deliberate crossing offset. Do not let visual rails intersect where collision proxies do not.
- The B latch should have a visible actuator/cable and a deterministic seed-bound phase. Its retreat must be physically clear of B and route A.
- Required later evidence: native candidate calibration, active-sphere pair collision log, pairwise swept-gap certificate with uncertainty, release proof, independent tray-settle traces, fresh-process replay, and native-timing camera review. This plan has no validation or rendering result.
