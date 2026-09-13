"""Direction 18: SI planar disc/finite-rail/hinge mechanics, without Blender.

The support is one shallow plane. A massless spring follower launches a sliding
disc; Coulomb impulses exchange momentum with finite boxes and a massive hinged
fin. A physically struck release peg unlocks a counterweighted vertical-axis
door. The latter has one rotational degree of freedom and a cable of constant
drum radius. These are deliberately scoped constrained mechanics, not a general
3D rigid-body solver. All visible actor transforms come from integrated state.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

VERSION = 'planar-puck-hinge-mechanics-1'


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _mul(a, scalar):
    return (a[0] * scalar, a[1] * scalar)


def _norm(a):
    return math.hypot(*a)


def _perp(a):
    return (-a[1], a[0])


def _quat(angle):
    return [0.0, 0.0, math.sin(angle / 2), math.cos(angle / 2)]


@dataclass(frozen=True)
class Settings:
    """SI values; length_unit_m only changes calculation units, not the design."""

    radius_m: float = 0.24
    mass_kg: float = 0.40
    gravity_m_s2: float = 9.81
    slope: float = 0.0008
    friction: float = 0.0032
    spring_n_m: float = 0.34
    compression_m: float = 0.9
    restitution: float = 0.82
    contact_friction: float = 0.05
    launch_enabled: bool = True
    length_unit_m: float = 1.0


def circle_box(point, radius, centre, half, angle=0.0):
    """Signed gap and outward normal for a circle and a finite 2D rectangle."""
    c, s = math.cos(angle), math.sin(angle)
    d = _sub(point, centre)
    p = (c * d[0] + s * d[1], -s * d[0] + c * d[1])
    q = (max(-half[0], min(half[0], p[0])), max(-half[1], min(half[1], p[1])))
    delta = _sub(p, q)
    length = _norm(delta)
    if length > 1e-15:
        n = _mul(delta, 1 / length)
        gap = length - radius
    else:
        axis = min(range(2), key=lambda i: half[i] - abs(p[i]))
        n = (math.copysign(1, p[0]), 0.0) if axis == 0 else (0.0, math.copysign(1, p[1]))
        gap = -(radius + half[axis] - abs(p[axis]))
    return gap, (c * n[0] - s * n[1], s * n[0] + c * n[1])


def contact_impulse(velocity, spin, normal, radius, mass, restitution,
                    friction=0.0, arm=(0.0, 0.0), hinge_omega=0.0, hinge_inertia=math.inf):
    """Disc/hinge normal plus capped Coulomb tangential impulse.

    Returns new disc velocity/spin, hinge angular velocity and world impulse.
    The same opposite impulse acts at ``arm`` on the hinge. An infinite hinge
    inertia is a fixed rail. This function is independently fixture tested.
    """
    inertia = mass * radius * radius / 2
    contact_velocity = _sub(velocity, _mul(_perp(arm), hinge_omega))
    vn = _dot(contact_velocity, normal)
    if vn >= 0:
        return velocity, spin, hinge_omega, (0.0, 0.0)
    effective = 1 / mass + _cross(arm, normal) ** 2 / hinge_inertia
    jn = -(1 + restitution) * vn / effective
    impulse = _mul(normal, jn)
    velocity = _add(velocity, _mul(impulse, 1 / mass))
    hinge_omega -= _cross(arm, impulse) / hinge_inertia
    tangent = _perp(normal)
    disc_arm = _mul(normal, -radius)
    relative = _sub(_add(velocity, _mul(_perp(disc_arm), spin)),
                    _mul(_perp(arm), hinge_omega))
    vt = _dot(relative, tangent)
    denom = 1 / mass + radius * radius / inertia + _cross(arm, tangent) ** 2 / hinge_inertia
    jt = max(-friction * jn, min(friction * jn, -vt / denom))
    tangential = _mul(tangent, jt)
    velocity = _add(velocity, _mul(tangential, 1 / mass))
    spin += _cross(disc_arm, tangential) / inertia
    hinge_omega -= _cross(arm, tangential) / hinge_inertia
    return velocity, spin, hinge_omega, _add(impulse, tangential)


def _box(id_, centre, half, angle=0.0, material='wood', **extra):
    return dict(id=id_, shape='box', centre=centre, half=half, angle=angle,
                material=material, **extra)


def _layout():
    return [
        _box('bank-rail', (0.0, 0.97), (4.4, 0.08)),
        _box('far-fin', (2.65, -0.38), (0.62, 0.045), -0.17, 'glass'),
        _box('near-fin', (2.65, -1.08), (0.62, 0.045), -0.17, 'glass'),
        _box('release-peg', (3.68, -1.15), (0.3, 0.035), 0.0, 'brass', latch=True),
        _box('groove-upper', (4.80, -0.48), (0.75, 0.06), -0.18),
        _box('groove-lower', (4.80, -2.10), (0.75, 0.06), -0.18),
        _box('dock-stop', (5.22, -1.0), (0.10, 0.57), 0.0, 'cork', compliant=True),
        _box('left-boundary', (-5.80, -0.7), (0.08, 3.3)),
        _box('bottom-boundary', (0.0, -3.90), (5.8, 0.08)),
    ]


def box_separation(a, b):
    """Separating-axis lower bound on clearance between two finite rectangles."""
    axes = [(math.cos(box['angle']), math.sin(box['angle'])) for box in (a, b)]
    axes += [_perp(axis) for axis in axes[:]]
    delta = _sub(a['centre'], b['centre'])
    margins = []
    for axis in axes:
        radii = []
        for box in (a, b):
            local_x = (math.cos(box['angle']), math.sin(box['angle']))
            radii.append(abs(_dot(axis, local_x)) * box['half'][0] +
                         abs(_dot(axis, _perp(local_x))) * box['half'][1])
        margins.append(abs(_dot(delta, axis)) - sum(radii))
    return max(margins)


def build_direction(direction='18', *, hz=240, substeps=8, settings=None, duration_s=30.0):
    """Build authoritative 240 Hz transforms plus contact/energy evidence.

    ``length_unit_m`` permits a metre/centimetre arithmetic-equivalence control.
    No wall-clock frame retiming or event-time position assignment occurs.
    """
    if str(direction) != '18':
        raise ValueError('puck backend supports direction 18 only')
    cfg = settings or Settings()
    if (not isinstance(hz, int) or not isinstance(substeps, int) or
            hz < 30 or hz > 480 or substeps < 1 or substeps > 32 or
            not math.isfinite(duration_s) or duration_s <= 0 or duration_s > 30 or
            any(not math.isfinite(value) or value <= 0 for value in
                (cfg.length_unit_m, cfg.mass_kg, cfg.radius_m, cfg.gravity_m_s2,
                 cfg.spring_n_m, cfg.compression_m)) or
            not 0 <= cfg.friction <= 1 or not 0 <= cfg.restitution <= 1 or
            not 0 <= cfg.contact_friction <= 1 or not 0 <= cfg.slope <= 0.01):
        raise ValueError('bounded simulation parameters required')
    # Solve in user-selected length units. Forces/torques are converted into
    # mass*unit/s² and mass*unit²/s²; output is always SI.
    u = cfg.length_unit_m
    scale = 1 / u
    dt = 1 / (hz * substeps)
    g = cfg.gravity_m_s2 * scale
    radius = cfg.radius_m * scale
    mass = cfg.mass_kg
    inertia = mass * radius * radius / 2
    p = (-5.0 * scale, -2.5 * scale)
    start = p
    v = (0.0, 0.0)
    spin = angle = 0.0
    launch_direction = (0.8, 0.6)
    compression0 = cfg.compression_m * scale if cfg.launch_enabled else 0.0
    compression = compression0
    launched = not cfg.launch_enabled
    boxes = _layout()
    for box in boxes:
        box['centre'] = _mul(box['centre'], scale)
        box['half'] = _mul(box['half'], scale)
    fin = dict(id='hinged-fin', pivot=(0.5 * scale, -0.65 * scale),
               length=1.3 * scale, halfwidth=0.055 * scale, mass=0.5,
               theta=-0.15, rest=-0.15, omega=0.0,
               inertia=0.5 * ((1.3 * scale) ** 2 + (0.055 * scale) ** 2) / 3,
               spring=0.035 * scale ** 2, damping=0.035 * scale ** 2)
    door = dict(id='greenhouse-door', pivot=(4.15 * scale, -1.8 * scale),
                length=0.95 * scale, halfwidth=0.055 * scale, mass=0.6,
                theta=math.pi / 2, rest=0.0, omega=0.0,
                inertia=0.6 * ((0.95 * scale) ** 2 + (0.055 * scale) ** 2) / 3 + 0.08 * (0.17 * scale) ** 2,
                spring=0.0, damping=0.18 * scale ** 2)
    latched = True
    events = []
    states = []
    active = set()
    min_gaps = {box['id']: math.inf for box in boxes}
    min_gap_times = {}
    max_penetration = max_step = max_contact_gain = 0.0
    max_fin_omega = max_spin = 0.0
    max_door_omega = 0.0
    swept_clearances = {hinge['id']: math.inf for hinge in (fin, door)}
    impulse_loss = friction_loss = hinge_damping_loss = stop_loss = 0.0
    external_work = 0.0
    stop_compression = max_stop_compression = 0.0
    stop_stiffness, stop_damping = 18.0, 1.8
    energy_rows = []
    latch_time = launch_time = None
    settled_at = None
    low_speed_since = None

    tilt = math.atan(cfg.slope)
    ct, st = math.cos(tilt), math.sin(tilt)
    # A preloaded torsion spring balances the fin's tiny incline gravity torque.
    fin['rest'] = fin['theta'] + (fin['mass'] * g * st * fin['length'] / 2 *
                                math.sin(fin['theta']) / fin['spring'])
    for hinge in (fin, door):
        hinge['initial_theta'] = hinge['theta']

    def world(point, height=0.0):
        return [point[0] * u * ct + height * st, point[1] * u,
                1.1 - point[0] * u * st + height * ct]

    def world_velocity(velocity):
        return [velocity[0] * u * ct, velocity[1] * u, -velocity[0] * u * st]

    def orientation(theta):
        a, b = tilt / 2, theta / 2
        return [math.sin(a) * math.sin(b), math.sin(a) * math.cos(b),
                math.cos(a) * math.sin(b), math.cos(a) * math.cos(b)]

    def energy():
        spring = 0.5 * cfg.spring_n_m * compression ** 2 + 0.5 * stop_stiffness * stop_compression ** 2
        linear = 0.5 * mass * _dot(v, v)
        rotational = 0.5 * inertia * spin ** 2
        for hinge in (fin, door):
            rotational += 0.5 * hinge['inertia'] * hinge['omega'] ** 2
            spring += 0.5 * hinge['spring'] * (hinge['theta'] - hinge['rest']) ** 2
            spring += hinge['mass'] * g * st * hinge['length'] / 2 * (
                math.cos(hinge['initial_theta']) - math.cos(hinge['theta']))
        return (linear + rotational + spring) * u * u

    def state(tick):
        objects = {
            'ceramic-puck': dict(position_m=world(p, 0.07),
                                 quaternion_xyzw=orientation(angle), scale=[1, 1, 1],
                                 velocity_m_s=world_velocity(v)),
        }
        for hinge in (fin, door):
            arm = _mul((math.cos(hinge['theta']), math.sin(hinge['theta'])), hinge['length'] / 2)
            centre = _add(hinge['pivot'], arm)
            velocity = _mul(_perp(arm), hinge['omega'])
            objects[hinge['id']] = dict(
                position_m=world(centre, 0.42),
                quaternion_xyzw=orientation(hinge['theta']), scale=[1, 1, 1],
                velocity_m_s=world_velocity(velocity),
                angular_velocity_rad_s=[st * hinge['omega'], 0, ct * hinge['omega']])
        # Massless follower position is constrained by the spring's compression.
        follower = _add(start, _mul(launch_direction, compression0 - compression - radius - 0.08 * scale))
        objects['spring-plunger'] = dict(position_m=world(follower, 0.08),
            quaternion_xyzw=orientation(math.atan2(launch_direction[1], launch_direction[0])), scale=[1, 1, 1],
            velocity_m_s=world_velocity(_mul(launch_direction, _dot(v, launch_direction))) if not launched else [0, 0, 0])
        spring_start = _add(start, _mul(launch_direction, -radius - 0.22 * scale))
        extension = max(0.06 * scale, compression0 - compression + 0.06 * scale)
        spring_centre = _add(spring_start, _mul(launch_direction, extension / 2))
        objects['launch-spring'] = dict(position_m=world(spring_centre, 0.08),
            quaternion_xyzw=orientation(math.atan2(launch_direction[1], launch_direction[0])),
            scale=[extension * u, 1, 1], velocity_m_s=world_velocity(
                _mul(launch_direction, _dot(v, launch_direction) / 2)) if not launched else [0, 0, 0])
        weight_z = 2.05 + 0.17 * (door['theta'] - math.pi / 2)
        objects['counterweight'] = dict(position_m=[4.15, -2.08, weight_z], quaternion_xyzw=[0, 0, 0, 1],
            scale=[1, 1, 1], velocity_m_s=[0, 0, 0.17 * door['omega']])
        objects['dock-stop'] = dict(position_m=world((5.22 * scale + stop_compression / 2, -1.0 * scale), 0.20),
            quaternion_xyzw=orientation(0), scale=[1 - stop_compression * u / 0.20, 1, 1],
            velocity_m_s=world_velocity((v[0] / 2, 0)) if stop_compression else [0, 0, 0])
        return dict(tick=tick, time_s=tick / hz, objects=objects)

    initial_energy = energy() / (u * u)
    states.append(state(0))
    for step in range(1, round(duration_s * hz) * substeps + 1):
        t = step * dt
        old_p = p
        velocity_before_step = v
        compression_before_step = compression
        force = (mass * g * st, 0.0)
        if not launched:
            compression = max(0.0, compression0 - _dot(_sub(p, start), launch_direction))
            force = _add(force, _mul(launch_direction, cfg.spring_n_m * compression))
            if compression <= 0:
                launched = True
                launch_time = t
                events.append(dict(type='spring_release', time_s=t, actors=['ceramic-puck', 'spring-plunger']))
        v = _add(v, _mul(force, dt / mass))
        speed = _norm(v)
        mu = 0.018 if (4.88 * scale <= p[0] <= 5.36 * scale and -1.62 * scale <= p[1] <= -0.38 * scale) else cfg.friction
        # Proximal Coulomb update: static friction may hold but never reverse.
        before_friction = 0.5 * mass * _dot(v, v)
        v = _mul(v, max(0.0, 1 - mu * g * ct * dt / max(speed, 1e-30)))
        friction_loss += before_friction - 0.5 * mass * _dot(v, v)
        before_spin = 0.5 * inertia * spin * spin
        spin *= math.exp(-0.08 * dt)
        friction_loss += before_spin - 0.5 * inertia * spin * spin
        p = _add(p, _mul(_add(velocity_before_step, v), dt / 2))
        if not launched:
            updated_compression = max(0.0, compression0 - _dot(_sub(p, start), launch_direction))
            v = _add(v, _mul(launch_direction,
                cfg.spring_n_m * (updated_compression - compression_before_step) * dt / (2 * mass)))
        angle += spin * dt
        external_work += mass * g * st * (p[0] - old_p[0])
        for hinge in (fin, door):
            if hinge is door and latched:
                continue
            torque = -hinge['spring'] * (hinge['theta'] - hinge['rest'])
            torque -= hinge['mass'] * g * st * hinge['length'] / 2 * math.sin(hinge['theta'])
            if hinge is door:
                torque -= 0.08 * g * 0.17 * scale
                if hinge['theta'] <= 0 and hinge['omega'] <= 0 and torque < 0:
                    continue  # Static angular stop reaction; no fictitious work.
            old_theta = hinge['theta']
            hinge['omega'] += torque / hinge['inertia'] * dt
            pred = hinge['omega']
            hinge['omega'] *= math.exp(-hinge['damping'] / hinge['inertia'] * dt)
            hinge_damping_loss += 0.5 * hinge['inertia'] * (pred ** 2 - hinge['omega'] ** 2)
            hinge['theta'] += hinge['omega'] * dt
            if hinge is door:
                if hinge['theta'] < 0:
                    stop_loss += 0.5 * hinge['inertia'] * hinge['omega'] ** 2
                    hinge['theta'] = 0.0
                    hinge['omega'] = 0.0
                external_work -= 0.08 * g * 0.17 * scale * (hinge['theta'] - old_theta)
        contacts = set()
        obstacles = list(boxes)
        for hinge in (fin, door):
            arm = _mul((math.cos(hinge['theta']), math.sin(hinge['theta'])), hinge['length'] / 2)
            obstacles.append(_box(hinge['id'], _add(hinge['pivot'], arm),
                (hinge['length'] / 2, hinge['halfwidth']), hinge['theta'], hinge=hinge))
        for box in obstacles:
            gap, normal = circle_box(p, radius, box['centre'], box['half'], box['angle'])
            if gap * u < min_gaps.get(box['id'], math.inf):
                min_gaps[box['id']] = gap * u
                min_gap_times[box['id']] = t
            if gap >= 0:
                if box.get('compliant'):
                    stop_compression = 0.0
                continue
            contacts.add(box['id'])
            if box.get('compliant'):
                # Unilateral Kelvin-Voigt facing: the visible face compresses
                # with the puck. Fixed backing remains 20 cm behind the face.
                stop_compression = -gap
                max_stop_compression = max(max_stop_compression, -gap * u)
                vn = _dot(v, normal)
                force_n = max(0.0, stop_stiffness * (-gap) - stop_damping * vn)
                impulse = _mul(normal, force_n * dt)
                v = _add(v, _mul(impulse, 1 / mass))
                stop_loss += max(0.0, -vn * (force_n - stop_stiffness * (-gap)) * dt)
                if box['id'] not in active:
                    events.append(dict(type='compliant_contact', time_s=t,
                        actors=['ceramic-puck', 'dock-stop'], force_n=force_n * u,
                        impulse_n_s=force_n * dt * u))
                continue
            max_penetration = max(max_penetration, -gap * u)
            remainder = 0.0
            old_gap, _ = circle_box(old_p, radius, box['centre'], box['half'], box['angle'])
            if old_gap > 0:
                # Locate the actual surface crossing; in particular do not use
                # a penetrated rounded-corner normal for the release-peg bank.
                end = p
                lo, hi = 0.0, 1.0
                for _ in range(28):
                    fraction = (lo + hi) / 2
                    probe = _add(old_p, _mul(_sub(end, old_p), fraction))
                    probe_gap, _ = circle_box(probe, radius, box['centre'], box['half'], box['angle'])
                    if probe_gap > 0:
                        lo = fraction
                    else:
                        hi = fraction
                p = _add(old_p, _mul(_sub(end, old_p), hi))
                _, normal = circle_box(p, radius, box['centre'], box['half'], box['angle'])
                remainder = (1 - hi) * dt
            else:
                p = _add(p, _mul(normal, -gap))
            hinge = box.get('hinge')
            movable = hinge is not None and (hinge is not door or not latched)
            arm = _sub(_sub(p, _mul(normal, radius)), hinge['pivot']) if hinge else (0.0, 0.0)
            h_omega = hinge['omega'] if movable else 0.0
            h_inertia = hinge['inertia'] if movable else math.inf
            before = 0.5 * mass * _dot(v, v) + 0.5 * inertia * spin ** 2
            if movable:
                before += 0.5 * h_inertia * h_omega ** 2
            v, spin, omega, impulse = contact_impulse(v, spin, normal, radius, mass,
                0.15 if box.get('compliant') else cfg.restitution, cfg.contact_friction,
                arm, h_omega, h_inertia)
            if movable:
                hinge['omega'] = omega
            after = 0.5 * mass * _dot(v, v) + 0.5 * inertia * spin ** 2
            if movable:
                after += 0.5 * h_inertia * omega ** 2
            impulse_loss += before - after
            max_contact_gain = max(max_contact_gain, (after - before) * u ** 2)
            magnitude = _norm(impulse) * u
            if magnitude > 1e-8 and box['id'] not in active:
                events.append(dict(type='contact', time_s=t, actors=['ceramic-puck', box['id']],
                    impulse_n_s=magnitude, impulse_vector_n_s=world_velocity(impulse),
                    point_m=world(_sub(p, _mul(normal, radius)), 0.07),
                    kinetic_energy_loss_j=(before - after) * u ** 2,
                    hinge_omega_before_rad_s=h_omega, hinge_omega_after_rad_s=omega if movable else 0.0))
            if box.get('latch') and latched and magnitude > 0.005:
                latched = False
                latch_time = t
                events.append(dict(type='latch_release', time_s=t, actors=['release-peg', 'greenhouse-door'],
                                   trigger_impulse_n_s=magnitude))
            p = _add(p, _mul(v, remainder))
        active = contacts
        max_step = max(max_step, _norm(_sub(p, old_p)) * u,
                       abs(fin['omega']) * fin['length'] * dt * u,
                       abs(door['omega']) * door['length'] * dt * u)
        max_fin_omega = max(max_fin_omega, abs(fin['omega']))
        max_door_omega = max(max_door_omega, abs(door['omega']))
        max_spin = max(max_spin, abs(spin))
        # Spring energy follows actual follower displacement after the step.
        if not launched:
            compression = max(0.0, compression0 - _dot(_sub(p, start), launch_direction))
        if p[0] > 4.7 * scale and _norm(v) * u < 0.015:
            low_speed_since = t if low_speed_since is None else low_speed_since
            if t - low_speed_since >= 0.75 and settled_at is None:
                settled_at = low_speed_since
                events.append(dict(type='settled', time_s=low_speed_since, actors=['ceramic-puck']))
        else:
            low_speed_since = None
        if step % substeps == 0:
            states.append(state(step // substeps))
            for moving in obstacles[-2:]:
                for fixed in boxes:
                    swept_clearances[moving['id']] = min(swept_clearances[moving['id']],
                        box_separation(moving, fixed) * u)
            mutual = box_separation(obstacles[-1], obstacles[-2]) * u
            for hinge in (fin, door):
                swept_clearances[hinge['id']] = min(swept_clearances[hinge['id']], mutual)
        if step % (hz * substeps) == 0:
            losses = friction_loss + hinge_damping_loss + impulse_loss + stop_loss
            residual = energy() - initial_energy * u ** 2 - external_work * u ** 2 + losses * u ** 2
            energy_rows.append(dict(time_s=t, stored_energy_j=energy(), dissipated_j=losses * u ** 2,
                                    gravity_work_j=external_work * u ** 2, balance_residual_j=residual))

    geometry = []
    for box in boxes:
        if box.get('compliant'):
            continue
        centre = box['centre']
        geometry.append(dict(id=box['id'], shape='box', position_m=world(centre, 0.20),
            quaternion_xyzw=orientation(box['angle']), half_extents_m=[box['half'][0] * u, box['half'][1] * u, 0.20],
            material=box['material'], role='silent_support' if 'boundary' in box['id'] else 'contact_object'))
    geometry.append(dict(id='supporting-table', shape='mesh', position_m=[0, 0, 0], quaternion_xyzw=[0, 0, 0, 1],
        vertices=[world((x * scale, y * scale)) for x, y in [(-5.9, -4), (5.9, -4), (5.9, 2), (-5.9, 2)]],
        faces=[[0, 1, 2, 3]], material='green_felt', role='silent_support'))
    geometry.append(dict(id='roughened-dock', shape='box', position_m=world((5.12 * scale, -1.0 * scale), -0.004),
        quaternion_xyzw=orientation(0), half_extents_m=[0.24, 0.62, 0.004], material='cork', role='silent_support'))
    anchor = _add(start, _mul(launch_direction, -radius - 0.26 * scale))
    geometry.append(dict(id='spring-anchor', shape='box', position_m=world(anchor, 0.14),
        quaternion_xyzw=orientation(math.atan2(0.6, 0.8)), half_extents_m=[0.04, 0.36, 0.14],
        material='wood', role='silent_support', constraint_support=True))
    for hinge in (fin, door):
        bearing_length = 1.45 if hinge is door else 0.95
        geometry.append(dict(id=hinge['id'] + '-bearing', shape='cylinder', radius_m=0.05,
            length_m=bearing_length, position_m=world(hinge['pivot'], bearing_length / 2), quaternion_xyzw=orientation(0),
            material='brass', role='silent_support', constraint_support=True))
    geometry.extend([
        dict(id='door-drum', shape='cylinder', radius_m=0.17, length_m=0.10,
             position_m=world(door['pivot'], 1.37), quaternion_xyzw=orientation(0),
             material='brass', role='silent_support', constraint_support=True),
        dict(id='door-overhead-frame', shape='box', half_extents_m=[0.08, 0.50, 0.06],
             position_m=[4.15, -2.08, 2.55], quaternion_xyzw=[0, 0, 0, 1], material='wood',
             role='silent_support', constraint_support=True),
        dict(id='door-frame-post', shape='box', half_extents_m=[0.08, 0.08, 0.725],
             position_m=[4.15, -2.56, 1.825], quaternion_xyzw=[0, 0, 0, 1], material='wood',
             role='silent_support', constraint_support=True),
        dict(id='latch-link', shape='curve', points=[[3.68, -1.15, 1.42], [3.90, -1.50, 1.46], [4.15, -1.80, 1.46]],
             radius_m=0.012, material='brass', role='silent_support',
             constraint='ideal massless latch linkage, no stored energy or timed force'),
        dict(id='drum-guide-cable', shape='curve', points=[[4.15, -1.97, 2.47], [4.15, -2.08, 2.50]],
             radius_m=0.008, material='steel', role='silent_support',
             constraint='fixed guide to the vertical counterweight cable'),
    ])
    actors = [
        dict(id='ceramic-puck', shape='cylinder', radius_m=cfg.radius_m, length_m=0.14, mass_kg=mass, material='ceramic'),
        dict(id='hinged-fin', shape='box', half_extents_m=[0.65, 0.055, 0.42], mass_kg=fin['mass'], material='glass',
             pivot_m=world(fin['pivot']), hinge_axis=[st, 0, ct]),
        dict(id='greenhouse-door', shape='box', half_extents_m=[0.475, 0.055, 0.42], mass_kg=door['mass'], material='glass',
             pivot_m=world(door['pivot']), hinge_axis=[st, 0, ct]),
        dict(id='spring-plunger', shape='box', half_extents_m=[0.08, 0.32, 0.08], material='brass', mass_kg=0.0,
             constraint='massless follower attached to compressed spring until zero compression'),
        dict(id='launch-spring', shape='coil', deformable=True, half_extents_m=[0.5, 0.04, 0.04], material='steel',
             visual='renderer may decorate as a coil within the supplied mechanical extent'),
        dict(id='dock-stop', shape='box', half_extents_m=[0.10, 0.57, 0.20], material='cork', deformable=True,
             constraint='Kelvin-Voigt facing: k=18 N/m, damping=1.8 Ns/m; fixed backing at intrinsic x=5.32m'),
        dict(id='counterweight', shape='box', half_extents_m=[0.13, 0.13, 0.18], mass_kg=0.08, material='brass',
             constraint='inextensible cable; drum radius 0.17 m; falls as door opens',
             cable={'fixed_endpoint_m': [4.15, -2.08, 2.50], 'actor_attachment_local_m': [0, 0, 0.18],
                    'radius_m': 0.008, 'visual_only_length_change': True}),
    ]
    gap_ids = ['far-fin', 'near-fin']
    for id_ in gap_ids:
        if 0 < min_gaps[id_] < 0.1:
            events.append(dict(type='near_miss', time_s=min_gap_times[id_],
                actors=['ceramic-puck', id_], surface_clearance_m=min_gaps[id_], impulse_n_s=0.0))
    events.sort(key=lambda event: event['time_s'])
    return dict(id='18_billiard_greenhouse', title='The Billiard Greenhouse', direction_id='18', version=VERSION,
        duration_s=duration_s, hz=hz, substeps=substeps, backend=VERSION,
        scope='SI planar sliding disc, finite static boxes, one coupled spring/damped hinge, latch-released counterweighted door',
        actors=actors, geometry=geometry, states=states, events=events,
        camera=dict(position=[10, -13, 14], look_at=[0, -1, 1], ortho_scale=15.0),
        parameters=dict(gravity_m_s2=cfg.gravity_m_s2, table_slope=cfg.slope, coulomb_mu=cfg.friction,
            dock_mu=0.018, spring_n_m=cfg.spring_n_m, compression_m=cfg.compression_m,
            length_unit_m=u, contact_friction=cfg.contact_friction, restitution=cfg.restitution),
        energy_audit=energy_rows,
        validation=dict(max_penetration_m=max_penetration, max_substep_motion_m=max_step,
            no_tunnelling_bound_m=0.009, no_tunnelling_bound_pass=max_step < 0.009,
            max_stop_compression_m=max_stop_compression, max_contact_energy_gain_j=max_contact_gain, max_abs_energy_balance_residual_j=max(
                (abs(row['balance_residual_j']) for row in energy_rows), default=0),
            min_gaps_m=min_gaps, fin_max_angular_speed_rad_s=max_fin_omega, puck_max_spin_rad_s=max_spin,
            hinge_static_clearances_m=swept_clearances,
            hinge_sweep_between_sample_bound_m=max(max_fin_omega * 1.3, max_door_omega * 0.95) / hz,
            near_miss_clearance_m=min(min_gaps[key] for key in gap_ids),
            launch_release_s=launch_time, latch_release_s=latch_time, settled_s=settled_at,
            contact_time_uncertainty_s=dt,
            final_puck_speed_m_s=_norm(v) * u, final_puck_position_m=world(p, 0.07),
            final_door_angle_rad=door['theta'], launch_enabled=cfg.launch_enabled,
            unsupported=['no general 3D motion or arbitrary bodies', 'massless spring follower',
                         'ideal cable/drum and ideal fixed hinge bearings', 'near-horizontal support constraint']),
        approval=None)
