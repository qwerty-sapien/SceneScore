# 03 — the detector ladder

**Owns:** `modules/muse/baseline/`, `modules/muse/training/pipeline.py`. **Budget:** 60
minutes.

Three rungs, in this order, on identical held-out data. Do not skip a rung because a later
one sounds better.

| Rung | What it is | Where it lives |
|---|---|---|
| A | Attributed RAGTM comparator | `baseline/ragtm.py::RagtmCandidatePort`, defaults preserved |
| B | Causal threshold and template baseline | `baseline/causal.py::CausalBaseline` + `Grammar` |
| C | Small regularized classifier on bounded features | `training/pipeline.py::fit_logistic` over `causal_features` |

A is a comparator and must never issue a control. B is the deterministic floor everything
else must beat. C is `("peak_z","bilateral_ratio","duration_ms","rise_slope","fall_slope","imu_rms")`
with L2 regularization — a regularized logistic or small tabular model is sufficient for
this timebox. Do not build a deep EEG model unless the ladder demonstrably fails and time
remains, which within six hours it will not.

`self_train` exists for a semi-supervised extension. Attempt it only after A–C work, only
on training-partition unlabelled data, and promote it only if held-out evidence improves.

## Causality is not optional

Everything claimed to work live is causal: one-pole low-pass, causal median and MAD
normalization, duration hysteresis, and a score computed from each sample **before** that
sample updates the running statistics. An acausal filter that peeks forward produces a
number that cannot be reproduced live, no matter how good it looks offline.

Warmup is enforced: no decision before `warmup_s` of established baseline, and warmup
restarts after every reset.

## Grammar lives here, and it is a latency decision

`Grammar` closes the sequence before committing. The closure floor is
`1000 * max_gap_s` = 500 ms at current config, leaving 250 ms of headroom under the repo's
750 ms p95 gate. Raising `max_gap_s` above 0.73 s makes that gate unreachable regardless of
how fast the classifier runs. Any change to `max_gap_s`, `min_separation_s`,
`min_duration_s` or `max_duration_s` is reported as a latency change and re-checked against
`examples/latency_ladder.json`.

## Report the whole pipeline

Candidate coverage — gestures the candidate stage never surfaced are misses, and a
classifier's score on the candidates that survived is not the system's recall. Grammar
rejections, quality abstention and refractory periods all count. Report decision latency as
a distribution, not a mean.

## Tests

All fourteen cases in `examples/gesture_grammar_cases.json`. Prefix safety: a triple emits
nothing. A candidate whose score is computed after the statistics update must fail a
causality test. Reset semantics on dropout, quality loss and refit. Determinism: identical
input and config produce identical decisions and an identical config digest. RAGTM
comparator parity against the existing Node oracle is preserved.

## Forbidden

Using cue timing, button presses, labels or soundtrack state as features. Tuning on the
final test split. Letting the comparator issue a control. Reporting classifier-only
performance as system performance. Claiming accuracy from synthetic fixtures.

## Done when

All three rungs run on the same held-out data, the grammar passes every control case, the
causality tests pass, and the handoff states plainly which rung is the candidate and on how
much real data.
