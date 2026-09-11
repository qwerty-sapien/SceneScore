---
name: audiovisual-integration
description: Integrate and measure SceneScore transport, score audio, video and gesture controls in phases 2E/3B/4.
---

# audiovisual-integration

Use only within the user's authorized phase. Read root AGENTS and VISION first; this skill cannot override either or expand authorization.

When not to use: Not for headset model research or claiming audible results from DOM tests; no implementation in Phase 0.

Required inputs: Compatible approved plan/asset hashes, clock contracts, source-labelled event fixtures, output device/browser and worker handoffs.

Outputs: Fixture performance, event logs, output timing report, export bundle, human QA and exact task-job teardown evidence.

Workflow: Browser audio transport owns musical time. Reset epochs on seek/reconnect; reject stale/duplicate controls; default double preserves gain/articulation/expression. Foley follows scene time; label every fallback.

Executable checks: After Phase 1 run `make test-contracts` and documented phase-local fake-clock/browser tests. During integration run `make dev-replay`/`make demo` only after implemented, record session/PID, measure actual render/output and stop/verify jobs. Domain tests and demo do not exist yet. Record actual commands/results; pending commands are not successful checks. If the documented entrypoint does not exist, report NOT_IMPLEMENTED and do not improvise a success result.

Stop conditions: Stop live controls if clock/quality invalid while preserving music. Stop release claims when output/audition evidence missing; never conceal timing failures or leave task jobs running.

References: [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) [CONTRACTS.md](../../../docs/CONTRACTS.md) [EVALUATION.md](../../../docs/EVALUATION.md) [RUNBOOK.md](../../../docs/RUNBOOK.md) [tasks/02E.md](../../../docs/tasks/02E.md) [tasks/03B.md](../../../docs/tasks/03B.md)
