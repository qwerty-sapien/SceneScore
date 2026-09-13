# Coordinator — animation-to-music vertical, six hours

## Goal

One animation, one original score, eight motion semantics that audibly change the
performance, and an accepted deliberate double blink that produces a musically sensible
harmonic transition — acknowledged audibly within 300 ms of acceptance and landing in the
new key at the next declared safe bar.

Two claims must survive an unfriendly listener: *the music is reacting to that animation*,
and *that blink caused that key change*. Everything in this pack serves one of those two.

## Product boundary

95–97% of musical identity and note placement comes from the existing original catalogue
in `modules/music/catalog.py`. Transformation is performance, not composition. The
creative layer is small, bounded, seeded and reproducible.

This pack owns the music side of the seam only. EEG acquisition, detection and gesture
grammar belong to the companion Muse pack. Both packs share
`INTERFACE_CONTRACT.md` byte-for-byte; read its ownership table before assuming you may
touch something.

## The three decisions this revision locks

1. **The blink decides when; the scene decides which way; the table decides how.**
   `signed_semitones` comes from the approved plan's causal world-Z motion policy at the
   request timestamp, never from the gesture. Unknown or deadband motion is a logged
   no-op, not a guess.
2. **Two harmonic tiers.** `contract_default` is ±2 semitones with three gestures, always
   on, already legal under `docs/VISION.md`. `auditioned_jazz` adds ±5, tritone
   substitution, common-tone diminished and a modal pivot; it stays behind the
   `SCENESCORE_JAZZ_TRANSITIONS` flag until a named human has auditioned each edge and a
   decision record amends VISION eligibility. Shipping the flag on without that audition
   is a gate failure, not a stretch goal.
3. **All eight motion semantics, including a new one.** approach, near_miss, separation,
   contact_onset, contact_sustain, contact_release and collision already come out of
   `pair_timeline`. `asymmetric_rebound` — a small object bouncing off a larger one — is
   new, derived, and carries explicit `mass_inferred: false` because an evaluated-area
   ratio is a geometric proxy and nothing more.

## Duration policy

The animation duration is authoritative. The hero scene is 30 s at 8 fps. Do not force a
global duration, do not truncate through a cadence, and do not stretch the animation to
fit the music. Adjust with phrase selection, a small global tempo change, or authored
repeat and ending regions — in that order of preference.

## Execution

Run 00 first and freeze the slice. 01 and 02 then run concurrently on disjoint module
trees. 03 and 05 run concurrently after 02. 04 joins 01 and 03. 06 integrates 04 and 05.
07 measures and auditions the exact demo candidate. 08 is the independent gate.

Repairs route to the owning node and rerun affected downstream gates. Three repair
attempts per gate, then report the failure honestly rather than widening scope.

## Success gate

A human watches one animation and hears the score react to approach, near miss, contact
and rebound in ways they can name without being told. They then trigger a control event
and hear an immediate acknowledgement, followed by a coherent landing in a new key. The
measured interval from accepted control to scheduled audible onset is recorded, separately
from detector latency and separately from the boundary wait.

If any part of that is not true at the six-hour mark, the deliverable is an honest failed
or blocked status with the measurements that were actually taken. `docs/EVALUATION.md`
release statuses apply; within this timebox the reachable ceiling is
`PIPELINE_TESTED_ONLY` plus a recorded audition verdict.
