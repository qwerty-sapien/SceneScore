# Manual key-change integration — 2026-09-13

Implemented the user-authorized manual button and the library piano progression
fix under [decision 0017](../../docs/decisions/0017-manual-key-change.md).
Use **Watch & listen**, then **Change key** below the transport. Randomness is
limited to feasible prepared ±2 edges and its seed is recorded. No advanced
conducting setup or detector arming is needed for this manual draft audition.

Owned changes: `apps/web/src/main.tsx`, `style.css`, Muse presence helper/callback
in `headset.ts`, `types.ts`, `MusePanel.tsx`; `packages/audio/manual-control.ts`,
standard `model.ts` transition lane support, `transport.ts` chord display;
manual-control/duet tests; `apps/web/tools/check-key-change.mjs`; decision/VISION
clarification and this report/evidence. Pre-existing user/task edits, media,
catalogue inputs, training work and frozen schema were preserved. No commit or
deployment was requested or performed.

## Actual validation

- **PASSED:** `make test-contracts` — Python fixture validator and 70 TypeScript
  contract tests; [log](contracts.log).
- **PASSED:** `node --import tsx --test packages/audio/tests/*.test.ts
  apps/web/src/muse/tests/*.test.ts` — 105 passed, zero failed, two optional exact
  prepared-artifact tests skipped; [log](tests.log). The skips are the optional
  Blender review candidate and exact music candidate cache tests. The frozen
  compiler golden remains passing.
- **PASSED:** `npm run typecheck`; [log](typecheck.log).
- **PASSED:** `npm run build`; [log](build.log). Vite retains its >500 kB chunk
  size advisory; no build errors.
- **PASSED:** scoped `git diff --check`.
- **PASSED:** `SCENESCORE_PLAYWRIGHT_MODULE=/Users/agent/.npm/_npx/9833c18b2d85bc59/node_modules/playwright-core/index.mjs
  node apps/web/tools/check-key-change.mjs` against loopback preview port 8797.
  [Browser evidence](../../output/playwright/manual-key-change/checks.json)
  records both actual browser score changes, tonic/chord arrival, queued button
  disabling, unchanged gain/unpitched events and approval:null. Both players
  work through normal Watch & listen with draft conducting still false.
- **PASSED, MOCKED HEADSET:** source selection alone leaves the button visible;
  scan discovery hides it; connected/disarmed/bad-quality Muse stays hidden;
  disconnect and companion loss restore it. No actual Bluetooth scan occurred.
- **PASSED:** desktop/mobile screenshots inspected; no horizontal overflow at
  390 px. See [library](../../output/playwright/manual-key-change/library.png),
  [music demo](../../output/playwright/manual-key-change/vertical.png) and
  [mobile](../../output/playwright/manual-key-change/mobile.png).

Both actual offline Web Audio renders were 30-second stereo at 48 kHz with no
clipped samples. Library peak/RMS: 0.349481 / 0.042909. Music demo peak/RMS:
0.012643 / 0.001946. These are rendered PCM checks, not speaker measurements or
human audition. Unit tests cover both random directions; the browser choices
and seeds are retained in the evidence.

Initial browser validation failed because the library's `piano-comp` lanes were
not reharmonized by the older compiler, and the chord display reverted during
rests. Both were fixed and regression-tested. One subsequent harness run timed
out because it expected “Rescan” after disconnect; the actual UI correctly resets
to “Scan for Muse”, and the locator was corrected. The duet test's former pure
transposition expectation was updated to require the requested V → I piano
reharmonization inside the transition bar, while retaining timing/duration and
ordinary transposition checks outside it. Final runs above passed.

## Limits and teardown

NOT RUN: real Muse classification/clock integration, human audition, acoustic or
physical display timing, full Python repository suite and public deployment.
This proves the exercised software music path independently of the classifier;
it does not establish that only classifier quality remains for a reliable live
brain-controlled system. Existing live clock/quality/arming gates still apply.

The initial sandboxed preview launch was denied local binding and exited. The
authorized retry used Vite PID 66892/session 29735 on 8797. TERM produced exit
143; process checks found no remaining preview/browser-test PIDs and `lsof`
found no listener on 8797. All three bounded Chrome checks closed their browsers
in `finally` and exited (first two failed, final passed). No capture, training,
container or other persistent task job was started. See [teardown](teardown.json).
