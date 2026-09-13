# Node 06 runtime integration contract

Status: **implementation GO**, conditional on the integrator's exact candidate cache check and browser integration. This is synthetic scheduler and source-work evidence. Human audition, human approval, actual browser latency and physical audio output remain separate gates.

The reviewed implementation is in `/private/tmp/scenescore-music-runtime`. Integrate only `packages/audio/engine.ts`, `packages/audio/transport.ts`, `packages/audio/tests/music-runtime.test.ts`, this request and `handoffs/music-06-runtime.md`. Other modified paths in the worktree are copied dependencies owned by the coordinator; do not copy them back.

## UI/export API

- `Timeline.currentTonic()` reflects the tonic only after actual scene time reaches the prepared arrival. `Timeline.currentChord(scene)` reads the active progression slot or the source harmony with completed signed changes. It does not show a requested future tonic early.
- `Decision.progression_start_s`, `progression_end_s`, `arrival_scene_s` are scene times. In vertical mode `boundary_s === arrival_scene_s`; the matching `*_audio_s` fields use the engine's anchor. Legacy boundary semantics remain intact. `ack_onset_audio_s` is exactly the captured receipt time plus 20 ms when scheduling succeeds.
- `Timeline.performedEvents()` returns the editable performed score with both acknowledgement notes per accepted request. It preserves completed programs and the actually reached tonic across pause. An interrupted program is clipped at the pause time. Seeking/restarting clears the current performed score history; the control decision journal still records cancellation.
- `renderPerformedOffline(timeline, duration, gainDb=-18, lanes={soundtrack:true,foley:true}, rate=48000, journal?, stem?)` renders the performed score with original source buffer offsets. `stem` uses the existing `piano | bass | brush | foley` mapping. It retains the source oscillator phase, decay and articulation when a sustain resumes after an overlay. It applies the same score start/end fades and supports the existing mix journal. Legacy `renderOffline` defaults are unchanged.
- The offline result is a render of the score schedule. It does not reproduce live scheduler jitter or establish acoustic/hardware sample parity. No API creates approval.

## Runtime and budgets

`bundle.music_vertical` enables the new implementation. The canonical ControlAction still passes all existing validation, source, quality, clock, expiry, plan, duplicate and pending checks. The supplied signed step is consumed unchanged.

Preparation loads the model's 216 voiced entries and its allowed default programs/dyads. At most 512 validated `bundle.holds` are used to remove conflicting programs before playback. Submission then uses the existing at-most-48-arrival by three-lead selector, without reading the source arrays or allocating a score-sized object. An explicit conservative performed-event budget is checked from precomputed costs before scheduling. One request remains pending until the prepared landing ends, even though the tonic changes earlier at arrival.

Engine submission schedules the two cached dyad sources at receipt +20 ms before materializing the performed score. It stops only bass/harmony sources at progression start. Independent lead/object/brush/Foley sources keep running. A partial dyad scheduling failure stops and disconnects all task-created dyad nodes and removes the pending program. A request during the audio pre-roll is validated, then suppressed as `transport_preroll`.

All pitch alternatives, program voices and acknowledgements are prepared before play. Pitched buffers are shared across event identity, velocity and dynamics: those two independent scalar controls are restored exactly as per-note gains. Master gain, lane mixing and articulation remain independent. `prepareAsync()` cooperatively yields with a four-millisecond target and caches no more than 128 MiB of mono Float32 source data. It fails the projected budget before allocating an oversized set. Original polyphony reserves two acknowledgement voices; the unaffected-source budget reserves four harmonic program voices plus the dyad. The performed offline renderer also reuses buffers and enforces 128 MiB. Cancellation clears its exact timer and prevents stale readiness publication.

Pause, seek, close and restart cancel owned audio nodes/timers. An interrupted vertical take becomes discontinuous, so it cannot pass the existing uninterrupted-performance export gate. Restart prepares the restored generation before accepting controls.

## Actual verification

Commands run in the isolated worktree:

```text
npm run typecheck
SCENESCORE_DEFAULT_BUNDLE=/Users/agent/Desktop/SceneScore/apps/web/public/studio/contact-brush_swing_light_v1.json node --import tsx --test packages/audio/tests/*.test.ts
node --import tsx --test --test-name-pattern='oversized pre-play|offline performed rendering' packages/audio/tests/music-runtime.test.ts
git diff --check
```

The final complete suite had **55 passed, 0 failed, 1 skipped** (session 3836, exit 0), including the oversized-cache guard, performed offline phase/stem test and unchanged protected-voice envelope assertion. Earlier focused offline/memory checks also both passed. Typecheck and diff check passed after all edits. The sole skipped check requires `SCENESCORE_MUSIC_BUNDLE` to identify the new exact prepared candidate, which was not available to this worker. The coordinator must run it at 48 kHz before claiming candidate integration.

The existing default bundle also passed its six Muse preparation tests at 48 kHz. Final synthetic evidence: 308 original events; 62,527,688 resident buffer bytes; 80 cooperative refresh slices; maximum observed slice 4.239 ms. This is a fake AudioContext observation of the retained legacy path, not browser or physical latency.

The focused tests additionally verify: two cached onsets before guarded source access; no synthesis in submit; protected sustain continuation; full-buffer phase offsets after a harmonic cut; actual tonic/slot state; pending rejection through landing end; two successive signed modulations and four exported dyads; hold exclusion; pause/seek and partial scheduling cancellation; exact gain restoration; completed-end restart; and cancellation without stale cache publication.

No browser, server, container or detached job was started. All test tool sessions exited 0. The exact candidate and browser/human gates remain with the integrator.
