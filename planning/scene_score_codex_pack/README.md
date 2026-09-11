# SceneScore: documentation-first Codex preparation pack

## Scope and status
This is a phased implementation brief, with original compositional sketches and machine-readable design seeds. It is not an implemented application. No Muse model has been trained, no real participant performance has been measured, and no Blender scene has been rendered by this pack.

The product is an animation-to-soundtrack authoring and performance tool. Geometry drives musical relationships and sound effects. A deliberate Muse double-blink cues a key change. The visual scene guides an explicitly defined upward/downward musical movement. This is not a game or a mental-state detector.

## Installation and first run
Place this folder's contents inside `.brief/` in a new local project directory. Open Codex at that project root. Start with exactly:

```text
Read .brief/prompts/00_foundations.md and execute only that phase. Treat .brief/ as immutable input. Establish the documentation and agent instructions before implementing the application. Follow its scope boundary and stop at its exit gate.
```

Supply `RAGTM_PATH` as a local path when available. The connected repository searches performed while preparing this pack did not locate the user's RAGTM implementation. Its successful Flappy Bird blink control is user-reported, not code-verified. Do not invent its implementation.

## Execution order
| Phase | Prompt | Dependency | Concurrency |
|---|---|---|---|
| 0 | 00_foundations.md | New repository | Solo |
| 1 | 01_contract_harness.md | Phase 0 | Solo, contract owner |
| 2A | 02A_muse_acquisition.md | Phase 1 | Parallel preparation |
| 2B | 02B_blender_assets.md | Phase 1 | Parallel preparation |
| 2C | 02C_music_assets.md | Phase 1 | Parallel preparation |
| 2D | 02D_arranger.md | Phase 1 fixtures | Parallel preparation |
| 2E | 02E_performance_ui.md | Phase 1 fixtures | Parallel preparation |
| 3A | 03A_muse_training.md | 2A and genuine labelled sessions | Parallel with media work |
| 3B | 03B_integration.md | 2B-2E and 2A baseline | Integrator after merge |
| 4 | 04_release_rehearsal.md | Integration | Solo release owner |

For each subsequent run: `Read .brief/prompts/<filename> and execute only that phase.` Start agents in separate worktrees after phase 1. Give each its ownership boundaries. Only the integrator changes shared schemas, dependency locks, root scripts, and cross-module tests. Hardware capture and CPU-heavy Blender renders must not contend during a participant session.

## Five-hour event scope
Preparation is conditional on the organizer's rules. A subscription does not authorize prebuilding a judged project. Record which code, training data, models, music and renders were created before the event. Do not misrepresent their origin.

With approved preparation complete: one polished scene, one original jazz sketch, one brush groove, near-miss and collision mapping, human-approved arrangement, double-blink modulation, replay/keyboard fallback, and an export constitute the demo. Ten scenes and four musical sketches form the prepared test library, not ten event-day features.

A suggested event work budget is: 0-30 minutes environment check and replay baseline; 30-110 first complete audiovisual path; 110-170 live Muse and quantized modulation; 170-230 arrangement preview and one scene variation; 230-270 failure tests and packaging; 270-300 rehearsal. These are planning allocations, not measured completion times.

When prebuilding is prohibited, use the same phase boundaries during the event but reduce to one generated scene, one score and a calibrated deterministic blink detector. Multi-session model research, statistical validation and a ten-scene library cannot honestly be promised within the same five-hour build.

## Files
`prompts/`: separate task contracts for separate Codex runs.
`seeds/`: original composition sketches, brush-groove definitions, ten animation recipes, gesture profiles and acceptance targets. These describe assets to implement and audition, rather than finished recordings.
`SOURCES.md`: checked primary references and verification limitations.
`ALL_PROMPTS.md`: convenience copy for reading only. Do not send it as one implementation instruction.

## Non-negotiable uncertainties
Near-perfect blink detection is an aspiration, not a property implied by unsupervised learning. Short recordings cannot establish near-zero false activation rates. A newly refitted headset requires independent validation. An external model's schema-valid output may still be musically wrong. Procedural brush sounds and geometry-derived timbre are creative approximations unless independently validated.
