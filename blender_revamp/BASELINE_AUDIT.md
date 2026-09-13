# Baseline findings from the supplied snapshot

## What was inspected

The uploaded `archive.tar.gz` was read and regular project files were extracted without the bundled Git repository, virtual environment, caches, dependency directories or macOS metadata. The audit focused on `modules/blender/`, `apps/web/tools/prepare.py`, relevant tools, root instructions/status, and existing media evaluation evidence. This is a targeted animation-path audit, not an exhaustive review of the application.

The submitted MP4 and `artifacts/phase3/performance/scenescore-DRAFT.mp4` have the same SHA-256:

`8b69ad6b639e670ed701e44f92aa49a359dee02c6e5d8a6755a1595941df2265`

FFprobe measured a 30-second H.264 video, 320x180, native 8 fps, 240 decoded frames. The archive's active hero configuration also specifies these settings. `evidence/baseline_metrics.json` contains the raw measurements and source hashes.

Sixteen sampled video frames were visually inspected. Additional excerpts preserve the original cadence for later inspection. No continuous video playback or audio audition was performed in preparing this pack. No Blender executable was available in the analysis environment, so scene-state conclusions rely on inspected source and supplied evaluated-state exports, not a newly executed simulation.

## Source-grounded failure mechanisms

| Finding | Snapshot evidence | Required correction |
|---|---|---|
| Dynamics deliberately absent | `modules/blender/recipes.py:1-4` states that normalized linear keys are authoritative and there is no dynamics solver. `modules/blender/README.md` describes synthetic choreography. | Establish a physical production mode and clearly distinguish deliberate driven choreography from free dynamics. |
| Constant-height approach and a frozen ball | `recipes.py:27-29` sends the projectile from x=-6 to x=-1 at z=1, then holds it there in the contact variant. With 30-second duration, travel occurs from 3.6 to 12.6 seconds. | A motivated release, credible free flight, contact response and supported final state. |
| Scheduled collapse independent of impact | `recipes.py:30-37` gives the three blocks predetermined translation/drop/bounce positions. The first block starts at 15 seconds, around 2.4 seconds after the projectile reaches the target. | Actual impact/support loss must cause motion. No scheduled collapse in a miss or no-launch control. |
| Translation without tumbling | `exporter.py:118-129` inserts location keys and forces LINEAR interpolation. The supplied block quaternions remain identity throughout. | Allow physically explained angular motion where contact torque/support loss produces it. Do not add arbitrary rotation everywhere. |
| No physical ground | `exporter.py:131-134` creates a visual-only plane at z=-1.1 and explicitly excludes it from interactions. | Real support geometry/collision representation consistent with the visible set. |
| Validation protects the old choreography | `validate.py:42-48` reconstructs the original recipe and checks trajectory agreement. It has no general penetration or physical-dynamics gate. `exporter.py:193-195` does the same comparison while exporting. | Independent physical and visual checks; retain integrity checks under their proper names. |
| Contact code assumes unrotated primitives | `geometry.py:gap` uses sphere/AABB and AABB/AABB proxies; `pair_timeline` receives positions without orientation. | Orientation-aware checks and temporal coverage appropriate for dynamic rotating bodies. |
| Preview settings leak into batch delivery | `batch.py:62` defaults to 12 fps; line 81 always appends `--preview`, which selects 320x180 in the exporter. The supplied actual hero was rendered at 8 fps. | Separate diagnostic, preview and final profiles; verify native decoded cadence. |
| Existing review did not assess continuous motion | `reports/media-evaluation/REVIEW.md` explicitly says the complete video was not watched and full-motion quality was not assessed. | Inspect actual motion before asserting motion quality; preserve the historical review honestly. |
| Active application selects old bundles directly | `apps/web/tools/prepare.py:21` hardcodes the old hero and near-miss folders before copying MP4/JSON into browser assets. | Rebuild and select a coherent new candidate across video, states, interactions and score data. |

Line numbers identify the supplied snapshot. Re-discover them if source hashes differ in the live repo.

## Quantitative evidence

Using only the supplied evaluated-state bounds, a separate script recomputed signed AABB gaps for the fixed-orientation, approximately 1 m cubes. Negative values indicate overlap. This computation imports no production recipe or contact helper.

| Pair | Sample time | Signed gap |
|---|---:|---:|
| tower-0 / tower-1 | 20.28125 s | -0.533744693 m |
| tower-0 / tower-2 | 21.15625 s | -0.070052385 m |
| tower-1 / tower-2 | 21.93750 s | -0.533127427 m |

These agree with the saved geometry report. They are severe geometric overlaps relative to the 1 m object dimensions. The exact sample times lie on the exported 32 Hz audit grid; they are not all actual 8 fps video frame times. Inspect surrounding video frames rather than claiming that a subframe was directly rendered.

The recorded projectile centre remains at z=1 throughout. Its lowest point is z=0.5 while the visual floor is z=-1.1: a 1.6 m unsupported gap in this scene. Final block bottoms are z=0, leaving a 1.1 m gap above that floor. Initial neighboring block faces are about 0.05 m apart. The scene provides no support mechanism explaining these separations.

**Apparent shrinking is not corroborated by the inspected transforms.** Every block's axis-aligned dimensions remain approximately 1 m, with deviations below 3e-7 m, and no scale animation is authored in the inspected exporter. The camera is orthographic. Preserve the user's visual complaint as a perceptual issue to investigate, but do not invent a diagnosed scale-keyframe defect. The new checks should detect actual scale drift and distinguish it from projection/occlusion.

The current `--substeps` value samples evaluated keyframed positions more densely. It is not a rigid-body solver setting. More export samples would reveal existing overlap more densely without resolving it.

## Actual negative media in this pack

`evidence/original-DRAFT.mp4` is the user's unchanged MP4. `evidence/contact-sheet.jpg` contains sampled frames at 0, 2, ..., 28 and 29.875 seconds; each 320x180 frame was enlarged for inspection. Enlargement adds no detail.

The following silent excerpts were re-encoded using FFmpeg at the source's native cadence, with no slow motion or frame interpolation:

| File | Original time interval | Review focus |
|---|---|---|
| `evidence/clips/12-17s-contact-freeze.mp4` | [12,17) seconds | Ball freezes; block response is delayed and scripted. |
| `evidence/clips/18-24s-block-overlap.mp4` | [18,24) seconds | Blocks translate through each other while remaining upright. |
| `evidence/clips/24-30s-unsupported-ending.mp4` | [24,30) seconds | Ball and blocks end visibly detached from meaningful support. |

These excerpts are real negative examples from the submitted artifact. They are not newly generated demonstrations.

## Interpretation

The snapshot supports a concrete diagnosis: the production specification and validator permit nonphysical motion. It does not establish that computer-use capability alone caused the failure. CLI and MCP can improve reproducibility and inspection, but neither replaces a physical scene model, causal staging or outcome-based validation.
