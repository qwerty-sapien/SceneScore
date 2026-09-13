# 05 — the deployed training and feedback surface

**Owns:** `apps/web/src/muse/`, `apps/web/public/muse/`, `services/bridge/`. **Budget:** 60
minutes. Depends on the frozen seam from 01, not on a working detector.

Extend the existing Vite app under its own subtree. The shared shell
(`apps/web/src/main.tsx`, `style.css`) belongs to the music pack; changes there go through
`docs/requests/`. Follow `apps/web/DESIGN.md`: a warm editing desk, not a dashboard, no
game indicators and no model theatre.

## Non-negotiable: mode honesty

Three states, always visible, never inferred: `live`, `replay`, `simulated`. The repo's
`Mode` type already enumerates `KEYBOARD`, `SYNTHETIC_TEST`, `REAL_REPLAY`, `LIVE_MUSE`.
A replayed or simulated event rendered as live is a truthfulness defect and fails this
node. `live` requires an armed, connected, quality-passing stream — not merely a selected
dropdown value.

## Provide

Connection and runtime status with the explicit mode. The guided collection protocol from
node 02 with session progress. A frontal-signal plot when locally available. **Cue state
and prediction state as separate displays** — never one widget that implies the cue caused
the prediction. Candidate, accepted-double and rejection markers with reasons. Delayed
feedback controls: performed, missed, uncertain, false positive, correct detection.
Training and evaluation summary with the active model version. A direct music demo where an
accepted event audibly invokes the deterministic transition. The keyboard fallback,
permanently.

## The bridge, if node 00 chose one

Loopback binding only. Bounded authenticated session handshake. Narrowly scoped streaming
and command surface — the browser asks for a stream and an arm state, not for arbitrary
local execution. Never exposed to the public internet. The deployed production build must
not require the bridge to load, render or run its replay and simulated paths.

If browser BLE was chosen instead, the proof is a working connection on the actual target
browser and headset recorded in node 00, not a support matrix. Keep the replay fallback
either way.

## Data

Raw EEG stays local. The deployed app holds non-sensitive configuration and model metadata
only. Prefer local storage for session UI state where server persistence adds nothing.
Uploading a recording requires a separate explicit opt-in and its own justification.

## Tests

Playwright coverage for: mode labelling in all four states, including that `live` cannot be
displayed without a live stream; the delayed feedback workflow; reconnect and error states;
a simulated blink producing an acknowledgement and then a key change; the bridge being
unavailable degrading to replay rather than to a blank page; a production build succeeding.

## Forbidden

Making the deployment responsible for Bluetooth or LSL acquisition. Implying a replay is
live. Exposing the bridge publicly. Uploading raw EEG. Showing an EEG feature as a mental
state, mood, focus or stress readout — this is an ocular-gesture control and the UI must
say nothing more.

## Done when

The production build deploys, the surface is fully usable with no hardware attached, every
mode is labelled honestly under test, and a simulated accepted event drives real audio.
