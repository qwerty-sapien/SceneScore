# 08 — Cube cascade

Identity: 08_cube_cascade; seed 2026091308; 11.20 s; 30 fps; 16:9. Sparse relay, not simultaneous pile-up. Cubes are scored persistent actors; routes/catchers/latches visible and silent. Gravity [0,0,-9.81] m/s². Cubes dynamic after release; latch arms alone prescribed mechanisms.

## Actors, mechanism and lanes

| ID / role | Physical definition | Look / score identity |
| --- | --- | --- |
| cube-a / scored initiator, voice:cube-a | 0.72 m, 1.05 kg; restitution .30; dynamic/static friction .42/.46; damping .020/.045 s⁻¹. Starts (-3.05,-1.30,4.45), rest. | Maple-like cube. |
| cube-b / scored relay, voice:cube-b | 0.56 m, .70 kg; restitution .44; friction .34/.38; damping .015/.035. Held by latch 1 at (-.15,.88,3.05). | Cobalt ceramic, edge band. |
| cube-c / scored terminal, voice:cube-c | 0.88 m, 2.25 kg; restitution .18; friction .50/.54; damping .025/.050. Held by latch 2 at (2.45,1.75,2.42). | Slate, glass inset. |
| latch-1/latch-2 / visible prescribed actuators | 0.42 m brass arms / passive stops. L1 rotates 34° only after A lever contact; L2 rotates 31° only after B trigger contact. | Visible pivots/stops; silent. |
| tracks/catchers / silent fixed supports | Separate 0.18 m U-tracks/OBB walls: A lower-front Y≈-1.30; B middle Y≈.25; C rear Y≈1.55. | Limestone / black frames. |

Keep unrelated solid edges ≥0.50 m apart. Latches cannot be invisible velocity sources: record latch angle/rate and cube state immediately pre/post release. Camera: one 45 mm-wide static composition at (10.4,-12.4,7.6) toward (.1,.25,2.3), maximum .25 m 6.0–8.5 s push, no cuts.

## Three sparse windows

| Window | Cause / target | Falsifier |
| --- | --- | --- |
| 0.82–1.96 s, a-bounce-and-latch | A falls to track-a, rebounds once, then physically hits latch-1; B release follows 0.85–1.25 s later. | Bounce/lever overlap; L1 moves early/without contact; A keyed; no causal state at release. |
| 3.42–5.06 s, b-rebound-and-near-pass | B wall-rebounds then passes supported A with certified 0.10–0.18 m cube/cube gap. | B releases without L1; no wall onset; gap out of range/unbracketed; collision/pile-up. |
| 6.62–8.18 s, c-release-and-transfer | B trigger opens L2; C enters 0.45–0.75 s later and transfers momentum once with B on track-c. | L2 early; C teleported/keyed; no B/C onset or velocity exchange; A joins contact. |

A reaches front catcher by 2.90 s; B middle catcher after near pass; C rear catcher after transfer. Do not turn support into collision spam; A/B near miss has no impact Foley.

## Ending and candidate gate

In 8.2–11.2 s settle separately at A (-.85,-1.38,.42), B (1.05,.15,.37), C (3.20,1.55,.48). Endpoint requires each supported, speed <0.08 m/s and angular speed <0.18 rad/s. Frame all three nonoverlapping so A → L1 → B → L2 → C is readable.

This multi-body/latch/gap brief is outside analytic scope and behind failed Native Bullet calibration. Promotion needs latch continuity controls, B/C transfer control, positive and intentionally-colliding A/B variants, solver-resolution comparison, fresh replay, and full-motion review. Until then it is source intent only.
