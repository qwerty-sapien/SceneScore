# C video and keyboard duet — 2026-09-13

User authorization: use the reviewed C.mp4 event proposals and integrate music into
the keyboard demo; audio generation was permitted. This is a scoped draft-audition
extension, not a Phase 4 release or formal approved performance.

## Delivered

`start-keyboard-demo.cmd` now opens keyboard.html with C video selected by default.
Play video + music starts the original Little Signals piano/guitar duet and the
video. Four bars fit 191/30 seconds (150.7853403 BPM); the original 96 BPM / ten-second
mode remains selectable. The video follows the AudioContext clock, including its
startup anchor and loop boundaries. Stop pauses both. Video load failures are
visible and the original sketch remains available. The UI reports a coarse video
element versus audio clock offset, not measured physical output synchronization.

Six markers from the existing GPT-4.1-mini response are preloaded:
approach arrival 1.0 s, contact 1.05 s, sustained contact 1.1 s,
separation 2.3 s, release 2.35 s, rebound 2.4 s. There is no near-miss proposal.
Approach uses the model interval end; contact/release use their onset-bracket
midpoints; other effects use interval onset. Midpoints are creative timing choices,
not claimed detection precision. API intervals/status/evidence, video hash and
response identity are retained in the source preset and editable exports.

The existing musical mapping and overlap precedence are preserved: approach
anticipates by two beats, near miss silences the previous half beat, and the other
effects last two beats. Model interval duration does not set musical duration.
Newest markers can truncate earlier responses on the same lane, notably the
contact/release cues in this dense sequence. Users can delete markers, add all
seven types at a cursor/playhead, restore the preset while stopped, change guitar
ornament/touch and queue key changes at the new video-length bar boundaries.

The original response is neither corrected nor promoted to certified physics.
User selection for audition is recorded separately from formal approval; exported
drafts retain approval:null and AUDITION_PENDING. Persistent musical lanes are
piano/guitar, not asserted per-ball identities. No geometry/EEG inference was added.

## Files and preparation

- `apps/web/src/keyboard/assets/C.mp4`: byte-identical copy of the supplied clip.
  SHA-256 d3a980678cb8488f8e20658c4e135f7a73171950556b505bebbc34d33911e617.
- `assets/c-video.json`: selected source proposals and explicit musical mapping.
- `packages/audio/keyboard-scenes.ts`: real-second wrapper around the existing
  four-bar compiler; pitches and existing effect rules are preserved.
- `apps/web/src/keyboard/player.ts`, `main.tsx`, `style.css`, `video.tsx`,
  `video-sync.ts`, `video.test.ts`: scene loading, dynamic tempo, video following
  the audio clock, UI and transport tests.
- `reports/c-video-score/render.ts`: bounded local procedural render using the
  same score compiler and keyboard voices. It emits a stereo mix, dual-mono
  piano/guitar stems and editable events. No API call or generated opaque track.
- `reports/c-video-score/C-scored-DRAFT.mp4`, `preview.html`, WAVs and JSON:
  ready-to-listen initial preset, with the original video stream copied.
- Production build: `artifacts/keyboard-web/keyboard.html` and bundled assets.

No extra API usage. Credentials stay outside browser assets. No dependencies,
shared frozen schema, root lockfiles or unrelated working changes were edited.

## Verification actually run

- `npm run typecheck`: PASSED.
- `node --import tsx --test packages/audio/tests/keyboard-score.test.ts apps/web/src/keyboard/player.test.ts apps/web/src/keyboard/video.test.ts`:
  PASSED, 21 tests. Covers existing musical mappings, live edits, video-length
  key boundaries, loop-time mapping, startup/stop, pending play race and errors.
- After the stopped-video reset fix, the five video tests were rerun: PASSED.
- `npm run test:contracts`: PASSED, 70 tests.
- `node node_modules/vite/bin/vite.js build --config apps/web/keyboard.vite.config.ts`:
  PASSED on final sources, bundled video included.
- Source FFmpeg decode: PASSED, 191 frames at 30 fps, time origin zero.
- `node --import tsx reports/c-video-score/render.ts`: PASSED, 70 events,
  305600 samples/channel at 48 kHz, 6.3666667 seconds. Mix peak 0.217414,
  RMS 0.0392242, zero clipped samples. Both stems finite/non-silent/unclipped.
- FFmpeg copy-video/AAC mux and independent decoded-video hash comparison:
  PASSED. Exact command/PID in `reports/c-video-score/mux-job.json`.
  Original and mux decoded video hashes match. WAV stems sum to mix within 1 LSB;
  see `validation.json`. Audio remains locally synthesized draft music.
- Bounded loopback HTTP smoke: PASSED for entry, JS, CSS and exact source video
  hash; API key absent from build. See `http-smoke.json`.
- `git diff --check` for owned source/report paths: PASSED (Git emitted line-ending
  normalization notices).

One initial Python edit attempt failed on the Windows default text encoding before
writing; it was rerun explicitly with UTF-8. No successful edit is inferred from
the failed attempt. CUA inventory again returned no apps/browsers. Browser UI
interaction, physical audio/display latency, speaker listening and the full Python
root suite are NOT_RUN. Fake media/clock tests and PCM measurements do not replace
human audition or establish physical A/V timing.

## Job cleanup

All finite exec sessions completed, including 18986, 3777, 97961, 6667 and mux
session 7948. Mux child PID 24296 exited 0 and was reaped. Local HTTP validation
PID 3504 used port 50066, shut down/closed its server and joined its thread before
exit 0. No persistent development server, browser, container or capture was left
running. The launch script starts a user-owned local server when the user opens it.
