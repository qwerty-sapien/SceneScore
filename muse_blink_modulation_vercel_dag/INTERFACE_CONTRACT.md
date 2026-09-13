# Cross-pack interface contract — accepted double blink to audible modulation

This file is **byte-identical** in `scenescore_hackathon_music_dag_v2/` and
`muse_blink_modulation_vercel_dag_v2/`. Both `CHECKSUMS.json` files record the same
digest. If the two copies diverge, both packs are invalid until an integrator decision
record reconciles them. Neither pack may edit it unilaterally.

It exists because the two packs previously described the same seam in two different
vocabularies and both claimed to own the harmonic transition.

## Single-owner rule

| Concern | Owning pack / node | Everyone else |
|---|---|---|
| EEG transport, candidates, gesture grammar | muse 02, 03 | may read diagnostics only |
| `ControlAction` construction and dispatch | muse 01 | may not re-derive fields |
| Transition table, voicings, arrival boundary | music 05 | consumes by ID, never re-plans |
| Audio scheduling and `Timeline.submit` | music 06 | submits, never schedules directly |
| Approval semantics and plan hashing | music 06 | may not synthesize an approval |
| Frozen contract `contracts/0.1/schema.json` | repo integrator | scoped request in `docs/requests/` |

A node needing a change outside its column writes a scoped change request. It does not
edit across the line and does not fork a parallel implementation.

## The seam record

The seam is exactly one `ControlAction` per accepted gesture, already defined by frozen
contract 0.1 and already validated by `packages/audio/transport.ts::Timeline.submit`.
Producers must populate, and consumers must not recompute:

- `id`, `sequence_id` — unique; a replayed or duplicated id is rejected, never re-run.
- `action` = `request_modulation`, `profile` = `double_modulate_mvp`, `gesture_count` = 2.
  Any other triple is rejected as `experimental_or_invalid_action`.
- `request.{seconds, clock, epoch}` — clock is `audio`, epoch must match the live
  transport epoch. A device-clock value that has not passed through a validated
  `ClockMapping` is rejected as `unmapped_or_stale_clock`.
- `expires.seconds` — a modulation that cannot reach a feasible boundary before expiry is
  rejected as `no_feasible_boundary_before_expiry`, not silently deferred.
- `approved_plan_hash`, `scene_policy_id` — must match the currently playing approved
  plan or the action is rejected as `stale_plan`.
- `signed_semitones` — **the detector does not choose this.** See below.
- `provenance.source_mode` ∈ `LIVE_MUSE | REAL_REPLAY | SYNTHETIC_TEST | KEYBOARD`.
- `status`, `reason` — a suppressed upstream action stays suppressed downstream.

## Who decides what

The blink decides **when**. The scene decides **which way**. The table decides **how**.

`signed_semitones` comes from the approved plan's motion policy evaluated at the request
timestamp — `motion_direction` in `modules/arranger/core.py` and `direction` in
`packages/audio/model.ts`, causal world-Z average over `lookback_s` with `deadband_m_s`.
Unknown or stale motion coverage holds and yields a logged no-op; it is never
back-filled, never guessed, and never taken from the gesture. This is a declared creative
mapping, not acoustics and not intent inference.

## Four sources, one entry point

`LIVE_MUSE`, `REAL_REPLAY`, `SYNTHETIC_TEST` and `KEYBOARD` must construct the same
record type and call the same `Timeline.submit`. A code path that only the keyboard can
reach, or a live path that bypasses validation for speed, invalidates every latency and
correctness claim made about the other three. The visible mode label is part of the
contract: the deployed UI must never render a replayed or simulated event as `LIVE_MUSE`.

## Latency ladder

Report these intervals separately. Collapsing them is the failure mode this contract
exists to prevent.

| Stamp | Meaning | Clock |
|---|---|---|
| `t0_final_blink_s` | last physical blink of the pair | device |
| `t1_decision_s` | detector commits after sequence closure | device |
| `t2_dispatch_s` | `ControlAction` constructed and dispatched | host monotonic |
| `t3_request_s` | `action.request.seconds` | audio |
| `t4_received_s` | `Decision.audio_received_s` | audio |
| `t5_ack_onset_s` | first scheduled audible acknowledgement onset | audio |
| `t6_boundary_s` | `Decision.boundary_s`, new key established | audio |

Budgets: `t1 − t0` ≤ 750 ms p95 (sequence closure is real latency and is disclosed, not
hidden). `t4 − t3` ≤ 5 ms. **`t5 − t4` ≤ 300 ms — this is the responsiveness claim.**
`t6` is musical and deliberately unbounded; it must never be added into, or subtracted
from, any of the above. A single "blink to music" number is not an acceptable report.

Clock domains do not silently mix. Crossing device to audio requires a `ClockMapping`
with anchors, offset, rate and validity; a stale mapping is an error, not a rounding
problem. `t5` is a scheduled onset, not an acoustic one: an acoustic claim requires
loopback or microphone capture and must say so.

## Forbidden on the accepted path

Between an accepted gesture and the scheduled acknowledgement there must be no network
call, no model inference, no LLM, no disk read, no unbounded search over transitions, no
allocation proportional to score length, and no recompilation of the arrangement. The
transition is a table lookup keyed by `(from_pc, signed_semitones, gesture_id)` over a
frozen table, plus a bounded voicing application. This is the reason the table is
precomputed: it is a latency requirement, not a stylistic preference.

## Failure semantics

Signal-quality loss, dropout, reconnect or refit clears partial gesture state and
requires re-arm; music continues unchanged. A rejected action produces a visible reason
from the enumerated set, never a silent drop. Repeated detector artifacts cannot queue a
cascade: one pending request at a time, enforced at the transport. Pausing clears pending
controls. An expired action is dropped and reported, never executed late.
