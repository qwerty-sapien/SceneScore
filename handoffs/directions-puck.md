# Direction 18 — Billiard Greenhouse scoped mechanics

Machine checks **GO**. Rendering, evaluated Blender replay and visual/story approval are **NOT_RUN here**, and remain the integrator/review track. No Blender, server, dependency or persistent background jobs were started. All commands below exited.

## Owned delivery

- `modules/blender/production/directions/puck.py`
- `modules/blender/tests/directions/test_puck.py`
- this handoff

Worktree `/private/tmp/scenescore-directions-puck`, base `a397f3f`. No root/shared files were edited; no commits or merges were performed.

```python
from modules.blender.production.directions.puck import build_direction
packet = build_direction('18', hz=240, substeps=8)
```

The packet has `id`, `title`, `duration_s=30`, `hz`, `backend`, `actors`, `geometry`, `states`, `events`, `validation`, `energy_audit`, `parameters`, `camera`, and `approval=None`. There are **7,201 evaluated output states** on `[0,30]`; internal integration uses **1/1,920 second**. Every actor state contains position in metres, XYZW quaternion, scale and velocity in m/s. Fin/door also expose world angular velocity. Output coordinates are Z-up; local mechanics coordinates follow the tilted supporting plane, with a rigid local-to-world transform.

Source SHA256: `d3612757edc986efa028095a3609194b371645d907ca4fbed625f88c527bd9f9`.

Tests SHA256: `4e22003b5aeb813ff51fb6fb467dfeab016c3fd1e31e4f393186b90dbd8e80ad`.

Default packet SHA256, `json.dumps(packet, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()`: `763202883d1327c357782c6ebddc6b7fdeea4da8257f8e76071eb4e6a65b9fc7`.

## Actual sequence

| Event | Time, seconds |
|---|---:|
| Spring fully extends; follower releases | 1.741146 |
| Fixed rail bank | 8.001042 |
| Hinged fin receives impulse | 12.348958 |
| Closest clearance to far stationary fin | 13.670833 |
| Closest clearance to near stationary fin | 17.427083 |
| Peg impact releases door latch | 17.629687 |
| Downstream guide contact | 21.765104 |
| Compliant dock contact begins | 24.602083 |
| Puck settles (speed below15mm/s for750ms) | 25.122917 |

The missed fins clear by **49.430mm and41.878mm**. Neither receives an impulse. The initial rail and fin contacts generate actual puck spin and finite hinge angular momentum. The fin reaches **0.177961rad/s**. The door stays exactly latched until a real peg impulse exceeds0.005Ns; then the integrated counterweight opens it. The puck never collides with the closed door. Final puck speed is **0.0382mm/s**.

## Mechanics and limits

- Puck:0.4kg, radius0.24m, height0.14m, solid-disc spin inertia `mr²/2`. Spring `k=0.34N/m`, compression0.9m. Massless follower remains exactly tangent to the disc until the spring force reaches zero.
- A single supporting plane supplies the normal constraint, exact projected gravity and Coulomb sliding friction `mu=0.0032`. Spin has viscous decay0.08/s. Rough dock friction is0.018, applied only when the puck centre lies within the actual material rectangle. This is an explicit centre-sampled contact-material model.
- The shallow plane slope is0.0008: approximately8mm of real descent across the10m x travel. **This descent is visually subtle.** Guide rails define the downstream groove; there is no deep ramp or separate descending channel. A visually steeper descent would require a further mechanical retune, not playback scaling.
- All bank/fin/peg/guide obstacles are finite rectangles. Hard contacts locate the surface crossing by bisection. Normal impulse and then capped Coulomb tangential impulse are sequential; restitution0.82 applies at the normal stage. The subsequent coupled tangential impulse may change the final relative normal velocity. The oblique fixture verifies separation, angular momentum conservation and non-increasing energy after both stages; this is not claimed to be a simultaneous multi-contact friction solver.
- Fin is a finite-width0.5kg hinged rectangle with its exact in-plane inertia, preloaded torsion spring0.035Nm/rad, damping0.035Nms/rad, and gravitational potential/torque from the shallow plane. Initial preload balances gravity.
- Door is a0.6kg finite-width hinged rectangle coupled to a0.08kg counterweight by an ideal constant-radius0.17m drum/cable. Combined inertia includes the counterweight. Damping0.18Nms/rad; a unilateral angular stop holds the door at zero with no fictitious work. The rigid release peg is an ideal impulse-triggered latch, not an independently deforming peg body.
- Dock facing is Kelvin-Voigt compliant:18N/m,1.8Ns/m. Actual maximum facing compression is10.297mm; its rendered front face follows the compression so the puck does not interpenetrate the visible compressed facing. The fixed backing remains at intrinsic x=5.32m.
- This is constrained planar mechanics, not Bullet/general3D or arbitrary body contact. Dynamic hinge-to-static collisions are excluded only after their entire candidate sweeps are certified clear. Bounds must be checked before accepting any modified settings.

