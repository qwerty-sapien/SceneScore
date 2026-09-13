# 05 — Tumbling tetrahedron

Identity: 05_tumbling_tetrahedron; seed 2026091305; 10.40 s; 30 fps; 16:9. Hero tetra-a is a regular 0.95 m-side convex tetrahedron: mass 1.65 kg; ochre ceramic with 12 mm black edge strips; restitution 0.34; dynamic/static friction 0.40/0.44; linear/angular damping 0.012/0.025 s⁻¹; gravity [0,0,-9.81] m/s². Release from rest at (-2.80,-1.45,5.15) m. Rotation arises only from asymmetric contacts/gravity.

## Actors, route and shot

| ID / role | Collision geometry in metres | Look |
| --- | --- | --- |
| tetra-a / scored dynamic hero, voice:tetra-a | Actual four-vertex convex hull, never sphere/box proxy. | Ochre ceramic, dark edge inlays, vertex cap. |
| incline-a / silent fixed support | Isolated 2.10×1.20×0.18 slab at (-1.55,-.72,3.75); downhill (+.780,+.260,-.570). | Limestone / walnut frame. |
| incline-b / interaction surface | Isolated 1.70×1.10×0.18 slab at (.18,.72,2.24); downhill (+.360,-.785,-.505). | Graphite stone / brass edge. |
| launch-lip / silent fixed support | 0.72 m hard edge at (1.10,1.05,1.78), fixed to incline-b. | Exposed graphite termination; no motor/impulse. |
| tetra-slot / silent fixed support | Three separate 0.12 m rails form pocket at (2.22,1.92,.56): 1.08 m inner side, 0.055 m radial clearance, 0.26 m base. | Pale stone recess; no hull shortcut over open slot. |

Keep ≥0.65 m air between inclines. Plinth/floor establishes scale but is excluded from contacts. Camera follows down from (8.8,-10.8,7.4) to (7.8,-9.8,5.9), 50 mm-equivalent, only through 7.2 s, then holds slot/end. Flight silhouette reads on clean dark background.

## Three salient windows

| Window | Cause / target | Falsifier |
| --- | --- | --- |
| 1.10–1.46 s, vertex-contact | A vertex reaches incline-a first and its normal begins irregular tumble. | Initial overlap; first contact >0.10 m from every vertex; no tumble; keyed state. |
| 3.14–3.58 s, edge-contact | Different edge meets incline-b, changes heading ≥20°, and launches over exposed lip. | Vertex repeats; no onset; <20° change; hidden energy source. |
| 7.62–8.18 s, slot-capture | Fully unsupported 5.20–7.10 s flight carries 1.25–1.90 turns, enters open slot and is captured by rails. | Any flight support/contact; rotation outside bound; opening blocked; snap/penetration/early sleep. |

At slot require measured path within open triangular prism, then two rails plus base support for ≥0.80 s. It must never parent/constraint-handoff.

## Ending and candidate gate

Dissipate naturally in 8.18–10.40 s. Endpoint: fully visible, centre ≥0.12 m above base, supported, speed <0.07 m/s, angular speed <0.16 rad/s, canted within matching negative space.

Convex tetra contacts and concave receiver exceed analytic model. Future evidence: tetra-on-slope convergence, rail-slot capture plus obstruction negative, independent vertex/edge classification, fresh-process replay, native-rate review. Coefficients are design inputs, not calibration evidence.
