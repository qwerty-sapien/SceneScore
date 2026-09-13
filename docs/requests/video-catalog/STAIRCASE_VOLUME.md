# Bouncing staircase playback level — 2026-09-13

The user reported that the staircase audio was too soft and requested “minimally 40db.” Decibels need a reference: no speaker/headphone calibration is available, so physical 40 dB SPL cannot be promised. The scoped implementation makes the existing three staircase mixes 12 dB louder by default, without changing source score/scene/video bytes, dynamics, timing, plan approval or other videos. Manual attenuation and mute remain available; this is not a forced loudness floor.

`apps/web/src/library/playback-gain.ts` selects -6 dB master gain instead of -18 dB for the exact measured scene/score hashes. Changed or unknown scores retain the original conservative default, and explicitly authored sound-design gain takes precedence. The player calls this after bundle verification and only when initializing a fresh player, preserving subsequent manual volume changes across soundtrack selection. The same gain state drives live audio and draft export. Existing frozen media, contracts and approval behavior are untouched.

The audiovisual-integration skill informed the actual PCM measurement and the separation of digital levels from physical output and human audition. The installed Playwright runtime was reused for a bounded isolated browser check; no dependency was installed. The existing CLI reconnect failure is documented in the catalog implementation report.

## Measured audio

Actual Chrome OfflineAudioContext output through the player, 48 kHz stereo, eight seconds. dBFS values are `20 * log10(amplitude)`; RMS is the full-clip average, not a continuous minimum or a LUFS/SPL measurement.

| Soundtrack | Before RMS dBFS | After RMS dBFS | After peak dBFS | Clipped samples |
| --- | ---: | ---: | ---: | ---: |
| Light swing | -49.084 | -37.084 | -22.688 | 0 |
| Sparse brush | -49.102 | -37.102 | -22.813 | 0 |
| Straight rag | -49.099 | -37.099 | -22.706 | 0 |

All three resulting average digital levels are above -40 dBFS. This must not be described as 40 dB SPL at the user's ears. Their device/output volume remains outside the website's measurement and control.

## Verification

- `node --import tsx --test packages/audio/tests/playback-gain.test.ts packages/audio/tests/mix.test.ts`: passed all eight tests. Coverage includes scoped default levels, unknown inputs, explicit authored levels, mute, independent lanes and manual attenuation.
- `npm run typecheck`: passed.
- `make test-contracts`: passed canonical Python cases and all 70 TypeScript tests.
- `npm run build`: passed; existing Vite large-chunk warning remains. This refreshed the static files used by the user's already-running server, without restarting it or rerunning soundtrack preparation.
- `git diff --check` on the affected source/tests: passed.
- Browser measurement command: `SCENESCORE_PLAYWRIGHT_MODULE=/Users/agent/.nvm/versions/node/v24.14.0/lib/node_modules/@playwright/cli/node_modules/playwright-core/index.mjs node apps/web/tools/check-staircase-volume.mjs`. Baseline comparison completed and closed the browser (PID 6017). Final post-build result and browser cleanup are in `output/playwright/staircase-volume/checks.json`; screenshot is `player.png` in the same directory.
- Human audition, calibrated speaker SPL and physical AV timing: not run. No automated listening approval was created.

One final-browser permission review timed out before launching. The explicitly permitted single retry was used; a timeout was not treated as evidence of unsafe application behavior. The user-owned `make demo` server is not task-owned and must remain untouched. No additional persistent server was started by this change.

Final browser verification passed for all three default levels, the 12 dB PCM increase, non-clipping output, manual-volume preservation across soundtrack changes and a fresh player's new default. There were no page errors. The browser closed successfully; the command exited zero. `ps -p 6017,62564 -o pid,ppid,command` confirmed both recorded browser-check processes absent. The user's server remains running and serves the updated build; refreshing the page loads it.
