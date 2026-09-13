# Muse vertical execution gate — 2026-09-13

Status: **PIPELINE_TESTED_ONLY**. The local software vertical is implemented and demonstrated using synthetic raw EEG. The user approved the reviewed Vercel payload; it is published and its browser simulator verified. A worn-headset demonstration, real detector training/evaluation and physical latency measurements remain incomplete. This is not SUPERVISED_DEMO_READY or a Phase 3B/4 pass.

Authority and immutable-input distinctions are recorded in [ADR 0011](../../docs/decisions/0011-muse-vertical.md). The user requested initiation of the complete vertical in parallel, with human participation reserved for blink training. START_HERE and nodes 00–07 supplied execution reference material. Three separate worktrees handled acquisition/training readiness, runtime/evaluation and browser/companion work; the integrator mounted and tested the music path. Concurrent Blender/music work was preserved.

## Delivered path

Local raw samples → unchanged causal baseline and double-only closure → semantic loopback companion → measured device/audio clock mapping → canonical ControlAction with scene-derived direction → the common audio submission path → scheduled acknowledgement → pivot and actual tonic arrival. Keyboard and simulation use that same submission path. Singles/triples, warmup, poor quality, gaps, reconnects, stale clocks, missing boundaries and disarming have explicit rejection behavior.

The browser offers an explicit unapproved conducting demo, simulator, companion status, source/arming controls and delayed local feedback notes. Demonstrations retain `approval:null`; automated execution is not human approval. The collection CLI records only after actual local consent and verified metadata. Feedback notes are not blink truth and do not start raw recording. Raw EEG remains local. The optional LSL route validates exact metadata and a train-derived numeric quality profile; no actual LSL connection was made.

Audio preparation is bounded and precomputed before acceptance. Pitched buffer cache identity now reflects synthesis parameters, reducing the tested bundle's prepared cache to about 62.53 MB. Following tonic arrival, future transition preparation yields in small cooperative slices; the measured maximum slice was 4.1 ms. Cancellation prevents obsolete preparation after pause, seek, reset or plan replacement. No music planning or external inference runs before the acknowledgement on the acceptance path.

## Exact browser evidence

[Final browser run](browser-e2e-final.json) loaded the staged build's `assets/index-z0EOXwAy.js` at loopback port 8771. One synthetic closed double produced one executed action, C → D, with pivot at scene 25 s and tonic arrival at 25.625 s. The scene's positive signed motion supplied +2 semitones. Gain, articulation and expression were unchanged; approval remained null.

| Interval / gate | Observed value | Result and scope |
|---|---:|---|
| Algorithmic final-candidate end → grammar decision | 503.90625 ms | One synthetic observation; closure floor preserved |
| Mapped decision request → browser audio receipt | 9.64265 ms | **FAIL** against 5 ms target; no p95 or physical claim |
| Accepted receipt → scheduled acknowledgement onset | 10 ms | Scheduled AudioContext time; acoustic onset unmeasured |
| Receipt → tonic arrival | 965.33333 ms | Deliberate musical wait, separate from dispatch |
| Host dispatch → browser receipt | null | No independently established direct measurement |
| Physical blink / speaker / Bluetooth transport latency | null | **NOT RUN** |

An earlier complete run changed C → B-flat and measured 13.95071 ms mapped receipt delay. A later valid event near the end was suppressed for lack of a feasible boundary. [Earlier evidence](browser-e2e.json) includes a real OfflineAudioContext render: 30 seconds, 48 kHz, stereo, peak 0.01882511, RMS 0.00285648, zero clipped samples. This is synthesized score PCM, not a microphone recording or human audition of the live acknowledgement. Video/audio software drift samples are retained without promoting them to physical synchronization measurements.

Real-DOM checks showed that selecting Live without a verified real stream does not assert LIVE_MUSE; cue feedback was disabled during the cue and enabled after the delay; independent review remained pending; no labels or EEG recording were generated. Test notes were deleted. [Screenshot](browser-local.png) records the local surface; it is not new production-scene evidence.

## Verification actually run

Counts below overlap; do not add them. Broad runs preceded the last clock/quality refinements, which received focused downstream checks and the final browser run.

