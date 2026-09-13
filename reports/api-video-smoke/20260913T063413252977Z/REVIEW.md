# Exploratory video-frame API trial

User authorized one simple video analysis experiment. No application integration,
new phase, human approval or seven-event accuracy claim is implied.

Command: `python reports/api-video-smoke/run.py`.
PASSED: source SHA-256 matches supplied baseline; FFmpeg extracted 31 native-size
JPEG frames at 0 through 29 seconds and 29.875 seconds; one Responses API request
returned HTTP 200, completed JSON. Exact extraction command, PID 23368 and exit 0
are in extraction.json. Parent exec session 97343 exited 0. No persistent jobs.

Model: gpt-4.1-mini-2025-04-14. Live API, synthetic Blender video, no audio input.
API latency: 13.871 seconds. Usage: 3504 input + 871 output tokens.
Estimated standard cost: $0.0027952 using $0.40 / million input and $1.60 / million
output (https://developers.openai.com/api/docs/models/gpt-4.1-mini).
This is a rate-based estimate, not a billing balance verification.

The prompt and exact response are in result.json. The source baseline was not sent
to the model. Individual frame filenames, timestamps and hashes are also recorded.

| Event | Model status | Model-proposed interval (seconds) |
|---|---|---|
| Approach | observed | 0-12 |
| Near miss | not observed | none |
| Separation | observed | 21-29.875 |
| Contact | uncertain | 12-13 |
| Sustained contact | uncertain | 13-21 |
| Contact release | observed | 21-22 |
| Rebound | not observed | none |

These are model proposals, not accepted markers. Read-only comparison against
blender_revamp/BASELINE_AUDIT.md and evidence/baseline_metrics.json found:

- The source audit records projectile travel at 3.6-12.6 seconds, followed by a
  fixed position. The model's 0-second approach onset includes an initial hold.
- The model invents projectile movement to the left after contact. In the source,
  blocks translate away from the stationary projectile. Visual inspection of
  extracted frames at 17 and 21 seconds supports the need to distinguish the two.
- Visible clearance at 17 seconds undermines the proposed sustained contact
  through 21 seconds and release at 21-22. This visual check does not establish
  an exact physical release time.
- The model describes rotation/tilting; the supplied baseline records constant
  block quaternions. The changing stack arrangement is not individual rotation.
- Contact release is labelled observed despite contact being uncertain; the
  physical interpretation should retain that uncertainty.
- The model groups all blocks into a tower, losing per-object event ownership.

NOT_RUN: formal independent annotation, precision/recall, dense adaptive follow-up,
audio audition, app marker insertion and approval. This single flawed draft and
one-second sampling cannot establish general event detection performance.
Frozen source media and earlier review artifacts were preserved.
