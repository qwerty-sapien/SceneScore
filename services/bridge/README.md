# Local Muse semantic companion

The companion runs acquisition and the existing causal detector on the control host.
Its HTTP response contains semantic candidates, closed gestures and gate diagnostics.
It never serves raw samples, recordings, filesystem paths or arbitrary commands. It
never records EEG. The deployed Vite site still loads and simulates without it.

Run from the repository root with the existing environment:

```sh
PYTHONPATH=src:. .venv/bin/python -m services.bridge --source synthetic --seconds 600 --origin http://127.0.0.1:5173
```

It prints a fresh ephemeral token and binds **only 127.0.0.1:8766**. Paste that token into
"Local companion & detector" in the Muse panel. Select SYNTHETIC_TEST, wait for warmup,
then arm the detector. A pair of synthetic frontal waveforms occurs every eight seconds;
the same `CausalBaseline.consume` and closure grammar used for acquisition produce the
semantic event. This is a software fixture, not a participant or hardware measurement.
The first second after connection/disarm is a new warmup. Start the music demo before
conducting; two same-source clock probes must estimate the device-to-audio rate before
dispatch becomes eligible. The panel cannot create or approve a musical plan.

For a deployed page add its exact HTTPS origin with `--origin https://YOUR-DEPLOYMENT`.
Origins have no trailing slash or path. Public binding is unsupported. Browser policies
may still require permission for loopback/private-network access or prevent HTTPS-to-HTTP
loopback access; the panel reports connection failure and preserves offline fallback.
Tokens remain in memory, never browser localStorage. The browser origin and bearer token
must both match, and each session is origin-bound and expires after ten minutes. A new
handshake disarms and resets warmup. A lost event subscriber disarms within 1.2 seconds.
The process lifetime is bounded by `--seconds` (maximum 3600).

Local raw-session replay:

```sh
PYTHONPATH=src:. .venv/bin/python -m services.bridge --source replay --replay-session /ABSOLUTE/LOCAL/SESSION --seconds 600 --origin http://127.0.0.1:5173
```

The raw store is read lazily without modifying its bytes. Real-device recordings are
visibly REAL_REPLAY; synthetic recordings remain SYNTHETIC_TEST. Provenance of derived
records includes the persisted manifest hash. Replay is paced on original timestamps.
Playback schedule clock anchors are explicit and separate from the recording's original
physical capture clock. Coarse source chunks can still add processing/transfer latency;
that latency is reported separately. The stream stops at EOF and disarms.

Optional exact-ID LSL acquisition (in memory, no recording):

```sh
PYTHONPATH=src:. .venv/bin/python -m services.bridge --source lsl --metadata /ABSOLUTE/VERIFIED/METADATA.json --lsl-source-id EXACT_ID --live-consent /ABSOLUTE/LOCAL/CONSENT.json --quality-profile /ABSOLUTE/CALIBRATED/quality-profile.json --seconds 600 --origin http://127.0.0.1:5173
```

The local consent file must include `live_processing:true`, `raw_recording:false` and
`participant_statement` in the participant's own words. This is separate from the
collection/retention consent needed by the recording tools. The optional existing pylsl
runtime must be available. The adapter resolves exactly one source and validates its rate,
channel order and units against canonical acquisition metadata before reading it. It
closes the inlet on exit. No daemon, Bluetooth discovery, dependency installation or
recording starts implicitly.

`--quality-profile` loads at most 65536 bytes of a local calibrated profile. The runtime's
`QualityGate` validates its exact hardware/channel/unit/rate/acquisition configuration
binding, digest and training-session provenance before any optional LSL acquisition.
Synthetic profiles cannot certify real streams. The gate applies causal calibrated
amplitude, variance, flatline, dropout and receipt-staleness checks to a copy's quality
field. Raw values and timestamps remain unchanged. These are **numeric signal checks,
not measured contact impedance**, health indicators or detection-accuracy evidence.

An absent profile remains `calibrated_quality_profile_missing`; an invalid/ineligible
profile fails startup. There is no unchecked good-quality flag. Once an eligible real
profile is generated using `modules.muse.runtime.quality.calibrate_profile` and the
audited training CLI (`python -m modules.muse.training --index /LOCAL/FROZEN-INDEX.json --quality-profile-out /LOCAL/quality-profile.json`), this same adapter can warm up and arm without another code change.
See `modules/muse/runtime/QUALITY.md`. The panel renders LIVE_MUSE only when the actual
verified real stream is connected, passes its calibrated checks, has warmed up and is
explicitly armed. No participant collection or live validation was performed here.

The adapter fetches the complete stream descriptor with `inlet.info`, since resolution
provides only summary metadata. Source timestamps remain in their original epoch.
`LSLClock` uses liblsl's documented extended time correction uncertainty and a measured
LSL-local-clock/Python-monotonic midpoint; observed offset changes add uncertainty.
Clock resets terminate that stream and require a new connection. Failure to obtain a
valid clock never falls back to an assumed zero offset. The extended correction is
[documented by liblsl](https://labstreaminglayer.readthedocs.io/projects/liblsl/ref/freefuncs.html).

Protocol: POST `/v1/session` authenticates the startup token and returns a short-lived
session token; authenticated GET `/v1/status`, GET `/v1/events?cursor=N` and POST
`/v1/clock`, `/v1/arm`, `/v1/disarm` are the entire API. POST bodies must be `{}` and at
most 2048 bytes. Event subscriptions wait at most 400 ms and return immediately on an
event. At most eight concurrent HTTP handlers and four sessions exist; the event ring has
128 entries. Overflow clears state and requires re-arm. Tokens are omitted from access
logs; all responses disable caching. Loopback Host checks and exact CORS origins apply
to preflight and actual requests. No unauthenticated status endpoint exists.

Clock probes preserve device and host epochs. Browser audio RTT midpoint forms each
anchor. At least two matching anchors, separated by one second or more, estimate the
rate; epoch, source, configuration and connection changes invalidate them. Anchors are
bounded to 30 seconds/16 entries; gross rates outside 0.995–1.005 are rejected. Current
and previous anchor uncertainties propagate across a 2.5-second validity period, and
uncertainty above the common 20-ms bound prevents dispatch. Probes refresh every two
seconds. Synthetic/replay anchors describe the explicit local playback schedule and
include the clock-read bracket; they do not measure original physical capture timing.
LSL anchors carry its native measured uncertainty and observed correction drift. Missing
context, rate warmup, stale mapping and epoch changes suppress controls visibly. The
browser's current motion context supplies sign at the mapped request time; neither the
detector nor companion chooses direction. Physical capture/output latency remains unmeasured.

Validation:

```sh
PYTHONPATH=src:. .venv/bin/python -m pytest services/bridge/tests -q
node --import tsx --test apps/web/src/muse/tests/state.test.ts
npm run typecheck
```

Tests are software fixtures only. HTTP tests bind temporary loopback ports and assert
that all server/source threads stop. Stop the actual companion with Ctrl-C or its bounded
lifetime; do not leave it running after a bounded task.
