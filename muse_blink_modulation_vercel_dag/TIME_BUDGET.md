# Six-hour budget

| Node | Budget | Hard stop behaviour |
|---|---|---|
| 00 lineage and architecture freeze | 25 min | Ship the decision record; name the unverified transport facts. |
| 01 control seam and latency ladder | 45 min | Freeze the seam even if instrumentation is partial. Everything downstream depends on it. |
| 02 acquisition and session protocol | 50 min | Cut relabel UI first. Keep record, cue, and export. |
| 03 detector ladder | 60 min | Cut the supervised classifier; ship the causal threshold baseline plus grammar. |
| 04 real data and frozen evaluation | 60 min | With no participant, this becomes a 20-minute honest `PIPELINE_TESTED_ONLY` export. |
| 05 deployed surface | 60 min | Replay and simulated modes first. Live mode stays visibly unavailable. |
| 06 dispatch into music | 30 min | Keyboard equivalence is the acceptance criterion, not live hardware. |
| 07 end-to-end gate | 30 min | Always runs. |

Total 6h 20m against a 6h wall clock. Cut from inside nodes, never the gate.

## The honest ceiling

`docs/EVALUATION.md` defines `SUPERVISED_DEMO_READY` as ≥100 verified held-out gestures
across ≥2 held-out refit sessions, ≥60 minutes of natural activity, recall ≥0.95, zero
observed false activations and armed availability ≥0.95. **That is not reachable in six
hours.** Collecting it alone exceeds the timebox.

Plan for `PIPELINE_TESTED_ONLY`, or `REAL_DATA_EXPLORATORY` if a consenting participant is
actually available. Export the label that the data supports and let the gate say so. A
demo that works on stage and is labelled exploratory is a success; the same demo labelled
`SUPERVISED_DEMO_READY` is a fabrication.

## Explicitly out of slice

Deep EEG models. Online adaptation during the demo. Triple-blink or amplitude-derived
controls (`docs/VISION.md` lists them as experimental and disabled). Multi-participant
generalization claims. Cloud storage of raw EEG. Safari parity. Any statistical target
claim — the arithmetic in `docs/EVALUATION.md` shows roughly 299 all-success opportunities
would be needed for 0.99 recall, and roughly 6 zero-event hours for 0.5 false activations
per hour.
