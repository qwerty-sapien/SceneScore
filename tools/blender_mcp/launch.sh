#!/bin/sh
# Repo-local, offline launch. Execute Python as a module to avoid stale venv shebangs.
set -eu
scenescore_root=$(CDPATH= cd -P "$(dirname "$0")/../.." && pwd)
scenescore_mcp_python=${BLENDER_MCP_PYTHON:-"$scenescore_root/artifacts/tools/blender-mcp-env/bin/python"}
if [ ! -x "$scenescore_mcp_python" ]; then
    echo "Blender MCP Python is missing or not executable. Prepare tools/blender_mcp/requirements.lock in the project environment or set BLENDER_MCP_PYTHON." >&2
    exit 1
fi
export BLENDER_HOST=127.0.0.1 BLENDER_PORT=9876 BLENDER_MCP_SAFE_MODE=1 DISABLE_TELEMETRY=true
exec "$scenescore_mcp_python" -m blender_mcp.server "$@"
