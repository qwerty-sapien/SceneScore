"""Independent mechanics controls and bounded direction-18 acceptance checks."""
import math
from functools import lru_cache

import pytest

from modules.blender.production.directions.puck import (
    Settings,
    box_separation,
    build_direction,
    circle_box,
    contact_impulse,
)


@lru_cache(maxsize=5)
def packet(substeps=8, unit=1.0, launch=True):
    return build_direction('18', hz=240, substeps=substeps,
                           settings=Settings(length_unit_m=unit, launch_enabled=launch))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def test_analytic_fixed_wall_restitution_and_frictionless_energy():
    outgoing, spin, omega, impulse = contact_impulse((2, 0.3), 0, (-1, 0),
                                                    0.24, 0.4, 0.75)
    assert outgoing == pytest.approx((-1.5, 0.3))
    assert impulse == pytest.approx((-1.4, 0))
    assert spin == omega == 0
    assert 0.2 * (4 - outgoing[0] ** 2) == pytest.approx(0.35)


def test_glancing_rail_friction_creates_spin_without_energy():
    v, w, _, impulse = contact_impulse((1, -0.6), 0, (0, 1), 0.24, 0.4, 0.82, 0.05)
    assert w != 0
    assert abs(impulse[0]) <= 0.05 * impulse[1] + 1e-12
    assert 0.2 * dot(v, v) + 0.25 * 0.4 * 0.24 ** 2 * w ** 2 < 0.2 * 1.36


def test_oblique_coupled_hinge_conserves_angular_momentum_and_dissipates():
    velocity, spin, omega = (1.0, -0.3), 0.2, -0.1
    normal, arm = (-0.6, 0.8), (0.5, 0.2)
    mass, radius, hinge_inertia = 0.4, 0.24, 0.3
    disc_inertia = mass * radius ** 2 / 2
    centre = tuple(arm[i] + radius * normal[i] for i in range(2))
    outgoing, new_spin, new_omega, impulse = contact_impulse(
        velocity, spin, normal, radius, mass, 0.8, 0.1, arm, omega, hinge_inertia)
    before_l = mass * cross(centre, velocity) + disc_inertia * spin + hinge_inertia * omega
    after_l = mass * cross(centre, outgoing) + disc_inertia * new_spin + hinge_inertia * new_omega
    assert after_l == pytest.approx(before_l, abs=1e-12)
    before_e = mass * dot(velocity, velocity) / 2 + disc_inertia * spin ** 2 / 2 + hinge_inertia * omega ** 2 / 2
    after_e = mass * dot(outgoing, outgoing) / 2 + disc_inertia * new_spin ** 2 / 2 + hinge_inertia * new_omega ** 2 / 2
    assert 0 <= after_e < before_e
    relative = (outgoing[0] + new_omega * arm[1], outgoing[1] - new_omega * arm[0])
    assert dot(relative, normal) > 0  # Separates after both impulse stages.
    tangent = (-normal[1], normal[0])
    assert abs(dot(impulse, tangent)) <= 0.1 * dot(impulse, normal) + 1e-12
    assert cross(arm, normal) != 0 and cross(arm, tangent) != 0


def test_finite_box_corners_and_separating_axes():
    gap, normal = circle_box((1.3, 1.4), 0.2, (0, 0), (1, 1))
    assert gap == pytest.approx(0.3)
    assert normal == pytest.approx((0.6, 0.8))
    a = dict(centre=(0, 0), half=(1, 0.2), angle=0)
    b = dict(centre=(0, 0.5), half=(1, 0.2), angle=0)
    assert box_separation(a, b) == pytest.approx(0.1)
    b['centre'] = (0, 0.2)
    assert box_separation(a, b) < 0


