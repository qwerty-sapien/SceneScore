# Audited baseline — what already exists

Audited against the working tree on 2026-09-12. Prior facts to **re-verify in node 00**,
not facts to trust blindly. `reports/phase3/GATE.md`, `reports/03A/MODEL_CARD.md` and
`docs/STATUS.md` are authoritative if they disagree with this file.

## Do not rebuild these

| Concern | Where it lives | State |
|---|---|---|
| RAGTM lineage and licence | `modules/muse/baseline/LINEAGE.md`, `RAGTM-LICENSE.txt`, `lineage.json` | Source inspected read-only at `RageAgainstTheMachine-main/`. ZIP-reported commit `8258b4e…`. MIT copied verbatim. |
| RAGTM comparator port | `modules/muse/baseline/ragtm.py` | `RagtmCandidatePort` preserves original defaults: alpha .02, 50 µV minimum, 7 µV deviation floor, score threshold 4, 250 ms cooldown, frontal-channel selection. Comparator only — must never issue a control. |
| Oracle test | `modules/muse/baseline/tests/ragtm_oracle.mjs` | Node harness wrapping verbatim frontend statements; compares 1,500 decisions on fixed-seed synthetic samples. Establishes a numerical subset only. |
| New causal detector | `modules/muse/baseline/causal.py` | `scenescore-new-causal-median/1`: one-pole low-pass, causal median/MAD normalization, bilateral path, duration hysteresis. `Config` defaults below. Exploratory, untuned. |
| Gesture grammar | `causal.py::Grammar` | Closure before commitment; triples and long trains rejected, never a prefix double. |
| Acquisition | `modules/muse/acquisition/{live,store,api}.py` | Health check, explicit-start raw recording, local store. `pylsl` imported only inside the explicit capture call. |
| Annotation | `modules/muse/annotation/workflow.py` | Review and relabel workflow. |
| Training primitives | `modules/muse/training/pipeline.py` | `causal_features` over `("peak_z","bilateral_ratio","duration_ms","rise_slope","fall_slope","imu_rms")`, grouped `validate_split`, `audit_real`, logistic and anomaly fits, `self_train`, `choose_development(recall_floor=0.95, max_latency_s=0.75, min_availability=0.95)`, `save_deployment`, `FinalTestLock`. |
| Event matching | `modules/muse/evaluation/events.py` | `Matcher`, one-to-one matching, quantiles, `candidate_diagnostics`. |
| Contracts | `contracts/0.1/schema.json` | `AcquisitionMetadata`, `EEGChunk`, `BlinkCandidate`, `GestureEvent`, `ControlAction`, `ClockMapping`. Frozen. |

## `causal.py::Config` defaults

`warmup_s 1.0`, `baseline_window_s 3.0`, `lowpass_hz 10.0`, `high_z 5.0`, `low_z 2.0`,
`floor_uv 7.0`, `min_duration_s .04`, `max_duration_s .4`, `min_separation_s .10`,
`max_gap_s .5`, `cooldown_s .25`. These are exploratory configuration values, hashed into
output. They are not tuned and carry no accuracy claim.

## The four facts that shape this pack

1. **There is no real data.** `reports/03A/MODEL_CARD.md` and `docs/STATUS.md` record
   `INSUFFICIENT_REAL_DATA` and **zero deployment models**. Everything downstream of
   collection is currently fixture-tested only.
2. **Closure delay is a latency floor, not an inefficiency.** Double-only grammar cannot
   commit until it has seen that no third blink arrives within `max_gap_s`. That is 500 ms,
   leaving 250 ms of headroom under the repo's 750 ms p95 gate. Verified by
   `examples/check_pack_examples.py`.
3. **The music side already accepts controls.** `packages/audio/transport.ts::Timeline.submit`
   validates and enqueues; `apps/web` already has `KEYBOARD`, `SYNTHETIC_TEST`,
   `REAL_REPLAY` and `LIVE_MUSE` modes with the last two disabled. You are filling in a
   socket that exists, not building the far side.
4. **The headset itself is unverified.** `docs/VISION.md` lists actual Muse generation,
   transport, channels, units, rate and Bluetooth permission as unresolved. The RAGTM
   source declares TP9/AF7/AF8/TP10 at 256 Hz; that declaration says nothing about this
   owner's headset. Discover the real values; do not hardcode remembered defaults.

## Missing, and therefore this pack's actual work

- No runtime adapter turning a `GestureEvent` into a dispatched `ControlAction`.
- No `ClockMapping` bridging device time to the browser audio clock.
- No deployed training or feedback surface; `apps/web` is served locally by `make demo` on
  127.0.0.1:8765 and has no Vercel configuration.
- No collected sessions, no independent labels, no refit coverage, no negative-activity
  exposure.
- No measured interval anywhere on the ladder between a physical blink and audible sound.
