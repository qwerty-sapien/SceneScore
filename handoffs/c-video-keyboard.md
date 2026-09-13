# Handover — C video → keyboard music demo

## What happened

The user explored detecting seven scene events with OpenAI vision: approach,
near miss, separation, contact, sustained contact, release and rebound. We created
a Git-ignored root `.env.local` template; the user supplied the API key. Live
GPT-4.1-mini image and video-frame calls succeeded. The claimed $100 credit balance
was **not verified**. Never print or bundle the key.

We analyzed `C:/Users/Yaw Tia/Desktop/Astra Hackathon/C.mp4` (6.37 seconds, 30 fps)
using 64 frames at 10 fps. The call took 18.976 seconds and cost approximately
$0.0161. It proposed six event types; near miss was not observed. Visual review
flagged conflated ball identities and questionable sustained-contact/rebound
claims. These are proposals, not validated physical events.

The user requested a visual report, then explicitly chose to use these proposals
and integrate music into the keyboard demo. The report embeds the video, all
frames, clickable timestamps, exact API output and clearly labelled review notes.

## Delivered

- Launch `start-keyboard-demo.cmd`; C video is now the default keyboard scene.
  Click **Play video + music**. Original sketch mode remains selectable.
- Six editable musical markers: approach arrival 1.0 s, contact 1.05 s,
  sustained contact 1.1 s, separation 2.3 s, release 2.35 s, rebound 2.4 s.
- Original Little Signals piano/guitar phrase fits one video loop: four bars,
  191/30 seconds, approximately 150.8 BPM. Audio clock drives video sync.
- Existing ornament, touch, next-bar key controls and WAV/editable-score exports
  remain. Restore API markers while stopped; delete/add markers to revise them.
- Audio was synthesized locally with existing editable voices; **no further API
  calls** were used. Draft approval remains null; user selection is recorded
  separately from formal performance approval.

## Key files

- `reports/c-video-analysis/C-video-report.html` — portable visual review.
- `reports/c-video-analysis/20260913T063904367636Z/` — raw response, frames, hashes.
- `apps/web/src/keyboard/assets/` — copied C.mp4 and source proposal preset.
- `apps/web/src/keyboard/{main.tsx,player.ts,video.tsx,video-sync.ts,video.test.ts}`
  and `packages/audio/keyboard-scenes.ts` — integration and timing wrapper.
- `reports/c-video-score/preview.html` / `C-scored-DRAFT.mp4` — scored preview.
  Same folder contains mix/stem WAVs, editable JSON, render script and validation.
- `docs/requests/03B/keyboard-c-video.md` — detailed changes, commands and cleanup.

## Verification / continuation

Passed: TypeScript typecheck; 21 audio/player/video tests; 70 contract tests;
production keyboard build; local HTTP asset checks; source/mux video hash match.
Rendered 70 events at 48 kHz; mix peak 0.2174, RMS 0.0392, no clipping. Video
frames are unchanged; stems sum to the mix within 1 LSB.

Not run: actual browser interaction, speaker audition, physical A/V timing, full
Python suite. No connected browser was available. All task jobs exited; no server
or container remains running. Unrelated working-tree changes were preserved.

Next useful step: user audition of the keyboard demo and adjustment of crowded
markers. Existing newest-marker precedence can shorten contact/release effects;
musical effects generally last two beats, independently of model interval length.
Do not treat the visual model output or automated checks as human approval,
certified detection accuracy, or authorization to begin Phase 4.
