# Human audition protocol — pending

## Music vertical source edition 1 — 2026-09-13

Software gate: **GO**. Human verdict: **AUDITION_PENDING**; reviewer and review date:
**none**. Approval: **null**. No person or model supplied a listening judgment for these
new files. The existing catalogue and all frozen review exports are preserved.

`build_vertical_score()` is an opt-in `music-vertical-source-1` score supplement for
`tilted_blue_v1` version 1 and exact `brush_swing_light_v1` version 1. Its canonical
composition and groove retain schema 0.1; source hashes, ending region and arrival
metadata are outside canonical records in `score['sidecar']`. Its changed composition
bytes require fresh exact human approval before performance activation.

The 12-bar form already equals the hero's 30 seconds at 96 BPM, so tempo is unchanged.
The ending covers ticks 42240–46080 / scene seconds 27.5–30. Its two existing half-bar
chord slots become C7 and C6/9. The last lead phrase changes F4–D4–B3 to E4–D4–C4;
46/48 notes (95.833%) remain byte-identical and all onset, duration, velocity,
articulation and swing flags are retained. Earlier harmony and bar topology are
unchanged. The intended tonic settlement is authored evidence, not a listening verdict.

Eligible arrivals are ticks 3840, 7680, …, 42240 / seconds 2.5, 5, …, 27.5. These
internal bar starts have no crossing pitched event in the source. Including origin
and end, maximum spacing is 2.5 seconds against the 4-second limit. Zero is the origin;
30 seconds is terminal and cannot establish a new audible key. Node 05 must consume
these eligibility points under its transition/expiry/approval checks.

Both new renders use the unchanged `stdlib-procedural-1` catalogue envelope at 48 kHz,
mono PCM16, no normalization, and aligned piano/lead, bass, brush and object-motif stems.
Every sample in the renderer's allocated 350-ms post-form buffer was verified zero in
every stem before omission. Both persisted mixes contain exactly 1,440,000 frames / 30
seconds and zero first/last samples. This preserves the actual musical intervals.

| New export | Sample peak | RMS | Clipped samples | Mix SHA-256 |
|---|---:|---:|---:|---|
| Unmodified source | 0.124176025390625 | 0.019274696298396794 | 0 | `9d3ccd60fad79f117b39d16275e30218309756809ee61ef90cd9d6b85c67af82` |
| Authored ending | 0.124176025390625 | 0.019272529787528907 | 0 | `ad365a0a4ad0732370551968c30782736500ccc36fa2f956270fd33e12cbe046` |

Outputs: `artifacts/music/music-vertical-source/unmodified/` and `authored-ending/`.
Each has score/composition/brush/events JSON, editable MIDI, mix and four stems,
measurements and a manifest binding source/render code and output hashes. The versioned
evidence fixture is `fixtures/music-vertical-source-v1.json`; reproduce in a clean
output location with `fixtures/render_vertical_source_v1.py`. Rendering seed context is
42 for this vertical edition; the preserved groove retains its independent 13007
humanization seed and the baseline composition provenance retains 104729.

Source hashes: original composition
`9a517e3ff24dc2d2855168a8233b8477b9fa3a993d1d16724989667d289c947d`;
exact groove `4d537af9f3f293efecda5e07ed41e78a9f75d7787c152fbdeb47edf8c46b495d`;
authored composition `76d75e3e98d31c48c7ea234c987efc03972b8f11e616c187d74f0a10fc6bc530`.

Passed: 52 music module tests, then four focused tests after adding the pitched-note
boundary-crossing check; Ruff. The first focused run failed the half-bar harmony
overlap check; preserving both half-bar slots repaired it without changing the form.
Not run: listening, physical audio output, synchronized animation audition, human
approval. Procedural timbre realism and perceived cadence quality remain unverified.

Velvet Orbit's frozen sparse lead-sheet sentence incorrectly calling it straight rag
remains a **deferred versioned correction**. Velvet Orbit is outside this demo path;
the original evidence and its recorded defect are not edited in place.

## Original Phase 2C review protocol

No person has listened to these exports as part of Phase 2C. All rows remain **AUDITION_PENDING**. File measurements establish technical output only. A language model's description of intended musical traits is not an audition result.

Use the exact mix hash in `fixtures/validation-48k.json` and the per-export manifest. A reviewer should use a comfortable independently chosen playback level, then compare base/sparse/animated versions of the same piece at unchanged system volume. Record reviewer name/date, playback setup and reviewed asset hashes before judging. A review can approve or request changes to a specific draft; it does not authorize a new live arrangement plan by itself.

| Piece | Base | Sparse/suspended | Animated/accented |
|---|---|---|---|
| Tilted Blue | AUDITION_PENDING | AUDITION_PENDING | AUDITION_PENDING |
| Almost, Then Away | AUDITION_PENDING | AUDITION_PENDING | AUDITION_PENDING |
| Corner Pocket Rag | AUDITION_PENDING | AUDITION_PENDING | AUDITION_PENDING |
| Velvet Orbit | AUDITION_PENDING | AUDITION_PENDING | AUDITION_PENDING |

For each piece, record concrete time locations and comments for:

1. Seed-call identity, contrasting answer and musical coherence across the complete form.
2. Blues/ragtime-derived identity, selective displaced accents, spacious voicings, lyrical arc and purposeful rests.
3. Straight-rag distinction and restrained accompaniment color; bossa should not replace the overall swing identity.
4. Cadence, turnaround and loop quality; distinguish the score loop boundary from the 350 ms tail.
5. Stable object marker identity and whether event space is sufficient. Actual scene alignment is not yet audited.
6. Brush sweep continuity, boundary fades, taps/swishes/chicks, timbral limitations and any clicks.
7. Melody/bass/brush/object balance, dynamics and articulation. Sparse/animated variants should differ intentionally without losing identity.
8. After arranger integration, exact prepared ±2 transitions, preserved expression and unpitched brush/Foley invariance.

Review record template:

```text
Reviewer/date:
Playback device/setup:
Composition/version/variation:
Exact mix SHA-256:
Decision: approved | changes_requested
Time-specific observations:
Required changes:
Known exclusions (e.g. no synchronized animation or live modulation reviewed):
```
