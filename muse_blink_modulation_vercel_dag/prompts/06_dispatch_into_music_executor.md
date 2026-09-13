# 06 — dispatch into the music executor

**Owns:** `modules/muse/runtime/dispatch.py`, `tests/ts/muse-dispatch.test.ts`. **Budget:**
30 minutes. Deliberately thin. If this node grows, something has crossed the seam.

Consume the frozen `ControlAction` from node 01 and hand it to the music engine's existing
entry point. Duplicate no EEG logic and no music theory.

## On an accepted double blink

1. Dispatch exactly once.
2. Let the music engine schedule its precomputed acknowledgement, run the progression and
   land the key. You observe; you do not schedule.
3. Update any UI state from the **actual music-engine state**, never from an optimistic
   local animation. A UI that shows a key change the engine refused is worse than a UI that
   shows nothing.
4. Record `t2` through `t6`, keeping detector latency, dispatch latency, responsiveness and
   boundary wait as four separate numbers.

## Equivalence is the acceptance criterion

Keyboard, simulated, replayed and live events must reach `Timeline.submit` through the
identical path with identical validation. Prove it with a test that runs the same assertion
set across all four sources, not with a comment claiming it.

Preserve every existing rejection: `stale_plan`, `unmapped_or_stale_clock`,
`future_expired_or_out_of_order`, `duplicate`, `one_pending_request_limit`,
`experimental_or_invalid_action`, `transport_not_playing`,
`no_feasible_boundary_before_expiry`. Surface the reason; never swallow it.

## Tests

Flood and debounce: a burst of detector artifacts cannot queue a modulation cascade. A
duplicate `id` or `sequence_id` is refused. An expired action is dropped with a reason, not
executed late. A control arriving while one is pending is refused with
`one_pending_request_limit`. Pause clears pending controls. Four-source equivalence.

## Forbidden

Choosing a key, chord, voicing or boundary. Computing `signed_semitones`. Writing to
`packages/audio/` — that belongs to the music pack; send a scoped request. Retrying a
rejected action. Any network call on this path.

## Done when

An accepted blink and a keyboard press are indistinguishable downstream, the four-source
equivalence test passes, and the ladder stamps come back with real values.
