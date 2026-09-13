# Catalog coverage and piano-led staircase — 2026-09-13

## User scope and diagnosis

The user reported static-like staircase audio after the volume change and supplied 78 generated-video paths missing from the gallery. Increasing gain alone did not address sound design. Source inspection confirmed that the staircase used `keyboard_damped_v1`'s legacy additive fallback, continuous filtered-noise brush sweeps, and `arranger_contact_noise_v1`; the piano/guitar edition used a distinct dedicated damped piano waveform. This is an evidenced implementation difference, not a claim that a machine performed a subjective listening review.

All 78 supplied paths existed and grouped into 43 byte-distinct MP4s. Automatic discovery subsequently found four additional completed generated videos. The built and browser-tested snapshot contains 47 videos: 3 scenes with live score bundles (25 soundtrack versions), 12 MP4s with existing mixed audio, and 32 silent renders. All 78 requested source paths remain individually represented in the coverage report. Silent renders are available to watch and explicitly labelled as lacking a prepared live soundtrack; no unrelated music or invented Foley was substituted. Gallery presence does not assert physics validation or human acceptance.

## Changes

- `apps/web/tools/prepare_piano.py` derives three separately labelled piano audition editions, preserving original scene/video/score files. Pitched note timings, pitches, dynamics and object ownership are retained. Continuous sweeps are omitted, other brush events attenuated by 18 dB, and noise contacts replaced with 120 ms wooden modes at original contact onsets. The existing eight-second playback window clips ends and preserves scene timing.
- New `scene_piano_v1`/`scene_wood_contact_v1` identities reuse the dedicated original piano/wood synthesis through `packages/audio/piano-voices.ts`. Legacy renderer IDs and existing recordings are unchanged.
- `packages/audio/piano-binding.ts` validates exact mix and score bytes, renderer version, plan configuration binding and bounded defaults. An old approval cannot silently approve this new sound design. Browser/offline render and export use the same voices and mix; new exports retain mix provenance. No human approval was created.
- Gallery defaults to **Clean piano** for the staircase. Old keyboard editions remain available for A/B. The user can still lower gain or mute either lane.
- `apps/web/tools/video-inventory.mjs` probes actual video/audio streams, hashes bytes, groups exact copies, rejects out-of-scope paths and inventories requested missing files honestly. `catalog.mjs` retains the 78-source request, discovers new generated media outside build mirrors and publishes hash-checked local copies and coverage. It rejects a source that changes during copying. No original media is modified.
- Native original-media player verifies its MP4 before playback. Original mixed audio and silent/no-score states are explicit; returning to the gallery pauses playback. Search matches original source paths and revision labels. Files remain local.

The audiovisual-integration and symbolic-arrangement skills informed the separate audio-stem measurements, exact timing/binding invariants and audition-pending labels. The installed Playwright runtime was reused for bounded browser checks because the earlier CLI reconnect issue is already documented. No dependency, Blender job, model request, cloud upload, or new persistent server was introduced. Other tasks' ongoing Muse, training, manual-key and Blender changes were preserved.

## Verification actually run

| Check | Result |
| --- | --- |
| `node --test apps/web/tools/video-inventory.test.mjs` | 3 passed: deduplication/coverage, path boundaries/build-mirror discovery, revision naming. Synthetic bytes are not represented as actual decoded media. |
| `node --import tsx --test packages/audio/tests/piano-binding.test.ts packages/audio/tests/playback-gain.test.ts` | 8 passed: exact bindings/tamper rejection, dedicated piano/wood synthesis, scoped defaults and manual attenuation. |
| `node --import tsx --test packages/audio/tests/*.test.ts` | 94 passed, 2 skipped, 96 total. |
| `make test-contracts` | Canonical Python fixtures and 70 TypeScript checks passed. |
| `.venv/bin/ruff check apps/web/tools/prepare_piano.py` | Passed. |
| `npm run typecheck` | Passed. |
| `npm run build` | Passed; existing Vite large-chunk warning remains. |
| Real prepared-pair `inspectImport` checks | All 3 new piano bundles accepted with exact matching video. |
| Real Chrome catalog pass | All 47 items played/decoded, no page errors; desktop/mobile checked. |

`apps/web/tools/check-catalog-audio.mjs` runs a bounded isolated Chromium check against the user's existing loopback server. It exports real 48 kHz stereo mix/piano/bass/brush/Foley WAVs for all three eight-second piano editions. All stems have zero clipped samples. Mix peak is approximately 0.2151 and RMS 0.04363. Piano-to-brush RMS ratios are 60.4 dB (swing), 66.7 dB (sparse), and 62.1 dB (straight); the remaining short brush taps are intentionally very quiet. Foley is nonzero and tonal/damped rather than noise-based.

Browser command:

```sh
SCENESCORE_PLAYWRIGHT_MODULE=/Users/agent/.nvm/versions/node/v24.14.0/lib/node_modules/@playwright/cli/node_modules/playwright-core/index.mjs node apps/web/tools/check-catalog-audio.mjs
```

Evidence: `output/playwright/catalog-audio/checks.json`, desktop/mobile screenshots and three groove-named subdirectories containing the actual WAV stems and mix. `apps/web/public/library/coverage.json` contains the exact requested/discovered source inventory. Physical speaker SPL, acoustic/display timing and human musical audition are **NOT_RUN**; approval remains null. A digital PCM pass does not establish perceptual realism or a release gate.

## Resource ownership

The first isolated browser check (PID 89384) closed its browser and exited zero. The user's already-running `make demo` server was reused and was not restarted or stopped. No task-owned development server was launched. Final post-teardown verification is appended after the last bounded browser pass.

Final browser pass (PID 93100) also exited zero, after all 47 playback/decode checks, explicit pause-on-navigation assertions for original-media players, desktop/mobile overflow checks and three complete six-file exports (mix, four stems and provenance JSON). The browser closed successfully. `ps -p 89384,93100 -o pid,ppid,command` confirmed both recorded task processes absent. Final typecheck and catalog-script syntax check passed. The user-owned website remains running with the refreshed build.

A separate exact-source check confirmed the committed 78-path request matches the pasted attachment in order, all three new editions bind the unchanged original bundle bytes, and all 600 pitched source events retain pitch, onset, duration, velocity, dynamics and object identity. All 24 source Foley onsets across the three editions remain unchanged. Only the separately described timbre/brush/contact-tail arrangement changed.
