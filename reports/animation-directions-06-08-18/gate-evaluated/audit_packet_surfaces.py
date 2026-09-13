"""Read-only pre-Blender packet surface check using the independent BVH."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import time

from audit_meshes import BVH, HERE, transform


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('packet', type=Path)
    parser.add_argument('--states', type=Path, help='JSONL states; omit for states embedded in packet')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--timeout-s', type=int, default=150)
    parser.add_argument('--radius-reserve', type=float, default=1e-6,
                        help='Pre-evaluation numerical reserve in metres; actual evaluated mesh checked separately')
    args = parser.parse_args()
    output = HERE/('RAW-'+args.tag+'.json')
    if output.exists():
        raise ValueError('preserve previous result: '+str(output))
    assert 1 <= args.timeout_s <= 300
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError(str(args.timeout_s)+'-second bound')))
    signal.alarm(args.timeout_s)
    started = time.time()
    raw = args.packet.read_bytes()
    packet = json.loads(raw)
    if args.states:
        trace = args.states.read_bytes()
        states = [json.loads(line) for line in trace.splitlines()]
    else:
        states = packet['states']
        trace = json.dumps(states, sort_keys=True, separators=(',', ':')).encode()
    triangles = {'guide': [], 'other_static': []}
    omitted = []
    quads = 0
    box_faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),
                 (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),
                 (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    for spec in packet['geometry']:
        if spec['shape'] == 'mesh':
            vertices, faces = spec['vertices'], spec['faces']
        elif spec['shape'] == 'box':
            half = spec['half_extents_m']
            vertices = [[x*half[0], y*half[1], z*half[2]] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
            faces = box_faces
        else:
            omitted.append({'id': spec['id'], 'shape': spec['shape']})
            continue
        pose = {'position_m': spec.get('position_m', [0, 0, 0]),
                'quaternion_xyzw': spec.get('quaternion_xyzw', [0, 0, 0, 1]),
                'scale': [1, 1, 1]}
        world = [transform(v, pose) for v in vertices]
        group = 'guide' if any(word in spec['id'] for word in ('-floor', '-guide-', '-capture-', '-contact-rail')) else 'other_static'
        for index, face in enumerate(faces):
            if len(face) == 3:
                combinations = [face]
            elif len(face) == 4:
                quads += 1
                a, b, c, d = face
                # Both possible diagonals conservatively enclose Blender's choice.
                combinations = [(a, b, c), (a, c, d), (a, b, d), (b, c, d)]
            else:
                raise ValueError('explicit triangles/quads required: '+spec['id'])
            for ids in combinations:
                triangles[group].append((spec['id'], index, tuple(world[i] for i in ids)))
    report = {'pid': os.getpid(), 'pgid': os.getpgid(0), 'started_unix_s': started,
              'audit_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'distance_script_sha256': hashlib.sha256((HERE/'audit_meshes.py').read_bytes()).hexdigest(),
              'packet_path': str(args.packet), 'packet_sha256': hashlib.sha256(raw).hexdigest(),
              'states_path': str(args.states) if args.states else 'embedded packet states, canonical JSON',
              'states_sha256': hashlib.sha256(trace).hexdigest(),
              'events_canonical_sha256': hashlib.sha256(json.dumps(packet.get('events'), sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
              'quad_both_diagonals_tested': quads, 'omitted_static_shapes': omitted, 'results': {}}
    print(json.dumps({k: report[k] for k in ('pid', 'pgid', 'packet_sha256', 'states_sha256')}), flush=True)
    centers = [s['objects']['bead']['position_m'] for s in states]
    assert args.radius_reserve >= 0
    radius = next(a['radius_m'] for a in packet['actors'] if a['id'] == 'bead')+args.radius_reserve
    report['conservative_radius_m'] = radius
    report['numerical_reserve_m'] = args.radius_reserve
    for group, tris in triangles.items():
        bvh = BVH(tris)
        best = (float('inf'), None)
        sampled = (float('inf'), None)
        for i, center in enumerate(centers):
            d, who, _ = bvh.nearest(center)
            if d-radius < sampled[0]:
                sampled = d-radius, {'tick': i, 'time_s': i/240, 'object': who[0], 'face': who[1]}
            if i:
                d, who, t = bvh.nearest(centers[i-1], center)
                if d-radius < best[0]:
                    best = d-radius, {'time_s': (i-1+t)/240, 'interval_ticks': [i-1, i], 'object': who[0], 'face': who[1]}
            if i % 1800 == 0:
                print(json.dumps({'group': group, 'tick': i, 'elapsed_s': time.time()-started}), flush=True)
        report['results'][group] = {'triangles': len(tris), 'sampled_minimum_gap_m': sampled, 'linear_swept_minimum_gap_m': best}
    report['elapsed_s'] = time.time()-started
    report['scope'] = 'Pre-Blender raw static surfaces versus declared sphere plus explicit numerical reserve, full240Hz linear replay segments. No moving receiver, no render claim; compare actual evaluated mesh separately.'
    output.write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
