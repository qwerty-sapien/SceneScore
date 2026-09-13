# Animation directions 06 / 08 / 18 — review record

This report concerns new, user-requested animation studies. The referenced successful staircase and the historical active scene are preserved. The selected scripts are creative direction; physical event times come from integration, not timeline retiming. Outputs remain drafts for human review.

## Method

Explicit SI mechanics generate 7,201 samples over `[0,30]` at 240 Hz. A saved Blender simulation scene carries those computed transforms. A second Blender process reopens and checks every sample, then maps key times to 30 fps without changing physical seconds. A third process evaluates all 7,201 ticks again through the dependency graph. Rendering produces 900 frames, followed by frame count, presentation-time and complete decoder checks. Source byte snapshots and exact job commands accompany each candidate.

Separate controls cover the new mechanisms; success of the earlier one-sphere/fixed-box model is not generalized to them. Native Bullet calibration remains outside this delivery. No authored translation, arbitrary size change, timed body teleport, or model review is substituted for physical dynamics or human approval.

## Direction 18

Independent source review closed earlier findings about puck/table alignment, a protruding dock pad, a spring follower gap, support-plane gravity, hinge gravitational torque, contact-material extent, coupled impulse behavior and incomplete refinement coverage. Root reran the integrated controls: **21 tests passed** (17 mechanics tests and four packet fault controls).

The integrated mechanics sequence is: spring release1.741s, rail bank8.001s, fin impulse12.349s, two non-contact clearances13.671s/17.427s, latch release17.630s, downstream guide contact21.765s, compliant dock contact24.602s and settling25.123s. Minimum intended near-miss clearance is41.878mm; maximum hard-contact numerical penetration is0.174493mm. Dock compression is separately represented by a deforming surface and is not counted as rigid penetration. Paired-resolution all-actor position difference is at most0.138757mm. The source handoff records controls and their limits in detail.

Three camera/presentation trials are preserved. V1's three-quarter camera obscured the puck around the fin. V2 raised and straightened the view; an independent review consumed nine stills and confirmed clearer bank, passage and dock framing. V3 corrects foundation face winding, makes inset legs meet the actual tilted underside, keeps coil bevel inside its declared envelope, and replaces the wide overhead wooden beam with a narrow fixed metal beam inside the same checked support envelope. The counterweight is more visible. Moving transforms and computed physics bytes are identical across these presentation trials.

Both reopened V3 checks passed all7,201 samples. Maximum differences are0.0000002644m position,0.0000004032rad rotation and0.0000005961 scale. The derived free cable segment follows the physical attachment and fixed endpoint; it supplies no new force.

This remains an explicitly constrained planar disc/hinge model. The table's slope0.0008 produces only about8mm descent across the course. The bank, fin, gap, latch, door and compliant dock form the visible story; a steep final ramp is not claimed. Fins use opaque tinted materials to keep contact edges legible. Some fin contact edges are partly occluded by the actual fin in the high view. Sparse still inspection does not establish continuous-motion perception.

## Resource handling

The first sandboxed Blender fixture process failed at native startup with signal11; its receipt is preserved and its group is absent. Bounded normal-host Blender invocations succeeded. All Blender/encoder work is serial with recorded groups, two rendering threads and finite time limits. Final media and teardown results are recorded separately after the current renders finish. No browser, server or container was started for these new studies.