def test_complete_causal_sequence_and_genuine_misses():
    p = packet()
    events = p['events']
    contacts = {e['actors'][1]: e for e in events if e['type'] in ('contact', 'compliant_contact')}
    assert set(contacts) == {'bank-rail', 'hinged-fin', 'release-peg', 'groove-upper', 'dock-stop'}
    assert 4 < contacts['bank-rail']['time_s'] < 9
    assert 9 < contacts['hinged-fin']['time_s'] < 14
    assert 14 < contacts['release-peg']['time_s'] < 19
    assert 24 < contacts['dock-stop']['time_s'] < 26
    latch = next(e for e in events if e['type'] == 'latch_release')
    assert latch['time_s'] == contacts['release-peg']['time_s']
    assert latch['trigger_impulse_n_s'] == contacts['release-peg']['impulse_n_s']
    assert contacts['hinged-fin']['hinge_omega_after_rad_s'] < -0.1
    misses = [e for e in events if e['type'] == 'near_miss']
    assert {e['actors'][1] for e in misses} == {'far-fin', 'near-fin'}
    assert all(0.025 < e['surface_clearance_m'] < 0.1 and e['impulse_n_s'] == 0 for e in misses)
    assert 25 < p['validation']['settled_s'] < 27


def test_no_unpowered_release_or_time_driven_motion():
    p = packet(launch=False)
    assert p['events'] == []
    assert p['validation']['latch_release_s'] is None
    assert p['validation']['final_door_angle_rad'] == math.pi / 2
    start = p['states'][0]['objects']['ceramic-puck']['position_m']
    assert all(math.dist(s['objects']['ceramic-puck']['position_m'], start) < 1e-12 for s in p['states'])


def test_integrated_door_waits_for_actual_latch_and_weight_descends():
    p = packet()
    release = p['validation']['latch_release_s']
    first = p['states'][0]['objects']
    for state in p['states']:
        if state['time_s'] < release:
            assert state['objects']['greenhouse-door']['position_m'] == first['greenhouse-door']['position_m']
            assert state['objects']['counterweight']['position_m'] == first['counterweight']['position_m']
    assert p['states'][-1]['objects']['counterweight']['position_m'][2] == pytest.approx(2.05 - 0.17 * math.pi / 2)
    assert p['validation']['final_door_angle_rad'] == 0


def test_contact_energy_sweeps_and_substep_bounds():
    v = packet()['validation']
    assert v['max_contact_energy_gain_j'] <= 1e-12
    assert v['max_abs_energy_balance_residual_j'] < 0.0002
    assert v['max_penetration_m'] < 0.001
    assert v['max_substep_motion_m'] < 0.001 < v['no_tunnelling_bound_m']
    assert min(v['hinge_static_clearances_m'].values()) > v['hinge_sweep_between_sample_bound_m'] + 0.02
    assert 0.005 < v['max_stop_compression_m'] < 0.02
    assert v['final_puck_speed_m_s'] < 0.001


def test_si_units_do_not_change_trajectory_or_impulses():
    metres, centimetres = packet(), packet(unit=0.01)
    for a, b in zip(metres['states'], centimetres['states'], strict=True):
        for id_, obj in a['objects'].items():
            assert math.dist(obj['position_m'], b['objects'][id_]['position_m']) < 1e-8
            assert obj['quaternion_xyzw'] == pytest.approx(b['objects'][id_]['quaternion_xyzw'], abs=1e-8)
    for a, b in zip(metres['events'], centimetres['events'], strict=True):
        assert a['type'] == b['type'] and a['time_s'] == b['time_s']
        if 'impulse_n_s' in a:
            assert a['impulse_n_s'] == pytest.approx(b['impulse_n_s'], abs=1e-8)


def test_timestep_refinement_converges_within_one_millimetre():
    coarse, base, fine = packet(4), packet(8), packet(16)
    def difference(a, b):
        return max(math.dist(x['objects']['ceramic-puck']['position_m'], y['objects']['ceramic-puck']['position_m'])
                   for x, y in zip(a['states'], b['states'], strict=True))
    coarse_error = difference(coarse, base)
    fine_error = difference(base, fine)
    assert fine_error < 0.001
    assert fine_error < 0.75 * coarse_error
    definitions = {a['id']: a for a in base['actors']}
    for a, b in zip(base['states'], fine['states'], strict=True):
        for id_, obj in a['objects'].items():
            other = b['objects'][id_]
            assert math.dist(obj['position_m'], other['position_m']) < 0.001
            cosine = min(1.0, abs(dot(obj['quaternion_xyzw'], other['quaternion_xyzw'])))
            assert 2 * math.acos(cosine) < 0.001
            if definitions[id_].get('deformable'):
                for axis, half in enumerate(definitions[id_]['half_extents_m']):
                    assert 2 * half * abs(obj['scale'][axis] - other['scale'][axis]) < 0.001
    for a, b in zip(base['events'], fine['events'], strict=True):
        assert a['type'] == b['type'] and a['actors'] == b['actors']
        assert abs(a['time_s'] - b['time_s']) <= 1 / 240 + 2 / 1920


