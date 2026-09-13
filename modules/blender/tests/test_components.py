"""Host-side geometry contracts, synthetic connections and authoring integration."""
import copy
import json
import math
from pathlib import Path

import pytest

from modules.blender.components import REGISTRY, Transform, component_spec, create_component
from modules.blender.components.connections import (ConnectionPolicy, RouteValidationError, assemble_route,
                                                    assemble_resolved, check_connection)
from modules.blender.components.examples import spatial_route_spec
from modules.blender.components.math3d import axis_angle, quaternion, qmul, rotate, sub
from modules.blender.planning import validate_plan

FIXTURES = Path(__file__).resolve().parents[1]/'fixtures'


def placed_after(a, kind='StraightChannel', *, offset=(0., 0., 0.), rotation=(0., 0., 0., 1.), parameters=None):
    b = create_component(component_spec('b', kind, parameters=parameters))
    origin = tuple(v+d for v, d in zip(sub(a.exit_anchor.position_m, rotate(rotation, b.entry_anchor.position_m)), offset))
    return create_component(component_spec('b', kind, parameters=parameters, transform=Transform(origin, rotation)))


def test_transform_composition_rotation_and_bounds():
    a = Transform.from_dict({'position_m': [1, 2, 3], 'quaternion_xyzw': axis_angle((0., 0., 1.), math.pi/2)})
    b = Transform((2., 0., 1.))
    assert a.compose(b).point((1., 0., 0.)) == pytest.approx(a.point(b.point((1., 0., 0.))))
    assert a.direction((1., 0., 0.)) == pytest.approx((0., 1., 0.))
    c = create_component(component_spec('platform', 'Platform', transform=a))
    assert c.bounds['minimum_m'] == pytest.approx((.4, 2., 2.88))
    assert c.bounds['maximum_m'] == pytest.approx((1.6, 4., 3.))
    assert c.entry_anchor.position_m == pytest.approx((1., 2., 3.15))
    assert quaternion((0., 0., 0., -1.)) == quaternion((0., 0., 0., 1.))
    assert json.dumps(quaternion((0., 0., 0., -1.))) == json.dumps(quaternion((0., 0., 0., 1.)))


@pytest.mark.parametrize('kind', list(REGISTRY))
def test_every_component_is_reusable_serializable_and_has_simple_separate_geometry(kind):
    original = component_spec('mechanism', kind, bevel_m=.002)
    before = copy.deepcopy(original)
    c = create_component(original)
    assert original == before
    assert create_component(json.loads(json.dumps(c.spec.to_dict()))).to_json() == c.to_json()
    changed = c.parameters
    changed['actor_radius_m'] = 99
    assert c.parameters['actor_radius_m'] == .15
    assert c.collision_geometry is not c.visual_geometry
    assert all(g.to_dict()['shape'] == 'box' for g in c.collision_geometry)
    assert all(o['mode'] == 'fixed' for o in c.analytic_obstacles())
    assert len(c.analytic_obstacles()) == c.feasibility_constraints['collider_count']
    assert c.feasibility_constraints['motion_solution_required']
    transformed = copy.deepcopy(original)
    transformed['transform'] = Transform((10., 20., 30.), axis_angle((0., 0., 1.), .7)).to_dict()
    d = create_component(transformed)
    assert d.entry_anchor.position_m == pytest.approx(d.spec.transform.point(c.entry_anchor.position_m))
    assert d.parameters == c.parameters
    assert len(d.collision_geometry) == len(c.collision_geometry)


def test_local_anchor_assertions_are_checked_and_never_move_geometry():
    spec = component_spec('ramp', 'Ramp')
    c = create_component(spec)
    spec['entry_anchor'] = c.entry_anchor.to_dict()
    assert create_component(spec).entry_anchor == c.entry_anchor
    spec['entry_anchor']['position_m'][0] += .01
    with pytest.raises(ValueError, match='anchor contradicts'):
        create_component(spec)


