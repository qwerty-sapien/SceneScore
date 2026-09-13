---
name: physics-aware-animation
description: Design, build, inspect and repair original SceneScore Blender animations using explicit physical causes, sparse readable event sequences, spatial composition, reference media and reproducible scene-to-music evidence. Use for new satisfying kinetic scenes and poor-animation repair, alongside blender-scene-export.
---

# Physics-aware, spatially creative animation

## Scope and authority

Read root `AGENTS.md`, `docs/VISION.md`, relevant contracts and the existing
`.agents/skills/blender-scene-export/SKILL.md`. This skill complements the exporter;
it does not replace canonical 0.1, approvals, production proofs or task ownership.
The user's current request governs new authoring scope. Do not silently reopen
an exhausted historical repair budget, rewrite frozen reviews, edit immutable
`.brief/`, activate an unapproved scene, change Muse/blink behavior or claim Phase 4.

Read [repo findings](references/REPO_AUDIT.md) before working on this snapshot.
The input archives do not contain the recorded `artifacts/` production tree.
Reported historical passes are not current reproducibility evidence.

## Success criterion

Create a causally legible kinetic scene whose motion is mechanically justified,
whose spatial design is interesting, and whose few salient interactions are
separated enough to support musical phrasing. Match selected reference qualities,
not their exact geometry, logo, event density or presumed simulation settings.

**Do not substitute one of these for another:** valid Python, a successful render,
a passing physics control, attractive stills, correct event timing, a good full
motion sequence, musical coherence, or human approval.

## Inputs and reference loading

Before generation, record duration/aspect ratio, event families, event spacing,
chosen physical backend, output/resource budget and selected references. Use
2–4 salient beats with at least two distinct primary event kinds as a starting
design, not a claim that every brief must have exactly that count. A collision
and rebound at one instant are one beat. Quiet intervals contain natural motion,
anticipation or supported rest; never freeze a free body to manufacture spacing.

References have three separate statuses:
- Visual reference: media inspected; physical implementation unknown.
- Reconstructed example: original source or original recreation available.
- Implementation exemplar: reconstruction executed and checks passed in its scope.

Select 2–3 relevant examples by mechanism, event order and contact geometry; use
style as a separate selection axis. Actually inspect/pass the selected media to
a video-capable reviewer and load its notes and tested source. Merely storing a
`.mov`, YouTube URL or ZIP in the repo does not make it an in-context example.
Record the exact hashes and intervals consumed by the run. Keep observations,
source-derived facts and reconstruction assumptions distinct.

Use [reference notes](references/EXEMPLARS.md). The supplied recordings are visual
references only. Both lack audio streams; do not infer their soundtrack mapping.
Use presentation timestamps, not frame-index divided by nominal FPS, to index
these variable-rate screen recordings. Sparse frames are composition evidence,
not a continuous-contact or speed-validation certificate.

The old exemplar search kit is optional upstream discovery/curation tooling.
Reuse its record and reconstruction templates; defer broad discovery until an
actual missing mechanism or failed generation justifies a new query. Never run
metadata collection as a prerequisite for building from already supplied media.

## 1. Write the scene intent before creating meshes

Create a versioned authoring supplement, not a new canonical contract. Start from
`assets/scene-intent.example.json`; it is NOT a current production-CLI input.
Declare persistent actors/sonic identities, silent supports, visible actuators,
gravity/material/control models, expected event order, target windows, geometric
constraints and the intended ending. For every beat state the physical cause and
the measurement that could falsify it.

An initial sparse policy is 1 s of separation between salient event windows,
maximum one simultaneous salient beat, and no more than 30% salient-window duty
cycle. These are proposed design defaults, not frozen project thresholds. Choose
and log policy values before comparing candidates. Continuous rolling support
is not a fresh dramatic event every sample; retain it in raw contact evidence.
Conversely, do not hide significant unintended collisions by relabelling them
"background" after generation. Merge microcontacts into declared episodes, then
review their salience and timing.

