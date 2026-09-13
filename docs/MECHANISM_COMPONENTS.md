# Mechanism component library (A5)

`modules.blender.components` supplies reusable fixed geometry without importing
Blender. `component.build()` evaluates a numerical blueprint;
`component.build_blender()` explicitly constructs its separate collision and visual
objects when called inside Blender. Components expose entry/exit anchors, travel
direction, world bounds, geometry, parameters and feasibility constraints.

```python
from modules.blender.components import component_spec, create_component, Transform

ramp = create_component(component_spec(
    'high-ramp', 'Ramp', parameters={'length_m': 2.0, 'drop_m': 0.5},
    transform=Transform((0.0, 0.0, 3.0)), material_role='guide'))
print(ramp.entry_anchor.position_m, ramp.exit_anchor.position_m)
print(ramp.to_json())
```

The immutable `ComponentSpec` accepts exactly `component_id`, `type`, `transform`,
`entry_anchor`, `exit_anchor`, `parameters`, `collision`, `visual`, and
`material_role`. Parameters are named finite numbers; unknown parameters or types
fail. Defaults describe mechanism dimensions and are overrideable across scenes.
No camera, lighting, palette or music decisions are embedded in the mechanisms.

Transforms are rigid world-space metres and unit XYZW quaternions, with local +X
forward and +Z support normal. Scale/shear are unsupported. Anchor positions refer
to **sphere centers**, accounting for actor radius and inclined support normals.
Null spec anchors request computation; nonnull anchors assert local geometry and
must agree with it. Evaluated anchors and bounds are world-space. `travel_direction`
is the entry direction; curves and deflectors also expose the exit direction.

| Component | Geometry and feasibility scope |
| --- | --- |
| `Ramp` | Inclined floor and two guide walls |
| `StraightChannel` | Straight floor and guide walls, freely transformed in XYZ |
| `CurvedChannel` | 4–24 fixed box segments, either turn direction, explicit sagitta/clearance bound |
| `DropTransition` | Separated upper and lower ledges with an unsupported ballistic interval |
| `FixedDeflector` | Finite angled panel and deck; nominal elastic-reflection ports |
| `ClearancePost` | Fixed box post and a numerical surface-clearance hypothesis |
| `Catcher` | Open-entry tray with sides/end wall; exit anchor is an internal terminal target |
| `Platform` | Flat support with no lateral walls |
| `SupportFrame` | Four legs and top beams, structural attachment anchors |

ClearancePost requires external support or a ballistic solution, and SupportFrame
is not a travel surface. They cannot masquerade as connected route segments.
The DropTransition's speed estimate explicitly assumes an unrotated horizontal
launch with zero vertical speed. The deflector direction is a geometric initial
hypothesis; actual material response and landing/retention require solving.

Every collision part is a simple fixed OBB. Curves are unions of boxes, not convex
hulls over concave passages. The Blender adapter builds passive BOX bodies with
zero extra collision margin, hidden from rendering. Separate visual meshes have no
rigid bodies and may receive bounded bevels and caller-supplied materials by role.
The blueprint exposes bevel discrepancy (`sqrt(3) * bevel_m`) and curved-route
approximation bounds. Arbitrary beauty meshes cannot become collision geometry.

Connections use an explicit serialized `ConnectionPolicy`. Reports include:

- Exit-to-entry distance, which must be strictly below tolerance.
- Direction mismatch in degrees and allowed angle.
- Available versus required sphere-radius clearance, including declared margin.
- Height change and necessary lossless entry-speed bound.
- Every cross-component OBB penetration depth and bounded joint-weld classification.
- Minimum sphere surface gap over the line between anchors.

Static welds default to forbidden. When explicitly allowed, both penetration depth
and the conservative intersection-region radius must fit the policy. This allows
faceted guide joins while continuing to reject sphere penetration at the seam.
Nonadjacent component intersections fail and cannot borrow a joint allowance.
Frame/platform attachment therefore needs touching surfaces, not overlapping solids.
A geometric connection pass establishes necessary conditions only; it does not
prove passage at speed, support continuity during a drop, or a desired event.

`assemble_route()` requires one nonbranching connected start-to-Catcher chain of
all travel components. Auxiliary structural/clearance components may be included.
IDs are unique, all sphere radii agree, and the entire scene stays within the
existing analytic backend's 128-box limit. `analytic_obstacles()` returns the exact
fields accepted by `simulate_sphere`, preserving component/part identity.

```sh
.venv/bin/python -m modules.blender.components \
  modules/blender/fixtures/component-route.example.json \
  --out /private/tmp/scenescore-component-route.json
```

The fixture is a high ramp, inclined approach, curved redirection, depth channel
and lower catcher spanning all three world axes. The descending channel bends
out of the first guide plane by 8.59 degrees. Sphere-center extents are approximately
4.33 × 4.34 × 1.51 m. The arc entry permits 0.06 m of static weld overlap and the
descending transition permits 0.08 m, each inside a 0.6 m joint region; measured
maxima are approximately 0.0392 and 0.0730 m. Sphere seam gaps remain zero within
arithmetic precision. This is
an assembly fixture, not a solved or rendered animation.

For A4 integration, use `assemble_resolved(resolved_constraints, layout)` or add
`--resolved PATH` to the CLI. It revalidates A4 integrity, matches every declared
fixed collision actor to component IDs, checks radius/start/terminal consistency
and world anchor positions, and returns analytic obstacles, collider-to-actor
mapping, initial/terminal states and still-unmeasured event constraints. Additional
collision geometry requires a corresponding actor declaration in the intent.
CLI outputs require a new file and include numerical rejection reports on failure.

The optional Blender smoke runner starts a fresh factory process with autoexec
disabled, two threads and a bounded timeout. It constructs one of every component,
checks world corners against host geometry, separates beauty/collision objects,
preserves preexisting objects, rejects duplicate component names, saves a `.blend`
and records source/artifact hashes. It records and verifies process-group cleanup.

```sh
.venv/bin/python tools/component_library_smoke.py \
  --out /private/tmp/scenescore-component-smoke \
  --receipt /private/tmp/scenescore-component-smoke-run.json --timeout 120
```

The library never clears a scene, generates a trajectory, renders, activates a
production selection or grants approval. The smoke establishes construction only.
