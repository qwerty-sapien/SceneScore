# C.mp4 exploratory visual review

Open `C-video-report.html` in a browser. It embeds the unchanged source video and
all 64 JPEG input frames, with event proposals, cited timestamps, slow interval
playback, a frame browser, visual review notes and the exact API response.
It requires no server, account, network access or additional API call.

Source: `C:/Users/Yaw Tia/Desktop/Astra Hackathon/C.mp4`; SHA-256
`d3a980678cb8488f8e20658c4e135f7a73171950556b505bebbc34d33911e617`.
Source probe: 6.37 seconds, 1920x1080, 30 fps, start time zero.
The initial FFmpeg metadata-only invocation exited 1 because no output file was
specified; metadata was read successfully. This was not a failed extraction.

Commands executed:
- `python reports/c-video-analysis/run.py`: PASS; 64 frames at 768x432,
  every third source frame. Actual timestamps 0.0–6.3 seconds come from showinfo.
- `python reports/c-video-analysis/run.py reports/c-video-analysis/20260913T063904367636Z`:
  PASS; one live Responses request, HTTP 200, completed JSON. GPT-4.1-mini-2025-04-14,
  high image detail, 18.976 seconds, 35825 input / 1132 output tokens. Estimated
  standard cost $0.0161412; no billing balance verification.
- `python reports/c-video-analysis/build_report.py`: PASS; portable HTML,
  3,730,774 bytes at initial generation.
- Inline Python HTMLParser/hash/timestamp verification plus `node --check` on the
  extracted JavaScript: PASS. Embedded video and all frame hashes match the run;
  all event evidence timestamps map to supplied frames; element IDs are unique.
- `git diff --check -- reports/c-video-analysis`: PASS.

Browser playback and rendered-layout automation: NOT_RUN; Playwright and
Puppeteer are unavailable in this project. Structural/script checks do not prove
browser behavior. The report exposes standard native video controls as well as
custom controls.

Review notes are the assistant's inspection of selected frames, not independent
human labels or ground truth. The model describes a single sphere, despite two
balls being visible simultaneously around 2.1 seconds. Its sustained-contact and
rebound intervals require review with identities tracked separately. The report
preserves the original response and explicitly labels both model proposals and
assistant observations. No accuracy score, app marker insertion, audio analysis,
music execution, human approval or general seven-event capability is established.

Original trial files are in `20260913T063904367636Z/`: result.json, manifest.json,
ffmpeg.log and the frames. FFmpeg child PID 15332 exited 0 and was reaped by the
extraction script. API exec session 74430 exited 0. Report generation and validation
also exited 0; no persistent jobs, servers or containers were started.
