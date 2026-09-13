# Keyboard scene-event timeline — 2026-09-13

Authorized by the user's request to add live editable scene events to keyboard.html. This supersedes the ornament shortcuts and playback cap in keyboard-playground.md. This is an object-free manual audition demo; no detected geometry, approval, Muse input or Phase 4 release is claimed.

## Delivered behavior

The playback bar spans the original four-bar, ten-second phrase. Hover and press 1–7: approach, near miss, separation, contact, sustained contact, contact release, rebound. An edit immediately schedules an audible cue (nominal audio-clock offset 5 ms; physical latency unmeasured), then repeats at its marked scene time. Future queued audio is refreshed after edits; already sounding notes finish. Marker effects also alter upcoming melody touch/ornament, with separation fade/register, sustained-contact/release dynamics and near-miss suspended chord tones. Overlapping mapping windows use the most recent event, then newest ID to break ties. Cues remain separate voices; contact Foley is unpitched. Global key controls retain their existing bar boundary behavior.

Click a marker to remove it or use Clear events. Tab to the timeline and use left/right arrows for a keyboard-only insertion position. Buttons insert at the playhead. Q/W/E/R now select ornaments; A/S/D and up/down retain their existing functions. Timeline supports up to 64 markers; edits are manual scene cues, not physically certified interactions. Markers remain through Stop/Play within the page session. No reload persistence is implied.

Playback repeats until stopped, audio suspension, or the existing scheduling-stall guard. Export records the first 120 seconds to retain the existing bounded offline renderer. Editable export includes scene markers and the recorded resolved events; approval remains null. New files: packages/audio/keyboard-scenes.ts and this report. Updated existing task files: apps/web/src/keyboard/main.tsx, player.ts, player.test.ts and style.css. Frozen schemas, locks and media assets were not edited by this task.

## Commands and evidence

- `npm run typecheck`: PASSED on final code. Initial new cue concat inference error was corrected with explicit ScoreEvent typing.
- `node --import tsx --test packages/audio/tests/keyboard-score.test.ts apps/web/src/keyboard/player.test.ts`: PASSED, 12 tests. New coverage: immediate preview, recurring markers across a loop boundary, queued-cue deletion, continued playback beyond 120 seconds with bounded recording, seven distinct cues, wrapped effect window and real procedural PCM synthesis. Initial removal fixture incorrectly inserted a live preview at the playhead; corrected to prepare the future marker before playback.
- Seven cue PCM synthesis at 8 kHz, maximum demo gain −6 dB: maximum sample peak 0.1176198348, minimum RMS 0.0127295592, finite/non-silent/unclipped. This is isolated cue synthesis, not a worst-case overlapping timeline mix or physical listening result. Existing 12 ornament/touch synthesis variants also passed (maximum peak 0.3245576620).
- `node node_modules/vite/bin/vite.js build --config apps/web/keyboard.vite.config.ts`: PASSED; output artifacts/keyboard-web/keyboard.html.
- `npm run test:contracts`: PASSED, 70 tests. Full root Python/make suite NOT_RUN for these isolated TypeScript changes.
- `git diff --check`: PASSED; unrelated pre-existing working changes retained.
- Browser UI, actual playback/download interaction and physical timing: NOT_RUN. CUA inventory returned no connected apps or browsers. Human audition remains AUDITION_PENDING.

The configured immutable host profile was absent at C:/Users/Yaw Tia/.config/agent-context/host-capabilities.json; no host rediscovery performed. No persistent server, browser tab, capture, render service or container was started. All finite test/build exec sessions exited (31707, 3299, 93993).

Launch using the existing start-keyboard-demo.cmd and open /keyboard.html. No new dependency installation is required.
