# Original symbolic music and local audition rendering

Phase 2C provides four original draft forms, an exact three-groove catalogue, complete lead/bass/brush/object-marker events, and actual procedural WAV/MIDI exports. Every draft remains **AUDITION_PENDING**. Generated sound is an auditionable technical fallback; no human listening judgment, instrumental realism, live browser playback or synchronized audiovisual demo is claimed.

## Public interfaces

`catalog.get_composition(id, version=1, variation='base')` returns canonical contract 0.1 `CompositionSpec`. Exact IDs: `tilted_blue_v1`, `almost_then_away_v1`, `corner_pocket_rag_v1`, `velvet_orbit_v1`. Versions must be integer 1; unknown IDs/versions/variations fail. Variations are `base`, `sparse`, `animated`; retain the exact returned bytes/hash when approving a variation, since the catalogue identity is shared and the content/provenance differs.

`catalog.get_groove(id, version=1)` returns canonical `BrushGroove`. IDs: `brush_swing_light_v1`, `brush_straight_rag_v1`, `brush_ballad_sparse_v1`. No fuzzy lookup, embeddings, remote calls or downloaded samples. `list_catalog()` provides exact IDs and the four registered procedural presets.

`catalog.build_score(id, version=1, variation='base')` returns module document `SceneScoreMusicScore` version 1. Its `composition` is canonical; `parts`, motifs, chord symbols, rests, phrase roles, independent expression lanes, preset recipes and loop/tail instructions supplement the deliberately smaller frozen schema. CompositionSpec.notes is the complete lead melody; the supplemental parts and resolved events contain accompaniment. No fields were silently added to the shared schema.

`events.resolve_events(composition, groove, plan_id='manual-audition', object_id='object-motif', humanize=True, variation='base')` returns canonical `ScoreEvent` records. Pass the selected variation explicitly. Lane IDs are `piano_or_lead`, `bass`, `brushes`, `object_motif`. Bind the latter's stable ID to the approved scene object in the arranger; the default is a visibly synthetic authoring identity. This function honors supplied canonical melody/harmony edits and rebuilds bounded accompaniment; it does not activate or approve a plan.

`events.transpose_events(events, semitones, min_pitch=28, max_pitch=96)` returns copied events, changing only note pitches. It does not change dynamics, articulation, expression, brush events or scene-time Foley. Integrator/arranger owns eligible ±2 edges, signed scene evidence and exact approval. No mixed waveform is pitch-shifted.

`render.render_events(events, output_wav, *, duration_s, sample_rate=48000, output_root=None, budget=None, cancellation=None, exact_event_ends=True)` renders a short canonical event candidate to a single PCM WAV and returns `{'asset': AudioAssetManifest, 'measurements': ..., 'audition_status': 'AUDITION_PENDING', 'tail_s': 0.35, 'input_events_sha256': ...}`. It maps arbitrary input lane names to synth parts by the exact `timbre_id`, leaves input records unchanged, checks register/duration/sample-work budgets and uses the same scoped no-overwrite/cancellation lock. Foley is explicitly unsupported: filter it only for a clearly labelled **music-only** audition, never claim the result is a synchronized full candidate. Caller owns exact plan approval and RunManifest/evidence context. For an arranger-owned output path pass its scoped `output_root` explicitly. File duration includes the 350 ms tail; supplied `duration_s` is the candidate musical timeline. Candidate mode `exact_event_ends_v1` places pitched attack/release fades inside each declared event interval, with no pitched samples at or beyond that event's absolute end (sample-grid rounding is at most one frame). Explicit `legato` notes retain a 35% sustain floor beneath the natural partial decay until their final fade, so long prepared tonic notes are not cut off by the catalogue gate ratio. Brushes retain their recipe/tail semantics. The returned `pitched_envelope_mode`, renderer version, asset ID and provenance config hash distinguish this mode. `exact_event_ends=False` explicitly requests the older catalogue gate/release behavior for comparisons; `synthesize` and normal catalogue exports continue to default to that unchanged behavior. No prior 48 kHz catalogue output was regenerated or relabelled.

`api.router` is a read-only FastAPI catalogue/score router; `health()` reports available symbolic/procedural tools and unverified audition. Integrator owns mounting. No job starts on import. There is intentionally no unbounded HTTP render endpoint or activation path.

## Authoring and creative choices

The opening two-bar motifs and complete harmonic maps preserve the supplied new seeds. Four manually authored contrasting answers, harmonically adjusted returns, turnarounds, explicit rests, bass lines and economical three-note comping voicings complete the forms. Tilted Blue is the 12-bar, 96 BPM C-blues hero (30 seconds); Almost, Then Away is eight bars at 96 BPM (20 seconds); Corner Pocket Rag is eight straight, syncopated bars at 120 BPM (16 seconds); Velvet Orbit is eight bars at 80 BPM (24 seconds).

