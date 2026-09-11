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
