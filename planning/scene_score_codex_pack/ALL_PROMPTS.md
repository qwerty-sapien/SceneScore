# SceneScore phased Codex prompts

Reading copy only. Execute the separate phase files in dependency order, never this document as one instruction.



---

# Phase 0: establish the documentation basis, then stop

You are the founding engineer and technical specification editor for a greenfield project provisionally called SceneScore. Your deliverable in this run is a compact, enforceable documentation and agent-instruction foundation. Do not implement the application, start model training, create rendered media, install a broad dependency stack, or roll directly into later phases.

## Read first
Read `.brief/README.md`, every `.brief/seeds/*.json`, and the remaining prompt headings to understand the dependency graph. Treat `.brief/` as immutable source material. Inspect the local repository and available runtime versions without overwriting existing work. Read any existing local instructions before adding project instructions. Do not change global Codex settings.

The current user brief is authoritative over older inferred preferences. Record unresolved choices explicitly and choose the smallest reversible implementation default. Only unresolved access/authorization or an essential missing input may block the affected track. Do not block unrelated tracks.

## Product intent to preserve
1. Turn a generated Blender animation into an editable score and synchronized sound-effects track. Give objects persistent sonic identities. Use approach, separation, collision, near miss and relative motion to influence phrasing, dynamics, articulation, ornamentation, harmony and sound design.
2. Use original short blues, rag-influenced jazz and brushed-jazz sketches. Retain MIDI/symbolic events and separate stems, so key changes and articulation remain editable. Avoid a single uneditable generated audio file as the only representation.
3. A deliberate Muse double-blink is the default hands-free modulation request. It leaves the current gain and articulation state unchanged. Animation direction guides a configured signed musical movement. Random choices are constrained, seeded and logged.
4. Triple-blink expressivity changes and amplitude-derived control are exploratory alternatives, disabled in the default demo. Expose gesture-to-action mappings as configuration. Do not silently replace the agreed double-blink key-change behaviour with volume control.
5. GPT Astra helps propose mappings, arrangements and tool plans. It never sits in a per-frame, per-sample or per-blink audio-critical path. Validated, approved musical plans execute locally and deterministically.
6. Build a usable authoring/performance demo, not a game, a return to Mind vs Machine, a stress detector, a claim of mind reading, or a general-purpose DAW. EEG is being used to detect ocular gestures.
7. The owner has a Muse headset and Blender on a Mac. Verify the actual hardware generation, transport, channels, units and sample rate locally. Historical context suggests a Muse 1, but that is not sufficient to choose a board ID without verification. No extra hardware purchase is a default requirement. The multimeter is outside scope and must not be connected to the worn headset.
8. Target a five-hour hackathon integration after permitted preparation. Rules on pre-existing work remain unverified. Track preparation provenance and distinguish prepared assets from event-day work.

## Audit the old baseline without inventing it
Look for `RAGTM_PATH` or an explicitly provided repository link/local checkout. Read its instructions and inspect only relevant acquisition, timestamping, filtering, blink detection, debounce/refractory logic, recording/replay, and Flappy Bird input abstraction. Record exact paths and commit hash, strengths, risks, dependencies and what can legally/practically be reused. Do not modify that repository. Do not import game code into this project. Preserve a runnable unchanged baseline for a future head-to-head comparison when possible.

If the repository is unavailable, create a clearly marked `RAGTM_NOT_INSPECTED` entry and an adapter plan. The successful blink-to-jump result is a user report, not a measured result in this project. Never infer a threshold, model, feature set or claimed performance from it.

## Recommended small architecture
Select a local-first TypeScript web application for the browser/audio layer and a small Python service for Muse, acquisition/evaluation and arrangement orchestration. Blender runs its own installed Python interpreter. A practical starting choice is React/Vite, Web Audio, FastAPI/WebSocket, NumPy/SciPy/scikit-learn and an optional compatible Muse transport such as BrainFlow. Confirm versions and platform support before locking them. Do not require a database, cloud deployment, GPU, Kubernetes or a large multi-agent framework.

The authoritative contracts are versioned JSON Schemas, with validated TypeScript/Python representations or shared fixture conformance. Never maintain silently diverging schemas. The arrangement API uses a supported provider-specific schema projection plus stricter local semantic checks.

The runtime paths are:
- Blender evaluated scene -> SceneManifest/ObjectState/InteractionEvent -> approved ArrangementPlan -> ScoreEvents -> local audio engine.
- Muse/recording/keyboard -> BlinkCandidate -> GestureEvent -> ControlAction -> musical-boundary scheduler.
- Browser transport owns musical time; explicit clock adapters map acquisition and video timestamps. No wall-clock assumption joins those systems.

