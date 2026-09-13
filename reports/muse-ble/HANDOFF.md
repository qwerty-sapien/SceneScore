# Direct Muse BLE integration handoff

Software implementation is integrated. Real Muse-AD3C plain connection and
notification-subscription checkpoints PASS. The later explicit local recording
attempt is currently BLOCKED at discovery: fresh scans did not find Muse-AD3C.
There is no pending authorization prerequisite or extra launcher question.
This is not a claim of end-to-end live conducting readiness.

## Architecture and files

Locked Bleak 3.0.2 owns one asyncio loop/thread and at most one BLE client.
Pure classic protocol code decodes and assembles packets; a causal clock
estimator maintains an explicit receipt mapping. The local adapter creates
canonical frontal EEGChunks, passes QualityGate and the existing Companion/
CausalBaseline, and serves only semantic events and bounded diagnostics to the
studio Muse panel. The frozen 0.1 contract is unchanged.

Main files: `modules/muse/acquisition/{muse_protocol,ble_clock,ble}.py`,
`services/bridge/{ble_source,server}.py`, `apps/web/src/muse/` client/types/panel/
headset helpers, `tools/{muse_demo,muse_ble_diagnose}.py`, root dependency locks,
Makefile and Vite type declarations. Unit/HTTP/UI/hardware-opt-in tests accompany
these. `files.json` lists exact paths and observed hashes.

## Exact initialization

Bounded scan → session-scoped handle mapped to discovered BLEDevice → connect →
assert connected → verify FE8D and control/EEG characteristic membership →
subscribe control → `h` → `p21` → subscribe TP9, AF7, AF8, TP10 → `d` → require
a structurally valid complete frame → STREAMING. Short pauses and last-operation
diagnostics preserve stage attribution. The standard `k` keepalive is serialized
with writes. Athena 273e0013 rejects the profile; even cleanup sends no classic
halt to an unverified/rejected profile. Shutdown stops notifications, halts a
verified classic device if possible, disconnects and joins the loop thread.

## Packets, clocks and reconnect

Exactly 20 bytes: big-endian 16-bit packet counter followed by twelve packed
12-bit unsigned samples. Convert `(raw-2048)*125/256` to uV. Four channels must
match one packet index. Eight-frame/.25-second buffering bounds, explicit
eviction/drop counts, rollover and reset detection prevent cross-index mixing
or imputation. Canonical chunks retain only AF7/AF8; local sample indices start
at the first observed boundary, while source time keeps the unwrapped counter.

The causal bounded Theil–Sen/median clock fit uses last-sample source time and
earliest channel receipt. Reordered receipt anchors, residual jitter, drift and
age contribute uncertainty. Constant one-way BLE delay cannot be identified
from packet counters: the explicit uncalibrated 25 ms allowance is NOT a measured
physical upper bound and exceeds the unchanged 20 ms browser gate. Timing thus
still suppresses BLE musical dispatch. No trust-quality/timing override exists.

Unexpected disconnect invalidates epochs/probes, clears partial frames and
pending grammar and requires explicit rescan/reconnect. Each connection gets
fresh session/device/host identities. Malformed input/gaps disarm immediately;
valid recovery must warm up and be rearmed. Missing quality calibration allows
streaming but leaves quality unverified and arm disabled. Raw EEG stays in
memory; this companion has no recording or raw-response endpoint.

## Website and commands

`make muse-live` builds and launches the web service plus BLE companion without
an additional interactive question. It supplies the existing bridge startup
file automatically. Optional `QUALITY_PROFILE=...` supplies
an eligible calibration; `make muse-demo` remains synthetic. Authenticate with
the ephemeral companion token, choose LIVE_MUSE, scan, select Muse-AD3C and
connect. The panel distinguishes companion, GATT, EEG, quality, warmup and arm.
Keyboard/simulation remain available. See `docs/MUSE_BLE.md` for standalone CLI,
API bounds, origin handling, diagnostic commands and manual acceptance steps.

## Commands actually run and results

| Check | Result | Evidence |
|---|---|---|
| `UV_CACHE_DIR=/private/tmp/scenescore-ble-uv-cache uv add --no-sync 'bleak>=3.0.2,<4'` | PASS; 45 locked packages | `pyproject.toml`, `uv.lock` |
| `UV_CACHE_DIR=/private/tmp/scenescore-ble-uv-cache uv sync --locked` | PASS; environment synchronized, Bleak import/version 3.0.2 verified | command output in task; lock unchanged afterward |
| `PYTHONPATH=.:src .venv/bin/python -m pytest modules/muse -q` | PASS: 232; 2 explicit hardware skips | `muse-tests.log` |
| `PYTHONPATH=.:src .venv/bin/python -m pytest services/bridge/tests -q` | PASS final: 34 | `bridge-tests-final.log` |
| `node --import tsx --test apps/web/src/muse/tests/*.test.ts` | PASS: 15 | `frontend-tests.log` |
| `npm run typecheck` | PASS final; an intermediate concurrent training-test typing error was subsequently fixed by that task | `typecheck-final.log`; earlier `typecheck.log` |
| `npm run build` | PASS; existing >500 kB bundle warning | `build.log`, `launcher-check.log` |
| Ruff on BLE/adapter/launcher/browser-fixture owned files | PASS | `lint.log` |
| `make test` | Initial combined run FAIL: 1,113 passed, 2 skipped, 1 failure in concurrently edited Blender plan validation | `make-test.log` |
| Isolated rerun of `test_valid_supported_catch_compiles_all_measurable_conditions` after concurrent change | PASS; no BLE-task edit to that file; full suite not repeated | `concurrent-blender-recheck.log` |
| Source/launcher focused regression | PASS: 12 | `final-adapter-tests.log` |
| Real-browser SOFTWARE FIXTURE | PASS observed authentication, scan/select, expired scan rejection, rescan, streaming count and missing-profile/disarmed state; no real Bluetooth | `../../output/playwright/ble-streaming-fixture.md` |
| Synthetic launcher → SIGTERM → exact child groups absent | PASS | `launcher-check.json` |

