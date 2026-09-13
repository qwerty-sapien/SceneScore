# Music node 03 handoff

Machine gate **GO**. Human A/B subgate **HUMAN-DECISION / AUDITION_PENDING**;
approval **null**. Node 04 may consume the software output. No person evaluated
mechanicalness, musical coherence or the full vocabulary's sound.

Worktree `/private/tmp/scenescore-music-source`, baseline
`527f949fbf10319b84428b1cf510c5d2c1c205d2`, continuing after node 02. Node-02 source
files and renders are frozen. No root write, merge, commit, browser, dependency,
canonical schema or renderer change was made. Existing `modules/music/events.py`
remains unchanged, SHA `1805f4cd62c22c75491da4c2e4f38b3e1163f5b412508df3ed15efbae738f2f8`.

Owned additions:

- `modules/music/ornament.py`, SHA
  `feed170dcb0e584d99088222757529ebdc18b669b740e05b1920b89c86cfdc67`.
- `modules/music/tests/test_ornament.py`, SHA
  `68aacb23364a58e84e48ec0aaf77d4fc41cb94e31ab2b510c4abb4519e54c991`.
- `modules/music/fixtures/music-ornament-v1.json`, SHA
  `8bec9fcfe4f202af48d94318b9a5179e1354223f6699b2e4b6a396e2bfcb98bc`.
- `modules/music/fixtures/render_ornament_v1.py`, SHA
  `5d49a18061ac9056a8ed4108c404f8c72a1a11dbafee9cfa0ed826034e18b892`.
- This handoff and `docs/requests/03/integration.md`.

## API and semantics

```python
from modules.music.ornament import TransformRequest, TransformBudgets, apply_transforms

request = TransformRequest(event_id, 'grace', preserves_duration=True)
result = apply_transforms(events, [request], composition, seed=42,
                          budgets=TransformBudgets())
candidate_events, audit = result.events, result.audit
```

Requests may also be equivalent JSON dictionaries. Parameters: `event_id`, `kind`,
`preserves_duration=True`, `articulation=None`, `velocity_delta=0`, `direction=1`,
`subdivisions=4`, `probability=1.0`, `related_event_ids=()`. Kinds: `articulation`,
`velocity`, `grace`, `mordent`, `turn`, `trill`, `tremolo`, `octave_doubling`,
`chord_redistribution`, `arpeggio`. Unsupported, malformed and duration-extending
requests fail explicitly. A valid request that is unsafe or exceeds a budget is
suppressed atomically; audit rows retain the reason and source remains intact.

Articulation accepts detached/staccato/tenuto/legato and changes only that control
plus provenance. Velocity accepts a delta in [-32, 32], rejects overflow rather than
clamping, and preserves all other musical controls. The two style controls do not
count as note decorations because they neither add notes nor change occupied slots.

Grace steals at most 120 ticks and one quarter of the parent slot, then returns to
the original main pitch. The parent ID denotes the shortened main body; new prefix
notes carry derived IDs. Mordent/turn/trill neighbors derive from current key and
chord, while grace explicitly declares its chromatic-approach rule. Tremolo repeats
the original pitch. Octave doubling keeps the source and adds only its octave.
All preserve object/plan/lane identity. Arpeggio and chord redistribution accept
two-to-four same-slot accompaniment voices, including separate harmony lanes;
source pitches must belong to current harmony. Melody groups are rejected.

Subdivision uses the parent's already-resolved interval, so it cannot swing that
interval twice. Source and group occupied start/end, positive raw tick durations,
total score duration, MIDI bounds and pitch register are validated. No helper
silently places a grace at a scene contact inside a different note; node 04 must
select its eligible source event and disclose any quantization. Withholding the
third or sustaining a harmony after a near-miss minimum remains node-04 mapping
ownership, not an implicit ornament here.

## Enforced bounds

Default budgets: at most 12 added events in a rolling second, two overlapping
ornament groups, 96 non-Foley events per bar, register 28–96, minimum generated-note
duration 25 ms, and 256 requests. No repeated kind on a lane within one bar, no
ornament on an existing ornament, no bar with every eligible source note decorated,
no duplicate request execution, and no new low-register cluster: simultaneous distinct
pitches **both below MIDI 48** must be at least five semitones apart. The existing
45/49 cross-floor dyad is preserved and not reclassified as a below-floor cluster.
These are declared software rules, not perceptual judgments.

