# A2 portability and truthful MCP errors

PASS for implementation/regression gates. Live Blender inspection remains
unavailable: the real host-side MCP handshake/list-tools succeeded, but the addon
connection was refused. The repaired client correctly exited 1 for the returned
text failure with `isError:false`; no GUI was started or unrelated listener stopped.
See [host inspection log](a2-host-client.log) and
[raw call/verdict](a2-mcp-host-inspection/calls.json).

Changes:

- `.codex/config.toml` now resolves the Git checkout root and invokes
  `tools/blender_mcp/launch.sh`. The launcher derives its own location and invokes
  the existing isolated Python's pinned server entrypoint, avoiding stale venv
  console-script shebangs. Relocation to a path with spaces, including invocation
  from a subdirectory, is tested. No global configuration or dependencies changed.
- `modules/blender/executables.py` resolves explicit executable overrides,
  `BLENDER_BIN`/`FFMPEG_BIN`/`FFPROBE_BIN`, PATH and the existing macOS Blender app
  fallback. Invalid explicit paths fail, executable bits are checked and symlinks
  are resolved. No runtime is installed and POSIX runner support is not expanded.
- Legacy batch, production CLI, production encoding, media verification, legacy
  optional encoding and mutation CLI use that discovery. The historical baseline
  test path is now repository-relative. The helper is included in production
  source hashes; new builds receive new provenance without rewriting old assets.
- `response_guard.py` extends the supplied helper with nested failure envelopes,
  traceback and exception detection, including `ModuleNotFoundError` embedded in
  success-prefixed output. `client.py` persists verdicts and returns nonzero on
  recognized response/transport failures, stopping subsequent calls. Scratch
  cleanup uses a unique object identity and remains in a finally block.
- Nonempty responses are the default. Empty scene object arrays and successful
  execution acknowledgements with empty stdout are valid. Blank content fails;
  an explicit guard-only option permits empty no-output execution, never empty
  inspection. Screenshots require image content. The client uses nonempty policy.

Safe mode, loopback 127.0.0.1:9876, telemetry opt-outs, tool allowlist, pinned
requirements and addon bootstrap remain intact. The launcher overrides unsafe
inherited environment values. Vendor addon-status missing-module behavior was
not patched or relabelled as success. No recipe, physics solver or production
validation threshold was redesigned.

Verification:

- [a2-tests.log](a2-tests.log): **424 passed, 4 subtests passed**, including all A0/A1 tests.
- [a2-launcher-tests.log](a2-launcher-tests.log): **48 passed** after replacing the
  initial module invocation with the pinned package's direct entrypoint to avoid
  an observed runpy double-import warning.
- [a2-owned-lint.log](a2-owned-lint.log): scoped Ruff passed.
- [a2-live-client.log](a2-live-client.log): sandbox MCP connection denied; client
  correctly returned 1. The host-access retry above confirmed connection refused,
  distinguishing an absent listener from the sandbox restriction.

New intermediate failures were resolved: stricter discovery initially caused six
existing media fixtures with nonexistent fake executable names to fail before
reaching their mocked process runner. The fixtures now supply the current Python
executable solely to satisfy discovery; FFmpeg output remains mocked, and all
original integrity/failure assertions still execute. See [a2-first-tests.log](a2-first-tests.log).

The broader lint attempt found five errors in a directions driver added by the
concurrent user work, outside this task. It was left untouched; the passing lint
scope explicitly excludes that directory. This is not hidden as a task pass for
that other code. No task-owned adapter/process group remains running.
