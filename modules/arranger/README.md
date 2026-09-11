# Phase 2D — editable local arrangement planning

`Context` consumes canonical scene/state/interaction/composition/groove records. `Context.from_summary` accepts the Phase 2B compact summary and exact Phase 2C catalogue entries. Full local states can be supplied instead when a causal request needs denser motion coverage. The compiler rejects missing IDs, wrong units/clocks, duplicate samples, changed input hashes, unsupported modes, unknown palettes/grooves, conflicting curves and exceeded voice/density/duration budgets.

All functions are synchronous and create no import-time process. `api.router` exposes health and a bounded data-only `/preview`; capture, renders and network calls are explicit CLI/library actions. Shared root mounts are integrator-owned. The legacy one-record capability dispatcher remains separate: its generic arrangement signature does not contain a scene/music bundle, so it is not falsely marked executable.

From repository root:

```sh
PYTHONPATH=.:src .venv/bin/python -m modules.arranger health
PYTHONPATH=.:src .venv/bin/python -m modules.arranger preview --input artifacts/arranger/fixture/input.json --output artifacts/arranger/fixture/preview.json
PYTHONPATH=.:src .venv/bin/python -m modules.arranger summary --input artifacts/arranger/fixture/input.json --output artifacts/arranger/fixture/summary.json
PYTHONPATH=.:src .venv/bin/python -m modules.arranger import --input artifacts/arranger/fixture/input.json --plan artifacts/arranger/fixture/plan.json --output artifacts/arranger/fixture/import.json
PYTHONPATH=.:src .venv/bin/python -m modules.arranger diff --plan before.json --other after.json
PYTHONPATH=.:src .venv/bin/python -m pytest modules/arranger/tests -q
```

Input is JSON `{context:{scene,states,interactions,composition,groove},policy?:{...},brief?:string}`. `Policy` is a typed, range-checked module sidecar; unknown fields fail. Its defaults bind compiler version, parameters and creative brief into the plan provenance config hash. The scene hash covers the entire supplied canonical scene/state/event set; the composition hash covers score **and** exact groove. JSON exports use sorted finite JSON plus a newline. Approval hashes bind the exact persisted UTF-8 bytes, including whitespace, rather than a reconstructed equivalent.

## Editable mapping policy

Default five separate numeric curves: approach→ornament (0..1), separation→dynamics (-12..0 dB), surface gap→phrasing (0..1), collision→timbre (0..1), world-Z velocity→register (-12..12 semitones). Curves have finite ordered input/output bounds. Unsupported or duplicate feature/lane assignments fail instead of relying on implicit ordering.

Approach smoothly increases an anticipatory chromatic neighbour on existing motif onsets; a .6/.4 Schmitt gate prevents threshold chatter. Spatial gaps at/below the editable 0.02m hysteresis margin do not create anticipatory ornament. This creates bounded tension without filling scored rests with frame-rate note-ons. Near-miss phrases use an unresolved second before the event and a delayed tonic afterward, only in affected object/time windows. Separation releases dynamics over 0.5 seconds. Exact collision/onset, contact sustain and release create separately labelled unswung Foley ScoreEvents; relative speed selects a soft/bright artistic contact timbre. Signed world-Z register features are exponentially smoothed. Initial evaluated area selects a bounded octave; material tags are not supplied in the canonical inputs and no physical acoustic inference is made.

Every object retains its sonic-identity-derived motif ID. The first three stable sorted object IDs have foreground notes; others retain editable identity but are silent under the default budget. Bass, up to three harmony voices, brushes and foreground motifs remain separate. Events over 12 simultaneous voices or 80 starts/second fail preparation rather than silently dropping collisions. Up to 120 seconds, 30,000 states, 512 interactions, 64 objects and 4,096 source notes are supported. This is an intentionally reversible first arrangement policy, not a universal geometry-to-music law. Changing one interaction changes only its local object region (plus the global provenance/plan hashes); changing the object set can change budget selection.

## Approval and deterministic preparation

