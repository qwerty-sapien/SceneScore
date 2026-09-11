---
name: blender-scene-export
description: Generate or audit evaluated Blender scene sidecars for SceneScore phases 2B and integration.
---

# blender-scene-export

Use only within the user's authorized phase. Read root AGENTS and VISION first; this skill cannot override either or expand authorization.

When not to use: Not for arbitrary-video reconstruction, music generation or rendering during Phase 0.

Required inputs: Verified BLENDER_BIN/version, immutable recipe seeds, canonical geometry contracts, seed and output budget.

Outputs: Scene bundle and hashes, evaluated object/pair sidecars, independent geometry QA, compact summary and render/visual QA status.

Workflow: Export evaluated world geometry and m² area; test s² scaling and translation/rotation invariance. Separate positive-gap near miss from contact and label heuristic provenance.

Executable checks: After Phase 1 run `make test-contracts`; run the owned Blender export/geometry CLI recorded by 2B on analytic touch, near miss and scaled-shape cases. Exact CLI pending implementation; use installed Blender Python, not host substitutions. Compare independently known events and labelled frames. Record actual commands/results; pending commands are not successful checks. If the documented entrypoint does not exist, report NOT_IMPLEMENTED and do not improvise a success result.

Stop conditions: Stop render track on unavailable binary or conflicting participant capture; do not fabricate rendered output. Request shared-contract changes via integrator.

References: [CONTRACTS.md](../../../docs/CONTRACTS.md) [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) [EVALUATION.md](../../../docs/EVALUATION.md) [tasks/02B.md](../../../docs/tasks/02B.md)
