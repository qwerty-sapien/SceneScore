"""Bounded real MCP client for the project-scoped pinned Blender server."""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]


async def main(args):
    args.out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, BLENDER_HOST='127.0.0.1', BLENDER_PORT='9876',
               BLENDER_MCP_SAFE_MODE='1', DISABLE_TELEMETRY='true')
    params = StdioServerParameters(command=str(ROOT/'artifacts/tools/blender-mcp-env/bin/blender-mcp'), env=env)
    results = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            available = await session.list_tools()
            (args.out/'available-tools.json').write_text(json.dumps([t.model_dump() for t in available.tools], indent=2))
            calls = [('get_addon_status', {}), ('get_scene_info', {'user_prompt': args.prompt})]
            if args.smoke:
                calls += [
                    ('execute_blender_code', {'code': 'import bpy\nbpy.ops.mesh.primitive_cube_add(size=0.1, location=(0,0,3))\nbpy.context.object.name="SCENESCORE_MCP_SCRATCH"', 'user_prompt': args.prompt}),
                    ('get_object_info', {'object_name': 'SCENESCORE_MCP_SCRATCH', 'user_prompt': args.prompt}),
                    ('execute_blender_code', {'code': 'import bpy\nbpy.data.objects.remove(bpy.data.objects["SCENESCORE_MCP_SCRATCH"], do_unlink=True)', 'user_prompt': args.prompt}),
                    ('get_scene_info', {'user_prompt': args.prompt}),
                ]
            if args.code:
                calls.append(('execute_blender_code', {'code': args.code.read_text(), 'user_prompt': args.prompt}))
            calls.append(('get_viewport_screenshot', {'max_size': 1280, 'user_prompt': args.prompt}))
            for index, (name, arguments) in enumerate(calls):
                response = await asyncio.wait_for(session.call_tool(name, arguments), 30)
                payload = response.model_dump(mode='json')
                for block in payload.get('content', []):
                    if block.get('type') == 'image':
                        target = args.out/f'{index:02d}-{name}.png'
                        target.write_bytes(base64.b64decode(block.pop('data')))
                        block['local_image'] = str(target)
                results.append({'tool': name, 'arguments': arguments, 'response': payload})
                (args.out/'calls.json').write_text(json.dumps(results, indent=2))
                print(json.dumps({'tool': name, 'isError': response.isError}), flush=True)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--code', type=Path)
    parser.add_argument('--prompt', default='Use Blender CLI/Python for reproducible production and the requested blender-mcp for bounded interactive inspection.')
    raise SystemExit(asyncio.run(main(parser.parse_args())))
