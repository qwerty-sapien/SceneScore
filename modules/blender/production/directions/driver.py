"""Blender-only rendering of explicit mechanics packets; never authors body motion."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from modules.blender.production.common import digest, dump, read, rows  # noqa: E402
from modules.blender.production.driver import linear_keys, state  # noqa: E402


PALETTE = {
    'wood': (.32, .16, .075, 1), 'glass': (.12, .42, .36, 1),
    'brass': (.64, .40, .10, 1), 'cork': (.40, .25, .12, 1),
    'green_felt': (.055, .19, .145, 1), 'ceramic': (.92, .33, .09, 1),
    'steel': (.28, .34, .40, 1), 'stone': (.65, .68, .67, 1),
    'track': (.67, .72, .73, 1), 'blue': (.04, .25, .66, 1),
    'coral': (.83, .20, .10, 1), 'gold': (.73, .46, .09, 1),
    'white': (.84, .86, .84, 1), 'dark': (.055, .08, .11, 1),
    'floor': (.14, .18, .21, 1), 'glow': (.15, .65, .80, 1),
    'ivory': (.80, .81, .76, 1), 'charcoal': (.075, .10, .13, 1),
    'teal': (.04, .40, .38, 1), 'copper': (.55, .24, .10, 1),
}


def material(name, *, stripe=False):
    import bpy
    if isinstance(name, (list, tuple)):
        rgba = tuple(name) if len(name) == 4 else (*name, 1)
        label = 'color_' + '_'.join(str(x) for x in rgba)
    else:
        label = str(name or 'stone')
        rgba = PALETTE.get(label, PALETTE['stone'])
    label += '_striped' if stripe else ''
    mat = bpy.data.materials.get(label)
    if mat:
        return mat
    mat = bpy.data.materials.new(label)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Roughness'].default_value = .30 if name in ('glass', 'ceramic') else .48
    bsdf.inputs['Metallic'].default_value = .58 if name in ('brass', 'steel', 'gold') else 0
    # Opaque tinted fins make contact edges legible without refraction hiding them.
    if name == 'glow':
        bsdf.inputs['Emission Color'].default_value = rgba
        bsdf.inputs['Emission Strength'].default_value = .8
    if stripe:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        coord = nodes.new('ShaderNodeTexCoord')
        separate = nodes.new('ShaderNodeSeparateXYZ')
        links.new(coord.outputs['Generated'], separate.inputs[0])
        subtract = nodes.new('ShaderNodeMath')
        subtract.operation = 'SUBTRACT'
        subtract.inputs[1].default_value = .5
        links.new(separate.outputs['X'], subtract.inputs[0])
        absolute = nodes.new('ShaderNodeMath')
        absolute.operation = 'ABSOLUTE'
        links.new(subtract.outputs[0], absolute.inputs[0])
        band = nodes.new('ShaderNodeMath')
        band.operation = 'LESS_THAN'
        band.inputs[1].default_value = .075
        links.new(absolute.outputs[0], band.inputs[0])
        mix = nodes.new('ShaderNodeMixRGB')
        mix.inputs[1].default_value = rgba
        mix.inputs[2].default_value = (.025, .035, .045, 1)
        links.new(band.outputs[0], mix.inputs[0])
        links.new(mix.outputs[0], bsdf.inputs['Base Color'])
    return mat


def make_object(spec, *, moving=False):
    import bpy
    shape = spec['shape']
    half = spec.get('half_extents_m')
    if half is None and 'dimensions_m' in spec:
        half = [x / 2 for x in spec['dimensions_m']]
    if shape == 'box' and 'coil' in spec.get('visual', ''):
        shape = 'coil'
    if shape == 'box':
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object
        for vertex in obj.data.vertices:
            for i in range(3):
                vertex.co[i] *= half[i]
    elif shape == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=24, radius=spec['radius_m'])
        obj = bpy.context.object
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    elif shape == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=spec['radius_m'],
            depth=spec.get('length_m', spec.get('depth_m', .15)))
        obj = bpy.context.object
    elif shape == 'hoop':
        outer = spec['radius_m']
        tube = spec.get('tube_radius_m', outer * .06)
        bpy.ops.mesh.primitive_torus_add(major_segments=96, minor_segments=12,
                                       major_radius=outer - tube, minor_radius=tube)
        obj = bpy.context.object
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    elif shape == 'mesh':
        mesh = bpy.data.meshes.new(spec['id'])
        mesh.from_pydata(spec['vertices'], [], spec['faces'])
        mesh.update()
        if spec['id'] == 'central-observatory-orb':
            for polygon in mesh.polygons:
                polygon.use_smooth = True
        obj = bpy.data.objects.new(spec['id'], mesh)
        bpy.context.collection.objects.link(obj)
    elif shape in ('curve', 'coil'):
        curve = bpy.data.curves.new(spec['id'], 'CURVE')
        curve.dimensions = '3D'
        if shape == 'coil':
            length = 2 * half[0]
            thickness = min(.009, min(half) / 4)
            points = [[-length / 2 + thickness + (length - 2 * thickness) * i / 320,
                       (half[1] - thickness) * math.cos(i / 320 * 20 * math.pi),
                       (half[2] - thickness) * math.sin(i / 320 * 20 * math.pi)] for i in range(321)]
        else:
            points = spec['points']
            thickness = spec.get('radius_m', .015)
        curve.bevel_depth = thickness
        curve.bevel_resolution = 2
        spline = curve.splines.new('POLY')
        spline.points.add(len(points) - 1)
        for point, xyz in zip(spline.points, points):
            point.co = (*xyz, 1)
        obj = bpy.data.objects.new(spec['id'], curve)
        bpy.context.collection.objects.link(obj)
    else:
        raise ValueError('Unsupported declared shape: ' + shape)
    obj.name = spec['id']
    obj.location = spec.get('position_m', [0, 0, 0])
    obj.rotation_mode = 'QUATERNION'
    q = spec.get('quaternion_xyzw', [0, 0, 0, 1])
    obj.rotation_quaternion = [q[3], *q[:3]]
    # Separate the upper receiver spring from the adjacent gold guide rails.
    material_name = 'coral' if spec['id'] == 'hoop-coil' else spec.get('material', 'stone')
    obj.data.materials.append(material(material_name,
        stripe=moving and shape in ('sphere', 'cylinder', 'hoop') and not spec.get('zero_spin', False)))
    if spec.get('checkpoint_time_s') is not None:
        signal = obj.data.materials[0].copy()
        signal.name = spec['id'] + '-signal'
        obj.data.materials[0] = signal
        bsdf = signal.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (.035, .045, .04, 1)
        bsdf.inputs['Emission Strength'].default_value = 0
    obj['role'] = spec.get('role', 'mechanical_actor' if moving else 'support')
    obj['mechanics_id'] = spec['id']
    return obj


def add_keys(obj, samples, oid, fps, hz):
    for sample in samples:
        pose = sample['objects'][oid]
        frame = 1 + sample['tick'] * fps / hz
        obj.location = pose['position_m']
        q = pose['quaternion_xyzw']
        obj.rotation_quaternion = [q[3], *q[:3]]
        obj.scale = pose.get('scale', [1, 1, 1])
        for channel in ('location', 'rotation_quaternion', 'scale'):
            obj.keyframe_insert(data_path=channel, frame=frame)
    linear_keys(obj)


def cable_specs(packet):
    return [dict(id=actor['id'] + '-tether', shape='cylinder',
                 radius_m=actor['cable']['radius_m'], length_m=1., material='steel',
                 deformable=True, role='visualization_of_inextensible_cable')
            for actor in packet['actors'] if 'cable' in actor]


def cable_poses(packet, sample):
    """Draw the free cable segment from physical endpoints; adds no dynamics."""
    from mathutils import Quaternion, Vector
    poses = dict(sample['objects'])
    for actor in packet['actors']:
        if 'cable' not in actor:
            continue
        cable = actor['cable']
        pose = poses[actor['id']]
        q = pose['quaternion_xyzw']
        rotation = Quaternion([q[3], *q[:3]])
        start = Vector(cable['fixed_endpoint_m'])
        end = Vector(pose['position_m']) + rotation @ Vector(cable['actor_attachment_local_m'])
        direction = end - start
        q = Vector([0, 0, 1]).rotation_difference(direction)
        poses[actor['id'] + '-tether'] = dict(position_m=list((start + end) / 2),
            quaternion_xyzw=[q.x, q.y, q.z, q.w], scale=[1, 1, direction.length])
    return dict(sample, objects=poses)


def support_specs(packet):
    """Static foundations below the declared support plane; never moving geometry."""
    table = next((s for s in packet['geometry'] if s['id'] == 'supporting-table'), None)
    if table is None:
        return []
    top = [[x, y, z - .001] for x, y, z in table['vertices']]
    bottom = [[x, y, z - .12] for x, y, z in table['vertices']]
    specs = [dict(id='table-foundation', shape='mesh', vertices=top + bottom,
                  faces=[[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2],
                         [2, 6, 7, 3], [3, 7, 4, 0]], material='wood', role='silent_support')]
    dx = [bottom[1][i] - bottom[0][i] for i in range(3)]
    dy = [bottom[3][i] - bottom[0][i] for i in range(3)]
    normal = [dx[1]*dy[2] - dx[2]*dy[1], dx[2]*dy[0] - dx[0]*dy[2], dx[0]*dy[1] - dx[1]*dy[0]]
    for index, (x, y, z) in enumerate(bottom):
        x *= .90
        y = -1 + (y + 1) * .86
        z = bottom[0][2] - (normal[0]*(x-bottom[0][0]) + normal[1]*(y-bottom[0][1])) / normal[2]
        specs.append(dict(id=f'table-leg-{index}', shape='box', half_extents_m=[.13, .13, z / 2],
                          position_m=[x, y, z / 2], material='wood', role='silent_support'))
    specs.append(dict(id='studio-floor', shape='box', half_extents_m=[8, 5, .05],
                      position_m=[0, -1, -.05], material='floor', role='silent_support'))
    return specs


def presentation_geometry(packet):
    specs = []
    for original in packet['geometry']:
        spec = dict(original)
        if spec['id'] == 'door-overhead-frame':
            # Narrow fixed metal beam exposes the counterweight. It lies inside
            # the independently checked original support envelope.
            spec['half_extents_m'] = [.015, .50, .025]
            spec['material'] = 'brass'
        if packet['id'] in ('06', '08') and ('-guide-left' in spec['id'] or '-guide-right' in spec['id']):
            specs.extend(open_side_rail(packet, spec))
        else:
            specs.append(spec)
    return specs


def open_side_rail(packet, wall):
    """Keep the actual contact strip; put its thickness outside the guide."""
    from mathutils import Vector
    other_id = wall['id'].replace('-guide-left', '-guide-right') if '-guide-left' in wall['id'] else wall['id'].replace('-guide-right', '-guide-left')
    other = next(g for g in packet['geometry'] if g['id'] == other_id)
    capture = packet['id'] == '08'
    fraction = .5 if capture else .24 / (.24 + .15)
    frames = []
    for i in range(0, len(wall['vertices']), 2):
        low, high = map(Vector, wall['vertices'][i:i+2])
        opposite_low, opposite_high = map(Vector, other['vertices'][i:i+2])
        center = low.lerp(high, fraction)
        opposite = opposite_low.lerp(opposite_high, fraction)
        n = (high-low).normalized()
        outward = (center-opposite).normalized()
        frames.append((low, high, center, n, outward))

    def mesh(id_, indices, full=False):
        vertices, faces = [], []
        for j, i in enumerate(indices):
            low, high, center, n, outward = frames[i]
            bottom = low if full else center - n*.018
            top = high if full else center + n*.018
            vertices.extend([list(bottom), list(top), list(bottom+outward*.024), list(top+outward*.024)])
            if j:
                a, b = (j-1)*4, j*4
                faces.extend([[a, b, b+1, a+1], [a+2, a+3, b+3, b+2],
                              [a, a+2, b+2, b], [a+1, b+1, b+3, a+3]])
        end = (len(indices)-1)*4
        faces.extend([[0, 1, 3, 2], [end, end+2, end+3, end+1]])
        return dict(id=id_, shape='mesh', vertices=vertices, faces=faces,
                    material='brass' if not full else 'steel', role='silent_support')
    result = [mesh(wall['id'], list(range(len(frames))))]
    step = 45 if capture else 25
    for i in range(0, len(frames)-1, step):
        result.append(mesh(wall['id']+f'-upright-{i}', [i, i+1], full=True))
    return result


def checkpoint_specs(packet):
    if packet['id'] != '06':
        return []
    result = []
    colors = dict(sphere='coral', cylinder='blue', hoop='gold')
    for event in packet['events']:
        if event['type'] not in ('equal-slope-exit', 'profile-checkpoint', 'lower-checkpoint', 'receiver-contact'):
            continue
        oid = event['actor_id'] + '-' + event['type'] + '-lamp'
        p = event['position_m']
        position = [p[0], p[1] - .43, p[2] + .08]
        result.extend([
            dict(id=oid + '-post', shape='cylinder', radius_m=.014, length_m=position[2],
                 position_m=[position[0], position[1], position[2]/2], material='charcoal', role='silent_support'),
            dict(id=oid, shape='sphere', radius_m=.045, position_m=position,
                 material=colors[event['actor_id']], role='electrical_checkpoint_indicator',
                 checkpoint_time_s=event['time_s']),
        ])
    return result


def animate_checkpoints(packet, out):
    import bpy
    evidence = []
    for spec in checkpoint_specs(packet):
        if 'checkpoint_time_s' not in spec:
            continue
        mat = bpy.data.objects[spec['id']].data.materials[0]
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        base = bsdf.inputs['Base Color']
        emission = bsdf.inputs['Emission Color']
        strength = bsdf.inputs['Emission Strength']
        base.default_value = (.035, .045, .04, 1)
        strength.default_value = 0
        base.keyframe_insert('default_value', frame=1)
        strength.keyframe_insert('default_value', frame=1)
        frame = 1 + spec['checkpoint_time_s'] * 30
        base.default_value = PALETTE[spec['material']]
        emission.default_value = PALETTE[spec['material']]
        strength.default_value = 2
        base.keyframe_insert('default_value', frame=frame)
        strength.keyframe_insert('default_value', frame=frame)
        action = mat.node_tree.animation_data.action
        for layer in action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(mat.node_tree.animation_data.action_slot)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'CONSTANT'
        evidence.append(dict(id=spec['id'], physical_event_time_s=spec['checkpoint_time_s'],
                             playback_frame=frame, position_m=spec['position_m']))
    dump(out / 'checkpoint_indicators.json', dict(indicators=evidence,
        scope='electrical indication of computed crossings; no force, motor or body pose added'))


def fit_course_camera(packet, objects):
    """Keep the complete apparatus in view; broad ground plates may run offscreen."""
    import bpy
    from mathutils import Vector
    if packet['id'] not in ('06', '08'):
        return
    scene = bpy.context.scene
    camera = scene.camera
    bpy.context.view_layer.update()
    inverse = camera.matrix_world.inverted()
    corners = [inverse @ (obj.matrix_world @ Vector(corner))
               for oid, obj in objects.items() if oid != 'grounded-base'
               for corner in obj.bound_box]
    left, right = min(p.x for p in corners), max(p.x for p in corners)
    bottom, top = min(p.y for p in corners), max(p.y for p in corners)
    aspect = scene.render.resolution_x / scene.render.resolution_y
    camera.data.ortho_scale = max(right-left, (top-bottom)*aspect) * 1.13
    shift = camera.matrix_world.to_quaternion() @ Vector([(left+right)/2, (bottom+top)/2, 0])
    camera.location += shift


def configure_scene(packet):
    import bpy
    from mathutils import Vector
    scene = bpy.context.scene
    # Eevee keeps draft rendering bounded on the local control host.
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 32
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.world.color = (.07, .07, .07)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.09, .13, .17, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .45
    scene.view_settings.view_transform = 'AgX'
    camera = packet.get('camera', {})
    if packet.get('direction_id') == '18':
        camera = dict(position=[0, -7, 26], look_at=[0, -1, 1.1], ortho_scale=13.5)
    elif packet['id'] == '06':
        camera = dict(position=[3, -10, 17], look_at=[.6, 0, 1.6], ortho_scale=10)
    position = camera.get('position', [12, -18, 16])
    target = Vector(camera.get('look_at', [0, 0, 1]))
    data = bpy.data.cameras.new('camera_beauty')
    obj = bpy.data.objects.new('camera_beauty', data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'
    data.ortho_scale = camera.get('ortho_scale', 15)
    data.clip_end = 150
    scene.camera = obj
    for name, location, energy, size in [
        ('key', [-5, -8, 16], 2400, 9), ('fill', [8, 3, 12], 1600, 7),
        ('rim', [-4, 8, 9], 1700, 6),
    ]:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy, light.shape, light.size = energy, 'DISK', size
        ob = bpy.data.objects.new(name, light)
        bpy.context.collection.objects.link(ob)
        ob.location = location
        ob.rotation_euler = (target - ob.location).to_track_quat('-Z', 'Y').to_euler()


def build(out):
    import bpy
    from modules.blender.geometry import area
    packet = read(out / 'packet.json')
    samples = [cable_poses(packet, sample) for sample in rows(out / 'mechanics_states.jsonl')]
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    specs = (presentation_geometry(packet) + packet['actors'] + cable_specs(packet)
             + support_specs(packet) + checkpoint_specs(packet))
    moving = {s['id'] for s in packet['actors'] + cable_specs(packet)}
    objects = {s['id']: make_object(s, moving=s['id'] in moving) for s in specs}
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.render.fps = packet['hz']
    scene.frame_start, scene.frame_end = 1, len(samples)
    for oid in moving:
        add_keys(objects[oid], samples, oid, packet['hz'], packet['hz'])
    configure_scene(packet)
    scene.frame_set(1)
    fit_course_camera(packet, objects)
    scene['motion_source'] = packet['backend']
    scene['scope'] = packet.get('scope', '; '.join(packet.get('validation', {}).get('assumptions', [])))
    scene['mechanics_states_sha256'] = digest(out / 'mechanics_states.jsonl')
    scene['approval'] = 'pending human review'
    deps = bpy.context.evaluated_depsgraph_get()
    geometry = {}
    for spec in specs:
        obj = objects[spec['id']].evaluated_get(deps)
        mesh = obj.to_mesh()
        mesh.calc_loop_triangles()
        vertices = [list(v.co) for v in mesh.vertices]
        world = [list(obj.matrix_world @ v.co) for v in mesh.vertices]
        triangles = [list(t.vertices) for t in mesh.loop_triangles]
        geometry[spec['id']] = dict(vertices_local=vertices, triangles=triangles,
            world_surface_area_m2=area(world, triangles), transform=state(objects[spec['id']], deps))
        obj.to_mesh_clear()
    dump(out / 'evaluated_geometry.json', geometry)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'simulation.blend'), check_existing=False)
    dump(out / 'build.json', dict(status='PASSED', motion_source=packet['backend'],
        blender_version=bpy.app.version_string, blender_build_hash=bpy.app.build_hash.decode(),
        simulation_sha256=digest(out / 'simulation.blend'), samples=len(samples),
        geometry_sha256=digest(out / 'evaluated_geometry.json'),
        static_presentation='table foundation below plane; narrower fixed metal overhead beam inside checked envelope',
        method='computed mechanics sampled at 240 Hz; no native rigid-body cache claimed'))


def check_scene(out, *, fps, target):
    import bpy
    packet = read(out / 'packet.json')
    scene = bpy.context.scene
    maximum = dict(position_m=0., rotation_rad=0., scale=0.)
    count = 0
    with (out / (target + '_states.jsonl')).open('w') as stream:
        for original in rows(out / 'mechanics_states.jsonl'):
            sample = cable_poses(packet, original)
            frame = 1 + sample['tick'] * fps / packet['hz']
            scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
            deps = bpy.context.evaluated_depsgraph_get()
            actual = {oid: state(bpy.data.objects[oid], deps) for oid in sample['objects']}
            for oid, wanted in sample['objects'].items():
                got = actual[oid]
                maximum['position_m'] = max(maximum['position_m'], math.dist(got['position_m'], wanted['position_m']))
                q1, q2 = got['quaternion_xyzw'], wanted['quaternion_xyzw']
                dot = abs(sum(a * b for a, b in zip(q1, q2)))
                dot /= math.sqrt(sum(a * a for a in q1) * sum(b * b for b in q2))
                maximum['rotation_rad'] = max(maximum['rotation_rad'], 2 * math.acos(min(1., dot)))
                maximum['scale'] = max(maximum['scale'], math.dist(got['scale'], wanted.get('scale', [1, 1, 1])))
            stream.write(json.dumps(dict(tick=sample['tick'], time_s=sample['time_s'], objects=actual), allow_nan=False) + '\n')
            count += 1
    passed = maximum['position_m'] < 1e-5 and maximum['rotation_rad'] < 1e-4 and maximum['scale'] < 1e-5
    report = dict(status='PASSED' if passed else 'FAILED', maximum=maximum, samples_checked=count,
        fresh_process=True, fps=fps, hz=packet['hz'], states_sha256=digest(out / 'mechanics_states.jsonl'),
        method='all computed ticks evaluated through reopened Blender dependency graph')
    dump(out / (target + '_validation.json'), report)
    if not passed:
        raise RuntimeError(str(report))


def replay(out):
    import bpy
    packet = read(out / 'packet.json')
    bpy.ops.wm.open_mainfile(filepath=str(out / 'simulation.blend'), load_ui=False, use_scripts=False)
    check_scene(out, fps=packet['hz'], target='simulation_reopen')
    scene = bpy.context.scene
    for spec in packet['actors'] + cable_specs(packet):
        obj = bpy.data.objects[spec['id']]
        action = obj.animation_data.action
        for layer in action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(obj.animation_data.action_slot)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            for point in (key.co, key.handle_left, key.handle_right):
                                point.x = 1 + (point.x - 1) * 30 / packet['hz']
                        curve.update()
    scene.render.fps, scene.render.fps_base = 30, 1
    scene.frame_start, scene.frame_end = 1, round(packet['duration_s'] * 30)
    animate_checkpoints(packet, out)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'scene.blend'), check_existing=False)
    dump(out / 'replay.json', dict(status='PASSED', scene_sha256=digest(out / 'scene.blend'),
        simulation_sha256=digest(out / 'simulation.blend'),
        mechanics_states_sha256=digest(out / 'mechanics_states.jsonl'),
        physical_time_scale=1, fps=30, hz=packet['hz']))


def main():
    import bpy
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['build', 'replay', 'verify', 'render', 'stills'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--width', type=int, default=960)
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--last', type=int, default=900)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.stage == 'build':
        build(args.out)
    elif args.stage == 'replay':
        replay(args.out)
    else:
        bpy.ops.wm.open_mainfile(filepath=str(args.out / 'scene.blend'), load_ui=False, use_scripts=False)
        if args.stage == 'verify':
            check_scene(args.out, fps=30, target='replay')
        else:
            scene = bpy.context.scene
            scene.render.resolution_x, scene.render.resolution_y = args.width, args.width * 9 // 16
            directory = args.out / ('stills' if args.stage == 'stills' else 'renders')
            directory.mkdir(exist_ok=True)
            if args.stage == 'stills':
                for frame in [1, 121, 241, 361, 481, 601, 721, 841, 900]:
                    scene.frame_set(frame)
                    scene.render.filepath = str(directory / f'frame_{frame:06d}.png')
                    bpy.ops.render.render(write_still=True)
            else:
                scene.frame_start, scene.frame_end = args.first, args.last
                scene.render.filepath = str(directory / 'frame_######')
                bpy.ops.render.render(animation=True)
    print('DIRECTION_STAGE_COMPLETE', args.stage, flush=True)


if __name__ == '__main__':
    main()