@pytest.mark.parametrize(('kind', 'parameters', 'match'), [
    ('Ramp', {'width_m': .2}, 'radius does not fit'),
    ('Ramp', {'drop_m': -1}, 'drop_m'),
    ('Ramp', {'actor_radius_m': 0}, 'positive'),
    ('CurvedChannel', {'segments': 4.5}, 'integer'),
    ('CurvedChannel', {'segments': 1000}, 'integer'),
    ('CurvedChannel', {'turn_deg': 0}, 'turn'),
    ('CurvedChannel', {'radius_m': .3}, 'radius'),
    ('DropTransition', {'drop_m': 0}, 'drop'),
    ('DropTransition', {'gap_m': 10}, 'landing'),
    ('Catcher', {'length_m': .4}, 'room'),
    ('SupportFrame', {'beam_m': 2}, 'beams'),
    ('FixedDeflector', {'panel_length_m': .1}, 'beyond'),
    ('FixedDeflector', {'deflection_deg': 0}, 'angle'),
    ('ClearancePost', {'path_offset_m': .2}, 'surface gap'),
    ('Platform', {'unknown_style': 1}, 'unknown'),
    ('Ramp', {'length_m': float('nan')}, 'finite'),
    ('Ramp', {'length_m': True}, 'boolean'),
    ('Ramp', {'length_m': 10**400}, 'large'),
])
def test_impossible_and_unsupported_component_parameters_rejected(kind, parameters, match):
    with pytest.raises(ValueError, match=match):
        create_component(component_spec('bad', kind, parameters=parameters))


@pytest.mark.parametrize(('field', 'value'), [
    ('type', 'motor'), ('collision', {'mode': 'fixed', 'shape': 'beauty_mesh', 'friction': .3, 'restitution': .4}),
    ('visual', {'bevel_m': .1}), ('transform', {'position_m': [0, 0, 0], 'quaternion_xyzw': [0, 0, 0, 2]}),
])
def test_invalid_spec_rejected(field, value):
    spec = component_spec('bad', 'Ramp')
    spec[field] = value
    with pytest.raises(ValueError):
        create_component(spec)


def test_valid_connection_and_numeric_failure_reasons():
    a = create_component(component_spec('a', 'StraightChannel'))
    b = placed_after(a)
    result = check_connection(a, b, .15)
    assert result['status'] == 'PASSED'
    assert result['metrics']['anchor_distance_m'] == 0
    assert result['metrics']['minimum_seam_surface_gap_m'] == pytest.approx(0)
    cases = [(placed_after(a, offset=(.01, 0., 0.)), 'ANCHOR_DISTANCE'),
             (placed_after(a, offset=(0., 0., .01)), 'INSUFFICIENT_HEIGHT_ENERGY'),
             (placed_after(a, rotation=axis_angle((0., 0., 1.), math.pi/2)), 'DIRECTION_MISMATCH'),
             (placed_after(a, offset=(-.5, 0., 0.)), 'ILLEGAL_COMPONENT_PENETRATION'),
             (placed_after(a, offset=(0., .29, 0.)), 'ACTOR_PENETRATES_SEAM')]
    for component, reason in cases:
        rejected = check_connection(a, component, .15)
        assert rejected['status'] == 'FAILED' and reason in rejected['errors'], rejected
    assert 'ACTOR_RADIUS_CLEARANCE' in check_connection(a, b, .36)['errors']
    assert 'ACTOR_RADIUS_SPEC_MISMATCH' in check_connection(a, b, .1)['errors']


def test_height_energy_and_structure_ports_are_explicit():
    a = create_component(component_spec('a', 'StraightChannel'))
    uphill = placed_after(a, rotation=axis_angle((0., 1., 0.), -.1))
    low = check_connection(a, uphill, .15)
    assert 'INSUFFICIENT_HEIGHT_ENERGY' in low['errors']
    high = check_connection(a, uphill, .15, ConnectionPolicy(available_entry_speed_m_s=3))
    assert 'INSUFFICIENT_HEIGHT_ENERGY' not in high['errors']
    assert high['metrics']['minimum_entry_speed_m_s'] > 1
    frame = placed_after(a, 'SupportFrame')
    assert 'NOT_TRAVEL_PORT' in check_connection(a, frame, .15)['errors']
    catcher = placed_after(a, 'Catcher')
    assert 'TERMINAL_HAS_OUTGOING_CONNECTION' in check_connection(catcher, placed_after(catcher), .15)['errors']


