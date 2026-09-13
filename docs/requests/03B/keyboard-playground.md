# Keyboard-to-music playground

Authorized by the user's request on 2026-09-13 to isolate UI key events, ornamentation and music playback. This is a standalone interactive draft audition, not the Phase 4 release or an approved scene performance. Integrator owns these new web/audio files. Existing scene studio, frozen schema, user modifications and frozen media-review assets are untouched.

Launch `start-keyboard-demo.cmd` from the repository, or:

```powershell
node node_modules/vite/bin/vite.js apps/web --host 127.0.0.1 --port 5177 --strictPort --open /keyboard.html
```

The user-started launcher keeps its server in the visible terminal; Ctrl+C ends it. Dependencies already present in this checkout are reused. No install, cloud API, video, EEG, sample download or backend is required. This development demo is not a Windows production deployment.

## Controls

- Space: start a new take / stop. Stop preserves the elapsed event track for export; restart replaces it.
- 1–4: plain melody, chromatic grace note, turn, trill. Ornaments replace each occupied melody slot, preserving deliberate rests and accompaniment.
- A/S/D: detached, staccato, legato melody envelopes.
- Up/down: queue ±2 semitones for all pitched parts at the next unscheduled bar, within ±12. Repeated requests replace the pending destination. Gain, articulation and brushes remain unchanged. This explicit manual keyboard direction does not alter the scene-dependent double-blink policy.
- Buttons provide equivalent pointer/touch controls. Focused input widgets retain their native keys; focused buttons retain native Space activation.
- Master level is set before starting. The exported take retains its recorded gain even if the next take's level is edited.

Original four-bar sketch `Little Signals`, 96 BPM, swing, local felt-piano/bass/brush synthesis using the existing `voice` function. Object-free manual score, with explicit manual planning and keyboard/mouse input provenance. New score definition: `packages/audio/keyboard-score.ts`. Notes are materialized seconds; no subsequent swing pass. Configuration hash binds the sketch, initial settings and gain. Exports preserve events, request/effective times, initial settings and `approval:null`; no approval is synthesized. Browser playback is capped at 120 seconds. A scheduling stall over 200 ms ends the take instead of replaying missed notes in a burst. Stop clears queued controls and native sources; suspended audio ends the take.

The 90 ms scheduling horizon precedes controls; ornaments/touch affect the next unscheduled melody slot. Repeated input keys are ignored. The green strip is a phrase/activity indicator, not a waveform. WAV export re-synthesizes the trimmed symbolic track with the existing OfflineAudioContext renderer, not a recording of physical output. Human audition is pending.

## Verification on 2026-09-13

- `npm run typecheck`: passed.
- `node --import tsx --test packages/audio/tests/keyboard-score.test.ts apps/web/src/keyboard/player.test.ts`: 7 passed. Covers bar scheduling, pending key replacement, stop cleanup/trim, stalled clock, pitched-only transposition, preserved accompaniment/rests and ornament slot bounds.
- The above includes actual procedural PCM array synthesis at 8 kHz across 12 ornament/touch combinations, 10 seconds each, at the maximum UI gain of −6 dB. Maximum sample peak 0.3245576620; minimum RMS 0.05623404; no clipped/nonfinite samples. This uses a buffer-allocation test adapter and the real synthesis function, not browser output or listening evidence.
- `node node_modules/vite/bin/vite.js build --config apps/web/keyboard.vite.config.ts`: passed; standalone build at `artifacts/keyboard-web/keyboard.html`. Public media are excluded from this build.
- `npm run test:contracts`: 70 passed. Existing frozen shared TypeScript contract checks; full Python/root make suite not run for this isolated TypeScript addition.
- HTTP GET `/keyboard.html` and `/src/keyboard/main.tsx`: both 200 from the actual Vite development server.
- Browser UI/audio, download interaction and physical timing: NOT_RUN. Connected CUA browser reported `No browser is available`. Human listening: AUDITION_PENDING.
- Configured immutable host profile was attempted at `C:/Users/Yaw Tia/.config/agent-context/host-capabilities.json`; it was absent. Host inventory was not rediscovered.

Task-owned validation server: exec session 74040, Node PID 12472, command `node node_modules/vite/bin/vite.js apps/web --host 127.0.0.1 --port 5177 --strictPort`, loopback port 5177. Child esbuild PID 19244. Exact teardown verification follows below.

Teardown: stopped exact Node PID 12472 and ensured its recorded esbuild child 19244 exited. Follow-up process and TCP queries confirmed zero remaining task PIDs and zero listeners on port 5177. No task server/container/capture job remains running.
