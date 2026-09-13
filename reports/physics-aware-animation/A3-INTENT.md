# A3 typed scene intent

PASS. `modules/blender/scene_intent.py` implements the immutable, serializable
`scene-intent-2` supplement. The example round-trips exactly through typed records
and JSON. A matching JSON Schema is generated from the types and checked for drift.
Canonical 0.1, the pack's version-1 linter/example, production recipes, solver,
physical thresholds and active/staged selection are unchanged by this node.

The representation covers contiguous route stages, persistent actors/voices,
explicit mechanics limits, event order, approximate target windows, sparse-event
policy, camera/ending intent, reference lessons and downstream music proposals.
Continuous support is a separate type and stream; it does not consume salient
count/duty. Near misses require positive physical clearance bounds in metres with
an optional target, and cannot overlap same-pair continuous support contact.

Strict input checks reject unknown/missing fields, unknown event kinds, duplicate
keys/IDs, non-finite/boolean numeric values, impossible ordering/windows, excessive
salience, silent-support voices and invalid actor/event/music references. Analytic
scope rejects moving obstacles or multiple dynamic spheres. Unimplemented explicit
mechanics/merge models and unbound references issue explicit warnings. Impact
Foley cannot be requested for a near miss or quantized away from scene time.

[SCENE_INTENT.md](../../docs/SCENE_INTENT.md) documents the full field contract,
versioning, warnings, structural versus semantic validation, and CLI. The example
is a restatement of the pack's hypothetical route with unmeasured clearance/time
requests, not a new implemented scene. It binds the supplied reference text notes;
no source videos were consumed or certified in this task. No builder/CLI adapter,
new mesh, scene generation, camera implementation or score mapping was added.

Verification:

- [a3-intent-tests-fixed.log](a3-intent-tests-fixed.log): **75 intent tests passed**.
  An initial test decorator typo caused collection failure and was corrected;
  [a3-intent-tests.log](a3-intent-tests.log) retains the failed attempt.
- [a3-intent-cli.log](a3-intent-cli.log): valid example reports
  `PLAN_VALID_NOT_PHYSICS_VALIDATED`, no warnings, `physics_validated:false`.
- [a3-final-tests.log](a3-final-tests.log): **503 passed, 4 subtests passed** across
  the full relevant Blender/scene/analytic/validation/media/MCP/intent/skill suite.
  This includes four directions tests added concurrently after the baseline.
- [a3-contracts.log](a3-contracts.log): Python contract conformance and **70
  TypeScript contract tests passed**.
- [a3-lint.log](a3-lint.log): scoped Ruff passed; `git diff --check` passed.

No unresolved task-introduced test failures. Live MCP inspection requires a
running addon; native physical calibration and human/perceptual gates retain
historical unresolved statuses. Plan validity does not approve physics or music.
A4 is pending its actual instructions; no A4 work was inferred from pack prose.
