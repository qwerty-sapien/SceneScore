"""Load the pinned addon for this owned GUI session; never save user preferences."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'artifacts/tools/blender-mcp/addon.py'
REVISION = '5f8ddaf6e987c4aa0c3467fcc548838b28f64477'
spec = importlib.util.spec_from_file_location('scenescore_blender_mcp', SOURCE)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
# Set the stored property before registration so upstream's auto-start stays off.
bpy.context.scene['blendermcp_auto_start_server'] = False
addon.register()
bpy.context.scene.blendermcp_auto_start_server = False
entry = bpy.context.preferences.addons.new()
entry.module = spec.name
entry.preferences.telemetry_consent = False
for name in ('polyhaven', 'hyper3d', 'hunyuan3d', 'sketchfab', 'polypizza'):
    setattr(bpy.context.scene, 'blendermcp_use_' + name, False)
assert not addon._telemetry_consent_enabled()
existing = getattr(bpy.types, 'blendermcp_server', None)
if existing is not None:
    existing.stop()
bpy.types.blendermcp_server = addon.BlenderMCPServer(host='127.0.0.1', port=9876)
bpy.types.blendermcp_server.start()
assert bpy.types.blendermcp_server.running
bpy.context.scene.blendermcp_server_running = True
print('SCENESCORE_MCP_READY ' + json.dumps({
    'revision': REVISION, 'addon_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'host': '127.0.0.1', 'port': 9876, 'telemetry': False,
    'blender_version': bpy.app.version_string,
}), flush=True)
