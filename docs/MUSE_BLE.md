# Direct Muse BLE through the local companion

The studio connects through `Bleak → classic Muse decoder → EEGChunk →
QualityGate → Companion → CausalBaseline → semantic loopback API → MusePanel`.
The browser receives device names, connection/gate summaries and semantic events.
It receives no EEG arrays, device addresses or recordings. No LSL, BrainFlow,
dongle, OS pairing or Web Bluetooth is required for this path.

## Run

```sh
uv sync --locked
make muse-live
```

`make muse-live` explicitly starts the local BLE workflow without an additional
question or paperwork. The launcher supplies the existing bridge CLI's local
startup record automatically. It does not record EEG. An existing local startup
file is still accepted for command compatibility:

```sh
make muse-live LIVE_CONSENT=/ABSOLUTE/LOCAL/consent.json
# Optional eligible calibrated quality profile:
make muse-live LIVE_CONSENT=/ABSOLUTE/LOCAL/consent.json QUALITY_PROFILE=/ABSOLUTE/LOCAL/quality-profile.json
```

The legacy startup JSON contains `live_processing:true`, `raw_recording:false`
and a nonempty `participant_statement`; the launcher creates it privately and
removes it on exit. `make muse-demo` preserves the explicitly synthetic demo. Prepared studio scene assets are still
required by the existing launcher; `make demo` prepares those separately.

The launcher builds the website, starts its loopback web service on port 8771
and the companion on 8766, and prints the companion's ephemeral token. Open the
printed URL, open the blink demo, choose LIVE_MUSE, authenticate with that token,
then **Scan for Muse → select Muse-AD3C → Connect headset**. Opening the page or
starting the bridge does not scan, connect or record. A standalone bridge:

```sh
PYTHONPATH=.:src .venv/bin/python -m services.bridge --source ble --seconds 600 \
  --live-consent /ABSOLUTE/LOCAL/consent.json --origin http://127.0.0.1:8765
```

Use `tools/muse_demo.py --source ble --port PORT --live-consent PATH` for another
web port. Its exact origin is passed to the bridge. Origin and bearer checks,
loopback binding, short-lived origin-bound sessions, body/handler/event bounds
and no-cache responses remain in force. Ctrl-C, SIGTERM and the lifetime budget
stop the launcher's exact child groups; companion shutdown joins its BLE thread.

## What connection means

The UI separates companion authentication, discovered headset, GATT connection,
valid EEG streaming, quality, warmup and detector arm state. All four classic
EEG characteristics must deliver valid same-index packets before hardware and
stream verification. `connected:true` means complete EEG frames have arrived.

Missing calibration allows streaming but keeps signal quality **unverified**
and arming disabled. Eligible calibration still goes through the existing
causal numerical quality checks. A good numeric profile is not contact impedance
or blink-accuracy evidence. Only AF7/AF8 enter the canonical conducting chunks
and quality binding; the four-channel packet assembler also checks TP9/TP10.

Frozen contract 0.1 requires real-device metadata to be hardware-verified.
Before any samples, the companion therefore holds an inert placeholder with
synthetic provenance and connected/hardware false. It generates no synthetic
EEG. The first verified complete hardware frame changes metadata to
`real_device`, `transport:bleak`, 256 Hz, uV and local-only storage before any
chunk reaches the quality gate or detector. Session/device/host IDs are fresh
for each connection; the acquisition configuration hash is deterministic.

## Initialization and faults

On a single dedicated asyncio loop: bounded scan → discovered BLEDevice object
connection → connected assertion → GATT verification → control notifications →
`h` → `p21` → TP9/AF7/AF8/TP10 notifications → `d` → bounded wait for a valid
four-channel frame → streaming. Short staged pauses retain the exact last
operation. The standard `k` keepalive is serialized with other writes. Only
control and EEG notifications are subscribed. Cleanup halts only a profile that
passed classic validation, stops notifications and disconnects.

The required service is FE8D; control is 273e0001 and EEG is 273e0003–0006,
using the full UUIDs in `muse_protocol.py`. Athena characteristic 273e0013
always rejects the profile; no classic commands are sent to it, even in cleanup.

Each EEG notification is exactly 20 bytes: big-endian 16-bit packet index then
twelve packed unsigned 12-bit readings. Pairs occupy three bytes; conversion is
`(reading - 2048) * 125 / 256` microvolts. Explicit synthetic boundary vectors
test this against the published layout. Frames never combine different indexes
and never impute a channel. Buffer/deadline limits evict incomplete frames and
charge twelve dropped samples per frame. Ordinary 16-bit rollover continues the
epoch; ambiguous resets require reconnect. Malformed input and gaps disarm and
clear pending gestures; structurally valid recovery must warm up and be rearmed.