def test_route_uses_xyz_and_has_deterministic_serialized_connections():
    document = spatial_route_spec()
    assert document == json.loads((FIXTURES/'component-route.example.json').read_text())
    route = assemble_route(document)
    assert assemble_route(json.loads(json.dumps(document))).to_json() == route.to_json()
    assert len(route.connection_reports) == 4
    points = [p for c in route.components.values() for p in c.centerline]
    assert all(max(p[i] for p in points)-min(p[i] for p in points) > 1 for i in range(3))
    from modules.blender.planning.validator import _spatial_metrics
    assert _spatial_metrics(points)['plane_thickness_m'] > .05
    assert route.components['ramp'].entry_anchor.position_m[2] > route.components['catcher'].exit_anchor.position_m[2]
    welds = [o for r in route.connection_reports for o in r['metrics']['solid_overlaps']]
    assert welds and all(w['allowed_static_weld'] and w['penetration_depth_m'] < .08 for w in welds)
    assert all(r['metrics']['minimum_seam_surface_gap_m'] > -1e-7 for r in route.connection_reports)
    assert route.to_dict()['physics_validated'] is False
    # Omit declared weld permission: no implicit static penetration allowance.
    for c in document['connections']:
        c['policy']['maximum_joint_overlap_m'] = 0
    with pytest.raises(RouteValidationError) as error:
        assemble_route(document)
    assert 'ILLEGAL_COMPONENT_PENETRATION' in str(error.value)


def test_invalid_route_graph_and_remote_collisions():
    original = spatial_route_spec()
    for changed in ['duplicate', 'missing', 'terminal', 'branch', 'radius']:
        document = copy.deepcopy(original)
        if changed == 'duplicate':
            document['components'].append(document['components'][0])
        elif changed == 'missing':
            document['connections'].pop()
        elif changed == 'terminal':
            document['terminal_component'] = 'ramp'
        elif changed == 'branch':
            document['connections'].append(document['connections'][0])
        else:
            document['actor_radius_m'] = .2
        with pytest.raises(ValueError):
            assemble_route(document)
    # An unrelated post intersecting the ramp cannot borrow an adjacent weld allowance.
    document = copy.deepcopy(original)
    document['components'].append(component_spec('intruder', 'ClearancePost', transform=Transform((1., 0., 2.5))))
    with pytest.raises(RouteValidationError, match='NONADJACENT_COMPONENT_PENETRATION'):
        assemble_route(document)


def test_backend_collider_budget_is_enforced_before_connection_work():
    document = spatial_route_spec()
    for i in range(5):
        document['components'].append(component_spec(f'curve-{i}', 'CurvedChannel'))
    with pytest.raises(ValueError, match='128 fixed OBBs'):
        assemble_route(document)


def test_drop_and_clearance_expose_physical_measurements():
    drop = create_component(component_spec('drop', 'DropTransition'))
    assert drop.feasibility_constraints['ballistic_interval']
    assert drop.feasibility_constraints['horizontal_launch_estimate']['fall_time_s'] == pytest.approx(math.sqrt(1.2/9.81))
    post = create_component(component_spec('clearance', 'ClearancePost'))
    assert post.feasibility_constraints['nominal_surface_clearance_m'] == pytest.approx(.04)
    assert post.feasibility_constraints['route_capable'] is False
    curved = create_component(component_spec('curve', 'CurvedChannel', parameters={'turn_deg': -90}))
    assert curved.exit_anchor.position_m[1] < 0
    assert curved.feasibility_constraints['route_approximation_bound_m'] > 0


