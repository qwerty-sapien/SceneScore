# SceneScore upload demo handoff

Launch `start-scenescore.cmd`, then open **http://127.0.0.1:5188/scenescore.html**.

Upload a video below 30 seconds / 128 MiB and choose **Create soundtrack**. Frames are extracted at 5 fps, analyzed with the configured API key, and used to arrange the original piano/guitar score. The finished MP4 has native playback and an editable event timeline. Edit timestamps/types, enable/disable/delete/add events, change key/touch/ornament/gain, then choose **Rebuild soundtrack**. Rebuilding does not call the API.

Use **Reopen a saved draft** to test the completed A and B results without new API calls. **Video A** and **B · first 29s** start new analyses; B's crop was explicitly selected by the user. The original files remain unchanged. Download the MP4, WAV, stems and score JSON from the result page.

## Files

- `apps/web/scenescore.html`, `apps/web/scenescore.vite.config.ts`, `apps/web/src/scenescore/`: page, editor, analysis adapter and score compilation.
- `tools/scenescore-server.ts`: loopback upload/analysis/render service, persisted sessions, cancellation and saved-response/manual recovery.
- `tools/scenescore-render.ts`: bounded local audio render with canonical ScoreEvent validation, stems and measurements.
- `packages/audio/keyboard-scenes.ts`: optional nonrepeating markers; existing keyboard behavior remains the default.
- `tools/check-scenescore.ts`, `tools/test-scenescore-flow.ts`: read-only media checks and local mutation/fault checks that reuse analysis.
- `docs/requests/03B/scenescore-upload-demo.md`: scope, rationale, API reference, resource bounds and limitations.

## Test inputs and evidence

| Clip | Session | Frames | Proposals | Enabled by default |
|---|---|---:|---:|---:|
| A, 22.983333 s | `074e5ab4-4250-47cf-acea-c872219e55d0` | 115 | 12 | 12 |
| B, first 29 s (decoded output 28.966667 s) | `6320ca20-bb84-4ec6-99ac-b7e9b9682d95` | 145 | 16 | 12 |

Each session is in `artifacts/scenescore/<session>/`. `job.json` identifies the latest revision; that revision contains `final.mp4`, `mix.wav`, `piano.wav`, `guitar.wav`, `request.json` and `score.json`. Earlier renders are preserved. `api-response.json` is the unmodified response; `analysis.json` records the validated proposals and source mode. `commands.jsonl` and `process-<pid>.log` record subprocess evidence. No source media from the earlier frozen model evaluation was changed.

Exactly two live model requests were used for A/B, to `gpt-4.1-mini`, returning `gpt-4.1-mini-2025-04-14`. A used 126,424 input / 1,402 output tokens; B used 80,454 / 1,528. A's original parser rejected numeric IDs; the saved response was recovered after checked ID normalization. B's saved response was reparsed to disable four incomplete object-pair proposals. Final regenerated versions therefore disclose `cached_gpt`; no extra inference was purchased for fixes or editing tests. These are model proposals, not validated event-detection results.

## Commands actually run

- `node --import tsx --test apps/web/src/scenescore/model.test.ts packages/audio/tests/keyboard-score.test.ts apps/web/src/keyboard/player.test.ts apps/web/src/keyboard/video.test.ts tests/ts/*.test.ts`: **98 passed**; `reports/scenescore-demo/tests.log`.
- `npm run typecheck`: passed; `typecheck.log`.
- `node node_modules/typescript/bin/tsc --noEmit --module esnext --moduleResolution bundler --target es2022 --esModuleInterop --skipLibCheck --resolveJsonModule --types node,vite/client tools/scenescore-server.ts tools/scenescore-render.ts tools/check-scenescore.ts tools/test-scenescore-flow.ts`: passed; `server-typecheck.log`.
- `node node_modules/vite/bin/vite.js build --config apps/web/scenescore.vite.config.ts`: passed; `build.log`. Frontend build is in `artifacts/scenescore-web/`; a backend is still required.
- `node --import tsx tools/test-scenescore-flow.ts <A-session> <B-session>`: passed; `flow.log` / `flow-checks.json`. Edits changed audio, restoration reproduced byte-identical audio, API response identity was preserved, concurrent/invalid requests were rejected, malformed and overlength uploads stopped before API calls, cancellation released the job slot, and saved sessions were reopenable through HTTP.
- `node --import tsx tools/check-scenescore.ts <A-session> <B-session>`: passed; `media-checks.log` / `media-checks.json`. Actual score contracts, content hashes, WAV duration/levels, stem sums, muxed decode, matching preview/final video streams, byte ranges and origin/header/asset restrictions were checked.
- Missing-key test used an isolated process on 5190 with an empty key. An A preview upload reached an explicit missing-key failure, then the manual endpoint produced a valid draft with zero model calls, nonzero audio and zero clipping; `manual-check.json`. A development hot-reload port collision during the two-server test was corrected by assigning each server a separate loopback hot-reload port.

Initial failures were corrected: unsupported FFmpeg scale option, numeric model IDs, and inherited keyboard ScoreEvents lacking tick fields. Original failed session/output records remain preserved. `make install` and full Python suites were **not run**: no installation/Python changes were needed for this scoped demo. No dependency lock or frozen schema was changed.

## Remaining checks

Browser interaction/visual QA, speaker audition and physical A/V latency are **NOT_RUN**. CUA reported no browsers and opening the in-app browser failed as unavailable. Native muxed playback is implemented, but HTTP/media checks are not a browser listening test. No human approval is fabricated; all exports remain drafts. The first user test should audition A/B, inspect crowded markers, and enable/revise B's uncertain proposals only as desired. The original musical phrase is reused and arranged locally; the demo does not claim novel model-composed music or object-specific voice inference.

Task servers are stopped before delivery; exact teardown evidence is in `reports/scenescore-demo/teardown.json`. No Docker container, capture job or unrelated process was started or terminated. Start the launcher again to use the demo.
