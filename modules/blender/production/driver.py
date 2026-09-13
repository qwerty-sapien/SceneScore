"""Trusted Blender-only production stages. Each invocation is a fresh process."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from modules.blender.production.common import data_hash, digest, dump, read, rows, source_hashes  # noqa: E402


def state(obj, deps):
    matrix = obj.evaluated_get(deps).matrix_world
    q = matrix.to_quaternion()
    return {'position_m': list(matrix.translation), 'quaternion_xyzw': [q.x, q.y, q.z, q.w],
            'scale': list(matrix.to_scale())}


def linear_keys(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    for layer in action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(obj.animation_data.action_slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'


def build(args):
    import bpy
    from modules.blender.geometry import area
    from modules.blender.production.scenes import create_scene
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
              if k not in ('stage', 'out', 'first', 'last', 'profile', 'camera')}
    config['parameters'] = read(args.parameters) if args.parameters else {}
    production = create_scene(config)
    tracks = production.pop('_analytic_tracks',{})
    if tracks:
        dump(args.out/'mechanics_states.json',tracks)
        production['mechanics']['states_sha256']=digest(args.out/'mechanics_states.json')
    deps = bpy.context.evaluated_depsgraph_get()
    geometry = {}
    for spec in production['objects']:
        obj = bpy.data.objects[spec['object_id']]
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        vertices = [list(v.co) for v in mesh.vertices]
        world_vertices = [list(evaluated.matrix_world@v.co) for v in mesh.vertices]
        triangles = [list(t.vertices) for t in mesh.loop_triangles]
        geometry[spec['object_id']] = {'vertices_local': vertices, 'triangles': triangles,
             'surface_area_m2': area(world_vertices, triangles),
             'material_rgba': list(obj.data.materials[0].diffuse_color),
             'method': 'evaluated dependency graph mesh with render bevel; world transformed triangles'}
        evaluated.to_mesh_clear()
    camera = bpy.data.objects['camera_beauty']
    production['camera'] = {'id': camera.name, 'transform': {
         'position_m': list(camera.matrix_world.translation),
         'quaternion_xyzw': list(camera.matrix_world.to_quaternion())[1:]+list(camera.matrix_world.to_quaternion())[:1],
         'matrix_row_major': [v for row in camera.matrix_world for v in row]}}
    production.update(version='blender-production-1', config=config, code_hashes=source_hashes(),
                      blender_version=bpy.app.version_string, blender_build_hash=bpy.app.build_hash.decode())
    for name,expected in production['code_hashes'].items():
        target=args.out/'generation_source'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
        if digest(target)!=expected:
            raise RuntimeError('Generation source changed during capture: '+name)
    production['source_fingerprint'] = data_hash({'config': config, 'code': production['code_hashes']})
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'simulation.blend'), check_existing=False)
    dump(args.out/'production.json', production)
    dump(args.out/'evaluated_geometry.json', geometry)
    dump(args.out/'config.json', config)
    print('BUILD_COMPLETE', flush=True)


def bake(args):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(args.out/'simulation.blend'), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    production = read(args.out/'production.json')
    if production['code_hashes']!=source_hashes():
        raise RuntimeError('Generation source changed after build; use a new candidate')
    count = round(production['duration_s']*production['physics_hz'])
    scene.frame_start, scene.frame_end = 1, count+1
    cache = scene.rigidbody_world.point_cache
    cache.frame_start, cache.frame_end = 1, count+1
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'simulation.blend'), check_existing=False)
    bpy.ops.ptcache.bake_all(bake=True)
    if not cache.is_baked:
        raise RuntimeError('Rigid-body cache did not bake')
    objects = {s['object_id']: bpy.data.objects[s['object_id']] for s in production['objects']}
    with (args.out/'physics_states.jsonl').open('w') as output:
        for tick in range(count+1):
            scene.frame_set(tick+1)
            deps = bpy.context.evaluated_depsgraph_get()
            output.write(json.dumps({'tick': tick, 'time_s': tick/production['physics_hz'],
                                    'objects': {oid: state(o, deps) for oid, o in objects.items()}},
                                   separators=(',', ':'), allow_nan=False)+'\n')
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'simulation.blend'), check_existing=False)
    caches = {str(p.relative_to(args.out)): digest(p) for p in sorted(args.out.rglob('*.bphys'))}
    dump(args.out/'bake.json', {'version': 'blender-bake-1', 'source_fingerprint': production['source_fingerprint'],
                              'baker_code_hashes': source_hashes(),
                              'is_baked': cache.is_baked, 'physics_hz': production['physics_hz'],
                              'sample_count': count+1, 'cache_hashes': caches,
                              'cache_storage': 'external bphys' if caches else 'embedded point cache in saved simulation.blend',
                              'simulation_hash': digest(args.out/'simulation.blend'),
                              'states_hash': digest(args.out/'physics_states.jsonl')})
    print('BAKE_COMPLETE', flush=True)


def replay(args):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(args.out/'simulation.blend'), load_ui=False, use_scripts=False)
    production = read(args.out/'production.json')
    scene = bpy.context.scene
    if not scene.rigidbody_world.point_cache.is_baked:
        raise RuntimeError('Fresh saved simulation has no baked cache')
    bake_position_error = 0.
    for sample in rows(args.out/'physics_states.jsonl'):
        scene.frame_set(sample['tick']+1)
        deps = bpy.context.evaluated_depsgraph_get()
        for oid, wanted in sample['objects'].items():
            got = state(bpy.data.objects[oid], deps)
            bake_position_error = max(bake_position_error, math.dist(got['position_m'], wanted['position_m']))
    if bake_position_error > 1e-5:
        raise RuntimeError('Fresh baked simulation differs from original extraction')
    dump(args.out/'bake-reopen.json', {'status': 'PASSED', 'fresh_process': True,
         'cache_is_baked': True, 'max_position_error_m': bake_position_error,
         'simulation_hash': digest(args.out/'simulation.blend')})
    scene.frame_set(1)
    scene.rigidbody_world.enabled = False
    moving = {}
    for spec in production['objects']:
        obj = bpy.data.objects[spec['object_id']]
        obj.animation_data_clear()
        obj.rotation_mode = 'QUATERNION'
        if spec['mode'] != 'passive':
            moving[spec['object_id']] = obj
    for sample in rows(args.out/'physics_states.jsonl'):
        frame = 1+sample['tick']*30/production['physics_hz']
        for oid, obj in moving.items():
            pose = sample['objects'][oid]
            obj.location = pose['position_m']
            q = pose['quaternion_xyzw']
            obj.rotation_quaternion = (q[3], *q[:3])
            obj.scale = pose['scale']
            obj.keyframe_insert(data_path='location', frame=frame)
            obj.keyframe_insert(data_path='rotation_quaternion', frame=frame)
    for obj in moving.values():
        linear_keys(obj)
    scene.render.fps, scene.render.fps_base = 30, 1
    scene.frame_start, scene.frame_end = 1, round(production['duration_s']*30)
    scene.frame_set(1)
    scene['motion_source'] = 'derived evaluated '+production['motion_mode']
    scene['physics_states_sha256'] = digest(args.out/'physics_states.jsonl')
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'scene.blend'), check_existing=False)
    bake_info = read(args.out/'bake.json')
    production['lineage'] = {'source_fingerprint': production['source_fingerprint'],
                             'bake_source_fingerprint': bake_info['source_fingerprint'],
                             'states_sha256': digest(args.out/'physics_states.jsonl'),
                             'artifacts': {name: digest(args.out/name) for name in ('simulation.blend', 'scene.blend', 'bake.json')}}
    production['lineage']['artifacts'].update(bake_info['cache_hashes'])
    for name,expected in production['code_hashes'].items():
        captured=args.out/'generation_source'/name
        if captured.is_file():
            production['lineage']['artifacts']['generation_source/'+name]=expected
    if (args.out/'mechanics_states.json').is_file():
        production['lineage']['artifacts']['mechanics_states.json']=digest(args.out/'mechanics_states.json')
    dump(args.out/'production.json', production)
    print('REPLAY_SAVED', flush=True)


def verify(args):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(args.out/'scene.blend'), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    production = read(args.out/'production.json')
    maxima = {'position_error_m': 0., 'quaternion_error': 0., 'scale_error': 0.}
    count = 0
    with (args.out/'replay_states.jsonl').open('w') as output:
        for sample in rows(args.out/'physics_states.jsonl'):
            frame = 1+sample['tick']*30/production['physics_hz']
            scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame))
            deps = bpy.context.evaluated_depsgraph_get()
            actual = {oid: state(bpy.data.objects[oid], deps) for oid in sample['objects']}
            for oid, wanted in sample['objects'].items():
                got = actual[oid]
                maxima['position_error_m'] = max(maxima['position_error_m'], math.dist(wanted['position_m'], got['position_m']))
                q1,q2 = wanted['quaternion_xyzw'], got['quaternion_xyzw']
                dot = abs(sum(x*y for x,y in zip(q1,q2)))/math.sqrt(sum(x*x for x in q1)*sum(x*x for x in q2))
                maxima['quaternion_error'] = max(maxima['quaternion_error'], 2*math.acos(min(1,dot)))
                maxima['scale_error'] = max(maxima['scale_error'], math.dist(wanted['scale'], got['scale']))
                count += 1
            output.write(json.dumps({**sample, 'objects': actual}, separators=(',', ':'))+'\n')
    passed = maxima['position_error_m'] <= 1e-5 and maxima['quaternion_error'] <= 1e-4 and maxima['scale_error'] <= 1e-5
    dump(args.out/'replay_validation.json', {'status': 'PASSED' if passed else 'FAILED', 'fresh_process': True,
         'mode': 'fresh_blender_process', 'source_states_sha256': digest(args.out/'physics_states.jsonl'),
         'samples_checked': round(production['duration_s']*production['physics_hz'])+1,
         'max_position_error_m': maxima['position_error_m'], 'max_rotation_error_rad': maxima['quaternion_error'],
         'max_scale_error': maxima['scale_error'],
         'method': 'fresh Blender process, every 240Hz sample of finalized 30fps replay evaluated from dependency graph',
         'count': count, 'metrics': maxima, 'source_hash': digest(args.out/'scene.blend'),
         'states_sha256': digest(args.out/'physics_states.jsonl'), 'replay_states_sha256': digest(args.out/'replay_states.jsonl')})
    if not passed:
        raise RuntimeError('Fresh replay differs from evaluated physics: '+repr(maxima))
    print('REPLAY_VERIFIED '+str(maxima), flush=True)


def render(args):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(args.out/'scene.blend'), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    prod = read(args.out/'production.json')
    width, height = (1920, 1080) if args.profile == 'final' else (640, 360)
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.camera = bpy.data.objects['camera_'+args.camera]
    if args.profile == 'diagnostic':
        neutral=bpy.data.materials.get('diagnostic_neutral') or bpy.data.materials.new('diagnostic_neutral')
        neutral.use_nodes=True
        bsdf=neutral.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=(.45,.45,.45,1)
        bsdf.inputs['Roughness'].default_value=.7
        scene.view_layers[0].material_override = neutral
    if hasattr(scene,'eevee') and hasattr(scene.eevee,'taa_render_samples'):
        scene.eevee.taa_render_samples=64 if args.profile=='final' else 16
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    total = round(prod['duration_s']*30)
    scene.frame_start, scene.frame_end = args.first, min(args.last or total, total)
    target = args.out/'renders'/args.profile/args.camera
    target.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(target/'frame_######')
    bpy.ops.render.render(animation=True)
    expected = {f'frame_{frame:06d}.png' for frame in range(1, total+1)}
    if expected.issubset({p.name for p in target.glob('*.png')}):
        video = target/'video.mp4'
        cmd = ['/opt/homebrew/bin/ffmpeg', '-v', 'error', '-nostdin', '-y', '-framerate', '30',
               '-start_number', '1', '-i', str(target/'frame_%06d.png'), '-frames:v', str(total),
               '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)]
        encoded = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        dump(target/'render.json', {'profile': args.profile, 'camera': args.camera, 'command': cmd,
             'returncode': encoded.returncode, 'stderr': encoded.stderr, 'frame_count': total,
             'source_hash': digest(args.out/'scene.blend'), 'states_hash': digest(args.out/'physics_states.jsonl'),
             'width': width, 'height': height, 'fps': 30,
             'renderer_code_hashes':source_hashes(),
             'video_hash': digest(video) if encoded.returncode == 0 else None})
        encoded.check_returncode()
    print('RENDER_COMPLETE', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--recipe')
    parser.add_argument('--variant')
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--physics-hz', type=int)
    parser.add_argument('--solver-substeps', type=int)
    parser.add_argument('--solver-iterations', type=int)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--profile', default='preview')
    parser.add_argument('--camera', default='beauty')
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--last', type=int)
    parser.add_argument('--parameters', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    {'build': build, 'bake': bake, 'replay': replay, 'verify-replay': verify, 'render': render}[args.stage](args)


if __name__ == '__main__':
    main()
