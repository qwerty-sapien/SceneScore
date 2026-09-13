# 08 — independent gate

**Owns:** `reports/music-vertical/GATE.md`. Writes no implementation code.
**Budget:** 30 minutes. This node always runs; a slice that skips its gate has produced
nothing.

Review the exact candidate from node 07, not a substitute fixture, and not the code you
would like to have shipped.

## Automated checks

- `make test` green: contracts, Python suite, ruff, TypeScript suite, typecheck, build.
- `python3 examples/check_pack_examples.py` still passes after every table or taxonomy edit.
- Deterministic score generation for a fixed seed, twice, byte-identical.
- Total score and media duration coherent; no event past media duration; no stuck notes.
- All eight motion semantics emit on the fixtures; equal-area contact emits no rebound;
  near miss emits no accent and no Foley.
- Every reachable modulation edge reaches a valid stable state; `auditioned_jazz` entries
  are unreachable with the flag off.
- Keyboard, synthetic and replay paths construct the same record and pass the same
  validation; no path bypasses `Timeline.submit`.
- Latency telemetry is present, and `t5 - t4` is reported without detector latency folded
  in and without the boundary wait subtracted out.
- Approval semantics intact: audition before approval, edits clear approval, no automated
  approval.
- Build and `make demo` still work from a clean checkout.

## Human checks

The node 07 audition verdict exists and is signed by a person, or the gate records
`AUDITION_PENDING` and does not pass.

## Verdict rules

Assign one of `docs/EVALUATION.md`'s release statuses. Within this timebox the honest
ceiling is `PIPELINE_TESTED_ONLY` plus a recorded audition verdict. Do not promote a status
because effort was spent. Do not describe schema validity, hash agreement or a model
review as audition, hardware validation or physical timing.

State plainly which of the eight motion semantics are demonstrated on the actual demo
scene and which are only covered by fixtures. Those are different claims.

## Deliver

`GATE.md` with: exact identities assessed; each check passed, failed, blocked or not run;
defects by timestamp routed to their owning node; the release status and why; the exact
demo commands; and a 60-second fallback procedure using keyboard input for when Muse
hardware is unavailable — which, within this timebox, it will be.

## Forbidden

Expanding scope to fix what you find — route the smallest repair to its owner and rerun
the affected gates. Passing a gate on a substitute fixture. Turning a missing fact into a
passing one.
