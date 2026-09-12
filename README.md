# SceneScore

Greenfield local-first animation-to-jazz studio. The local browser now plays an editable original score against verified Blender video, with optional deliberate-blink conducting, keyboard fallback and separate collision Foley. Phase 2E/3 software is delivered; the formal approved-performance, human-audition and AV-timing gates remain open. See reports/phase3/GATE.md.

Run `make install`, `make doctor`, then `make test` from this root. See docs/RUNBOOK.md for exact runtime/configuration assumptions and the next authorized phase boundary. Read AGENTS.md before work; docs/VISION.md is the canonical product brief and docs/STATUS.md distinguishes evidence from pending work.

With the preserved verified local scene assets, `make demo` prepares/builds the studio and serves http://127.0.0.1:8765. Audition is available before approval. A human must approve the exact plan before conducting; missing Muse/API access does not block draft playback. Ctrl-C stops the local server.

- planning/scene_score_codex_pack/: unchanged supplied planning ZIP contents.
- .brief/: byte-identical compatibility copy required by that pack's prompt paths.
- contracts/, fixtures/, src/scenescore/, packages/contracts/: Phase 1 schema and harness.
- modules/muse/, modules/blender/, modules/music/, modules/arranger/: tested Phase 2 domain modules with explicit CLI and bounded local query/preview routes.
- artifacts/: measured scene/music outputs and unapproved audition candidates; ignored by Git, hashes recorded in reports.
- apps/web/, packages/audio/: browser authoring/performance surface, deterministic procedural audio, native scheduling, exact approval and stereo/stem export.
- RageAgainstTheMachine-main/: unchanged source under an independent local Git repository, ignored by the parent. Not a registered remote submodule; no game code imported.

The newer kinetic_jazz_codex_pack prompt is not available here. This phase follows the installed SceneScore pack while preserving the user's direct optional-Muse and musical-identity requirements. No later phase is authorized merely by a document link.
