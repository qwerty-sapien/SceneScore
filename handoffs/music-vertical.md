# Blender scene to music vertical handoff

The requested DAG ran parallel geometry/source branches, then ornament, mapping and transition work, runtime integration, exact-candidate measurement and an independent gate. The existing studio now has a draft music route, original editable score/MIDI, articulational mappings, two near-miss holds, signed keyboard key-change control and draft audio/stem/video artifacts. Human subgates remained pending while independent work continued.

**Status:** `PIPELINE_TESTED_ONLY`; release `NOT_READY`; human audition `AUDITION_PENDING`; approval `null`. Resource cleanup is complete: the user confirmed the browser had always been closed, and the exact demo server was verified absent. The user has rejected the legacy animation quality; see `reports/music-vertical/USER-FEEDBACK.md`.

- [Independent gate](../reports/music-vertical/GATE.md)
- [Measurements and limitations](../reports/music-vertical/MEASUREMENTS.md)
- [DAG ledger](../reports/music-vertical/LEDGER.md)
- [Exact artifact hashes](../reports/music-vertical/ASSET-HASHES.json)
- [Resource teardown](../reports/music-vertical/TEARDOWN.json)
- [Mapped draft video](../artifacts/music-vertical/candidate-v1/mapped-draft.mp4)
- [Unmodified draft video](../artifacts/music-vertical/candidate-v1/unmodified-draft.mp4)
- [Editable MIDI](../artifacts/music-vertical/candidate-v1/score.mid)

Run `make music-demo` from the repository and open the printed local URL. Select **Start music demo**. For the reviewed full 30-second legacy synthetic candidate, press **M** around 19 seconds and 24.5 seconds to request the scene-directed −2 and +2 changes; the observed new-tonic arrivals were 22.5 and 27.5 seconds. The launcher is bounded to 600 seconds by default; stop it with Ctrl-C and verify its printed child exit. This is unapproved keyboard demonstration mode.

The two static MP4s demonstrate the animation-driven score without live key-change requests. Their comparison uses matching independent Foley. Browser control traces and performed offline statistics are separate evidence. No physical Blender replacement, EEG detector, acoustic measurement or human approval is implied.

The actual frozen scene has six of eight semantics, no collision/rebound and no added ornament notes. Articulation/dynamics and near-miss withholding are realized; some numeric ornament/register intentions remain sidecars. The library and fixtures exercise additional ornament transforms, but their listening verdict remains pending. The AV p95 was 144.33 ms against 50 ms, so the timing gate failed.

The combined checks passed 677 Python, 70 contract TS, 10 bridge and 64 audio tests, plus Ruff, typecheck and build; the skipped opt-in exact-candidate cache test passed separately. Later concurrent Blender changes were preserved and are not retroactively certified by that result. The exact loaded browser build and preparation source are archived. Four owned worktrees remain for review, with identities in `WORKTREES.json`; no task job is intended to remain active.

Outstanding work is explicit in the gate: repair and remeasure AV timing on an identified build, finish the remaining semantic realization if required for release, obtain a named human's exact-asset audition, verify the browser export interaction and replace the rejected legacy animation with a physically validated candidate. Browser cleanup is resolved by the user’s direct confirmation. No broader phase is authorized by this handoff.
