# Phase 2E → Phase 3 gate

Current result: **software implementation delivered; product NOT_READY**. Phase 3A follows the prompt's honest no-data branch. The formal Phase 3B exit gate is **NOT PASSED**: human plan approval and an approved modulation/export run are missing, and observed software AV timing exceeds the proposed target. No Phase 4 work is authorized or started.

## Actual evidence

- Root checks: 257 Python tests, 65 shared TypeScript tests, audio tests, Ruff, typecheck and production build. Final command log: `checks.log`. Audio test count increased from 14 to 16 for preparation rollback and full-run export enforcement.
- Immutable input check: 19 supplied hashes and planning copies pass. Frozen contract 0.1 and dependency locks unchanged. RAGTM remains nested source and was not modified.
- 2E: native browser audio executor, hash-verified scene bundles, conservative mixer, source labels, exact approval, keyboard/labelled synthetic control path, bounded queue/epochs, local draft audition. Earlier handoff `handoffs/02E.md` remains historical evidence.
- 3A: 12 fixture tests; training-only research primitives, grouped split audit, independent-label resolution, locked matching/final-test claim and safe artifact gate. Actual private data audit is `INSUFFICIENT_REAL_DATA`; no deployable model trained, no real accuracy claimed. See `reports/03A/MODEL_CARD.md`.
- 3B: one-command `make demo` exercised on 127.0.0.1:8765. Chrome 152 completed 30 seconds offline with 308 scheduled events and no approval. `artifacts/phase3/performance/browser.json` records actual browser provenance. The first browser wait hit its 30-second harness timeout just before the 30-second score finished; the subsequent state read confirmed natural completion at exactly 30 seconds.
- Actual stereo mix and piano/bass/brush/Foley stems: 48 kHz, 1,440,000 frames each, 30 seconds, no clipped samples. Independent PCM stem-sum maximum error 2 LSB (4-LSB rounding bound). Mix float peak 0.0186006, RMS 0.00284761. `artifacts/phase3/performance/independent-audio-check.json` and the browser export record contain measurements.
- Actual ffmpeg mux: `artifacts/phase3/performance/scenescore-DRAFT.mp4`; matched video hash, zero source timestamp offset and duration verified. Video stream copied, audio AAC-transcoded; lossless WAVs retained. This is **DRAFT_NOT_APPROVED**, with `approval:null`, not an approved performance.
- Browser fault checks: unavailable video and changed bundle bytes fail visibly; restoring assets recovers; approved playback remains disabled. Offline playback requires assets already loaded; no claim of offline first installation. Shared tests cover provider timeout, invalid IDs/JSON, replay loss/reconnect, quality and duplicates.

## Gates still open

Latest last-200-frame software offset: p95 absolute **137.33 ms**, max **139.67 ms**, against proposed 50 ms. Source video is 8 fps. This measures browser frame timestamps relative to the audio clock, not microphone/display onset. No physical output latency, Safari parity or live headset path was measured. Do not hide this failure or claim sub-frame precision.

Automatic approval review rejected the automated identity clicking `Approve exact plan` and `Play approved`. A human approval request remains unanswered. No alternate tool was used to bypass that boundary. The real approved modulation/export path remains NOT_RUN; synthetic unit tests are not human approval. Human musical/visual audition is AUDITION_PENDING.

Muse generation/channels/units/rate/fit/permissions, independent real recordings and clock bridge remain unverified. No configured API key/model was used; manual plans and local playback remain usable. Broader composition selection, imported plan diff UI, numeric mapping editor and automatic looping remain outside this delivered vertical slice and must be completed or explicitly cut before release. The separate Kinetic Jazz ZIP remains unavailable; the supplied SceneScore pack remains immutable.

The requested model evaluation follows this implementation gate and cannot turn these missing facts into passing evidence. Its frozen sample and report are in `reports/media-evaluation/`. Teardown and final revision are recorded in `handoffs/03B.md`.

Evaluation completed: requested GPT-5.6-Sol xhigh coordinator plus six fresh judge contexts reviewed 4/17 current deliverables. All selected hashes, 283 indexed support hashes and four decodes passed. One supporting-document defect remains: the sparse Velvet Orbit lead sheet incorrectly calls it straight rag. The frozen source artifacts were preserved; the finding is recorded for a versioned correction. RS=1, PC=1, PF=0 apply only to the small technical/symbolic packet experiment, with substantive N=3 and duplicate-control N=6 separated. No audio-perception tool was available; human audition, continuous motion and physical AV gates remain open. See the full REVIEW and raw trials; this review does not pass Phase 3B.