`baseline` and `compile_preview` produce review candidates, never human approval. `import_plan` validates without changing bytes. `exact_diff` lists changed fields. To approve, a human reviewer must review the exact plan/scene/score/policy and create a canonical `Approval` identifying reviewer/time/decision and `approved_payload_sha256`, with both exact input hashes. `ApprovedSession` requires that approval and exposes defensive copies of active plan, input context and events. A changed score, groove, trajectory, policy, brief or payload requires new approval. Tests construct clearly synthetic approvals; they do not approve delivered music.

`ApprovedSession.request(id, scene_time_s, count=2, source_mode='keyboard')` cheaply prepares a transition in local data. It does not start sound, process EEG or claim that a hardware gesture passed quality gates. Source mode is explicit; the future control executor must accept only quality-gated, unexpired canonical ControlActions and map host/audio/scene epochs before calling this module. Keyboard and labelled replay can exercise this preparation without a device. Singles/triples are no-ops; no amplitude input exists. Duplicate, out-of-order and same-boundary requests are suppressed. No model/provider reference exists in the session.

Direction averages the selected object's preceding 300ms world-Z velocity with a 0.02m/s deadband and causal piecewise-constant weighting. Missing, stale, ambiguous or stationary coverage holds. Camera projection is not used. Default focus is the first stable object ID, explicitly editable before approval. Approved families contain signed ±2 transitions for twelve tonics; no ±5 expansion. Only major, minor and blues-centre single-key source forms are supported. Every pitched voice moves/revoices within 28..96, while gain, velocity, articulation and unpitched brush/Foley remain fixed. Sustains crossing the next approved bar split there; a new major dominant prepares a major/minor tonic arrival one beat later. Harmonic metadata distinguishes mode, tonic and register. An objectively valid direct arrival remains `AUDITION_PENDING`; it is not proof of perceived modulation. This phase compiles ScoreEvents, not the Phase 2E/3B audio transport.

## Optional Responses adapter

`provider.Planner` uses only configured `OPENAI_API_KEY` and exact `OPENAI_MODEL`, with no default model, endpoint substitution or subscription/billing assumption. `GET /v1/models/{exact_id}` checks access/identity, then a small `POST /v1/responses` structured parameter proposal checks capability. Official wire format reviewed: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs). The narrow module proposal schema omits infrastructure/approval fields; local construction yields a canonical ArrangementPlan followed by separate semantic validation. The existing full-plan provider projection remains frozen and unchanged.

At most three candidates, one in-process invocation, one retry per retryable request, and a shared 20-second wall budget (configurable to 45 maximum) cover preflight and proposals. HTTP executes without a shell in a bounded child; timeout kills and waits for that exact child. No generated text can request tools, run code, change files/configuration, or select paths. Only allowlisted compact numeric geometry, event IDs, musical metadata and the deliberate creative brief leave the machine; EEG, acquisition/device metadata and provenance are excluded. No images are sent automatically.

Cache includes scene/score/groove/brief/model/schema/compiler/parameter/seed hashes. Cache bytes and musical semantics are checked on read, and cached provenance remains distinct. Missing key/model, 404, 429, refusal, truncation, malformed data, invalid music, unknown IDs and timeout return the manual baseline without changing any active plan. Cache and output paths are caller-selected local paths; the model never supplies paths. Separate command processes need the future shared job scheduler for global concurrency enforcement; the explicit CLI should be run serially.

`propose` is an explicit network-capable CLI; it never runs during playback. Actual live API status in this environment is `NOT_RUN` because both key and model are absent. Provider tests use an injected synthetic transport; their `live_gpt` wire-path labels are test outputs, not live service evidence.

## Audition handoff

Tracked golden ScoreEvents are synthetic fixture evidence. Delivered plans are drafts; no approval is fabricated. The Phase 2C `render_events` adapter accepts pitched/brush events with exact preset IDs for a candidate audition WAV. Foley remains a separate exact scene-time event stream; the music-only preview must be labelled as excluding Foley. Full audio/video output synchronization, performance UI, real Muse validation and trained accuracy are later gates. No subjective listening result is asserted.
