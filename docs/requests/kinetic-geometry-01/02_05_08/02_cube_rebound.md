# 02 — Cube rebound

Identity: 02_cube_rebound; seed 2026091302; 9.60 s; 30 fps; 16:9. Hero cube-a is a 0.80 m ash-blue matte-plastic cube: mass 2.40 kg; restitution 0.42; dynamic/static friction 0.48/0.52; linear/angular damping 0.015/0.040 s⁻¹; gravity [0,0,-9.81] m/s². Release at (-2.55,-1.25,6.05) m from zero linear/angular velocity. First contact earns spin; no post-release impulse or rotation key.

## Actors and spatial build

| ID / role | Collision geometry in metres | Visual treatment |
| --- | --- | --- |
| cube-a / scored dynamic hero, voice:cube-a | Convex 0.80 m cube. | Roughness 0.42, 18 mm visual bevel, one darker face marker. |
| slab-1 / silent fixed support | Center (-1.25,-0.45,3.75); 2.60×1.45×0.18; downhill (+.966,+.145,-.215). | Light concrete, brass under-frame. |
| slab-2 / silent fixed support | Center (1.05,.70,2.42); 2.20×1.25×0.18; downhill (+.590,-.690,-.420). | Pale ceramic, thin black frame. |
| slab-3 / interaction surface | Center (-.10,1.88,1.08); 1.75×1.10×0.18; downhill (+.720,+.430,-.545). | Green anodized metal, 10 mm visual bevel. |
| catcher / silent fixed support | Tray at (2.10,2.55,.38): 1.70×1.45 floor, 0.18 side lips, 0.28 end stop. | Off-white ceramic. |

Slabs alternate X/Y and retain ≥0.55 m open air between outlines: not a staircase. Dark floor is 0.25 m below catcher and nonparticipating. Use upper-left key, camera-right fill and rim light for depth. Camera is static at (9.2,-11.0,7.0) m toward (0,.75,2.55), 55 mm-equivalent. At most a 0.35 m push during 0–5.5 s; no contact-hiding cut/move. Keep catcher in endpoint frame.

## Three salient windows

| Window | Cause / target | Falsifier |
| --- | --- | --- |
| 1.05–1.38 s, broad-face-rebound | Free fall hits slab-1 broad-face-first, redirects toward +X/+Y, and begins visible tumble. | Wrong pair; contact ≤0.12 m from edge/corner; no positive outgoing Z velocity; transform-driven exit. |
| 3.34–3.72 s, edge-biased-rebound | Rotating cube meets slab-2 edge-first and changes heading ≥25° into depth. | No new onset; contact >0.12 m from every edge; <25° heading change; extra slab contact in preceding gap. |
| 5.86–6.28 s, corner-rebound | Corner-biased bounce on slab-3 feeds catcher. A fixed 35 mm rail-tip may supply visible pre-contact edge graze only. | No new onset; contact >0.12 m from every corner; rail-tip tunnels/penetrates; unintended overlapping collision. |

Rail-tip graze is within window 3, not another musical beat: 0.18–0.45 s before corner contact and certified 0.015–0.045 m positive gap. Integrated orientation must total 2.0–4.0 turns; reject less/more or any cosmetic spin key.

## Ending and candidate gate

From 6.3 s use gravity/contact into catcher. In 8.35–9.60 s remain visibly supported with endpoint speed <0.08 m/s and angular speed <0.18 rad/s; no early sleep/freeze. End with an off-axis cube fully visible.

This cube is outside analytic sphere scope. Promotion needs cube-on-slab 30/60/120-substep convergence, independent face/edge/corner classification, fresh-process replay and native-rate full-motion/camera review. Failure remains unvalidated; do not loosen a tolerance or reset a coefficient.
