# Evaluated scene generator — Phase 2B

Current authoring/tooling supplements: [typed scene intent](../../docs/SCENE_INTENT.md)
and [portable Blender/MCP/FFmpeg discovery](../../tools/blender_mcp/README.md).
The scene-intent validator is planning-only and does not add a recipe or renderer input.

Ten trusted, separately runnable Blender scripts build original abstract choreography and export canonical 0.1 scene records. **Synthetic generated animation**, not measured rigid-body physics. The module does not contain audio, model calls, participant capture or application UI.

Use Blender **5.2.1 LTS**, the actually tested version. It runs in Blender's Python, with no new packages. A user-supplied macOS image was temporarily mounted read-only for this phase; it is not a persistent installation. Set `BLENDER_BIN` to an available, verified binary for later runs. Missing Blender blocks generation, not reading existing bundles or keyboard/replay music workflows.

```sh
"$BLENDER_BIN" --background --factory-startup --python-exit-code 1 --threads 2 --python modules/blender/scenes/01_head_on.py -- --seed 42 --out artifacts/blender/head-on --export-only
python -m modules.blender.batch --blender "$BLENDER_BIN" --out artifacts/blender/new-smoke --duration 3 --fps 8 --timeout 120
python -m modules.blender.batch --blender "$BLENDER_BIN" --out artifacts/blender/new-hero --recipe 10_projectile_tower --fps 8 --render --timeout 600
python -m modules.blender.batch --blender "$BLENDER_BIN" --out artifacts/blender/new-miss --recipe 10_projectile_tower --variant near_miss --fps 8 --render --timeout 600
PYTHONPATH=.:src python -m modules.blender.validate artifacts/blender/new-hero/10_projectile_tower-default
PYTHONPATH=.:src python -m pytest modules/blender/tests -q
```

Standalone script flags: `--seed`, `--out`, `--variant`, `--duration`, `--fps`, `--fps-base`, `--resolution WIDTH HEIGHT`, `--substeps`, `--preview`, `--export-only`. `--preview` sets 320×180 but preserves full duration. Ordinary default resolution is 640×360; hero duration is 30 seconds, others 20. Output directories must be empty. Matched variants (`contact`, `near_miss`) are supported for twins and hero only; others reject non-default variants instead of silently ignoring them. Seed affects palette and a monotonic timing warp while preserving geometry and event order. Canonical default seed 42 retains seed recipe timing. No arbitrary `.blend` imports or embedded script execution.

The batch runner launches serial trusted scripts, records exact commands, PID/PGID and timeout before waiting, terminates owned groups and verifies disappearance. It uses no shell and never kills unrelated processes. Per-job timeout is 1–1800 seconds. SIGTERM and keyboard interruption enter owned-group cleanup. A forced kill of the runner itself cannot execute cleanup: its explicitly recorded process groups then require task teardown; do not close a terminal as a substitute. Do not render during a competing participant capture session.

## Bundles and provenance

Each export writes `scene.blend`, `manifest.json`, full `object_states.jsonl`, `interactions.jsonl`, `geometry.json`, `summary.json`, `config.json`, `generator.json`, `qa.json`, and `bundle_hashes.json`. Rendered runs additionally write a PNG frame sequence, four selected labelled frames, encoding command/results and `preview.mp4` when installed FFmpeg successfully encodes H.264. An encode failure leaves a reported frame sequence, never a renamed fake video. Validation uses installed FFprobe for actual decoded frame count, duration and SHA-256. `qa.json` retains the export-time state; subsequent validation/review reports are separate and never retroactively mutate a hashed bundle.

Exact source `.blend`, rendered video and every sidecar/frame are linked by SHA-256 of persisted bytes. `generator.json` records source module/script hashes and configuration. No bitwise repeatability of Blender container bytes or GPU render across machines is claimed; scripted positions, IDs, event ordering and config are deterministic for fixed inputs. Changing parameters changes the scene ID/config hash; changed persisted source/video invalidates the arrangement input hash.

