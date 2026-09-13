# 07 — measure the exact demo candidate and get a human to listen

**Owns:** `reports/music-vertical/`, `artifacts/`. Writes no implementation code.
**Budget:** 40 minutes.

This node exists because `reports/phase3/GATE.md` shows the repo's real blocker is not
code: it is an unanswered approval, `AUDITION_PENDING`, and an AV offset of p95 137.33 ms
against a 50 ms target on an 8 fps source. Measuring and auditioning is the work, not the
paperwork after the work.

## Measure, on the exact candidate

Review the artifact that will be demoed, not a substitute fixture. Record its hashes
first.

Report these separately, never summed:

| Interval | What it is |
|---|---|
| `t4 - t3` | control request to transport receipt |
| `t5 - t4` | **accepted control to scheduled audible onset — the 300 ms claim** |
| `t6 - t5` | boundary wait, musical and unbounded by design |
| video vs audio clock | last-200-frame absolute offset, p95 and max |

State sample count, percentile method, browser, sample rate, duration and load. A
scheduled onset is not an acoustic onset: if you have not captured a microphone or loopback
signal, `physical_output_measured` stays false and no acoustic claim is made. Do not claim
precision finer than the 8 fps source supports.

Compare against the previous figures in `reports/phase3/GATE.md`. A regression is a
finding, not something to smooth over.

## Audition

A named human listens to the full take and records a verdict with date and asset hash:

- Does the tune stay recognizable and pleasant after transformation?
- Are ornaments sparse enough to feel intentional rather than mechanical?
- Does approach build without giving away the outcome?
- **Does a near miss read as withheld resolution rather than a weak hit?**
- **Does a small object bouncing off a large one put the figure on the small object?**
- Does the acknowledgement register as an immediate response to the control?
- Does the key change land coherently, without a jarring pitch or a truncated cadence?
- Do the animation-driven changes support the visual action rather than distract from it?

If nobody listens inside the timebox, the verdict is `AUDITION_PENDING` and the pack says
so. An automated identity, a schema check or a model's opinion of a rendered file is not
an audition and must not be recorded as one.

## Deliver

One report with: exact asset and config hashes; commands actually run; the measurements
above; the audition verdict or its absence; every check marked passed, failed, blocked or
not run; and defects recorded by timestamp with the owning node named.

## Done when

The report exists and a reader can tell exactly what was heard, what was measured, what was
not, and by whom.
