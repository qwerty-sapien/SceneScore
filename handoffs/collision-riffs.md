# Original collision riff audition handoff

User feedback on Jam e938fe62-df2c-4b9d-93b1-738dce23fc78 authorizes a new melody and meaningful contact sound. See docs/decisions/0013-collision-riff-audition.md and reports/collision-riffs/DELIVERY.md.

Entry points: modules/arranger/collision_riffs.py; tools/prepare_collision_riffs.py; packages/audio/riff-voices.ts and riff-binding.ts; tools/render_collision_riffs.ts. Default studio catalogue references the separate riff-studio assets; original piano bundles and production/frozen routes are preserved. Rebuilding the base studio alone restores its original catalogue; make demo then regenerates the riffs only for the eligible 30-second legacy selection.

Final listening artifacts: artifacts/collision-riffs/{guitar,vibraphone}-final/Pocket-Workshop-DRAFT.mp4 and DRAFT-mix.wav. Editable scores: artifacts/collision-riffs/scores-v2. Human listening/approval remains pending; no deployment performed in this task. Browser exports remain unverified due a Chrome extension UI block. Normal root typecheck has an unrelated training-app ambient Vite type error; explicit Vite client types pass. Actual test counts and cleanup are in delivery evidence. Do not label the legacy animation physically validated or promote these audition drafts to human-approved performance.
