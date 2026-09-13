# Animation directions 06 / 08 / 18 — review record

This report concerns new, user-requested animation studies. The referenced successful staircase and the historical active scene are preserved. The selected scripts are creative direction; physical event times come from integration, not timeline retiming. Outputs remain drafts for human review.

All three movies are complete: **30 seconds, 900 frames, 1280×720, 30 fps, silent**. Each passed full decoding, frame/PTS checks, fresh Blender replay and frozen-source lineage verification. The [final audit](final-audit.json) binds the completed media and independent geometry evidence.

| Direction | Movie | Editable scene |
|---|---|---|
| 06 — Three Ways Down | [video.mp4](../../artifacts/blender/revamp/directions/06_three_ways_down-v4/renders/video.mp4) | [scene.blend](../../artifacts/blender/revamp/directions/06_three_ways_down-v4/scene.blend) |
| 08 — Spiral Observatory | [video.mp4](../../artifacts/blender/revamp/directions/08_spiral_observatory-v3/renders/video.mp4) | [scene.blend](../../artifacts/blender/revamp/directions/08_spiral_observatory-v3/scene.blend) |
| 18 — The Billiard Greenhouse | [video.mp4](../../artifacts/blender/revamp/directions/18_billiard_greenhouse-v3/renders/video.mp4) | [scene.blend](../../artifacts/blender/revamp/directions/18_billiard_greenhouse-v3/scene.blend) |

Each directory also retains the computed states, simulation scene, evaluated meshes, source snapshot, diagnostic stills, every rendered PNG and exact job commands. There is no new score/audio performance or human musical approval in this animation delivery.

## Method

Explicit SI mechanics generate 7,201 samples over `[0,30]` at 240 Hz. A saved Blender simulation scene carries those computed transforms. A second Blender process reopens and checks every sample, then maps key times to 30 fps without changing physical seconds. A third process evaluates all 7,201 ticks again through the dependency graph. Rendering produces 900 frames, followed by frame count, presentation-time and complete decoder checks. Source byte snapshots and exact job commands accompany each candidate.

Separate controls cover the new mechanisms; success of the earlier one-sphere/fixed-box model is not generalized to them. Native Bullet calibration remains outside this delivery. No authored translation, arbitrary size change, timed body teleport, or model review is substituted for physical dynamics or human approval.

## Direction 06

The sphere, solid cylinder and finite torus use their actual rotational inertias, an equal initial slope, then separate planar course profiles. Their receivers first engage at 14.579, 15.138 and 16.475 seconds. Each receiver supplies compression-only force, releases at zero force and can recontact; the visible plunger and spring follow that computed response. Small residual motion is retained through 30 seconds. Twelve electrical checkpoint indicators change state at measured crossings. They supply no body forces.

The original elevated crossovers and mechanical finish flag become planar profiles and electrical checkpoints. This model does not claim unsupported hoop steering. Fifteen backend controls passed, including analytic slope acceleration, energy, friction, contact separation, and refinement of every actor and event. Maximum energy residual is about 1.53e-13 J; the required static friction coefficient remains below 0.137.

Four presentation trials are preserved. The original opaque guide walls hid the bodies; the final scene uses narrow solid contact bands, outward thickness and sparse uprights. A higher camera keeps all three lanes framed, orientation stripes reveal rotation, and the upper spring has a distinct material. Nine V3 stills were independently inspected, followed by root inspection of the V4 correction. Some narrow guide rails still occlude portions of the hoop receiver. These samples do not establish native-speed perceptual acceptance.

Independent checks used the actual evaluated meshes and every 240 Hz replay pose, including conservative bounds between stored poses. Final V4 maximum swept own-floor intrusion is 0.013734 mm. Other-static clearance lower bounds are 27.623460 mm for the sphere, 3.837098 mm for the cylinder and 27.830657 mm for the hoop. Own guide contact planes were checked separately. See `gate-evaluated/RESULTS-06-v4.json` and its stated scope. Fresh Blender processes chose some different UV-sphere quad diagonals between presentation trials; final geometry was audited directly, not assumed byte-identical. Physical states and events remain unchanged across these trials.

## Direction 08

The counterwound spiral is an explicitly frictionless sliding bead constrained by a visible groove, including a top capture strip where the computed reaction requires it. The short free drop and bowl drain become smoothly joined, supported descending grooves. The bead has no rotation stripe because this model does not simulate three-dimensional rolling.

An independent sweep of the original evaluated triangular walls found approximately 31 mm of penetration. Positive smooth-surface Jacobians and sampled centreline clearances had not detected this actual triangulation defect. That trial is rejected and preserved. The repair samples by world-space curvature and surface error, with explicit narrow contact bands and outward braces. Its first audit removed the large defect but found a 0.227643 mm between-pose overlap against the capture strip, above the unchanged 0.2 mm gate. The final repair adds a declared 60 micrometre outward contact-skin allowance for the finite mesh/replay proxy. Dynamics and events are retained exactly; the repair does not steer or retime the bead.

Final V3's actual Blender geometry passed the independent sample and sweep audit. Maximum guide intrusion is 0.168883 mm, including a measured bead-radius bound plus a 1 micrometre reserve. At the 7,201 stored poses, minimum guide clearance is positive, at 0.039021 mm. Other-static swept clearance is 23.856539 mm. Sampled plunger intrusion is 0.001333 mm including that reserve; sampled coil clearance is 50.432154 mm. Scale remains exactly one and orientation remains fixed, consistent with the declared sliding model. See `gate-evaluated/RESULTS-08-final-evaluated-v3.json` for inputs, scope and limits. No criterion was relaxed: one raw audit attempt exceeded its runtime cap and was rerun with a longer bounded runtime and unchanged numerical method.