## Create these foundation files, fully populated
- `AGENTS.md`: concise root guidance, reading order, immutable product invariants, ownership rules, exact phase boundaries, test-report honesty, and how to resume. Keep it small enough to be reliably read; link detailed documents rather than copying them.
- `docs/VISION.md`: canonical user intent, a 60-second demo story, user interactions, MUST/SHOULD/EXPERIMENTAL scope, exclusions and unresolved questions.
- `docs/ARCHITECTURE.md`: module boundaries, dependency direction, data/control flows, audio clock, graceful degradation and human approval boundaries.
- `docs/CONTRACTS.md`: names and semantics of shared schemas, units, coordinate/time conventions, identity, provenance and versioning. Specify invariants, not just type names.
- `docs/EVALUATION.md`: event-level blink evaluation, data split rules, audio/scene correctness, musical audition, performance measurements, targets versus evidence, and release statuses.
- `docs/RUNBOOK.md`: environment discovery, permission checks, permitted preparation, phase gates, commands planned for phase 1, data capture procedure, demo scope and fallbacks.
- `docs/STATUS.md`: completed/not-started/blocked tracks and next authorized runs. Never mark unrun work complete.
- `docs/LINEAGE.md`: actual RAGTM inspection status and precise reuse evidence.
- `docs/decisions/0001-scope-and-stack.md`: architectural decisions, rejected alternatives and conditions that would justify changing them.
- `requirements.yaml`: stable requirement IDs, priority, source intent, owner, acceptance evidence and planned tests.
- `tools/capabilities.yaml`: a minimal capability registry design, with available/unavailable/unverified statuses; do not pretend a proposed plugin is installed.
- `.agents/skills/` with four narrowly triggered `SKILL.md` files: `blink-evaluation`, `blender-scene-export`, `symbolic-jazz-arrangement`, `audiovisual-integration`. Include when to use, when not to use, needed inputs, outputs, executable checks, stop conditions and reference documents. Skills must not override the vision or user instructions.
- `docs/tasks/` with the ownership matrix and one task card per subsequent phase, linked to the immutable prompt file. Each card states inputs, owned paths, dependencies, exit gate and handoff path.

## Requirements that must become explicit invariants
Detection: no 100% accuracy promises; supervised calibration labels remain labels even when mixed with unlabelled data; no random-window leakage between sessions; no detector-generated ground truth; no synthetic data masquerading as headset performance; no tuning on final test sessions. Report all missed gestures, including those lost during abstention or refractory periods.

Gestures: natural blinks produce no action; accidental natural blink clusters can resemble deliberate gestures; double/triple discrimination has an unavoidable prefix ambiguity and a declared decision delay. Confidence is not a calibrated probability unless tested as such. Signal-quality failures suppress new controls without interrupting music.

Geometry: actual evaluated object positions and world-space surface area; distinguish centre separation from surface gap and physical impact from a proximity heuristic; include object/object interactions, not only isolated positions. Specify how upstream geometry affects music without claiming physically accurate acoustics.

Music: key, chord, register, dynamics, articulation, phrasing, ornamentation and timbre are separate controls. No indiscriminate whole-track pitch shifting. Unpitched brushes are not transposed with the key. Collision Foley remains locked to scene time and is never blindly snapped to the musical grid. Randomness is seeded. Stable identities persist across loops and key changes.

Tools: discover by capability, validate preconditions and input/output schemas, execute within scoped permissions and resource budgets, cache by content/version/parameters, and record provenance. A deterministic function or CLI may implement a capability; MCP is an optional adapter, not an excuse to build a plugin marketplace.

Evidence: mark real device, replay, synthetic, cached GPT, manual plan and keyboard modes visibly. Human audition is a separate evaluation from schema validity. No fake successful tests or manufactured media/model benchmarks.

## Change protocol
Future agents read root AGENTS, VISION, their task card and relevant contracts before editing. A worker cannot change shared schemas, provider model IDs, root dependency locks, gesture defaults, priorities or evaluation thresholds to make its local task easier. It proposes a scoped change in `docs/requests/<track>/` for the integrator. Human product updates can amend the vision, with an explicit change record and affected tests. Do not freeze known mistakes permanently under the guise of consistency.

Parallel workers write only their owned module and `handoffs/<track>.md`; the integrator alone updates shared status/locks. Use separate worktrees. The handoff records exact files, commands and results, assumptions, pending hardware checks and compatibility requirements.

## Exit gate
Check that the documents agree on scope, clocks, gesture mapping, preparation rules and ownership. Every MUST requirement needs an owner and an observable acceptance test, even when its implementation is pending. List unresolved hardware/API/repository access honestly. Provide the ready-to-run phase 1 instruction and the later parallel schedule. Stop. Do not implement phase 1 in this run.


---

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


---

# Phase 2A: real Muse capture, labels, replay and the preserved baseline

Prerequisite: phase 1 contracts are frozen. Read AGENTS, VISION, the blink-evaluation skill, CONTRACTS and EVALUATION. Own `modules/muse/acquisition/`, `modules/muse/baseline/`, `modules/muse/annotation/`, module-local tests and `handoffs/02A.md`. Do not alter shared schemas, browser UI, audio, root lockfiles or Blender code. Expose the agreed router/CLI interface for later mounting.

## Objective
Produce genuine, timestamped, privacy-preserving Muse recordings and trustworthy gesture annotations. Deliver a causal baseline and exact replay before pursuing complex models. An agent cannot perform the owner's blinks or manufacture the resulting data.

## Inspect and preserve RAGTM
Use the phase 0 lineage report and `RAGTM_PATH`. Read and preserve the actual previously successful acquisition and blink logic. Package its relevant logic behind the new adapter with its original parameters and version recorded. Test behaviour equivalence on real replay when recordings exist. Preserve its dependency/licence information. Do not modify the original repository or bring over game UI.

If unavailable, implement an explicitly NEW deterministic baseline. Never label it the old RAGTM detector. Report what still needs code comparison.

## Hardware and stream
Verify the precise Muse generation/board and supported transport on this Mac. Prefer the proven original transport when available; otherwise test a compatible BrainFlow adapter. Do not guess board/channel indices, units or sample rate. Do not require browser Bluetooth as the only route. Support exactly one functioning live transport initially plus file replay and synthetic fixtures.

Record original numerical samples without destructive preprocessing, sequence/sample indices, actual rate, units, channel names/masks, source/device time if present, host monotonic receipt time, packet gaps, quality and optional IMU. Device timestamps and host timestamps have distinct semantics. Derive sample times explicitly; never assign every sample in a received batch the same time. State timing accuracy limits.

