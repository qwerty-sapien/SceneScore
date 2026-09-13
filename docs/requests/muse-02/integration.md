# Muse 02–04 integration request

The bounded acquisition/training implementation adds module-owned supplements
only. Mounting and root dependencies remain with the integrator. Preserve the
root locks; optional `pylsl`/native `liblsl` is absent in the tested project
runtime and the explicit diagnostic reports that fact without recording.

Public additions: `acquisition diagnose`, `collect`, `review`;
`baseline.replay.replay_session`; training `--freeze-assignments`; detailed
`readiness_report`. Collect accepts canonical AcquisitionMetadata and a separate
`scenescore.collection-protocol/1`; frozen index version 2 binds the recorded
consent bytes and precollection group assignment. Canonical 0.1 is unchanged.
An index created under the old protocol must be reaudited for genuine evidence,
not silently populated with invented declarations.

Pack/repository discrepancy: pack example trains describe onset-to-onset gaps;
repository Grammar uses previous **end** to next onset and strict advancement
past `last_end + max_gap_s`. Repository authority wins. Config defaults and the
500 ms closure floor remain unchanged. No threshold calibration or final matcher
lock was invented from fixtures. The runtime owner handles translated grammar
cases and any separately evidenced causal fix.

The actual LSL adapter lacks contact-quality measurements and never auto-arms.
Live control remains blocked until that signal provenance is independently
established; displaying advertised metadata is not sufficient. The collector's
raw progress remains local and is stripped from the collection summary callback.
No shared API should upload or expose arbitrary raw/session filesystem paths.
