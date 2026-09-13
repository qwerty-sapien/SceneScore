# A1 skill-pack merge

PASS: 388 tests and 4 subtests passed after integration, including all 358 baseline
tests, 18 supplied plan tests and 12 supplied MCP guard tests. The example linter
returned `PLAN_VALID_NOT_PHYSICS_VALIDATED`. See [a1-tests.log](a1-tests.log) and
[a1-plan-linter.log](a1-plan-linter.log). No baseline test regressed.

All 19 files were read before integration; archive paths and file types were
checked before temporary extraction. All 18 entries in the supplied manifest
match their SHA-256. [a1-pack-inventory.json](a1-pack-inventory.json) records the
archive digest, temporary directory and every file digest.

Added without overwriting anything:

- `.agents/skills/physics-aware-animation/SKILL.md`
- Its `assets/scene-intent.example.json`, three `references/` documents,
  `scripts/check_story_plan.py` and `tests/test_check_story_plan.py` (7 skill files).
- `docs/requests/blender-skill-repair.md` as a proposed future brief, subject to the
  current A0–A3 scope; it does not authorize scene building or backend repairs.
- `tools/blender_mcp/response_guard.py` and `test_response_guard.py`, initially
  byte-identical, unwired helpers. A2 will strengthen and integrate them.

Existing files changed in A1: none. Existing exporter skill preserved byte-for-byte.
No merge conflicts or newer-file replacements. The original `scene-intent-1`
example is a design linter input, not a renderer input or the forthcoming typed
schema. A3 will use a separately versioned supplement rather than changing it.

Supplied files deliberately not merged:

| Files | Reason |
|---|---|
| `README.md`, `MANIFEST.json` | Pack metadata; retained in original ZIP and temporary extraction, not replacements for repository root documents. |
| `evidence/NEW_CHECKS.md`, `SOURCE_EXCERPTS.md`, `existing-scoped-tests.log`, `mcp-guard-tests.log`, `reference_metadata.json`, `story-tests.log` | Historical uploaded-archive audit; not fresh local evidence. Reference notes explicitly identify their source as pack evidence. The current local artifact inventory supersedes its missing-artifacts observation. |
| `patches/mcp_client_result_handling.patch` | Inspected individually but not blindly applied: it misses embedded traceback/exception text and continues mutations after failures. A2 manually adapts response recording/exit propagation against the current client. |

The supplied helper recognizes flag/prefix/JSON failures, rejects empty content
and expects images for screenshots. A2 must add nested execution-error detection,
explicit empty-output semantics and client-level failure tests before using it.
The supplied linter lacks typed route/camera/reference/music fields and numerical
near-miss clearance; A3 addresses those separately. No new scene was implemented.
