"""Check analytical acceptance examples without importing Blender or repo code.

Usage: python check_reference_cases.py [analytic_cases.json]

These are small exact-model reference checks. They test the included example data
and counterexamples, not a Blender scene, simulation engine or final render.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from typing import Any


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def axes(box: dict[str, Any]) -> list[list[float]]:
    angle = math.radians(box['rotation_z_deg'])
    c, s = math.cos(angle), math.sin(angle)
    return [[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]]


def projection_radius(box: dict[str, Any], axis: list[float]) -> float:
    return sum(h * abs(dot(a, axis)) for h, a in zip(box['half_extents_m'], axes(box)))


def box_gap_same_z_rotation(a: dict[str, Any], b: dict[str, Any]) -> float:
    # In these fixtures both boxes share a Z rotation, so their three common
    # orthogonal axes suffice for separating-axis and overlap-depth testing.
    if abs(a['rotation_z_deg'] - b['rotation_z_deg']) > 1e-10:
        raise ValueError('This tiny oracle only supports equally oriented boxes')
    delta = [y - x for x, y in zip(a['centre_m'], b['centre_m'])]
    return max(abs(dot(delta, axis)) - projection_radius(a, axis) - projection_radius(b, axis) for axis in axes(a))


def assess(case: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    kind = case['kind']
    tol = case.get('analytic_tolerance', 1e-8)
    if kind == 'constant_acceleration':
        initial = case['initial']
        error = 0.0
        for row in case['samples']:
            t = row['t_s']
            expected = [p + v * t + 0.5 * a * t * t for p, v, a in zip(initial['p_m'], initial['v_m_s'], initial['a_m_s2'])]
            error = max(error, max(abs(a - b) for a, b in zip(expected, row['p_m'])))
        return error <= tol, {'max_position_residual_m': error}
    if kind == 'isolated_1d_collision':
        m1, m2 = case['masses_kg']
        u1, u2 = case['incoming_m_s']
        v1, v2 = case['outgoing_m_s']
        before, after = m1 * u1 + m2 * u2, m1 * v1 + m2 * v2
        ke_before, ke_after = 0.5 * (m1 * u1**2 + m2 * u2**2), 0.5 * (m1 * v1**2 + m2 * v2**2)
        restitution_residual = abs((v2 - v1) - case['effective_restitution'] * (u1 - u2))
        valid = abs(after - before) <= tol and ke_after <= ke_before + tol and restitution_residual <= tol
        return valid, {'momentum_residual_kg_m_s': after - before, 'kinetic_energy_before_j': ke_before, 'kinetic_energy_after_j': ke_after, 'restitution_residual_m_s': restitution_residual}
    if kind == 'fixed_wall_collision':
        residual = abs(case['outgoing_normal_m_s'] + case['effective_restitution'] * case['incoming_normal_m_s'])
        return residual <= tol, {'normal_velocity_residual_m_s': residual}
    if kind == 'box_nonpenetration':
        a, b = case['boxes']
        gap = box_gap_same_z_rotation(a, b)
        aabb_overlap = all(abs(b['centre_m'][i] - a['centre_m'][i]) < projection_radius(a, unit) + projection_radius(b, unit) for i, unit in enumerate([[1,0,0],[0,1,0],[0,0,1]]))
        return gap >= -tol, {'signed_separating_axis_gap_m': gap, 'broad_phase_aabbs_overlap': aabb_overlap}
    if kind == 'rigid_scale':
        initial = case['world_scale_samples'][0]
        error = max(abs(s[i] - initial[i]) for s in case['world_scale_samples'] for i in range(3))
        return error <= tol, {'max_world_scale_drift': error}
    if kind == 'undisturbed_target':
        # This fixture explicitly assumes the target is stably supported,
        # receives no launch/contact and has no other external disturbance.
        displacement = max(math.sqrt(sum((p[i] - case['initial_position_m'][i])**2 for i in range(3))) for p in case['positions_m'])
        return displacement <= tol, {'maximum_displacement_m': displacement}
    raise ValueError(f'Unknown reference kind: {kind}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases', nargs='?', type=Path, default=Path(__file__).with_name('analytic_cases.json'))
    args = parser.parse_args()
    data = json.loads(args.cases.read_text())
    output: list[dict[str, Any]] = []
    for case in data['cases']:
        accepted, measurements = assess(case)
        output.append({'id': case['id'], 'expected_accept': case['expected_accept'], 'actual_accept': accepted, 'correct_classification': accepted == case['expected_accept'], 'measurements': measurements})
    good = all(item['correct_classification'] for item in output)
    result = {'scope': 'analytical_example_data_only_no_Blender_execution', 'status': 'PASSED' if good else 'FAILED', 'cases': len(output), 'positives_accepted': sum(x['expected_accept'] and x['actual_accept'] for x in output), 'negatives_rejected': sum(not x['expected_accept'] and not x['actual_accept'] for x in output), 'results': output}
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if good else 1)


if __name__ == '__main__':
    main()
