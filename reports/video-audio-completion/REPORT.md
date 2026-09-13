# Video audio completion — 2026-09-13

Implemented locally. Final built catalog: **60 unique videos**, accounting for
**78/78 requested paths**; **48 live music players** (3 prepared scene-score
videos and 45 video-only piano accompaniments), **12 embedded soundtracks**,
**0 silent players**, **0 catalog issues**. Counts reflect the final build;
concurrent rendering expanded the original 47-video snapshot during this task.

Silent clips receive original seeded browser piano, fitted to their duration
with recurring swing phrases, an ending, new takes, pause/seek/volume and editable
score download. Version 2 supports 2–120 seconds without stretching a two-bar
phrase over a long clip. Source video hashes remain verified. These previews
use duration, not inferred collision timing; their UI clearly labels the scope.

Live scene scores and new exports use `effect-mix-1`: music is faded over 80 ms
to 0.8× normal amplitude before effects, held through their tails, and restored
over 250 ms. Combined overlapping effects target 1.2× the ducked music RMS;
nearby effects share a duck to avoid pumping. Full dry original score PCM is
the reference for both live playback and exported stems. Clip-edge effects,
resume/seek, disabled effects, lane/master controls and existing event envelopes
are preserved. Export reports carry the policy. No canonical score bytes or
approval records are rewritten.

Historical embedded MP4 soundtracks keep their saved mix. The new effect policy
applies to live scene scores and new exports. No frozen review sample was
re-rendered, no human approval was created, and no deployment was performed.

## Actual verification

- `node --import tsx --test packages/audio/tests/*.test.ts apps/web/tools/video-inventory.test.mjs`:
  **102 passed, 2 optional prepared-candidate tests skipped**. `audio-tests.log`.
- `make test-contracts`: Python canonical fixture validation and **70 TypeScript
  tests passed**. `contracts.log`.
- Final `node --import tsx --test packages/audio/tests/effect-mix.test.ts packages/audio/tests/mix.test.ts`:
  **10 passed**, including exact 80% gain, ramps, overlaps, seek origin, mute,
  RMS calibration, silent reference, full score duration and clip-edge events.
  `final-focused-tests.log`.
- `npm run typecheck`: **passed**. `typecheck.log`.
- `npm run build`: **passed**, including regenerated full-coverage catalog.
  `build-final.log`. Vite retains its >500 kB bundle-size advisory.
- `SCENESCORE_PLAYWRIGHT_MODULE=/Users/agent/.npm/_npx/9833c18b2d85bc59/node_modules/playwright-core/index.mjs node apps/web/tools/check-audio-completion.mjs`:
  **all 60 videos decoded and produced nonzero playback PCM in Chromium**;
  every audio context closed on navigation. New-take and seeking flows exercised.
  `output/playwright/audio-completion/checks.json` and screenshots.
- The same browser command with `SCENESCORE_PCM_ONLY=1`: **3 prepared players and
  5 representative final 48 kHz mixes passed**, after final clip-edge/automation
  fixes. Effect-to-ducked-music ratios were approximately **1.19990–1.20000**;
  **zero clipped samples**, maximum sampled mix peak **0.78072** at −6 dB;
  sum-of-stems error below **1e-6**. The near-miss has no Foley and no duck.
  `output/playwright/audio-completion-final-mix/checks.json`.
- `node --check` on updated browser check scripts and `git diff --check`: **passed**.
  The two older browser scripts were updated for dynamic live counts/accompaniment
  and syntax checked; the new completion script performed the browser validation.

Not run: human listening approval, physical speaker/display timing, full Python
application suite, external deployment. PCM measurements are signal-level
measurements, not perceived-loudness or human musical-quality judgments.

## Resource teardown

The initial sandboxed browser command could not bind localhost (EPERM); it closed
its Vite instance and exited 1. The authorized host-permission retry succeeded.
The full browser check owned Node/Vite PID **5462** and Chromium PID **5474**;
Chromium exited **0**, Vite closed, and tool session **11124** exited **0**.
The final mix check owned Node/Vite PID **7150** and Chromium PID **7161**;
Chromium exited **0**, Vite closed, and tool session **53685** exited **0**.
Browser reports record these identities and closure. All bounded test/build
sessions returned their exit codes. No task-owned server, browser, watcher,
container or other persistent job remains running.
