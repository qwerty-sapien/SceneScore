# SceneScore A0–A3 result

A0, A1, A2 and A3 PASS their scoped gates. A4 is pending because its instructions
were not supplied. No new scene or physical-backend repair was implemented.

| Node | Result and evidence |
|---|---|
| A0 | [Baseline](A0-BASELINE.md): 358 existing tests passed; actual Blender evaluated-geometry fixture passed with host access. Sandbox startup crashes and unavailable MCP addon are recorded separately. |
| A1 | [Merge report](A1-MERGE.md): all 19 supplied files inspected, 18 manifest hashes verified, 10 new files selectively merged. Seven skill files and the exporter skill remain byte-identical. 388 tests plus 4 subtests passed. |
| A2 | [Portability/error handling](A2-MCP.md): portable repository launcher and executable discovery; flags and embedded execution errors now fail tasks. 424 tests plus 4 subtests passed; 48 final focused tooling checks passed. Real MCP returned an unavailable-addon error and correctly produced exit 1. |
| A3 | [Intent schema](A3-INTENT.md): typed version-2 authoring supplement, example, JSON Schema, semantic validation and 75 focused tests. Complete final relevant suite: 503 tests plus 4 subtests passed. Python contracts, 70 TypeScript contract tests and scoped lint passed. |

The initial checkout was dirty at `a397f3f4975e82374bacbf70302eda6c92621f28`.
During execution another process advanced HEAD to
`555f112181352ccb7556275ed4fbe50120a90990`, committing the earlier A0–A2 work
alongside user diagnostics and directions work. This task did not stage, commit,
reset, stash, check out or revert anything. A plain `git diff` therefore omits
some completed work; [task-files.json](task-files.json) lists the 32 task-owned
code/documentation/skill paths and their hashes relative to the original baseline.

[Preservation record](final-preservation.json): 23 of 25 initially protected paths
are unchanged, including the original ZIP and exporter skill. The other two are
concurrent updates to `docs/decisions/0012-animation-directions-06-08-18.md` and
`reports/muse-training/diagnostics-verification.json`, neither edited by this task.
The initial tracked user diff remains in [a0-user.patch](a0-user.patch). Later
unrelated directions sources/tests/reports were preserved. No user changes were
overwritten by this task.

Current limitations are explicit: no live Blender addon, historical native
calibration still unresolved, no new simulation/render, no full-motion review or
human music/visual approval. Intermediate fixture/test failures were fixed and
retained in logs; lint findings in concurrent directions work were not modified.
The scene-intent supplement is not a renderer input and cannot bypass any gate.

[Teardown](teardown.json): all 19 recorded bounded job groups were verified absent.
MCP adapters exited; no task-owned persistent server, GUI, container or worker
remains. The temporary pack extraction path is in [its inventory](a1-pack-inventory.json).
