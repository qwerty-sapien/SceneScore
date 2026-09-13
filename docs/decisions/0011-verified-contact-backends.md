# Scope physical backends to their measured behavior

The Blender revamp's independent controls discovered timestep-dependent elastic
response in this installed Bullet build. Expected-elastic controls at240/480/960Hz
failed restitution, energy or penetration gates. `RESTITUTION-DIAGNOSTIC.md` links
matching-build source: positive-gap speculative-contact correction explains the
measured velocity losses. Neither stored-property fixes nor split impulse repaired
them. Relative manifold thresholds also prevent assuming uniform unit scaling is
a solution. These failures stay recorded; no threshold is relaxed.

The bounded zero-restitution repair also failed after three attempts. The final
50/100-substep transfer diverged 32.570 mm (5 mm limit); the fine run retained
0.163740 m/s relative speed (0.1 m/s limit). Damped native workshop scenes remain
diagnostic candidates only. Neither elastic nor inelastic coupled Bullet contact
is accepted by this run. Geometry, gravity, causality,
support, replay and convergence gates remain binding.

The staircase's bouncing sphere instead uses independently validated, explicit
SI mechanics against fixed solids. Constant-gravity flight, instantaneous contact
response and friction follow recorded physical parameters. Blender keyframes are
derived playback samples, never hand-authored collapse or normalized flight.
Separate isolated bounce/convergence controls must pass after Blender evaluation.
This follows the pack's allowance for independently validated mechanics. The
analytic backend does not support coupled moving obstacles or dynamic towers.
