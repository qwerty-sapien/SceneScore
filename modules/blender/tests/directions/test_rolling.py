"""Independent equations and geometric controls for constrained directions."""
import hashlib
import json
import math
import struct
from functools import lru_cache

import pytest

from modules.blender.production.directions.rolling import (
    Path, RADIUS, add, build_direction, dot, mul, norm, simulate, spiral_path,
)


@lru_cache(maxsize=4)
def packet(direction, substeps=8):
    return build_direction(direction, hz=240, substeps=substeps)


def test_constant_ramp_matches_independently_derived_rotational_acceleration():
    theta = .12
    tangent = (math.cos(theta), 0., -math.sin(theta))
    path = Path([(100., lambda u: ((u*tangent[0], 0., 20+u*tangent[2]),
                                  tangent, (0., 0., 0.)))])
    for inertia in (.4, .5, 1.):
        rows = simulate(path, inertia_ratio=inertia, duration_s=2, hz=60, substeps=8)
        acceleration = 9.81*math.sin(theta)/(1+inertia)
        for row in rows:
            assert row['arc_length_m'] == pytest.approx(.5*acceleration*row['time_s']**2, abs=1e-10)
            assert row['speed_m_s'] == pytest.approx(acceleration*row['time_s'], abs=1e-10)
            assert row['floor_normal_N'] == pytest.approx(9.81*math.cos(theta), abs=1e-10)
            assert row['static_friction_N'] == pytest.approx(-inertia*acceleration, abs=1e-10)
            assert abs(row['energy_residual_J']) < 1e-9


def test_absent_gravity_slope_is_a_negative_motion_control():
    path = Path([(10., lambda u: ((u, 0., 1.), (1., 0., 0.), (0., 0., 0.)))])
    rows = simulate(path, inertia_ratio=.4, duration_s=2, hz=30)
    assert all(row['speed_m_s'] == 0 and row['arc_length_m'] == 0 for row in rows)


def test_spiral_joins_are_c2_and_have_no_parameter_cusps():
    path = spiral_path()
    for (length, left), (_, right) in zip(path.pieces, path.pieces[1:]):
        for a, b in zip(left(length), right(0.)):
            assert a == pytest.approx(b, abs=3e-12)
    assert min(norm(path.at(path.end*i/2000)[1]) for i in range(2001)) > .3
    for i in range(2001):
        _, _, n, b, k, _, _ = path.frame(path.end*i/2000)
        for height in (-.28, -.24, .24, .28):
            for side in (-.28, .28):
                assert 1-dot(k, add(mul(n, height), mul(b, side))) > .1


@pytest.mark.parametrize('direction', ['06', '08'])
def test_exact_30_second_clock_energy_and_resolved_displacements(direction):
    p = packet(direction)
    assert len(p['states']) == 7201
    assert [s['time_s'] for s in p['states']] == [i/240 for i in range(7201)]
    for metrics in p['validation']['actors'].values():
        assert metrics['max_energy_residual_J'] < 1e-3
        assert metrics['max_output_displacement_over_radius'] < .25
        assert metrics['max_guide_work_W'] < 1e-9
        assert metrics['dissipated_energy_J'] > .1
        assert abs(metrics['final_speed_m_s']) < .02
    assert max(m['last_motion_s'] for m in p['validation']['actors'].values()) >= 27


def test_three_way_inertia_is_visible_before_different_profiles():
    p = packet('06')
    row = p['states'][5*240]['objects']
    assert row['sphere']['position_m'][0] > row['cylinder']['position_m'][0] > row['hoop']['position_m'][0]
    assert row['sphere']['speed_m_s'] > row['hoop']['speed_m_s']*1.2
    actors = {a['id']: a for a in p['actors']}
    torus = actors['hoop']
    expected = ((torus['radius_m']-torus['tube_radius_m'])**2+.75*torus['tube_radius_m']**2)/torus['radius_m']**2
    assert torus['inertia_ratio'] == pytest.approx(expected)
    for name in ('sphere', 'cylinder', 'hoop'):
        metrics = p['validation']['actors'][name]
        assert metrics['min_floor_normal_N'] > 0
        assert metrics['max_required_static_friction_coefficient'] < .8
        rows = [s['objects'][name] for s in p['states']]
        assert any(r['speed_m_s'] < -.03 for r in rows)
        for r in rows[::37]:
            assert r['angular_velocity_world_rad_s'][1]*RADIUS == pytest.approx(r['speed_m_s'])
            assert sum(q*q for q in r['quaternion_xyzw']) == pytest.approx(1.)


def test_spiral_sliding_is_explicit_and_downward_force_has_visible_capture():
    p = packet('08')
    assert p['actors'][0]['zero_spin'] is True
    assert any(g['id'].endswith('capture-rail') for g in p['geometry'])
    assert p['validation']['actors']['bead']['max_capture_rail_normal_N'] > 1
    assert p['validation']['actors']['bead']['max_reaction_N'] < 150
    assert all(s['objects']['bead']['angular_velocity_world_rad_s'] == [0., 0., 0.]
               for s in p['states'])
    kinds = {e['type'] for e in p['events']}
    assert {'outer-spiral-complete', 'crossover-complete', 'lower-counterspiral-complete',
            'receiver-contact', 'receiver-recoil'} <= kinds


