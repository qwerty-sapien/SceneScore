# Muse training webpage — delivery gate

Status: **implemented and published; synthetic browser workflow passed**.
Real participant EEG collection and personal detector evaluation remain **NOT RUN**.

Published page: https://scenescore-muse-vertical.vercel.app/train/.
Use `Launch Blink Trainer.command` or `make muse-train` for the authenticated local
page. The hosted page needs browser Local network access permission to reach the
local service. Raw EEG, reviews and models are never part of the static deployment.

## Delivered

- Standalone React page with existing-source LSL discovery, frontal raw traces,
  explicit processing/recording consent and real-source metadata attestation.
- B down/up intent markers, ignored autorepeat/editable targets, blur release,
  hands-free cues, stopped-session trace review, reviewed/uncertain classes.
- Local causal two-second window classifier with train/development partition
  guards, final-test exclusion, live uncalibrated scores and no music authority.
- Exact local raw/model download, exact-session deletion and model invalidation
  after review changes or deletion. Independent raw clocks and gaps preserved.
- Bounded loopback service, source timeout/cleanup, interrupted-record recovery,
  exact-byte raw validation cache and isolated optional pylsl receiver runtime.

The supplied RAGTM source was inspected read-only for its existing LSL stream and
trace/capture flow. No game code or automatic upload behavior was imported.
The original music/Blender app was not rebuilt for this standalone page.

## Commands and results

- `PYTHONPATH=.:src .venv/bin/python -m pytest -q services/training/tests modules/muse/training/tests/test_web_model.py`:
  **34 passed in 2.51 seconds**, including temporary loopback lifecycle tests.
- `node --import tsx --test apps/training/tests/*.test.ts`: **10 passed**.
- `node_modules/.bin/tsc -p apps/training/tsconfig.json`: **passed**.
- `VITE_STUDIO_URL=https://scenescore-muse-vertical.vercel.app node_modules/.bin/vite build apps/training --base ./ --outDir ../../artifacts/training-dist --emptyOutDir`:
  **passed**, including final hosted-permission help.
- `.venv/bin/ruff check services/training tools/muse_training.py` and scoped model
  lint, plus `git diff --check`: **passed**.
- `tools/muse_training.py --seconds 20 --no-open --no-build`: startup/readiness and
  bounded exit **passed**; browser reached it after expiry. Repeated with 60
  seconds: automatic authentication, fragment scrubbing, no source/recording and
  bounded exit **passed**.
- Two Vercel production deploys and first deployment inspect succeeded. Final
  deployment returned **READY**; all three final training assets served HTTP 200
  and matched the reviewed SHA-256 values.
- Full repository `make test`: **NOT RUN**; unrelated concurrent music/Blender
  work remains outside this change's focused verification.

## Actual browser evidence

[browser-flow.json](browser-flow.json) records the synthetic-only run: 40 seconds,
10,242 samples, six B intervals plus one cue; three positive and three comparison
windows fitted; an uncertain review stayed excluded. Review changes removed the
old model. Live model scores appeared. Exported chunks exactly matched the stored
raw records, then both test sessions were deleted and the model invalidated.
A later 10-second capture used 32–40 sample chunks; B typing, repeat and blur
produced exactly one intended down/up pair. No test review is human approval.

The first browser run exposed repeated full-session validation and request
timeouts. Kind-specific canonical validation plus an exact-byte cache reduced
the profiled 40-second read from 2.26 seconds to 0.46 seconds initially / 0.035
seconds cached. The repeated browser fit completed in an observed 205 ms; this
is a single software observation, not a timing guarantee or device measurement.

Desktop and 390px mobile layouts were inspected; no horizontal overflow. Hosted
HTTPS-to-loopback authentication and synthetic traces passed after granting the
test origin Local network access. The first hosted request timed out while that
permission was unavailable; setup help now names the required action.

## Real-data limit and teardown

Native pylsl/NumPy import smoke passed in `artifacts/muse-training-runtime`, without
changing root dependency locks. Bounded metadata-only LSL discovery found **zero
advertised sources**. MuseLSL transmission itself is not installed by this task;
start the existing RAGTM/Muse LSL source and select it. No physical capture,
participant labels, held-out accuracy or music-control certification is claimed.
Double blinking is the default deliberate gesture; actual separability remains
to be measured against ordinary singles, triples, movement and keypress-only data.

[deployment.json](deployment.json), [source-manifest.json](source-manifest.json),
[deployment-manifest.json](deployment-manifest.json) and [lifecycle.json](lifecycle.json)
bind the delivery. All task-owned service/test processes exited; ports 8767/8768
have no listeners. The named temporary export copies were removed, and browser
test pages closed. The published static page is intentionally retained.