The CLI Playwright wrapper could not resolve its package in the network sandbox;
browser inspection used the already installed Playwright tool. Initial sandboxed
HTTP tests could not bind sockets; reruns with loopback permission passed.
Those infrastructure failures are separate from software or hardware regressions.

## Actual Muse-AD3C hardware result

The first bounded scan found no advertisement. After the user confirmed that the
headset was on nearby, the retry found and connected to it. The actual service
and characteristic set matched the user-supplied classic profile; no Athena
marker was present.

| Actual command suffix | Result | Measured hold | Evidence |
|---|---|---|---|
| `--name Muse-AD3C --seconds 30` | PASS; clean disconnect | 30.0002 s | `hardware-plain-retry.log` |
| `--name Muse-AD3C --stage one-eeg --seconds 30` | PASS; control + one EEG subscription; clean disconnect | 30.0004 s | `hardware-one-eeg.log` |
| `--name Muse-AD3C --stage all-eeg --seconds 30` | PASS; control + four EEG subscriptions; clean disconnect | 30.0012 s | `hardware-all-eeg.log` |

Each command used `.venv/bin/python tools/muse_ble_diagnose.py`. These checks sent
no stream-start command and received zero notifications. They prove the measured
connection/subscription holds, not EEG decoding on this hardware.

Following the user's explicit instruction to record locally, the separate
diagnostic recording workflow was implemented and invoked. It uses the
production manager and canonical AF7/AF8 adapter, plus the existing local raw
Recorder on an owned thread with a bounded 128-chunk queue. Original values,
device/receipt times and gaps are preserved; no raw data enters HTTP or logs.
The Git-ignored destination must be a new directory under `private_data/`.
Replay validation and private file permissions are checked. Launching the
website still does not start a recording.

| Later hardware command | Result | Evidence |
|---|---|---|
| `--stage stream --seconds 60 --record private_data/muse-ble-20260913-capture-01` | FAIL at scan deadline; zero samples/files | `hardware-stream-recording-01.log` |
| Same command with destination `capture-02`, after scan deadline fix | BLOCKED: completed discovery found no Muse-AD3C; zero samples/files | `hardware-stream-recording-02.log` |
| Previously successful direct name scanner, `--stage plain --seconds 1` | BLOCKED: no Muse-AD3C advertisement during its 15-second scan | `hardware-plain-current.log` |

Bleak's discovery duration excludes native scanner startup/shutdown. The outer
deadline now allows two additional seconds instead of half a second, within
the unchanged browser request limit. A delayed native-start fixture verifies
this correction. The successful empty scan is current availability evidence;
it does not establish that the headset is off or that earlier holds failed.

`recording-regression-tests.log` records 36 passing manager/recording/launcher
tests, including exact synthetic replay, bounded-queue overflow, write-error
propagation, no-file creation without samples, and no redundant launcher prompt.
`recording-lint.log` passed. Full tests were not repeated after these isolated
CLI/scan changes. No real EEG recording or 60-second EEG streaming pass is
claimed. Quality calibration, physical timing and Windows hardware validation
also remain unverified.

## Concurrent work and teardown

Training app/service/model files were avoided. During this task the other
conversation expanded checkpoint changes into MusePanel, bridge.ts, types.ts,
server.py and the causal baseline. Further edits to those shared paths stopped
when that overlap was observed. Its additions are preserved. Only the BLE-owned
adapter was adjusted through the existing disarm seam to cancel pending arms and
clear prior checkpoint display on a fresh BLE session. See
`docs/requests/muse-ble/concurrent-training-followup.md`, `concurrent-overlap.json`
and the saved frontend `.concurrent.diff` files for later joint review.

Another task advanced the shared Git checkout while this work ran; the BLE task
did not make that combined commit. Do not attribute its entire diff to BLE.
Frozen inputs/contracts were not edited by this task.

All task-owned hardware processes completed and disconnected; all fixture/test
threads exited. Software fixture PID 61989, stalled CLI PID 61993, synthetic
launcher PID 69156 and child groups 69204/69205 are absent. Only this task's
browser tab was closed. Three BLE worktrees were removed after integration;
unrelated worktrees/jobs were preserved. No Docker container was started.
`teardown.json` records the exact verification.

For the explicit recording follow-up, PIDs 88784 and 89175 are verified absent;
all diagnostic/test exec sessions exited. Both BLE and recorder threads joined.
Neither proposed raw-session directory exists because no EEG frame arrived.
No new server or container was started. See `recording-teardown.json`.
