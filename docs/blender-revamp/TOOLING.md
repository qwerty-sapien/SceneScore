# Blender revamp tooling — node 01

This document records the scoped tooling implementation. It does not certify a
render, a bake, physical motion, aesthetic quality or an interactive MCP session.
The coordinator owns the production generation CLI, project MCP configuration,
installation, Blender GUI session and candidate directories.

## Bounded CLI runner

`modules/blender/batch.py` retains the trusted recipe entrypoints and two Blender
threads. Output destinations remain scoped; legacy entrypoints reject nonempty
candidate directories. The no-render default remains export-only. The batch
runner no longer inserts the exporter's `--preview` switch, which silently
reduced every batch to 320×180. It now forwards explicit dimensions:

- `--profile final` (default): 1920×1080.
- `--profile preview`: 640×360.
- `--resolution WIDTH HEIGHT`: explicit override, each dimension 32–1920.
- `--fps 30` (default): preserved identically for either profile. A lower cadence
  can be requested for a labelled compatibility fixture; it is not production QA.

These flags apply to the existing **legacy synthetic choreography** entrypoints.
They do not convert export sampling into dynamics. The coordinator's production
CLI separately owns build, bake, export, validation, diagnostic render and final
render operations and separates 240 Hz state extraction from Bullet solver
substeps and native 30 fps presentation.

Example legacy compatibility command, **not executed as a Blender render in this
worker**:

```sh
python -m modules.blender.batch --blender "$BLENDER_BIN" \
  --out artifacts/blender-compatibility/unique-preview \
  --recipe 10_projectile_tower --profile preview --fps 30 --render --timeout 1800
```

For final dimensions use `--profile final`; adding `--resolution 1280 720`
explicitly chooses a different delivery size. Never reuse a populated candidate
output directory. The coordinator's execution ledger supplies the cumulative
compute, storage and repair budgets; per-job timeout alone does not enforce them.

`bounded(command, log, timeout=600, *, cleanup_grace=2)` is also available to the
production CLI. It records command, PID, PGID, return code, elapsed seconds,
status, cleanup signals and confirmed group absence in the adjacent `.job.json`.
`start_new_session=True` gives each job its own process group. Cancellation during
launch is deferred until its identity is captured. SIGINT/SIGTERM handlers are
restored on every path, and repeated cancellation cannot abandon cleanup.
Signal-driven cancellation requires running this function on the main thread.

A log-open or launch failure launches no job or records a failed job. An initial
evidence-write failure still terminates and reaps the owned process. A final
write failure returns `status: failed` with `evidence_write_error`; the caller
must preserve this returned record elsewhere. It must not treat a missing file
as successful evidence. Log-close failures also fail the job after cleanup.

Cleanup gives the complete group a graceful SIGTERM window, then a SIGKILL
window. It checks for surviving descendants after the leader has exited and
reaps the leader before accepting group absence. A transient denied probe means
absence is not proven and is retried within that same deadline. An unverified
remaining group yields failure; it is never reported as cleaned. Trusted jobs
must not detach descendants into new sessions, which would escape process-group
ownership. The Blender/FFmpeg commands used here do not request detachment.

## Pinned Blender MCP preparation

Primary source inspected read-only:
[ahujasid/blender-mcp revision 5f8ddaf](https://github.com/ahujasid/blender-mcp/tree/5f8ddaf6e987c4aa0c3467fcc548838b28f64477).
The coordinator's local checkout at
`artifacts/tools/blender-mcp` resolves to that full revision. Install both addon
and server from this same reviewed checkout; do not use an unpinned latest
package or mix addon/server revisions. Keep server Python separate from Blender
Python. No global Codex settings belong to this task.

The inspected README and server support the following environment values for a
project-scoped MCP server configuration:

```toml
BLENDER_HOST = "127.0.0.1"
BLENDER_PORT = "9876"
BLENDER_MCP_SAFE_MODE = "1"
DISABLE_TELEMETRY = "true"
```

These are environment values, not a complete install command. The coordinator
must resolve and record the actual trusted server executable. Safe mode checks
code passed through the server and is defense in depth; do not bypass a rejected
operation through another execution path. The addon server constructor defaults
to `localhost`; verify the actual listening address remains loopback.

The addon's telemetry flag is **addon preferences** `telemetry_consent`, not a
scene flag. Set it false as well as `DISABLE_TELEMETRY=true`. The upstream
`disable_telemetry` tool turns off rich telemetry but its response explicitly
states that minimal usage counts otherwise remain; both controls are needed.
The scene flags below must all remain false:

```text
blendermcp_use_polyhaven
blendermcp_use_hyper3d
blendermcp_use_sketchfab
blendermcp_use_hunyuan3d
```

Coordinator-owned live proof must record the server/addon revisions and actual
responses from `get_addon_status`, `get_scene_info`, `get_object_info`,
`get_viewport_screenshot` and `execute_blender_code`, as available after server
registration. Use one owned scratch scene. Capture the baseline object inventory,
create one uniquely named disposable object through bounded safe-mode code,
inspect it, capture a real viewport image, delete it, and compare the restored
inventory. Preserve the screenshot and response hashes. Any accepted production
edit must be captured in source-controlled generation. Keep bake/render jobs in
the bounded CLI, outside the MCP socket.

**MCP status for this worker: PREPARATION COMPLETE; LIVE PROOF NOT RUN.** No addon
was installed, project configuration modified or Blender GUI started by this
worker. Any unavailable trust, install or restart step remains a named live-proof
blocker; it does not imply CLI production failed.

## Executed checks

Worktree: `/private/tmp/scenescore-revamp-tooling`. Interpreter:
`/Users/agent/Desktop/SceneScore/.venv/bin/python`.

```sh
/Users/agent/Desktop/SceneScore/.venv/bin/python -m pytest \
  modules/blender/tests/test_interfaces.py \
  modules/blender/tests/test_production_runner.py -q
/Users/agent/Desktop/SceneScore/.venv/bin/python -m ruff check \
  modules/blender/batch.py modules/blender/tests/test_production_runner.py
```

The first focused process runs exposed a transient EPERM during shutdown probes,
including under host-access approval. The runner was repaired to retry until
verified absence or deadline. Failed-run test identities were inspected separately
and confirmed absent. Final focused run: **18 passed in 1.54 s**; Ruff: **all checks passed**. Tests exercise
real short Python subprocesses plus injected log/evidence failures and command
construction. Profile tests intercept the launcher and therefore do **not** count
as actual Blender render verification. No final animation-quality claim is made.
