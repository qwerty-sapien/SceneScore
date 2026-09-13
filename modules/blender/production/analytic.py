"""SI mechanics for one unit-mass solid sphere against fixed oriented boxes.

This is an analytic-segment/impulse model, not Bullet output. Each internal step
uses constant-gravity free flight and bisects newly crossed surfaces to apply an
impact at contact. Contacts in output rows cover the preceding output interval,
so an impact is not lost between integer ticks. No moving obstacles are supported.

Friction is a capped Coulomb contact impulse with I=2/5 mr². Supported rolling
resistance is an opposing angular impulse, coefficient 0.02 by default; it removes
energy and never reverses spin. Substep-resolution settling removes only a tiny
outward speed <= |g|*dt after an inelastic impact. Deep overlap and unresolved
multiple-contact steps fail explicitly rather than creating a teleport or hold.
"""
import math

MODEL_VERSION = 'fixed-obb-sphere-mechanics-1'
GRAVITY_M_S2 = (0., 0., -9.81)


def _add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _mul(a, s):
    return tuple(x*s for x in a)


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _norm(a):
    return math.sqrt(_dot(a, a))


def _quat_mul(a, b):
    av, bv = a[:3], b[:3]
    return (*_add(_add(_mul(bv, a[3]), _mul(av, b[3])), _cross(av, bv)), a[3]*b[3]-_dot(av, bv))


def _unit_quat(q):
    length = _norm(q)
    if not math.isfinite(length) or length <= 1e-12:
        raise ValueError('quaternion must be finite and nonzero')
    return tuple(x/length for x in q)


def _rotate(q, v):
    t = _mul(_cross(q[:3], v), 2)
    return _add(v, _add(_mul(t, q[3]), _cross(q[:3], t)))


def _orientation(q, omega, dt):
    speed = _norm(omega)
    if speed <= 1e-15:
        return q
    half_angle = speed*dt/2
    delta = (*_mul(omega, math.sin(half_angle)/speed), math.cos(half_angle))
    return _unit_quat(_quat_mul(delta, q))


def _sphere_box(position, radius, box):
    """Signed gap and outward world normal, including contained sphere centres."""
    q = box['quaternion_xyzw']
    local = _rotate((-q[0], -q[1], -q[2], q[3]), _sub(position, box['position_m']))
    half = box['half_extents_m']
    closest = tuple(max(-h, min(h, x)) for x, h in zip(local, half))
    delta = _sub(local, closest)
    distance = _norm(delta)
    if distance > 1e-15:
        return distance-radius, _rotate(q, _mul(delta, 1/distance))
    axis = min(range(3), key=lambda i: half[i]-abs(local[i]))
    normal = [0., 0., 0.]
    normal[axis] = 1. if local[axis] >= 0 else -1.
    return -(radius+half[axis]-abs(local[axis])), _rotate(q, normal)


def _friction_impulse(velocity, omega, normal, radius, normal_impulse, coefficient):
    arm = _mul(normal, -radius)
    contact = _add(velocity, _cross(omega, arm))
    tangent = _sub(contact, _mul(normal, _dot(contact, normal)))
    speed = _norm(tangent)
    if speed <= 1e-15 or normal_impulse <= 0 or coefficient <= 0:
        return velocity, omega
    # Unit mass, I = 2/5 r²: inverse effective tangential mass = 1 + 5/2.
    magnitude = min(speed/3.5, coefficient*normal_impulse)
    impulse = _mul(tangent, -magnitude/speed)
    return _add(velocity, impulse), _add(omega, _mul(_cross(arm, impulse), 2.5/radius**2))


