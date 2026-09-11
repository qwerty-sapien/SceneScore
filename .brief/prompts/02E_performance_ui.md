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