Run the plan linter:

```sh
python .agents/skills/physics-aware-animation/scripts/check_story_plan.py \
  .agents/skills/physics-aware-animation/assets/scene-intent.example.json
```

`PLAN_VALID_NOT_PHYSICS_VALIDATED` only means the proposed plan is internally
consistent. It is not trajectory evidence and must never unlock production.

## 2. Select an explicitly supported physical model

Use the existing backend capability limits, not a "physics on" checkbox:

| Intended behavior | Appropriate scope |
|---|---|
| One sphere with fixed oriented-box obstacles | Existing `fixed-obb-sphere-mechanics-1`, after controls and candidate-specific convergence |
| Multiple dynamic bodies, moving-contact obstacles, stacks, coupled launchers | Native Bullet or another explicitly integrated backend with fresh applicable controls |
| Driven carriers/rotors | Explicit prescribed actuator with visible support; check velocities, continuity and work/energy source where relevant |
| Adhesion, liquid merging or deformable contact | A separately declared and tested model; not the current rigid-body or one-sphere scope |

The analytic backend computes motion and replays it kinematically in Blender.
That is not the same as hand-authoring a desired trajectory. Its current scope
is one dynamic sphere against fixed OBBs: do not simulate two independent balls
and pretend they collide, or replay a moving gate into a fixed-obstacle solver.

Separate rendered detail from collision geometry but measure their discrepancy.
Primitive/convex proxies must preserve visible gaps and contact surfaces. Do not
place a convex hull over a concave passage and claim its interior is traversable.
Any new component or proxy representation needs its own correctness check.

The snapshot records failed native transfer/convergence calibration and a separate
restitution diagnosis. Do not repeat blind substep/iteration increases, reset a
coefficient and call it repaired, or relax acceptance tolerances. Preserve the
failure and investigate a falsifiable new hypothesis in a fresh candidate. An
alternative backend is a new declared model, not a silent fix to native Bullet.

## 3. Design a feasible route; then solve its parameters

Plan a connected spatial route with clear elevation changes, crossings, visible
support and an intentional landing/catch. A useful component contract exposes
entry/exit positions, travel direction, admissible speed range, collision shape,
physical material, actuation limits, bounds and independent tests. Start with
ramps, rails, deflectors, fixed clearance posts and catchers; add more complex
carriers, constrained catapults and moving gates only with supporting mechanics.

Choose parameter bounds for release position/time, ramp slope, deflector normal,
obstacle placement and actuator phase. Propose candidates, simulate cheaply,
measure the actual event sequence, and adjust physical parameters. Back-solving
a target ballistic landing or a contact normal is a useful initial guess, not
an excuse to bypass the final simulation.

Use bounded parameter search rather than one huge script followed by one render.
Filter infeasible candidates before beauty rendering. Keep the seed, candidate
parameters, rejected outcomes and objective components. Hard physics constraints
remain hard; visual appeal cannot compensate for interpenetration or wrong events.
Do not force physical collisions onto musical beats by changing actor keyframes.

Add reusable source components instead of continually expanding a monolithic
`create_scene`. The present registry admits only known recipes/controls; introduce
new IDs through reviewed registry/selection changes, without mutating immutable
seed identities or misleading existing arrangement hashes.

## 4. Review motion and staging through a closed loop

Use CLI/Python for reproducible generation and baking. Use the existing pinned
Blender MCP for inspection and bounded scratch changes. Follow
[the MCP loop](references/MCP_LOOP.md); successful inspection is not validation.

Before beauty work, inspect the complete graybox clip at native timing, plus
side/top views and event-dense windows. Confirm incoming cause, interaction,
outgoing consequence, depth ordering and supported ending. Frame all salient
actors; do not accept an ending parked at the extreme edge or out of view.
Keep the decisive interaction in one readable shot. Avoid distracting camera
motion during it; a slow reveal between events is acceptable.