def _advance(position, velocity, omega, orientation, dt, support, radius, friction, rolling_resistance):
    acceleration = GRAVITY_M_S2
    next_velocity = _add(velocity, _mul(acceleration, dt))
    next_omega = omega
    if support is not None:
        box, normal = support
        normal_force = max(0., -_dot(GRAVITY_M_S2, normal))
        acceleration = _sub(GRAVITY_M_S2, _mul(normal, _dot(GRAVITY_M_S2, normal)))
        next_velocity = _add(velocity, _mul(acceleration, dt))
        next_velocity, next_omega = _friction_impulse(
            next_velocity, omega, normal, radius, normal_force*dt,
            friction*box['friction'])
        rolling = _sub(next_omega, _mul(normal, _dot(next_omega, normal)))
        speed = _norm(rolling)
        if speed > 1e-15:
            reduction = min(speed, 2.5*rolling_resistance*normal_force*dt/radius)
            next_omega = _sub(next_omega, _mul(rolling, reduction/speed))
    next_position = _add(position, _mul(_add(velocity, next_velocity), dt/2))
    next_orientation = _orientation(orientation, _mul(_add(omega, next_omega), .5), dt)
    return next_position, next_velocity, next_omega, next_orientation


def _vector(value, name, count=3):
    result = tuple(float(x) for x in value)
    if len(result) != count or not all(math.isfinite(x) for x in result):
        raise ValueError(name+' must contain finite values of the correct length')
    return result