Repeated calls retain prior ornament groups and their added-event counts, so they
cannot reset budgets. Density decisions and arbitration are deterministic under
input/request ordering and a fixed seed/version. Brush and Foley records are
compared byte-for-byte and never transformed; Foley is excluded from the music
event budget. Invalid base sources fail before an edit is attempted.

Optional runs, free flourishes and duration-extending transforms are **not enabled**.
The required duration-preserving vocabulary is implemented; no free pitch generator
or renderer-specific style branch was introduced.

## Actual validation and media

- `PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest -q modules/music/tests`:
  **83 passed**, 46.01 s, two existing dependency deprecation warnings. This includes
  all 31 node-03 tests, the frozen variation fixture and unchanged catalogue tests.
- `/Users/agent/Desktop/SceneScore/.venv/bin/ruff check modules/music/ornament.py modules/music/tests/test_ornament.py modules/music/fixtures/render_ornament_v1.py`:
  **passed**.
- `PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python modules/music/fixtures/render_ornament_v1.py`:
  two actual 10-second/48-kHz mono PCM16 excerpts **passed**, 2.06 and 2.11 seconds.
- Independent PCM16 comparison: 69,545 changed samples, **zero outside the three
  requested source intervals**; evidence `independent-ab-check.json`.

The initial smoke test exposed a below-floor comparison that also caught the
cross-floor 45/49 dyad; the comparison was corrected to require both pitches below
the unchanged MIDI-48 floor. One negative-control test initially expected the
slot-mismatch reason before its invalid melody-voice precondition; the fixture was
corrected. An unused test import was removed after Ruff flagged it. Final tests and
lint above pass, with no skipped frozen-fixture test.

Output root: `/private/tmp/scenescore-music-source/artifacts/music/music-vertical-ornaments/`.
Both excerpts cover scene time [0, 10] from the same 30-second ending edition; neither
is a claim about a complete cadence. `A-source.wav` SHA
`5200e4a4895e13a3875346a48ddf4de547e600b5e34574a2cb2932c93de1de61`, RMS
0.01889580726627145. `B-variation.wav` SHA
`eec5fc17db08fa85ba3487a38abb810344faa15b9789640b37e17e96c795e9c2`, RMS
0.019078144935991977. Both are exactly 480,000 frames, peak 0.10736083984375,
zero clipped samples and zero endpoint samples. Float difference RMS is
0.005628012363386814; that metric establishes distinct PCM only.

The frozen variation applies one grace at 5–5.625 s, velocity +12 at
6.0416667–6.25 s, and legato at 7.5–8.125 s. It adds one event, with maximum one
new event/second, one overlapping ornament and 24 music events/bar. Full-score
source-event SHA `81017381a1d2ee1c1d0feb33df67cde7ff642d80715c044d19c7238178357114`;
variation-event SHA `6a235a3680bf44067e45cd9e2f00773f6b901807bd88a3626d5f2b381711c7c9`.

Renderer `stdlib-procedural-1-event-ends-1` keeps pitched fades inside occupied
intervals; its existing 15-ms outer brush fade is recorded. No extra mix fade was
introduced, no note straddles the excerpt end, and the omitted allocated 350-ms
buffer was verified zero for every stem. The manifest binds code/input/event/file
hashes, budget, exact command and process ID. Source media remains unchanged.

## Limits and resource teardown

Python's candidate renderer distinguishes legato; staccato and tenuto tokens alone
do not change its envelope. The coordinator's browser engine handles those envelopes
under separate tests. This A/B therefore covers grace, velocity and legato, and
does not establish the full vocabulary's perceived quality, lack of mechanicalness,
physical timing or human approval. Reviewer/date remain null.

Render PID 42422/session 71734 exited **0**. Full test session 21273 exited **0**.
Earlier smoke/test sessions 95508, 4050, 45006 and 82873 all returned final exit
codes; none is live. All direct analysis and Ruff commands completed. No server,
browser, container, subprocess worker or persistent job was started by node 03.
No node-02 or node-03 job remains live.
