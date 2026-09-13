# Concrete positive and negative examples

These are acceptance examples and analytical fixtures. Positive scenes described below still need to be built, rendered and reviewed in Blender. The supplied negative video excerpts already exist. Do not describe the analytical JSON as measured physical footage or a completed Blender simulation.

## 1. Hero scene: a small practice court

**Positive:** A simple, grounded figure faces a short stack on a visible platform in a compact practice court. A restrained floor marking and back wall establish the lane and scale. The figure visibly holds the ball, shifts into a throwing pose, accelerates its hand and releases. The ball follows a readable arc, strikes the stack, and the blocks topple through contact/support loss. They collide with the platform/floor and settle irregularly but coherently. The ball rebounds, deflects or continues according to its collision, then comes to a supported rest. The figure follows the outcome and relaxes. One simple camera keeps the causal chain visible.

**Negative:** The same old hovering sphere and three cubes are retained. A stick figure and attractive wall are added behind them, but the figure never holds or releases the ball. The stack still collapses on a timer. This adds decoration while leaving the central causal failure unchanged.

**Review:** Without sound, labels or reading the brief, can the viewer identify the throw, contact, consequence and ending? Are hand contact, floor support and the target all visible? Keep the setting simple enough that its purpose is understood before action starts.

## 2. Alternative: an explicit small launcher

**Positive:** A visible spring/paddle mechanism loads, releases, transfers motion into a ball and returns with a restrained damped movement. The mechanism explains the initial impulse; the ball's flight and subsequent collisions follow from the release state. The set resembles a small kinetic workshop.

**Negative:** A launcher stands beside the ball while the ball starts moving independently. An invisible force activates the target regardless of whether the ball reaches it.

**Review:** The energy source and release event must be legible. Complex machinery, downloadable assets and decorative motion are unnecessary.

## 3. Flight and timing

**Positive analytical reference:** Gravity is [0,0,-9.81] m/s². A ball starts at [0,0,1] m with velocity [3,0,2] m/s. For unpowered flight with no drag:

`p(t) = [3t, 0, 1 + 2t - 4.905t²]`

At t=0.2 s, p=[0.6,0,1.2038] m. At t=0.4 s, p=[1.2,0,1.0152] m. Horizontal speed remains 3 m/s, while vertical velocity changes. This is an intentional positive control against an overbroad prohibition of constant speed components.

**Negative:** The same ball is translated to [0.6,0,1] and [1.2,0,1] at those times with no support or force explaining the constant height. Alternatively, every flight segment is given a default ease-in/ease-out, so it slows before contact and resumes after a pose-like pause.

**Review:** Check forces and world-space acceleration away from contact windows. Timing should also read clearly at native frame cadence; a correct path stretched over many seconds changes its mechanics.

## 4. Impact and recoil

**Positive:** An isolated equal-mass, frictionless, elastic 1D collision has incoming velocities [3,0] m/s and outgoing velocities [0,3] m/s. The projectile stops as the target takes its momentum. This is a valid zero-recoil counterexample. A separate fixed-wall test with effective restitution 0.5 takes incoming +2 m/s normal velocity to -1 m/s.

**Negative:** The projectile is frozen at first contact regardless of mass/material, the target waits several seconds and then follows a programmed path, and the ball remains suspended after the stack leaves. Another negative is an unpowered collision producing more total kinetic energy than entered, under a test setup with no stored energy or external work.

**Review:** Match response to the specific scene. Do not demand that every ball bounce backward. Do not equate a Blender material setting with measured pairwise restitution without checking the effective response.

## 5. Solids and supporting geometry

**Positive:** A unit cube rests with its bottom touching the visible platform and negligible jitter after settling. In a collision, two cubes maintain separation within a justified solver tolerance. A falling upper block starts losing support and rotating because of contacts, not because a timer fires.

**Negative:** Use the actual 18-24 second excerpt: neighboring unit blocks overlap by about 0.534 m at sampled extrema. Use the 24-30 second excerpt for unsupported rest. Neither is a small numerical contact error.

**Overzealous-validator negative:** Reject two separate rotated thin boxes merely because their AABBs overlap. The JSON includes two boxes with half-extents [1,0.1,0.1], both rotated 45 degrees about Z, separated by 0.3 m along their shared short-axis normal. Their actual gap is 0.1 m despite broad-phase AABB overlap.

**Review:** Use an orientation-aware narrow phase and handle containment as well as surface crossings. Sampling must be sufficient to observe fast contact, with explicit limits where it is not continuous.

## 6. Scale and release handoff

**Positive:** The held ball's world position and velocity continue across release, and its rigid dimensions remain unchanged. A tumbling cube's world AABB changes because of rotation, while its local geometry and world scale remain constant.

**Negative:** Removing a parent changes the ball's size or position. A release switches to dynamics but drops its velocity to zero. A block shrinks by 10% during descent to reduce apparent collision risk.

**Review:** Inspect world transforms and rigid shape invariants before and after the handoff. Measure actual geometry scale instead of inferring it from a few low-resolution pixels. The original video's suspected shrinking was not confirmed by its exported dimensions.

## 7. Matched near miss and causal counterfactual

**Positive:** Only the launch/aim changes. The ball passes visibly clear of the target; the same physical stack stays stable. The ball can later strike the floor and make appropriate floor-contact Foley. A no-launch control also leaves the target standing.

**Negative:** The target collapses on the contact variant's timer even though the ball missed. Or the system suppresses all contacts/sounds in the miss variant, erasing legitimate later floor impacts. Or the camera makes a true geometric gap look like a hit and viewers cannot distinguish the two outcomes.

**Review:** Check the specific ball/target pair, the visible miss and the subsequent actual contacts. Share all unrelated setup and material parameters across variants.

## 8. Appearance and scene meaning

**Positive:** A restrained set establishes function; a clear focal hierarchy follows the action; contact shadows connect objects to their supports; material families suggest coherent weight/response; softened edges catch light; the main action occupies a readable region of the image. A simple figure has a clear silhouette and purposeful posing.

**Negative:** A new gradient/HDRI surrounds the same unexplained animation. Decorative props obscure contact. Depth-of-field and bloom hide intersections. Repeated camera moves compensate for empty staging. Tiny white object IDs remain in the final image. Every object has a shiny random material that obscures form.

**Review:** Use both a neutral contact pass and the beauty pass. Judge the complete silent clip and event windows. A gradient is acceptable as part of lighting; it cannot supply missing scene purpose.

## 9. Review-harness quality

**Positive:** The independent validator rejects actual known-invalid clips/scenes, accepts analytically valid counterexamples, and reports its measurement scope. Reviewers inspect full native-cadence motion and isolate defects by time/frame. A new render invalidates prior visual review of the old hash.

**Negative:** The generator computes a path, the validator imports that path and verifies that the output follows it, and a successful file hash check becomes evidence of realism. Another negative is converting an 8-fps source into a 30-fps container and claiming improved animation. A third is repeating the creator's self-assessment without looking at the media.

**Review:** Mutation-test the actual production path. A still-image or metadata-only reviewer must leave motion quality unverified. The quality goal is behavior on the delivered artifact, not the number of tests or documents.
