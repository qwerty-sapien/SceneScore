# Integration amendment: full-library audio

User authority and interpretation: `docs/decisions/0018-full-library-audio.md`.
The integrator accepts the catalog/player/audio-engine paths for this request.

- Silent catalog entries receive duration-bound, original live piano with explicit
  video-only provenance; prepared scene scores and existing audio remain available.
- Shared live/offline effect calibration and ducking use version `effect-mix-1`.
  New export reports record that policy without changing approval or score bytes.
- Canonical contract 0.1 is unchanged. Generated video accompaniment advances to
  `video-accompaniment-2`; older catalog seeds remain accepted and new score
  downloads identify version 2. New browser takes do not fetch a model or samples.
- Relevant checks: audio/contract suites, coverage build, full-library browser PCM,
  prepared playback, effect-to-music RMS, stem sum, clipping and teardown.

Historical embedded MP4 mixes are retained, so the new mix setting is heard in
live scores and new exports, not retroactively in frozen videos.
