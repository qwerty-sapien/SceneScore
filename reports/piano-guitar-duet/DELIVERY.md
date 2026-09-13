# Pocket Workshop — piano and guitar duet

The user's follow-up explicitly requires a backing piano part that synchronizes and complements the guitar riff. The revised guitar candidate adds a distinct felt-piano voice and replaces the previous guitar chord layer with piano accompaniment. The guitar hook and scene contact replies remain the lead.

The backing uses guide-tone voicings with at most four semitones of movement per voice between successive bars. Piano chord attacks fall in written guitar phrase gaps, on the same 96 BPM, once-swung 960 PPQ clock. Notes can sustain quietly under the returning guitar phrase. Both piano and guitar leave the contact replies exposed. Piano attacks with less than 180 ms of usable space are omitted, preventing a clipped blip immediately before an impact. The final contact arrangement has 20 three-note piano chord attacks.

Final listening outputs:

- `artifacts/piano-guitar-duet/final/DRAFT-mix.wav`
- `artifacts/piano-guitar-duet/final/Pocket-Workshop-Piano-Guitar-DRAFT.mp4`
- Separate guitar, piano, bass, brush and Foley WAV stems in that directory.
- `artifacts/piano-guitar-duet/scores-final/`: editable score, event data, plans, sound-design binding and MIDI with a separate piano track/channel, for contact and miss.

The normal prepared studio selects “Guitar + piano · Pocket Workshop”. The new candidate ID ends in `guitar-piano-v2`, and the hash-bound sound-design supplement is `collision-riffs-2`. Old version-1 bundles remain supported; original Tilted Blue stays selectable. A changed accompaniment invalidates the exact plan identity. All new exports remain approval:null and AUDITION_PENDING. The prior listening files and reports remain intact.

Verification actually performed:

- 15 targeted Python tests passed, including harmony membership, attack placement in guitar rests, shared swing, bounded voice leading, contact rests, minimum note duration and six-file export integrity.
- 80 audio/Muse UI tests passed, two skipped. The new tests verify distinct deterministic piano synthesis, rejection of a shifted/unbound backing part, separate piano stem naming and synchronized piano/guitar transposition.
- The initial candidate's audio-engine preparation completed with 24.4 MB of cached buffers, including 66 piano buffers, below the existing 128 MiB limit. This used buffer generation in Node; no live AudioContext or output-device measurement is claimed.
- Root lint and production build passed. Typecheck with explicit `node,vite/client` types passed. Normal root typecheck encountered the pre-existing `apps/training/src/main.tsx:9` ImportMeta.env typing error; unrelated training work was preserved.
- All 18 built catalogue entries passed their contract/hash checks after final preparation.
- The final video fully decodes. All six stereo 16-bit WAV outputs contain exactly 1,440,000 frames at 48 kHz / 30 seconds, with no clipping and a common final fade. The independently quantized stem sum differs from the mix by at most two PCM units. Piano PCM is silent throughout each protected contact-reply window. Final audio measurements are in `audio-final-audit.json`.
- The piano is approximately 4.15 dB below the guitar in whole-clip RMS; this is a measured mix balance, not a listening judgment. Human listening/approval, new browser audition and physical output latency remain unverified for this revision.

Exact executed build/render/mux/decode commands and process identities are recorded in this directory's `.job.json` files. Reproduce with the existing `tools/prepare_collision_riffs.py`, followed by `tools/render_collision_riffs.ts` on `contact-brush_swing_light_v1-guitar-piano-v2.json`, and `tools/mux_performance.py`; use fresh render/mux destinations. All owned process groups exited and their absence was verified. No server or browser was started in this follow-up, and no deployment was performed.