The bead completes the outer spiral at 20.008 seconds, the descending crossover at 20.717 seconds and the lower spiral at 22.396 seconds. Its spring receiver engages at 22.750 seconds; natural recoil and recontacts continue, with speed remaining above 0.01 m/s until 28.725 seconds. The ideal guide supplies explicit constraint forces but does zero work. Initial energy is 32.373 J and the maximum balance residual is approximately 1.21e-5 J.

Nineteen tests passed on the repaired source; the two preserved penetration witnesses also passed against float32 facets. The integrator verified the exact source/test hashes and reran 23 packet/geometry controls. The shared channel generator changed during this repair: a new 06 generation from current source would use its new mesh too. The delivered 06 V4 movie remains bound to its earlier frozen source snapshot. Reproduce each delivered candidate from its own `generation_source/`, not an assumed common current backend.

An independent review inspected all nine final V3 stills at 0, 4, 8, 12, 16, 20, 24, 28 and 29.967 seconds. The bead stays visible and consistently sized; the supporting groove, top capture and final receiver are framed. The final bead rests in the lower-left receiver. Some narrow rails cross its silhouette without fully hiding it. No blocking visual issue was found in these samples. This is a sampled visual review, not continuous playback acceptance.

## Direction 18

Independent source review closed earlier findings about puck/table alignment, a protruding dock pad, a spring follower gap, support-plane gravity, hinge gravitational torque, contact-material extent, coupled impulse behavior and incomplete refinement coverage. Root reran the integrated controls: **21 tests passed** (17 mechanics tests and four packet fault controls).

The integrated mechanics sequence is: spring release1.741s, rail bank8.001s, fin impulse12.349s, two non-contact clearances13.671s/17.427s, latch release17.630s, downstream guide contact21.765s, compliant dock contact24.602s and settling25.123s. Minimum intended near-miss clearance is41.878mm; maximum hard-contact numerical penetration is0.174493mm. Dock compression is separately represented by a deforming surface and is not counted as rigid penetration. Paired-resolution all-actor position difference is at most0.138757mm. The source handoff records controls and their limits in detail.

Three camera/presentation trials are preserved. V1's three-quarter camera obscured the puck around the fin. V2 raised and straightened the view; an independent review consumed nine stills and confirmed clearer bank, passage and dock framing. V3 corrects foundation face winding, makes inset legs meet the actual tilted underside, keeps coil bevel inside its declared envelope, and replaces the wide overhead wooden beam with a narrow fixed metal beam inside the same checked support envelope. The counterweight is more visible. Moving transforms and computed physics bytes are identical across these presentation trials.

Both reopened V3 checks passed all7,201 samples. Maximum differences are0.0000002644m position,0.0000004032rad rotation and0.0000005961 scale. The derived free cable segment follows the physical attachment and fixed endpoint; it supplies no new force.

Root additionally inspected full-render frames 366, 374 and 390 around the hinged-fin impact, confirming the sampled before/after poses show the fin response and consistent puck size. The impact edge remains partly occluded by the fin itself.

This remains an explicitly constrained planar disc/hinge model. The table's slope0.0008 produces only about8mm descent across the course. The bank, fin, gap, latch, door and compliant dock form the visible story; a steep final ramp is not claimed. Fins use opaque tinted materials to keep contact edges legible. Some fin contact edges are partly occluded by the actual fin in the high view. Sparse still inspection does not establish continuous-motion perception.

## Resource handling

The first sandboxed Blender fixture process failed at native startup with signal11; its receipt is preserved and its group is absent. Bounded normal-host Blender invocations succeeded. All Blender/encoder work was serial with recorded groups, two rendering threads and finite time limits. The final audit confirmed all 53 recorded artifact-job groups absent, including rejected/preflight trials. The independent reviewer separately recorded teardown of every audit process. All worker sessions exited. No browser, server or container was started for these new studies.

## Commands and validation records

- The CLI stages `prepare`, `build`, `replay`, `verify`, `stills`, `render`, `encode` and `media` ran for each delivered candidate. Exact executable arguments, timeouts, process IDs and exits are in each candidate's `jobs/*.job.json`. [Runner instructions](../../modules/blender/production/directions/README.md) give the reproduction sequence.
- Puck mechanics: 17 author tests passed; the root run combined those with four packet fault controls, **21 passed** in [puck-tests.log](puck-tests.log).
- Initial rolling mechanics: **15 passed** in the root [rolling-tests.log](rolling-tests.log). After geometry repair, the exact integrated source passed **19 worker tests** in 639.83 seconds and both preserved float32 failure witnesses in 106.94 seconds. The [rolling handoff](../../handoffs/directions-rolling.md) records hashes and commands. Those costly identical-source tests were not duplicated after copying; root checked hashes and actual saved Blender geometry/replay instead.
- Final root integration controls: `PYTHONPATH=.:src .venv/bin/python -m pytest modules/blender/tests/directions/test_packet.py modules/blender/tests/test_geometry.py -q` — **23 passed** in [integration-controls.log](integration-controls.log).
- Ruff on the new direction modules, tests and both CLI tools passed: [lint-final.log](lint-final.log). Scoped `git diff --check` passed.
- `tools/audit_direction_animations.py` ran on the three delivered paths — **PASSED**, with source/evidence hashes, exact media cadence/decode, reference preservation and process-group absence recorded in [final-audit.json](final-audit.json).
- Native-speed human visual acceptance and music audition remain **NOT_RUN**. Sampled visual review, numerical mechanics checks and media integrity are reported separately above.