def test_resolved_constraints_are_consumed_with_layout_and_actor_binding():
    plan = json.loads((FIXTURES/'scene-feasibility-plan.example.json').read_text())
    layout = spatial_route_spec()
    route = assemble_route(layout)
    support = copy.deepcopy(plan['intent']['actors'][1])
    support['id'] = 'approach'
    plan['intent']['actors'].append(support)
    plan['route']['start']['position_m'] = list(route.components['ramp'].entry_anchor.position_m)
    plan['route']['terminal']['position_m'] = list(route.components['catcher'].exit_anchor.position_m)
    # Numeric intent positions are hints, so align them to the candidate component anchors.
    for stage, component in zip(plan['route']['stages'], ['ramp', 'deflector', 'post', 'catcher']):
        stage['position_m'] = list(route.components[component].exit_anchor.position_m)
    report, resolved = validate_plan(plan)
    assert report['status'] == 'PASSED', report
    built = assemble_resolved(resolved, layout)
    assert len(built['collider_actor_map']) == len(built['analytic_obstacles'])
    assert built['event_constraints'][2]['measurement_status'] == 'NOT_MEASURED'
    assert built['planning_constraints']['reference_lessons'] == plan['intent']['reference_lessons']
    assert built['resolved_constraints_sha256'] == resolved['sha256']
    resolved['constraints']['actor_radius_m'] = .2
    with pytest.raises(ValueError, match='stale'):
        assemble_resolved(resolved, layout)


def test_tilted_support_and_unknown_policies_rejected():
    with pytest.raises(ValueError, match='face away'):
        create_component(component_spec('upside', 'Ramp', transform=Transform(quaternion_xyzw=axis_angle((1., 0., 0.), math.pi))))
    with pytest.raises(ValueError, match='exactly'):
        ConnectionPolicy.from_dict({'distance_tolerance_m': .001})
    # Quaternion composition remains unit length across a bend plus an incline.
    q = qmul(axis_angle((0., 1., 0.), .3), axis_angle((0., 0., 1.), 1.2))
    assert math.hypot(*quaternion(q)) == pytest.approx(1.)


def test_obstacles_are_consumable_by_existing_backend_without_translation():
    from modules.blender.production.analytic import simulate_sphere
    component = create_component(component_spec('floor', 'Platform'))
    states = simulate_sphere((1., 0., .15), (0., 0., 0.), .15, component.analytic_obstacles(),
                             duration_s=1/240, hz=240, substeps=4)
    assert len(states) == 2 and states[-1]['contacts'] == [0]
    assert states[-1]['position_m'][2] == pytest.approx(.15)


def test_component_cli_outputs_numeric_geometry_and_failure_receipt(tmp_path):
    import subprocess
    import sys
    source, out = tmp_path/'route.json', tmp_path/'geometry.json'
    source.write_text(json.dumps(spatial_route_spec()))
    command = [sys.executable, '-m', 'modules.blender.components', str(source), '--out', str(out)]
    assert subprocess.run(command, capture_output=True, timeout=15).returncode == 0
    assert json.loads(out.read_text())['status'] == 'READY_FOR_PARAMETER_SOLUTION'
    original = out.read_bytes()
    source.write_text('{}')
    assert subprocess.run(command, capture_output=True, timeout=15).returncode != 0
    assert out.read_bytes() == original
    failed = tmp_path/'failure.json'
    assert subprocess.run(command[:-1]+[str(failed)], capture_output=True, timeout=15).returncode == 1
    assert json.loads(failed.read_text())['status'] == 'FAILED'


@pytest.mark.parametrize(('kind', 'parameters', 'match'), [
    ('DropTransition', {'length_m': 1.3}, 'footprint'),
    ('FixedDeflector', {'panel_height_m': .1}, 'cover'),
    ('ClearancePost', {'post_height_m': .1}, 'reach'),
])
def test_geometry_covers_declared_interaction(kind, parameters, match):
    with pytest.raises(ValueError, match=match):
        create_component(component_spec('bad', kind, parameters=parameters))
