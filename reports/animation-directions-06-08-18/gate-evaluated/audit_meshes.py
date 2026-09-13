"""Independent, bounded evaluated-surface audit. No Blender or project imports."""
import hashlib
import argparse
import heapq
import json
import math
import os
from pathlib import Path
import signal
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
START = time.time()


def sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def dot(a, b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def lerp(a, b, t):
    return tuple(a[i]+t*(b[i]-a[i]) for i in range(3))


def transform(v, pose):
    v = tuple(v[i]*pose['scale'][i] for i in range(3))
    q = pose['quaternion_xyzw']
    # Blender's evaluated quaternion is normalized up to export precision.
    length = math.sqrt(sum(x*x for x in q))
    x, y, z, w = (a/length for a in q)
    t = cross((x, y, z), v)
    tt = cross((x, y, z), t)
    return tuple(pose['position_m'][i]+v[i]+2*w*t[i]+2*tt[i] for i in range(3))


def bbox(points):
    return tuple(min(p[i] for p in points) for i in range(3))+tuple(max(p[i] for p in points) for i in range(3))


def box_distance(a, b):
    return sum(max(0., a[i]-b[i+3], b[i]-a[i+3])**2 for i in range(3))


def point_segment(p, a, b):
    ab = sub(b, a)
    t = max(0., min(1., dot(sub(p, a), ab)/max(dot(ab, ab), 1e-300)))
    return dot(sub(p, lerp(a, b, t)), sub(p, lerp(a, b, t)))


def point_triangle(p, tri):
    a, b, c = tri
    ab, ac, ap = sub(b, a), sub(c, a), sub(p, a)
    d00, d01, d11 = dot(ab, ab), dot(ab, ac), dot(ac, ac)
    d20, d21 = dot(ap, ab), dot(ap, ac)
    denom = d00*d11-d01*d01
    if denom > 1e-26:
        v, w = (d11*d20-d01*d21)/denom, (d00*d21-d01*d20)/denom
        if v >= 0 and w >= 0 and v+w <= 1:
            n = cross(ab, ac)
            return dot(ap, n)**2/dot(n, n)
    return min(point_segment(p, a, b), point_segment(p, b, c), point_segment(p, c, a))


def segment_segment(p1, q1, p2, q2):
    d1, d2, r = sub(q1, p1), sub(q2, p2), sub(p1, p2)
    a, e, f = dot(d1, d1), dot(d2, d2), dot(d2, r)
    if a < 1e-26:
        s, t = 0., max(0., min(1., f/max(e, 1e-300)))
    else:
        c = dot(d1, r)
        if e < 1e-26:
            t, s = 0., max(0., min(1., -c/a))
        else:
            b = dot(d1, d2)
            denom = a*e-b*b
            s = max(0., min(1., (b*f-c*e)/denom)) if denom > 1e-26 else 0.
            t = (b*s+f)/e
            if t < 0:
                t, s = 0., max(0., min(1., -c/a))
            elif t > 1:
                t, s = 1., max(0., min(1., (b-c)/a))
    delta = sub(lerp(p1, q1, s), lerp(p2, q2, t))
    return dot(delta, delta), s


def segment_triangle(p, q, tri):
    a, b, c = tri
    n = cross(sub(b, a), sub(c, a))
    direction = sub(q, p)
    denominator = dot(n, direction)
    if abs(denominator) > 1e-24:
        t = dot(n, sub(a, p))/denominator
        if 0 <= t <= 1 and point_triangle(lerp(p, q, t), tri) < 1e-22:
            return 0., t
    best = min((point_triangle(p, tri), 0.), (point_triangle(q, tri), 1.))
    for x, y in ((a, b), (b, c), (c, a)):
        best = min(best, segment_segment(p, q, x, y))
    return best


class BVH:
    def __init__(self, triangles):
        self.triangles = triangles
        self.bounds = [bbox(t[2]) for t in triangles]
        self.nodes = []
        self.build(list(range(len(triangles))))

    def build(self, ids):
        bounds = tuple(min(self.bounds[j][i] for j in ids) for i in range(3))+tuple(max(self.bounds[j][i+3] for j in ids) for i in range(3))
        index = len(self.nodes)
        self.nodes.append(None)
        if len(ids) <= 8:
            self.nodes[index] = bounds, ids, None
        else:
            axis = max(range(3), key=lambda i: bounds[i+3]-bounds[i])
            ids.sort(key=lambda j: self.bounds[j][axis]+self.bounds[j][axis+3])
            middle = len(ids)//2
            self.nodes[index] = bounds, None, (self.build(ids[:middle]), self.build(ids[middle:]))
        return index

    def nearest(self, p, q=None):
        query = bbox([p] if q is None else [p, q])
        queue = [(box_distance(query, self.nodes[0][0]), 0)]
        best = (math.inf, -1, 0.)
        while queue:
            distance, index = heapq.heappop(queue)
            if distance > best[0]:
                break
            _, ids, children = self.nodes[index]
            if ids is not None:
                for j in ids:
                    if box_distance(query, self.bounds[j]) > best[0]:
                        continue
                    d, s = (point_triangle(p, self.triangles[j][2]), 0.) if q is None else segment_triangle(p, q, self.triangles[j][2])
                    if d < best[0]:
                        best = d, j, s
            else:
                for child in children:
                    d = box_distance(query, self.nodes[child][0])
                    if d <= best[0]:
                        heapq.heappush(queue, (d, child))
        return math.sqrt(max(0., best[0])), self.triangles[best[1]][:2], best[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_snapshot(folder, filename, hashes):
    path = ROOT/'artifacts/blender/revamp/directions'/folder/filename
    data = path.read_bytes()
    dest = HERE/'inputs'/folder/filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.read_bytes() != data:
        raise ValueError('refusing to replace frozen input snapshot: '+str(dest))
    dest.write_bytes(data)
    hashes[str(path.relative_to(ROOT))] = digest(data)
    return [json.loads(line) for line in data.splitlines()] if filename.endswith('.jsonl') else json.loads(data)


def actor_shape(spec, obj):
    vs = obj['vertices_local']
    result = {'shape': spec['shape'], 'vertices': len(vs), 'triangles': len(obj['triangles']), 'local_bounds_m': bbox(vs), 'initial_transform': obj['transform']}
    if spec['shape'] == 'sphere':
        radii = [math.sqrt(dot(v, v)) for v in vs]
        planes = []
        for ids in obj['triangles']:
            a, b, c = (vs[i] for i in ids)
            n = cross(sub(b, a), sub(c, a))
            if dot(n, n) > 1e-24:
                planes.append(abs(dot(a, n))/math.sqrt(dot(n, n)))
        result.update(vertex_radius_m=[min(radii), max(radii)], circumsphere_to_inscribed_face_deficit_m=spec['radius_m']-min(planes))
    elif spec['shape'] == 'cylinder':
        result['radial_vertex_error_m'] = max(abs(math.hypot(v[0], v[1])-spec['radius_m']) for v in vs)
        result['axial_length_error_m'] = max(v[2] for v in vs)-min(v[2] for v in vs)-spec['length_m']
    elif spec['shape'] == 'hoop':
        major, tube = spec['radius_m']-spec['tube_radius_m'], spec['tube_radius_m']
        result['torus_surface_vertex_error_m'] = max(abs(math.hypot(math.hypot(v[0], v[1])-major, v[2])-tube) for v in vs)
        result['finite_torus_inertia_ratio'] = (major*major+.75*tube*tube)/spec['radius_m']**2
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', default='v1')
    parser.add_argument('--six', default='06_three_ways_down-v1')
    parser.add_argument('--eight', default='08_spiral_observatory-v1')
    args = parser.parse_args()
    output_path = HERE/('RESULTS-'+args.tag+'.json')
    if output_path.exists():
        raise ValueError('refusing to overwrite an earlier result: '+str(output_path))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('150-second audit bound')))
    signal.alarm(150)
    report = {'pid': os.getpid(), 'pgid': os.getpgid(0), 'started_unix_s': START, 'input_sha256': {}, 'shapes': {}, 'static_geometry': {}, 'clearance': {}}
    print(json.dumps({'pid': report['pid'], 'pgid': report['pgid'], 'status': 'started'}), flush=True)
    packets = {}
    for folder in (args.six, args.eight):
        packet = load_snapshot(folder, 'packet.json', report['input_sha256'])
        geometry = load_snapshot(folder, 'evaluated_geometry.json', report['input_sha256'])
        rows = load_snapshot(folder, 'replay_states.jsonl', report['input_sha256'])
        packets[folder] = packet, geometry, rows
        report['shapes'][folder] = {a['id']: actor_shape(a, geometry[a['id']]) for a in packet['actors']}
        static, changed = [], []
        for spec in packet['geometry']:
            if spec['id'] not in geometry:
                changed.append({'id': spec['id'], 'reason': 'presentation replacement; original object absent'})
                continue
            actual = geometry[spec['id']]
            if spec['shape'] == 'mesh':
                expected = spec['vertices']
                measured = [transform(v, actual['transform']) for v in actual['vertices_local']]
                if len(expected) != len(measured):
                    changed.append({'id': spec['id'], 'packet_vertices': len(expected), 'evaluated_vertices': len(measured)})
                    continue
                error = max(math.dist(a, b) for a, b in zip(expected, measured, strict=True))
                static.append((error, spec['id']))
        report['static_geometry'][folder] = {'presentation_topology_changes': changed, 'maximum_same_topology_packet_to_evaluated_vertex_error_m': max(static)}
    packet, geometry, rows = packets[args.eight]
    moving = {a['id'] for a in packet['actors']}
    triangles = {'guide': [], 'other_static': []}
    for oid, obj in geometry.items():
        if oid in moving:
            continue
        group = 'guide' if any(token in oid for token in ('-floor', '-guide-', '-capture-')) else 'other_static'
        vertices = [transform(v, obj['transform']) for v in obj['vertices_local']]
        for index, ids in enumerate(obj['triangles']):
            triangles[group].append((oid, index, tuple(vertices[i] for i in ids)))
    radius = packet['actors'][0]['radius_m']
    centers = [s['objects']['bead']['position_m'] for s in rows]
    for group, tris in triangles.items():
        tree = BVH(tris)
        minimum, swept = (math.inf, None), (math.inf, None)
        max_gap = -math.inf
        for i, center in enumerate(centers):
            d, who, _ = tree.nearest(center)
            gap = d-radius
            max_gap = max(max_gap, gap)
            if gap < minimum[0]:
                minimum = gap, {'tick': i, 'time_s': i/240, 'object': who[0], 'triangle': who[1]}
            if i:
                d, who, fraction = tree.nearest(centers[i-1], center)
                gap = d-radius
                if gap < swept[0]:
                    swept = gap, {'time_s': (i-1+fraction)/240, 'interval_ticks': [i-1, i], 'object': who[0], 'triangle': who[1]}
            if i % 1800 == 0:
                print(json.dumps({'group': group, 'tick': i, 'elapsed_s': time.time()-START}), flush=True)
        report['clearance'][group] = {'triangles': len(tris), 'samples': len(centers), 'minimum_center_to_triangle_minus_radius_m': minimum, 'maximum_nearest_gap_m': max_gap, 'minimum_linear_swept_clearance_m': swept}
    # The moving receiver is a separate actual-pose OBB surface check.
    for actor in ('observatory-plunger', 'observatory-coil'):
        receiver = geometry[actor]
        bounds = bbox(receiver['vertices_local'])
        minimum = (math.inf, None)
        for i, row in enumerate(rows):
            pose = row['objects'][actor]
            delta = sub(row['objects']['bead']['position_m'], pose['position_m'])
            q = pose['quaternion_xyzw']
            inverse = {'position_m': [0., 0., 0.], 'scale': [1., 1., 1.], 'quaternion_xyzw': [-q[0], -q[1], -q[2], q[3]]}
            local = transform(delta, inverse)
            distance = math.sqrt(sum(max(0., bounds[j]*pose['scale'][j]-local[j], local[j]-bounds[j+3]*pose['scale'][j])**2 for j in range(3)))
            if distance-radius < minimum[0]:
                minimum = distance-radius, i/240
        report['clearance'][actor+'_sampled'] = {'samples': len(rows), 'minimum_gap_m': minimum,
            'method': 'evaluated local bounds transformed by every replay pose; OBB encloses coil mesh'}
    report['method'] = 'Independent exact point/segment-to-triangle Euclidean distances with AABB BVH; radius0.24m is conservative versus the inscribed evaluated bead. Segment sweeps use Blender linear translation between adjacent240Hz keys. Moving plunger sampled separately. No native Bullet or perceptual acceptance claim.'
    report['limitations'] = ['Surface-clearance sign denotes sphere/surface overlap, not a general signed-distance field for arbitrary closed meshes. Analytic point-inside exclusions and exact rendered-sphere mesh contact are not separately certified.', 'Moving receiver and coil use sampled OBB bounds, not inter-sample sweeps.', '06 full body-to-mesh sweeps are not performed; shape and static mesh agreement only.']
    report['elapsed_s'] = time.time()-START
    report['status'] = 'MEASURED_NOT_GLOBAL_ACCEPTANCE'
    output_path.write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps({'status': report['status'], 'elapsed_s': report['elapsed_s'], 'clearance': report['clearance']}), flush=True)


if __name__ == '__main__':
    main()
