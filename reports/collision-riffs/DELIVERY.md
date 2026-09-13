# Pocket Workshop — local original-music audition

The normal prepared studio now opens a new guitar-led composition with a separate vibraphone alternative. Twelve new bundles cover contact/miss and the three existing brush grooves; all six original piano bundles remain byte-identical and selectable. Four authored contact cues produce four short wood knocks and twelve owned melodic reply notes. The miss has no collision audio. This changes the soundtrack for the legacy 30-second Jam demo; it does not certify its animation physics or alter frozen Blender/music selections.

## Actual delivery

- `artifacts/collision-riffs/guitar-final/`: 30-second guitar mix, guitar/bass/brush/Foley WAV stems, exact event/plan report and matched `Pocket-Workshop-DRAFT.mp4`.
- `artifacts/collision-riffs/vibraphone-final/`: same outputs with a distinct mallet voice.
- `artifacts/collision-riffs/scores-v2/`: editable composition, fully resolved events, sound-design binding, exact plan and General MIDI approximations for both contact and miss.
- `apps/web/public/riff-studio/`: 18 checked catalogue entries and original matched videos; normal `studio/catalog.json` points to the new default. The built catalogue was also checked.
- `artifacts/collision-riffs/source-final/`: snapshots of the production source used for the delivery.
- `reports/collision-riffs/delivery.json`: exact hashes, measurements, source map, commands, resource teardown and verification scope.

All delivered plans and exports have approval:null / AUDITION_PENDING. The source voices use original local synthesis; no sampled recordings or borrowed melody are used. MIDI is an approximation, with authoritative resolved timing and synthesis parameters retained in JSON. The two final sets of lossless WAVs are byte-identical to the earlier independently checked renders; formatting and stronger source-binding checks invalidated the plan identity without changing sound.

## Verification

- `make test` with a 900-second bound: canonical checks and 70 TypeScript contracts passed; 785 Python tests passed. It then stopped at two bridge tests because the sandbox denied binding a local socket. Rerunning all ten bridge tests with host access passed.
- 78 audio/Muse UI tests passed, two skipped. New pitch, decay, cache-equivalence, contact timing, object ownership, stem names, source binding and stale approval checks passed.
- Final targeted Python suite: 13 passed, including new version-3 export mutations. Final riff TypeScript tests: four passed.
- Root lint and production build passed. `npm run typecheck` remains blocked by the separate in-progress training app: `apps/training/src/main.tsx:9`, missing `ImportMeta.env` typing. `npx tsc --noEmit --types node,vite/client` passed; no unrelated training source or root type configuration was edited by this task.
- Eighteen source and built catalogue entries passed hash, contract and score-binding checks. Original piano bundle hashes are unchanged.
- Both final videos fully decode. Each stereo 16-bit WAV has 1,440,000 frames at 48 kHz (30 seconds). No clipping; mix peaks 0.403604 (guitar) and 0.280637 (vibraphone). Stem sum differs from the separately quantized mix by at most three integer PCM units. Exact event sample anchors, decaying knocks and zero final samples were checked.
- Browser guitar play-through reached 30 seconds. Final instrument switching, pause, seek, resume, near-miss selection and original-piano selection passed. Human listening, model audio perception and measured physical output latency remain unverified. The single last displayed software-drift sample (-22.3 ms) does not establish a 50 ms percentile timing gate.
- Browser export was attempted, but a Chrome extension UI blocked automation. Download completion/file integrity remains unverified. The supplied WAV/stem files were actually rendered using the same voice() function in Node and separately audited; they are not claimed as browser downloads.

## Reproduce

Run from the repository root with `PYTHONPATH=.:src` and the existing `.venv`:

```sh
PYTHONPATH=.:src .venv/bin/python tools/prepare_collision_riffs.py --scores artifacts/collision-riffs/scores-v2
node --import tsx tools/audit_collision_riffs.ts
node --import tsx tools/render_collision_riffs.ts apps/web/public/riff-studio/contact-brush_swing_light_v1-guitar.json NEW_GUITAR_DIR
PYTHONPATH=.:src .venv/bin/python tools/mux_performance.py NEW_GUITAR_DIR/DRAFT.json apps/web/public/riff-studio/contact.mp4 --out NEW_GUITAR_DIR/Pocket-Workshop-DRAFT.mp4
npm run build
make demo
```

Replace `guitar` with `vibraphone` for the other sound. Rendering/mux require fresh destinations and preserve existing evidence. `make demo` prepares the selected animation, adds this score only for the eligible legacy 30-second selection and serves the local app. Production playback-window and frozen music routes keep their own scores.

No deployment was performed by this task. All owned CLI process groups are verified absent and all three task-created browser tabs were closed. The original supplied/user browser tabs were preserved. Another workspace action created commit bf4bfc2 during implementation; this task neither created that commit nor reverted it. Final integration fixes and the final evidence may remain uncommitted.
