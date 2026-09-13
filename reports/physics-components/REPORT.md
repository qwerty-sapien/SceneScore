# A4–A5 implementation report

A4 and A5 pass their authoring/construction gates. The final focused suite passes
**166 tests** (45 plan-validator, 46 component, 75 existing intent tests). The wider
Blender/geometry/scene-generation/analytic-mechanics/validation/MCP regression run
passes **624 tests plus 4 subtests**. That wider run preceded the last reference
propagation, descending fixture and contact-onset guards; the affected authoring
suite was rerun afterwards. Python contract validation, all **70 TypeScript
contract tests**, scoped Ruff and scoped `git diff --check` pass.

Blender **5.2.1 LTS** constructed all **9 component types**, with **50 passive BOX
colliders and 50 separate visual meshes**. World-corner error was at most
**8.92e-7 m** against a 1e-5 m smoke tolerance. Existing factory objects remained
present. The final process exited in about 1.49 seconds, within its 120-second,
two-thread budget; its process group is absent. Final component source hashes
match the smoke receipt. No render or full-route simulation was performed.

| Deliverable | Evidence |
| --- | --- |
| A4 behavior and usage | [Plan validation documentation](../../docs/PLAN_VALIDATION.md), [A4 report](A4.md) |
| Passing paired outputs | [plan_validation.json](valid-plan-final/plan_validation.json), [resolved_constraints.json](valid-plan-final/resolved_constraints.json) |
| Rejected missing clearance | [Failure report](invalid-plan/plan_validation.json), [blocked constraints](invalid-plan/resolved_constraints.json) |
| A5 components and connections | [Component documentation](../../docs/MECHANISM_COMPONENTS.md), [A5 report](A5.md), [assembled geometry](assembled-route.json) |
| Final Blender artifact | [Editable component smoke scene](../../artifacts/blender/component-library-a5-final-20260913/components.blend), [smoke measurements](../../artifacts/blender/component-library-a5-final-20260913/smoke.json) |
| Tests and cleanup | [Regression log](regression.log), [final focused log](authoring-final-guards.log), [contracts](contracts.log), [final lint](lint-guards.log), [teardown](teardown.json) |

Changes are confined to 25 authoring/library/test/fixture/documentation files plus
this report/evidence directory and the two bounded smoke artifact directories.
The [manifest](task-files.json) records exact paths and hashes. Relative to the
A4 starting snapshot, all 25 implementation/documentation files are additions.
Some appeared as tracked modifications later because another task committed the
shared working tree during this work. No commit, reset, stash, merge or global
settings change was performed by this task.

The [baseline](baseline.json) captured HEAD
`555f112181352ccb7556275ed4fbe50120a90990` and dirty/untracked user work before A4.
The [preservation check](preservation.json) finds **108 of 109** captured source
hashes unchanged, no missing files, and only the concurrently edited directions
driver changed. The exporter, A3 schema/module, existing mechanics and physical
validator, both animation skills, and MCP configuration are unchanged by A4–A5.
Unrelated ongoing Muse/training/directions edits are preserved and excluded from
this task's change summary. Earlier A0–A3 evidence remains under
[physics-aware-animation](../physics-aware-animation/REPORT.md).

New failures during development are retained: an initial test-collection typo,
a catch fixture violating A3 timing/arity/ending rules, and the resulting missing
unary-settle-to-terminal-support adaptation. These were corrected; final focused
checks pass. The negative CLI intentionally returns exit 1 for an unmeasurable
near miss. One banked-route experiment remained planar, and a descending join was
rejected under its original weld bound; both geometric checks are retained. The
final example declares the descending joint's measured static weld explicitly,
while sphere-penetration checks remain strict. No existing production tolerance
was changed. The earlier `valid-plan/` output predates the final guard/constraint
fields; use `valid-plan-final/` for current consumption.

Passing intent validation and constructing fixed components do not certify a
physical trajectory, event timing, visual quality, score audition or approval.
Those remain explicit later gates; generated outputs carry `physics_validated:
false` and no approval. No production scene selection or generation backend was
redesigned. No task-owned persistent job or container remains active.
