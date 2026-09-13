# Deferred training integration

The direct-BLE request explicitly says to avoid files being changed by the
concurrent task **Simplify Muse training interface**. This implementation owns
the studio Muse panel and semantic companion; the trainer is a separate app.

Protected paths for this run: `apps/training/`, `services/training/`,
`modules/muse/training/`, `docs/MUSE_TRAINING.md`, `tools/muse_training.py`, and
`tools/muse-training-requirements.txt`. The baseline hashes and Git base are in
`reports/muse-ble/concurrent-baseline.json`. Changes to those hashes during this
run belong to concurrent work and must not be reverted or bundled into the BLE
handoff. Blender/media work is also outside this task.

After both tasks finish, inspect their final diffs before proposing a trainer
adapter. The trainer currently owns raw local traces, recording/label consent,
reviewed windows and stopping-accuracy decisions. Reuse the new pure Muse
protocol and BLE manager through a trainer-owned adapter if desired. The
semantic companion must continue to exclude EEG from every HTTP response;
do not turn its API into a raw-trace or recording endpoint to serve training.

The trainer follow-up must preserve fresh session/refit/clock provenance,
separate recording consent, independent labels and held-out stopping criteria.
Neither Bluetooth connectivity nor a high classifier score certifies signal
quality or authorizes musical controls. A trainer transport update will require
rechecking its final UX/API and updating its transport documentation together.

## Shared overlap observed during integration

After the BLE edits were integrated, the other task added checkpoint selection
to `apps/web/src/muse/MusePanel.tsx`, `bridge.ts`, `types.ts`,
`services/bridge/server.py`, and an exploratory option in
`modules/muse/baseline/causal.py`. These files were then frozen for this BLE task;
no later replacement or cleanup of the other task's edits is authorized here.
Observed hashes and frontend comparison diffs are in
`reports/muse-ble/concurrent-overlap.json` and adjacent `.concurrent.diff` files.

Reconcile checkpoint state with BLE session changes after both tasks complete:
the BLE adapter constructs a fresh baseline on first verified frames, so active
checkpoint/evaluation display and pending-arm state need an explicit reset seam.
The BLE-owned adapter now uses the existing disarm seam on connection and
malformed input, cancelling pending warmup arms, and clears optional prior
checkpoint/evaluation display at a new session. Focused fixtures cover this
compatibility behavior without editing the active shared files.
The new checkpoint API/accuracy semantics belong to the concurrent task and are
outside the BLE feature's narrow API claims. Recheck detector selection, clock
configuration hashes and rearm behavior on the final combined diff.
