# A0 baseline — 2026-09-13

PASS for baseline establishment; no production edits in A0.

Git: `main`, HEAD `a397f3f4975e82374bacbf70302eda6c92621f28`, tracking
`origin/main`. Eleven tracked files already modified, no staged changes.
Existing Muse diagnostics, animation directions, decision records and supplied ZIP
are preserved by SHA-256 in [a0-git.json](a0-git.json); the initial tracked diff is
[a0-user.patch](a0-user.patch). This is a shared dirty checkout.

Runtime versions: Python 3.13.7, pytest 9.1.1, Ruff 0.16.7, Node 24.14.0,
npm 11.9.0, uv 0.11.28, Blender 5.2.1 LTS (9e2066aef7ef), FFmpeg/FFprobe 8.1.2.
The existing isolated MCP environment contains blender-mcp 1.9.1 / mcp 1.30.0;
the application venv intentionally lacks MCP. Exact commands and outputs:
[a0-versions.json](a0-versions.json).

Repository map: `modules/blender/` owns geometry, ten legacy scripted recipes,
export/query/selection and tests; `production/` owns build, bake, replay,
verify-replay, validate, export and render, analytic sphere/fixed-OBB mechanics,
native calibration, contact certificates and media validation. `tools/blender_mcp/`
contains pinned dependencies, bootstrap and standalone client. `apps/`,
`packages/`, `services/`, `src/`, `contracts/` contain the existing application,
music/audio and frozen shared contracts. `.agents/skills/blender-scene-export/`
is the existing exporter skill; `.brief/` and supplied archives are immutable inputs.

Generation path: legacy `python -m modules.blender.batch` invokes trusted recipe
scripts and `exporter.py`; production `python -m modules.blender.production`
invokes `driver.py` and `scenes.py` in Blender, then records evaluated states,
replay, scoped physical proofs, sidecars and media. No scene-intent adapter exists.
One-sphere/fixed-OBB mechanics and prescribed mechanisms have distinct scopes;
historical native Bullet calibration remains FAILED, independent of unit tests.

Configuration findings: `.codex/config.toml` embeds this checkout's absolute MCP
command. The client derives the root but assumes a fixed environment executable
and returns zero despite response errors. Production CLI and mutation helper use
a macOS-only Blender default; production rendering hard-codes Homebrew FFmpeg.
Safe mode, loopback 127.0.0.1:9876, telemetry opt-outs and tool allowlist are present.
Bootstrap disables asset integrations and never saves preferences. These must remain.

Current artifacts: [a0-artifacts.json](a0-artifacts.json) inventories 369 relevant
blend/video/manifest/proof files by path and size. Historical hero bundles,
revamp controls/catalogue, the explicit staircase selection and final draft muxes
exist here, unlike the skill pack's older archive-only audit. The active/staged
selection and historical approval/null status were not changed or recertified.
Untracked `production/directions/` sources are pre-existing user work.

Commands and results:

- `.venv/bin/python -m pytest -q modules/blender/tests tests/test_blender_scene_mutations.py tests/test_production_mutations.py tests/test_production_media.py`:
  **358 passed**, 29.58 s. Covers geometry, recipes, analytic mechanics, calibration,
  validation, replay/export/selection, media and mutation harnesses.
  [a0-tests.log](a0-tests.log), [job receipt](a0-tests.json).
- Blender `--background --factory-startup --disable-autoexec --python-exit-code 1 --threads 2 --python modules/blender/tests/blender_geometry_check.py`:
  sandbox launches via PATH and app binary both exited -11 before the assertion.
  The same app-binary command with approved host access **passed**:
  evaluated area 36.00000069938221 m² versus 36 m² expected.
  [host result](a0-blender-host-geometry.log), sandbox results
  [PATH](a0-blender-geometry.log), [app](a0-blender-app-geometry.log).
- Available MCP `get_scene_info`, read-only: **unavailable live addon**; response
  says “Could not connect to Blender” but `isError:false`.
  [exact response](a0-live-mcp.json). No dedicated existing MCP tests found.

No new software failures. Sandbox startup crashes and MCP connection failure are
recorded baseline/environment limitations. The documented vendor addon-status
missing-module defect is historical, not freshly reproduced with an active addon.
No simulation candidate, render, backend calibration repair or human review ran.
All owned baseline process groups exited and their absence was verified in receipts.
