---
name: symbolic-jazz-arrangement
description: Author or validate SceneScore symbolic jazz, brush catalogues and human-approved arrangement plans in phases 2C/2D.
---

# symbolic-jazz-arrangement

Use only within the user's authorized phase. Read root AGENTS and VISION first; this skill cannot override either or expand authorization.

When not to use: Not for opaque audio-only composition, copying recordings, live audio-critical model calls or Phase 0 media work.

Required inputs: Composition/brush seeds, validated scene summary, exact groove versions, approved palette/transition bounds and optional verified provider configuration.

Outputs: Editable score/events, separate stems when rendered, plan approval hashes, catalogue/provenance and independent audition status.

Workflow: Separate harmony/register/expression lanes; only pitched voices transpose. Resolve swing once using composition policy; preserve Foley scene time. Validate model shape and musical semantics, then obtain human review of exact plan.

Executable checks: After Phase 1 run `make test-contracts`; use 2C/2D owned test/renderer commands from handoffs for bar totals, unknown grooves, signed modulation, brush invariance, seed repeatability, stale approval and non-silent render. Exact domain commands pending; schema tests cannot pass audition. Record actual commands/results; pending commands are not successful checks. If the documented entrypoint does not exist, report NOT_IMPLEMENTED and do not improvise a success result.

Stop conditions: Stop activation of invalid/unapproved plans; use labelled manual baseline for absent API. Stop on missing asset rights or unsafe ranges; mark unheard music AUDITION_PENDING.

References: [VISION.md](../../../docs/VISION.md) [CONTRACTS.md](../../../docs/CONTRACTS.md) [EVALUATION.md](../../../docs/EVALUATION.md) [tasks/02C.md](../../../docs/tasks/02C.md) [tasks/02D.md](../../../docs/tasks/02D.md)
