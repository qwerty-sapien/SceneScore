# Music node 06 runtime handoff

**Implementation GO; exact candidate and browser integration pending.** Read `docs/requests/06/runtime.md` for API, budgets, verification and limitations. This worker owns only the two runtime files, its new runtime test and these two documents.

Preserved the coordinator's completed Muse ControlAction seam, motion reader dependencies, legacy transition goldens, sliced refresh/cancellation and waveform cache. Added opt-in vertical table execution with two cached acknowledgement notes at receipt +20 ms before score work, harmonic-only overlays, actual-arrival tonic state, pending landing limits, prefiltered near-miss holds, bounded cooperative pre-play buffers, cancellation, and phase-preserving performed/stem exports.

Integration guard: root files were verified unchanged against `reports/music-vertical/RUNTIME-DEPENDENCY.json` immediately before this handoff. Do not overwrite intervening edits without reconciling ownership.

| Owned code path | Reviewed SHA-256 |
|---|---|
| `packages/audio/engine.ts` | `3bb662bbbef40f2c5f6f286fe479f580fd4148061a639124447700ba64d4855d` |
| `packages/audio/transport.ts` | `2245f9a55598e8c60cb4cf331ab0273121cb54bf744d555a45dfa07756abd371` |
| `packages/audio/tests/music-runtime.test.ts` | `71b9ad9c684b31ea5c9aca3d22b10caf2b8d479136397930dbc053877f1e3aa4` |

Tests: final full audio suite 55 passed / 0 failed / 1 exact-candidate check skipped; focused checks passed; typecheck and diff check passed. No approval or acoustic claim. No task-owned persistent jobs remain. All recorded test sessions exited normally.
