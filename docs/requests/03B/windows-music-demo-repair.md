# Windows prepared music demo repair — 2026-09-13

Authorized scope: review the failed local launch and make the existing music and
bounce/collision demo work. Integrator owns this scoped web/root launch repair.

## Cause and changes

Windows Git checkout converted LF to CRLF in 22 prepared JSON bundles. Replacing
CRLF with LF reproduced each existing catalog SHA-256 exactly before any write.
The same verified restoration was applied to the frozen key-transition table
(`abc0f83a5cadfbc7919d8c6e75731e52f8fe6d8af70f30078ebb3f5e932a00ba`).
No catalog digest, music, media, policy, approval, or reviewed sample was changed.
Root `.gitattributes` pins these files to LF for subsequent checkouts.

`apps/web/src/main.tsx` now mounts the existing Library at `/`, retaining direct
`?review=1` and `?music=1` players. The missing `choose` handler now selects an
existing entry matching scene, arrangement and groove, rejecting unavailable
combinations. Existing load behavior clears approval on selection changes.

`start-music-demo.cmd` builds the browse index and starts the existing Vite
dependency directly on loopback port 5176 with the bouncing staircase review URL.
It avoids the unavailable Python/uvicorn environment and missing source-render
artifacts. This serves preserved public assets; it does not regenerate media.
The user keeps its console open while listening and stops it with Ctrl+C.

## Commands and evidence

- `node apps/web/tools/catalog.mjs`: PASSED, three animations and 22 soundtracks,
  zero unavailable entries (previously zero animations / 22 failed checks).
- `npm run typecheck`: initially FAILED with two missing `choose` references;
  PASSED after the UI fix.
- `npm run build`: PASSED after the UI fix. Existing large-chunk advisory remains.
- Inline Node/tsx audit used `sha` and `verifyBundle` from the actual audio runtime
  on all 22 prepared bundles and matched videos: PASSED, including all three
  staircase grooves and contact/near-miss music.
- `node --import tsx --test packages/audio/tests/*.test.ts`: 74 passed, one failed,
  three optional artifact-dependent tests skipped. The sole failure was the
  transition-table raw-byte hash changed by CRLF.
- Focused reproduction: `node --import tsx --test
  packages/audio/tests/transport.test.ts
  packages/audio/tests/vertical-transitions.test.ts
  packages/audio/tests/vertical-preview.test.ts
  packages/audio/tests/vertical-engine.test.ts
  packages/audio/tests/window.test.ts`: 29 passed / same one failure, recorded in
  `output/music-demo-regression.log`.
- After restoring the table, `node --import tsx --test
  packages/audio/tests/vertical-transitions.test.ts`: all ten passed, recorded in
  `output/music-demo-transition-recheck.log`. Full suite was not repeated.
- Direct Vite launch with `--host 127.0.0.1 --port 5176 --strictPort`: PASSED.
  HTTP checks returned 200 for `/`, `/?review=1`, `/src/main.tsx`, and the library
  catalog. All three staircase bundles and video fetched over HTTP passed the
  actual runtime validator, including exact byte hashes.
- `git diff --check`: PASSED.

Desktop browser observation and actual acoustic playback: NOT RUN. Browser CUA
had no connected browser, and Windows computer-use initialization and retry both
returned native-pipe-unavailable. No automated human approval was created.
The user launcher itself was not double-clicked through Windows automation.
Prior failed shell browser launch is not claimed as a successful open.

## Resource identities

Validation/build/test sessions: 44100, 15393, 31429, 32241 completed. Temporary
Vite session 49525 owned listener PID 30240 on loopback 5176; Ctrl+C stopped it.
Final process and listener absence is checked before handoff. No render, capture,
container, provider job, or new dependency installation occurred.

Contract migration: none. Original exact persisted bytes and frozen 0.1 remain
authoritative. No Phase 4 or product-readiness claim is made.
