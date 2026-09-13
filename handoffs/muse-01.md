# Muse nodes 01 and thin 06 handoff

Base `527f949`; isolated worktree `/private/tmp/scenescore-muse-runtime`, branch
`codex/muse-runtime`. No commits or merges made. No task-owned persistent jobs
started. Root schemas, grammar/config, locks, shell, music policy and audio
implementation are unchanged.

Implemented the runtime's canonical action adapter, explicit affine clock
mapping, fault/warmup/rearm gates, bounded duplicate caches, versioned semantic
envelope and receipt/latency helpers. Runtime supplies no signed direction and
does no I/O, inference, approval creation or music scheduling. The browser
integrator still owns the real common dispatch path and music receipt stamps.

Validation commands actually run from the worktree:

```text
PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest modules/muse/runtime/tests modules/muse/evaluation/tests modules/muse/baseline/tests -q
node --import tsx --test tests/ts/muse-dispatch.test.ts
node_modules/.bin/tsc --noEmit
/Users/agent/Desktop/SceneScore/.venv/bin/ruff check modules/muse/runtime modules/muse/evaluation/latency.py
```

Focused Python run: 41 passed. TypeScript conformance/four-source Timeline run:
5 passed. Typecheck passed. Ruff initially found one unused test import, removed
before final recheck. An initial closure-boundary assertion incorrectly expected
no emission for an independent blink *after* the exclusion window; corrected the
test to match the preserved strict repository rule, then 41 tests passed.

Evidence paths: `modules/muse/runtime/tests/control-envelope.json`,
`modules/muse/evaluation/grammar-audit-v1.json`,
`modules/muse/evaluation/grammar-semantics-v1.json`, and
`modules/muse/evaluation/pack-reference-check-v1.json`. The original prompt-pack
checker was run using `python examples/check_pack_examples.py` on a byte-identical
temporary copy: 14/14 own-reference cases and 6/6 negative mutations passed.
Runtime agrees with only 11/14 original pack expectations, for the three
documented onset-vs-end semantics conflicts. All 14 repository expectations and
the separately versioned 14 corrected cases pass. Immutable pack unchanged.

Not run/blocked: live Muse acquisition, real participant training, held-out real
accuracy, physical audio loopback, human approval/audition and browser deployed
integration. The four-source tests use visibly synthetic fixture identities,
including the real_device branch. They establish software gate equivalence only.
Runtime status is PIPELINE_TESTED_ONLY; this is not product readiness.

Owned files to integrate:

- `modules/muse/runtime/{__init__.py,adapter.py,clock.py,dispatch.py,README.md}`
- `modules/muse/runtime/tests/{test_runtime.py,control-envelope.json}`
- `modules/muse/evaluation/{latency.py,grammar-audit-v1.json,grammar-semantics-v1.json,pack-reference-check-v1.json}`
- `tests/ts/muse-dispatch.test.ts`
- `docs/requests/muse-01/001-seam-and-pack-discrepancies.md`
- `handoffs/muse-01.md`

The temporary root `node_modules` symlink was used only for inherited locked
dependencies and removed after checks. No dependency installation or live jobs.
