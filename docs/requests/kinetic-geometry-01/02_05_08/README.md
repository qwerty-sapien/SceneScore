# Kinetic Geometry — 02 / 05 / 08 authoring cards

Status: DESIGN_INTENT_NOT_MEASURED. These are deterministic source plans, not simulated, validated, rendered, reviewed, or approved media. SI units; scene time begins at frame zero; 30 fps; 16:9.

## Scope

All three briefs require dynamic convex non-spheres and/or coupled dynamic bodies. They use native_bullet intent because the available analytic route planner only supports one sphere against fixed OBBs. Native Bullet calibration is historically failed: 32.570 mm versus a 5 mm transfer/convergence limit and 0.163740 m/s versus a 0.1 m/s outgoing-relative-speed limit. These cards do not repair, waive, or reinterpret that failure.

The scene-intent-2 JSON files are authoring inputs and must warn NATIVE_CALIBRATION_REQUIRED. The companion cards supply positions, dimensions, coefficients and falsifiers outside that schema. Do not prescribe post-release transforms. A prescribed latch is only a visible actuator with a recorded causal release state.

| Recipe | Duration / seed | Candidate | Ending |
| --- | --- | --- | --- |
| 02_cube_rebound | 9.60 s / 2026091302 | Dynamic cube + three static offset slabs | One supported cube in lower catcher. |
| 05_tumbling_tetrahedron | 10.40 s / 2026091305 | Convex tetrahedron + isolated slopes + three-rail slot | Tetrahedron visible and canted in matching slot. |
| 08_cube_cascade | 11.20 s / 2026091308 | Three dynamic cuboids + static routes + two visible latches | Three cubes at distinct separate catches. |

## Construction/evidence requirements

- Separate visual mesh from primitive/convex collision geometry. The tetra slot is three rails, never a concave passage represented by a convex hull.
- Use a new candidate directory; bake monotonically. Seed may vary palette/bounded layout only, never a solved event.
- Extract evaluated state/contact/gap at 240 Hz on the same seconds clock as 30 fps playback and compare a finer solver candidate. A beauty render does not prove an impact, gap, roll or rotation.
- Each card's three event windows are sparse music-facing episodes. Support/travel/settling remains raw evidence; near misses receive no impact Foley and all score response needs exact approval.

No recipe is physically plausible or render-ready until fresh applicable calibration, independent candidate checks, replay, and native-rate visual review pass.