World coordinates are right-handed Z-up metres. Browser Y-up conversion is `(x,y,z) → (x,z,-y)`, determinant +1; quaternions are xyzw; matrices are row-major storage acting on column vectors. Frames render the half-open interval `[0,duration)`; audit samples include the right endpoint. `t=(frame-1)*fps_base/fps`. Render count is rounded from requested duration×fps/fps_base; actual duration is count×fps_base/fps. Substeps default to four per rendered frame. Full previews at 8fps do **not** validate a 50ms visual timing gate.

Meshes are obtained from the evaluated dependency graph, triangulated and transformed to world space. Static shape/area/material information is cached; positions, rotation, scale/bounds and causal finite-difference velocities/accelerations are exported. Area uses transformed triangles and handles nonuniform scale. Volume is null because watertightness/orientation is not certified. All generated animations preserve topology/scale; future deforming imports need a new geometry-cache policy. Every exported evaluated position is asserted against the independent linear recipe at each substep. Blender 5.2's Python insertion initially ignored the UI interpolation preference; the corrected exporter sets every layered-action F-curve key to LINEAR explicitly. Earlier version-1 artifacts are superseded diagnostics.

## Contact and motion semantics

Pairs are unordered stable identities with no self-pairs. Analytic sphere/sphere and sphere/axis-aligned-box proxies and axis-aligned box gaps distinguish centre distance from surface gap. Sphere meshes are triangulated display approximations of their declared smooth-sphere proxies. Numeric proxy tolerance is 1e-5m; it is not a physical measurement or mesh-fidelity uncertainty. Positive analytic sphere gap is conservative for the inscribed display mesh. Contact episodes generate onset, sustain and release once each. A near miss requires approach, a bracketed positive gap minimum and subsequent separation without an intervening contact; its minimum time and end are in `geometry.json`/`summary.json` details. Exact linear sphere/sphere swept tests catch whole-frame tunnelling. Other contacts are substep sampled and **do not guarantee continuous collision detection**. Near-miss emission additionally requires a conservative Lipschitz lower-gap certificate for every linear segment (or exact sphere sweep); ambiguous inter-sample gaps suppress the near-miss claim. Overlapping boxes remain geometric overlap, never invented impact force. `physical_impact=false`, `impulse_ns=null` throughout.

The hero has hold/approach, a contact hold, scripted tower displacement/collapse, sparse settling and an ending. Its matched near miss changes the projectile's Y lane and keeps the tower upright; stable object and sonic IDs remain unchanged. The domino recipe is a deliberately stylized sliding-tile cascade with exact axis-aligned proxies, not a physics-backed toppling simulation. The visual floor is excluded from interaction metadata and named accordingly. Mapping shape/material to music remains a creative choice.

## Arranger/service boundary and checks

`modules.blender.summary.compact_summary(bundle_dir)` returns version `blender-summary-1`: canonical scene manifest; bounded object features/motion envelopes and five selected canonical states per object; canonical event timeline and exact minima/end details; provenance. `event_query`/`state_query` require exact IDs and raise `KeyError` for unknown values. Full local frames/vertices are not sent to a model. No EEG is present.

`modules.blender.api` exports `router` and side-effect-free `health()`. The integrator mounts `/scene`; module endpoints are health, summary, event and state. Reads resolve under the local artifact root, reject escaping/symlink paths and do not spawn Blender. A generic service render capability remains unregistered pending shared cancellation/cache design.

Independent checks cover known sphere touch/tunnelling, a known positive-gap near miss, constant separation, de-duplicated contact episodes, sphere/plane box contact, area s² scaling plus rigid invariance/nonuniform scale, all ten IDs/keys/determinism, stable matched hero IDs, query/path scope and actual timeout cleanup. `tests/blender_geometry_check.py` runs **inside Blender** and independently verifies a two-copy evaluated array modifier after translation, rotation and nonuniform scaling: expected 36m². Canonical validation is separate from geometry QA, rendering, visual review and future human music audition. See `handoffs/02B.md` for commands actually run and final evidence.

API grounding: actual mounted Blender RNA and action-layer introspection; official [RenderSettings 5.2](https://docs.blender.org/api/5.2/bpy.types.RenderSettings.html). Current online geometry API pages returned an access error during this run; local executable introspection and the evaluated mesh test supplied the missing verification.
