"""Independent mechanics expectations; no recipe or production-validator imports."""
import copy
import math

import pytest

from modules.blender.production.analytic import simulate_sphere


FLOOR = {'position_m': [0, 0, -.5], 'half_extents_m': [20, 20, .5],
         'quaternion_xyzw': [0, 0, 0, 1], 'friction': 1., 'restitution': 1.}
G = 9.81
R = .25


def energy(row):
    return G*row['position_m'][2] + sum(v*v for v in row['velocity_m_s'])/2 + .2*R*R*sum(
        w*w for w in row['angular_velocity_world_rad_s'])


def test_unconstrained_gravity_is_exact_and_has_no_stale_hold():
    rows = simulate_sphere([1, 2, 3], [2, -3, 1], R, [], 1., hz=120)
    for row in rows:
        t = row['time_s']
        assert row['position_m'] == pytest.approx([1+2*t, 2-3*t, 3+t-.5*G*t*t], abs=2e-11)
        assert row['velocity_m_s'] == pytest.approx([2, -3, 1-G*t], abs=2e-11)
        assert row['contacts'] == []
    assert rows[-1]['position_m'][2] < rows[-2]['position_m'][2]


def test_elastic_bounce_matches_independent_impact_time_and_energy():
    rows = simulate_sphere([0, 0, 2], [0, 0, 0], R, [FLOOR], 1., restitution=1, friction=0)
    impact = math.sqrt(2*(2-R)/G)
    incoming_speed = G*impact
    elapsed = 1-impact
    assert rows[-1]['position_m'][2] == pytest.approx(R+incoming_speed*elapsed-.5*G*elapsed**2, abs=2e-8)
    assert rows[-1]['velocity_m_s'][2] == pytest.approx(incoming_speed-G*elapsed, abs=2e-8)
    assert max(abs(energy(row)-2*G) for row in rows) < 2e-8
    contact_rows = [row for row in rows if row['contacts']]
    assert abs(contact_rows[0]['time_s']-impact) <= 1/240
    assert min(row['position_m'][2] for row in rows) >= R-1e-9


def test_material_restitution_is_product_and_dissipates_energy():
    floor = {**FLOOR, 'restitution': .8}
    rows = simulate_sphere([0, 0, 2], [0, 0, 0], R, [floor], .8, restitution=.5, friction=0)
    impact = math.sqrt(2*(2-R)/G)
    elapsed = .8-impact
    expected_upward = .4*G*impact
    assert rows[-1]['position_m'][2] == pytest.approx(R+expected_upward*elapsed-.5*G*elapsed**2, abs=2e-8)
    assert rows[-1]['velocity_m_s'][2] == pytest.approx(expected_upward-G*elapsed, abs=2e-8)
    assert energy(rows[-1]) < energy(rows[0])


def test_oblique_friction_matches_solid_sphere_impulse_and_loses_energy():
    rows = simulate_sphere([0, 0, 2], [3, 0, -1], R, [FLOOR], .65,
                           restitution=.8, friction=1, rolling_resistance=0)
    impact = (-1+math.sqrt(1+2*G*(2-R)))/G
    # I = 2/5 mr² gives tangential inverse effective mass 1 + 5/2.
    impulse = -3/3.5
    contact = next(row for row in rows if row['contacts'])
    assert contact['velocity_m_s'][0] == pytest.approx(3+impulse, abs=2e-9)
    assert contact['angular_velocity_world_rad_s'][1] == pytest.approx(-2.5*impulse/R, abs=2e-9)
    assert contact['time_s']-impact >= 0
    assert energy(contact) < energy(rows[0])
    assert all(math.sqrt(sum(q*q for q in row['quaternion_xyzw'])) == pytest.approx(1, abs=1e-12)
               for row in rows)
    assert rows[-1]['quaternion_xyzw'] != [0, 0, 0, 1]


def test_coulomb_cap_for_sliding_impact():
    rows = simulate_sphere([0, 0, 2], [30, 0, -1], R, [FLOOR], .6,
                           restitution=.5, friction=.01, rolling_resistance=0)
    impact = (-1+math.sqrt(1+2*G*(2-R)))/G
    incoming = 1+G*impact
    tangent_impulse = -.01*1.5*incoming
    contact = next(row for row in rows if row['contacts'])
    assert contact['velocity_m_s'][0] == pytest.approx(30+tangent_impulse, abs=2e-8)


def test_rotated_obstacle_normal_controls_frictionless_impulse():
    angle = .2
    normal = (math.sin(angle), 0, math.cos(angle))
    box = {**FLOOR, 'position_m': [0, 0, 0], 'half_extents_m': [20, 20, .1],
           'quaternion_xyzw': [0, math.sin(angle/2), 0, math.cos(angle/2)]}
    initial_gap = 2*normal[2]-.1-R
    impact = math.sqrt(2*initial_gap/(G*normal[2]))
    rows = simulate_sphere([0, 0, 2], [0, 0, 0], R, [box], .8,
                           restitution=1, friction=0, rolling_resistance=0)
    incoming_normal = -G*impact*normal[2]
    expected_x_velocity = -2*incoming_normal*normal[0]
    assert rows[-1]['velocity_m_s'][0] == pytest.approx(expected_x_velocity, abs=2e-8)
    assert abs(energy(rows[-1])-energy(rows[0])) < 2e-8


