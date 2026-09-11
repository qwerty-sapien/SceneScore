# Human audition protocol — pending

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