## Renderer contract

Cylinder axes are localZ. Fin and door box meshes are centred at their supplied state origins, long axis localX. Their `pivot_m` and `hinge_axis` describe actual plane-normal bearings. Do not reinterpret the state origin as the pivot.

`launch-spring` has shape `coil` and `deformable=True`: its X scale is the physical changing spring length. `dock-stop` has `deformable=True`: its X scale compresses a20cm facing. All other actor scales stay exactly `[1,1,1]`. Coil decoration must remain inside the supplied physical extent and must not introduce body motion.

The packet includes spring anchor, bearing pins, drum, overhead frame/post, fixed latch linkage and guide cable. `counterweight.cable` supplies a fixed endpoint, local attachment offset and radius; the integrator may derive its visible cable extent from those endpoints at every240Hz tick. That is an ideal cable visual, not another source of force. The spring intentionally joins its anchor, and each fin/door intentionally encloses its own bearing; these constrained joints are excluded from clearance checks.

The table mesh and rough pad are aligned to the support plane; the pad is flush/inset. A static under-table slab, legs and floor may be added entirely below that plane. No moving body extends below it. Use materials wood/glass/brass/cork/green_felt/ceramic/steel. Suggested camera `[10,-13,14]`, look-at`[0,-1,1]`, orthographic scale15.

## Verification actually run

```sh
PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest modules/blender/tests/directions/test_puck.py -q
/Users/agent/Desktop/SceneScore/.venv/bin/ruff check modules/blender/production/directions/puck.py modules/blender/tests/directions/test_puck.py
git diff --check
```

**17 tests passed in30.87s**, Ruff passed, diff whitespace check passed. Tests cover analytic wall restitution, frictional spin, oblique coupled hinge angular momentum/energy/separation, finite corners, the causal complete sequence, launch-disabled control, pre-latch door immobility, support/clock alignment, finite unit quaternions, metre/centimetre equivalence, full actor convergence, support exclusion sweeps, and invalid input rejection.

- Maximum pre-resolution hard penetration: **0.174493mm**.
- Maximum substep dynamic-point travel: **0.417998mm**, below the9mm no-tunnelling bound (one tenth of the thinnest hard fin thickness).
- Maximum positive contact energy gain: **0J**.
- Maximum full-system balance residual: **0.057121mJ**. Ledger includes spring/rotational/hinge gravitational energy, projected gravity/counterweight work, contact/friction/damping/stop losses.
- Fin/static minimum separating-axis clearance: **246.197mm**. Door/static minimum: **42.776mm**. Between-sample hinge sweep bound: **2.810mm**.
- Metre versus centimetre calculation units preserve actor positions/orientations and contact identity/timing within1e-8 SI tolerance.
- 8→16 substeps maximum position difference: puck**0.047163mm**, fin**0.005697mm**, door**0.138757mm**, counterweight**0.049660mm**, plunger**0.000010mm**, spring**0.000005mm**, dock facing**0.023577mm**. The paired-resolution test also bounds every quaternion angle below0.001rad, every deformable extent below1mm and event time difference below5.21ms while requiring event actor identity equality.
- Worst actual 8→16 quaternion difference: **0.000292119rad**, door. Worst deformable full-extent difference: **0.047154mm**, dock facing. Worst event time difference: **0.260417ms**, spring release; all event types and actor identities match.
- An independent3D OBB audit encloses all cylinders conservatively and checks every240Hz actor state against the added fixed support geometry. Its minimum clearance is **60.000mm**, spring-plunger to spring-anchor; inter-row point movement is below4mm. Explicit own bearings and spring-anchor attachment are constrained exceptions, not accidental overlaps.

No audio, render, Blender cache, actual evaluated replay or human perception check was run by this worker. Static supports and cable framing still require the independent visual review.
