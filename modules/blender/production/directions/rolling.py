"""Passive, constrained mechanics for Three Ways Down / Spiral Observatory.

The coordinate is integrated from Newton/Lagrange equations, never from a
timeline. 06 is planar no-slip rolling with a measured-in-model viscoelastic
contact torque. 08 is a frictionless, zero-spin sliding bead in a fitted groove.
These are explicitly ideal guide models, not a Bullet contact simulation.
"""
from __future__ import annotations

import bisect
import math

G = 9.81
RADIUS = .24
CONTACT_SKIN_ALLOWANCE_M = .00006


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def mul(a, k):
    return tuple(x*k for x in a)


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    return mul(a, 1/norm(a))


def _qmul(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return (w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z)


class Path:
    """C2 parametric pieces; analytic derivatives, not a position lookup."""

    def __init__(self, pieces):
        self.pieces = pieces
        self.ends = []
        end = 0.
        for length, _ in pieces:
            end += length
            self.ends.append(end)
        self.end = end

    def at(self, u):
        if u < 0 or u > self.end:
            edge = 0. if u < 0 else self.end
            p, d, _ = self.at(edge)
            return add(p, mul(d, u-edge)), d, (0., 0., 0.)
        i = min(bisect.bisect_right(self.ends, u), len(self.pieces)-1)
        start = self.ends[i-1] if i else 0.
        return self.pieces[i][1](u-start)

    def frame(self, u):
        p, d, dd = self.at(u)
        h = norm(d)
        t = mul(d, 1/h)
        curvature = mul(add(dd, mul(t, -dot(t, dd))), 1/(h*h))
        n = unit(add((0., 0., 1.), mul(t, -t[2])))
        b = cross(t, n)
        return p, t, n, b, curvature, h, dot(d, dd)/(h*h)

    def geometry_second_derivative_bound(self, lo, hi):
        """Analytic bound used only by the skin tessellator, never dynamics."""
        start, result = 0., 0.
        for length, evaluate in self.pieces:
            a, b = max(lo, start), min(hi, start+length)
            if b > a:
                result = max(result, evaluate.geometry_second_bound(a-start, b-start))
            start += length
        return result


def _bezier_split(control, t):
    levels = [control]
    while len(levels[-1]) > 1:
        levels.append([add(mul(a, 1-t), mul(b, t))
                       for a, b in zip(levels[-1], levels[-1][1:])])
    return [level[0] for level in levels], [level[-1] for level in reversed(levels)]


def _quintic(a, b, length):
    coefficients = []
    for j in range(3):
        c0, c1, c2 = a[0][j], a[1][j]*length, a[2][j]*length*length/2
        p = b[0][j]-c0-c1-c2
        d = b[1][j]*length-c1-2*c2
        dd = b[2][j]*length*length-2*c2
        coefficients.append((c0, c1, c2, 10*p-4*d+dd/2,
                             -15*p+7*d-dd, 6*p-3*d+dd/2))

    derivatives = [coefficients]
    for _ in range(2):
        derivatives.append([tuple(i*c[i]/length for i in range(1, len(c)))
                            for c in derivatives[-1]])

    def evaluate(u):
        t = u/length
        result = []
        for order in derivatives:
            values = []
            for c in order:
                value = 0.
                for coefficient in reversed(c):
                    value = value*t+coefficient
                values.append(value)
            result.append(tuple(values))
        return tuple(result)
    # The cubic Bernstein hull of p'' is an interval bound, not a sample maximum.
    controls = [tuple(sum(derivatives[2][axis][i]*math.comb(k, i)/math.comb(3, i)
                          for i in range(k+1)) for axis in range(3)) for k in range(4)]
    def second_bound(lo, hi):
        left = _bezier_split(controls, hi/length)[0]
        restricted = _bezier_split(left, lo/hi if hi else 0.)[1]
        return max(norm(value) for value in restricted)
    evaluate.geometry_second_bound = second_bound
    return evaluate


def ramp_path(slope=-.045, length=6., y=0., profile=0):
    """Center path; visible floor is the exact radius offset of this path."""
    def evaluate(x):
        initial = -.0055
        h = max(0., min(1., x-1))
        blend = 10*h**3-15*h**4+6*h**5
        integral = 2.5*h**4-3*h**5+h**6+max(0., x-2)
        z = 2.2+initial*x+(slope-initial)*integral
        dz = initial+(slope-initial)*blend
        ddz = (slope-initial)*30*h*h*(1-h)**2 if 1 < x < 2 else 0.
        if 2 < x < length-1:
            w = length-3
            # sin^4 has value, first and second derivative zero at joins.
            cycles, amplitude = ((1, .024), (3, .008), (1, -.025))[profile]
            a = math.pi*cycles/w
            s, c = math.sin(a*(x-2)), math.cos(a*(x-2))
            z += amplitude*s**4
            dz += amplitude*4*a*s**3*c
            ddz += amplitude*4*a*a*(3*s*s*c*c-s**4)
        return (x-3., y, z), (1., 0., dz), (0., 0., ddz)
    cycles, amplitude = ((1, .024), (3, .008), (1, -.025))[profile]
    derivative_bound = 1.875*abs(slope+.0055)+4*abs(amplitude)*(math.pi*cycles/(length-3))**2
    evaluate.geometry_second_bound = lambda lo, hi: derivative_bound
    return Path([(length, evaluate)])


def _spiral(radius_a, radius_b, height_a, height_b, angle_a, angle_b):
    length = abs(angle_b-angle_a)
    sign = 1 if angle_b > angle_a else -1
    dr, dz = (radius_b-radius_a)/length, (height_b-height_a)/length

    def evaluate(u):
        angle, r = angle_a+sign*u, radius_a+dr*u
        c, s = math.cos(angle), math.sin(angle)
        return ((r*c, r*s, height_a+dz*u),
                (dr*c-sign*r*s, dr*s+sign*r*c, dz),
                (-2*sign*dr*s-r*c, 2*sign*dr*c-r*s, 0.))
    evaluate.geometry_second_bound = lambda lo, hi: max(abs(radius_a+dr*lo), abs(radius_a+dr*hi))+2*abs(dr)
    return length, evaluate


def spiral_path():
    outer = _spiral(3.2, 2.05, 3.3, 3.05, 0., 2.5*math.pi)
    lower = _spiral(1.65, .8, 1.8, 1.35, math.pi/2, -2*math.pi)
    bridge = _quintic(outer[1](outer[0]), lower[1](0), 1.5)
    end = ((-.2, -1., .55), (-.6, 0., -.04), (0., 0., 0.))
    chute = _quintic(lower[1](lower[0]), end, 2.8)
    def terminal(u):
        return add(end[0], mul(end[1], u)), end[1], end[2]
    terminal.geometry_second_bound = lambda lo, hi: 0.
    return Path([outer, (1.5, bridge), lower, (2.8, chute), (1., terminal)])


def simulate(path, *, inertia_ratio, drag=0., duration_s=30., hz=240,
             substeps=8, dock_k=14., dock_c=5., radius=RADIUS):
    """Integrate unit-mass Lagrange equations and dissipation by RK4.

    Rolling drag is a resisting moment c*r*v; point-contact static friction is
    f=-k*a-c*v. Spring/dashpot forces act through the center along the guide.
    A unilateral massless spring/dashpot plunger separates when its force
    reaches zero, retracts freely, and may be contacted again. Gap and force
    zero-crossings are bisected; there is no tensile contact or body projection.
    """
    if (not isinstance(hz, int) or not isinstance(substeps, int) or hz < 1 or substeps < 1
            or duration_s <= 0 or hz*duration_s*substeps > 2_000_000
            or dock_k < 0 or dock_c <= 0 or inertia_ratio < 0 or radius <= 0):
        raise ValueError('invalid bounded clock')
    dt = 1/(hz*substeps)
    # u, du/dt, travelled arc length, dissipated energy, dock compression
    y = (0., 0., 0., 0., 0.)
    rows = []
    initial_z = path.at(0)[0][2]
    end_metric = norm(path.at(path.end)[1])
    contact = False

    def derivative(state, touching):
        u, w, _, _, compression = state
        _, t, _, _, _, h, metric = path.frame(u)
        v = h*w
        resistance = drag(u) if callable(drag) else drag
        plunger_speed = v if touching else -dock_k*compression/dock_c
        force = dock_k*compression+dock_c*v if touching else 0.
        a = (-G*t[2]-resistance*v-force)/(1+inertia_ratio)
        return (w, a/h-metric*w*w, v,
                resistance*v*v+dock_c*plunger_speed**2, plunger_speed)

    def advance(state, delta, touching):
        k1 = derivative(state, touching)
        k2 = derivative(add(state, mul(k1, delta/2)), touching)
        k3 = derivative(add(state, mul(k2, delta/2)), touching)
        k4 = derivative(add(state, mul(k3, delta)), touching)
        return tuple(state[i]+delta*(k1[i]+2*k2[i]+2*k3[i]+k4[i])/6 for i in range(5))

    def crossing(state, touching):
        if touching:
            velocity = norm(path.at(state[0])[1])*state[1]
            return -(dock_k*state[4]+dock_c*velocity)
        return (state[0]-path.end)*end_metric-state[4]

    for step in range(round(duration_s*hz)*substeps+1):
        if step % substeps == 0:
            u, w, s, dissipation, compression = y
            p, t, n, b, curvature, h, _ = path.frame(u)
            speed = h*w
            deriv = derivative(y, contact)
            acc = deriv[1]*h + path.frame(u)[6]*h*w*w
            reaction = add(mul(curvature, speed*speed),
                           add((0., 0., G), mul(t, -G*t[2])))
            floor = dot(reaction, n)
            resistance = drag(u) if callable(drag) else drag
            friction = -inertia_ratio*acc-resistance*speed
            energy = .5*(1+inertia_ratio)*speed*speed+G*p[2]+.5*dock_k*compression**2
            angle = s/radius if inertia_ratio else 0.
            roll = (0., math.sin(angle/2), 0., math.cos(angle/2))
            # Cylinder/torus local Z axis becomes world Y; no yaw steering.
            orientation = _qmul(roll, (-math.sqrt(.5), 0., 0., math.sqrt(.5))) if inertia_ratio else (0., 0., 0., 1.)
            rows.append({'tick': step//substeps, 'time_s': step*dt,
                         'position_m': list(p), 'velocity_m_s': list(mul(t, speed)),
                         'quaternion_xyzw': list(orientation), 'scale': [1., 1., 1.],
                         'angular_velocity_world_rad_s': [0., speed/radius if inertia_ratio else 0., 0.],
                         'parameter': u, 'arc_length_m': s, 'speed_m_s': speed,
                         'tangential_acceleration_m_s2': acc, 'floor_normal_N': floor,
                         'side_normal_N': dot(reaction, b), 'reaction_N': list(reaction),
                         'reaction_work_W': dot(reaction, mul(t, speed)),
                         'static_friction_N': friction, 'energy_J': energy,
                         'dissipated_energy_J': dissipation,
                         'energy_residual_J': energy+dissipation-G*initial_z,
                         'dock_compression_m': compression,
                         'plunger_speed_m_s': deriv[4], 'receiver_contact': contact,
                         'receiver_force_N': max(0., dock_k*compression+dock_c*speed) if contact else 0.,
                         'receiver_gap_m': compression-(u-path.end)*end_metric})
        if step == round(duration_s*hz)*substeps:
            break
        remaining = dt
        for _ in range(4):
            candidate = advance(y, remaining, contact)
            if crossing(candidate, contact) <= 1e-12:
                y = candidate
                break
            lo, hi = 0., remaining
            for _ in range(25):
                mid = (lo+hi)/2
                if crossing(advance(y, mid, contact), contact) > 0:
                    hi = mid
                else:
                    lo = mid
            y = advance(y, hi, contact)
            remaining -= hi
            contact = not contact
            if remaining < 1e-12:
                break
        else:
            raise ValueError('unresolved receiver switching')
    return rows


def _mesh(identifier, vertices, faces, material):
    return {'id': identifier, 'shape': 'mesh', 'position_m': [0., 0., 0.],
            'quaternion_xyzw': [0., 0., 0., 1.], 'vertices': vertices,
            'faces': faces, 'material': material}


def _orb():
    vertices = []
    for j in range(17):
        phi = math.pi*j/16
        for i in range(32):
            theta = 2*math.pi*i/32
            vertices.append([.48*math.sin(phi)*math.cos(theta),
                             .48*math.sin(phi)*math.sin(theta), 2.5+.48*math.cos(phi)])
    faces = [[j*32+i, j*32+(i+1)%32, (j+1)*32+(i+1)%32, (j+1)*32+i]
             for j in range(16) for i in range(32)]
    return [_mesh('central-observatory-orb', vertices, faces, 'gold'),
            {'id': 'central-orb-column', 'shape': 'box', 'position_m': [0., 0., 1.01],
             'half_extents_m': [.065, .065, 1.01], 'material': 'dark'}]


def _channel(path, identifier, *, radius=RADIUS, width=.72, samples=500,
             side_half_width=RADIUS, capture=False):
    """Floor offset and side walls, plus visible load-bearing legs."""
    vertices, faces, wall_a, wall_b, roof, centers, underside = [], [], [], [], [], [], []
    extension = 1.65/norm(path.at(path.end)[1])
    for i in range(samples+1):
        p, _, n, b, _, _, _ = path.frame((path.end+extension)*i/samples)
        centers.append(p)
        floor = add(p, mul(n, -radius))
        vertices.extend([list(add(floor, mul(b, -width/2))), list(add(floor, mul(b, width/2)))])
        underside.extend([list(add(add(floor, mul(b, -width/2)), mul(n, -.04))),
                          list(add(add(floor, mul(b, width/2)), mul(n, -.04)))])
        # Bead's side constraints lie at ±radius, not arbitrary decorative width.
        for target, sign in ((wall_a, -1), (wall_b, 1)):
            edge = add(p, mul(b, sign*side_half_width))
            target.extend([list(add(edge, mul(n, -.24))), list(add(edge, mul(n, .24)))])
        roof.extend([list(add(add(p, mul(n, radius)), mul(b, -.035))),
                     list(add(add(p, mul(n, radius)), mul(b, .035)))])
        if i:
            faces.append([2*i-2, 2*i-1, 2*i+1, 2*i])
    offset = len(vertices)
    deck_faces = list(faces)+[[offset+i for i in reversed(face)] for face in faces]
    deck_faces.extend([[i, i+2, i+2+offset, i+offset] for i in range(0, offset-2, 2)])
    deck_faces.extend([[i, i+offset, i+2+offset, i+2] for i in range(1, offset-2, 2)])
    deck_faces.extend([[0, offset, offset+1, 1], [offset-2, offset-1, 2*offset-1, 2*offset-2]])
    geometry = [_mesh(identifier+'-floor', vertices+underside, deck_faces, 'track'),
                _mesh(identifier+'-guide-left', wall_a, faces, 'brass'),
                _mesh(identifier+'-guide-right', wall_b, faces, 'brass')]
    if capture:
        geometry.append(_mesh(identifier+'-capture-rail', roof, faces, 'steel'))
        for index in range(0, samples+1, 45):
            p, t, n, b, _, _, _ = path.frame((path.end+extension)*index/samples)
            brace = [list(add(add(add(p, mul(t, a)), mul(b, lateral)), mul(n, h)))
                     for h in (radius, radius+.04) for lateral in (-radius-.04, radius+.04)
                     for a in (-.025, .025)]
            geometry.append(_mesh(f'{identifier}-capture-brace-{index}', brace,
                                  [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1],
                                   [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]], 'steel'))
    for i in range(0, samples, max(1, samples//12)):
        a, b = vertices[2*i], vertices[2*i+1]
        center = [(a[j]+b[j])/2 for j in range(3)]
        height = max(.05, center[2]-.15)
        if any(q[2] < height+.1 and math.hypot(q[0]-center[0], q[1]-center[1]) < radius+.12
               for q in centers):
            continue  # An upper post must not obstruct the lower journey.
        geometry.append({'id': f'{identifier}-support-{i}', 'shape': 'box',
                         'position_m': [center[0], center[1], height/2],
                         'half_extents_m': [.055, .055, height/2], 'material': 'dark'})
        p, t, n, b, _, _, _ = path.frame((path.end+extension)*i/samples)
        upper = [list(add(add(add(p, mul(n, -radius-.03)), mul(t, a)), mul(b, side)))
                 for a, side in ((-.055, -.055), (.055, -.055), (.055, .055), (-.055, .055))]
        lower = [[center[0]+a, center[1]+b, height]
                 for a, b in ((-.055, -.055), (.055, -.055), (.055, .055), (-.055, .055))]
        geometry.append(_mesh(f'{identifier}-support-cap-{i}', lower+upper,
                              [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
                               [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], 'steel'))
    p, t, _, _, _, _, _ = path.frame(path.end)
    back = add(p, mul(t, 1.6))
    geometry.append({'id': identifier+'-backstop', 'shape': 'box',
                     'position_m': list(back), 'half_extents_m': [.06, .36, .36],
                     'quaternion_xyzw': list(_align_x(t)), 'material': 'dark'})
    return geometry


def _skin_point(frame, profile_point):
    p, _, n, b, _, _, _ = frame
    height, lateral = profile_point
    return add(add(p, mul(n, height)), mul(b, lateral))


def _triangle_faces(faces):
    return [[face[0], face[i], face[i+1]] for face in faces for i in range(1, len(face)-1)]


def _skin_profiles(radius, width, side_half_width, capture):
    # Declared finite mesh/replay proxy allowance. It never enters mechanics.
    skin_radius = radius+CONTACT_SKIN_ALLOWANCE_M
    skin_side = side_half_width+CONTACT_SKIN_ALLOWANCE_M
    lateral = [-width/2, -.04, 0., .04, width/2]
    profiles = {'floor': [(-skin_radius, b) for b in lateral]+[(-skin_radius-.04, b) for b in reversed(lateral)]}
    for name, sign in (('left-contact-rail', -1), ('right-contact-rail', 1)):
        profiles[name] = [(h, sign*skin_side) for h in (-.018, 0., .018)] + [
            (h, sign*(skin_side+.024)) for h in (.018, 0., -.018)]
    if capture:
        profiles['capture-rail'] = [(skin_radius, b) for b in (-.035, 0., .035)] + [
            (skin_radius+.025, b) for b in (.035, 0., -.035)]
    return profiles


def _station_errors(path, lo, hi, profiles, radius):
    du = hi-lo
    fractions = (0., .25, .5, .75, 1.)
    frames = [path.frame(lo+fraction*du) for fraction in fractions]
    second_bound = path.geometry_second_derivative_bound(lo, hi)
    arc_bound = du*(min(frames[0][5], frames[-1][5])+second_bound*du)
    chord_bound = second_bound*du*du/8
    angle = max(math.acos(max(-1., min(1., dot(a[j], b[j]))))
                for a, b in zip(frames, frames[1:]) for j in (1, 2, 3))
    surface_chord, contact_plane_error, plane_ratio = 0., 0., 0.
    for profile in profiles.values():
        skins = [[_skin_point(frame, point) for point in profile] for frame in frames]
        for i, fraction in enumerate(fractions[1:-1], 1):
            surface_chord = max(surface_chord, max(math.dist(p, add(mul(a, 1-fraction), mul(b, fraction)))
                              for p, a, b in zip(skins[i], skins[0], skins[-1])))
        for j, first in enumerate(profile):
            k = (j+1) % len(profile)
            last = profile[k]
            h0, b0 = first
            h1, b1 = last
            dh, db = h1-h0, b1-b0
            alpha = max(0., min(1., -(h0*dh+b0*db)/max(1e-30, dh*dh+db*db)))
            # Do not spend the outward allowance on coarser contact facets.
            free_gap = max(0., math.hypot(h0+alpha*dh, b0+alpha*db)-radius-CONTACT_SKIN_ALLOWANCE_M)
            allowed = .00003+.1*free_gap
            a, b, c, d = skins[0][j], skins[0][k], skins[-1][k], skins[-1][j]
            for index, u in enumerate(fractions[1:-1], 1):
                for v in (.25, .5, .75):
                    actual = _skin_point(frames[index], (h0+v*dh, b0+v*db))
                    if u <= v:
                        expected = add(add(mul(a, 1-v), mul(b, v-u)), mul(c, u))
                        normal = cross(add(b, mul(a, -1)), add(c, mul(a, -1)))
                    else:
                        expected = add(add(mul(a, 1-u), mul(c, v)), mul(d, u-v))
                        normal = cross(add(c, mul(a, -1)), add(d, mul(a, -1)))
                    error = abs(dot(add(actual, mul(expected, -1)), normal))/max(1e-30, norm(normal))
                    plane_ratio = max(plane_ratio, error/allowed)
                    if free_gap < .0001:
                        contact_plane_error = max(contact_plane_error, error)
    return arc_bound, chord_bound, angle, surface_chord, contact_plane_error, plane_ratio


def _adaptive_skin_stations(path, profiles, radius):
    """World-distance, frame-turn and faceted-surface refinement; no time input."""
    end = path.end+1.65/norm(path.at(path.end)[1])
    knots = [0., *path.ends, end]
    pending = [(a, b, 0) for a, b in reversed(list(zip(knots, knots[1:])))]
    stations = [0.]
    maxima = [0.]*6
    while pending:
        lo, hi, depth = pending.pop()
        errors = _station_errors(path, lo, hi, profiles, radius)
        accepted = (errors[0] <= .025 and errors[1] <= .00002 and errors[2] <= .01
                    and errors[3] <= .000025 and errors[5] <= 1.)
        if accepted:
            stations.append(hi)
            maxima = [max(a, b) for a, b in zip(maxima, errors)]
        else:
            if depth >= 22 or len(pending)+len(stations) > 30000:
                raise ValueError('skin tessellation exceeded its explicit resource bound')
            middle = (lo+hi)/2
            pending.extend(((middle, hi, depth+1), (lo, middle, depth+1)))
    return stations, {'version': 'adaptive-contact-skin-3', 'station_count': len(stations),
                      'contact_skin_outward_allowance_m': CONTACT_SKIN_ALLOWANCE_M,
                      'independent_surface_intrusion_limit_m': .0002,
                      'max_station_arc_bound_m': maxima[0],
                      'max_center_chord_bound_m': maxima[1],
                      'max_quarter_interval_frame_turn_rad': maxima[2],
                      'max_observed_surface_chord_error_m': maxima[3],
                      'max_observed_contact_triangle_plane_error_m': maxima[4],
                      'max_clearance_scaled_plane_error_ratio': maxima[5]}


def _loft_skin(path, stations, profile, identifier, material):
    vertices = [list(_skin_point(path.frame(u), point)) for u in stations for point in profile]
    width = len(profile)
    faces = []
    for i in range(len(stations)-1):
        for j in range(width):
            k = (j+1) % width
            a, b, c, d = i*width+j, i*width+k, (i+1)*width+k, (i+1)*width+j
            faces.extend(([a, b, c], [a, c, d]))
    faces.extend(_triangle_faces([list(reversed(range(width))),
                                 list(range(len(vertices)-width, len(vertices)))]))
    return _mesh(identifier, vertices, faces, material)


def _frame_box(identifier, frame, tangent_limits, normal_limits, lateral_limits, material):
    p, t, n, b, _, _, _ = frame
    vertices = [list(add(add(add(p, mul(t, a)), mul(n, h)), mul(b, lateral)))
                for h in normal_limits for lateral in lateral_limits for a in tangent_limits]
    faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1],
             [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return _mesh(identifier, vertices, _triangle_faces(faces), material)


_legacy_channel = _channel


def _channel(path, identifier, *, radius=RADIUS, width=.72, samples=500,
             side_half_width=RADIUS, capture=False):
    """Explicit facets and outward supports; mechanics and their clock are unchanged."""
    profiles = _skin_profiles(radius, width, side_half_width, capture)
    stations, proof = _adaptive_skin_stations(path, profiles, radius)
    geometry = [_loft_skin(path, stations, profile, identifier+'-'+name,
                           'track' if name == 'floor' else 'steel' if name == 'capture-rail' else 'brass')
                for name, profile in profiles.items()]
    geometry[0]['tessellation'] = {**proof, 'centerline_parameters': stations}
    # Keep the previously checked grounded supports/backstop. Their source poses
    # are independent of the adaptive station indexing.
    for item in _legacy_channel(path, identifier, radius=radius, width=width,
                                samples=samples, side_half_width=side_half_width, capture=False):
        if '-support-' in item['id'] or item['id'].endswith('-backstop'):
            if item['shape'] == 'mesh':
                item['faces'] = _triangle_faces(item['faces'])
            geometry.append(item)
    arc = [0.]
    for a, b in zip(stations, stations[1:]):
        arc.append(arc[-1]+math.dist(path.at(a)[0], path.at(b)[0]))
    next_support = 0.
    for index, distance in enumerate(arc):
        if distance+1e-12 < next_support:
            continue
        next_support += .9
        frame = path.frame(stations[index])
        top = radius+CONTACT_SKIN_ALLOWANCE_M+.05 if capture else .15
        for label, sign in (('left', -1), ('right', 1)):
            lateral = sorted((sign*(side_half_width+CONTACT_SKIN_ALLOWANCE_M+.024),
                              sign*(side_half_width+CONTACT_SKIN_ALLOWANCE_M+.052)))
            geometry.append(_frame_box(f'{identifier}-{label}-upright-{index}', frame,
                                       (-.009, .009), (-radius-.03, top), lateral, 'steel'))
            foot = sorted((sign*max(0., side_half_width-.04), sign*(side_half_width+.052)))
            geometry.append(_frame_box(f'{identifier}-{label}-rail-foot-{index}', frame,
                                       (-.014, .014), (-radius-.04, -radius-.005), foot, 'steel'))
        if capture:
            geometry.append(_frame_box(f'{identifier}-capture-brace-{index}', frame,
                                       (-.014, .014), (radius+CONTACT_SKIN_ALLOWANCE_M+.025,
                                                       radius+CONTACT_SKIN_ALLOWANCE_M+.05),
                                       (-side_half_width-.052, side_half_width+.052), 'steel'))
    return geometry


def _align_x(t):
    axis = cross((1., 0., 0.), t)
    q = (*axis, 1+t[0])
    return tuple(v/norm(q) for v in q) if norm(q) > 1e-10 else (0., 0., 1., 0.)


def _receiver(path, identifier, rows, half_width=.18):
    p, t, _, _, _, _, _ = path.frame(path.end)
    q = list(_align_x(t))
    actors = [{'id': identifier+'-plunger', 'shape': 'box',
               'half_extents_m': [.025, half_width, .14], 'material': 'steel', 'mass_kg': 0.,
               'mechanics': 'Unilateral massless spring/dashpot plunger; passive retraction, zero tensile force.'},
              {'id': identifier+'-coil', 'shape': 'coil',
               'half_extents_m': [.5, min(.07, half_width*.7), min(.07, half_width*.7)], 'material': 'gold',
               'mass_kg': 0., 'deformable': True}]
    timeline = {a['id']: [] for a in actors}
    for row in rows:
        c = row['dock_compression_m']
        speed = row['plunger_speed_m_s']
        front, back = RADIUS+.05+c, 1.54
        if front >= back:
            raise ValueError('receiver stroke exhausted')
        for suffix, center, scale, velocity in (
                ('-plunger', RADIUS+.025+c, [1., 1., 1.], speed),
                ('-coil', (front+back)/2, [back-front, 1., 1.], speed/2)):
            timeline[identifier+suffix].append({
                'position_m': list(add(p, mul(t, center))), 'quaternion_xyzw': q,
                'scale': scale, 'velocity_m_s': list(mul(t, velocity)),
                'tick': row['tick'], 'time_s': row['time_s']})
    return actors, timeline


def _validation(rows, radius):
    moving = [row for row in rows if abs(row['speed_m_s']) > .01]
    return {'max_energy_residual_J': max(abs(row['energy_residual_J']) for row in rows),
            'min_floor_normal_N': min(row['floor_normal_N'] for row in rows),
            'max_capture_rail_normal_N': max(0., -min(row['floor_normal_N'] for row in rows)),
            'max_reaction_N': max(norm(row['reaction_N']) for row in rows),
            'max_guide_work_W': max(abs(row['reaction_work_W']) for row in rows),
            'max_required_static_friction_coefficient': max(abs(row['static_friction_N'])/max(1e-12, row['floor_normal_N']) for row in rows),
            'max_output_displacement_m': max(math.dist(a['position_m'], b['position_m']) for a, b in zip(rows, rows[1:])),
            'max_output_displacement_over_radius': max(math.dist(a['position_m'], b['position_m'])/radius for a, b in zip(rows, rows[1:])),
            'dissipated_energy_J': rows[-1]['dissipated_energy_J'],
            'source_energy_J': rows[0]['energy_J'],
            'final_mechanical_energy_J': rows[-1]['energy_J'],
            'min_receiver_force_N': min(row['receiver_force_N'] for row in rows),
            'min_receiver_gap_m': min(row['receiver_gap_m'] for row in rows),
            'max_receiver_compression_m': max(row['dock_compression_m'] for row in rows),
            'receiver_contact_episodes': sum(row['receiver_contact'] and
                (i == 0 or not rows[i-1]['receiver_contact']) for i, row in enumerate(rows)),
            'final_speed_m_s': rows[-1]['speed_m_s'],
            'last_motion_s': moving[-1]['time_s'] if moving else 0.,
            'dock_compression_m': rows[-1]['dock_compression_m']}


def _recoil_events(rows, actor_id):
    return [{'time_s': b['time_s'], 'type': 'receiver-recoil', 'actor_id': actor_id,
             'position_m': b['position_m'], 'causal': True}
            for a, b in zip(rows, rows[1:])
            if a['dock_compression_m'] != 0 and a['speed_m_s']*b['speed_m_s'] < 0
            and abs(a['dock_compression_m']-b['dock_compression_m']) > 1e-7]


def build_direction(identifier, hz=240, substeps=8):
    """Return the renderer packet at exact ticks 0..30*hz (inclusive)."""
    identifier = str(identifier).zfill(2)
    if identifier not in {'06', '08'}:
        raise ValueError('rolling backend owns directions 06 and 08')
    actors, geometry, timelines, events, validations = [], [], {}, [], {}
    if identifier == '06':
        # Finite torus: I_axis/m = major_radius² + 3/4 tube_radius².
        tube = .025
        hoop_k = ((RADIUS-tube)**2+.75*tube**2)/RADIUS**2
        specs = [('sphere', .4, -1.1, 0, 6.0), ('cylinder', .5, 0., 1, 6.3),
                 ('hoop', hoop_k, 1.1, 2, 6.6)]
        for name, inertia, y, profile, length in specs:
            path = ramp_path(length=length, y=y, profile=profile)
            def resistance(u):
                return .3*max(0., min(1., u-1))
            rows = simulate(path, inertia_ratio=inertia, drag=resistance, hz=hz,
                            substeps=substeps, dock_k=8., dock_c=1.3)
            actors.append({'id': name, 'shape': name, 'radius_m': RADIUS, 'length_m': .3,
                           'tube_radius_m': tube, 'mass_kg': 1., 'inertia_ratio': inertia,
                           'material': {'sphere': 'coral', 'cylinder': 'blue', 'hoop': 'gold'}[name]})
            timelines[name] = rows
            half_width = RADIUS if name == 'sphere' else (.15 if name == 'cylinder' else tube)
            geometry.extend(_channel(path, name, samples=300, side_half_width=half_width))
            receiver_actors, receiver_states = _receiver(path, name, rows, half_width*.8)
            actors.extend(receiver_actors)
            timelines.update(receiver_states)
            validations[name] = _validation(rows, RADIUS)
            events.extend(_recoil_events(rows, name))
            for fraction, kind in ((.16, 'equal-slope-exit'), (.4, 'profile-checkpoint'),
                                   (.7, 'lower-checkpoint'), (1., 'receiver-contact')):
                threshold = 1. if kind == 'equal-slope-exit' else path.end*fraction
                row = next((r for r in rows if r['parameter'] >= threshold), None)
                if row:
                    events.append({'time_s': row['time_s'], 'type': kind, 'actor_id': name,
                                   'position_m': row['position_m'], 'causal': True})
        title = 'Three Ways Down'
        assumptions = ['Planar rolling: fixed world Y axles; no invisible steering.',
                       'Unit masses; exact solid sphere/cylinder and finite-torus axial inertias.',
                       'Initial 1m low-loss equal slope; later viscoelastic torque rises to −0.3*r*v N m; static coefficient 0.8.',
                       'Unilateral massless receiver: k=8 N/m, c=1.3 N s/m; separation, passive retraction and recontacts.',
                       'Race routes use different planar profiles; crossing routes/finish flag become electrical checkpoint lamps.']
        camera = {'position': [9., -12., 9.], 'look_at': [0., 0., 1.4], 'ortho_scale': 9.3}
    else:
        path = spiral_path()
        rows = simulate(path, inertia_ratio=0., hz=hz, substeps=substeps, dock_k=32., dock_c=5.)
        actors.append({'id': 'bead', 'shape': 'sphere', 'radius_m': RADIUS,
                       'mass_kg': 1., 'inertia_ratio': .4, 'effective_rolling_inertia_ratio': 0.,
                       'material': 'glow', 'zero_spin': True,
                       'mechanics': 'Polished frictionless sliding bead; zero initial spin, no applied torque.'})
        timelines['bead'] = rows
        geometry.extend(_channel(path, 'observatory', samples=900, capture=True, width=.5))
        geometry.extend(_orb())
        receiver_actors, receiver_states = _receiver(path, 'observatory', rows)
        actors.extend(receiver_actors)
        timelines.update(receiver_states)
        validations['bead'] = _validation(rows, RADIUS)
        events.extend(_recoil_events(rows, 'bead'))
        for boundary, kind in zip(path.ends, ('outer-spiral-complete', 'crossover-complete',
                                             'lower-counterspiral-complete', 'nest-chute-entry',
                                             'receiver-contact')):
            row = next((r for r in rows if r['parameter'] >= boundary), None)
            if row:
                events.append({'time_s': row['time_s'], 'type': kind, 'actor_id': 'bead',
                               'position_m': row['position_m'], 'causal': True})
        title = 'Spiral Observatory'
        assumptions = ['Polished sliding bead, zero spin: no claim of 3D no-slip rolling.',
                       'Frictionless ideal groove reactions pass through bead center and do zero work; visible upper rail supplies downward reaction.',
                       'Two opposite spirals joined by C2 descending crossover and receiver chute.',
                       'Short freefall and off-center bowl become supported C2 guide segments.',
                       'Unilateral massless receiver plunger: k=32 N/m, c=5 N s/m; passive retraction, all energy sink recorded.']
        camera = {'position': [8., -11., 9.], 'look_at': [0., 0., 1.8], 'ortho_scale': 8.8}
    states = [{'tick': tick, 'time_s': tick/hz,
               'objects': {name: rows[tick] for name, rows in timelines.items()}}
              for tick in range(30*hz+1)]
    geometry.append({'id': 'grounded-base', 'shape': 'box', 'position_m': [1., 0., -.1],
                     'half_extents_m': [4.6, 3.7, .1], 'material': 'floor'})
    return {'id': identifier, 'title': title, 'duration_s': 30., 'hz': hz,
            'backend': 'analytic-constrained-guide-v1', 'seed': 42,
            'actors': actors, 'geometry': geometry, 'states': states,
            'events': sorted(events, key=lambda e: (e['time_s'], e['actor_id'], e['type'])),
            'validation': {'actors': validations, 'assumptions': assumptions,
                           'substeps': substeps, 'gravity_m_s2': [0., 0., -G],
                           'human_review': 'PENDING', 'evaluated_blender_replay': 'NOT_RUN'},
            'camera': camera}
