# Piano/guitar passage replacements — 2026-09-13

User-authorized revision of keyboard.html. Supersedes keyboard-scene-timeline.md's additive cue design. The original sketch now has exactly two lanes: felt-piano accompaniment (left-hand roots and chord voicings) and fingerstyle-guitar melody/ornaments. No brushes, separate bass instrument, Foley or cue overlay is emitted. This remains manual keyboard audition, with approval:null.

## Musical rules

1. Approach replaces piano from two beats before the marker through a half-beat resolution: five ascending semitones land on the local chord root at the marker. The whole anticipation targets the key scheduled at arrival.
2. Near miss replaces both parts with silence for the half beat immediately before the marker. Notes crossing the window are cut, not just new attacks suppressed. Playback resumes at the marker.
3. Separation replaces piano for two beats from the marker: chromatic descent from the local chord's third to root, with diminishing velocity.
4. Contact replaces guitar for two beats with a local dominant-seventh chord.
5. Sustained contact replaces both parts for two beats with one piano root and one guitar melody note, using their natural ringing decay.
6. Contact release replaces guitar with a light descending motif that resolves to the local root.
7. Rebound replaces guitar with a bounded turn/trill figure resolving to its root.

Local chord roots follow the original I/I/IV/V phrase. All replacement pitches follow transposition; key boundaries split and retune held notes. Most recently added marker wins per affected lane; near-miss silence always wins. Unaffected lanes continue. Anticipation and hold windows wrap across the ten-second loop seam. The UI shows actual compiled piano/guitar notes and highlights replacement notes.

Edits rebuild future passages at the current playhead with a nominal 12 ms scheduling offset and an 8 ms fade of superseded sounding notes. A future marker does not play an unrelated instant preview. Audio already heard cannot be changed; passed anticipation becomes available on the next loop. Deleting markers restores the original passage. Key controls retain the next-bar boundary. Controls remain Q/W/E/R for guitar ornament, A/S/D for guitar touch, arrows for key, and hover plus 1–7 for scene markers.

The compiler is local and bounded to neighboring cycles, with at most 64 markers. The take records its first 120 seconds while playback continues. The existing suspension/stall guard still stops interrupted playback. Export synthesizes recorded symbolic notes; it is not physical audio capture, and the live edit fade is not a measured output-latency claim.

## Verification

Commands run: `npm run typecheck`; `node --import tsx --test packages/audio/tests/keyboard-score.test.ts apps/web/src/keyboard/player.test.ts`; `node node_modules/vite/bin/vite.js build --config apps/web/keyboard.vite.config.ts`.

Final verification: typecheck and standalone build passed; 14 tests passed. Tests cover two-instrument routing, chromatic direction and timing, replacement rather than overlay, near-miss silence over active notes and loop seams, sustained notes, overlap precedence, key changes during holds, arrival-key anticipation, live replacement cleanup, continuous looping, export bounds and stall handling.

Actual procedural PCM synthesis at 8 kHz, maximum UI gain −6 dB: seven effect-plus-duet variants, peak 0.588737309, minimum RMS 0.074688378, finite/non-silent/unclipped. Twelve baseline ornament/touch variants also passed, peak 0.351660848. These are sample-array results, not listening or speaker measurements. Browser interaction and listening NOT_RUN; previous CUA inventory has no connected browser. Human audition AUDITION_PENDING. Full root Python suite and shared contract rerun NOT_RUN for this scoped revision; shared schemas and dependencies are unchanged.

Initial checks caught unavailable TypeScript findLast library support and a separation endpoint being clipped; both corrected. Task files: packages/audio/keyboard-score.ts, keyboard-scenes.ts, tests/keyboard-score.test.ts; apps/web/src/keyboard/player.ts, player.test.ts, main.tsx, style.css. Build output: artifacts/keyboard-web/keyboard.html. No task server, browser tab, container or background service started; finite verification sessions exited. Existing unrelated working changes preserved.
