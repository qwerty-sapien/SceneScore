# Phase 2D: geometry-to-music planning with human approval

Prerequisite: phase 1 fixtures. Read AGENTS, VISION, CONTRACTS and the symbolic-jazz-arrangement skill. Own `modules/arranger/`, its local tests and `handoffs/02D.md`. Work against fixture scene summaries, score catalogues and capability interfaces. Do not edit the Blender exporter, music asset generator, audio engine, service root or shared schemas.

## Objective
Translate a scene and creative brief into an editable, validated musical plan. This does not require training another end-to-end neural model. Build a deterministic mapping baseline and an optional GPT Astra planning adapter that proposes variations over the same bounded representation.

## Inputs and model role
Consume scene objects and their stable identities, world-space geometric properties, compact sampled motion envelopes, pair surface-gap/relative-motion events, selected rendered frames when useful, the actual symbolic music/brush catalogue and the human's creative brief. Never send raw EEG or device identifiers to the model.

The model may request approved capability queries, such as exact event details, score/groove lookup, candidate rendering and validation. It cannot assume unavailable plugins exist, choose arbitrary filesystem paths, install software or execute generated code as an arrangement. Use the phase 1 registry. Implement tools as typed local functions/CLI adapters first. MCP exposure is optional and must wrap existing tested capabilities, with schemas and health checks.

Use a verified OpenAI model ID from configuration and a small capability preflight. Structured outputs enforce shape; separate checks enforce musical and timing semantics. Handle refusal, truncation, unknown IDs, invalid numeric ranges, timeouts and rate errors. Do not silently change model names or API endpoints to get a passing run. An exported summary plus manual JSON-plan import provides a human-reviewed no-API path. The user's ChatGPT subscription is not assumed to provide application API billing.

## Deterministic baseline mapping
Create explicit, editable rules with smoothing and hysteresis:
- Approach/declining surface gap: bounded tension, density or anticipatory ornament; no claim that proximity has one objectively correct musical meaning.
- Near miss: a phrase approaches a cadence and defers/resolves according to the chosen style, with its event time intact.
- Collision onset: synchronized Foley or a registered pitched accent at exact scene time; sustained contact is a separate texture.
- Separation: decay/release or thinning of orchestration.
- Up/down motion: configured melodic-register/contour direction and eligible modulation direction.
- Size/surface area/material tags: an artistic timbre/register mapping within bounds, explicitly not a physical acoustic prediction.

Give objects persistent motif and palette IDs. Limit simultaneous voices and event density. Preserve silence and foreground accents. Smooth frame-level features so distances do not chatter into dozens of musical changes. Phrasing, dynamics, note gate, ornaments, harmony and timbre are distinct lanes with separate bounds and priorities.

## Modulation and expression policies
Default double-blink queues one key-change request, while current gain and articulation settings remain fixed. Consider only a small pre-approved transition graph. A useful first graph allows signed tonic shifts of +/-2 semitones, with optional +/-5 only after audition. Define key mode, tonic pitch class and register movement separately because pitch classes have no intrinsic up/down order. Bound register to prevent cumulative octave drift.

For supported keys, render a brief pivot or dominant preparation and establish the new tonic through a cadence or arrival. Change/revoice melody, bass and harmony consistently. Keep brushes and nonpitched Foley untransposed. A valid chord change within the same key must not be labelled modulation. During a short demo, a clear direct transition into an explicitly established new tonal region is acceptable; do not claim a theory check proves perceived tonality.

Precompute or cheaply compile transitions before playback. No GPT call is required for each blink. The chosen direction comes from the scene around the request time under an explicit aggregation policy, not arbitrary global randomness. Define the direction coordinate frame. A practical visual default is the selected protagonist's projected vertical velocity over the preceding 300 ms, with screen-up made positive and a deadband; a world-Z alternative is explicit. Camera motion and screen/world axis conversion must be handled consistently. This is an artistic policy, not a learned physical law. For ambiguous/stationary motion use the documented approved fallback direction or hold; display which policy acted.

Optional triple-blink toggles a pre-approved bounded expressivity preset at a musical boundary. It must not also fire the double-blink action. Blink amplitude controls remain disabled until independently evaluated. The runtime action parser, rather than the language model, enforces those choices.

## Approval, caching and parameter search
Generate at most a small configurable number of candidate plans, for example three. Each includes an explanation tied to real object/event IDs, changed lanes, bounds, assumptions and uncertainty. Presentable outputs include exact plan diffs and short audition renders. Human approval freezes a content hash. Approve a bounded family of transitions/presets so the live performer need not confirm every blink. A new unapproved plan cannot replace the active one during playback.

Cache by scene/score/brief/model/schema/version and parameter hashes. Use bounded retries, wall-time and concurrency limits. The deterministic baseline and the last approved plan remain available if the API fails. Label cached, manual and live-generated provenance.

An optional Optuna sweep may adjust smoothing, density, voice-leading penalties, gain limits and anticipation length against objective technical checks. Never call such a score universal musical quality. Keep subjective audition ratings separate and record who/when evaluated them. Do not tune EEG model thresholds in this module.

## Tests
Validate IDs, units, times, typed curves, parameter ranges, approved hashes and pitch/register bounds. Test seed reproducibility and cache invalidation when a trajectory changes. Confirm that changing one interaction updates only affected score regions/objects where the policy allows. Ensure identical inputs with the same approved plan produce identical event sequences.

Test missing API keys, unavailable models, malformed schema-valid but musically invalid plans, unknown grooves, refusal, timeout, stale asset hashes, conflicting lanes and repeated requests. The baseline must render usable event output without external service calls. Model text must never mutate code/config/credentials.

## Exit gate
A fixture scene becomes a validated baseline plan and, when credentials allow, an actual schema-validated GPT proposal with review metadata. Manual import/export, deterministic constrained modulation and golden ScoreEvents all work. Provide an honest live-API test status and a human audition handoff. Do not build a multi-agent theatre UI or train an audio model.
