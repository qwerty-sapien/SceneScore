# 05 — the precomputed harmonic transition

**Owns:** a new `modules/music/transitions.py`, `packages/audio/model.ts`,
`packages/audio/tests/`. **Budget:** 45 minutes. **Reference:**
`examples/transition_table.json`, `INTERFACE_CONTRACT.md`.

The table is **shipped with this pack**, already validated: 216 resolved entries, every
voice leading within 3 semitones per voice, 14 of 14 negative controls rejected. You are
not designing it from scratch. You are loading it, honouring it, and wiring it to audio.

## Why it is precomputed

Latency. Between an accepted control and the scheduled acknowledgement there is no search,
no inference, no network call, no disk read and no recompilation of the arrangement.
Lookup is `(tier, from_pc, signed_semitones, lead_bars) -> entry` and is O(1). This is a
requirement, not a preference; a runtime chord chooser fails this node no matter how good
it sounds.

## Two tiers

`contract_default` — ±2 semitones, gestures `dominant_prep_v1`, `backdoor_v1`,
`ii_v_i_v1`. Always on. Already legal under `docs/VISION.md` and already the shape
`packages/audio/model.ts::transition` implements.

`auditioned_jazz` — adds ±5, `tritone_sub_v1`, `common_tone_dim_v1`,
`modal_pivot_biii_v1`. Gated behind `SCENESCORE_JAZZ_TRANSITIONS`, **off** until a named
human auditions each edge and a decision record amends VISION eligibility. Shipping it on
without that audition is a gate failure.

Gesture selection is by available lead: half a bar, one bar or two bars of headroom before
the arrival boundary. Deterministic, declared in the table, never chosen at runtime by
taste.

## On an accepted control

1. **Acknowledge audibly within 300 ms.** Schedule the gesture's declared acknowledgement —
   a quiet guide-tone dyad, velocity ≤ 60, or a held common tone. It must not change master
   gain, must not alter articulation or the expression preset, and must not interrupt a
   sounding melody note incorrectly. This is the only thing the listener hears before the
   boundary, so it is the whole perceived responsiveness of the system.
2. **Run the progression** from the entry's slots, splitting any note sounding across the
   boundary the way `transition()` already does.
3. **Land at the next declared safe bar** from node 02's eligible boundaries.
4. **Move only the following voices:** `bass`, `harmony-0`, `harmony-1`, `harmony-2`. The
   lead, brushes, object motifs and Foley are untouched.
5. **Bound every pitch** into `[register_min, register_max]` after transposition.

`signed_semitones` arrives on the `ControlAction` from the plan's motion policy. Do not
recompute it, do not override it, and do not let the gesture choose it.

## Tests

Every one of the 216 entries reaches a valid stable state. Voice leading within 3
semitones per voice on every consecutive slot pair. No entry changes gain, articulation or
expression. Acknowledgement scheduled within 300 ms of acceptance in the fake-clock test.
A note sounding across the boundary is split, not dropped and not doubled. Register bounds
hold. `auditioned_jazz` entries are unreachable with the flag off. Two modulations in
sequence return to a valid state. A modulation during a `near_miss` hold resolves
coherently rather than stacking two unresolved gestures.

Run `python3 examples/check_pack_examples.py` and keep it passing after any table edit.

## Forbidden

Choosing a destination at runtime. Any network, model or LLM call on this path.
Allocation proportional to score length. Editing the table without rerunning the checker.
Enabling the jazz tier without a recorded audition. Writing to `modules/arranger/core.py` —
that belongs to node 04; send a scoped request.

## Done when

Both tiers load from the frozen table, the default tier is wired end to end, the
acknowledgement is measurably inside 300 ms on the fake clock, and every modulation edge
in the enabled tier has a passing test.
