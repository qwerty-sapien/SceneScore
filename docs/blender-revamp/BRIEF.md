# Blender production brief — kinetic workshop

Node 02 deliverable. Authority: the user's approved production plan and the
music-handoff patch; the supplied packs remain unchanged. This is a production
specification, not evidence that a scene has been built or reviewed. No external
visual references were viewed. Analytical examples in the supplied reference
document remain analytical examples.

## Concept decision

| Concept | Causal strengths | Cost and failure risk | Decision |
|---|---|---|---|
| Minimal grounded figure in a practice court | A held ball and purposeful throw can make intention immediate. | Requires credible feet, grip, acceleration, release and follow-through; a decorative figure adds no causality. | Defer; unnecessary rigging for this slice. |
| Small mechanical kinetic workshop | An exposed paddle, supported ball and short travel lane show the energy source and consequence directly. | Needs a real paddle–ball contact and visible support; a launcher beside an independently moving ball fails. | Selected. |

**Action:** An exposed paddle launches a ball from a small supported deck toward
a three-block tower; contact brings the tower down, while a visibly different aim
leaves it standing, and all free bodies finish on physical supports.

## Shot, beats and physical staging

Use metres, world Z up, ordinary gravity and a fixed three-quarter view. The
action runs screen-left to screen-right. Stage a short launcher deck on the left,
a clear flight lane in the centre and the tower directly on the workshop floor
on the right. Provide floor beyond and beside the target for the ball and fallen
blocks; any perimeter catcher must be a visible collider. Keep supports below
the action silhouette. No invisible containment walls.

Starting production dimensions: 0.8 m block sides, three blocks with touching
support faces, and a 0.28 m ball radius. The launcher deck is approximately
0.45 m above the floor; its exposed lip is roughly 0.8–1.2 m before the tower's
front face. These are initial geometric design values, not validated solver
settings. Adjust deck/lane/aim after physics trials if needed, recording the
change and rebuilding both variants. Keep rigid dimensions constant in a run.

The projectile is dynamic from the start, resting on a passive deck. A visible
driven paddle slides along a visibly supported guide behind it. The paddle's
contact supplies the launch impulse; the ball rolls/slides across the deck and
leaves its lip under gravity. Do not inject a release velocity, reparent the
ball, switch it from a keyed pose into dynamics, or key its flight. Record both
paddle separation and deck departure as distinct observed transitions. The
paddle stops on its guide, then retracts slowly without touching the departing
ball. Do not imply an unmodelled spring drives it: the guide and actuator housing
identify it as a powered mechanism.

| Beat | Readable action | Timing rule |
|---|---|---|
| Establish | Supported ball, grounded launcher and intact tower are simultaneously visible. | Begin with a short stable dwell, nominally 0.5 s. |
| Anticipation | Paddle retracts slightly along its guide, leaving the ball supported. | Nominally 0.2–0.3 s; it must not move the ball at a distance. |
| Launch | Paddle advances and visibly touches the ball before the ball accelerates. | Tune driven motion in physical seconds; no normalized timeline stretching. |
| Travel | Ball clears the deck, with a visible downward component under gravity. | Use measured motion; do not insert a pause or ease before impact. |
| Contact / miss | Contact occurs in an unobscured silhouette; the miss shows daylight between ball and tower. | Identify from evaluated states and native frames, not a scheduled beat. |
| Response | Contact changes ball/block motion; support loss propagates through the tower. In the miss, the tower stays still. | Immediate physical consequence; no collapse keys or variant timer. |
| Settling | Fallen blocks and ball respond to actual floor contacts and friction. | Continue until the frozen settling gate passes. |
| Ending | Hold the resulting supported arrangement; the intact miss tower provides the comparison. | Include approximately 0.75 s of settled outcome, then end. |

Target a compact first trial of about 8–10 s, but **final physical duration is
authoritative**. Extend simulation if necessary for settling; shorten a proven
settled tail to the readable ending. Deliver contact and miss with the same
duration, using the longer required result, rounded upward to a 30 fps frame
boundary. Retain native motion and the 240 Hz state clock. Do not fill 30 s or
fit the existing score. These provisional beat times are never event truth.

## Appearance and diagnostic views

- Use matte warm-grey floor/wall (`#B8B2A6`), dark graphite mechanism
  (`#30383B`), muted teal ball (`#267E86`) and warm ochre blocks (`#C69047`).
  Use colour as a stable object-family cue; no random glossy materials.
- Suggest rubber for the ball, painted wood for blocks and painted metal for the
  launcher. Set actual mass/friction/restitution in the physics configuration;
  the visual material names do not prove effective collision response.
- Use small render bevels, about 1% of the block width, with physical shapes and
  visible surfaces agreeing within the validation tolerance. Never use a bevel
  or lighting to disguise collider mismatch. Keep the ball smooth and its radius
  invariant.
- Use one broad key light from above/front-left and restrained fill. Preserve
  contact shadows at the deck, tower base and floor. Use an ordinary matte back
  wall only if it clarifies scale/depth; no floating props, text, branded assets,
  bloom, depth of field, motion blur or animated camera.
- Beauty camera: fixed perspective, approximately 50 mm equivalent, looking
  downward about 20–25 degrees with enough horizontal angle to expose both the
  launch lane and lateral miss gap. Frame the complete motion envelope with
  approximately 10% margin, keeping the mechanism, tower and final rests visible.
  At 640×360, aim for at least 24 pixels across the ball and a clearly visible
  miss gap of at least 12 pixels at closest passage. Measure these on renders;
  camera placement must never conceal a physics failure.
