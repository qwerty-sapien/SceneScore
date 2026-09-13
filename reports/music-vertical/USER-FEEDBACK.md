# User rejection of the delivered legacy animation

Authority: direct user feedback on 2026-09-13 and the supplied [Jam recording](https://jam.dev/c/e938fe62-df2c-4b9d-93b1-738dce23fc78). The animation verdict is **CHANGES_REQUESTED / REJECTED_FOR_PHYSICAL_QUALITY**. This is a visual rejection, not approval or rejection of an exact musical arrangement; audio audition remains pending.

The user reports cubes phasing through one another, robotically smooth translation, constant-speed ball motion, apparent shrinking, constant-speed falls, and an abrupt ball stop without recoil. The user also states that the browser had always been closed. Current cleanup records now attribute closure to that direct confirmation; no further browser cleanup action is required from the user.

## Recording and artifact identity

The Jam page was opened in a temporary in-app browser tab. Its Info panel identifies `https://scenescore-muse-vertical.vercel.app/`, recorded 13 September 2026 at 09:06 GMT+8, and a 1 minute 9 second recording. The visible app is the default **Projectile & tower** scene with a 30-second timeline, not the staged physical-scene review route. The recording was played; selected frames visibly show the legacy tower scene and overlapping cubes. No full continuous-motion perceptual certification is asserted. Jam's Transcript panel reports no speech detected. The temporary Jam tab was explicitly closed and an empty tab inventory verified.

`reports/muse-vertical/deployment-manifest.json` binds the deployed `studio/contact.mp4` to SHA-256 `07a65b59bda1afc07fc1397f72232f2855df595b2cfe3948ea602d517890a04a`. That is exactly the source video reused in this music candidate. The deployment record reports 320×180 video at 30 seconds. The source candidate records 8 fps. These are artifact-selection facts, not a cache diagnosis.

The music preparation tool explicitly selects `artifacts/blender/validated-hero/10_projectile_tower-default`. Its name does not establish physical validity. The separate revamp did not replace the active hero because its native coupled-body calibration failed. Neither fact justified presenting the unchanged video as a satisfactory full vertical result.

## Evaluated motion findings

[legacy-motion-audit.json](legacy-motion-audit.json) was computed read-only from the unchanged exported object states, not from a new simulation.

- Two axis-aligned one-metre cubes intersect with **0.533745 m minimum translation depth at 20.28125 s**. This is solid interpenetration, far beyond a solver tolerance.
- The ball's median moving horizontal speed is **0.555557 m/s**. Its horizontal velocity never becomes negative; it stops at position `[-1,0,1]` after approximately **12.625 s** and never recoils.
- The cube motions are piecewise linear, without gravitational acceleration or collision-driven rotation. Their motion is prescribed independently of the ball.
- Exported cube dimensions remain one metre within floating-point error (less than 0.3 micrometres of variation). Actual scale shrink is not present in these transforms. The user's shrinking impression is recorded as a visual symptom; occlusion/projection may contribute, but that explanation was not independently established.

The cause is explicit in `modules/blender/recipes.py`: its module documents that it has no dynamics solver, the hero contains hard-coded ball/tower key positions, and `position()` linearly interpolates them. `modules/blender/exporter.py` inserts location keys with linear interpolation. There is no physical impulse or recoil rule in that legacy path.

## Disposition

The previously reported software checks remain historical evidence about score/transport behavior. They do **not** pass animation quality. The full vertical delivery is incomplete until a different, validated scene replaces this rejected input and the deployed/default path is shown to load that exact replacement.

A read-only review of the native revamp calibration found no simple configuration error or successful repair. The final transfer control retains 0.163740 m/s outgoing separation velocity and 32.570 mm coarse/fine trajectory divergence, against 0.1 m/s and 5 mm limits. Moving measurement windows does not remove the discrepancy. The earlier repair trials already covered lower solver settings; no identical scalar sweep was rerun.

A distinct next physics investigation would test an explicitly recorded collision representation, with an independently bounded collider approximation, fresh drop/transfer controls and unchanged convergence criteria. A floor-only bounce improvement would not certify a dynamic tower. No new physics result, replacement video, deployment or model spatial-ability claim is made by this report.

No source animation, frozen candidate, deployment or acceptance threshold was changed during this feedback investigation. The factual cleanup correction and this rejection record are the changes. The original reports preceding the correction are preserved in `history/2026-09-13-before-user-correction/`.
