# Phase 2B: ten reproducible Blender scripts and evaluated scene sidecars

Prerequisite: phase 1. Read AGENTS, VISION, CONTRACTS, the blender-scene-export skill and `.brief/seeds/animation_recipes.json`. Own `modules/blender/`, its local tests, generated manifests under the agreed artifact location, and `handoffs/02B.md`. Request shared-contract changes rather than editing them.

## Objective
Create ten separately runnable Python scene scripts using one reusable scene-generation/export library. The owner should need no Blender animation knowledge. Each script builds a visually distinct short abstract animation and its machine-readable scene bundle. Build the hero scene first, then generalize. A render batch must not disrupt concurrent Muse data collection.

## Environment and execution
Inspect the installed Blender version and supported API through local help/introspection and current official documentation. Do not assume an engine name or operator signature from memory. Respect `BLENDER_BIN`; the conventional Mac path is `/Applications/Blender.app/Contents/MacOS/Blender` but verify existence. Blender scripts execute in Blender's Python, separate from the service virtual environment. Avoid third-party Blender Python dependencies where possible.

Document commands of the form:
```
"$BLENDER_BIN" --background --factory-startup --python modules/blender/scenes/01_head_on.py -- --seed 42 --out artifacts/scenes/head_on
```
Implement the flags before documenting them as working. Include `--preview`, `--export-only`, duration/fps/resolution parameters and a bounded batch runner. Run only generated/trusted scripts. Never enable arbitrary embedded scripts in an imported blend file. Prefer a fast installed render engine, modest preview resolution and primitives with consistent lighting/material design. Detect render/encoding capabilities; use frame sequences and a verified encoder fallback when necessary. Never hide a failed encode by renaming a file extension.

## Ten scenes
Implement the seed recipes: head-on contact, near-miss twins, passing ascent/descent, orbital approach, bouncing staircase, sliding contact, size/shape contrast, domino cascade, expanding/contracting crowd and the hero geometric projectile/tower short. No copyrighted characters or gameplay. Parameter variants should meaningfully vary contact versus near miss, timing, density and direction, not only colour.

Each exports `.blend`, preview video when rendered, manifest, sampled object states, pair interactions, camera information, thumbnails and render/export QA. The hero has a clear approach, anticipation, impact, sparse aftermath and ending. A matched near-miss variant creates a deterministic live comparison without requiring on-stage Blender editing.

## Evaluated geometry, not invented metadata
Evaluate each frame from the dependency graph after relevant animation/physics evaluation. Use world-space transforms. If rigid-body simulation is used, bake or deterministically evaluate sequentially and export the same evaluated result used in rendering. Do not read original object transforms and assume they include simulated motion. Capture generator/tool versions and simulation settings.

Define `t_seconds = (frame - frame_start) * fps_base / fps`, an explicit end convention and any sub-frame event times. Include rational fps, rendered frame count and actual clip duration. State Blender Z-up/right-handed coordinates and the browser conversion once; include quaternion component order and matrix layout. Hash the rendered asset and sidecar together.

For each stable object ID export sampled world position, rotation, scale, world bounds, shape/role/material tags and velocities derived consistently in time. Calculate surface area from evaluated world-space triangles, correctly handling nonuniform scale. Cache static geometry rather than resending it every frame. Use volume only for suitable watertight geometry; otherwise null with an explanation. Geometry/material-to-sound mappings remain artistic assumptions.

For every relevant pair in these small scenes, export centre separation AND surface gap or a clearly labelled proxy, closest-approach time, relative velocity and interaction state. For a small object count, pairwise computation is acceptable; avoid a premature spatial-index framework. Only call it a collision when supported by geometric/contact logic. A distance threshold alone is a proximity event.

Start with analytic sphere contacts, sphere/plane interactions and scripted validated contacts; use declared geometry proxies for more complex meshes. Classify broad-phase bounding overlap separately from exact contact. Address fast-motion tunnelling using substeps or swept tests for supported primitives. When impulse/force is unavailable, report relative normal speed or a documented proxy, not a fabricated physical force.

A near miss requires approach, a local minimum surface gap, subsequent separation, and no contact in the event window. Preserve onset, minimum-gap time and end. Separate overlapping/continuous contact into onset/sustain/release instead of producing hundreds of impacts. A renderer-side position change must regenerate associated metadata and invalidate stale arrangement caches.

## GPT input views
Keep full local frames/states for audit. Produce a compact semantic summary containing object identities/geometric features, event timeline, bounded motion envelopes and selected keyframes. Offer exact event/state queries by ID. Do not send all vertices or every frame for every arrangement call. No raw EEG enters this summary.

## Validation
Use analytic ground-truth cases independent of the detection result: known sphere touch time, a known non-contact near miss, constant-separation motion and uniform scale changes. Check area scaling by s^2 and invariance to translation/rotation. Verify timestamps, no self-pairs, event de-duplication, stable IDs, source/video hashes and duration. Render selected frames with object labels/markers for human comparison. Report geometric uncertainty and visual QA separately.

All ten scripts must support an export/low-resolution smoke run. Render the hero and its matched variant fully before spending time on polished renders of all ten. Do not report every asset rendered when only scripts were generated. If Blender cannot run in this environment, deliver runnable scripts, documented prerequisites and clearly `RENDER_NOT_RUN` tests.

## Exit gate
One verified hero bundle plus a validated script/export path for all ten recipes; command outputs and actual render status; independent geometry tests; compact summary fixtures compatible with the arranger. No new application UI or audio logic.