Use a local chunked format with a versioned manifest and separate label/event JSONL. Persist cleanly on disconnect, maintain bounded memory, and make recording recoverable. Keep raw data, names, device addresses and optional video outside git and cloud requests. Use pseudonymous participant/session IDs. Recording must be visible and explicitly started by the user. Provide deletion and export controls.

On disconnection or severe quality loss: reset partial gesture state, suppress new commands, keep the soundtrack running, display the cause and reconnect without replaying stale events. Refit/reconnect requires warmup and explicit re-arming. Never infer new blinks by interpolating missing packets.

## Acquisition/annotation interface
Provide a small module-owned local capture page or CLI independent of the production web UI. Show raw frontal channels when available, candidate markers, stream quality and clock diagnostics. Modes: natural activity; randomized instructed gestures; self-paced gestures; review/relabel; real replay; synthetic software test.

The cue records requested intent, not the actual occurrence. After each trial allow confirmed performed/missed/uncertain labels. Mark actual blink onset/end or sequence completion through review. Optional local webcam timing is permissible only with consent and never required or sent to GPT. No detector prediction may automatically become evaluation ground truth. Keep cue timestamps, user responses and prediction data separate.

Avoid simultaneous keyboard labels that could teach the detector hand/head movement artifacts. Use delayed confirmation or later review. Cue content/timing and game/audio feedback are not model features.

## Proposed preparation protocol
Use comfortable voluntary gestures, normal rest breaks and a stop control. Do not ask the user to strain or hold their eyes closed for long periods. Begin with a short comfort/fit check, then collect multiple independent sessions with the headset removed and refitted between sessions.

Across preparation, aim for 200-300 verified deliberate double-blink examples and at least 60-120 minutes of varied natural activity if practical, distributed across sessions rather than one continuous fit. These are data collection goals, not a requirement to exhaust the participant or a guarantee of near-perfect accuracy. Leave one or more sessions untouched for final evaluation.

Include natural single/double blinks, reading, watching the animation, speaking, smiling, looking around, head turns, jaw activity, gentle headset adjustment, quiet rest and ordinary blinking. Include self-paced deliberate gestures so the model does not depend on a predictable cue rhythm. Include triple sequences only for the optional experimental profile. Annotate ambiguous spontaneous clusters separately and include their false-activation impact in free-running tests.

## Causal baseline
Retain a blink-sensitive path. Do not run an ocular-artifact-removal pipeline that deletes the target signal. Evaluate a causal low-frequency filter and robust baseline normalization appropriate to the observed stream; choose settings through held-out development data, not a remembered universal amplitude threshold.

Use frontal channels and optional temporal/IMU context according to measured channel availability. Do not blindly subtract correlated frontal channels or common-average away the bilateral blink. Features may include amplitude relative to baseline, waveform duration/slope/area, channel agreement, saturation and motion flags. Preserve sign convention and latency information.

A two-stage baseline detects candidate blink waveforms, then uses a finite-state grammar for gestures. It needs hysteresis, waveform de-duplication, minimum separation, configurable inter-blink gaps, sequence closure and a bounded cooldown. Initial timing values are exploratory and must be calibrated. Do not hide missed gestures with a long cooldown.

For double-plus-triple mode, wait for the sequence-closing interval after the second blink. A third accepted blink changes the sequence class before commitment; execute exactly one action. Default double-only mode should still reject overlong/ambiguous trains under its documented grammar. Distinguish last-blink-to-decision latency from first-blink-to-decision and decision-to-musical-action delay.

## Exit gate
Deliver real capture/replay commands, annotation workflow, untouched raw-data format, baseline adapter, stream fault tests and a short genuine recording when the owner has provided one. If no hardware session has occurred, report `HARDWARE_UNVERIFIED` and stop at the working recorder/test-fixture boundary. Do not claim trained accuracy. Handoff includes the exact command for phase 3A and any remaining human acquisition actions.


---

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


---

# Phase 2C: original symbolic jazz sketches, brush grooves and synthesis assets

Prerequisite: phase 1. Read AGENTS, VISION, CONTRACTS, the symbolic-jazz-arrangement skill and the composition/brush JSON seeds. Own `modules/music/`, its local tests, music artifact outputs and `handoffs/02C.md`. Browser playback implementation belongs to phase 2E; agree the event/synth preset contract and export fixtures without editing its files.

## Objective
Create four short, original, human-auditionable composition drafts with editable notes, harmony and expression. Use the provided new motifs as seeds. They are compositional sketches, not existing commercial tracks. Expand into complete short forms without imitating a named artist or copying a known melody. Generic blues harmonic forms are reusable musical structures; do not claim the form itself is novel.

The four sketches are Tilted Blue (C blues, 96 BPM), Almost, Then Away (F brushed jazz, 96 BPM), Corner Pocket Rag (C, straight syncopated 120 BPM) and Velvet Orbit (D minor, 80 BPM). Keep the straight rag-influenced feel distinct from swung blues. Provide piano/lead, bass, brushes and object-motif stems. Include rest/space so animation events can be heard.

## Required assets
For each piece: authoritative symbolic JSON, MIDI, optional MusicXML when convenient, a rendered audition mix, stems, a human-readable lead sheet in Markdown, and a manifest with tempo/meter/key/harmony, loop boundaries, motif IDs, instrument/preset IDs, seeds, provenance and hashes. Build one hero piece completely before expanding all four.

Use reliable local MIDI generation such as music21 or a simpler supported library after verifying it. MIDI is a note/event interchange file, not an audio recording. Supply an actual renderer for audition, or explicitly mark audio pending. Retain a procedural no-download synth fallback. Optional high-quality piano/bass/brush samples must have documented licences and redistribution rights; do not silently fetch commercial loops or assume installed General MIDI brushes sound realistic.

