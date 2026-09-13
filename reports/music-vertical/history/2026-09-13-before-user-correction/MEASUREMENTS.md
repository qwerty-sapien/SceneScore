# Node 07 — exact music vertical measurements

The software pipeline was exercised through a full 30-second browser take and draft exports. Release is **NOT_READY**: AV timing failed, human audition is **AUDITION_PENDING**, and approval remains **null**. Task teardown is incomplete because closure of the owned browser tab cannot be confirmed after both browser-control tools failed. The demo server has exited.

Machine-readable measurements, exact commands, load, defects and check dispositions are in [MEASUREMENTS.json](MEASUREMENTS.json). [ASSET-HASHES.json](ASSET-HASHES.json) binds 65 candidate, media, preparation-source and loaded browser-build files. [TEARDOWN.json](TEARDOWN.json) records resource identities and the unresolved tab.

## Exact candidate and observed behavior

The assessed candidate is `artifacts/music-vertical/candidate-v1/candidate.json`, SHA-256 `d9ce7fd69f7aa9d47b6db169a6c779fa82a8795fce299858b614f358b797a0c9`. It uses the unchanged legacy synthetic projectile/tower animation, 30 seconds at 8 fps, seed 42; original Tilted Blue version 1 at 96 BPM with an authored ending; and `brush_swing_light_v1` version 1. It does not substitute the concurrently developed physical Blender scene.

The plan SHA is `fd090867ab61fde774879f23ae56ea388e88db072521d9dd9f5a3bc5b489808d`. The source video SHA is `07a65b59bda1afc07fc1397f72232f2855df595b2cfe3948ea602d517890a04a`. Full scene, composition, controls, holds, configuration and preparation-code hashes are in the JSON report and candidate manifest. Two actual preparations produced identical candidate, event, plan, control, hold and MIDI bytes; see [DETERMINISM.json](DETERMINISM.json).

The actual scene supports approach/separation articulation and dynamics, contact-related source-slot articulation and separate Foley, and two one-beat third-withholding intervals at 12.625–13.25 and 17.875–18.5 seconds. It has no canonical collision or asymmetric rebound. Those types have analytic fixture coverage only. The actual mapped score adds zero ornament notes; some ornament-density, tension and register intentions remain sidecar data. Fixture rebound may quantize to a source slot up to 0.75 seconds after contact. These limits prevent a claim that every pack behavior is fully demonstrated by this scene.

## Browser take and timing

The retained two-control run is [browser-two-control-take.json](browser-two-control-take.json), captured 2026-09-12 at 19:40:36 UTC. Chrome 152 used a 48 kHz AudioContext. The loaded script was `index-BBrePzdL.js`; its exact bytes and CSS are preserved in `browser-build/`. Browser user-agent text is not evidence of the host's architecture.

The input was automated activation of the keyboard UI path, using a bounded 20 ms timer. No EEG detector or human performer supplied these controls. The repository's combined tests ran concurrently with playback, and browser instrumentation was active. CPU utilization was not measured. The first full take is retained separately because its second externally dispatched request arrived after the end; it was not silently replaced or discarded.

| Observation | Value | Disposition |
|---|---|---|
| First request / arrival | −2 at 19.0067 s / B-flat at 22.5 s | Executed |
| Second request / arrival | +2 at 24.5053 s / C at 27.5 s | Executed |
| Request to receipt, t4 − t3 | 0 ms, both timestamp records | AudioContext-domain observation; not zero wall-clock latency |
| Receipt to scheduled acknowledgement, t5 − t4 | 20 ms, both records | Passes 300 ms for n=2 scheduled onsets; acoustic output unmeasured |
| Acknowledgement to arrival, t6 − t5 | 3473.33 ms and 2974.67 ms | Intentional musical wait, reported separately |
| Absolute video/audio software offset | Last 200 samples; nearest-rank p95 144.33 ms; max 147.67 ms | **FAILED** 50 ms target |
| Difference from previous p95 137.33 ms | About +7.00 ms | Regression retained as a finding |
| Cache | 1,021 buffers; 96,361,088 bytes | Below 128 MiB budget |
| End state | Complete at 30 s; paused; 279 performed events; tonic C | Approval null |

The source frame period is 125 ms. These software timestamps do not establish finer physical display or acoustic precision. The final refresh's two slices and 4 ms maximum are cached-refresh statistics, not initial cold preparation cost. Detector closure, host dispatch, real device/replay and physical output were **NOT_RUN** in this music take.

## Audio and video evidence

The static mapped and unmodified renders each include a stereo mix plus piano, bass, brush and Foley stems at 48 kHz for 30 seconds. Independent PCM inspection found no clipping, zero endpoints and stem sums within two PCM16 quantization units of each mix. Their matched draft MP4s preserve the original video timestamps. They contain no runtime key-change requests.

The actual browser OfflineAudioContext separately rendered the performed timeline with preserved source-buffer offsets: stereo, 48 kHz, 30 seconds, peak 0.01281291, RMS 0.00198715 and zero clipped samples. [browser-offline-render.json](browser-offline-render.json) records that result. It is an offline render of browser state, not recorded speaker output.

The browser's export-button check is **BLOCKED / UNCONFIRMED**: the Playwright transport closed before the click returned. No downloaded performance WAV or export success is asserted. Static WAV/stem/mux exports remain reviewable. A UI screenshot was saved before the disconnect at [browser-music.png](browser-music.png).

## Verification and unresolved work

`make test` passed 677 Python tests, 70 contract TypeScript tests, 10 bridge tests, 64 audio tests with one opt-in candidate check skipped, Ruff, typecheck and build. The exact-candidate cache check separately passed. The first restricted run could not bind loopback sockets in two bridge tests; its authorized rerun passed without removing tests. Five focused bundle-binding regressions passed after an independently found defect was repaired. The pack checker passed all 216 entries, eight semantic types and 14 negative controls. Logs and the independent gate provide scoped evidence.

The current root later received concurrent Blender edits. They were preserved. The saved preparation-source snapshot and loaded browser-build bytes identify what this report assessed; the earlier full test result does not certify arbitrary later root changes. No clean-checkout `make demo` result is asserted. Pause/seek/cancellation and fault handling have runtime test coverage, but the entire fault matrix was not repeated in the browser after tool failure.

No named human listened and supplied a dated, exact-asset verdict. Recognizability, pleasantness, sparse ornament feel, withheld resolution, owner identity, acknowledgement salience, coherent key landing and ending remain **AUDITION_PENDING**. Automated checks and model review did not create approval. Independent DAG work continued while these human subgates stayed pending.

At 19:41 UTC on September 12, node 06/07 recorded the AV failure. The coordinator also recorded the browser transport failure. The server's exact PID/PGID 23506 exited with status 0 and was confirmed absent; the launcher session 28673 exited 0. Mux process groups are confirmed absent in their job records. The completed UI timer was 1488. The owned browser tab 0 at `http://127.0.0.1:8772/?music=1` was last observed paused and complete, but its closure is unverified. No unrelated browser process was killed. A user cleanup confirmation has been requested.

The independent verdict is in [GATE.md](GATE.md). The node's measurement/report obligation is complete; release and overall task cleanup are not passed.
