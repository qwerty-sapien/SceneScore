# 07 — Capsule Pendulum: authoring source plan

`status: DESIGN_INTENT_NOT_MEASURED` · `id: 07_capsule_pendulum` · `seed: 707613` · `duration_s: 10.6` · `clock: scene_seconds_zero_at_start` · `render: 9:16, 30 fps (proxy 540×960; final 1080×1920)`

This is an implementation-ready intent, not a claim that the pendulum constraint, collision, or settling has been simulated. It is deliberately a compact two-level mechanism rather than a generic ramp variation.

## Declared mechanics

- **Model:** `native_bullet`, proposed model version `native-bullet-hinged-compound-capsule-1`, 240 Hz. The capsule is one dynamic compound body (central cylinder plus two spherical ends); the pendulum is a dynamic bob/arm attached to a fixed overhead pivot by a single hinge with angular limits `[-32°, +32°]`. Upper/lower channels and catcher are passive fixed geometry. No post-release transform is allowed for either dynamic body.
- **Scope boundary:** the existing A4 gate cannot certify coupled dynamic bodies, hinges, or a capsule collision shape; current production validation also accepts only sphere/box colliders and historical native calibration is failed. Before construction can pass, a narrowly scoped native Bullet adapter must expose compound-capsule/hinge states, candidate calibration, constraint error, and collision/settle predicates. A visual pendulum swing or keyframed redirection is not a substitute.
- **World/solver:** gravity `(0, 0, -9.81) m/s²`; candidate substeps `50`, solver iterations `20`, collision margin `0.0015 m`; compare at 100 substeps as a declared resolution control only. Capsule `mass 0.80 kg`, capsule radius `0.180 m`, cylinder half-length `0.360 m`, friction `0.40`, restitution `0.00`, angular damping `0.045 s⁻¹`. Pendulum bob/arm `mass 1.50 kg`, pivot-to-COM `1.20 m`, friction `0.34`, restitution `0.00`, angular damping `0.035 s⁻¹`; rails/catcher friction `0.46`, restitution `0.00`.

## Actors, palette, and route

| ID | role and motion | collision/visual identity |
| --- | --- | --- |
| `capsule` | hero actor, dynamic, scored | ivory ceramic capsule with a narrow vermilion belt; `voice:capsule` |
| `pendulum-arm` | visible actuator/mechanism, dynamic, scored | walnut arm with burnished-brass end bob; `voice:pendulum` |
| `pendulum-pivot` | silent support, passive | graphite overhead yoke and clearly visible hinge pin |
| `upper-channel` | silent support, passive | dark slate descending channel with cyan inner edge |
| `lower-channel` | silent support, passive | open, broad curved track; lower steel frame visible underneath |
| `lower-catcher` | silent support, passive | shallow ivory tray, physically able to retain the capsule |

Proposed capsule-centre anchors in metres, with pendulum pivot at `(0.10, -0.02, 4.15)` and neutral bob centre `(-0.27, -0.12, 2.97)`:

| scene time | anchor | purpose |
| ---: | --- | --- |
| 0.00 | `(-2.50, -0.75, 4.05)` | immediate retained upper release |
| 1.45 | `(-1.30, -0.52, 3.48)` | gravity acceleration on exposed upper channel |
| 2.55 | `(-0.43, -0.17, 3.02)` | capsule reaches the neutral pendulum bob |
| 3.35 | `(0.38, -0.58, 2.22)` | redirected, descending exit onto lower rail |
| 4.95 | `(1.22, -0.25, 1.42)` | broad lower curve, spatially separated from pendulum |
| 6.55 | `(1.95, 0.55, 0.72)` | decelerating approach to lower catcher |
| 8.35 | `(2.25, 0.85, 0.48)` | retained final rest |

The pendulum must remain in the shot after collision: its initial forward swing moves toward positive X/positive Y, then crosses neutral with diminishing envelope while the capsule descends in the lower foreground. The lower rail begins only after an unobstructed gravity-driven handoff; do not hide the direction change behind the pendulum or a foreground frame.

## Camera and event contract

Use a three-quarter mechanism composition: `48 mm`, fixed camera `(7.8, -10.4, 6.45)`, target `(0.35, -0.12, 2.45)`. A gentle 3% push from `t=0.2–2.3` may establish the impact, then hold through `t=4.1`; no cut. Frame the pivot, bob, capsule path, lower curve, and catcher in one portrait shot. Warm key light on brass/wood; cool fill separates the slate rails; retain contact shadows beneath all supports.

| window | salient event and physical cause | required measurement / falsifier |
| --- | --- | --- |
| 0.55–1.80 | `upper-acceleration`: gravity on the upper channel accelerates the capsule toward the bob. | Tangential speed gain ≥`1.00 m/s` from evaluated states. Fail if the gain comes from a transform/impulse inserted after release or the support is discontinuous. |
| 2.55–2.76 | `capsule-pendulum-transfer`: a dynamic capsule contacts the dynamic bob, redirects downward, and supplies the pendulum's initial swing. | New capsule/bob contact onset inside window; capsule heading change ≥`32°`; pendulum angular speed ≥`0.80 rad/s` within `0.20 s` after onset; hinge anchor error ≤`0.005 m` across the swing. Fail on keyframed pendulum motion, absent contact, post-contact constraint violation, or a bob/capsule interpenetration correction masquerading as transfer. |
| 7.85–8.45 | `lower-capture-settle`: the capsule's supported roll dissipates into the catcher while the pendulum continues its naturally diminishing residual motion. | Capsule terminal linear speed ≤`0.025 m/s` and angular speed ≤`0.070 rad/s` for ≥`1.5 s`; pendulum swing amplitude must decrease over successive post-impact half-cycles through at least `t=7.2`. Fail if either object is frozen, the capsule misses/exits the catcher, or pendulum movement is edited independently of its constraint. |

Salience policy: three windows, ≥`1.0 s` gaps, at most one salient event at once, duty `2.06/10.6 = 19.4%`. The lower-track decelerating roll and the pendulum's residual swinging are continuous physically meaningful motion, not repeated event spam.

## Construction notes and acceptance prerequisites

- Use a tested compound/convex collision representation whose rendered capsule differs from its collision envelope by a recorded bound. A stretched sphere or a cosmetic capsule around a box is not sufficient without declaring that proxy and checking its contact geometry.
- The yoke must visibly support the hinge. Keep all guide walls below capsule centreline around impact so the collision is legible and no passive wall supplies the apparent redirection.
- Required later evidence: native calibration bound to this exact compound/hinge candidate, per-tick hinge error, contact episode/heading traces, pendulum angular-envelope decay, capsule catch trace, fresh replay, and full-motion review. These are not performed by this plan.
