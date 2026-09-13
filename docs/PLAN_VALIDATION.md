# Scene plan validation (A4)

The authoring gate takes `scene-feasibility-plan-1` JSON or YAML and produces
`plan_validation.json` plus `resolved_constraints.json`. A pass means the requested
plan is coherent within the declared scope. It does not establish that a trajectory,
render, music arrangement or human approval exists. Canonical contract 0.1 and the
production validation thresholds remain unchanged.

```sh
.venv/bin/python -m modules.blender.planning \
  modules/blender/fixtures/scene-feasibility-plan.example.json \
  --out /private/tmp/scenescore-plan-example
```

Choose a new output directory. Invalid input produces a failed report and blocked
constraints; previous outputs are never overwritten. JSON duplicate keys, YAML
aliases/duplicate keys/unsafe tags, nonfinite numbers and inputs over 1 MB fail.
PyYAML is an existing development dependency; JSON needs no YAML dependency.

The versioned wrapper contains the existing typed `scene-intent-2` as `intent`,
plus `motion_contract`, numerical `route` states and measurable `events`.
See [the full example](../modules/blender/fixtures/scene-feasibility-plan.example.json)
and [JSON Schema](../modules/blender/fixtures/scene-feasibility-plan.schema.json).
The older abstract intent alone is intentionally insufficient for this gate.

| Field | Meaning |
| --- | --- |
| `intent` | A3 actors, route stages, mechanics, ordering/windows, support contacts, camera, ending, reference lessons and music hints |
| `motion_contract` | Sphere radius, physical coefficients, analytic solver provenance, replay policy and explicit absence of teleportation/control overrides |
| `route.start` | Actor, fixed support, sphere-center position and velocity, in world metres and m/s |
| `route.stages` | Ordered stage IDs and world-space position hints; these are proposed positions, not measured trajectories |
| `route.terminal` | Actor, fixed catch support, sphere-center position and maximum ending speed |
| `events` | One numerical contract per abstract salient event, with all nine required keys |

Every event declares `id`, `type`, `actor`, `target`, `after`, `time_window`,
`success_condition`, `failure_conditions` and `music_salience`. `target` may be
null for a unary acceleration/deceleration/release. `after` may be null, an ID or
an ID list. It must agree with the A3 total order. Windows use scene seconds and
refine the abstract stage/event windows; adjacent windows must satisfy the declared
sparse gap and duty policy. Unordered or overlapping abstract plans fail first.

| Event type | Required success condition |
| --- | --- |
| `acceleration_phase` | Positive `speed_gain_min` in m/s |
| `deceleration_phase` | Positive `speed_loss_min` in m/s |
| `salient_collision` | `target_contact: true`; optional positive `heading_change_min_deg` up to 180 |
| `near_miss` | Positive ordered `surface_clearance_m: {min, max}` in metres |
| `release` | `support_released: true` |
| `supported_catch` | Contact, nonnegative `speed_max_m_s`, positive `supported_duration_min_s` that fits the window |

A3's unary `settle` becomes a `supported_catch` whose target resolves from the
terminal support. Collision, bounce and graze remain one collision episode.
A near miss compiles into minimum surface-clearance bounds, no contact throughout
the window, and bracketed approach/separation. Pixels cannot satisfy it.

Each failure list must include `success_condition_not_met`, `missed_time_window`
and `unphysical_motion`. Optional `wrong_target` and `unexpected_contact` add
falsification predicates. Resolved events expose explicit metric/operator/value/unit
predicates, time windows and stable actor/target IDs. Every measurement starts
`NOT_MEASURED`; events emit once per episode. Continuous rolling support is retained
in `continuous_support` and cannot become repeated salient collisions or per-sample
notes. Near misses never become impact Foley.

Only `fixed-obb-sphere-mechanics-1`, one dynamic sphere, world-Z gravity
`[0, 0, -9.81]`, fixed collision targets, and solver-derived motion are accepted.
Two dynamic actors, native/moving-contact mechanisms, soft-body/fluid models,
manual post-release keyframes, teleportation and control overrides fail explicitly.
Conservative lossless energy and travel-time bounds reject obviously unreachable
heights, speed gains or deadlines; passing these necessary bounds is not a solver.

The report answers six questions about ordering, backend support, sparse spacing,
measurement criteria, defined route states and downstream music suitability.
Structural failures leave dependent answers `NOT_EVALUATED`. Warnings include
nearly planar routes, clustered event locations, uniform spacing, weak endings and
incomplete camera coverage. Camera omissions are warnings even when A3 alone would
reject them; unknown camera references still fail. Thresholds are exposed in the
report as authoring heuristics, separate from frozen production thresholds.

Before consuming saved constraints, call
`modules.blender.planning.verify_resolved(document)`. It recomputes validation from
the bound source and requires exact agreement, detecting stale or edited artifacts.
The hash is an integrity binding, not authentication or human approval.
[The component library](MECHANISM_COMPONENTS.md) can bind these constraints to a
serialized layout. Parameter solving, independent contact/physics checks, fresh
replay, full-motion/camera review and exact human approval remain later gates.
