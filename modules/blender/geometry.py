"""Dependency-free geometric math; distances use explicit primitive proxies."""
import math


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def area(vertices, triangles):
    total = 0.
    for i, j, k in triangles:
        a, b = sub(vertices[j], vertices[i]), sub(vertices[k], vertices[i])
        total += norm((a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]))/2
    return total


def sphere_sweep(a0, a1, b0, b1, radius_sum):
    """Exact first contact fraction for linear relative motion, including tunnelling."""
    p, v = sub(a0, b0), sub(sub(a1, a0), sub(b1, b0))
    c = dot(p, p)-radius_sum**2
    if c <= 0:
        return 0.
    aa, bb = dot(v, v), 2*dot(p, v)
    disc = bb*bb-4*aa*c
    if aa == 0 or disc < 0:
        return None
    t = (-bb-math.sqrt(disc))/(2*aa)
    return t if 0 <= t <= 1 else None


def gap(a, pa, b, pb):
    """Signed sphere/sphere or sphere/axis-aligned box gap; AABB box proxy otherwise."""
    d = norm(sub(pa, pb))
    if a['shape'] == b['shape'] == 'sphere':
        return d-a['radius']-b['radius'], 'analytic_sphere_proxy'
    if a['shape'] == 'sphere' or b['shape'] == 'sphere':
        if b['shape'] == 'sphere':
            return gap(b, pb, a, pa)
        q = [abs(x-y)-h for x, y, h in zip(pa, pb, b['half'])]
        signed = norm([max(x, 0) for x in q])+min(max(q), 0)
        return signed-a['radius'], 'analytic_sphere_aabb_proxy'
    q = [abs(x-y)-h-k for x, y, h, k in zip(pa, pb, a['half'], b['half'])]
    return norm([max(x, 0) for x in q])+min(max(q), 0), 'axis_aligned_box_exact'


def pair_timeline(a, b, samples, tolerance=1e-5):
    """One onset/sustain/release per episode; near miss needs a bracketed positive minimum.

    Samples are (seconds, evaluated position A, evaluated position B). Subframe export
    plus swept sphere tests bound missed fast contacts. No impulse is inferred.
    """
    rows = []
    for i, (t, pa, pb) in enumerate(samples):
        g, method = gap(a, pa, b, pb)
        if i:
            pt, ppa, ppb = samples[i-1]
            rel = tuple(x/(t-pt) for x in sub(sub(pb, pa), sub(ppb, ppa)))
            delta = sub(pb, pa)
            n = norm(delta)
            radial = dot(rel, delta)/n if n else 0.
            tangent = math.sqrt(max(0., dot(rel, rel)-radial**2))
        else:
            radial, tangent = 0., 0.
        rows.append(dict(t=t, gap=g, distance=norm(sub(pa, pb)), normal=radial,
                         tangent=tangent, method=method))
    events = []
    def emit(kind, start, end, point):
        events.append(dict(event_type=kind, onset_s=start, duration_s=end-start, sample=point))
    # Swept sphere contacts catch trajectories crossing entirely between samples.
    if a['shape'] == b['shape'] == 'sphere':
        for i in range(1, len(rows)):
            if rows[i-1]['gap'] > tolerance and rows[i]['gap'] > tolerance:
                t0, a0, b0 = samples[i-1]
                t1, a1, b1 = samples[i]
                u = sphere_sweep(a0, a1, b0, b1, a['radius']+b['radius'])
                if u is not None:
                    t = t0+u*(t1-t0)
                    point = dict(rows[i], t=t, gap=0., distance=a['radius']+b['radius'])
                    emit('collision', t, t, point)
    i = 0
    while i < len(rows):
        if rows[i]['gap'] <= tolerance:
            start = i
            while i+1 < len(rows) and rows[i+1]['gap'] <= tolerance:
                i += 1
            emit('contact_onset', rows[start]['t'], rows[start]['t'], rows[start])
            if i > start:
                emit('contact_sustain', rows[start]['t'], rows[i]['t'], rows[start])
            if i+1 < len(rows):
                emit('contact_release', rows[i+1]['t'], rows[i+1]['t'], rows[i+1])
        i += 1
    # Bracket each strict turn, extending across flat minima; reject contact windows.
    i = 1
    while i < len(rows)-1:
        if rows[i]['gap'] < rows[i-1]['gap']-tolerance:
            end = i
            while end+1 < len(rows) and abs(rows[end+1]['gap']-rows[i]['gap']) <= tolerance:
                end += 1
            if end+1 < len(rows) and rows[end+1]['gap'] > rows[i]['gap']+tolerance:
                lo, hi = i-1, end+1
                while lo > 0 and rows[lo-1]['gap'] > rows[lo]['gap']+tolerance:
                    lo -= 1
                while hi+1 < len(rows) and rows[hi+1]['gap'] > rows[hi]['gap']+tolerance:
                    hi += 1
                emit('approach', rows[lo]['t'], rows[i]['t'], rows[i])
                # Positive sampled gaps alone cannot rule out tunnelling. Certify each
                # linear segment: exact sphere sweep or conservative Lipschitz gap bound.
                certified=True
                for j in range(lo+1,hi+1):
                    _,a0,b0=samples[j-1]
                    _,a1,b1=samples[j]
                    if a['shape']==b['shape']=='sphere':
                        safe=sphere_sweep(a0,a1,b0,b1,a['radius']+b['radius']) is None
                    else:
                        displacement=norm(sub(sub(a1,a0),sub(b1,b0)))
                        safe=min(rows[j-1]['gap'],rows[j]['gap'])-displacement>tolerance
                    certified=certified and safe
                if rows[i]['gap'] > tolerance and certified:
                    emit('near_miss', rows[lo]['t'], rows[hi]['t'], rows[i])
                emit('separation', rows[end]['t'], rows[hi]['t'], rows[end])
                i = end
        i += 1
    return rows, sorted(events, key=lambda e: (e['onset_s'], e['event_type']))