def simulate_sphere(initial_position_m, initial_velocity_m_s, radius_m, obstacles,
                    duration_s, hz=240, restitution=.55, friction=.35, substeps=32,
                    rolling_resistance=.02):
    """Return integer-tick SI states, including both t=0 and the exact endpoint.

    duration_s*hz must be integral. Obstacle restitution/friction combine by
    multiplication with the sphere's coefficients. Obstacles are immutable fixed
    solids; dynamic/driven modes are rejected. A displacement bound rejects inputs
    too fast for the chosen constant substep rate instead of allowing tunnelling.
    """
    position = _vector(initial_position_m, 'position')
    velocity = _vector(initial_velocity_m_s, 'velocity')
    radius = float(radius_m)
    duration = float(duration_s)
    if not isinstance(hz, int) or not isinstance(substeps, int) or hz < 1 or not 1 <= substeps <= 256:
        raise ValueError('positive integer hz and substeps 1..256 required')
    if not all(math.isfinite(x) for x in (radius, duration, restitution, friction, rolling_resistance)):
        raise ValueError('finite physical parameters required')
    if radius <= 0 or duration <= 0 or not 0 <= restitution <= 1 or not 0 <= friction <= 1 or not 0 <= rolling_resistance <= 1:
        raise ValueError('positive radius/duration and coefficients 0..1 required')
    count = round(duration*hz)
    if count < 1 or abs(count-duration*hz) > 1e-8 or count*substeps > 2_000_000:
        raise ValueError('duration must have an integral tick count within the work budget')
    boxes = []
    for item in obstacles:
        if item.get('mode', 'passive') not in ('fixed', 'passive'):
            raise ValueError('only fixed obstacles are supported')
        box = dict(item)
        box['position_m'] = _vector(item['position_m'], 'obstacle position')
        box['half_extents_m'] = _vector(item['half_extents_m'], 'obstacle half extents')
        box['quaternion_xyzw'] = _unit_quat(_vector(item['quaternion_xyzw'], 'obstacle quaternion', 4))
        if min(box['half_extents_m']) <= 0:
            raise ValueError('obstacle half extents must be positive')
        for key in ('friction', 'restitution'):
            box[key] = float(item[key])
            if not math.isfinite(box[key]) or not 0 <= box[key] <= 1:
                raise ValueError('obstacle coefficient must be 0..1')
        boxes.append(box)
    if len(boxes) > 128:
        raise ValueError('at most 128 fixed obstacles supported')
    dt = 1/(hz*substeps)
    slop = max(1e-10, radius*1e-8)
    max_correction = max(1e-8, radius*1e-5)
    settling_speed = _norm(GRAVITY_M_S2)*dt
    omega, orientation = (0., 0., 0.), (0., 0., 0., 1.)

    def snapshot(tick, contacts):
        return {'tick': tick, 'time_s': tick/hz, 'position_m': list(position),
                'velocity_m_s': list(velocity), 'quaternion_xyzw': list(orientation),
                'angular_velocity_world_rad_s': list(omega), 'contacts': sorted(contacts)}

    initial_contacts = set()
    for i, box in enumerate(boxes):
        gap, _ = _sphere_box(position, radius, box)
        if gap < -max_correction:
            raise ValueError('initial sphere containment/overlap exceeds bounded correction')
        if gap <= slop:
            initial_contacts.add(i)
    result = [snapshot(0, initial_contacts)]
    touched = set()
    for step in range(1, count*substeps+1):
        if _norm(velocity)*dt + .5*_norm(GRAVITY_M_S2)*dt**2 > radius*.25:
            raise ValueError('displacement exceeds the bounded collision step; increase substeps')
        remaining = dt
        for _ in range(12):
            if remaining <= dt*1e-10:
                break
            support = None
            for i, box in enumerate(boxes):
                gap, normal = _sphere_box(position, radius, box)
                if gap < -max_correction:
                    raise RuntimeError('contact penetration exceeds bounded correction')
                if gap < 0:
                    position = _add(position, _mul(normal, -gap))
                vn = _dot(velocity, normal)
                if gap <= slop:
                    touched.add(i)
                    if abs(vn) <= settling_speed and _dot(GRAVITY_M_S2, normal) < -1e-8:
                        # A true elastic rebound is retained. At zero velocity an
                        # initially supported sphere obeys the resting constraint.
                        if vn <= 1e-10 or restitution*box['restitution'] < 1:
                            if support is None or _dot(GRAVITY_M_S2, normal) < _dot(GRAVITY_M_S2, support[1]):
                                support = (box, normal)
            if support is not None:
                normal = support[1]
                velocity = _sub(velocity, _mul(normal, _dot(velocity, normal)))
            trial = _advance(position, velocity, omega, orientation, remaining,
                             support, radius, friction, rolling_resistance)
            hit = None
            earliest = remaining
            for i, box in enumerate(boxes):
                end_gap, _ = _sphere_box(trial[0], radius, box)
                if end_gap >= -slop:
                    continue
                start_gap, _ = _sphere_box(position, radius, box)
                lo, hi = 0., remaining
                if start_gap <= slop:
                    hi = 0.
                else:
                    for _ in range(35):
                        mid = (lo+hi)/2
                        p = _advance(position, velocity, omega, orientation, mid,
                                     support, radius, friction, rolling_resistance)[0]
                        if _sphere_box(p, radius, box)[0] > 0:
                            lo = mid
                        else:
                            hi = mid
                if hi <= earliest:
                    earliest, hit = hi, i
            if hit is None:
                position, velocity, omega, orientation = trial
                remaining = 0.
                break
            position, velocity, omega, orientation = _advance(
                position, velocity, omega, orientation, earliest, support, radius, friction, rolling_resistance)
            box = boxes[hit]
            gap, normal = _sphere_box(position, radius, box)
            if gap < -max_correction:
                raise RuntimeError('impact penetration exceeds bounded correction')
            if gap < 0:
                position = _add(position, _mul(normal, -gap))
            incoming = _dot(velocity, normal)
            normal_impulse = -(1+restitution*box['restitution'])*min(0., incoming)
            velocity = _add(velocity, _mul(normal, normal_impulse))
            velocity, omega = _friction_impulse(velocity, omega, normal, radius,
                                                normal_impulse, friction*box['friction'])
            touched.add(hit)
            remaining -= earliest
        else:
            raise RuntimeError('multiple contact resolution exceeded bounded iterations')
        if step % substeps == 0:
            result.append(snapshot(step//substeps, touched))
            touched = set()
    return result
