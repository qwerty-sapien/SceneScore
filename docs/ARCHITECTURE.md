# Architecture — documentation design, no implementation

Choose local TypeScript React/Vite and Web Audio for authoring/performance, with a small Python FastAPI/WebSocket service for Muse and planning. NumPy/SciPy/scikit-learn and BrainFlow are candidates, not installed or compatibility-locked requirements. Blender uses its own installed Python. No GPU, database, cloud hosting or framework for autonomous agents is required.

## Modules and dependencies
| Module | Responsibility | May consume |
|---|---|---|
| `contracts/`, `fixtures/` | Canonical JSON Schema and cross-language conformance | Immutable brief semantics |
| `modules/blender/` | Generate/evaluate/export scenes | Contracts and recipe seeds |
| `modules/music/` | Editable compositions, groove catalogue, render recipes | Contracts and music seeds |
| `modules/muse/` | Capture, annotate, replay, causal baseline, later evaluation | Contracts; local raw data |
| `modules/arranger/` | Geometry mapping, provider projection, semantic validation | Scene summaries, music catalogue, contracts |
| `services/local/` | Bind loopback, mount module routers, enforce request limits | Module interfaces; never audio scheduling |
| `packages/audio/` | Score scheduling, transport, mixing, offline rendering | Approved ScoreEvents and manifests |
| `apps/web/` | Authoring/review, transport UI, visible provenance | Contracts, audio, service adapters |

Modules expose router/CLI adapters without modifying service root. Phase 1 fixes interface signatures and fixture conformance before worker launch. Modules do not import UI or each other's private implementation. Shared changes go through the integrator.

## Runtime paths
`Blender evaluated scene → SceneManifest + ObjectState + InteractionEvent → ArrangementPlan → semantic checks → human-approved hash → ScoreEvents → local audio`.

`Muse / recording / keyboard → BlinkCandidate → GestureEvent → ControlAction → musical-boundary scheduler`. Keyboard uses an explicit labelled adapter; it must not manufacture an EEG trace. Detector output never defines ground truth.

GPT Astra is a requested planning role, not a verified application API model ID. A configured provider may propose constrained data from compact scene/music summaries. Never send raw EEG. No model/tool network call occurs per frame, audio sample or blink. Model outputs and imported scene text are untrusted data, not code or tool authorization. Local validation plus preview/audition and exact-hash approval precede plan activation. Editing any approved input/plan invalidates approval.

## Clock ownership
The browser audio transport is master for musical time. A tempo map converts quarter-note ticks into transport seconds. AudioContext time maps from an explicit transport anchor; video scene seconds use a recorded scene/transport mapping. Acquisition carries device/sample clocks and monotonic receipt time; an explicit adapter estimates offset/drift and uncertainty to browser transport. Wall-clock UTC is provenance only. Do not assume device seconds equal host or scene seconds.

Clock maps have version/epoch, anchors and uncertainty. Seek, reconnect or resume starts a new relevant epoch, cancels stale pending actions and resets anchors. Deduplicate action IDs; reject out-of-order/stale controls and report reasons. If mapping is uncertain, suppress controls and retain music. Modulation requests select the next approved bar/phrase beyond the scheduling horizon; late requests defer to the next eligible boundary or expire visibly. Phase 1 defines fake-clock tests; Phase 2E measures the horizon and latency rather than guessing. Foley stays at absolute scene time, never blindly on a beat grid. Loops retain object identity but use loop-instance event IDs.

## Mapping and graceful degradation
Approach/separation can drive bounded density, dynamics and phrasing; surface gap can guide tension/ornamentation; validated impact drives Foley and optional score accents; world-space size/shape informs stable timbre/register presets. These are creative mappings, not physically accurate acoustics. Register contours and modulation sign follow VISION's explicit policy.

Network/API loss → approved cached plan or visibly manual plan. Headset loss/bad quality → music continues, disarm live controls and offer visibly replay/keyboard mode. Missing sample → approved identified local fallback, otherwise mute affected lane with error. Invalid/stale plan → keep last compatible approved plan or stop activation. Missing Blender → fixture sidecars only, with synthetic mode shown. No silent provenance substitution.

## Approval and resource boundaries
The user approves musical content and event-rule compliance; the integrator approves shared interface changes. Participant recording requires consent and verified device settings. Capability preconditions include schemas, paths, permission, cost and concurrency budgets. Cache content/config/tool-version hashes; revalidate approval on reuse. Hardware capture and CPU-heavy renders cannot overlap a participant session. Record exact jobs and stop them on task exit.
