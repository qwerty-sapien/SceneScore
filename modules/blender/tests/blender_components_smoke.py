"""Run only in a fresh bounded Blender process; no motion or rendered-media claim."""
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main():
    import bpy
    from mathutils import Vector
    from modules.blender.components import REGISTRY, Transform, component_spec, create_component
    from modules.blender.components.math3d import axis_angle
    out = Path(sys.argv[sys.argv.index('--')+1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    # Keep the factory scene objects: the reusable adapter must preserve preexisting content.
    prior = {o.name for o in bpy.data.objects}
    results = []
    for i, kind in enumerate(REGISTRY):
        transform = Transform((i % 3*7., i//3*7., 3.), axis_angle((0., 0., 1.), math.radians(i*17)))
        component = create_component(component_spec(kind.lower(), kind, transform=transform, bevel_m=.002))
        built = component.build_blender()
        assert len(built['collision_objects']) == len(built['visual_objects']) == len(component.collision_geometry)
        maximum_error = 0.
        for name, geometry in zip(built['collision_objects'], component.collision_geometry):
            obj = bpy.data.objects[name]
            assert obj.rigid_body.type == 'PASSIVE' and obj.rigid_body.collision_shape == 'BOX'
            assert obj.hide_render and len(obj.data.vertices) == 8 and not obj.modifiers
            actual = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
            expected = geometry.vertices
            error = max(min(math.dist(v, w) for w in actual) for v in expected)
            maximum_error = max(maximum_error, error)
            assert error < 1e-5, (kind, name, error)
        for name in built['visual_objects']:
            obj = bpy.data.objects[name]
            assert obj.rigid_body is None and not obj.hide_render and len(obj.modifiers) == 1
        assert prior <= {o.name for o in bpy.data.objects}
        try:
            component.build_blender()
        except ValueError:
            pass
        else:
            raise AssertionError('duplicate component silently overwritten')
        results.append({**built, 'maximum_world_corner_error_m': maximum_error, 'blueprint': component.to_dict()})
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'components.blend'))
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((ROOT/'modules/blender/components').glob('*.py'))}
    report = {'status': 'PASSED', 'scope': 'construction and numerical geometry smoke', 'blender_version': bpy.app.version_string,
              'component_count': len(results), 'components': results, 'preexisting_objects_preserved': sorted(prior),
              'physics_validated': False, 'simulation': 'NOT_RUN', 'rendering': 'NOT_RUN', 'approval': None,
              'source_sha256': source_hashes, 'blend_sha256': hashlib.sha256((out/'components.blend').read_bytes()).hexdigest()}
    (out/'smoke.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'status': 'PASSED', 'component_count': len(results), 'output': str(out)}))


if __name__ == '__main__':
    main()
