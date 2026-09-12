# SceneScore local studio

Prepare from repo root: `PYTHONPATH=.:src .venv/bin/python apps/web/tools/prepare.py --assets-root artifacts --out apps/web/public/studio`.
Run: `npm run dev -- --port 5176 --strictPort`; bind loopback. Stop the exact server when finished. `make demo` is the Phase3 integration entrypoint once implemented.

All data/assets are fetched locally and video bytes are SHA-256 checked before playback. Playback after loading works offline. An unapproved draft has a separate audition/export action. Approving an exact plan is a human action; automated test fixtures do not create human listening approval. Changing scene/groove/focus/register clears approval. Source keyboard/synthetic replay is prominent; live device/replay unavailable options are disabled. Triple/amplitude experiments are off.

Inspect the draft, select a conducting object with meaningful world-Z motion (tower-2 descends around18s; the horizontal projectile holds), enter the real reviewer, approve the exact plan, arm and play. M requests a prepared boundary modulation with invariant gain/articulation. Space toggles approved playback. Synthetic replay is explicitly labelled and requests at18s. This path still needs the user's actual approval in the current session.

Generated public/studio data is ignored, reproducible from verified source artifacts and packaged with the static build. No external fonts, sample files or model requests. See handoffs/02E.md for actual browser evidence and remaining synchronization/human gates.
