# SceneScore

Greenfield local-first animation-to-jazz studio. Phase 2A/B/C/D provide local acquisition/replay, evaluated Blender scenes, original symbolic music and editable arrangement planning. The performance UI/audio executor and full transport integration are later phases. See reports/phase2/GATE.md for verified scope and pending hardware/audition gates.

Run `make install`, `make doctor`, then `make test` from this root. See docs/RUNBOOK.md for exact runtime/configuration assumptions and the next authorized phase boundary. Read AGENTS.md before work; docs/VISION.md is the canonical product brief and docs/STATUS.md distinguishes evidence from pending work.

- planning/scene_score_codex_pack/: unchanged supplied planning ZIP contents.
- .brief/: byte-identical compatibility copy required by that pack's prompt paths.
- contracts/, fixtures/, src/scenescore/, packages/contracts/: Phase 1 schema and harness.
- modules/muse/, modules/blender/, modules/music/, modules/arranger/: tested Phase 2 domain modules with explicit CLI and bounded local query/preview routes.
- artifacts/: measured scene/music outputs and unapproved audition candidates; ignored by Git, hashes recorded in reports.
- apps/web/, packages/audio/: minimal shell and fake-clock reference; no audio engine.
- RageAgainstTheMachine-main/: unchanged source under an independent local Git repository, ignored by the parent. Not a registered remote submodule; no game code imported.

The newer kinetic_jazz_codex_pack prompt is not available here. This phase follows the installed SceneScore pack while preserving the user's direct optional-Muse and musical-identity requirements. No later phase is authorized merely by a document link.
