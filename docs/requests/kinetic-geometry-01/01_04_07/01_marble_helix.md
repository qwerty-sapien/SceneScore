# 01 — Marble Helix: authoring source plan

`status: DESIGN_INTENT_NOT_MEASURED` · `id: 01_marble_helix` · `seed: 101947` · `duration_s: 10.4` · `clock: scene_seconds_zero_at_start` · `render: 9:16, 30 fps (proxy 540×960; final 1080×1920)`

This is a recipe-authoring supplement, not a bake, validation report, or render claim. It transfers only the layered, exposed-route lesson recorded in `.agents/skills/physics-aware-animation/references/EXEMPLARS.md`; it does not reconstruct either supplied video.

## Declared mechanics

- **Model:** `native_bullet`, proposed model version `native-bullet-sphere-kinematic-rotor-1` at 240 Hz. The polished marble is one dynamic rigid sphere; the rail, 14-facet fixed bowl proxy, and supports are passive collision geometry. The yellow paddle is a visibly motor-supported kinematic actuator and must retain a time-sampled collision proxy for the clearance calculation.
- **Scope boundary:** this is deliberately outside A4's `fixed-obb-sphere-mechanics-1`: that scope cannot certify a moving paddle. Candidate-specific native calibration, the marble/paddle swept-gap sampler, replay, and a full-motion review are required before a pass may be reported. Do not call a collision-disabled decorative paddle a certified near miss.
- **World/solver:** gravity `(0, 0, -9.81) m/s²`; Bullet candidate substeps `50`, solver iterations `20`, collision margin `0.0015 m`; use a separate 100-substep comparison only as a convergence measurement, not an automatic repair.
- **Materials/mechanics:** marble `radius 0.160 m`, `mass 0.45 kg`, friction `0.34`, restitution `0.00`, angular damping `0.055 s⁻¹`; rail/bowl friction `0.43`, restitution `0.00`; paddle friction `0.30`, restitution `0.00`. Paddle axle is at `(1.56, -0.28, 2.23)`, horizontal Y-axis, blade half-span `0.42 m`, blade thickness `0.035 m`, angular speed `18°/s` from `t=0.0` through `t=5.2` (visible motor housing at `(1.56, -0.28, 2.47)`). The zero restitution avoids compensating for a weak route with artificial bounce; the bowl's decay is friction/damping, not an animated stop.

## Actors, palette, and route

| ID | role and motion | collision/visual identity |
| --- | --- | --- |
| `helix-marble` | hero actor, dynamic, scored | chrome sphere with a narrow cobalt equator; `voice:helix-marble` |
| `helix-rail` | silent support, passive | exposed banked C-channel segmented into fixed boxes; ivory ceramic track, satin aluminium underside |
| `clearance-paddle` | visible actuator, kinematic/driven | two thin saffron blades and a visible axle/motor; collidable swept proxy |
| `receiving-bowl` | silent support, passive | open 14-facet concave bowl, pale blue ceramic interior with a saffron rim |
| `helix-frame` | silent support, passive | graphite posts and cross-bracing; never a travel surface |

The route is a **1.35-turn open, banked spiral**, not an enclosing tube. Sphere-centre anchors in metres are proposed solve targets, not sampled trajectory results:

| scene time | anchor | purpose |
| ---: | --- | --- |
| 0.00 | `(-0.65, -0.72, 4.10)` | retained upper cradle; release immediately at frame 1 |
| 1.05 | `(0.74, -0.31, 3.56)` | first visible turn and gravity-driven speed-up |
| 2.20 | `(-0.18, 0.83, 2.62)` | lower spiral, opposite depth side |
| 3.20 | `(1.28, -0.35, 1.93)` | exposed exit passing below the rotating paddle |
| 4.50 | `(1.82, -0.05, 1.42)` | descending transfer lip toward the bowl |
| 5.45 | `(2.35, 0.22, 0.86)` | tangential bowl entry; bowl centre `(2.35, 0.22, 0.45)` |
| 6.55 | `(2.59, -0.03, 0.78)` | first visible bowl orbit |
| 8.45 | `(2.35, 0.22, 0.61)` | supported rest in the bowl centre |

Give every rail segment an open outer edge, a low inner guide, and a visible support beneath it. The spiral drops `2.17 m` before the bowl; bowl facets must leave the sphere visible from the camera rather than forming a cup wall across it.

## Camera and event contract

Use one slow tracking-descent shot: lens `46 mm`; camera moves from `(7.6, -10.2, 6.2)` toward `(7.9, -8.6, 4.7)`, looking at a weighted rail/marble target that moves from `(0.0, 0.0, 2.8)` to `(1.65, -0.05, 1.5)`. Stop camera lateral motion over `t=2.75–3.65` so the clearance reads in one stable view; keep the bowl and its final rest in the lower third after `t=5.2`. Studio key: broad upper-left softbox, weak cool fill, ground-plane contact shadows.

| window | salient event and physical cause | required measurement / falsifier |
| --- | --- | --- |
| 0.55–1.80 | `spiral-acceleration`: gravity on the supported banked rail converts height into rolling speed. | Tangential speed gain ≥`1.15 m/s` from evaluated states. Fail if speed is obtained by a post-release transform/velocity injection or the spiral does not descend in Z. |
| 3.10–3.35 | `paddle-near-miss`: the exiting marble passes the moving blade's lower tip while the motor continues to turn. | Swept sphere-to-paddle **surface** gap over `2.85–3.65 s`: min `0.045 m`, max `0.080 m`, target `0.060 m`; no contact interval. Fail on any contact, a gap outside bounds, or a clearance derived from a static paddle pose. |
| 7.90–8.45 | `bowl-capture-settle`: a tangential entry circulates around the concave passive bowl, loses energy through declared contact/damping, then rests. | Retain continuous bowl-contact intervals; terminal linear speed ≤`0.025 m/s` and angular speed ≤`0.070 rad/s` for ≥`1.5 s` without keyframed freezing. Fail if the marble exits, is hidden by the bowl, or is teleported to centre. |

Salience policy: minimum inter-window gap `1.0 s`; maximum one simultaneous salient event; salient duty `2.15/10.4 = 20.7%`; continuous rolling/bowl support remains raw evidence, not repeated impact events.

## Construction notes and acceptance prerequisites

- Initial construction should use 16–20 short banked fixed boxes for the spiral and a 14-facet fixed-box bowl proxy, staying below the existing 128-collider cap. Collision proxies and beveled visual mesh must be measured separately.
- The visible paddle needs a fixed motor support and deterministic actuator phase bound to the seed; do not let it touch the rail or bowl.
- Required later evidence: full native trajectory at both resolutions, paddle swept-gap certificate with uncertainty, bowl contact/settle trace, fresh-process replay, and native-time visual review. Human approval and music audition remain separate and unrequested.
