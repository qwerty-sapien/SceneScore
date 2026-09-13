# From reference clip to executable few-shot example

Do not treat a collection of video URLs as an input/output demonstration for a
code-generating skill. Supply actual supported media inputs plus an explicit
construction plan and a reconstruction that you have run. When a model does not
accept video, supply timestamped event frames and a compact event ledger; do not
pretend sparse frames preserve all the dynamics.

## One reference package

```text
example_id/
  clip.mp4                 # authorized excerpt; original timing retained
  frames/                  # coarse overview plus dense event frames
  annotation.json          # exemplar_template.json, filled from evidence
  scene_spec.json          # units, objects, materials, trajectories, constraints
  build_scene.py           # tested minimal reconstruction, when available
  scene.blend              # licensed source or your reconstruction
  preview.mp4              # actually rendered result
  validation.json          # checks, tolerances, measurements, seed, version
  provenance.txt           # licenses, attribution, permission, source mapping
```

Not all candidates will contain every file. The strongest code-generation few
shots are reconstruction-tested packages; visual-only references must be labeled
as such. A reconstructed scene is an interpretation, not the creator's hidden
implementation. Never label inferred masses or friction values as measurements.

## Demonstration format

USER INTENT
[One concrete animation brief, specifying objects, gravity/material regime,
required events, spatial relationships, desired duration, and camera constraints.]

REFERENCE INPUT
[Attach authorized media. Include source-relative and clip-relative time mapping.]

OBSERVED EVENT LEDGER
[Time window, persistent objects, contact or clearance, before/after velocity
change, evidence frames, uncertainty. Preserve the temporal and causal order.]

IMPLEMENTATION PLAN
[State what is actually observed, what comes from source inspection, and what is
an assumption. Choose dynamic/kinematic/hybrid motion. Describe initial states,
actuation, release/handoff, colliders, collision margins, and simulation settings.]

EXECUTABLE EXAMPLE
[Provide the tested reconstruction script or source, with version and seed.]

VALIDATION
[Show checks and actual results; distinguish rendered-frame checks from 3D
geometric or solver-state checks. Mark untested assertions explicitly.]

## Retrieval policy proposal

For a new prompt, select 3-5 examples rather than the entire corpus. Prioritize
matching material/solver family, event sequence, and contact geometry; then add
one example with a different layout or object shape. Texture similarity is a
secondary objective. Keep rigid and fluid merging examples from silently
substituting for one another. Include failure examples only when clearly labeled
with the defect and correction.

## Generation instruction template

Create a Blender scene satisfying the requested event graph. Use the supplied
examples as patterns for construction and validation, not as permission to copy
unsupported physical assumptions or an identical scene.

Before a final beauty render:
1. Make a simple collision-geometry preview with stable object IDs.
2. Choose units, time scale, material model, and control mode explicitly.
3. Plan initial states and any actuation to achieve the requested event order.
4. Simulate or evaluate trajectories; validate intended contacts and clearances.
5. Adjust release times, obstacle poses, and initial conditions, not arbitrary
   visual easing, when those are the physical causes being modeled.
6. Recheck transitions between driven and dynamic phases for continuity.
7. Render a diagnostic view in which all essential interactions are observable.
8. Record settings, seed, measurements, and unresolved issues before final output.

For a near miss, use positive surface clearance in source geometry over the whole
critical interval, not center-to-center distance alone or screen-space overlap.
Sample at sufficient temporal resolution for the chosen tolerance; a per-frame
check can miss fast contacts. For controlled experiments, perturb initial states
and report the range over which the intended event still occurs. Exact grazing
or near-miss staging can legitimately be timing-sensitive; label that sensitivity.

## Evaluation proposal

Hold out entire base scenes and creators, including their crops and variants.
Compare zero-shot, visual-only examples, and annotated executable examples on the
same briefs and seeds. Measure requested event-order success, unintended contacts,
penetration/clearance violations, motion continuity, framing of key events, and
human ratings of spatial inventiveness. Do not claim robustness from attractive
renders alone. Add examples that address observed failure modes.
