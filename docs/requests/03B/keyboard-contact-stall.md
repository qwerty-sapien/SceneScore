# Contact playback stall investigation — 2026-09-13

User reported keyboard.html stopping/crashing on event 4. Supplied console messages reference extension loaders and asynchronous message channels; they do not contain a SceneScore exception stack. Exact browser failure remains unconfirmed; no connected browser was available from the established session inventory.

Identified a concrete scheduler workload defect: four contact guitar notes were synthesized synchronously using 14 sine/exponential evaluations per sample. A Node benchmark using the real voice function and a sample-buffer adapter at 48 kHz measured 190.11, 175.37 and 179.22 ms for the chord alone. Additional accompaniment/UI work could exceed the player's existing 200 ms stall guard. Earlier 8 kHz audio checks missed this workload.

Added packages/audio/keyboard-voice.ts with a damped complex-oscillator recurrence for the same fingerstyle partials. It preserves frequency, damping, amplitude, articulation envelope and fade; other instruments delegate to the original renderer. Player scheduling now uses this guitar renderer. Timer exceptions stop cleanly and invoke an on-page error callback; stall stops also explain the interruption visibly. The threshold was not relaxed. Existing scene markers survive a stop. Shared synthesis presets were not changed.

Commands run: direct `node --import tsx --input-type=module -e` benchmark of compileDuet contact notes through voice at 48 kHz (three trials); `npm run typecheck`; `node --import tsx --test packages/audio/tests/keyboard-score.test.ts apps/web/src/keyboard/player.test.ts`; `node node_modules/vite/bin/vite.js build --config apps/web/keyboard.vite.config.ts`.

Final results: typecheck/build PASSED; 16 tests PASSED. Optimized four-note contact synthesis measured 30.03 ms at 44.1 kHz and 14.64 ms at 48 kHz in the test run. Maximum sample differences versus original synthesis were 3.73e-9 and 1.86e-9 respectively. Timing is local CPU evidence, not a browser latency guarantee. Regression tests also cover scheduler exception cleanup and delivery to the UI error callback. Build: artifacts/keyboard-web/keyboard.html. Actual browser reproduction/listening NOT_RUN; root Python/shared contract rerun NOT_RUN for this scoped change.

No task server, browser tab, capture or container started. Finite verification session 3466 exited successfully. The user's existing server on port 5177 was not stopped or replaced.
