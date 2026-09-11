# Phase 3A: compare blink models, lock evaluation and export a deployment artifact

Prerequisite: phase 2A and real, independently labelled recording sessions. Read AGENTS, VISION, EVALUATION, LINEAGE, contracts and the blink-evaluation skill. Own `modules/muse/training/`, `modules/muse/evaluation/`, local detector-model implementations and `handoffs/03A.md`. Do not alter root schemas or musical controls. Keep the baseline API stable.

## Objective and scientific boundary
Seek very high event-level recall with very few false activations. Do not assume unsupervised learning is inherently more accurate. Deliberate and natural blink clusters can generate overlapping observations; an unlabelled cluster has no intrinsic intent label. The owner providing positive double-blink trials is supervised information. Explore semi-supervised and unsupervised methods, but promote only measured improvements against simple baselines.

No real data means build the training/evaluation pipeline, tests and acquisition instructions, then report `INSUFFICIENT_REAL_DATA`. Never train on synthetic fixtures and publish the result as Muse performance. Never report cross-person generalization from one person's recordings.

## Data and split integrity
Audit annotations before training. Use participant, recording/session, headset refit and trial groups. Train/development/final-test sessions are split BEFORE windows, augmentations or feature fitting. No windows or overlapping chunks from a session can enter different split roles. Reserve genuine natural-activity recordings and a later headset-refit session for final evaluation.

Fit scaling, feature selection, dimensionality reduction, pseudo-labels, template construction and hyperparameters only on the allowed training/development partition. Self-supervised use of test recordings is still leakage. Freeze any deployment calibration/adaptation rule before testing, use a separate declared calibration segment, and never retrospectively normalize from future samples. Report calibrated versus uncalibrated deployment separately.

All reported online results must use causal filtering and actual temporal windows. Offline zero-phase filters, centred windows and future-frame knowledge may be used for annotation aids only, not as evidence of live accuracy. Avoid suppressing the ocular artifact being detected. Raw data remain auditable and local.

## Model comparison ladder
A. Unchanged RAGTM detector when actually available; otherwise clearly named new baseline.
B. Causal robust-threshold/template candidate detector plus finite-state gesture grammar.
C. Small supervised regularized logistic model or gradient-boosted tabular classifier on candidate waveform/context features, with training-only calibration and the same grammar.
D. Semi-supervised self-training or label spreading, using genuine training-only unlabelled intervals and an independent labelled development set. Cap pseudo-label quantities, require calibrated confidence, track class balance and audit likely errors. Do not simply relabel everything the baseline accepts as perfect truth.
E. An unsupervised anomaly/cluster baseline such as Isolation Forest or training-only PCA plus clustering. It identifies unusual patterns, not intent; cluster semantics/thresholds require labelled evaluation. Explain when movement or electrode artifacts dominate its novelty score.

A self-supervised small temporal encoder is a stretch experiment only after the above produce trustworthy replay evaluation and there is enough real data. Do not download a large EEG model blindly or assume incompatible channel layouts transfer.

Use a common feature/candidate interface, record latency and deployment cost, and keep model-choice comparisons on identical held-out recordings. Inspect raw frontal morphology, bilateral agreement, durations, slopes, amplitude relative to noise and optional motion context. No cue timing, label confirmation, user name or offline annotation metadata becomes a predictive feature.

## Optimization objective
ROC-AUC and average precision/PR curves are diagnostics. Their denominator, sampling scheme and aggregation unit must be explicit. They do not replace evaluation of complete gesture sequences in free-running recordings. A candidate classifier's AUC excludes upstream missed candidates, so also report candidate coverage and full pipeline misses.

Primary model selection: minimize observed false activations per hour subject to a development-set recall floor and bounded latency/availability. Explore a Pareto frontier or constrained Optuna study, with a small trial/time budget. Do not optimize a weighted score that hides unacceptable false activations. Hyperparameter tuning uses grouped development folds only. Final test is evaluated once for a selected frozen model; revisions need a new untouched test set.

Required end-to-end outputs:
- Matched TP, FP, FN, event recall, precision, F1 and one-to-one matching rules.
- False activations per armed hour AND per elapsed monitored hour, with cooldown and abstention durations disclosed.
- Recall over all instructed/verified gestures, including attempts during poor quality or cooldown; additionally report eligible/armed recall with an explicit denominator.
- Onset/final-blink-to-decision latency median and p95; downstream bar wait separately.
- Double versus triple confusion and ordinary-blink errors when applicable.
- Session-specific metrics, quality strata, refit drift, availability and suppression reasons.
- ROC-AUC, PR diagnostics and confidence intervals with the evaluation unit clearly labelled; never derive these from only accepted positive detections.

Use time-based one-to-one event matching with a frozen tolerance, fixed exclusion rules and independent labels. Count duplicate activations as FP. Do not widen the matching interval after seeing errors. Report ambiguous label counts and sensitivity analyses rather than dropping every difficult example.

## Honest uncertainty and release status
Aspirational targets: event recall >=99% and false activations <=0.5/hour under tested conditions, with a lower false rate as a stretch. These are goals, not a deadline guarantee.

With n successes in n independent opportunities, a one-sided 95% binomial lower bound is 0.05^(1/n). For 100/100 this is about 97.05%; roughly 299/299 are needed for a 99% lower bound. Session dependence makes this idealized calculation optimistic, so also use session-level uncertainty or explicitly report inadequate session count.

With zero false activations in T hours under a stationary Poisson assumption, the one-sided 95% upper bound is -log(0.05)/T, approximately 3/T per hour. Zero in 30 minutes allows roughly 6/hour; about six hours of relevant negative exposure with zero events is needed for a 0.5/hour upper bound. Report the assumptions and do not multiply evidence by replaying the same recording.

Statuses: `PIPELINE_TESTED_ONLY`, `REAL_DATA_EXPLORATORY`, `SUPERVISED_DEMO_READY`, `TARGET_STATISTICALLY_SUPPORTED`, or `NOT_READY`. Supervised demo readiness uses the separately specified pilot gate and requires transparent limited evidence. It is not equivalent to statistically establishing the aspirational target. A frozen simple baseline can be the correct deployment choice.

## Gesture grammar and exploratory controls
Double/triple mode must delay commitment until the closing interval; report that latency tradeoff. Do not emit a double action and later claim it was a triple. Default double-only mapping remains key change with invariant gain/articulation. Test a sequence rejected for excess blinks rather than treating two prefixes as valid doubles.

Amplitude-derived control requires within-session normalization, labelled intended effort categories and held-out refit repeatability. Voltage amplitude is affected by contact/motion and is not a verified physical blink-strength measurement. Keep it disabled unless it improves a defined expressive task. Do not directly map unbounded raw amplitudes to loudness.

## Artifact and exit gate
Export the chosen model, preprocessor parameters, channel/unit assumptions, grammar, thresholds, calibration procedure, train/data/version hashes, feature names, measured latency and an evaluation card. Prefer a safe documented format; do not load untrusted pickle files. Provide an unchanged real-replay command and a rollback to baseline. Online adaptation is off during the demo unless independently validated and explicitly enabled.

Run a held-out real session plus reconnect/packet-loss and replay-determinism tests. Separate software-only faults from empirical performance results. Write a concise failure taxonomy and the next targeted collection action. Do not keep optimizing indefinitely or manufacture 100% results to satisfy the aspiration.
