# 04 — map the eight motion semantics to musical intent

**Owns:** `modules/arranger/core.py`, `modules/arranger/tests/`, `modules/arranger/golden/`.
**Budget:** 50 minutes. **Reference:** `examples/motion_event_taxonomy.json`.

This is the node that makes someone say *the music is reacting to that animation*. It maps
events to **intents**, never to individual notes.

## Start from what exists

`LANES` already defines `(approach, ornament)`, `(separation, dynamics)`,
`(surface_gap, phrasing)`, `(collision, timbre)`, `(vertical_motion, register)`, and
`curve` already does bounded linear mapping with clamping. Extend that table; do not
invent a second mapping language.

Add the `tension` and `accent` lanes, and mappings for `near_miss`, `contact_onset`,
`contact_sustain`, `contact_release` and `asymmetric_rebound` with the ranges and drivers
in the taxonomy.

## The two that carry the demo

**`near_miss` must sound like a withheld resolution, not a weak approach.** Hold the
prevailing harmony unresolved for at least one beat past the minimum — sus4, or an upper
structure with the third withheld — then release without a downbeat accent. The absence of
the hit is the musical event. A near miss must never produce a percussive transient, never
fire Foley, and never trigger a key change. Until the moment of resolution, an approach
that ends in a near miss must be indistinguishable from one that ends in contact;
pre-announcing the outcome destroys the effect.

**`asymmetric_rebound` gives the small object the voice.** The rebounding object's motif
takes a grace-note or appoggiatura at the contact tick, register biased up by
`curve(register, area_ratio)`, velocity scaled by `speed_retention`. The anchor object gets
at most one low damped note and never a melodic figure. A rebound chain inside
`rebound_window_s` decays in velocity and stays inside the density budget.

## Output

A time-indexed control track aligned to the exact animation clock, deterministic for a
fixed seed, with no event spilling past the media duration. Persistent object voices keep
their sonic identity across the whole take, including across a key change.

Missing or out-of-coverage inputs fall back to the unmodified score with a logged reason.
A sparse compact motion summary may be adequate for planning and inadequate for causal
conducting; when coverage is insufficient, it holds.

## Tests

Deterministic alignment against a golden fixture. No event past media duration. Every lane
range clamped. Null driver inputs produce the unmodified score plus a reason, never a
default value. Equal-area contact produces no rebound figure. A near miss produces no
accent and no Foley. Object identity is stable across a modulation. Density stays inside
budget with all eight event types firing in the same second.

## Forbidden

Mapping an event straight to a specific note. Inferring emotion or intent from geometry.
Letting a mapping change key, gain, articulation or expression preset as a side effect.
Writing to `packages/audio/model.ts` — that belongs to node 05; send a scoped request.

## Done when

The golden fixture is deterministic, all eight types map, near miss and rebound behave as
specified, and an A/B of mapped against unmodified is audibly different in ways a listener
can name.
