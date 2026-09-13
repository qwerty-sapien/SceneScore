# 01 — freeze the control seam and instrument the ladder

**Owns:** a new `modules/muse/runtime/`, `modules/muse/evaluation/`. **Budget:** 45
minutes. **Reference:** `INTERFACE_CONTRACT.md`, `examples/latency_ladder.json`.

This node runs before the detector work on purpose. Freezing the boundary is what lets
nodes 05 and 06 proceed in parallel with 03 and 04, and it prevents three nodes inventing
three slightly different event shapes.

## Deliver

1. **A runtime adapter** from `GestureEvent` to `ControlAction`, emitting exactly one
   accepted action per closed deliberate double blink. It populates `id`, `sequence_id`,
   `action: request_modulation`, `profile: double_modulate_mvp`, `gesture_count: 2`,
   `request`, `expires`, `approved_plan_hash`, `scene_policy_id`, `provenance.source_mode`,
   plus detector and model version and enough diagnostics for latency evaluation.

   It does **not** compute `signed_semitones`. The approved plan's motion policy does.

2. **A `ClockMapping`** from the device epoch to the browser audio epoch, with anchors,
   offset, rate estimate, uncertainty and a validity window. A value crossing domains
   without it is rejected as `unmapped_or_stale_clock`, not rounded.

3. **Three sources, one entry point.** Live detector, recorded replay and explicit
   simulator all construct the same record and pass the same validation. The keyboard path
   in `apps/web` already exists and is the fourth; do not fork it.

4. **Ladder instrumentation.** Emit a latency trace record carrying `t0` through `t4` with
   their declared clock domains. `t5` and `t6` come back from the music engine. Report the
   intervals separately; a single blink-to-music number is not an acceptable output.

## Enforce at the boundary

One accepted action per closed gesture. No second blink may trigger before closure. Triple
and ambiguous trains rejected with a documented rule — never a prefix double. Partial state
cleared on dropout, quality loss, reconnect, refit and model reload, each requiring warmup
and re-arm. Duplicate `id` or `sequence_id` rejected, never re-run. An upstream-suppressed
action stays suppressed downstream. Rejections carry an enumerated reason.

Raw EEG does not cross this boundary. Diagnostics may carry scores and quality flags; they
may not carry samples.

## Tests

Every case in `examples/gesture_grammar_cases.json` — four positive, ten negative — through
the real adapter, including the dropout and quality-loss faults. Prefix safety: the triple
case emits zero actions. Clock mapping rejects a stale or out-of-window conversion.
Duplicate dispatch is refused. Flood: a burst of detector artifacts cannot queue a cascade.
The simulator and the live path produce byte-identical records given identical inputs.

Run `python3 examples/check_pack_examples.py` and keep it passing.

## Forbidden

Choosing a key, chord, voicing or boundary. Computing `signed_semitones`. Any network call,
model or LLM between acceptance and dispatch. Emitting before closure. A fast path that
skips validation for live events.

## Done when

The seam is frozen and documented, all fourteen grammar cases pass through the real
adapter, the ladder stamps are emitted with correct clock domains, and nodes 05 and 06 can
start without waiting for a detector.
