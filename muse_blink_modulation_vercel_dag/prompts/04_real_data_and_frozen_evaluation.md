# 04 — collect what you can, freeze, and report honestly

**Owns:** `modules/muse/training/`, `reports/muse-vertical/`. **Budget:** 60 minutes, or 20
if node 00 found no participant.

## If a consenting participant is available

Collect under `PARTICIPANT_PROTOCOL.md`: multiple short sessions, at least one deliberate
removal and refit, and natural-activity negatives with logged exposure. Optimize collection
quality before model complexity — thirty clean labelled gestures across two refits beat
three hundred from one uninterrupted sitting.

Assign train, development and final-test membership **before** comparing rungs A, B and C.
Fit preprocessing, thresholds and grammar on development data only. Claim the final split
through `FinalTestLock` and do not reopen it. `choose_development` already encodes the
selection gates: `recall_floor=0.95`, `max_latency_s=0.75`, `min_availability=0.95`.

Pre-register the event matcher before the final evaluation: one-to-one accepted decision to
independently verified gesture, chronological to the nearest eligible final-blink timestamp
within a development-chosen window, with the tie rule and numerical tolerance declared in
the locked config. That window is not the latency target.

## If no participant is available

Do not manufacture one. Run the full pipeline on replay and fixtures, export
`PIPELINE_TESTED_ONLY`, and state in one sentence what would be needed for the next status.
This is a successful outcome for this node, not a failure.

## Report

Event-level TP, FN and FP. Recall. Precision, undefined when the denominator is zero — say
undefined, do not write 0 or 1. False activations per **armed** hour and per **elapsed
monitored** hour, with the denominator named at every use. Candidate coverage. Ambiguous
label counts. Decision latency distribution. Per-session and per-refit breakdown alongside
pooled counts. Every miss by cause.

Duplicates and unmatched controls count as false activations. Every unmatched verified
gesture counts as a miss, including those lost to quality abstention or refractory.

Confidence scores are not probabilities unless calibration was independently tested. Say so.

## Statistical honesty

`docs/EVALUATION.md` gives the arithmetic: a one-sided 95% all-success recall lower bound
is `0.05**(1/n)`, so n=100 all successes supports about 0.9705, and roughly 299 would be
needed for 0.99. A zero-false-event upper rate is `-log(0.05)/hours`, so one clean hour
supports about 2.996/hour, and roughly six would be needed for 0.5/hour. Session dependence
and drift still require assessment on top of that.

Whatever n you collected in six hours, compute the bound and report it. Do not report a
point estimate as a capability.

## Deliver

`reports/muse-vertical/` with: exact code, config, data and model hashes; the commands
actually run; split membership; the locked matcher config; the results above; the release
status; and every check marked passed, failed, blocked or not run. Plus a rollback command
to the deterministic baseline.

## Forbidden

Tuning after seeing final-test results. Retrospective threshold adjustment. Reporting
synthetic performance as real. Promoting the status to match the effort. Deleting or
reshaping an inconvenient session.

## Done when

The report exists, the status is the one the data supports, and a reviewer can reconstruct
every number from the recorded hashes and commands.
