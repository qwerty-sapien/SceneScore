# Phase 3A — real-data research pipeline

Current result: **INSUFFICIENT_REAL_DATA / PIPELINE_TESTED_ONLY**. No deployment model was trained or exported. Numerical fixture fitting in unit tests demonstrates code behavior only. Raw recordings stay in ignored `private_data/02A`.

Run from the repository root:

```sh
PYTHONPATH=.:src .venv/bin/python -m modules.muse.training --data-root private_data/02A --index private_data/02A/split.json
PYTHONPATH=.:src .venv/bin/python -m pytest -q modules/muse/training modules/muse/evaluation
```

The audit CLI deliberately does not start training. A frozen index contains `sessions`, each with `session_id`, `participant_id`, `refit_id`, `role` (train/development/final_test), root-relative `path`, local `consent_ref`, and `content_sha256`. The hash is `pipeline.digest` of `{metadata, chunks, labels}` from the Phase 2A recorder. Assign complete session/refit groups before extracting windows. Keep trial groups inside their session. Do not copy overlapping chunks into differently named sessions. Index provenance and actual participant/refit identity require independent human review; IDs cannot prove independence. Reserve later refits and natural activity for final test. Cross-person claims additionally require participant-held-out splits; the current splitter makes no such claim.

Use the existing Phase 2A acquisition/annotation workflow and unchanged replay command. First verify actual device generation, frontal channels, units, sampling rate, clock/packet behavior, consent and fit. Collect separate calibration, deliberate doubles, natural blinks, triple negatives, talking/reading/motion, poor quality and reconnect/refit trials. Independently label actual gestures, not cue times or detector output. Resolve append-only supersession with `resolve_labels`; retain uncertainty/disagreement and report sensitivity rather than manufacturing truth.

The bounded feature whitelist is bilateral peak/noise ratio, bilateral agreement, duration, causal slopes and optional motion RMS. The caller supplies only a past window and a noise estimate fitted on a declared earlier calibration segment. No labels, cue timing, user identity or future normalization enters the vector. Candidate coverage must be evaluated against all gestures; classifier scores alone omit upstream misses.

Comparison ladder: attributed Phase 2A RAGTM candidate baseline and robust causal baseline; regularized logistic (at most 500 steps/10,000 rows); training-only PCA/two-cluster novelty; capped self-training. All use the unchanged downstream grammar. Novelty is not intent. Logistic scores are uncalibrated. Self-training requires an independently reviewed development-calibration evidence hash, both pseudo classes, at most half as many pseudo rows as labelled rows and at most 500 total. The function is a research primitive, not an automatic confidence certification; the caller must verify that calibration evidence belongs to that exact base model. No model-selection sweep, pseudo-labelling or real fitting was performed.

Freeze a small candidate grid, split/data hashes, matcher and calibration rule before fitting. `choose_development` minimizes false activations per armed hour subject to explicit recall/latency/availability constraints; defaults .95/.75s/.95 are exploratory pilot constraints, not the .99 aspiration. Select on identical development sessions only. Claim `FinalTestLock` once, before evaluating the selected model on final sessions. A new model needs new untouched final data. `save_deployment` writes exclusive JSON, never pickle; it requires real audit, development selection, grammar/channel contracts and includes baseline rollback. Its arguments remain a caller-reviewed provenance boundary, not a security attestation. Do not deploy artifacts directly from a synthetic fixture.

Failure taxonomy and next collection action:

| Failure | Next evidence |
|---|---|
| Natural/deliberate morphology overlap | Longer independently labelled natural activity, report irreducible ambiguity |
| Missed upstream candidate | Raw frontal window and candidate coverage |
| Motion/contact novelty dominates | Paired IMU/contact strata and later refit |
| Double/triple prefix confusion | Actual closure timestamps; never emit and retract a double |
| Cooldown/quality suppression | All-opportunity recall plus armed/elapsed exposure |
| Timing/reconnect drift | Source epoch and packet-loss replay; no stale sequence discharge |

Triple/amplitude experiments and online adaptation remain disabled. No live Muse path or trained accuracy is claimed.
