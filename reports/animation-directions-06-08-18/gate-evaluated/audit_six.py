"""Independent06 bounds: swept floor, other-static capsule, rail halfspaces."""
import argparse
import json
import math
import os
import signal
import time

from audit_meshes import BVH, HERE, bbox, cross, dot, load_snapshot, sub, transform


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', default='06_three_ways_down-v2')
    parser.add_argument('--tag', default='06-v2')
    args = parser.parse_args()
    output_path = HERE/('RESULTS-'+args.tag+'.json')
    if output_path.exists():
        raise ValueError('preserve previous result: '+str(output_path))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('150-second bound')))
    signal.alarm(150)
    started = time.time()
    report = {'pid': os.getpid(), 'pgid': os.getpgid(0), 'input_sha256': {}, 'actors': {}}
    print(json.dumps({'pid': report['pid'], 'pgid': report['pgid'], 'status': 'started'}), flush=True)
    folder = args.folder
    packet = load_snapshot(folder, 'packet.json', report['input_sha256'])
    geometry = load_snapshot(folder, 'evaluated_geometry.json', report['input_sha256'])
    rows = load_snapshot(folder, 'replay_states.jsonl', report['input_sha256'])
    moving = {a['id'] for a in packet['actors']}
    world = {oid: [transform(v, obj['transform']) for v in obj['vertices_local']]
             for oid, obj in geometry.items()}
    radius_bound = .2400004  # Encloses evaluated radius/scale/axis roundoff.
    for name in ('sphere', 'cylinder', 'hoop'):
        specs = next(a for a in packet['actors'] if a['id'] == name)
        centers = [s['objects'][name]['position_m'] for s in rows]
        lane = centers[0][1]
        side_half = {'sphere': .24, 'cylinder': .15, 'hoop': .025}[name]
        maximum_y_support = 0.
        maximum_axle_error = 0.
        for row in rows:
            pose = row['objects'][name]
            rot = dict(pose, position_m=[0., 0., 0.], scale=[1., 1., 1.])
            axes = [transform(a, rot) for a in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
            coefficients = [axes[i][1]*pose['scale'][i] for i in range(3)]
            normal = math.sqrt(sum(v*v for v in coefficients))
            radial = math.hypot(coefficients[0], coefficients[1])
            if name == 'sphere':
                support = .2400003*normal
            elif name == 'cylinder':
                support = .24*radial+.15*abs(coefficients[2])
            else:
                support = .215*radial+.025*normal
            maximum_y_support = max(maximum_y_support, support+abs(pose['position_m'][1]-lane))
            maximum_axle_error = max(maximum_axle_error, math.hypot(axes[2][0], axes[2][2]))
        excluded, minimum_rail_plane = [], math.inf
        for oid in geometry:
            if oid.startswith(name+'-guide-left') or oid.startswith(name+'-guide-right'):
                excluded.append(oid)
                ys = [v[1]-lane for v in world[oid]]
                if min(ys) < 0 < max(ys):
                    raise ValueError('own side rail crosses lane centre: '+oid)
                minimum_rail_plane = min(minimum_rail_plane, min(abs(y) for y in ys))
        if minimum_rail_plane-maximum_y_support < -.0002:
            raise ValueError('own side rail fails evaluated Y separating plane: '+name)
        floors, others = [], []
        for oid, obj in geometry.items():
            if oid in moving or oid in excluded:
                continue
            target = floors if oid == name+'-floor' else others
            for index, ids in enumerate(obj['triangles']):
                target.append((oid, index, tuple(world[oid][i] for i in ids)))
        # The own floor is a Y extrusion of its XZ cross-section. Its distance
        # from the cylinder's central Y segment therefore equals the centre's
        # distance while the segment remains inside the extrusion width.
        fv = world[name+'-floor']
        low_y, high_y = min(v[1] for v in fv), max(v[1] for v in fv)
        assert low_y < lane-.15 and high_y > lane+.15
        assert all(min(abs(v[1]-low_y), abs(v[1]-high_y)) < 1e-6 for v in fv)
        pairs = {(round(v[0], 6), round(v[2], 6)): set() for v in fv}
        for v in fv:
            pairs[(round(v[0], 6), round(v[2], 6))].add(0 if abs(v[1]-low_y)<1e-6 else 1)
        assert all(s == {0, 1} for s in pairs.values())
        for _, _, tri in floors:
            n = cross(sub(tri[1], tri[0]), sub(tri[2], tri[0]))
            length = math.sqrt(dot(n, n))
            if length:
                assert min(abs(n[1])/length, abs(1-abs(n[1])/length)) < 1e-6
        floor_tree, other_tree = BVH(floors), BVH(others)
        floor_best = (math.inf, None)
        other_best = (math.inf, None)
        other_lower = (math.inf, None)
        previous_distance = None
        for i, center in enumerate(centers):
            if i:
                d, who, fraction = floor_tree.nearest(centers[i-1], center)
                if d-radius_bound < floor_best[0]:
                    floor_best = d-radius_bound, {'time_s': (i-1+fraction)/240, 'triangle': who[1]}
            if name == 'cylinder':
                a, b = list(center), list(center)
                a[1] -= .15
                b[1] += .15
                d, who, _ = other_tree.nearest(a, b)
            else:
                d, who, _ = other_tree.nearest(center)
            if d-radius_bound < other_best[0]:
                other_best = d-radius_bound, {'time_s': i/240, 'object': who[0], 'triangle': who[1]}
            if previous_distance is not None:
                lower = min(d, previous_distance)-radius_bound-math.dist(center, centers[i-1])/2-2e-7
                if lower < other_lower[0]:
                    other_lower = lower, {'interval_ticks': [i-1, i]}
            previous_distance = d
            if i % 2400 == 0:
                print(json.dumps({'actor': name, 'tick': i, 'elapsed_s': time.time()-started}), flush=True)
        report['actors'][name] = {'bound': 'world-Y capsule radius.24 endpoints+/-.15' if name == 'cylinder' else 'circumsphere radius.24',
            'own_rail_ids_excluded_only_after_halfspace_check': excluded,
            'maximum_actual_Y_half_support_m': maximum_y_support,
            'minimum_own_rail_Y_halfspace_m': minimum_rail_plane,
            'Y_separation_lower_bound_m': minimum_rail_plane-maximum_y_support,
            'maximum_local_Z_axle_deviation_from_world_Y': maximum_axle_error,
            'own_floor_Y_extrusion_verified': True,
            'own_floor_exact_swept_gap_m': floor_best,
            'other_static_sampled_gap_m': other_best,
            'other_static_inter_sample_gap_lower_bound_m': other_lower,
            'triangles_tested': len(floors)+len(others)}
    report['scope'] = 'Evaluated static triangles at all7201poses. Own floor exact swept distances; other-static linear-between-key distance lower bound from1-Lipschitz translation. Own rail exclusion independently bounded in Y. Moving receivers remain covered by root explicit-pose/source-gap verification.'
    report['elapsed_s'] = time.time()-started
    report['target_m'] = .0002
    report['status'] = 'PASSED_SCOPED_STATIC_GEOMETRY' if all(
        a['own_floor_exact_swept_gap_m'][0] >= -.0002 and a['other_static_inter_sample_gap_lower_bound_m'][0] >= -.0002
        for a in report['actors'].values()) else 'FAILED'
    output_path.write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps({'status': report['status'], 'actors': report['actors'], 'elapsed_s': report['elapsed_s']}), flush=True)


if __name__ == '__main__':
    main()
