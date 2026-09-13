# 02 — make one composition demo-ready

**Owns:** `modules/music/catalog.py`, `modules/music/fixtures/`, `modules/music/AUDITION.md`.
**Budget:** 40 minutes.

Four original compositions and three brush grooves already exist as unauditioned seeds.
You are not choosing a tune from the world; you are making one of these good enough to
carry a demo, and recording honestly what you did and did not verify.

## Deliver

1. **Render the unmodified source** for the frozen composition and groove and listen to it.
   Record renderer version, sample rate, duration, peak, RMS and clipping count. A render
   that has not been listened to is not an audition.

2. **A clean ending.** The score must land naturally at the scene duration frozen in 00.
   Author an explicit ending region rather than truncating. Never cut through a cadence.
   If a small global tempo adjustment is needed, state the old and new BPM and why.

3. **Declared safe harmonic boundaries.** Node 05 needs to know where a key change may
   land. Mark bar or phrase boundaries as eligible arrival points, with at least one
   eligible boundary within any 4-second window of the demo, or the 300 ms acknowledgement
   will be followed by an uncomfortably long wait.

4. **The Velvet Orbit correction.** `reports/media-evaluation/REVIEW.md` records that the
   sparse `velvet_orbit_v1` lead sheet incorrectly calls it straight rag. Fix it as a
   **versioned correction** with a new artifact; frozen prior evidence is preserved, not
   edited in place. If Velvet Orbit is not on the demo path, record the correction as a
   deferred note rather than spending slice time on it.

5. **Provenance.** Source hash for every composition and groove touched, written into
   `AUDITION.md` alongside the audition verdict, reviewer name and date — or an explicit
   `AUDITION_PENDING` if nobody listened.

## Tests

Bar and tick totals; exact groove lookup by id **and** version (unknown groove is an
error, never a fallback); pitch, velocity and register bounds; beat-to-second conversion
across the tempo map; swing applied exactly once; unpitched brush invariance under
transposition; rendered audio is non-silent, the expected duration, and free of clipped
samples.

## Forbidden

Composing a new tune. Downloading third-party MIDI or arrangements. Transposing an
unpitched groove. Editing a frozen artifact in place. Writing an audition verdict nobody
performed. Expanding the catalogue — this slice needs one good composition, not four
mediocre ones.

## Done when

One composition and groove render cleanly at the frozen duration with a real ending,
eligible arrival boundaries are declared, and `AUDITION.md` records either a named human
verdict or an honest `AUDITION_PENDING`.
