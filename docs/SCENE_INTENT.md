# Scene intent supplement, version 2

`modules.blender.scene_intent.SceneIntent` is a typed, immutable authoring plan.
It does not build meshes, simulate, invoke MCP, render, choose an active scene,
map a score or confer approval. All times and clearances in its example are
unmeasured targets. It remains separate from frozen canonical contract 0.1 and
measured `InteractionEvent` records.

The pack's `scene-intent-1` JSON and linter remain intact. Version 2 adds required
route, mechanics, persistent voice, clearance, camera, reference and music fields.
Version 1 is rejected at this boundary: converting it requires deliberately
specifying those fields, not filling them with inferred physical evidence. The
new example restates the supplied hypothetical offset-chute brief; there is no
new recipe, geometry, parameter solution or production adapter.

```python
from pathlib import Path
from modules.blender.scene_intent import SceneIntent

intent = SceneIntent.from_json(
    Path('modules/blender/fixtures/scene-intent-2.example.json').read_text()
)
assert SceneIntent.from_json(intent.to_json()) == intent
warnings = intent.validation_warnings()
```

Use `from_dict` / `from_json` at input boundaries. `to_dict` / `to_json` also
validate directly constructed dataclasses. Unknown fields, missing fields,
unknown enum values, duplicate JSON keys, non-finite numbers and boolean-as-number
coercion fail with `IntentValidationError`. Tuples preserve explicit ordering and
immutable nested records. JSON emits arrays, numeric SI values and explicit nulls.

| Field | Meaning and constraints |
|---|---|
| `clock`, `duration_s` | Scene seconds from declared start, 0–30 s duration. Windows are approximate half-open `[start_s,end_s)` intervals, never observed event times or uncertainty estimates. |
| `actors` | Persistent IDs, physical role, shape, motion, collision participation and distinct sonic identities. Unscored objects have null voice IDs; silent supports cannot own voices. |
| `mechanics` | Backend/model version, supported scope, gravity in m/s², contact/material/actuation models and limitations. Analytic scope allows exactly one dynamic colliding sphere and fixed OBB colliders. Native Bullet warns that fresh calibration is required; other explicit models warn that implementation is missing. Textual models still need numerical parameterization before any future builder. |
| `route_stages` | Ordered, contiguous stages cover the full duration. Each declares participants, entry/exit intent and a causal mechanism. This version describes one ordered route; branching or concurrent route scheduling needs a new version. |
| `support_contacts` | Continuous physical support retained in raw evidence, separate from salient events. Participants/stages/windows must resolve; support does not consume salient-event count or duty cycle. |
| `events`, `event_order` | One primary kind, explicit participants, stage, approximate target window, physical cause and falsifiable measurement requirement. `event_order` names every event exactly once. Reversed/overlapping/infeasible timing is rejected. Events are all proposed salient beats; observed incidental impacts cannot later be hidden by this plan. |
| `clearance` | Required only for near misses: positive `minimum_m`/`maximum_m` signed surface-gap range, optional `target_m` inside it. A zero/negative gap, target outside range, or simultaneous same-pair support contact contradicts a near miss. Later measurement must establish approach, positive gap, separation and uncertainty. |
| `salience_policy` | Chosen minimum spacing, maximum count, minimum kind diversity and duty cycle; this version allows one simultaneous salient event. These are authoring policies, not changes to frozen physical thresholds. |
| `camera`, `ending` | Intended focus and coverage of every event, framing, supported ending through the endpoint and no teleport reset. Allowing an offscreen ending emits a warning. These declarations do not prove visibility or support. |
| `reference_lessons` | Source, status, lesson, evidence note, optional exact source hash and consumed media interval. Missing/unbound references warn; an implementation exemplar requires a hash. The example binds supplied text notes, not freshly viewed reference videos. |
| `music_hints` | Proposals tied to scored actors and optional matching events. Exact approval remains required downstream. Impact Foley needs a contact event and scene-time onset; a near miss cannot request impact Foley. No live music or blink behavior changes. |

Supported event definitions: acceleration, deceleration and settle each have one
participant; collision, bounce, graze, near miss, release and merge each name two.
Merge is rejected by current rigid-body scopes. An `other_explicit` adhesion/model
study may describe it with an explicit unimplemented-model warning. Unknown kinds
are rejected. Continuous support is never accepted as a salient event kind.

Run the complete semantic validator:

```sh
.venv/bin/python -m modules.blender.scene_intent modules/blender/fixtures/scene-intent-2.example.json
.venv/bin/python -m modules.blender.scene_intent --schema
.venv/bin/python -m pytest -q modules/blender/tests/test_scene_intent.py
```

A valid plan reports `PLAN_VALID_NOT_PHYSICS_VALIDATED`, its warnings, and
`physics_validated:false`. Invalid plans exit 1. The checked-in JSON Schema at
`modules/blender/fixtures/scene-intent-2.schema.json` is generated from the same
types and tested for drift; it validates structure only. Cross-reference, timing,
mechanics-scope and salience rules require the Python validator. Passing either
validator cannot unlock an existing production gate. A future adapter must be
explicitly implemented and separately validated before consuming these targets.
