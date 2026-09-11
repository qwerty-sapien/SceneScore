# Phase 1: executable contracts and the minimal harness

Execute only after phase 0. Read AGENTS, VISION, CONTRACTS, EVALUATION and the phase 1 task card. You own shared schemas, root setup, CI, runtime skeletons and fixtures in this phase. Do not implement model training, the ten scenes, complete synthesis or production UI yet.

## Objective
Make future independent Codex runs converge on one working set of interfaces. Build the smallest executable harness that rejects incompatible artifacts and exposes missing capabilities. Do not create a generic agent framework.

## Repository layout
Use the agreed stack, roughly:
```
apps/web/                    # performance and authoring interface
services/local/              # localhost app, mounted module routers
modules/muse/                # acquisition, detection, training
modules/blender/             # scene recipes and evaluated exporters
modules/music/               # symbolic assets and rendering recipes
modules/arranger/            # typed planning and approved mapping rules
packages/audio/              # browser score engine, transport, mixing
contracts/                  # versioned source-of-truth schemas
fixtures/                   # public/synthetic contract and integration inputs
artifacts/                  # generated outputs, ignored by git
private_data/               # real EEG/labels, ignored by git
models/local/               # real fitted model artifacts, ignored by git
reports/, handoffs/, tools/, tests/
```
Keep secrets in an ignored environment file. Provide `.env.example` with `RAGTM_PATH`, `BLENDER_BIN`, Muse transport/board settings, `OPENAI_API_KEY`, and `OPENAI_MODEL`, without real values. Configure rather than invent a provider model ID; verify access through a harmless small structured-response preflight when credentials are available. Missing cloud credentials must leave fixture/manual arrangement paths usable. Verify Mac Blender executable path, versions, Python architecture, Bluetooth permissions and local browser audio prerequisites through a `doctor` command. Do not install privileged system components automatically.

## Define and test these schema families
1. Acquisition metadata and EEG chunk: schema/version/session/sequence IDs, channel names and units, sample rate, channel mask, device timestamp, monotonic host receipt time, sample indices, quality/dropout state and optional IMU. Raw EEG stays local.
2. BlinkCandidate, GestureEvent and ControlAction: start/end/final-blink/decision timestamps, source mode, model version, score type, quality, gesture count, action enum, unique IDs and explicit suppression reasons.
3. SceneManifest: source/render hashes, generator/config/version/seed, rational fps, start frame, duration, metres, axes/handedness, quaternion order, matrix layout, camera and stable object identities. Do not rely on implicit Blender/browser axis conventions.
4. ObjectState and InteractionEvent: world transforms, velocity/acceleration where defined, bounds, surface area in square metres, optional physically meaningful volume, surface gap, centre distance, relative normal/tangential speed, stable pair identity, onset/duration, uncertainty and analytic/scripted/heuristic provenance. Impact impulse may be null when unavailable.
5. CompositionSpec, BrushGroove, ScoreEvent and AudioAssetManifest: PPQ, meter, tempo map, quarter-note tick time, key and harmony maps, MIDI pitch convention C4=60, note duration/velocity, instrument, articulation/dynamics/ornament lanes, swing convention, seed, groove/sample IDs, sample rate, source and licensing metadata.
6. ArrangementPlan and approval: input hashes, palette/recipe IDs, mapping curves, bounded parameters, event IDs, motif ownership, allowed harmonic transitions, uncertainty, review status, approved hash and version. The plan is data, never arbitrary executable model code.
7. RunManifest and EvaluationReport: code/config/data/schema/model hashes, split membership, commands, runtime/platform, result provenance, passed/failed/not-run status and evidence paths.

Implement fixture validation in Python and TypeScript against the same semantics. Generate types from the canonical schema where practical. Do not duplicate handwritten incompatible truth. A provider-schema projection may support fewer JSON Schema keywords, but preserve local semantic validation.

## Tool registry and task harness
Implement a small registry with: capability ID; input/output schemas; units/coordinate prerequisites; adapter; health check; side effects; timeout/concurrency/cost class; allowed output paths; cache key inputs; provenance; fallback and approval requirement.

Initial capability names can be `muse.capture`, `muse.replay`, `blink.evaluate`, `scene.generate`, `scene.export`, `scene.summarize`, `music.catalog.lookup`, `music.arrange`, `music.validate`, `audio.render`, and `av.evaluate`. Unimplemented capabilities must explicitly report NOT_IMPLEMENTED. Registry conformance tests must not pretend these implementations already exist.

Route exact declared capabilities, not free-text guesses. Reject incompatible schemas or missing requirements before execution. Cache deterministic outputs by input/config/tool-version hash. Limit external calls, retries and concurrent renders. Treat imported scene text and model output as data, never tool-authorizing instructions. Tools use scoped path arguments, not unrestricted shell strings. Wrap selected adapters in MCP later only when useful and testable.

A lightweight task runner records dependencies, ownership and run artifacts. No automated merging of conflicting agents. Root lockfiles change only under the integrator.

## Harness fixtures and executable checks
Create clearly synthetic examples: one collision, one near miss, one separating pair; a tiny symbolic jazz motif and brush pattern; one double-blink, one single, one triple; packet loss, duplicates, stale timestamps, bad quality and no-event recordings. These only test software paths, not accuracy.

Test contracts, monotonic times, units, hashes, event deduplication and every invalid fixture. Test seed reproducibility. Define interfaces for clock mapping and musical scheduling with a fake clock. Validate that double-blink preserves gain/articulation and that a triple cannot execute both actions when multi-count mode is enabled. Leave domain tests explicitly pending rather than passing placeholders.

Provide a supported root entrypoint such as `make doctor`, `make test-contracts`, `make test`, `make dev-replay`, `make assets`, and `make demo`. If `make` is unavailable, provide an equivalent documented runner. Commands that require unfinished modules fail with actionable status, not false success. Add a lightweight CI path that needs no headset, Blender or API key; separate marked local-hardware/render/live-API tests.

## Exit gate
Clean checkout -> install documented dependencies -> doctor -> passing contracts/fixture tests. Record genuinely unverified environment elements. Freeze contract version 0.1 and commit-compatible worktree base. Publish exact ownership for 2A-2E, including dependency requests and service router interfaces. Each task can develop against fixtures without another worker's unfinished implementation. Stop and hand off.
