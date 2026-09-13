# Music vertical independent gate

Coordinator addendum, 2026-09-13: the user rejected the unchanged legacy animation for physical quality. [USER-FEEDBACK.md](USER-FEEDBACK.md) records the Jam evidence and an independent evaluated-state audit, including 0.533745 m cube interpenetration. The full vertical delivery remains incomplete; prior software passes do not certify this animation. The user also confirmed the browser had always been closed, resolving that separate cleanup concern.

Final independent node 08 review, incorporating the node 07 report issued at 2026-09-13 00:59 UTC: `MEASUREMENTS.json`, `ASSET-HASHES.json` and `TEARDOWN.json`. The review is finalized; the release gate does not pass.

The release verdict is **NOT_READY**. Software evidence reaches **PIPELINE_TESTED_ONLY**. Human audition is **AUDITION_PENDING**, approval is **null**, and the measured software audiovisual offset fails its 50 ms target. **Cleanup correction, 2026-09-13:** the user confirmed the browser had always been closed. The cleanup blocker is removed; the server exit remains independently verified. No human, acoustic, live-device, physical-scene or Phase 4 acceptance is implied.

## Exact candidate assessed

The review used the original frozen 30-second, 8-fps legacy synthetic projectile/tower animation, seed 42, Tilted Blue/version 1 with its authored ending, and `brush_swing_light_v1` version 1. No physical Blender replacement or substitute scene was promoted.

| Input/artifact | SHA-256 |
|---|---|
| `artifacts/music-vertical/candidate-v1/candidate.json` | `d9ce7fd69f7aa9d47b6db169a6c779fa82a8795fce299858b614f358b797a0c9` |
| Exact draft plan bytes | `fd090867ab61fde774879f23ae56ea388e88db072521d9dd9f5a3bc5b489808d` |
| Scene input bytes | `424d74fa8cf65b702354d94b592ea2b0e90fdaf779722ac6dc17ffc81145856a` |
| Composition/groove input bytes | `e8b7b69331f3a17c121071d913154bfa84c6eb1a7735989d64a76f002392c2e6` |
| Original matched video | `07a65b59bda1afc07fc1397f72232f2855df595b2cfe3948ea602d517890a04a` |
| Mapped static mix WAV | `be2cc7d80acdd3d8c114ae4585f0ac1485aa84a679fc2552b46f01b74465f201` |
| Unmodified static mix WAV | `d596c758d85a9f66320708394301086dbdad32c2db7cca8cd303a3675ef367b2` |
| Mapped draft mux | `3646bea555ad8f8e3a0255cb349cc6b71a0436903e8de1ee8ebfab1811bf7e10` |
| Unmodified draft mux | `d1d024256487765d7463ebc88a707f9952ac41bd1b6c75fed042b230b209a2bb` |
| Loaded browser JavaScript, `browser-build/index-BBrePzdL.js` | `140254cd834fb83e662bf63409778a75e0526445f50bf17994fd0776f7fdd40b` |
| Loaded browser CSS, `browser-build/index-DhfNs5k7.css` | `93e6bf561906243a3c8a19057786762a242878f97fabd5b79eb282e7e495ae0c` |

The two static muxes contain animation-driven mapped/unmodified scores without runtime control requests. The browser's two-control performance is separate evidence. All 42 frozen pack/schema/lock/source-media hashes were independently rechecked unchanged. All 11 preparation-code snapshot files match the candidate's recorded code hashes, including the preserved core version predating later concurrent Blender edits. See `INDEPENDENT-CANDIDATE-REVIEW.json`, `IMMUTABLE-CHECK.json` and the candidate's `preparation-code-snapshot/`.

At finalization all **65** entries in `ASSET-HASHES.json` were independently rehashed and matched. The saved loaded browser build identifies the tested implementation; later root edits are not silently covered by this review. Node 07's timing arithmetic matches the retained browser record and the independent review.

## What the actual scene demonstrates

