# Project Blender MCP

The project config starts `sh tools/blender_mcp/launch.sh` from the Git checkout
root, including when Codex starts in a subdirectory. The launcher derives its
own root, uses the existing isolated environment's Python with
a direct import of `blender_mcp.server.main`, and avoids console scripts with stale absolute shebangs.
An optional `BLENDER_MCP_PYTHON` selects an explicitly prepared Python executable.
No runtime is downloaded or installed by the launcher. If the environment is
missing, prepare it separately from `requirements.lock`; keep the pinned source
revision and compatible addon. Do not copy a virtual environment between hosts.

Launch always sets loopback `127.0.0.1:9876`, `BLENDER_MCP_SAFE_MODE=1` and
`DISABLE_TELEMETRY=true`, even when inherited values disagree. The existing tool
allowlist, addon bootstrap, disabled external asset integrations and no-preference-
save policy remain in force. This launcher starts the MCP STDIO adapter, not a
Blender GUI/addon. It does not stop any existing GUI/listener.

From the repository root, using that environment:

```sh
artifacts/tools/blender-mcp-env/bin/python tools/blender_mcp/client.py \
  --inspect-only --out artifacts/blender/mcp-inspection \
  --prompt 'Inspect the current Blender scene.'
```

`--inspect-only` performs one read-only scene call. The ordinary client starts
with addon-status and scene inspection, and stops on the first failure. Scratch
smoke objects use unique identities and cleanup is attempted even after a failed
object inspection. Call receipts include the raw response and verdict; recognized
MCP/embedded execution errors and transport timeouts return nonzero. No missing
vendor module is hidden or repaired by changing upstream dependencies.

The guard rejects `isError`, failure envelopes, traceback/exception text and
known error prefixes, including nested results with a success prefix. Nonempty
content is required by default. `{"objects":[]}` and execution acknowledgements
with no stdout are valid; blank/missing content is not. A guard caller can
explicitly allow empty content only for no-output execution. The standalone
client always uses the default nonempty policy. Screenshot calls require an image.
This conservative classifier is not a universal verifier of arbitrary printed text.

Blender CLIs now discover `--blender`, then `BLENDER_BIN`, then PATH, then the
verified macOS app location when present. Paths must be executable; symlinks are
resolved for Blender resource discovery. The FFmpeg paths use `FFMPEG_BIN` /
`FFPROBE_BIN` then PATH (media verification also accepts explicit arguments).
An invalid explicit override fails without fallback. Legacy export retains its
existing frame-sequence-only behavior if no encoder is installed. These changes
do not add platform support to the POSIX process-group runner or certify versions.

Host-only regression tests: `python -m pytest modules/blender/tests/test_mcp.py
modules/blender/tests/test_executables.py tools/blender_mcp/test_response_guard.py`.
