# Kinetic geometry 01 — 03 / 06 / 09 source plans

These are implementation-ready **design intents**, not bakes, renders, or
validation evidence.  They deliberately use `native_bullet` because each scene
needs a non-spherical dynamic hero plus an actual moving contact/hinge.  The
existing fixed-OBB sphere model is not an acceptable substitute.  The builder
must run candidate-specific calibration, 240 Hz state extraction, fresh 30 fps
replay, physical-event checks, and proxy review before any pass status.

All dimensions are metres, masses are kilograms, angles are degrees, and
angular velocities are radians/second.  Suggested extraction is 240 Hz and
playback/render cadence is 30 fps.  The target is 9:16 (540 x 960 proxy, 1080 x
1920 final) with a single continuous camera per clip.  Seeds are deterministic
candidate seeds, not measured production identities.

| Clip | Intent sidecar | Duration / seed | Backend scope |
| --- | --- | --- | --- |
| 03 Triangle Catapult | `03_triangle_catapult.scene-intent.json` | 10.4 s / `305103` | Dynamic triangular prism and spring-powered hinged arm against fixed supports; no post-release transform or angular-velocity injection. |
| 06 Rolling Torus Gate | `06_rolling_torus_gate.scene-intent.json` | 10.2 s / `305106` | Dynamic torus rolling on finite rail, physical latch contact, counterweighted hinged gate and compliant catch. |
| 09 Geometric Relay | `09_geometric_relay.scene-intent.json` | 10.6 s / `305109` | Three dynamic heroes, two real impulse/latch transfers, spring launcher and supported terminal catches. |

`native_bullet` is a proposed backend selection, not an assertion that its
historical calibration applies to these contacts.  If a candidate cannot pass
fresh relevant controls, do not replace its motion with authored transforms;
record the blocked candidate or implement a separately declared explicit model
with equivalent measured contact, hinge, and launch constraints.

The JSON files use the repository's `scene-intent-1` supplement format.  They
are intentionally marked `DESIGN_INTENT_NOT_MEASURED`; a plan-lint result would
not establish mechanics, camera coverage, render quality, replay, or approval.