A damped multi-partial keyboard sound, a short plucked bass and filtered-noise brush approximation are acceptable technical fallbacks, but label their timbral limitations and audition them. Accurate instrumental realism is not an acceptance claim.

## Original score development
Preserve the seed motif identity while composing contrasting answer phrases. Use explicit durations and rests, register limits, chord functions and turnaround/cadence locations. Create two bounded variations per piece: sparse/suspended and animated/accented. Musical quality must be assessed by a person listening to A/B exports; no language-model rating alone constitutes an audition pass.

Represent notes in MIDI pitch numbers and durations/onsets in integer quarter-note PPQ ticks. Document C4=60. Use an explicit tempo map even when constant. Distinguish harmonic chord events from key-region events. Support future transposition/revoicing at a selected boundary rather than pitch-shifting the already mixed waveform.

Define separate lanes for:
- Phrasing: phrase boundaries, rests, cadence targets and density.
- Dynamics: bounded velocity/gain curves with preserved overall headroom.
- Articulation: gate/duration ratio, attack/release and accents.
- Ornamentation: sparse approaches, grace notes and turns within note/rate/register budgets.
- Timbre: registered synth or sample palette parameters.

Do not let every motion update change every lane. Double-blink key changes leave gain/articulation parameters invariant unless a separately approved animation rule changes them.

## Brush rhythm catalogue
Implement exact lookup by `groove_id` and version, not embedding/RAG retrieval. Keep `composition_id`, pitched key and unpitched `groove_id` separate. A brush groove identifies a rhythm/technique recipe, not the tune or a tonal key.

Use the seed techniques: continuous sweep, light tap, accented swish and hi-hat chick. Store start/duration in PPQ ticks, technique, hand/stroke direction when meaningful, velocity/envelope, optional sample ID, sweep/filter recipe, humanization limits and seed. Preserve continuous sweeps as envelopes; MIDI drum hits alone cannot fully encode them. Export MIDI as a declared approximation alongside the authoritative brush JSON.

Catalogue at least light swing, straight rag support and sparse ballad textures. Record which events are swingable. Apply swing exactly once, never to collision Foley, continuous sweep boundaries or already-resolved timestamps. Deterministic humanization must be reproducible, bounded, loop-safe and separately configurable from event synchronization. Provide resolved event timing for exact replay.

Loopable brush audio needs aligned boundaries and controlled crossfades/tails. Use a continuous prepared sweep where appropriate. Do not create clicks with abrupt random-buffer changes. No sample download is required for the initial prototype.

## Rendering and quality checks
Reference sample rate may be 48 kHz, while a live browser context can use another actual rate. Store and handle the real rate. Export stems at matching start time and duration, including a declared tail policy. Keep unpitched percussion unchanged under key transposition. Maintain audible headroom and a conservative initial playback gain; do not claim a dBFS ceiling guarantees safe physical listening volume.

Test bar lengths, ticks, rests, note ranges, velocities, unknown groove IDs, beat/second conversions, swing double-application, transposition of pitched voices only, deterministic generation, stem alignment and sample-peak/clipping checks. A symbolic-only MIDI export does not satisfy a non-silent audio render test. Do not normalize away the intended expressive dynamics.

## Exit gate
At least one complete, audible, approved-capable hero arrangement and all four symbolic forms; exact groove lookup and three authored brush recipes; renderer provenance; golden score/render fixtures; a specific human audition checklist and statuses. Mark anything not listened to as `AUDITION_PENDING`. No arbitrary third-party backing track or black-box audio model is required.


---

# Phase 2D: geometry-to-music planning with human approval

Prerequisite: phase 1 fixtures. Read AGENTS, VISION, CONTRACTS and the symbolic-jazz-arrangement skill. Own `modules/arranger/`, its local tests and `handoffs/02D.md`. Work against fixture scene summaries, score catalogues and capability interfaces. Do not edit the Blender exporter, music asset generator, audio engine, service root or shared schemas.

## Objective
Translate a scene and creative brief into an editable, validated musical plan. This does not require training another end-to-end neural model. Build a deterministic mapping baseline and an optional GPT Astra planning adapter that proposes variations over the same bounded representation.

## Inputs and model role
Consume scene objects and their stable identities, world-space geometric properties, compact sampled motion envelopes, pair surface-gap/relative-motion events, selected rendered frames when useful, the actual symbolic music/brush catalogue and the human's creative brief. Never send raw EEG or device identifiers to the model.

The model may request approved capability queries, such as exact event details, score/groove lookup, candidate rendering and validation. It cannot assume unavailable plugins exist, choose arbitrary filesystem paths, install software or execute generated code as an arrangement. Use the phase 1 registry. Implement tools as typed local functions/CLI adapters first. MCP exposure is optional and must wrap existing tested capabilities, with schemas and health checks.

Use a verified OpenAI model ID from configuration and a small capability preflight. Structured outputs enforce shape; separate checks enforce musical and timing semantics. Handle refusal, truncation, unknown IDs, invalid numeric ranges, timeouts and rate errors. Do not silently change model names or API endpoints to get a passing run. An exported summary plus manual JSON-plan import provides a human-reviewed no-API path. The user's ChatGPT subscription is not assumed to provide application API billing.

## Deterministic baseline mapping
Create explicit, editable rules with smoothing and hysteresis:
- Approach/declining surface gap: bounded tension, density or anticipatory ornament; no claim that proximity has one objectively correct musical meaning.
- Near miss: a phrase approaches a cadence and defers/resolves according to the chosen style, with its event time intact.
- Collision onset: synchronized Foley or a registered pitched accent at exact scene time; sustained contact is a separate texture.
- Separation: decay/release or thinning of orchestration.
- Up/down motion: configured melodic-register/contour direction and eligible modulation direction.
- Size/surface area/material tags: an artistic timbre/register mapping within bounds, explicitly not a physical acoustic prediction.

