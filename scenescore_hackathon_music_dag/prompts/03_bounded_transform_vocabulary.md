# 03 — bounded, rhythm-preserving performance vocabulary

**Owns:** `modules/music/events.py`, a new `modules/music/ornament.py`,
`modules/music/tests/`. **Budget:** 50 minutes.

`resolve_events`, `apply_swing`, `swung_tick` and `transpose_events` already exist and are
tested. Build the ornament layer on top of them. The default path preserves the tune's
phrase and bar timing; anything that does not must say so in the transform request.

## The vocabulary

Implement a typed transform request — one small record, not style conditionals scattered
through the renderer. Each entry declares `preserves_duration: true|false`.

Duration-preserving (the default set): articulation change, velocity change, grace-note
stealing from the following note, mordent, turn, trill inside the occupied slot, tremolo,
octave doubling, and chord or arpeggio redistribution inside the existing harmonic slot.

Bounded creative (rare, budgeted): chord-tone and pentatonic/blues runs, chromatic
approach notes, and a short ascending or descending flourish. Pitches derive from the
current key and chord plus the declared rule set. Free random pitch generation is
forbidden.

## Budgets, enforced not documented

- At most `max_events_per_second_added` (12) new events per second.
- At most `max_simultaneous_ornaments` (2) overlapping ornaments.
- No two ornaments of the same kind within one bar on the same lane.
- Density decisions are seeded; the same seed, input and version yields byte-identical
  output.

## Invariants, tested

No note outside its allowed time slot unless explicitly marked. No zero, negative or
malformed durations. No hanging notes. Stable total score duration. MIDI pitch and
velocity in range. Swing applied exactly once to eligible events using the composition's
selected policy. Register bounds respected after every transposition. Unpitched brushes
unchanged by every transform. Foley untouched.

Anti-ugliness checks, which are the ones that actually matter for a demo: no
low-register cluster below the declared floor; no bar where every eligible note is
decorated; no ornament stacked on an ornament; total event count per bar within the
plan's budget.

## Forbidden

Rewriting the melody. Changing meter or bar topology. Applying swing twice. Transposing
brushes. Reaching into the renderer to special-case a style. Adding a transform the
current renderer cannot voice cleanly — a vocabulary that sounds bad is worse than a
smaller one.

## Done when

The typed request drives every ornament, invariants and anti-ugliness checks pass,
determinism holds under a fixed seed, and a short A/B render demonstrates the vocabulary
without it sounding mechanical.