Unexpected disconnect or source timeout invalidates clocks and partial frames,
disarms and reports the operation that failed. There is no automatic reconnect.
Use a fresh scan and explicit connection. Quality loss or headset absence does
not stop music or remove keyboard and synthetic fallback.

## Timing limitation

Logical device time is the unwrapped packet index × 12 samples / 256 Hz, with
per-sample offsets. A bounded causal robust fit relates the last sample of each
frame to the earliest notification receipt; assembly delay is not confused with
capture time. Reordered arrival anchors are excluded from fitting and add
uncertainty. Residual jitter, drift allowance and sample age remain visible.

Classic packets do not reveal constant one-way Bluetooth delay. The estimator
therefore retains an **uncalibrated 25 ms allowance**, explicitly not a measured
physical upper bound. This exceeds the unchanged **20 ms** browser mapping gate:
live musical dispatch remains suppressed even if a quality profile permits
detector arming. There is no UI/CLI override. Independent physical latency
measurement and a reviewed clock calibration design remain necessary before
claiming timing-qualified BLE conducting. Software tests do not resolve that
measurement limitation.

## API and diagnostics

After the existing `/v1/session` handshake, authenticated POSTs accept only:

| Endpoint | Body | Result |
|---|---|---|
| `/v1/muse/scan` | `{}` | Up to 64 `{id,name}` candidates and status |
| `/v1/muse/connect` | `{"device_id":"scan handle"}` | Status |
| `/v1/muse/disconnect` | `{}` | Status |

Handles are random, recent-scan/session scoped, expire, and map only to the
actual discovered BLEDevice. CoreBluetooth UUIDs are not stable selectors and
are not sent to the page. Only one scan/connect operation runs at a time.
Normal browser requests retain 3.5-second deadlines; scan uses 15 seconds,
connection 25 seconds and disconnect 8 seconds. Stage/last-error/last-operation,
connection and streaming durations, rates, sample/gap/malformed counts and last
packet age provide bounded diagnostics. Raw native errors, EEG and tokens are
never logged by handlers.

Lower-layer hardware regression (no stream-start commands, no recording):

```sh
.venv/bin/python tools/muse_ble_diagnose.py --name Muse-AD3C --seconds 30
# Isolate subscription layers, then test the production manager:
.venv/bin/python tools/muse_ble_diagnose.py --name Muse-AD3C --stage one-eeg --seconds 30
.venv/bin/python tools/muse_ble_diagnose.py --name Muse-AD3C --stage all-eeg --seconds 30
.venv/bin/python tools/muse_ble_diagnose.py --name Muse-AD3C --stage stream --seconds 60
# Separate explicit recording workflow, using a new local session folder:
.venv/bin/python tools/muse_ble_diagnose.py --name Muse-AD3C --stage stream --seconds 60 \
  --record private_data/my-muse-session
```

`--record` saves canonical AF7/AF8 samples in uV with original device/receipt
times and explicit gaps. A bounded writer queue keeps filesystem sync off the
Bluetooth loop; overflow or a write failure stops the diagnostic visibly.
Replay validation reports counts without printing EEG. Files use private
permissions under the Git-ignored `private_data/` folder. The HTTP companion
and MusePanel still have no raw recording endpoint.

For manual acceptance, power on the headset, unplug its charger, disconnect
other Muse apps, enable host Bluetooth and permit the Python host process to
use Bluetooth. No OS pairing is needed. Hold actual EEG streaming for at least
60 seconds and inspect counts, stage faults and gates. Windows uses the same
Bleak object abstraction; Windows hardware validation is separate.

The separately edited trainer is deliberately untouched. See
`docs/requests/muse-ble/concurrent-training-followup.md` before any later trainer
diff. Validation and hardware results for this run are in
`reports/muse-ble/HANDOFF.md`; commands here are instructions, not PASS evidence.

References: [Bleak 3 client API](https://bleak.readthedocs.io/en/latest/api/client.html),
[MuseLSL wire protocol and commands](https://github.com/alexandrebarachant/muse-lsl/blob/master/muselsl/muse.py),
[Muse characteristic constants](https://github.com/alexandrebarachant/muse-lsl/blob/master/muselsl/constants.py).
