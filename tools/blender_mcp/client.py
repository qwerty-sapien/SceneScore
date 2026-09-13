"""Bounded real MCP client for the project-scoped pinned Blender server."""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import uuid

try:
    from .response_guard import classify_response
except ImportError:  # Direct invocation from the isolated MCP environment.
    from response_guard import classify_response

ROOT = Path(__file__).resolve().parents[2]


async def run_calls(session, calls, out, results):
    """Persist every attempted call; stop on the first failure, returning nonzero."""
    for name, arguments in calls:
        try:
            response = await asyncio.wait_for(session.call_tool(name, arguments), 30)
            payload = response.model_dump(mode='json')
        except Exception as error:
            payload = {'isError': True, 'content': [{'type': 'text', 'text': f'{type(error).__name__}: {error}'}]}
        verdict = classify_response(name, payload)
        if verdict['status'] == 'PASSED':
            for block in payload.get('content', []):
                if block.get('type') == 'image':
                    try:
                        target = out/f'{len(results):02d}-{name}.png'
                        target.write_bytes(base64.b64decode(block['data'], validate=True))
                        del block['data']
                        block['local_image'] = str(target)
                    except (KeyError, ValueError, OSError) as error:
                        verdict = {'status': 'FAILED', 'reasons': [f'image persistence failed: {error}']}
        results.append({'tool': name, 'arguments': arguments, 'response': payload, 'verdict': verdict})
        (out/'calls.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps({'tool': name, 'isError': payload.get('isError'), 'verdict': verdict}), flush=True)
        if verdict['status'] != 'PASSED':
            return 1
    return 0


async def main(args):
    # Host-side response/client unit tests do not require the optional MCP SDK.
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    args.out.mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(command='sh', args=[str(ROOT/'tools/blender_mcp/launch.sh')], env=dict(os.environ))
    results = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), 30)
            available = await asyncio.wait_for(session.list_tools(), 30)
            (args.out/'available-tools.json').write_text(json.dumps([t.model_dump() for t in available.tools], indent=2))
            calls = [('get_scene_info', {'user_prompt': args.prompt})]
            if not args.inspect_only:
                calls.insert(0, ('get_addon_status', {}))
            if await run_calls(session, calls, args.out, results):
                return 1
            if args.smoke:
                # Unique scratch identity; cleanup still runs after an inspection error.
                scratch = 'SCENESCORE_MCP_SCRATCH_' + uuid.uuid4().hex
                try:
                    failed = await run_calls(session, [
                        ('execute_blender_code', {'code': f'import bpy\nbpy.ops.mesh.primitive_cube_add(size=0.1, location=(0,0,3))\nbpy.context.object.name={scratch!r}', 'user_prompt': args.prompt}),
                        ('get_object_info', {'object_name': scratch, 'user_prompt': args.prompt}),
                    ], args.out, results)
                finally:
                    cleanup_failed = await run_calls(session, [
                        ('execute_blender_code', {'code': f'import bpy\nobj=bpy.data.objects.get({scratch!r})\nif obj is not None:\n    bpy.data.objects.remove(obj, do_unlink=True)', 'user_prompt': args.prompt}),
                    ], args.out, results)
                if failed or cleanup_failed:
                    return 1
            calls = []
            if args.code:
                calls.append(('execute_blender_code', {'code': args.code.read_text(), 'user_prompt': args.prompt}))
            if not args.inspect_only:
                calls.append(('get_viewport_screenshot', {'max_size': 1280, 'user_prompt': args.prompt}))
            return await run_calls(session, calls, args.out, results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--code', type=Path)
    parser.add_argument('--inspect-only', action='store_true', help='one read-only scene call; no status, mutation or screenshot')
    parser.add_argument('--prompt', default='Use Blender CLI/Python for reproducible production and the requested blender-mcp for bounded interactive inspection.')
    args = parser.parse_args()
    if args.inspect_only and (args.smoke or args.code):
        parser.error('--inspect-only cannot be combined with --smoke or --code')
    raise SystemExit(asyncio.run(main(args)))