| Command / check | Outcome | Evidence |
|---|---|---|
| `PYTHONPATH=.:src .venv/bin/python -m pytest -q` | 517 passed, two upstream deprecation warnings | [root-pytest.log](root-pytest.log) |
| `npm run test:contracts` | 70 passed | [contracts-ts.log](contracts-ts.log) |
| `PYTHONPATH=.:src .venv/bin/python -m scenescore.cli test-contracts` | Passed | Tool execution in task |
| `PYTHONPATH=.:src .venv/bin/python -m pytest -q services/bridge/tests` | Final 10 passed | [bridge-tests.log](bridge-tests.log) |
| `node --import tsx --test apps/web/src/muse/tests/state.test.ts packages/audio/tests/muse-control.test.ts` | Final 7 passed | [final-ui-control-tests.log](final-ui-control-tests.log) |
| Audio tests plus Muse dispatch tests | 34 passed after cooperative preparation repair | Tool execution and scoped handoffs |
| Runtime/quality Python subset | 42 passed after quality integration | Tool execution and scoped handoffs |
| `npm run typecheck` | Passed | [typecheck.log](typecheck.log) |
| `npm run build` | Passed; 214 modules | [build.log](build.log) |
| `ruff check modules/muse services/bridge tools/muse_demo.py` | Passed | Tool execution |
| `git diff --check` | Passed | Tool execution |
| `make muse-readiness` | INSUFFICIENT_REAL_DATA, zero real models | [readiness.json](detector/readiness.json) |
| Quality-profile CLI without a frozen index | Expected failure, exit 2, no output artifact | Tool execution |
| Bounded launcher on port 8781 for 10 s | Both children exited; ports cleared | [teardown.json](teardown.json) |

Root `make test` now includes companion HTTP tests and Muse UI tests in addition to existing checks. The full combined Make target was not rerun after that command-list-only edit. Tests use synthetic/fixture data; there is no empirical detector accuracy claim.

The five RAGTM lineage hashes matched and the 20 baseline tests, including numerical Node oracle parity, passed. The two pack interface copies are byte-identical. The immutable pack reference checker passes its own 14 grammar and six seam examples. The actual repository adapter agrees with 11/14 original grammar examples: P2, N3 and N8 expose onset-gap versus end-to-next-onset semantics. All 14 versioned repository-semantic cases pass. [Grammar audit](../../modules/muse/evaluation/grammar-audit-v1.json) preserves those failures explicitly; no immutable example or default detector threshold was changed. Frozen schemas and dependency locks have no diff.

## Pending evidence and publication

At the recorded diagnostic, pylsl, bleak, muselsl and brainflow were absent from the project environment. There were zero eligible private session manifests. Headset generation, firmware, channels, units, measured rate, fit and Bluetooth permissions remain unverified. These are current task observations, not permanent host facts. No runtime substitute or global configuration was created.

Training needs actual participant consent, verified Muse transport, separate refits with independent labels and frozen train/development/final-test assignments. The CLI audits data and can calibrate numeric signal validity from training sessions; it does not silently train/promote a learned classifier. Recall, false activations, confidence intervals and real latency remain null. The baseline rollback remains available. Contact impedance is not measured by the numeric quality profile.

The reviewed Vercel payload contains 14 static files totaling 25,839,229 bytes: browser code and synthetic scene/music assets, with no raw EEG, models or credentials. [Deployment manifest](deployment-manifest.json) binds exact file and source hashes. [Final integrity check](final-integrity.json) confirms all payload bytes unchanged; concurrent music work subsequently changed `packages/audio/model.ts`, so the staged build is a frozen tested snapshot, not a claim about later working-tree code.

**Publication complete after explicit approval.** Automatic approval review initially rejected the upload for lack of authorization for the exact payload/destination. The user's subsequent `approve` reply resolved that requirement. The unchanged 14-file payload was verified against the manifest, deployed, and inspected as READY/production. Live URL: https://scenescore-muse-vertical.vercel.app. See [deployment evidence](deployment.json).

Remote browser verification loaded the site, checked five representative served assets against their exact SHA-256 hashes, played the matched 30-second video, and executed one semantic simulation changing C to B-flat at scene 18.125 s. It retained SYNTHETIC_TEST and approval:null. An immediate first-frame simulation was suppressed as stationary; the successful request followed elapsed scene motion. [Remote run](browser-vercel.json). This does not rerun the raw EEG detector or establish hardware behavior. HTTPS-to-loopback companion access remains **NOT RUN**. All deployment CLI sessions exited; playback stopped and the browser page closed. The published site is intentionally retained.

The 5 ms value comes from the supplied [interface contract](../../muse_blink_modulation_vercel_dag/INTERFACE_CONTRACT.md), not a separate user instruction or an empirically justified perception threshold. The pack specifies the number but supplies no study or derivation. It is treated as an engineering budget to keep software handoff overhead small; exceeding it alone does not demonstrate a perceptible delay. The contract separately sets a 300 ms scheduled-acknowledgement budget and discloses grammar closure and musical waiting. No threshold was silently changed to turn the observed 9.64 ms into a pass.

All task-owned persistent jobs have exited and the browser page is closed; see [teardown](teardown.json). Worktrees retain reviewable source changes and have no running workers or services. No commit or merge of unrelated work was performed.
