# Runbook — Phase 1 frozen harness

## Local install and checks

Use /Users/agent/Desktop/SceneScore as the root. Existing Desktop interpreter: /usr/local/bin/python3 (3.13.7); Node 24.14.0, npm 11.9.0 and uv 0.11.28. No carrier upgrade was performed. .python-version and Python range bind 3.13; exact dependency versions are in uv.lock and package-lock.json.

Run `make install` (or `make install PYTHON=/absolute/path/to/existing/python3.13`). It uses locked uv sync without managed-Python downloads, npm ci with lifecycle scripts disabled, and generated TypeScript. Required tools are uv, npm, Node and the bound Python. `make doctor` reports software requirements separately from optional external tracks. `make test` runs shared fixture checks, Python tests, lint, TypeScript typecheck and the minimal shell build. `make check-locks` verifies locked resolution and installed metadata. `python tools/verify_sources.py` checks immutable planning inputs.

`PYTHONPATH=src .venv/bin/python -m scenescore.cli run-task --task 01 --check test-contracts` records bounded phase ownership/dependencies/results at artifacts/harness/task-01.json. It does not launch later phases or merge workers. `make dev-replay`, `make assets` and `make demo` deliberately exit nonzero with NOT_IMPLEMENTED until the required domain modules exist. No recorder, scene, music or live detector is hidden behind those commands.

Optional service skeleton: `make service` binds 127.0.0.1:8765. Before starting, record the exact process/session identity; stop that process and verify exit before ending the task. In-process TestClient tests do not leave a server listening. The web shell is not a performance UI. Do not interpret a Vite build as audio/visual output validation.

## Configuration and hardware

.env.example has blank RAGTM_PATH, BLENDER_BIN, Muse transport/board/channel/unit/rate and OPENAI_API_KEY/OPENAI_MODEL placeholders. No application code automatically sources .env in this phase; supply environment variables explicitly without committing secrets. RAGTM defaults to the nested source path for read-only presence checks only. Never run its optional recording-upload path blindly.

Doctor consumes the immutable host profile when present, without re-probing captured OS/architecture facts. Blender binary/bundled Python, Bluetooth permission and real audio unlock/output remain unverified until explicitly exercised. Historical Muse 1/256Hz configuration is not verified device evidence. Verify actual channels, units, rate, clocks, consent and fit before real capture. Keep untouched raw EEG/labels in ignored private_data; never upload raw EEG or connect a multimeter to the worn headset. Human labels must remain independent of detector output; split complete sessions/refits before training or final evaluation.

API credentials/model pair are not configured in the observed environment. Do not invent a model ID or infer API billing from a ChatGPT subscription. Phase 2D must run a bounded structured-response preflight for its actual configured model and validate locally. Missing API access leaves fixture/manual plans usable. Approved plans play locally without external calls.

## Next phase instructions — do not auto-launch

For optional Muse track: "Read AGENTS.md, docs/VISION.md, docs/CONTRACTS.md, docs/EVALUATION.md, docs/tasks/02A.md and .brief/prompts/02A_muse_acquisition.md. Execute Phase 2A only from the contracts-v0.1 base in its own worktree. Treat planning/ and .brief/ as immutable, inspect the nested RAGTM source read-only, use the frozen interfaces and stop at the 2A exit gate. Report hardware checks not performed honestly."

For each of 02B/02C/02D/02E, substitute its task card and exact prompt from OWNERSHIP; authorize that track explicitly. Once authorized, those tracks may work in separate worktrees from contracts-v0.1. Integrator mounts module routers and owns shared schemas/locks/scripts/status. Local workers request changes in docs/requests/<track>/ and hand off exact evidence. No CPU-heavy Blender renders during participant capture. 3A requires real independently labelled sessions; 3B requires 2B–2E and a 2A baseline or labelled replay/keyboard; trained detector optional. 4 audits the integrated product.

## Event preparation and teardown

Organizer rules remain unverified. Record which code/data/models/music/renders predate the event; do not present existing assets as event-day work. The suggested five-hour allocations in the immutable README are planning assumptions, not measured completion promises. Keep one scene/score/groove, coherent original swing identity, prepared double-blink modulation and keyboard/replay fallbacks central. Cut scope if prior work is prohibited.

Before every final response, terminate and verify every task-owned job/container by exact identity. Reuse suitable Docker images and honor the image-count/lifecycle policy. Phase 1 used bounded installation/build/test commands and in-process service tests only; no persistent server, worker or container was started.
