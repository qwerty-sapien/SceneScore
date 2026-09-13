# Full-library music and effect balance

Authority: the user's 2026-09-13 instruction to equip all videos with generated
or existing audio, make effects 10–30% louder than the base track, and fade the
base track to 20% softer during effects. The user noted that only three videos
had audio.

Every catalog video now has either its prepared scene score, its existing MP4
soundtrack, or original seeded piano generated in the browser. The latter is a
video-only draft fitted to duration, with editable score download and new takes;
it makes no scene-motion or collision inference. No approval is created.

The concrete mix default is 20% above the simultaneous, ducked music **RMS**.
Music gain becomes 0.8; the effects target is 1.2 times that level. This is a
linear signal-level interpretation, not a perceived-loudness guarantee. Music
fades down over 80 ms before each effect and returns over 250 ms after its tail.
Overlapping effects are calibrated as a combined stem; closely spaced effects
hold the duck. The original dry score is the fixed reference, preserving the
existing requirement that key-change requests do not alter gain policy. During
rests, effect calibration uses the full-score RMS reference without adding notes.

Live playback and new WAV/stem exports use the same versioned mix policy.
Historical MP4 soundtracks and frozen review samples remain as saved; the new
mix is not represented as a replacement for those historical artifacts. No
Phase 4 release or human audition approval is implied.

Changes are supplemental audio/catalog behavior; frozen contract 0.1 bytes and
prepared scene/score hashes remain unchanged. Verification and resource cleanup
are recorded in `reports/video-audio-completion/REPORT.md`.
