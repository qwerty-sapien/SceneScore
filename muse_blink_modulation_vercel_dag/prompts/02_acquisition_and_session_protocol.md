# 02 — local acquisition and the labelling workflow

**Owns:** `modules/muse/acquisition/`, `modules/muse/annotation/`. **Budget:** 50 minutes.
**Reference:** `PARTICIPANT_PROTOCOL.md`.

`live.py`, `store.py`, `api.py` and `annotation/workflow.py` exist. Make them a workflow a
tired person can run correctly at hour four of a hackathon.

## One-command scripts

Transport health check. Explicit-start raw recording. Cued deliberate-double-blink
collection. Natural-activity and ordinary-blink negative collection, with exposure duration
logged. Session review, relabel and export. Deterministic replay through the exact causal
detector path. Split and index creation by complete session and refit.

Each prints what it is about to do, what it recorded, and where it went. A script that
silently succeeds is a script that silently records the wrong thing.

## Record the truth about the signal

Actual channel names, order, units, verified sample rate and transport as reported by the
device in node 00 — never remembered Muse defaults. Preserve raw samples and timestamps
unmodified and local. Record conversions separately from the raw data; never overwrite raw
in place. Reconcile sample and drop counts against stream continuity, with explicit gaps.
`EEGChunk` names the device epoch separately from the host receipt epoch.

## Labelling

Follow `PARTICIPANT_PROTOCOL.md`. Labels are `performed`, `missed`, `uncertain` and natural
negative. Cue state and prediction state are stored and displayed separately. **No
simultaneous motor confirmation** — a button press during the gesture leaks motor artifact
into the labelled window; delayed confirmation and review are the accepted path.

Support many short sessions and at least one deliberate removal and refit. Refit is the
dominant real-world failure and a model that has never seen one is untested.

## Tests

Replay determinism: the same recording through the same detector path yields identical
decisions. Split leakage: no window from one session appears in two roles. Fault resets:
dropout, reconnect and quality loss clear partial state. Ambiguous sequences are preserved
as ambiguous rather than coerced. Artifact serialization round-trips. Recording with no
device fails loudly rather than producing an empty session that looks valid.

## Forbidden

Uploading raw EEG anywhere. Recording anyone without consent under
`PARTICIPANT_PROTOCOL.md`. Deriving labels from detector output. Using cue timing as
evidence a gesture occurred. Hardcoding channel or rate defaults. Adding heavy dependencies
to the root locks — `pylsl` stays imported only inside the explicit capture call.

## Done when

A person can run collection end to end from one command each, the recorded metadata matches
what the device actually reported, replay is deterministic, and every label's independence
from the detector is auditable.