def test_rest_supported_sphere_stays_supported_without_gravity_easing():
    rows = simulate_sphere([0, 0, R], [0, 0, 0], R, [FLOOR], .25)
    assert rows[-1]['position_m'] == pytest.approx([0, 0, R], abs=1e-12)
    assert rows[-1]['velocity_m_s'] == pytest.approx([0, 0, 0], abs=1e-12)
    assert all(row['contacts'] == [0] for row in rows)


def test_rolling_resistance_is_explicit_dissipation():
    coast = simulate_sphere([0, 0, R], [2, 0, 0], R, [FLOOR], .5, rolling_resistance=0)
    slowed = simulate_sphere([0, 0, R], [2, 0, 0], R, [FLOOR], .5, rolling_resistance=.02)
    assert energy(slowed[-1]) < energy(coast[-1])
    assert all(energy(b) <= energy(a)+1e-10 for a, b in zip(slowed, slowed[1:]))


def test_missing_floor_is_a_negative_bounce_control():
    rows = simulate_sphere([0, 0, 2], [0, 0, 0], R, [], 1., restitution=1)
    assert rows[-1]['position_m'][2] == pytest.approx(2-.5*G, abs=2e-11)
    assert rows[-1]['position_m'][2] < 0
    assert rows[-1]['velocity_m_s'][2] < 0
    assert not any(row['contacts'] for row in rows)


def test_32_and_64_substeps_converge_without_changing_output_clock():
    args = ([0, 0, 2], [3, 0, 0], R, [FLOOR], 1.)
    a = simulate_sphere(*args, substeps=32)
    b = simulate_sphere(*args, substeps=64)
    assert len(a) == len(b) == 241
    assert a[-1]['time_s'] == b[-1]['time_s'] == 1
    assert max(math.dist(x['position_m'], y['position_m']) for x, y in zip(a, b)) < 1e-7
    assert max(math.dist(x['velocity_m_s'], y['velocity_m_s']) for x, y in zip(a, b)) < 1e-7


def test_bad_initial_containment_and_moving_solids_are_rejected():
    with pytest.raises(ValueError, match='containment/overlap'):
        simulate_sphere([0, 0, -.5], [0, 0, 0], R, [FLOOR], .1)
    with pytest.raises(ValueError, match='fixed obstacles'):
        simulate_sphere([0, 0, 2], [0, 0, 0], R, [{**FLOOR, 'mode': 'driven'}], .1)
    with pytest.raises(ValueError, match='integral tick count'):
        simulate_sphere([0, 0, 2], [0, 0, 0], R, [], .101)


def test_inputs_are_preserved_and_unresolved_fast_motion_fails_closed():
    obstacles = [copy.deepcopy(FLOOR)]
    before = copy.deepcopy(obstacles)
    simulate_sphere([0, 0, 2], [0, 0, 0], R, obstacles, .1)
    assert obstacles == before
    with pytest.raises(ValueError, match='displacement'):
        simulate_sphere([0, 0, 2], [1000, 0, 0], R, obstacles, .1, substeps=1)


def test_fixed_staircase_and_backstop_converge_to_supported_rest():
    boxes = [{**FLOOR, 'position_m': [0, 0, -.15], 'half_extents_m': [7, 4, .15],
              'friction': .85, 'restitution': .8},
             {**FLOOR, 'position_m': [5.6, 0, .35], 'half_extents_m': [.12, 3.7, .35],
              'friction': .7, 'restitution': .12}]
    for i in range(4):
        height = 1.6-.4*i
        boxes.append({**FLOOR, 'position_m': [-2.5+1.2*i, 0, height/2],
                      'half_extents_m': [.58, .8, height/2], 'friction': .7, 'restitution': .8})
    boxes.append({**FLOOR, 'position_m': [-3.4, 0, 2.1], 'half_extents_m': [.85, .5, .06],
                  'quaternion_xyzw': [0, math.sin(.35/2), 0, math.cos(.35/2)],
                  'friction': .7, 'restitution': .12})
    a = simulate_sphere([-3.9, 0, 2.63], [0, 0, 0], R, boxes, 8., restitution=.6, substeps=32)
    b = simulate_sphere([-3.9, 0, 2.63], [0, 0, 0], R, boxes, 8., restitution=.6, substeps=64)
    assert len(a) == len(b) == 1921
    assert set(i for row in a for i in row['contacts']) == set(range(7))
    assert a[-1]['position_m'][2] == pytest.approx(R, abs=1e-8)
    assert a[-1]['position_m'][0] <= 5.6-.12-R+1e-8
    assert a[-1]['contacts'] == [0, 1]
    assert math.sqrt(sum(v*v for v in a[-1]['velocity_m_s'])) < 1e-6
    assert max(math.dist(x['position_m'], y['position_m']) for x, y in zip(a, b)) < .001
