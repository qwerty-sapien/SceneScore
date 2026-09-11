---
name: blink-evaluation
description: Evaluate SceneScore blink detectors on independently labelled sessions; use for phases 2A/3A evaluation and audit.
---

# blink-evaluation

Use only within the user's authorized phase. Read root AGENTS and VISION first; this skill cannot override either or expand authorization.

When not to use: Not for gameplay, mental-state inference, media generation or Phase 0 model training.

Required inputs: Verified device metadata, immutable raw sessions, independent labels, frozen session/refit split, causal baseline/config hashes.

Outputs: Event report, per-session errors/exposure/availability/confidence bounds, split manifest, model card and rollback handoff.

Workflow: Check frozen split disjointness and chronological one-to-one matching. Include all abstention/cooldown misses; separately report armed and elapsed exposure. Do not tune final tests or use synthetic accuracy.

Executable checks: In Phase 1 use `make test-contracts` once implemented. In 2A/3A run the task-owned replay/evaluator CLI recorded in its handoff on the frozen split; exact CLI is pending implementation. Require nonzero exit for invalid splits and compare counts to independent annotation. No executable evaluator exists in Phase 0. Record actual commands/results; pending commands are not successful checks. If the documented entrypoint does not exist, report NOT_IMPLEMENTED and do not improvise a success result.

Stop conditions: Stop empirical evaluation if device units, independent labels, locked matcher or consent are missing; software fixtures may continue in authorized phases. Stop training at the declared gate, not at a desired score.

References: [EVALUATION.md](../../../docs/EVALUATION.md) [LINEAGE.md](../../../docs/LINEAGE.md) [CONTRACTS.md](../../../docs/CONTRACTS.md) [tasks/02A.md](../../../docs/tasks/02A.md) [tasks/03A.md](../../../docs/tasks/03A.md)
