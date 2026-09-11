# Task ownership and dependency schedule

Roles are accountable assignments for future runs, not agents launched now. Phase 0 is solo; no future phase is authorized by these cards. The user names the active phase.

| Phase | Accountable owner | Prerequisite | Card |
|---|---|---|---|
| 01 | integrator | Phase 0 documentation gate | [01](01.md) |
| 02A | 02A | Phase 1 frozen contracts | [02A](02A.md) |
| 02B | 02B | Phase 1 frozen contracts | [02B](02B.md) |
| 02C | 02C | Phase 1 frozen contracts | [02C](02C.md) |
| 02D | 02D | Phase 1 frozen contracts and fixtures | [02D](02D.md) |
| 02E | 02E | Phase 1 frozen contracts and fixtures | [02E](02E.md) |
| 03A | 03A | Phase 2A plus genuine independently labelled sessions | [03A](03A.md) |
| 03B | integrator | Phase 2B–2E handoffs and Phase 2A baseline or labelled replay/keyboard | [03B](03B.md) |
| 04 | release | Phase 3B integration gate | [04](04.md) |

The integrator owns contracts/, shared fixtures/, services/local/ mounting, root dependency locks/scripts, tools/, cross-module tests and shared STATUS. Release is a coordinated integrator role for final shared edits. Each worker may write its owned paths, handoffs/<phase>.md and docs/requests/<phase>/ only. Integrator merges proposed public golden fixtures from handoffs. No worker edits `.brief/`.

After Phase 1, authorized 2A–2E work may proceed concurrently in separate worktrees from the frozen base. Schedule participant capture separately from CPU-heavy Blender work. 3A may overlap media work only after 2A handoff and genuine labels; its detector paths are disjoint from acquisition. 3B integrates after 2B–2E and usable 2A fallback; 3A is optional. 4 is a solo release audit. Each phase stops for its own exit gate.

## Frozen Phase 1 handoff

Use Git tag contracts-v0.1 as the shared base. Canonical schema: contracts/0.1/schema.json; generated TypeScript: packages/contracts/generated.d.ts; Python boundary validator: src/scenescore/contracts.py. Router/CLI signature: services/local/README.md. The integrator also owns src/scenescore/ and contracts/provider/. Only contracts.validate currently executes. Workers may import public validators; no dependency on another worker's unfinished module is required for fixture development.

Module entrypoints: modules/muse/acquisition/api.py → /muse; modules/blender/api.py → /scene; modules/music/api.py → /music; modules/arranger/api.py → /arranger, each exporting router: APIRouter and health() -> dict. Module owners add no import-time jobs. Integrator alone mounts routers. Phase 2E owns apps/web/ and packages/audio/, including replacement of the fake-clock reference with tested production timing. Proposed dependencies and shared golden fixtures go through the integrator. See handoffs/01.md for exact checks and unresolved facts.

## Completed authorized wave

2A/B/C/D were implemented in four separate worktrees from contracts-v0.1, with three workers plus the integrator owning 2D. Root merged their owned commits, accepted scoped interface requests, mounted local module routes and added cross-module conformance tests. See reports/phase2/GATE.md for exact revisions/cleanup. 2E, 3A, 3B and 4 remain unstarted. Future worktrees should use the completed wave commit to consume these module implementations; historical contracts-v0.1 remains the unchanged schema baseline.
