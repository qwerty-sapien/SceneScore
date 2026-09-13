# 01 — motion semantics, including the asymmetric rebound

**Owns:** `modules/blender/geometry.py`, `modules/blender/summary.py`,
`modules/blender/tests/`. **Budget:** 60 minutes. **Reference:**
`examples/motion_event_taxonomy.json`.

`pair_timeline` already emits seven event types with swept-sphere contact detection and
per-segment tunnelling certification. Do not rewrite it. Extend it, and give the existing
output the fields the music side needs.

## Deliver

1. **Drivers on every event.** Each emitted event carries the normalized scalar its
   musical lane needs: closing rate for `approach`, `min_gap_m` and `closeness` for
   `near_miss`, opening rate for `separation`, `|normal_before|` for `contact_onset` and
   `collision`, `duration_s` for `contact_sustain`, `|normal_after|` for
   `contact_release`. Reference speeds and gaps come from the taxonomy defaults and are
   configurable, hashed, and recorded in provenance.

2. **Collision deduplication.** A swept `collision` within `contact_dedupe_s` (0.03 s) of a
   `contact_onset` for the same pair is one musical event. Keep the swept timestamp,
   record `method: "swept_sphere_exact"`, and drop the duplicate. Two accents for one
   visible impact is the defect this prevents.

3. **`asymmetric_rebound`**, exactly as specified in the taxonomy. Derived from a
   triggering `contact_onset` or `collision` plus `ObjectState` evaluated-mesh areas:
   requires `area_ratio >= 4.0`, a normal-velocity sign reversal, and both speeds above
   `rebound_min_speed_m_s`. Emits `rebounding_object_id` (smaller area),
   `anchor_object_id` (larger), `area_ratio`, `speed_retention` (null when the pre-contact
   speed is below the floor), `method: "evaluated_area_ratio_proxy"`,
   `mass_inferred: false`, `restitution_claimed: false`.

   This is a **module-versioned supplement**. It does not become a field on a canonical
   `InteractionEvent` without an integrator decision. Bump the module version and say so.

4. **Fixtures** covering each of the eight types, with at least one case per type that a
   downstream node can test against without running Blender.

## Tests

Analytic positive controls with independently known answers: a sphere pair that contacts,
a pair whose minimum gap stays positive (near miss), a pair at constant separation, a
tunnelling case the sweep must catch, a small-over-large rebound, a large-over-small
rebound (roles must swap correctly), an equal-area contact (must **not** emit a rebound),
and a rebound where the pre-contact normal speed is below the floor (`speed_retention`
must be null, not zero).

Negative controls: a rebound emitted with a null area must be rejected; a rebound without a
triggering contact must be rejected; area taken from object origin metadata rather than an
evaluated mesh must be rejected.

Do not let a test derive its expected trajectory from the same recipe it evaluates.

## Forbidden

Inferring impulse, force, mass, momentum, restitution or energy. Using screen-space size.
Using object-origin metadata instead of evaluated meshes. Emitting a rebound when either
area is null. Changing existing event onset semantics — downstream golden fixtures depend
on them.

## Done when

Eight types emit with drivers, the analytic controls pass, `make test` is green, and the
handoff states which of the eight the chosen demo scene actually produces.