| Semantic | Actual canonical episodes | Evidence and limitation |
|---|---:|---|
| Approach | 6 | 159 causal source-slot control rows; mapped legato. Numeric ornament/tension/register intentions do not themselves synthesize extra notes. |
| Near miss | 2 | Third withholding over [12.625, 13.25] and [17.875, 18.5] seconds. Each hold is one beat (0.625 s), with no forbidden pitch-class overlap in the mapped score. No near-miss accent, Foley or key action is generated. |
| Separation | 6 | Detached articulation and attenuation; numeric density/register intentions remain sidecar data. |
| Contact onset | 4 | Source-slot staccato where a slot is available, plus the separate scene-time Foley stream. No pitched timbre switch or accent-velocity automation is claimed. |
| Contact sustain | 4 | Mapped intent/dynamics and separate Foley sustain; perception remains unreviewed. |
| Contact release | 4 | Mapped release intent and separate Foley release; perception remains unreviewed. |
| Collision | 0 | Analytic fixture coverage only. |
| Asymmetric rebound | 0 | Analytic fixture coverage only. Actual evaluated area ratio is about 1.925, below the required 4. Equal-area negatives suppress the figure. |

The mapped candidate has 269 events, including 12 independent Foley events, against 258 source music events. Every event ends by 30 seconds; brushes are unchanged. Pitch/time identity is retained for 159/162 source notes (98.15%) and 47/48 lead notes (97.92%); these percentages do not mean articulation/dynamics are unchanged. There are **zero added ornament events on this actual scene**. The fixture rebound chooses the smaller owner, but may place its grace on a later existing source slot, up to 0.75 seconds after the contact; the pack's literal contact-tick realization is therefore not fully established. None of these data checks is a listening verdict.

## Machine and integration checks

| Check | Result | Evidence |
|---|---|---|
| Combined repository checks | PASSED | `make-test-final-authorized.log`: 70 contract TypeScript tests; 677 Python tests; 10 bridge tests; Ruff; 64 audio tests, one candidate-dependent test skipped; typecheck and build. The candidate-dependent check separately passed in `candidate-cache-test.log`. |
| Initial restricted combined run | BLOCKED, superseded | `make-test-final.log`: two bridge tests could not bind loopback sockets in the sandbox. The authorized rerun passed; no failing test was removed. |
| Pack table/taxonomy checker | PASSED | `pack-check-final.log`: 216 entries, eight semantic types, 14/14 negative controls rejected. Original table/taxonomy bytes remain frozen. |
| Fixed-seed generation twice | PASSED | Independent byte comparison of both actual candidate files; `DETERMINISM.json` additionally binds repeated events, plan, controls, holds and MIDI. |
| Exact packet/plan binding | PASSED after repair | `INDEPENDENT-BINDING-REVIEW.json`: the unchanged candidate verifies, and five focused regression tests pass. |
| Eight fixture semantics and negative controls | PASSED, fixture scope | Node 01/04 handoffs and combined tests; actual-scene type limitations remain in the table above. |
| Note bounds, duration and source/Foley separation | PASSED | Twenty independent candidate checks in `INDEPENDENT-CANDIDATE-REVIEW.json`; static WAV endpoints are zero. No physical stuck-note observation is claimed. |
| Transition reachability and jazz exclusion | PASSED | `TRANSITION-REVIEW.json`: matching 216-entry Python/TypeScript pitch digest, 72 valid default guide-tone dyads, signed step history; jazz remains disabled and unreachable. |
| Common control validation path | PASSED, software scope | Keyboard/synthetic/replay/device adapters use the same `dispatchControl → Engine.submit → Timeline.submit` seam in contract/runtime tests. Actual real replay and hardware were NOT_RUN. |
| Two browser controls and actual tonic state | PASSED, software observation | `browser-two-control-take.json`: −2 request at 19.0067 s arrives at 22.5 s; +2 request at 24.5053 s arrives at 27.5 s; both executed, final tonic C, complete at 30 s, 279 performed events, approval null. |
| Pause/seek/restart, pending and cancellation | PASSED in runtime tests | Node 06 tests cover pending rejection through landing end, pause/seek cancellation, source phase, partial scheduling failure and bounded preparation. The browser restarted the same candidate between retained attempts. Do not infer every fault case was repeated in the browser. |
| Exact-candidate cache budget | PASSED | 1,021 buffers, 96,361,088 bytes, below 128 MiB. Fake-context cache check and actual browser snapshot are separately labelled. |
| Static PCM/stem/mux consistency | PASSED | `INDEPENDENT-PCM-REVIEW.json`: ten WAVs, each 1,440,000 frames/48 kHz/stereo/PCM16, unclipped and zero endpoints. Each mix differs from separately quantized stem sums by at most two PCM16 LSB. Mux reports preserve draft labels. |
| Browser performed offline render | PASSED, software scope | `browser-offline-render.json`: actual OfflineAudioContext, 30 s/stereo/48 kHz, peak 0.012813, RMS 0.001987, zero clipped samples. It renders recorded source offsets, not measured live output. |
| Browser export-button/download completion | BLOCKED | Playwright disconnected before confirmation. The static WAV/mux artifacts and browser OfflineAudioContext statistics are available; a completed browser export download is not claimed. |
| Approval truthfulness | PASSED for reviewed candidate/run | Candidate and browser approval null; audition pending; no automated approval. UI edits clear approval. Human approved performance was NOT_RUN. |
| Clean-checkout `make demo` | NOT_RUN | Current-tree build and dedicated existing-studio music route were exercised. No clean Git checkout result is asserted. |
| Human listening | BLOCKED / AUDITION_PENDING | No named reviewer, date and exact-asset listening verdict. |
| Acoustic/display onset, real hardware/replay | NOT_RUN | No microphone/loopback/display capture or eligible real recording evaluated in this music run. |
| Node 07 measurement report | PASSED as evidence delivery | `MEASUREMENTS.json` records exact identities, separate timing intervals, load, retained attempts, missing listening verdict and explicit passed/failed/blocked/not-run checks. Its AV result remains FAILED. |
| Server/render/test teardown | PASSED | `TEARDOWN.json`: server session 28673 exited 0; exact PID/PGID 23506 absent by authorized `ps`; log records SIGINT and exit 0. Foreground sessions exited; mux process groups are absent. |
| Owned browser-tab teardown | RESOLVED by user confirmation | The user stated on 2026-09-13 that it had always been closed. Tool verification remains unavailable; it is not evidence of an open tab. `TEARDOWN.json` records the authority. |

