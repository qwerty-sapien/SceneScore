# Canonical product specification — revision 0.1

Authority: current user request and `.brief/prompts/00_foundations.md`; seed values are proposed designs, not measurements. This is an animation-to-soundtrack authoring and performance tool using ocular gestures, not a game or mental-state detector.

## Sixty-second demo story
0–10 seconds: select a prepared scene and original sketch, inspect stable object voices and visible source mode. 10–20: preview a proposed mapping and approve its exact version. 20–40: play approach, near miss or contact with distinct musical phrasing and scene-timed Foley. 40–50: deliberately double-blink (or visibly use keyboard fallback); see the pending key change and hear it at the approved boundary without changing gain/articulation. 50–60: stop and export the editable score, stems, synchronized result and provenance. This is a planned story, not an existing demo.

## User interactions and scope
MUST: select/import a supported generated scene bundle; inspect geometry evidence; assign persistent sonic identities; select original symbolic music and an exact brush groove; edit/preview/approve a plan; unlock browser audio; play/pause/seek; arm/disarm controls; inspect queued/suppressed actions; export editable score, separate stems and synchronized audiovisual output. Display mode, quality, plan approval and timing state. All MUST acceptance obligations are enumerated in [requirements.yaml](../requirements.yaml).

MUST: default `double_modulate_mvp` queues `request_modulation` at the next approved bar/phrase. Preserve master gain, articulation and expression preset. Singles and triples cause no action. Reject ambiguous trains. Signal-quality failure suppresses new controls while music continues. Natural blink clusters can resemble deliberate gestures: there is no guaranteed intent inference.

MUST: key, chord, register, dynamics, articulation, phrasing, ornamentation and timbre remain distinct controls. Symbolic pitched voices adapt via approved harmonic transitions; unpitched brushes and scene-timed Foley are independent. Random choices are bounded, seeded and logged. Human approval precedes execution of a new or changed plan.

SHOULD: prepare the ten recipes, four expanded sketches and three grooves for testing if event rules permit. Hero default is `10_projectile_tower`, 30 seconds, with `tilted_blue_v1` at 96 BPM and `brush_swing_light_v1`. The near-miss variant demonstrates a non-impact. Other sketches are `almost_then_away_v1` (20s), `corner_pocket_rag_v1` (16s, straight eighths), and `velvet_orbit_v1` (24s). These are unrendered, unauditioned seeds; durations are nominal. Do not force all forms into one duration or groove.

EXPERIMENTAL, disabled: triple-blink expression and amplitude-derived controls; triple mode requires independent confusion/latency testing, sequence closure before commitment and no double action for the same triple. Optional ±5-semitone transitions require audition; default eligibility is ±2 only. No online model adaptation during the demo unless separately validated and explicitly enabled.

## Signed motion policy (reversible default)
An approved plan chooses a stable focus object, world Z axis, causal lookback and deadband. At the request's scene timestamp, positive evaluated vertical velocity permits +2 semitones; negative permits −2. Zero/deadband/unknown motion or no approved edge means a logged no-op. Store the sign, sampled interval, policy version and chosen edge; do not reinterpret at execution. Numerical lookback/deadband and bounded register range must be set and tested in Phase 2D before activation. Pitch class wraps modulo 12; signed interval and register are separate. This is an explicit creative mapping, not acoustic physics.

## Exclusions and unresolved choices
No game/Flappy Bird import, stress/emotion inference, mind reading, general DAW, arbitrary-video reconstruction, single opaque audio file as the only score, extra hardware purchase, GPU/database/cloud requirement or plugin marketplace. The multimeter is out of scope and must never connect to a worn headset.

Unresolved: actual Muse generation, transport, channels/units/rate and Bluetooth permission; Blender binary/version; RAGTM runtime reproducibility and third-party/data reuse terms (source and root license inspected in LINEAGE); API credentials/billing/model ID; participant sessions/consent; target browser/audio output; organizer preparation rules. [STATUS](STATUS.md) records evidence and affected tracks. Historical Muse 1 and successful blink-to-jump are user reports, not verification. Defaults can change through a decision record with affected tests; `.brief/` remains unchanged.

## User clarification preserved for subsequent phases

The core studio MUST work with keyboard and clearly labelled replay; Muse is an optional deliberate-blink conducting track. Hardware absence cannot block authoring, score playback or export. There is no directional thought-control interface: geometry supplies the motion policy, and gestures request discrete prepared actions.

Predominant musical identity is original blues/ragtime-derived swing. The named inspirations are expressed as chosen creative traits, not copied tunes or artist emulation: Brubeck → selective metric displacement and occasional asymmetric accents; Evans → spacious chord voicings and economical inner-voice motion; Mingus → blues-rooted call/response and contrasting ensemble density; Carmichael → clear, singable original melodic arcs; Monk → purposeful rests, angular original motifs and selective dissonant accents; Gilberto → restrained, steady bossa-inflected accompaniment; Lyra → lyrical original phrases over gently syncopated accompaniment. Bossa remains an accompaniment color rather than replacing the swing identity. Use rhythmic variation selectively, retain space and melodic coherence, and audition originals independently. No new music was composed or auditioned in Phase 1.

Authority: the user's six explicit requirements in the later documentation-stage request. The unavailable Kinetic Jazz ZIP has not been reconstructed or represented as read. The available SceneScore pack governs this authorized Phase 1; these direct product requirements remain binding.

## Personal trainer clarification (2026-09-13)

The user authorized the [minimal B-only trainer](decisions/0015-minimal-personal-trainer.md):
93% is an advisory stopping target, and compatible saved weights remain usable
below it or without evaluation. The next Arm loads the latest compatible
checkpoint; live weights stay fixed while armed. This explicit exception does
not change musical-plan approval, signal-quality requirements or independent
accuracy claims. Training records and model artifacts remain local.

## Manual key-change audition (2026-09-13)

The user authorized a **Change key** button during ordinary playback, hidden
when the local companion detects Muse. For this manual request, a logged seeded
choice among feasible prepared ±2 transitions replaces geometry direction and
uses the existing chord-transition scheduler. Draft audition needs no detector
arming and creates no approval. Live double-blink semantics remain as specified
above. See [decision 0017](decisions/0017-manual-key-change.md).

## Full-library audio and effect balance (2026-09-13)

The user authorized original, visibly labelled video-only piano accompaniment
for videos without prepared scene scores or embedded audio. Live scores and new
exports place effects 20% above the ducked music RMS; music fades to 80% of its
normal amplitude around effects. See [decision 0018](decisions/0018-full-library-audio.md).
Historical embedded mixes and frozen review samples retain their original audio.