def rotate(q, v):
    x, y, z, w = q
    tx, ty, tz = 2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])
    return (v[0] + w * tx + y * tz - z * ty,
            v[1] + w * ty + z * tx - x * tz,
            v[2] + w * tz + x * ty - y * tx)


def obb_clearance(centre_a, q_a, half_a, centre_b, q_b, half_b):
    axes_a = [rotate(q_a, axis) for axis in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]]
    axes_b = [rotate(q_b, axis) for axis in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]]
    axes = axes_a + axes_b
    for a in axes_a:
        for b in axes_b:
            c = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
            length = math.sqrt(dot(c, c))
            if length > 1e-9:
                axes.append(tuple(x / length for x in c))
    delta = tuple(a - b for a, b in zip(centre_a, centre_b, strict=True))
    return max(abs(dot(delta, axis)) - sum(abs(dot(axis, a)) * h for a, h in zip(axes_a, half_a)) -
               sum(abs(dot(axis, b)) * h for b, h in zip(axes_b, half_b)) for axis in axes)


def support_clearances(p):
    """Independent 3D OBB sweep of fixed support exclusions, at all240Hz rows."""
    supports = [g for g in p['geometry'] if g.get('constraint_support')]
    worst = (math.inf, None, None)
    for definition in p['actors']:
        id_ = definition['id']
        if id_ == 'launch-spring':
            continue  # Elastic spring intentionally joins the fixed anchor.
        half = definition.get('half_extents_m', [definition.get('radius_m', 0)] * 2 +
                              [definition.get('length_m', 0) / 2])
        for support in supports:
            if support['id'] == id_ + '-bearing':
                continue  # The bearing is the explicitly constrained joint.
            fixed_half = support.get('half_extents_m', [support.get('radius_m', 0)] * 2 +
                                     [support.get('length_m', 0) / 2])
            for state in p['states']:
                obj = state['objects'][id_]
                extent = [h * s for h, s in zip(half, obj['scale'], strict=True)]
                gap = obb_clearance(obj['position_m'], obj['quaternion_xyzw'], extent,
                    support['position_m'], support['quaternion_xyzw'], fixed_half)
                if gap < worst[0]:
                    worst = (gap, id_, support['id'])
    return worst


def test_excluded_support_geometry_clears_full_actor_sweeps():
    # OBBs enclose cylinders, so a positive gap is conservative for their mesh.
    minimum, _, _ = support_clearances(packet())
    assert minimum > 0.03
    # The largest possible dynamic-point movement between rows is under4mm;
    # positive margins above30mm also certify the inter-row sweep here.
    assert packet()['validation']['max_substep_motion_m'] * 8 < 0.004


def test_packet_clock_rigid_scale_and_support_alignment():
    p = packet()
    assert len(p['states']) == 7201
    deformable = {a['id'] for a in p['actors'] if a.get('deformable')}
    assert deformable == {'launch-spring', 'dock-stop'}
    tilt = math.atan(p['parameters']['table_slope'])
    normal = (math.sin(tilt), 0, math.cos(tilt))
    for index, state in enumerate(p['states']):
        assert state['tick'] == index and state['time_s'] == index / 240
        for id_, obj in state['objects'].items():
            assert sum(v * v for v in obj['quaternion_xyzw']) == pytest.approx(1, abs=1e-12)
            assert len(obj['velocity_m_s']) == 3
            if id_ not in deformable:
                assert obj['scale'] == [1, 1, 1]
        pos = state['objects']['ceramic-puck']['position_m']
        assert dot(normal, (pos[0], pos[1], pos[2] - 1.1)) == pytest.approx(0.07, abs=1e-12)


@pytest.mark.parametrize('kwargs', [{'hz': 0}, {'substeps': 0}, {'duration_s': 31},
                                   {'settings': Settings(length_unit_m=float('nan'))},
                                   {'settings': Settings(mass_kg=0)}])
def test_unbounded_or_nonphysical_inputs_rejected(kwargs):
    with pytest.raises(ValueError):
        build_direction(**kwargs)
