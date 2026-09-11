# Phase 2C: original symbolic jazz sketches, brush grooves and synthesis assets

Prerequisite: phase 1. Read AGENTS, VISION, CONTRACTS, the symbolic-jazz-arrangement skill and the composition/brush JSON seeds. Own `modules/music/`, its local tests, music artifact outputs and `handoffs/02C.md`. Browser playback implementation belongs to phase 2E; agree the event/synth preset contract and export fixtures without editing its files.

## Objective
Create four short, original, human-auditionable composition drafts with editable notes, harmony and expression. Use the provided new motifs as seeds. They are compositional sketches, not existing commercial tracks. Expand into complete short forms without imitating a named artist or copying a known melody. Generic blues harmonic forms are reusable musical structures; do not claim the form itself is novel.

The four sketches are Tilted Blue (C blues, 96 BPM), Almost, Then Away (F brushed jazz, 96 BPM), Corner Pocket Rag (C, straight syncopated 120 BPM) and Velvet Orbit (D minor, 80 BPM). Keep the straight rag-influenced feel distinct from swung blues. Provide piano/lead, bass, brushes and object-motif stems. Include rest/space so animation events can be heard.

## Required assets
For each piece: authoritative symbolic JSON, MIDI, optional MusicXML when convenient, a rendered audition mix, stems, a human-readable lead sheet in Markdown, and a manifest with tempo/meter/key/harmony, loop boundaries, motif IDs, instrument/preset IDs, seeds, provenance and hashes. Build one hero piece completely before expanding all four.

Use reliable local MIDI generation such as music21 or a simpler supported library after verifying it. MIDI is a note/event interchange file, not an audio recording. Supply an actual renderer for audition, or explicitly mark audio pending. Retain a procedural no-download synth fallback. Optional high-quality piano/bass/brush samples must have documented licences and redistribution rights; do not silently fetch commercial loops or assume installed General MIDI brushes sound realistic.

A damped multi-partial keyboard sound, a short plucked bass and filtered-noise brush approximation are acceptable technical fallbacks, but label their timbral limitations and audition them. Accurate instrumental realism is not an acceptance claim.

## Original score development
Preserve the seed motif identity while composing contrasting answer phrases. Use explicit durations and rests, register limits, chord functions and turnaround/cadence locations. Create two bounded variations per piece: sparse/suspended and animated/accented. Musical quality must be assessed by a person listening to A/B exports; no language-model rating alone constitutes an audition pass.

Represent notes in MIDI pitch numbers and durations/onsets in integer quarter-note PPQ ticks. Document C4=60. Use an explicit tempo map even when constant. Distinguish harmonic chord events from key-region events. Support future transposition/revoicing at a selected boundary rather than pitch-shifting the already mixed waveform.

Define separate lanes for:
- Phrasing: phrase boundaries, rests, cadence targets and density.
- Dynamics: bounded velocity/gain curves with preserved overall headroom.
- Articulation: gate/duration ratio, attack/release and accents.
- Ornamentation: sparse approaches, grace notes and turns within note/rate/register budgets.
- Timbre: registered synth or sample palette parameters.

Do not let every motion update change every lane. Double-blink key changes leave gain/articulation parameters invariant unless a separately approved animation rule changes them.

## Brush rhythm catalogue
Implement exact lookup by `groove_id` and version, not embedding/RAG retrieval. Keep `composition_id`, pitched key and unpitched `groove_id` separate. A brush groove identifies a rhythm/technique recipe, not the tune or a tonal key.

Use the seed techniques: continuous sweep, light tap, accented swish and hi-hat chick. Store start/duration in PPQ ticks, technique, hand/stroke direction when meaningful, velocity/envelope, optional sample ID, sweep/filter recipe, humanization limits and seed. Preserve continuous sweeps as envelopes; MIDI drum hits alone cannot fully encode them. Export MIDI as a declared approximation alongside the authoritative brush JSON.

Catalogue at least light swing, straight rag support and sparse ballad textures. Record which events are swingable. Apply swing exactly once, never to collision Foley, continuous sweep boundaries or already-resolved timestamps. Deterministic humanization must be reproducible, bounded, loop-safe and separately configurable from event synchronization. Provide resolved event timing for exact replay.

Loopable brush audio needs aligned boundaries and controlled crossfades/tails. Use a continuous prepared sweep where appropriate. Do not create clicks with abrupt random-buffer changes. No sample download is required for the initial prototype.

## Rendering and quality checks
Reference sample rate may be 48 kHz, while a live browser context can use another actual rate. Store and handle the real rate. Export stems at matching start time and duration, including a declared tail policy. Keep unpitched percussion unchanged under key transposition. Maintain audible headroom and a conservative initial playback gain; do not claim a dBFS ceiling guarantees safe physical listening volume.

Test bar lengths, ticks, rests, note ranges, velocities, unknown groove IDs, beat/second conversions, swing double-application, transposition of pitched voices only, deterministic generation, stem alignment and sample-peak/clipping checks. A symbolic-only MIDI export does not satisfy a non-silent audio render test. Do not normalize away the intended expressive dynamics.

## Exit gate
At least one complete, audible, approved-capable hero arrangement and all four symbolic forms; exact groove lookup and three authored brush recipes; renderer provenance; golden score/render fixtures; a specific human audition checklist and statuses. Mark anything not listened to as `AUDITION_PENDING`. No arbitrary third-party backing track or black-box audio model is required.
