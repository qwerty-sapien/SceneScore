# SceneScore video library and local studio

Prepare from repo root: `PYTHONPATH=.:src .venv/bin/python apps/web/tools/prepare.py --assets-root artifacts --out apps/web/public/studio`.
Run: `make demo` for the prepared/built studio on 127.0.0.1:8765. For development, `npm run dev -- --port 5176 --strictPort` binds loopback. Stop the exact server when finished.

## Watch and listen

The homepage is a searchable video catalog. Select an animation, choose a soundtrack version, then press **Watch & listen**. The browser plays the video alongside the prepared, editable score and a separate Foley event stream. Music and sound effects have independent switches. Space pauses/resumes when a form control is not focused. Return with **Video library**; leaving the player stops its audio. Ordinary listening is draft audition, not formal approval.

The catalog builder (`apps/web/tools/catalog.mjs`, run by `predev` and `prebuild`) discovers prepared `studio-catalog-1` catalogs immediately under `apps/web/public/`. It prepares separately versioned clean-piano staircase editions, checks bundle/video hashes, inventories generated MP4s under `artifacts/`, groups exact video copies, and writes the ignored `public/library/catalog.json`. No Blender render or external model runs. Legacy `?music=1` and `?review=1` direct-player views remain available; the gallery defaults the staircase to the new clean-piano edition.

The full generated-video archive is separate from live scoring capability. **Live soundtracks** have matched editable score bundles and independent music/effects controls. **Original audio** plays the existing mix inside an MP4, without separate stems or live conducting. **Live piano** fills clips without prepared scene scores using an original, seeded browser score fitted to the video duration. It is visibly labelled video-only: it does not infer geometry or invent collision effects. All catalog videos must have a scene score, generated piano accompaniment, or embedded audio. Review/trial/diagnostic versions remain distinguishable, and their presence does not imply production acceptance.

`apps/web/video-sources.txt` preserves all 78 paths supplied by the user. New generated MP4s are discovered automatically at the next build; build mirrors are excluded from automatic discovery but explicitly requested paths are still accounted for. The downloadable `/library/coverage.json` records each source path, exact content hash and availability. Original files are unchanged; hash-named playback copies are generated under `public/library/media/`. The verified snapshot contains 60 unique videos (3 scene-score videos, 45 generated piano accompaniments, 12 original-audio exports, zero silent players); counts can grow as other tasks finish rendering.

The staircase's new piano-led edition reuses the dedicated damped piano synthesis from the piano/guitar track, omits continuous brush sweeps, attenuates remaining brush taps and replaces noise contacts with short damped wooden modes at the original scene onsets. Its exact plan/score/voice configuration is hash-bound and exported. The three older keyboard versions remain selectable as **Legacy keyboard**; frozen source bundles and recordings are preserved. All editions remain audition-pending.

## Add a video

Use **Add video bundle** to select a rendered MP4 and its matching prepared SceneScore JSON (`studio-bundle-1`). A prepared sidecar includes evaluated Blender scene data, the score, effects, plan and source bindings. A raw `.blend`, plain MP4, or raw Blender metadata sidecar alone is not sufficient: this UI does not infer geometry or generate a score from arbitrary pixels. **Download video + sidecar** in an existing player gives you an exact compatible pair to import on another browser.

Imports are validated and saved in IndexedDB on this browser/origin; they are not uploaded to a server or shared with other users. They survive reload, but clearing site data removes them, and different localhost ports have different storage. **Remove copy** removes only the browser copy, never your original files. Limits: 120-second scenes, 256 MiB video, 64 MiB JSON, and 12 imports / 512 MiB total. Browser storage quotas may be lower. Playback works offline after the app and selected media are loaded; cold offline launch is not provided.

All data/assets are fetched locally and video bytes are SHA-256 checked before playback. Imports never fetch paths from the uploaded JSON. Importing, downloading or watching does not create human approval. Changing scene/groove/focus/register clears approval. Triple/amplitude experiments are off.

## Optional conducting and export

Expand **Arrangement & conducting** to inspect the draft, select a conducting object with meaningful world-Z motion (tower-2 descends around18s; the horizontal projectile holds), enter the real reviewer, approve the exact plan, arm and play. M requests a prepared boundary modulation with invariant gain/articulation. Synthetic replay is explicitly labelled and requests at18s. Formal performance still needs the user's actual approval in the current session. Muse controls remain optional; this catalog does not establish hardware readiness.

Generated public/studio data is ignored, reproducible from verified source artifacts and packaged with the static build. No external fonts, sample files or model requests. See handoffs/02E.md for actual browser evidence and remaining synchronization/human gates.

Phase 3 export downloads stereo mix, piano/bass/brush/Foley stems and a versioned event/control/automation log. `tools/mux_performance.py` verifies the exact files and matched video before muxing. Draft export has no approval; approved export requires a full playback from the start without seeking. Current full gate and actual evidence are in reports/phase3/GATE.md. Missing assets and changed hashes recover after restoring/reloading the correct bundle.

## Catalog checks

Run `node --import tsx --test packages/audio/tests/catalog-import.test.ts` for import integrity tests. `apps/web/tools/check-library.mjs` is a bounded real-Chromium smoke test: supply an installed `playwright-core` module using `SCENESCORE_PLAYWRIGHT_MODULE` and a running local app URL using `SCENESCORE_CATALOG_URL`. It writes screenshots and checks to `output/playwright/catalog/`, closes its own browser, and does not stop the separately owned app server. Automated audio checks measure rendered PCM, not physical speaker/display latency or human musical quality.

## Effects balance

The user-requested `effect-mix-1` policy places the combined Foley stem at 1.2× the
music RMS during its event interval. Music fades to 0.8× normal amplitude over
80 ms before the effect, holds through its tail, and returns over 250 ms.
Overlapping effects share a duck envelope and a measured gain; nearby effects
hold the duck to avoid repeated pumping. Percentages describe linear signal
amplitude/RMS, not perceived loudness. Original dry score PCM is the fixed
reference, so key-change requests do not modify the effect gain policy.

Live playback and new WAV/stem exports share this policy; stem exports retain
the full mix's calibration and ducking. Export JSON records the policy. Historical
MP4 audio and frozen review recordings retain their original mix. A video-only
piano preview supplies music but has no fabricated collision sound effects.

`apps/web/tools/check-audio-completion.mjs` owns an isolated Vite server on 8796
and Chromium, checks every catalog item's nonzero playback PCM, measures five
representative 48 kHz mixes and their stems, and closes both resources. Set
`SCENESCORE_PLAYWRIGHT_MODULE` to the installed playwright-core module. Optional
`SCENESCORE_PCM_ONLY=1` reruns the three prepared players and mix measurements.