def test_spiral_nonlocal_course_and_stationary_orb_have_positive_clearance():
    path = spiral_path()
    centers = [path.at(path.end*i/1000)[0] for i in range(1001)]
    arc = [0.]
    for a, b in zip(centers, centers[1:]):
        arc.append(arc[-1]+math.dist(a, b))
    clearance = min(math.dist(a, b) for i, a in enumerate(centers)
                    for j, b in enumerate(centers) if j > i and arc[j]-arc[i] > 2.)
    # Swept groove floor offset radius + half-width and bead radius.
    assert clearance > math.hypot(.28, .28)+.24+.04
    assert min(math.dist(p, (0., 0., 2.5)) for p in centers) > .48+.24


def test_vertical_posts_do_not_intersect_the_lower_bead_journey():
    p = packet('08')
    posts = [g for g in p['geometry'] if g['shape'] == 'box' and
             ('-support-' in g['id'] or g['id'] == 'central-orb-column')]
    assert len(posts) >= 4
    for state in p['states']:
        center = state['objects']['bead']['position_m']
        for post in posts:
            distance = math.sqrt(sum(max(0., abs(center[j]-post['position_m'][j])-post['half_extents_m'][j])**2
                                     for j in range(3)))
            # A whole output-step travel bound is reserved beyond the body.
            margin = norm(state['objects']['bead']['velocity_m_s'])/240+.001
            assert distance >= RADIUS+margin


@pytest.mark.parametrize('direction', ['06', '08'])
def test_receiver_deforms_continuously_and_records_all_sink_energy(direction):
    p = packet(direction)
    coils = [a['id'] for a in p['actors'] if a['shape'] == 'coil']
    for name in coils:
        values = [s['objects'][name]['scale'][0] for s in p['states']]
        assert min(values) > .05
        assert max(values)-min(values) > .1
        assert max(abs(a-b) for a, b in zip(values, values[1:])) < .06
    for name in p['validation']['actors']:
        rows = [s['objects'][name] for s in p['states']]
        assert all(b['dissipated_energy_J'] >= a['dissipated_energy_J']-1e-10
                   for a, b in zip(rows, rows[1:]))
        assert min(r['receiver_force_N'] for r in rows) >= 0
        assert min(r['receiver_gap_m'] for r in rows) >= -1e-7
        assert any(r['dock_compression_m'] > .01 and not r['receiver_contact'] for r in rows)
        assert any(r['receiver_contact'] for r in rows)


@pytest.mark.parametrize('direction', ['06', '08'])
def test_eight_and_sixteen_substeps_converge_at_the_actual_240hz_clock(direction):
    a, b = packet(direction, 8), packet(direction, 16)
    for name in a['states'][0]['objects']:
        max_position = max(math.dist(x['objects'][name]['position_m'], y['objects'][name]['position_m'])
                           for x, y in zip(a['states'], b['states']))
        max_velocity = max(math.dist(x['objects'][name]['velocity_m_s'], y['objects'][name]['velocity_m_s'])
                           for x, y in zip(a['states'], b['states']))
        assert max_position < 2e-4
        assert max_velocity < 1e-3
        for x, y in zip(a['states'], b['states']):
            q1, q2 = x['objects'][name]['quaternion_xyzw'], y['objects'][name]['quaternion_xyzw']
            angle = 2*math.acos(min(1., abs(sum(i*j for i, j in zip(q1, q2)))))
            assert angle < .002
            assert x['objects'][name]['scale'] == pytest.approx(y['objects'][name]['scale'], abs=2e-4)
    assert [(e['actor_id'], e['type']) for e in a['events']] == [(e['actor_id'], e['type']) for e in b['events']]
    assert [e['time_s'] for e in a['events']] == pytest.approx([e['time_s'] for e in b['events']], abs=1/240)


def test_fixed_seed_repeat_is_exact_without_a_random_or_clock_input():
    assert build_direction('06', hz=20, substeps=2) == build_direction('06', hz=20, substeps=2)


def test_out_of_scope_direction_is_rejected():
    with pytest.raises(ValueError, match='owns directions'):
        build_direction('18')


