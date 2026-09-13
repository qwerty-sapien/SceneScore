# 07 — end-to-end gate

**Owns:** `reports/muse-vertical/GATE.md`. Writes no implementation code. **Budget:** 30
minutes. Always runs.

Validate the replayable software path always, and the worn-headset path when hardware is
available. Review the exact demo candidate, not a substitute fixture.

## Required checks

- Production build and deploy succeed; the surface loads with no hardware attached.
- The deployed UI distinguishes `live`, `replay` and `simulated`, and cannot show `live`
  without a live stream. Verified by test, not by looking at it once.
- The chosen hardware path connects from the actual target setup, or is marked **blocked**
  with the precise reason from node 00.
- Raw EEG remained local under the chosen architecture. Check, do not assume.
- Deliberate double blinks produce exactly one semantic event each. A short natural-activity
  segment produces no event storm; report the actual count and the exposure denominator.
- A triple produces nothing. A dropout mid-gesture clears state and requires re-arm.
- The accepted event reaches the same music-control path as keyboard simulation, proven by
  the four-source equivalence test.
- Every ladder interval reported separately: closure delay disclosed, `t5 - t4` measured
  against the 300 ms target, boundary wait not folded in, `physical_output_measured` false
  unless a microphone or loopback capture exists.
- UI key and chord state matches the actual audio engine state.
- Exact model, config and source hashes recorded, plus a rollback-to-baseline command.
- `python3 examples/check_pack_examples.py` passes.

## Blind run

Run a short free-running negative segment and several deliberate trials **without tuning
after observing the results**. Report actual counts and the interval bound from node 04's
arithmetic. If you tune after this run, it is no longer a blind run and the report says so.

## Verdict rules

Assign a `docs/EVALUATION.md` release status. Within this timebox the honest ceiling is
`PIPELINE_TESTED_ONLY`, or `REAL_DATA_EXPLORATORY` with a consenting participant. A
detector status is not a product release status. Do not promote either to match effort
spent.

If the live path could not be completed, record a precise blocker and keep a convincing
replay and simulated demo — clearly not described as hardware-validated.

## Deliver

`GATE.md` with exact identities assessed, each check passed, failed, blocked or not run,
defects by timestamp routed to their owning node, the release status and its reasoning, the
exact demo commands, and a 60-second fallback procedure using keyboard input.

## Forbidden

Expanding scope to fix what you find. Passing a gate on a substitute fixture. Turning a
missing fact into a passing one. Reporting a single blink-to-music number.