- Diagnostic views: fixed lane-side orthographic view for release/gravity/floor
  support; fixed top orthographic view for aim and the closest miss gap; fixed
  target three-quarter view for block contacts/settling. Use a sharp, neutral
  material override with contact shadows. Diagnostic overlays belong in review
  artifacts only; beauty clips contain no IDs or debug labels.

## Matched controls and catalogue dispositions

For the hero, retain seed, dimensions, masses, collision materials, solver,
timing, lights, camera, tower and floor across contact, near miss and no launch.
Only the launcher's lateral aim/placement changes for the miss; translate the
supported launcher assembly together so the ball remains properly seated. Use a
gap visibly clear at preview size and independently positive in physical units.
No launch disables paddle advance in the same scene and must leave the tower
stable. An intact miss tower does not suppress genuine later ball–floor contact
or its eligible Foley. Existing scored IDs and sonic identities persist; added
actuator/support/scenery objects are silent and never acquire motif ownership.

| Exact recipe | Production disposition | Positive / reject pair |
|---|---|---|
| `01_head_on` | Opposed supported decks and exposed paddles launch dynamic balls along one lane; collisions determine the outcome. | Accept momentum/material-dependent response after visible contact; reject mirrored retreat keys, hovering endpoints or compulsory recoil. |
| `02_near_miss_twins` | Use the head-on mechanism with matched `contact` and `near_miss` aim settings; `default` remains the miss interpretation. | Accept visible positive clearance with no ball–ball impact; reject contact Foley on a miss or different hidden forces between variants. |
| `03_passing_ascent` | Two separated visible inclined guides carry supported, explicitly driven lift carriages upward/downward; scored bodies stay attached visibly. | Accept powered motion with continuous carriage support and a clear passing gap; reject unsupported constant-height/linear flight or detached moving decoration. |
| `04_orbital_approach` | A grounded turntable and visible radial arms drive the two orbiting bodies inward and outward. Bodies remain visibly mounted and are labelled driven in evidence. | Accept clear mechanical orbital motion without collision; reject claiming keyed arcs are free dynamics or hiding intersecting arms/bodies. |
| `05_bouncing_staircase` | A visible release support/paddle starts a dynamic ball above supported descending steps; gravity and actual impacts determine its route. | Accept step contact before each bounce and a supported ending; reject keyed parabola resets, timed upward impulses or a final airborne freeze. |
| `06_sliding_contact` | A paddle starts a dynamic slider on a continuous grounded surface; friction slows it into a supported resting region. | Accept measured material-dependent deceleration; reject arbitrary constant-speed travel followed by floating lift-off. |
| `07_shape_contrast` | Keep the large supported box as the scale reference; supported launchers initiate the small and high moving bodies on physically clear lanes. | Accept stable dimensions and readable size-dependent clearances; reject moving obstacles without cause, rescaling bodies or hiding an unsupported high path. |
| `08_domino_cascade` | Six upright dynamic tiles rest on the floor; one exposed driven striker starts a contact-driven cascade. | Accept neighbour contact/support loss before each topple; reject independent per-tile animation clocks or sideways sliding as a substitute for toppling. |
| `09_breathing_crowd` | Eight bodies are visibly mounted on radial driven carriages with grounded guides; a single in/out cycle ends at rest. | Accept an explicit supported kinetic sculpture with nonintersecting paths; reject interpreting synchronized keys as collective unforced physics or emotion. |
| `10_projectile_tower` | Produce the selected hero, matched aim-only miss and no-launch control above; `default` is contact. | Accept paddle contact, gravity-governed travel, consequential collapse and floor-supported rest; reject the launcher-as-prop, timed collapse, midair stopping or miss collapse. |

Every recipe gets native 30 fps previews and independent validation of its own
motion class; driven motion is permitted only where the visible mechanism and
exported classification explain it. Retain the legacy choreography as explicitly
labelled legacy assets. Catalogue support additions must not silently replace
existing scored objects. Quantities such as step dimensions may change only with
recorded source changes and regenerated geometry/music-input hashes.

## Review pairs and delivery gate

| Feature | Accept | Reject |
|---|---|---|
| Contact visibility | Ball–paddle and ball–target interfaces remain visible before and after contact in full-speed playback and diagnostics. | Props, blur, cropping or camera alignment obscure the contact; a still is used as proof of correct response. |
| Attachment / release | Dynamic ball is visibly seated; direct paddle contact supplies acceleration and subsequent flight is continuous. | Ball starts independently beside the launcher, changes scale/position at release or loses velocity through a kinematic reset. |
| Response timing | State evidence and frames place response within the justified solver/sample uncertainty of contact. | Target waits for a story timer or collapses with no launch. |
| Ending | Consequences remain legible and all free bodies are supported with settling verified. | Unsupported frozen bodies, fading before unresolved motion, or arbitrary extra time imposed by the music. |
| Set design | Sparse workshop explains support, direction and energy source; the action dominates at 640×360. | Gradients/props decorate an unexplained mechanism, random shine obscures shape or debug text remains in beauty output. |
| Miss | Gap is physically positive and visually unambiguous; tower remains stable; subsequent genuine floor impacts are retained. | Ambiguous apparent hit, collapse on the contact timer, or blanket removal of all miss contacts/Foley. |

Review complete silent native-cadence clips, contact windows and neutral/beauty
passes against exact render hashes. A successful render, attractive still,
metadata check or sampled-image review cannot establish continuous-motion
quality. Record automated, model-visual and human judgments separately; leave
unobserved motion and human audition gates unverified. No composition, Muse/EEG
development or human approval is performed by this brief.
