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

Executable checks: After Phase 1 run `make test-contracts`; run the owned Blender export/geometry CLI recorded by 2B on analytic touch, near miss and scaled-shape cases. Legacy CLI is `python -m modules.blender.batch`; the production CLI is `python -m modules.blender.production` with separate build, bake, replay, verify-replay, validate, export and render stages. Use installed Blender Python, not host substitutions. Compare independently known events and labelled frames. Record actual commands/results; pending commands are not successful checks. If the documented entrypoint does not exist, report NOT_IMPLEMENTED and do not improvise a success result.

Stop conditions: Stop render track on unavailable binary or conflicting participant capture; do not fabricate rendered output. Request shared-contract changes via integrator.

References: [CONTRACTS.md](../../../docs/CONTRACTS.md) [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) [EVALUATION.md](../../../docs/EVALUATION.md) [tasks/02B.md](../../../docs/tasks/02B.md)

## Authorized production revamp

Read [production status and commands](../../../reports/blender-revamp/DELIVERY.md) before resuming. Preserve archived candidates and source snapshots; build into a new directory. Default extraction is240Hz and playback30fps on the same seconds clock. Bullet solver resolution and extraction rate are independent. Calibrate the declared backend on isolated controls before judging production motion; a successful process exit or replay does not close physical or perceptual gates.

Use `modules.blender.selection` for exact active or explicit staged identity. Silent physical supports never own a musical motif. Canonical0.1 remains unchanged; roles, production evidence, features and playback policy are versioned supplements. Bind their exact bytes/hashes through preparation and approval. Keep full original music and a separate scene-duration excerpt with10ms final fade; no adaptive composition in this DAG.

Pinned Blender MCP is for bounded loopback inspection/scratch experiments only; see [MCP evidence](../../../reports/blender-revamp/MCP.md). Capture accepted interactive changes in generation source and invalidate derived evidence. CLI generation remains independent. Full decoding and still inspection do not certify continuous motion or human audition. Native hero calibration currently fails; do not activate it or render final hero/control production until that prerequisite passes under an explicitly authorized repair scope.
