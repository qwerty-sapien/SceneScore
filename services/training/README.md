# Local Muse training service

Start explicitly from the repository root. Importing this package opens no
network listener, discovers no streams and starts no recording.

```sh
SCENESCORE_TRAINING_TOKEN=YOUR_RANDOM_STARTUP_TOKEN PYTHONPATH=.:src .venv/bin/python -m services.training --port 8767 --seconds 600 --data-root private_data/02A/training-web --web-root artifacts/training-dist --origin http://127.0.0.1:8767
```

The parent launcher supplies a random token and isolated optional pylsl runtime;
this package installs nothing. Omit the token to generate one and print the local
fragment URL. Startup authorization lasts 600 seconds. Authenticated activity
renews the session token for 600 seconds; process lifetime is bounded to 3600 seconds.
The listener binds 127.0.0.1 only. Each API request uses Bearer authentication and
exact Host validation. POST additionally requires an allowlisted exact Origin;
GET permits an absent same-origin browser Origin header but rejects mismatched
Origin and cross-site Fetch Metadata. Requests are bounded to 16 KiB,120/10 seconds,
4 concurrent handlers and 3 second socket I/O. Responses/export are bounded to 32 MiB.
Static access stays within the selected web root; dot paths, hidden targets and
outside symlinks are rejected. No cookies, uploads or public raw endpoints exist.

`GET /v1/diagnostics` provides timestamped connection evidence and raw-signal
summaries, with no raw sample arrays. `POST /v1/diagnostics/monitor {enabled:true}`
starts metadata discovery every ten seconds while the browser polls; disabling it
or losing diagnostic polls for five seconds stops the worker. `/diagnostics/check`
requests an immediate check. Its optional `request_bluetooth_permission:true`
flag is sent only by the explicit Enable Bluetooth check button. Discovery never
selects an inlet, pairs the headset or records data.

The launcher compiles `tools/muse_bluetooth.swift` into an ignored local helper
with its Bluetooth usage description. It only observes FE8D service advertising
and system-connected peripherals. Each helper process is bounded, its exact
identity retained, then reaped; shutdown terminates an active helper and joins
the diagnostic thread. Streaming disables active BLE scans while retaining the
system-connection query. The metadata monitor serializes bounded LSL discovery
without putting it in the acquisition lock or audio path. Invalid EEG outlets
remain visible as descriptor failures; non-EEG outlets are ignored.

Checks separately report permission/power, device observations, LSL metadata,
selected inlet, sample receipt age and recent continuity/rate/variation. Stale
hardware observations expire after twenty seconds. Freshness is a diagnostic
0.5-second batch-age check; source timeout stays two seconds and rate mismatch
uses the existing 2% recording criterion. Neither varying data nor BLE discovery
certifies electrode contact or a physical Muse identity. `.env`'s MUSE_TRANSPORT,
MUSE_BOARD_ID and MUSE_UNITS are unused by this LSL trainer.

Endpoints match `docs/requests/muse-training-api.md`. Source connection and
recording have separate consent actions. Real discovery opens a bounded LSL
inlet to inspect `info()`'s full descriptor, then closes it. Selection is by
unique discovered source ID. Labels must identify AF7/AF8 or FP1/FP2 in stable
left/right order. Equivalent microvolt spellings are normalized to canonical
uV without changing numeric samples; original descriptors are saved. Unknown
units are errors. Original additional channels and all raw timestamps are kept.
A real preview has no hardware-verification claim. A real recording requires
`metadata_confirmed:true` at `/record/start` plus timestamp-rate consistency.
Canonical Recorder `hardware_verified` then means the explicit operator
attestation, as its `operator_verified` manifest indicates; it does not mean
measured contact quality, physical device timing, or clinical verification.

Rehearsal is only `source_id:synthetic`, clearly labelled. It independently repeats
this 12 second waveform: double pulses at 3.0/3.3 seconds, a single at 7.0 seconds,
triple at 9.0/9.3/9.6 seconds, and quiet intervals elsewhere. B input never drives
samples. A B-held interval and guided cue are coarse intent markers only;
browser time, host receipt and latest source anchor remain separate. Mapping
uncertainty is null because no browser/device clock calibration was measured.
Correct actual device intervals after stopping and leave uncertain examples
uncertain. Reviews are append-only and neutral about reviewer identity. No
keyboard/cue timing becomes a feature or automatic truth label.

Acquisition batches 32..128 samples, splitting at actual source gaps. A recording
stops at its requested 10..600 second duration or before its 31 MiB raw-data limit.
There is no interpolation or raw decimation. The preview alone decimates to 2048
points and exposes gap timestamps. Source fault, timestamp/clock reset, explicit
disconnect,5 seconds without browser status/trace polling, and shutdown stop the
source and close recording. Pending B intervals and future cue intervals close
at the last recorded source timestamp. Recorded/session counts are recovered
from canonical raw chunks after an interrupted process. The optional source
worker and HTTP handlers are joined on shutdown; no detached service starts.

Closed raw reads validate the exact canonical kind schema plus the unchanged
semantic/continuity rules. A two-entry bounded cache is keyed by SHA-256 of every
persisted manifest/consent/chunk byte and path; modifications invalidate it.
This avoids repeatedly evaluating all unrelated schema union alternatives.
Review markers/annotations are read independently of this raw cache.

`/train` assembles full-rate, epoch-continuous two-second preceding windows from
reviewed train/development sessions. Final-test raw data is excluded before
loading. The model module enforces fit partition, mode/refit, overlap and minimum
example gates. Uncertain review IDs remain visible in the report. Fitting and
trace prediction execute outside the acquisition lock; publication checks the
review revision. Prediction additionally checks source mode, ordered channel
units and rate, rejects gaps/stale connection/model state, and has no musical
control authority. Review changes or exact session deletion invalidate the local
model file. No successful fixture fit implies real blink accuracy.

Focused tests use temporary source threads, loopback ports, raw stores and
explicitly synthetic examples. They cover HTTP consent/authentication, actual
canonical roundtrip, markers/autorepeat, review/train/prediction invalidation,
raw tampering, split gates, source fault/subscriber timeout, pending-connect
cancellation, persistence-failure teardown, descriptor/unit ambiguity, duplicate
source IDs and interrupted recovery. Every test-owned thread/server is closed.

```sh
PYTHONPATH=.:src .venv/bin/python -m pytest -q services/training/tests
.venv/bin/python -m ruff check services/training
```

Loopback tests require permission to bind temporary local sockets. No actual
headset connection or real training was performed by these tests.