Give objects persistent motif and palette IDs. Limit simultaneous voices and event density. Preserve silence and foreground accents. Smooth frame-level features so distances do not chatter into dozens of musical changes. Phrasing, dynamics, note gate, ornaments, harmony and timbre are distinct lanes with separate bounds and priorities.

## Modulation and expression policies
Default double-blink queues one key-change request, while current gain and articulation settings remain fixed. Consider only a small pre-approved transition graph. A useful first graph allows signed tonic shifts of +/-2 semitones, with optional +/-5 only after audition. Define key mode, tonic pitch class and register movement separately because pitch classes have no intrinsic up/down order. Bound register to prevent cumulative octave drift.

For supported keys, render a brief pivot or dominant preparation and establish the new tonic through a cadence or arrival. Change/revoice melody, bass and harmony consistently. Keep brushes and nonpitched Foley untransposed. A valid chord change within the same key must not be labelled modulation. During a short demo, a clear direct transition into an explicitly established new tonal region is acceptable; do not claim a theory check proves perceived tonality.

Precompute or cheaply compile transitions before playback. No GPT call is required for each blink. The chosen direction comes from the scene around the request time under an explicit aggregation policy, not arbitrary global randomness. Define the direction coordinate frame. A practical visual default is the selected protagonist's projected vertical velocity over the preceding 300 ms, with screen-up made positive and a deadband; a world-Z alternative is explicit. Camera motion and screen/world axis conversion must be handled consistently. This is an artistic policy, not a learned physical law. For ambiguous/stationary motion use the documented approved fallback direction or hold; display which policy acted.

Optional triple-blink toggles a pre-approved bounded expressivity preset at a musical boundary. It must not also fire the double-blink action. Blink amplitude controls remain disabled until independently evaluated. The runtime action parser, rather than the language model, enforces those choices.

## Approval, caching and parameter search
Generate at most a small configurable number of candidate plans, for example three. Each includes an explanation tied to real object/event IDs, changed lanes, bounds, assumptions and uncertainty. Presentable outputs include exact plan diffs and short audition renders. Human approval freezes a content hash. Approve a bounded family of transitions/presets so the live performer need not confirm every blink. A new unapproved plan cannot replace the active one during playback.

Cache by scene/score/brief/model/schema/version and parameter hashes. Use bounded retries, wall-time and concurrency limits. The deterministic baseline and the last approved plan remain available if the API fails. Label cached, manual and live-generated provenance.

An optional Optuna sweep may adjust smoothing, density, voice-leading penalties, gain limits and anticipation length against objective technical checks. Never call such a score universal musical quality. Keep subjective audition ratings separate and record who/when evaluated them. Do not tune EEG model thresholds in this module.

## Tests
Validate IDs, units, times, typed curves, parameter ranges, approved hashes and pitch/register bounds. Test seed reproducibility and cache invalidation when a trajectory changes. Confirm that changing one interaction updates only affected score regions/objects where the policy allows. Ensure identical inputs with the same approved plan produce identical event sequences.

Test missing API keys, unavailable models, malformed schema-valid but musically invalid plans, unknown grooves, refusal, timeout, stale asset hashes, conflicting lanes and repeated requests. The baseline must render usable event output without external service calls. Model text must never mutate code/config/credentials.

## Exit gate
A fixture scene becomes a validated baseline plan and, when credentials allow, an actual schema-validated GPT proposal with review metadata. Manual import/export, deterministic constrained modulation and golden ScoreEvents all work. Provide an honest live-API test status and a human audition handoff. Do not build a multi-agent theatre UI or train an audio model.


---

# Phase 2E: local performance UI, editable score playback and clock discipline

Prerequisite: phase 1. Read AGENTS, VISION, CONTRACTS, the audiovisual-integration skill and fixture contracts. Own `apps/web/`, `packages/audio/`, their local tests and `handoffs/02E.md`. Consume fixtures and exposed interfaces without editing other workers' modules or root locks. Propose shared dependency changes to the integrator.

## Objective
Build one focused local authoring/performance interface with reliable audiovisual playback. The browser performs deterministic score execution. GPT planning, Blender rendering and Muse processing remain outside the timing-critical callback.

## Interface
A single screen contains the scene preview; three lanes for soundtrack, collision/Foley and accepted gesture controls; an editable arrangement summary; current key/chord; brush-groove selector; source/status indicators; master volume/mute; play/pause/seek; Muse arm/disarm and keyboard/replay fallback. Optional waveform/candidate diagnostics live in a collapsible panel. Avoid an agent dashboard, user accounts, billing, complex DAW controls or a game.

Clearly indicate LIVE_MUSE, REAL_REPLAY, SYNTHETIC_TEST or KEYBOARD and LIVE_GPT, CACHED_PLAN, MANUAL_PLAN or BASELINE. Never substitute a recording silently. Display quality/warmup and the next scheduled modulation rather than pretending gestures execute instantly.

## Audio engine
Use Web Audio directly or a verified small scheduling library. Implement enough piano/lead, bass, brushes and effects to audition the score contracts. Coordinate synth/sample preset IDs with phase 2C. A local procedural fallback must work without downloading samples or calling a model.

Use audio-context time as the scheduling clock and explicitly map it to project/media time. Handle actual sample rate and audio output latency where exposed. JavaScript timers can fill a bounded lookahead queue; they must not be the sole source of audio onset precision. Use native scheduled nodes or AudioWorklet when justified. Keep renders, network calls and large JSON parsing off the audio work path.