After every accepted interactive edit, change the generation source/spec, create
a new candidate, invalidate affected caches/proofs, rebuild and reopen in a
fresh process. A `.blend` edit not reproduced by source is not a completed repair.
Do not reuse stale sidecars after changing geometry, timing or camera dependencies.

## 5. Add visual polish only to a successful motion design

Use a small intentional material palette, coherent scale, believable edges,
contact shadows, controlled reflections and lighting that separates depth. Match
the selected reference's legibility and material response rather than adding
random geometry. Build supports and working clearances into the design.

Camera/layout/light/materials are separate parameters from mechanics. Preserve a
cheap diagnostic render profile, a full-motion preview and an explicit final
profile. Test render-engine/version properties against the installed binary;
do not assume a legacy sample attribute was applied because a guarded setter
silently skipped it. EEVEE versus Cycles is a rendering choice, not a physics fix.
A higher-resolution image alone cannot repair dull routing or poor timing.

## 6. Validate the produced sequence, not just the brief

Preserve all current physical, replay, hash and media gates. Add separate actual
story evidence, without treating intent targets as observations:
- Measured event episodes/uncertainty match the required order and distinct kinds.
- Near misses have positive surface-gap evidence across approach and separation;
  a graze requires contact evidence, not just projected overlap.
- Event salience, duration, spacing and significant unintended contacts are reviewed.
- A full-motion reviewer verifies clarity, camera coverage, natural timing and ending.

Run backend-appropriate controls and candidate-resolution comparisons. Test small
parameter perturbations and negative controls: shift a clearance post into the
path, remove a deflector, disable a launcher, deliberately reuse stale evidence,
and introduce an offscreen critical event. The applicable gate must reject these.
Do not use rendered stills to certify velocity, impact, rolling or causal continuity.
Keep unknowns `NOT_RUN`/`UNVERIFIED`, never implied PASSED.

The current validator's overall PASSED is scoped to physical candidate checks;
its perceptual/story fields are not part of that overall conjunction. Introduce
a separate publication decision requiring the actual visual/story review, without
silently changing the meaning of a historical physical-validation report.

## 7. Hand motion to music without losing the product's twist

Preserve animation-to-score direction. Use evaluated states and certified event
markers through the existing handoff, keeping raw contacts separate from sparse
musically salient episodes. Maintain stable object voices. Silent structural
supports cannot own motifs; intentional sounding targets must be explicit roles.

Continuous motion can influence a bounded phrase contour or texture through an
approved mapping. Selected events can motivate a response, ornament, space or
harmonic tension; do not emit a new note for every contact sample. Near miss is
not impact Foley. Physical Foley retains scene-time onset; musical quantization
and scene synchronization are separate policies.

Preserve original editable symbolic music, stems, exact source identities and
approval. The snapshot's staged drafts use existing-score excerpts: do not call
that fully adaptive scoring. Any richer adaptation requires its own authorized
implementation and audition. Keep the deliberate double-blink/keyboard harmonic
modulation workflow and signed-motion policy unchanged; do not infer mood or
emotion from geometry and do not expand gesture controls.

## Deliverables and reporting

An accepted implementation exemplar includes source spec, deterministic builder,
`.blend`/cache or declared mechanics trace, native-timing clip, actor/role metadata,
measured events with uncertainty, scoped validation reports, full-motion review,
exact runtime/version/hash provenance and music-handoff compatibility. Mark the
independent statuses: built, simulated, physics-checked, replay-checked,
story-reviewed, visual-reviewed, music-auditioned, approved. No single "success"
boolean should hide unfinished gates.

Missing Blender blocks a fresh Blender claim, not planning or host-side tests.
Unrelated GUI/MCP processes must not be terminated. Report commands actually run,
failed candidates and unresolved limits; clean up only task-owned processes.
