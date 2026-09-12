# Evaluation protocol — proposed gates, no measured results

Current evidence update: Phase 2E/3 actual results are in reports/phase3/GATE.md; the opening historical Phase 0 statements below no longer describe software coverage. Proposed thresholds remain unchanged. Actual draft audio and browser video timestamps were measured; human approval/listening, real Muse accuracy and physical output timing remain unverified. The 50-ms software AV target was not met. The requested model media review has its own frozen protocol in reports/media-evaluation/PROTOCOL.md; it cannot approve a human plan or infer auditory quality from schemas.

All seed thresholds remain proposed. Current release state is `NOT_READY`; not even pipeline tests have run. Each future report records code/config/schema/data/model hashes, commands, session splits, device assumptions, runtime, modes, raw counts, evidence paths and not-run checks. No 100% accuracy promise; no manufactured benchmarks or media evidence.

## Event-level blink protocol
Collect genuine independently annotated sessions, with participant consent and an annotation source independent of detector output (for example synchronized observation/video with its own consent). Prompt timing alone is not proof a gesture occurred. Review actual start/end/final-blink timing, ambiguity and disagreement. Preserve raw data; supervised calibration labels stay labels even if unlabelled data is also used. Synthetic events test software only.

Split by complete sessions and headset refits (and participant when claiming generalization), never random adjacent windows. Assign train/development/final-test membership before model comparison; fit preprocessing/thresholds/grammar using causal development data only. No final-test tuning, detector-generated truth or leakage from overlapping windows. Final test is immutable; a failed test can motivate a newly collected independent test set, not retrospective tuning. Keep the unchanged baseline for the same held-out replay when available.

Pre-register event matcher before final evaluation: one-to-one accepted decision to independently verified gesture, chronological matching to nearest eligible final-blink timestamp within a development-chosen fixed window; declare tie rule, count/label handling and numerical tolerance in the locked config. This window is not the latency target. Numerical matcher and grammar settings remain uncalibrated; do not evaluate release readiness until fixed. Duplicates/unmatched controls count as false activations; all unmatched verified gestures count as misses, including quality abstention and refractory/cooldown periods. Natural blinks and accidental clusters are explicit negatives; do not assume intent can always be separated.

Report TP/FN/FP, recall, precision (undefined when denominator zero), false activations per armed hour AND per elapsed monitored hour, negative-activity exposure, armed availability, abstention/refractory duration and all misses by cause. Report per-session/refit results and pooled counts with uncertainty. Confidence scores are not probabilities unless calibration is independently tested. Multi-count grammar incurs prefix ambiguity: wait for sequence closure; third blink prevents a double; declare closure delay and resulting latency. Default triple control is disabled.

## Proposed acceptance values from seeds
| Measure | Target / gate |
|---|---|
| Primary event recall | 0.99 aspiration |
| False activations/hour | ≤0.5 primary, ≤0.1 stretch aspiration |
| Supervised demo pilot | ≥100 verified held-out gestures across ≥2 held-out refit sessions; ≥60 minutes natural activity; observed recall ≥0.95; zero observed false activations; armed availability ≥0.95 |
| Final blink to decision p95 | ≤750 ms |
| Decision to visual confirmation p95 | ≤100 ms |
| Collision rendered offset p95 | ≤50 ms |
| Live A/V drift | goal ≤50 ms; report trajectory, maximum and p95 over stated duration |

Pilot counts permit only a supervised demo candidate, not primary statistical claims. One-sided 95% all-success recall lower bound is `0.05**(1/n)` under independent Bernoulli assumptions; zero-false-event upper rate is `-log(0.05)/hours` under stationary Poisson assumptions. At n=100 all successes the lower bound is about 0.9705; zero false events in 1 hour gives about 2.996/hour. Roughly 299 all-success independent opportunities and 6 zero-event hours would support 0.99 and 0.5/hour separately under those assumptions; session dependence/drift still require assessment. For nonzero failures report an appropriate interval and method. Report armed and elapsed exposure distinctly; disclose which denominator a claim uses.

## Scene/audio correctness and audition
Phase 1 software fixtures cover schema rejection, units, clocks, deduplication, seed determinism, loss/reconnect and control lane preservation. Blender tests use independently known sphere contact, positive-gap near miss, constant separation, and area scaling by s² with translation/rotation invariance. Verify evaluated meshes, pair identities, source/video hashes, duration and labelled visual frames; uncertainty and visual QA are separate.

Music tests cover bar/tick totals, exact groove lookup, pitch/velocity/register bounds, beat-second conversion, single swing application, pitched-only transposition, unpitched brush invariance, scene-time Foley, seeded events and stem alignment. Actual audio renders must be checked for non-silence, expected duration and clipping, with sample peak statistics. DOM/schema tests cannot establish sound. Human audition separately reviews phrasing, chord transitions, near-miss tension, object identity, brush approximation, balance, clicks, ending/loop quality and preserved expression; record reviewer/date/asset hash and `AUDITION_PENDING`, approved or changes requested.

## Timing and release evidence
Measure device-to-host, candidate/closure, final-blink-to-decision, websocket/UI confirmation, scheduler wait and physical/rendered output separately. Musical-boundary wait is intentional and must not be hidden in detector latency. Use fake clocks for scheduling logic; measured audio/video output or loopback/capture is required for output claims. State devices, browser, sample rate, duration, load, sample count and percentile method; no unsupported sub-frame precision at 30fps. Exercise pause/seek/loop/resume, audio suspension, duplicate/stale/late events, network/stream loss and failure of assets/API. Record task job cleanup.

Release statuses: `PIPELINE_TESTED_ONLY` requires software evidence; `REAL_DATA_EXPLORATORY` requires real sessions without demo gate; `SUPERVISED_DEMO_READY` requires pilot plus integration/audition gates; `TARGET_STATISTICALLY_SUPPORTED` additionally requires appropriate bounds and assumptions supporting the declared targets; `NOT_READY` applies to missing essential demo evidence or failed safety/correctness gates. A detector status never substitutes for product release evidence. The release owner audits every MUST in requirements.yaml; unmet gates remain visible.

## Phase 1 evidence update

The earlier opening status describes Phase 0. Software pipeline checks now exist, with actual commands/results in handoffs/01.md and reports/phase1/. Product remains NOT_READY; its software harness alone qualifies as PIPELINE_TESTED_ONLY. All empirical blink, render, listening, browser audio and live API checks remain NOT_RUN. Do not promote software conformance into those categories.