Document scheduled, rendering and measured acoustic/visual onset as distinct timing quantities. Use the video frame callback/time when available and a tested fallback. Measure drift rather than claiming a master clock guarantees synchronization. Apply bounded correction policies; never repeatedly seek the video every frame. Display buffering/seek state and handle browser suspension. Target a tested Chrome/Chromium path first and check Safari when available; report actual tested browsers rather than promising all-browser parity.

Playback starts only after a user gesture unlocks audio. Provide a conservative gain default and hard mute. Limit peaks and polyphony; do not claim a digital peak ceiling guarantees a safe physical listening level.

## Control semantics
A valid double-blink event queues one modulation at the next approved bar/phrase boundary. Show acceptance immediately after detector commitment. The musical-boundary delay is visible. Use the same `ControlAction` for Muse, replay and keyboard so fallback exercises real logic. Preserve source provenance. IDs make duplicate deliveries idempotent.

If a control arrives after the current scheduling deadline, defer to the next feasible boundary and show it. Do not schedule notes in the past. A modulation updates future pitched notes coherently, while already sounding notes finish or crossfade under a defined rule. Avoid stuck notes and abrupt clicks. Unpitched brushes/Foley retain their original pitch and exact scene-event alignment.

Pause/seek/resume clears/reschedules the future audio queue and partial control requests using a new transport generation ID. Distinguish historical gesture markers from new controls. Loops do not replay the same external gesture action. Cap pending requests and specify how repeated accepted gestures coalesce rather than creating a minutes-long backlog.

Triple-blink expression is visible only behind the experimental flag. Count disambiguation belongs upstream; the UI must not fire both actions for one event. Double-blink alone does not change gain, brush level, articulation or the expression preset.

## Authoring and export
Load a matched video/scene bundle; reject incompatible hashes or offer a clearly marked inspection-only mode. Show mapping rules and allow audition/approve/reject of candidate plans. Select a prerecorded trajectory variant and invalidate/reload the matching plan. Live mesh editing and background Blender rerendering are stretch goals, not demo prerequisites.

Provide mute-lane A/B comparison: silent animation, stock symbolic baseline, scene-aware approved plan and live modulation. Export a performance event log with score/scene/control hashes. An offline audio render should use the same resolved score/control event semantics. Full video muxing can be handed to the integration/export adapter.

## Tests and exit gate
Unit tests with fake clocks cover synchronization calculations, seek/resume, duplicate controls, late controls, source reconnect, invalid plans and unrelated-lane invariance under double-blink. Browser tests cover user audio unlock, source indicators, queue behavior, assets failing to load and a fully offline fixture demo. Use actual audio rendering checks for non-silence, durations and peaks; a DOM test alone does not establish sound output.

Deliver one complete fixture performance, golden event logs, measured timing report where test tools allow, and a human audio/visual QA checklist. Explicitly mark listening and live hardware checks not performed. No fabricated live EEG trace.


---

# Phase 3A: compare blink models, lock evaluation and export a deployment artifact

Prerequisite: phase 2A and real, independently labelled recording sessions. Read AGENTS, VISION, EVALUATION, LINEAGE, contracts and the blink-evaluation skill. Own `modules/muse/training/`, `modules/muse/evaluation/`, local detector-model implementations and `handoffs/03A.md`. Do not alter root schemas or musical controls. Keep the baseline API stable.

## Objective and scientific boundary
Seek very high event-level recall with very few false activations. Do not assume unsupervised learning is inherently more accurate. Deliberate and natural blink clusters can generate overlapping observations; an unlabelled cluster has no intrinsic intent label. The owner providing positive double-blink trials is supervised information. Explore semi-supervised and unsupervised methods, but promote only measured improvements against simple baselines.

No real data means build the training/evaluation pipeline, tests and acquisition instructions, then report `INSUFFICIENT_REAL_DATA`. Never train on synthetic fixtures and publish the result as Muse performance. Never report cross-person generalization from one person's recordings.

## Data and split integrity
Audit annotations before training. Use participant, recording/session, headset refit and trial groups. Train/development/final-test sessions are split BEFORE windows, augmentations or feature fitting. No windows or overlapping chunks from a session can enter different split roles. Reserve genuine natural-activity recordings and a later headset-refit session for final evaluation.

Fit scaling, feature selection, dimensionality reduction, pseudo-labels, template construction and hyperparameters only on the allowed training/development partition. Self-supervised use of test recordings is still leakage. Freeze any deployment calibration/adaptation rule before testing, use a separate declared calibration segment, and never retrospectively normalize from future samples. Report calibrated versus uncalibrated deployment separately.

All reported online results must use causal filtering and actual temporal windows. Offline zero-phase filters, centred windows and future-frame knowledge may be used for annotation aids only, not as evidence of live accuracy. Avoid suppressing the ocular artifact being detected. Raw data remain auditable and local.

## Model comparison ladder
A. Unchanged RAGTM detector when actually available; otherwise clearly named new baseline.
B. Causal robust-threshold/template candidate detector plus finite-state gesture grammar.
C. Small supervised regularized logistic model or gradient-boosted tabular classifier on candidate waveform/context features, with training-only calibration and the same grammar.
D. Semi-supervised self-training or label spreading, using genuine training-only unlabelled intervals and an independent labelled development set. Cap pseudo-label quantities, require calibrated confidence, track class balance and audit likely errors. Do not simply relabel everything the baseline accepts as perfect truth.
E. An unsupervised anomaly/cluster baseline such as Isolation Forest or training-only PCA plus clustering. It identifies unusual patterns, not intent; cluster semantics/thresholds require labelled evaluation. Explain when movement or electrode artifacts dominate its novelty score.

A self-supervised small temporal encoder is a stretch experiment only after the above produce trustworthy replay evaluation and there is enough real data. Do not download a large EEG model blindly or assume incompatible channel layouts transfer.