@pytest.mark.parametrize('direction,states_hash,events_hash', [
    ('06', '6d4463bb50a08448d3a737847a659f5cc84d14d6cef617d654e43560b486b233',
     'a24d23d30f40c4f03a800aee6df3c2e7513c16f19fe085d005bb4a4487d0d145'),
    ('08', '338562a90757e83476e82b26fd2d1919e7a6906976a0ec8d5582df58442a9f81',
     '5ee8f5ee58f08d07ccda5c8a8f0e027c7c3e91411282b5f5d9f7880dee99d819'),
])
def test_geometry_repair_preserves_every_dynamic_state_and_event_byte(direction, states_hash, events_hash):
    p = packet(direction)
    for key, expected in (('states', states_hash), ('events', events_hash)):
        data = json.dumps(p[key], sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        assert hashlib.sha256(data).hexdigest() == expected


def _point_triangle_distance(point, triangle):
    # Independent planar projection plus clamped edge minimization.
    a, b, c = triangle
    ab, ac, ap = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)], [point[i]-a[i] for i in range(3)]
    aa, bb, cc = sum(x*x for x in ab), sum(x*y for x, y in zip(ab, ac)), sum(x*x for x in ac)
    d, e = sum(x*y for x, y in zip(ap, ab)), sum(x*y for x, y in zip(ap, ac))
    denominator = aa*cc-bb*bb
    if denominator > 1e-26:
        u, v = (d*cc-e*bb)/denominator, (e*aa-d*bb)/denominator
        if u >= 0 and v >= 0 and u+v <= 1:
            return math.dist(point, [a[i]+u*ab[i]+v*ac[i] for i in range(3)])
    distances = []
    for a, b in ((a, b), (b, c), (c, a)):
        axis = [b[i]-a[i] for i in range(3)]
        u = sum((point[i]-a[i])*axis[i] for i in range(3))/max(1e-30, sum(x*x for x in axis))
        u = max(0., min(1., u))
        distances.append(math.dist(point, [a[i]+u*axis[i] for i in range(3)]))
    return min(distances)


@pytest.mark.parametrize('center,old_triangle,minimum_overlap', [
    ([-.8663250691954615, 1.7166747058808944, 2.4539704708024233],
     [[-.659115731716156, 1.9823800325393677, 2.4110281467437744],
      [-.599338173866272, 1.5219571590423584, 2.5328369140625],
      [-.7287144660949707, 2.016185998916626, 2.3709259033203125]], .031),
    ([.12055052700169853, -.9848438163783209, .6162830952522578],
     [[.015960886793492488, -1.0013734052274186, .8314084287351624],
      [.010534426748143613, -.9667966278851585, .8314084287351624],
      [.00795426626672454, -.9665224965433584, .8300957384914484]], .0002),
], ids=['evaluated-v1-31mm-wall', 'raw-v3-0.228mm-capture-sweep'])
def test_evaluated_skin_failure_witnesses_rejected_and_repaired_float32_facets_clear(
        center, old_triangle, minimum_overlap):
    assert RADIUS-_point_triangle_distance(center, old_triangle) > minimum_overlap
    closest = math.inf
    for mesh in packet('08')['geometry']:
        if mesh['shape'] != 'mesh':
            continue
        vertices = [struct.unpack('fff', struct.pack('fff', *p)) for p in mesh['vertices']]
        for face in mesh['faces']:
            for i in range(1, len(face)-1):
                triangle = [vertices[j] for j in (face[0], face[i], face[i+1])]
                if any(center[j] < min(p[j] for p in triangle)-RADIUS or
                       center[j] > max(p[j] for p in triangle)+RADIUS for j in range(3)):
                    continue
                closest = min(closest, _point_triangle_distance(center, triangle))
    assert closest >= RADIUS-.0002


def test_adaptive_skin_has_explicit_triangles_world_bounds_and_analytic_chord_certificate():
    p = packet('08')
    floor = next(g for g in p['geometry'] if g['id'] == 'observatory-floor')
    proof = floor['tessellation']
    assert proof['contact_skin_outward_allowance_m'] == .00006
    assert proof['independent_surface_intrusion_limit_m'] == .0002
    stations = proof['centerline_parameters']
    assert proof['max_station_arc_bound_m'] <= .025
    assert proof['max_center_chord_bound_m'] <= .00002
    assert proof['max_observed_surface_chord_error_m'] <= .000025
    assert proof['max_observed_contact_triangle_plane_error_m'] <= .00003
    assert proof['max_clearance_scaled_plane_error_ratio'] <= 1
    assert max(b-a for a, b in zip(stations, stations[1:])) > 4*min(b-a for a, b in zip(stations, stations[1:]))
    path = spiral_path()
    for a, b in zip(stations, stations[1:]):
        bound = path.geometry_second_derivative_bound(a, b)*(b-a)**2/8
        pa, pb = path.at(a)[0], path.at(b)[0]
        for fraction in (.13, .41, .79):
            actual = path.at(a+fraction*(b-a))[0]
            chord = [x+fraction*(y-x) for x, y in zip(pa, pb)]
            assert math.dist(actual, chord) <= bound+1e-12
    for g in p['geometry']:
        if any(token in g['id'] for token in ('-floor', '-contact-rail', '-capture-', '-upright-', '-rail-foot-')):
            assert all(len(face) == 3 for face in g['faces'])
    assert not any('-guide-left' in g['id'] or '-guide-right' in g['id'] for g in p['geometry'])
