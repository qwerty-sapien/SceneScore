# Runbook — Phase 2 modules on the frozen 0.1 contracts

## Local install and checks

Use /Users/agent/Desktop/SceneScore as the root. Existing Desktop interpreter: /usr/local/bin/python3 (3.13.7); Node 24.14.0, npm 11.9.0 and uv 0.11.28. No carrier upgrade was performed. .python-version and Python range bind 3.13; exact dependency versions are in uv.lock and package-lock.json.

Run `make install` (or `make install PYTHON=/absolute/path/to/existing/python3.13`). It uses locked uv sync without managed-Python downloads, npm ci with lifecycle scripts disabled, and generated TypeScript. Required tools are uv, npm, Node and the bound Python. `make doctor` reports software requirements separately from optional external tracks. `make test` runs shared fixture checks, Python tests, lint, TypeScript typecheck and the minimal shell build. `make check-locks` verifies locked resolution and installed metadata. `python tools/verify_sources.py` checks immutable planning inputs.

`PYTHONPATH=src .venv/bin/python -m scenescore.cli run-task --task 01 --check test-contracts` records bounded phase ownership/dependencies/results at artifacts/harness/task-01.json. It does not launch later phases or merge workers. `make dev-replay`, `make assets` and `make demo` deliberately exit nonzero with NOT_IMPLEMENTED until the required domain modules exist. Those historical umbrella targets remain placeholders; use the explicit Phase 2 module commands below.

Optional service skeleton: `make service` binds 127.0.0.1:8765. Before starting, record the exact process/session identity; stop that process and verify exit before ending the task. In-process TestClient tests do not leave a server listening. The web shell is not a performance UI. Do not interpret a Vite build as audio/visual output validation.

## Configuration and hardware

.env.example has blank RAGTM_PATH, BLENDER_BIN, Muse transport/board/channel/unit/rate and OPENAI_API_KEY/OPENAI_MODEL placeholders. No application code automatically sources .env in this phase; supply environment variables explicitly without committing secrets. RAGTM defaults to the nested source path for read-only presence checks only. Never run its optional recording-upload path blindly.

Doctor consumes the immutable host profile when present, without re-probing captured OS/architecture facts. Current Blender evidence is recorded below. Bluetooth permission and real audio unlock/output remain unverified until explicitly exercised. Historical Muse 1/256Hz configuration is not verified device evidence. Verify actual channels, units, rate, clocks, consent and fit before real capture. Keep untouched raw EEG/labels in ignored private_data; never upload raw EEG or connect a multimeter to the worn headset. Human labels must remain independent of detector output; split complete sessions/refits before training or final evaluation.

API credentials/model pair are not configured in the observed environment. Do not invent a model ID or infer API billing from a ChatGPT subscription. Phase 2D must run a bounded structured-response preflight for its actual configured model and validate locally. Missing API access leaves fixture/manual plans usable. Approved plans play locally without external calls.

## Next phase instructions — do not auto-launch

For optional Muse track: "Read AGENTS.md, docs/VISION.md, docs/CONTRACTS.md, docs/EVALUATION.md, docs/tasks/02A.md and .brief/prompts/02A_muse_acquisition.md. Execute Phase 2A only from the contracts-v0.1 base in its own worktree. Treat planning/ and .brief/ as immutable, inspect the nested RAGTM source read-only, use the frozen interfaces and stop at the 2A exit gate. Report hardware checks not performed honestly."

For each of 02B/02C/02D/02E, substitute its task card and exact prompt from OWNERSHIP; authorize that track explicitly. Once authorized, those tracks may work in separate worktrees from contracts-v0.1. Integrator mounts module routers and owns shared schemas/locks/scripts/status. Local workers request changes in docs/requests/<track>/ and hand off exact evidence. No CPU-heavy Blender renders during participant capture. 3A requires real independently labelled sessions; 3B requires 2B–2E and a 2A baseline or labelled replay/keyboard; trained detector optional. 4 audits the integrated product.

## Event preparation and teardown

Organizer rules remain unverified. Record which code/data/models/music/renders predate the event; do not present existing assets as event-day work. The suggested five-hour allocations in the immutable README are planning assumptions, not measured completion promises. Keep one scene/score/groove, coherent original swing identity, prepared double-blink modulation and keyboard/replay fallbacks central. Cut scope if prior work is prohibited.

Before every final response, terminate and verify every task-owned job/container by exact identity. Reuse suitable Docker images and honor the image-count/lifecycle policy. Phase 1 used bounded installation/build/test commands and in-process service tests only; no persistent server, worker or container was started.

## Phase 2 wave baseline — current

The user-authorized 2A/B/C/D wave is implemented. Use `make test` for shared and module tests (pytest importlib mode), lint, TypeScript checks and the existing shell build. `PYTHONPATH=.:src` includes module namespaces. Mounted loopback module routes: `/muse` diagnostics, `/scene` saved bundle queries, `/music` catalogue, `/arranger` local plan preview. Importing the service starts no capture, renderer, provider, audio engine or worker. Generic single-record `/capabilities/run` domain dispatch remains explicitly unregistered; use the module CLIs/functions documented in handoffs. No dependency/contract freeze amendment was required.

Current evidence is `reports/phase2/GATE.md`; module-specific commands/limits are in the four handoffs. Scene assets: `artifacts/blender/validated-hero/10_projectile_tower-default` and `artifacts/blender/final-near-miss/10_projectile_tower-near_miss`. Music review set: `artifacts/music/review-v2`. Arranger review set: `artifacts/arranger/evaluated-hero-audition`, where music-only WAVs exclude the separate exact-time Foley event stream. Plans are drafts and no human approval exists. Do not conflate procedural audio measurement with listening approval.

Blender was run from a read-only mount of the supplied `/Users/agent/Downloads/blender-5.2.1-macos-arm64.dmg`, then detached. For another authorized render, remount/read the verified binary explicitly and detach after the bounded job. Do not persist the temporary mount path as an installed application. The optional Muse and API facts above remain unverified/unconfigured.

Exact next launch instruction (only when the user authorizes it):

> Read AGENTS.md, docs/VISION.md, docs/CONTRACTS.md, docs/EVALUATION.md, docs/tasks/02E.md, handoffs/02A.md through handoffs/02D.md, reports/phase2/GATE.md, and .brief/prompts/02E_performance_ui.md. Execute Phase 2E only against the completed Phase 2 wave. Treat planning/ and .brief/ as immutable. Own apps/web/ and packages/audio/ in a separate worktree from the completed wave commit; request shared contract, dependency, routing or registry changes through the integrator. Build keyboard-first and clearly labelled replay authoring/performance controls with optional Muse, preserve exact plan approval and local deterministic audio execution, and stop at the Phase 2E exit gate. Do not train a model or begin Phase 3B integration or Phase 4 release rehearsal.