Use a common feature/candidate interface, record latency and deployment cost, and keep model-choice comparisons on identical held-out recordings. Inspect raw frontal morphology, bilateral agreement, durations, slopes, amplitude relative to noise and optional motion context. No cue timing, label confirmation, user name or offline annotation metadata becomes a predictive feature.

## Optimization objective
ROC-AUC and average precision/PR curves are diagnostics. Their denominator, sampling scheme and aggregation unit must be explicit. They do not replace evaluation of complete gesture sequences in free-running recordings. A candidate classifier's AUC excludes upstream missed candidates, so also report candidate coverage and full pipeline misses.

Primary model selection: minimize observed false activations per hour subject to a development-set recall floor and bounded latency/availability. Explore a Pareto frontier or constrained Optuna study, with a small trial/time budget. Do not optimize a weighted score that hides unacceptable false activations. Hyperparameter tuning uses grouped development folds only. Final test is evaluated once for a selected frozen model; revisions need a new untouched test set.

Required end-to-end outputs:
- Matched TP, FP, FN, event recall, precision, F1 and one-to-one matching rules.
- False activations per armed hour AND per elapsed monitored hour, with cooldown and abstention durations disclosed.
- Recall over all instructed/verified gestures, including attempts during poor quality or cooldown; additionally report eligible/armed recall with an explicit denominator.
- Onset/final-blink-to-decision latency median and p95; downstream bar wait separately.
- Double versus triple confusion and ordinary-blink errors when applicable.
- Session-specific metrics, quality strata, refit drift, availability and suppression reasons.
- ROC-AUC, PR diagnostics and confidence intervals with the evaluation unit clearly labelled; never derive these from only accepted positive detections.

Use time-based one-to-one event matching with a frozen tolerance, fixed exclusion rules and independent labels. Count duplicate activations as FP. Do not widen the matching interval after seeing errors. Report ambiguous label counts and sensitivity analyses rather than dropping every difficult example.

## Honest uncertainty and release status
Aspirational targets: event recall >=99% and false activations <=0.5/hour under tested conditions, with a lower false rate as a stretch. These are goals, not a deadline guarantee.

With n successes in n independent opportunities, a one-sided 95% binomial lower bound is 0.05^(1/n). For 100/100 this is about 97.05%; roughly 299/299 are needed for a 99% lower bound. Session dependence makes this idealized calculation optimistic, so also use session-level uncertainty or explicitly report inadequate session count.

With zero false activations in T hours under a stationary Poisson assumption, the one-sided 95% upper bound is -log(0.05)/T, approximately 3/T per hour. Zero in 30 minutes allows roughly 6/hour; about six hours of relevant negative exposure with zero events is needed for a 0.5/hour upper bound. Report the assumptions and do not multiply evidence by replaying the same recording.

Statuses: `PIPELINE_TESTED_ONLY`, `REAL_DATA_EXPLORATORY`, `SUPERVISED_DEMO_READY`, `TARGET_STATISTICALLY_SUPPORTED`, or `NOT_READY`. Supervised demo readiness uses the separately specified pilot gate and requires transparent limited evidence. It is not equivalent to statistically establishing the aspirational target. A frozen simple baseline can be the correct deployment choice.

## Gesture grammar and exploratory controls
Double/triple mode must delay commitment until the closing interval; report that latency tradeoff. Do not emit a double action and later claim it was a triple. Default double-only mapping remains key change with invariant gain/articulation. Test a sequence rejected for excess blinks rather than treating two prefixes as valid doubles.

Amplitude-derived control requires within-session normalization, labelled intended effort categories and held-out refit repeatability. Voltage amplitude is affected by contact/motion and is not a verified physical blink-strength measurement. Keep it disabled unless it improves a defined expressive task. Do not directly map unbounded raw amplitudes to loudness.

## Artifact and exit gate
Export the chosen model, preprocessor parameters, channel/unit assumptions, grammar, thresholds, calibration procedure, train/data/version hashes, feature names, measured latency and an evaluation card. Prefer a safe documented format; do not load untrusted pickle files. Provide an unchanged real-replay command and a rollback to baseline. Online adaptation is off during the demo unless independently validated and explicitly enabled.

Run a held-out real session plus reconnect/packet-loss and replay-determinism tests. Separate software-only faults from empirical performance results. Write a concise failure taxonomy and the next targeted collection action. Do not keep optimizing indefinitely or manufacture 100% results to satisfy the aspiration.


---

# Phase 3B: integrate one complete performance before expanding scope

Prerequisites: phase 2B-2E handoffs and either the real Muse baseline or a clearly labelled replay/keyboard adapter from phase 2A. A newly trained detector is optional. Read AGENTS, all handoffs, VISION, CONTRACTS and EVALUATION. You are the integrator and may reconcile shared schemas, root locks, service mounting and cross-module tests through recorded decisions. Preserve worker commits and avoid broad rewrites.

## First vertical slice
Load the hero scene and matching sidecar -> exact catalogue lookup of Tilted Blue and a light brush groove -> baseline mapping or approved GPT plan -> deterministic audio playback -> one double-blink/keyboard modulation -> exported mix/performance log. Complete this before adding all ten scenes, every model, triple gestures or a live editor.

Start with replay and keyboard to expose integration failures independently of hardware. Then connect the real headset without changing downstream action semantics. Use the best frozen real-data detector available, including a simple baseline when it performs better. Source changes are explicit in the UI and log.

## Clock and identity reconciliation
Trace one real control end to end: original sample index/time -> candidate -> final blink -> detector decision -> bridge receipt -> requested transport position -> scheduled musical boundary -> rendered note change. Display these distinct delays. Use handshake/offset estimation between monotonic clocks where necessary; never equate Python monotonic time with browser performance time by numerical value.

