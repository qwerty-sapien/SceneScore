# Muse training webpage handoff

The user's request for a RAGTM-like live EEG collection/training webpage is
implemented as `apps/training`, `services/training` and a personal window model
in `modules/muse/training/web_model.py`. The root launcher is
`Launch Blink Trainer.command` / `make muse-train`.

Public page: https://scenescore-muse-vertical.vercel.app/train/.
Start locally to authenticate automatically and avoid the hosted page's browser
Local network access permission. Select an existing Muse LSL source; no stream
or recording starts automatically. See [user guide](../docs/MUSE_TRAINING.md).

The model is experimental, causal and local, with `control_authority:false`.
B/cue timing never becomes a feature or automatic ground truth. Review actual
raw intervals before fitting; use fresh complete development refits for separate
window results. The trained window model does not automatically replace or arm
the earlier double-only music detector.

34 backend/model and 10 UI tests pass. Desktop/mobile, actual synthetic browser
record/review/train/predict/export/delete, hosted-to-loopback access and launcher
cleanup passed. No advertised real stream or participant data was available.
The complete evidence and exact commands are in
[delivery gate](../reports/muse-training/GATE.md). All task-owned jobs stopped.

Existing concurrent music/Blender changes and the supplied RAGTM source were
preserved. No frozen schema or dependency lock changed. Optional receiver
dependencies live under ignored `artifacts/muse-training-runtime`.