## Timing observed, kept separate

The retained second browser take used Chrome 152 on macOS, a 48 kHz AudioContext, the exact 30-second/8-fps candidate, and two automated activations of the keyboard UI path. It is not a detector trial or a human performance. The first take is retained separately because only its first control arrived before the end.

| Interval | Observations | Result |
|---|---|---|
| t4 − t3, request to transport receipt | 0 ms in both AudioContext timestamp records | Software timestamp observation; not proof of zero wall-clock latency. |
| t5 − t4, receipt to scheduled acknowledgement | 20 ms in both records | PASSED the 300 ms scheduled-onset threshold for n=2; acoustic output unmeasured. |
| t6 − t5, acknowledgement to musical arrival | 3473.33 ms and 2974.67 ms | Recorded intentional musical wait; not subtracted from or folded into another interval. |
| Video/audio absolute software offset | Last 200 samples, nearest-rank p95 144.33 ms, max 147.67 ms | FAILED the 50 ms target; p95 about 7.00 ms worse than the previous 137.33 ms result. |

Arithmetic and raw-record references are in `INDEPENDENT-BROWSER-REVIEW.json` and `MEASUREMENTS.json`. The frame period is 125 ms, so these software differences do not support sub-frame physical precision. The browser take ran alongside repository `make test`, with a bounded 20 ms automation timer and trace snapshots; CPU-load percentage and cold preparation time were not measured. The final two cached refresh slices (maximum 4 ms) are not the initial cold preparation cost. The recorded user-agent is browser evidence only; no host architecture is inferred from it.

## Findings and remaining gates