Predominant blues/ragtime-derived identity retains distinct straight-rag and ballad colors. The user’s inspirations are recorded as original design traits: Brubeck’s selective displaced accents, Evans’s spacious economical voicings, Mingus’s call/response density contrasts, Carmichael’s clear arcs, Monk’s angular answers and rests, Gilberto’s restrained steady accompaniment, and Lyra’s lyrical phrases. Bossa-colored comping is restricted to selected Almost/Velvet bars and never replaces the lead timing policy. These are intentional compositional choices, not listening assessments or artist imitation claims.

Sparse variations reduce answer/accompaniment density and velocities while retaining call identity. Animated variants selectively accent existing notes, animate the bass and allow no more than one chromatic pickup per two-bar answer; no random melody generation occurs. Melody, harmony, dynamics, articulation, ornamentation and timbre remain independently editable. Chord intervals above 12 remain available as extension/voicing inputs.

## Clocks and synthesis

PPQ is 960; C4=MIDI60. Symbolic ticks are unswung quarter-note ticks. Tempo conversion supports piecewise maps; these four exports use explicit constant maps. Swing warps eligible note/hit onsets and endpoints once. Continuous sweeps, resolved events, scene-time Foley and the straight rag are not shifted. Humanization is deterministic (groove seed 13007), bounded to ±6 ms/±3 velocity, loop-contained, excluded from sweep boundaries and separate from scene effect synchronization.

Preset IDs: `keyboard_damped_v1`, `bass_pluck_v1`, `object_bell_v1`, `brush_noise_v1`. Damped partials and plucked bass are band-limited by dropping partials near Nyquist; brushes use seeded smoothed filtered noise. Continuous sweep noise never resets at each bar. The exact-length `brushes-loop.wav` has 15 ms boundary fades, with zero endpoint samples, while the main mix/stems share a declared 350 ms release tail. This is a fade-based technical loop preparation, not an auditioned perfect loop. No normalization hides intended dynamics. Initial dynamics are -12 dB plus conservative per-part synthesis gains. File peak limits do not establish physical listening safety.

Reference exports are mono PCM16 at actual 48 kHz; 8–48 kHz is supported and recorded. The procedural synth does not require a sound device. MIDI format 1 includes tempo, meter, named parts and resolved swing/humanization. Lead and comping use separate channels to avoid shared-pitch note-off collisions; bass uses its declared 0.70 gate and other pitched parts use 0.82. Continuous brushes are explicitly approximated as drum hits; brush JSON envelopes remain authoritative. Renderer runtime and sample rate delimit deterministic hash scope; cross-platform floating-point bit identity is not promised.

## Commands

From the repository with its locked environment installed:

```sh
PYTHONPATH=.:src .venv/bin/python -m pytest modules/music/tests -q
.venv/bin/ruff check modules/music
PYTHONPATH=.:src .venv/bin/python -m modules.music.render --composition tilted_blue_v1 --variation base --output artifacts/music/new-hero
PYTHONPATH=.:src .venv/bin/python -m modules.music.export_all --output artifacts/music/new-review
```

Outputs must be new paths strictly under `artifacts/music`; existing paths and symlinks are rejected. Direct trusted calls can supply a narrower `output_root`, cancellation event and `RenderBudget`. Per-render runtime defaults to 120 seconds, form plus tail ≤61 seconds, at most 5,000 events, at most 48 kHz and a 64 MiB output estimate; the complete export wave is capped at 600 seconds. One render runs per Python process. The integrator's capability harness must govern concurrency across processes before exposing rendering as an executable service capability. The CLI creates no child process, server, audio stream, container or network connection. Failed/cancelled render calls remove only their own newly created partial output; previously completed exports remain intact. `export_all` handles SIGINT/SIGTERM cooperatively and records its exact PID.

## Evidence and limitations

Each export includes canonical composition/brush/events, complete editable score JSON, MIDI, Markdown lead sheet, five aligned mix/stem WAVs, an exact-length brush loop, measurements, canonical RunManifest and canonical AudioAssetManifest records. `manifest.json` hashes exact persisted files; its own hash is recorded by the aggregate audit rather than recursively included. The audio contains only project-authored notes and procedural synthesis; no third-party sample licenses were assumed. The project has not selected general distribution terms for these original outputs.

Golden fixtures in this module preserve all four canonical compositions, all three grooves, the first twelve resolved hero events and a short actual PCM render's measured statistics. Unit tests independently parse MIDI, inspect PCM, check peak/RMS/endpoints/duration/stem summation, exercise catalogue errors, harmony totals, rests/registers/velocities, swing state, humanization, pitched-only transposition and render resource controls. A production model/device is unnecessary for this software evidence.

Human review must identify reviewer/date/exact mix hash and compare all three variants for melodic coherence, phrasing, harmony/cadence, event space, marker identity, near-miss tension, brush timbre, balance, clicks and loop/tail quality. Prepared modulations require an additional arranger/integration audition. Browser playback, physical output timing, synchronized Foley and A/V export belong to later authorized integration. No unknown hardware or API state blocks offline symbolic work.