Trace one visual contact: evaluated scene time -> interaction event -> exact Foley schedule -> displayed video time. Confirm frame origins, fps/base, loop durations, encode offsets and audio output latency are handled. Separate scheduled offset from measured audiovisual offset. Reject stale sidecars and mismatched media hashes.

Deduplicate event IDs and bound queued controls. On pause/seek/refit/reconnect, clear partial gestures and stale transport generations. No missed gesture queue should discharge after reconnection. A Muse failure leaves the current composition playing.

## Human approval and demonstration
Provide scene/score selection, rule inspection, candidate plan diff, short audition and approve/reject. Freeze a plan plus its approved modulation family. The performer may then blink without an approval modal. A new plan cannot silently replace a playing one. New scene variants invalidate affected caches.

The visible demonstration is:
1. Play a short silent animation.
2. Add the original groove and baseline phrase.
3. Enable scene-aware anticipation, collision accents and separation release.
4. Trigger a double-blink that requests a visible, musically timed key change while volume/articulation stay unchanged.
5. Select the matched near-miss variant, showing changed music and absent collision Foley.
6. Export the played performance and show which inputs/plans/controls produced it.

This is animation, not a game. A judge does not need a headset for the demo to remain understandable. No unverified inference about emotions, focus or stress belongs in the UI or pitch.

## Export
Resolve the complete performance log to the same symbolic event sequence used by live playback. Produce a stereo audio file, separate stems, score/control log, arrangement/scene hashes and a muxed video where a verified local encoder is available. Handle source/output duration, tails, sample rates and video timestamp offset explicitly. A fallback audio-plus-video bundle must be labelled when muxing was not performed.

## Integration tests and resource management
Run scene contract checks, music tests, model/replay tests and browser tests from a clean local start. Exercise no network, no API key, API timeout, unavailable samples, stale cache, invalid JSON, dropped stream, bad quality, duplicate/out-of-order events, excessive controls, rapid pause/seek, audio context suspension and unknown groove/model IDs.

All degraded paths must preserve the active performance or give an actionable recovery. Do not silently fake success. Keep raw EEG private and service binding on localhost with appropriate local-origin restrictions. No secrets in frontend bundles or logs. Limit render and training concurrency while capturing EEG or playing the demo.

Report peak levels, scheduled/observed timing, event correctness, real-source provenance and human audition status separately. Do not let a green test suite imply musical quality or empirical detector reliability.

## Exit gate
A documented one-command replay demo and an actually exercised live-Muse path when hardware is available; one complete exported performance; correct default gesture behaviour; approved arrangement and provenance; no schema drift; explicit remaining limitations. The core remains demo-ready with network/headset loss. Cut stretch goals before modifying tests to hide failures.


---

# Phase 4: independent release audit and five-hour demo rehearsal

Read AGENTS, VISION, EVALUATION, RUNBOOK, STATUS and all handoffs. Act as the release engineer. First assess the existing product; do not expand it. Own final cross-module fixes, evidence and the demo runbook. Preserve a reproducible baseline and revert risky last-minute changes.

## Evidence audit
For each MUST requirement inspect the implementation and an actual evidence artifact. Distinguish tests run from tests merely written. Verify real/synthetic/replay/device provenance, model/data/split hashes, source/scene/video alignment and arrangement approval. Check the RAGTM reuse claims against actual inspected code or label them unavailable.

Inspect the fitted blink artifact and report: real session counts, independent refits, intentional gestures, true/missed/duplicate commands, natural-activity exposure, false activations, availability, latency, thresholds and confidence bounds. Do not re-tune the final test. A small perfect test remains a small test. No claim of 99%-plus performance or near-zero false rate without relevant evidence.

## Rehearsal gates
- Cold-start replay demo from documented commands without private data or API credentials.
- Real Muse connection, fit, warmup, arming and several deliberately performed gestures when the user is present.
- A natural-activity interval while speaking and watching the animation, with false activations recorded.
- Pause, seek, loop, late/duplicate gesture, stream loss/reconnection and unavailable API.
- Human audition on the actual output device: piano/bass/brush balance, believable suspense, clearly audible modulation, absence of abrupt clicks or unbearable transients.
- Exported performance matches the played sequence, within declared timing/renderer limits.

For subjective checks, record a simple human rating and a specific observation. Never state that the agent heard audio unless an actual listening-capable test occurred. Ask for bounded human audition actions through the app/runbook rather than pretending approval.

## Scope freeze
Keep one hero scene, one score, one brush groove and double-blink modulation polished. Hide unsupported gesture classes and unvalidated intensity control. Preserve the other prepared scenes/music as test assets or selectable extras only when they pass checks. No emotion detection, arbitrary-video reconstruction, universal music generator, large self-supervised model or generic plugin marketplace is needed.

## Event-day runbook
Use the planning budget in `.brief/README.md` only if the organizer allows the prepared materials. The plan must identify prepared code/data/models/music/renders and what is built during the event. If prior work is forbidden, document the smaller compliant version and do not misrepresent authorship or development time.

Provide a 60-90 second script explaining the geometry-to-score mapping, showing a near-miss/impact comparison and one genuine blink modulation. Keep a labelled real replay and a keyboard control ready. A fallback can demonstrate the composition system while honestly separating the failed hardware component.

## Final deliverables
A release checklist with PASS/FAIL/NOT_RUN, tested platform/browser/device versions, one reproducible command sequence, last-known-good artifact hashes, a privacy/license inventory, a concise known-limitations list, and a demonstration recording only if actually captured. Summarize measured performance without inflated claims. Do not force a success label; end with the real readiness status and the smallest remaining corrective task.
