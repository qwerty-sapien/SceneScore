# Music DAG node 04 handoff

Implementation is additive and candidate-ready. Final machine check and exact source evidence are recorded below and in `docs/requests/04/hero-checks.json`. Human A/B subgate remains `HUMAN-DECISION / AUDITION_PENDING`; approval is null. No new render or listening judgment was produced by node 04.

Worktree: `/private/tmp/scenescore-music-motion`. Coordinator-authorized ownership: append-only opt-in implementation in `modules/arranger/core.py`, new `modules/arranger/tests/test_music_vertical.py` and its fixture, this handoff and `docs/requests/04/`. The coordinator copied frozen node 02/03 dependencies and a reviewed Context role/playback dependency before implementation. The exact pre-04 core prefix is preserved (SHA-256 `1cea0b2eda18e8c3ccf240b43fa0d046dab759c490138f926fe7e1a44405f2f4`). Preserve the coordinator's later root Context.scene_inputs addition by integrating only the region starting `# Additive music vertical.`. No commit, merge, root overwrite, schema/lock edit or service/UI/audio change was made.

API: `compile_vertical_preview(ctx, *, geometry, policy=Policy(), seed=42, variation='base', mapping_config=None, brief=legacy_brief) -> dict`; `validate_vertical_result(result)` checks exact packet bindings without approval. Full signature, row shapes, preparation/transition obligations and hash convention are in `docs/requests/04/integration.md`.

Frozen 30-second/8-fps hero compilation produces 258 source events, 269 mapped events including 12 separate Foley events, and 179 control rows (159 causal approach-slot rows plus 20 other episode controls). Holds are [12.625, 13.25] and [17.875, 18.5] seconds. Three of 162 pitched source slots change identity/timing: 98.15% retained; one of 48 lead slots changes: 97.92% retained. No duplicated object melodies, no changed brush records, no event after the media end. All six observed hero semantic types map; collision and asymmetric rebound remain synthetic fixture-only. Tower-2 is an explicit manual focus and the existing causal world-Z function yields −2 at 18 s. No gesture direction was inferred from blink data.

Controls cover all eight types across portable analytic fixtures, including all eight within one second under the combined density cap. Rebound roles, negative equal-area case, retention velocity, register, grace identity and source-slot delay are checked. Near miss starts at the certified minimum, omits the current harmony third for a full beat, and adds no accent/Foley/key action. Missing inputs leave the source unchanged with a reason. Changes to a future minimum scalar cannot affect an identical earlier approach. Exact source and control provenance bind the new canonical draft plan. The old compiler/goldens are preserved.

Actual command history:

- Initial new suite (without its not-yet-written golden): 25 passed, one failed, one deselected, 91.58 s; session 60752 exited 1. A focused confirmation (session 48059 exit 1) identified the same issue: coincident contact articulation overrode rebound tenuto. Priority was corrected; this was one evidenced repair, not a changed gate.
- New suite after that repair/golden: 29 passed, 110.11 s; session 62230 exited 0. Later additions validate exact packet tampering and combined mapping refinements in the final full run below.
- Initial Ruff found one assigned lambda in the new test. It was replaced by a named helper. Final focused Ruff session 90894 exited 0; no lint rule or existing test changed.
- Read-only hero smoke session 11720 exited 0; final read-only candidate/hash evidence session 28430 exited 0. No file in the frozen source bundle changed. The final plan payload SHA-256 is recorded in `hero-checks.json`; file-preparation output belongs to the coordinator's separate CLI.

No server, browser, renderer, environment, container, process worker, network call, audio stream or detached job was started. Every bounded Python/Ruff session recorded here returned a final exit code. Full-wave root tests and browser/audio A/B evidence belong to the coordinator; human perception and approval remain pending.

Owned changed/new paths for integration:

- appended region of `modules/arranger/core.py`
- `modules/arranger/tests/test_music_vertical.py`
- `modules/arranger/tests/fixtures/music-vertical-v1.json`
- `docs/requests/04/integration.md`
- `docs/requests/04/hero-checks.json`
- `handoffs/music-04.md`

Final machine gate **GO**: `PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest modules/arranger/tests -q` completed **66 passed** (30 new vertical checks plus 36 existing), two existing dependency deprecation warnings, 127.47 s. The same bounded command then ran `/Users/agent/Desktop/SceneScore/.venv/bin/ruff check modules/arranger/core.py modules/arranger/tests/test_music_vertical.py` and `git diff --check`, both passed. Session 64837 returned **exit 0**. All node-04 command sessions are complete; no task-owned resource remains live. No final root/full-wave result is preclaimed.

Realization qualification requested by coordinator: critical near-miss third withholding and fixture-rebound grace/register/retention/anchor behavior are actual mapped ScoreEvents. Approach's implemented performance change is causal legato; its numeric ornament/tension/register intentions do not themselves add ornaments or pitch motion. Separation realizes detached articulation and attenuation, with its ornament/register intentions retained as sidecar data. Contact realizes staccato source slots and independent Foley; its accent scalar does not secretly alter velocity, and no pitched preset switch occurs from the timbre scalar. Full realized-versus-intention details are appended to the integration request. The browser must play the compiled events rather than assume all numeric controls are synthesis automation.
