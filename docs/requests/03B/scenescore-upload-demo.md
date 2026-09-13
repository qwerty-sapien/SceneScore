# SceneScore upload demo — integration decision

Authority: the user's September 13 request for `scenescore.html`, uploading videos shorter than 30 seconds, analyzing frames at 5 fps, generating music, applying effects, and delivering a playable video with an event editor. The user subsequently selected the first 29 seconds of B. This authorizes this additional demo, not Phase 4 or a release claim.

The integrator owns the new web entrypoint, local Node service, renderer and integration checks. No workers, application-stack installation, frozen-schema edits, dependency-lock edits, global settings changes or changes to `.brief/` are part of this work. Existing keyboard changes and unrelated working-tree edits are preserved.

## Behavior and contracts

- `start-scenescore.cmd` starts the local service; open `http://127.0.0.1:5188/scenescore.html`. The HTML requires this service. A static build alone cannot run video processing or call the API.
- Uploads are capped at 128 MiB and decoded duration must be below 30 seconds. The A shortcut reads the supplied A.mov. The explicitly labelled B shortcut prepares its first 29 seconds; uploading the full B file is rejected. Originals remain unchanged.
- A bounded FFmpeg conversion prepares an H.264 preview, up to 1280×720 while preserving aspect ratio. Five JPEG samples per second are taken from that preview at 0.2-second intervals, using FFmpeg's regular sampling grid. Sampling is not a guarantee of event accuracy or subframe timing. Source audio is neither analyzed nor mixed into the result.
- One GPT-4.1-mini Responses call proposes objects and events. The server reads `.env.local`; keys are not sent to the frontend. The request sets `store:false`, timeout 120 seconds, 7,000 output tokens, and no automatic paid retry. The raw response is retained separately from validated/editable proposals. Implementation follows the [official vision input documentation](https://developers.openai.com/api/docs/guides/images-vision).
- Integer model object IDs are converted consistently to `object-N`, with collision and reference checks. Unsupported types, invalid times and unknown references fail. Uncertain proposals and proposals without two distinct object IDs start disabled. The original response remains available for provenance. Model-observed events are still proposals, not ground truth.
- Music is a local deterministic arrangement of the existing original Little Signals piano/guitar phrase, fitted to the clip. It is not a new opaque API-generated audio recording. Piano/guitar identities remain stable. This prototype maps event types to passages; it does not claim inferred object-specific instruments or reconstructed 3D geometry.
- `compileDuet` gained an optional `repeatMarkers=false` mode. Its default remains unchanged for keyboard playback. Uploaded-video events occur once and can span musical phrase boundaries; end-of-clip anticipation does not wrap into the start.
- Effects retain the existing semantics: approach anticipation, near-miss silence, separation descent, contact chord, sustained duet, release motif and rebound ornament. Near-miss silence wins overlapping windows, then the higher marker ID wins. Effects have musical beat windows, distinct from model interval length. This can shorten crowded effects and remains inspectable in the editor.
- Exports provide frozen-0.1-valid ScoreEvents, unswung PPQ=960 ticks, resolved seconds, settings, editable markers, source/frame/code hashes, model provenance, stereo WAV, piano/guitar stems, and muxed MP4. Tick recovery is rounded to PPQ; resolved seconds govern rendering. Swing is marked already applied once. All exports have `approval:null` and `AUDITION_PENDING`.
- Native playback uses the muxed video and its audio in one media element. The silent-source comparison is explicitly labelled. Changing an event or music setting pauses playback and marks the rendered version stale; rebuilding creates a new revision without another API call. Downloads continue to identify the last rendered version until rebuild completes.
- The page can reopen saved drafts. Failed parsing can recover an existing response as `cached_gpt`; a failed API prerequisite can continue as `manual_plan`. No successful inference is claimed in manual mode.

## Resources and local boundary

HTTP binds to loopback on 5188; development hot reload uses loopback on 5288. Requests verify Host and Origin; mutations also require a custom header. Asset paths are allowlisted, private source uploads are not directly served, and Vite denies environment files and raw session storage. Browser-facing health reports only whether a key is configured.

One processing job is allowed at a time, with a 120-second child-process limit, two FFmpeg threads, at most 150 samples, 64 editable events, 20 sessions and 20 render revisions per session. Session storage is under ignored `artifacts/scenescore/`. Archive completed sessions manually when the limit is reached. Cancellation terminates/reaps the owned worker before releasing its slot. `commands.jsonl` records child PIDs, arguments, exit codes and cancellation; per-child logs accompany it.

The required host-capabilities file was absent at the specified location. Captured host facts were not recreated. The existing Node/FFmpeg installation was used for this local demo; no Windows production environment was substituted. Existing FFmpeg lacked `force_divisible_by`; the preparation filter uses a compatible even-dimension scale instead.

## Verification

See `reports/scenescore-demo/` and `handoffs/scenescore-demo.md`. Checks distinguish software/media validity from browser operation, human listening and physical timing. No formal approval or Phase 3B/4 gate is advanced.