| Time UTC, 2026-09-12 | Owner | Finding | Disposition |
|---|---|---|---|
| 19:30 | 06, model integration | P2: browser verified events against their own bundle hash without tying musical content to the plan-bound digest; missing optional vertical packet fields could skip checks. | CLOSED. Lossless JSON projection preserves Python number tokens, requires the vertical packet, and validates its mapped musical digest. Candidate bytes unchanged; independent five-test rerun passed. |
| 19:41 | 06/07 | Software audiovisual p95 144.33 ms exceeds 50 ms and regresses from 137.33 ms. | OPEN. No threshold amendment or source-scene replacement accepted. |
| 19:41 | 07/coordinator | Browser control transport disconnected after successful playback/offline measurement. Browser export completion and owned-tab closure could not be confirmed at the time. Tab cleanup was subsequently resolved by direct user confirmation. | Export check remains BLOCKED. Repeated close/tab calls returned `Transport closed`; CUA exposed only an empty in-app browser and its Chrome lookup timed out. No unrelated browser process was killed. |
| 19:31 | 04 | Actual-scene ornament-density/register intentions are only partly realized, and fixture rebound can quantize later than contact. | OPEN scope qualification. Do not claim fully realized taxonomy or an actual rebound demo. |
| Recorded through finalization | Human audition subgates 02/03/04/07 | No named human has reviewed the full exact A/B, withheld resolution, sparse ornaments, owner identity, acknowledgement, key landing or ending. | HUMAN-DECISION / AUDITION_PENDING. Independent software work continued. |

Earlier node 05 voicing/guide-tone/register-history findings are closed only to the scope recorded in `TRANSITION-REVIEW.json`. No new implementation code was written by this reviewer.

## Resource status at finalization

The owned web server's exact session, PID and process group have exited. No containers were started; worker and foreground test/render jobs exited; mux reports verify their process groups absent. The owned browser tab was last observed paused, complete at 30 seconds, with bounded UI timer 1488 complete. That observation does **not** establish tab closure or cleanup of every page-owned resource. At the time of the tool failure, closure could not be verified because Playwright returned `Transport closed` and CUA could not obtain Chrome. The user subsequently confirmed the tab had always been closed, resolving this cleanup concern without further browser inspection. No shared browser process was terminated without established ownership.

## Demo commands and 60-second keyboard fallback

From `/Users/agent/Desktop/SceneScore`, use the already prepared exact candidate:

```sh
PYTHONPATH=.:src .venv/bin/python tools/music_demo.py --candidate artifacts/music-vertical/candidate-v1 --port 8772 --seconds 600
```

Open `http://127.0.0.1:8772/?music=1`. The launcher builds the existing studio, reports its exact child PID/process group, and stops that child when interrupted or when its bounded lifetime ends. This is the command exercised during the run; the saved browser build above remains authoritative for the measured result if concurrent root changes produce a different subsequent build. The server from this run is confirmed stopped.

Within 60 seconds: open the music route and select **Start music demo**. Leave approval pending and use the keyboard path. Listen/watch the full 30-second take; press **M** at approximately 19 seconds and again at 24.5 seconds. The selected tower's causal world-Z motion chooses −2 then +2; the expected new tonic arrivals are 22.5 and 27.5 seconds. The score continues if no request is made. If a request is rejected, use its visible reason; do not bypass the transport. If the browser is unavailable, open the hashed `mapped-draft.mp4` for the static articulation demo, explicitly stating that this fallback has no runtime key-change controls. Stop the launcher with Ctrl-C and verify its reported child exit.

Actual commands supporting the gate are preserved in `MEASUREMENTS.json`, the logs and node handoffs. This reviewer additionally ran bounded read-only Python candidate/hash and standard-library PCM inspections, exact-candidate Node verification, `node --import tsx --test packages/audio/tests/music-bundle.test.ts` (5 passed), and a final 65-file asset-hash/measurement-arithmetic check (passed). An initial metadata probe used the wrong interaction key, and a PCM probe initially attempted unavailable NumPy; corrected probes passed without installing dependencies. All reviewer foreground commands exited. This reviewer started no server, browser, container, detached worker or persistent job. The coordinator amended only the cleanup status on 2026-09-13 from the user's direct confirmation; the earlier independent review is archived under `history/2026-09-13-before-user-correction/`.
