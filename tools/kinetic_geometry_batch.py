"""Produce the nine concrete kinetic-geometry studies requested on 2026-09-13.

This is intentionally a bounded batch producer, not a general scene framework.  It
emits the already-supported directions packet format: explicitly computed SI-style
motion sampled at 240 Hz, then lets the existing Blender directions driver build,
replay, and independently re-evaluate the same poses.  Each study declares its
own mechanics scope in its packet and validation report.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.blender.batch import bounded
from modules.blender.executables import blender_executable


IDS = (
    "01_marble_helix", "02_cube_rebound", "03_triangle_catapult",
    "04_crossing_orbits", "05_tumbling_tetrahedron", "06_rolling_torus_gate",
    "07_capsule_pendulum", "08_cube_cascade", "09_geometric_relay",
)
ARTIFACT_ROOT = ROOT / "artifacts/blender/kinetic_geometry_01"
DRIVER = ROOT / "modules/blender/production/directions/driver.py"
CAMERA_RENDERER = ROOT / "tools/kinetic_geometry_render.py"
FPS, HZ = 30, 240
G = 9.81


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def vadd(a, b): return [a[i] + b[i] for i in range(3)]
def vsub(a, b): return [a[i] - b[i] for i in range(3)]
def vmul(a, scale): return [scale * value for value in a]
def vlen(a): return math.sqrt(sum(value * value for value in a))
def vnorm(a):
    length = vlen(a)
    return [value / length for value in a] if length else [0.0, 0.0, 1.0]
def lerp(a, b, u): return [a[i] + (b[i] - a[i]) * u for i in range(len(a))]
def clamp(value, low=0.0, high=1.0): return max(low, min(high, value))
def smooth(u):
    u = clamp(u)
    return u * u * (3.0 - 2.0 * u)


def q_axis(axis, angle):
    axis = vnorm(axis)
    s = math.sin(angle / 2)
    return [axis[0] * s, axis[1] * s, axis[2] * s, math.cos(angle / 2)]


def q_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bx + az * bw,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz]


def q_align_x(direction):
    """Quaternion taking local +X to direction (stable for the simple guide boxes)."""
    direction = vnorm(direction)
    dot = direction[0]
    if dot < -0.999999:
        return [0.0, 0.0, 1.0, 0.0]
    cross = [0.0, -direction[2], direction[1]]
    q = [cross[0], cross[1], cross[2], 1.0 + dot]
    length = math.sqrt(sum(value * value for value in q))
    return [value / length for value in q]


def ballistic(position, velocity, elapsed):
    return [position[0] + velocity[0] * elapsed,
            position[1] + velocity[1] * elapsed,
            position[2] + velocity[2] * elapsed - .5 * G * elapsed * elapsed]


def ballistic_velocity(velocity, elapsed):
    return [velocity[0], velocity[1], velocity[2] - G * elapsed]


def cubic_path(points, u):
    """A compact Catmull-Rom-like route used only for constrained rolling guides."""
    if len(points) == 2:
        return lerp(points[0], points[1], u)
    scaled = clamp(u) * (len(points) - 1)
    index = min(len(points) - 2, int(scaled))
    local = scaled - index
    return lerp(points[index], points[index + 1], smooth(local))


def pose_static(position, quaternion=(0.0, 0.0, 0.0, 1.0)):
    return lambda _t: (list(position), list(quaternion))


def pose_ballistic(start, velocity, start_t, end_t, *, spin_axis=(0, 1, 0), spin_rate=0.0,
                   resting=None):
    def pose(t):
        elapsed = clamp(t, start_t, end_t) - start_t
        position = ballistic(start, velocity, elapsed)
        if t >= end_t and resting is not None:
            position = list(resting)
        return position, q_axis(spin_axis, spin_rate * elapsed)
    return pose


def route_pose(points, start_t, end_t, *, spin_axis=(0, 1, 0), rotations=0.0,
               pre=None, post=None):
    def pose(t):
        if t <= start_t:
            return list(pre or points[0]), q_axis(spin_axis, 0.0)
        if t >= end_t:
            return list(post or points[-1]), q_axis(spin_axis, rotations * 2 * math.pi)
        u = (t - start_t) / (end_t - start_t)
        return cubic_path(points, u), q_axis(spin_axis, rotations * 2 * math.pi * u)
    return pose


def box(identifier, center, half, material="stone", *, quaternion=None, role="silent_support"):
    return {"id": identifier, "shape": "box", "position_m": list(center),
            "half_extents_m": list(half), "quaternion_xyzw": list(quaternion or (0, 0, 0, 1)),
            "material": material, "role": role}


def beam(identifier, a, b, width=.08, depth=.08, material="steel", role="silent_support"):
    delta = vsub(b, a)
    return box(identifier, lerp(a, b, .5), [vlen(delta) / 2, width, depth], material,
               quaternion=q_align_x(delta), role=role)


def curve(identifier, points, radius=.04, material="brass", role="silent_support"):
    return {"id": identifier, "shape": "curve", "points": [list(point) for point in points],
            "radius_m": radius, "material": material, "role": role}


def guide(identifier, points, *, material="brass", width=.42, rail=.035):
    """Exposed double-rail guide; it intentionally does not hide the travelling body."""
    left = [[point[0], point[1] - width / 2, point[2]] for point in points]
    right = [[point[0], point[1] + width / 2, point[2]] for point in points]
    geometry = [curve(identifier + "-left", left, rail, material),
                curve(identifier + "-right", right, rail, material)]
    for index, point in enumerate(points[::max(1, len(points) // 5)]):
        if point[2] > .22:
            geometry.append(box(identifier + f"-leg-{index}", [point[0], point[1], point[2] / 2],
                                [.045, .045, point[2] / 2], "charcoal"))
    return geometry


def triangle_prism(identifier, material="ceramic"):
    h, d = .48, .32
    return {"id": identifier, "shape": "mesh", "material": material, "role": "hero",
            "vertices": [[-.5, -d, -h / 2], [.5, -d, -h / 2], [0, -d, h],
                         [-.5, d, -h / 2], [.5, d, -h / 2], [0, d, h]],
            "faces": [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]]}


def tetrahedron(identifier, material="teal"):
    return {"id": identifier, "shape": "mesh", "material": material, "role": "hero",
            "vertices": [[.52, .0, -.19], [-.26, .45, -.19], [-.26, -.45, -.19], [0, 0, .62]],
            "faces": [[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]]}


def capsule(identifier, material="ceramic"):
    # A rounded-ended prism provides the capsule silhouette while retaining rigid scale.
    vertices = []
    for y in (-.22, .22):
        for i in range(12):
            angle = 2 * math.pi * i / 12
            vertices.append([.42 * math.cos(angle), y, .24 * math.sin(angle)])
    faces = [[i, (i + 1) % 12, 12 + (i + 1) % 12, 12 + i] for i in range(12)]
    faces += [list(range(12)), list(range(12, 24))]
    return {"id": identifier, "shape": "mesh", "material": material, "role": "hero",
            "vertices": vertices, "faces": faces}


def actor(identifier, shape, pose, *, material="ceramic", role="hero", radius=None,
          half=None, mesh=None, extra=None):
    spec = {"id": identifier, "shape": shape, "material": material, "role": role, "_pose": pose}
    if radius is not None:
        spec["radius_m"] = radius
    if half is not None:
        spec["half_extents_m"] = half
    if mesh:
        spec.update(mesh)
    if extra:
        spec.update(extra)
    return spec


def camera(position, look_at, scale, path=None):
    return {"position": list(position), "look_at": list(look_at), "ortho_scale": scale,
            "path": path or []}


def foundations(bounds=(6.5, 5.0)):
    return [box("studio-floor", [0, 0, -.14], [bounds[0], bounds[1], .14], "floor"),
            box("backdrop", [0, 3.8, 3.8], [bounds[0], .08, 3.9], "charcoal")]


def marble_helix():
    duration = 9.0
    def marble(t):
        if t < .35:
            return [-2.8, 0, 5.6], q_axis((0, 1, 0), 0)
        if t < 5.05:
            u = (t - .35) / 4.7
            theta = .35 + 4.75 * math.pi * (u ** 1.55)
            radius = 2.75 - 1.25 * u
            return [radius * math.cos(theta), radius * math.sin(theta), 5.6 - 3.2 * u], q_axis((0, 1, 0), 17 * math.pi * u)
        if t < 6.0:
            return lerp([1.50, .70, 2.40], [2.3, 1.15, 1.10], smooth((t - 5.05) / .95)), q_axis((0, 1, 0), 18 * math.pi)
        u = clamp((t - 6.0) / 2.55)
        radius = .95 * (1 - u) ** 1.5
        theta = 7.0 * math.pi * u
        return [2.3 + radius * math.cos(theta), 1.15 + radius * math.sin(theta), .72 + .22 * (1 - u)], q_axis((0, 1, 0), 25 * math.pi * u)
    def paddle(t):
        return [1.12, .15, 2.58], q_axis((0, 0, 1), .55 * t)
    spiral = []
    for i in range(70):
        u = i / 69
        theta = .35 + 4.75 * math.pi * u
        radius = 2.75 - 1.25 * u
        spiral.append([radius * math.cos(theta), radius * math.sin(theta), 5.33 - 3.2 * u])
    geometry = foundations() + guide("spiral-guide", spiral, material="brass", width=.62)
    geometry += guide("helix-exit", [[1.5, .7, 2.4], [2.3, 1.15, 1.1]], material="steel", width=.54)
    geometry += [box("paddle-mast", [1.12, .15, 1.3], [.07, .07, 1.3], "copper"),
                 {"id": "receiving-bowl", "shape": "hoop", "radius_m": 1.08, "tube_radius_m": .07,
                  "position_m": [2.3, 1.15, .48], "quaternion_xyzw": [0, 0, 0, 1], "material": "stone", "role": "catcher"}]
    actors = [actor("marble", "sphere", marble, material="gold", radius=.26),
              actor("near_miss_paddle", "box", paddle, material="copper", role="driven_actuator", half=[.86, .06, .06])]
    return dict(id="01_marble_helix", seed=1101, duration_s=duration,
        backend="constrained_rolling_spiral_v1 + driven_paddle", scope="One rigid sphere rolls on an explicitly sampled, gravity-descending open rail. Paddle rotation is prescribed by a visible motor mast; the certified near miss is not a contact.",
        actors=actors, geometry=geometry, camera=camera([10, -12, 10], [0, 0, 2.7], 9.3,
            [[0, [10, -12, 10], [0, 0, 3.6]], [9, [8, -10, 7.5], [1.1, .4, 2.2]]]),
        events=[{"id":"release","type":"release","time_s":.35,"object_ids":["marble"],"cause":"retaining pin clears"},
                {"id":"paddle_near_miss","type":"near_miss","time_s":3.92,"object_ids":["marble","near_miss_paddle"],"surface_gap_m":.155,"cause":"open spiral clearance"},
                {"id":"bowl_capture","type":"capture","time_s":6.02,"object_ids":["marble","receiving-bowl"],"cause":"concave bowl"}],
        requirements={"positive_gap_m":.155,"settled_after_s":8.55,"visible_z_descent_m":3.2})


def cube_rebound():
    duration = 8.7
    impacts = [(.0, [-2.6, -1.55, 6.6], [.9, .25, 0], .95),
               (.95, [-1.745, -1.3125, 2.17], [2.45, 1.62, 4.62], .90),
               (1.85, [.46, .145, 2.37], [2.05, 1.38, 3.48], .69),
               (2.54, [1.8745, 1.0972, 2.43], [1.45, .82, 1.85], .53)]
    def cube(t):
        for start, p, velocity, span in impacts:
            if start <= t < start + span:
                return ballistic(p, velocity, t - start), q_mul(q_axis((1, .35, .2), 1.75 * t), q_axis((0, 0, 1), .65 * t))
        if t < .95:
            return ballistic(impacts[0][1], impacts[0][2], t), q_axis((1, .35, .2), 1.75 * t)
        u = clamp((t - 3.07) / 5.63)
        return lerp([2.64, 1.53, 1.74], [3.25, 1.72, 1.60], smooth(u)), q_mul(q_axis((1, .35, .2), 5.38), q_axis((0, 0, 1), .4 * (1 - u)))
    geometry = foundations() + [
        box("slab_a", [-1.75, -1.31, 1.42], [1.12, .72, .14], "stone", quaternion=q_axis((0, 1, 0), -.18)),
        box("slab_b", [.46, .15, 1.62], [1.04, .58, .14], "ceramic", quaternion=q_mul(q_axis((1, 0, 0), .17), q_axis((0, 0, 1), -.32))),
        box("slab_c", [1.87, 1.10, 1.67], [.80, .72, .14], "copper", quaternion=q_mul(q_axis((0, 1, 0), .28), q_axis((0, 0, 1), .26))),
        box("landing_table", [3.1, 1.67, 1.28], [1.08, .72, .14], "wood"),
    ]
    return dict(id="02_cube_rebound", seed=1202, duration_s=duration,
        backend="piecewise_rigid_box_impulse_v1", scope="A single rigid cube follows gravity between four measured fixed-plane impulses. Each impact uses a declared outgoing translational and angular state; this is an analytic impact model, not a claim of calibrated native Bullet.",
        actors=[actor("rebound_cube", "box", cube, material="blue", half=[.38, .38, .38])], geometry=geometry,
        camera=camera([9.8, -12.5, 8.8], [.45, .1, 2.2], 8.0, [[0,[10,-13,9],[.4,.1,2.4]],[8.7,[8,-10,7.5],[1.0,.3,2.0]]]),
        events=[{"id":"broad_face_bounce","type":"impact","time_s":.95,"object_ids":["rebound_cube","slab_a"],"post_vertical_velocity_m_s":4.62},
                {"id":"edge_bounce","type":"impact","time_s":1.85,"object_ids":["rebound_cube","slab_b"],"post_vertical_velocity_m_s":3.48},
                {"id":"corner_landing","type":"impact","time_s":2.54,"object_ids":["rebound_cube","slab_c"],"post_vertical_velocity_m_s":1.85}],
        requirements={"rotations":2.35,"settled_after_s":8.0,"impact_spacing_s":.69})


def triangle_catapult():
    duration = 8.8
    launch_t, land_t = .92, 2.67
    start, velocity = [-4.0, -1.05, 1.14], [4.15, 1.55, 8.63]
    end = ballistic(start, velocity, land_t - launch_t)
    def triangle(t):
        if t < launch_t:
            return [-4.12, -1.05, 1.14], q_axis((.25, 1, .35), 0)
        if t < land_t:
            elapsed = t - launch_t
            return ballistic(start, velocity, elapsed), q_axis((.28, .86, .42), 4.25 * math.pi * elapsed / (land_t - launch_t))
        u = clamp((t - land_t) / 5.6)
        return cubic_path([end, [2.95, 1.2, 1.25], [3.65, 1.55, .72]], u), q_axis((.28, .86, .42), 4.25 * math.pi + .25 * math.pi * u)
    def arm(t):
        return [-4.75, -1.05, .62], q_axis((0, 1, 0), -.82 * smooth(t / launch_t))
    geometry = foundations() + [box("catapult_base", [-4.75,-1.05,.28],[1.05,.9,.28],"wood"),
        box("catapult_pivot",[-4.75,-1.05,.62],[.16,.55,.16],"brass"),
        box("suspended_obstacle",[-.25,.40,4.25],[.16,1.0,.16],"charcoal"),
        box("chute_floor",[2.9,1.18,1.05],[1.45,.48,.1],"stone",quaternion=q_axis((0,1,0),-.25)),
        box("chute_side_a",[3.25,.72,1.27],[1.1,.06,.38],"steel",quaternion=q_axis((0,1,0),-.25)),
        box("chute_side_b",[3.25,1.64,1.27],[1.1,.06,.38],"steel",quaternion=q_axis((0,1,0),-.25)),
        box("triangle_catch",[3.65,1.55,.49],[.22,.55,.25],"wood")]
    return dict(id="03_triangle_catapult", seed=1303, duration_s=duration,
        backend="ballistic_prism_launch_v1 + prescribed_catapult_arm", scope="The triangular prism receives a declared off-centre launch impulse from a visibly driven arm, then follows gravity-only free flight with constant angular momentum until its chute contact.",
        actors=[actor("triangle_prism", "mesh", triangle, material="coral", mesh=triangle_prism("triangle_prism")),
                actor("catapult_arm", "box", arm, material="wood", role="driven_actuator", half=[1.0,.12,.10])], geometry=geometry,
        camera=camera([10,-12,6.8],[0.0,.3,2.4],5.5,[[0,[10,-12,6.8],[-3.2,-.9,1.4]],[3,[8,-11,6],[.4,.1,4.0]],[8.8,[8,-10,6.5],[2.8,1.3,1.3]]]),
        events=[{"id":"arm_launch","type":"launch","time_s":launch_t,"object_ids":["catapult_arm","triangle_prism"],"launch_velocity_m_s":velocity,"angular_turns":2.125},
                {"id":"obstacle_clearance","type":"near_miss","time_s":1.79,"object_ids":["triangle_prism","suspended_obstacle"],"surface_gap_m":.31},
                {"id":"chute_capture","type":"capture","time_s":land_t,"object_ids":["triangle_prism","chute_floor"]}],
        requirements={"airborne_rotation_turns":2.125,"settled_after_s":7.9})


def crossing_orbits():
    duration = 9.0
    route_a = [[-4.25,-1.7,5.15],[-2.6,-.65,4.0],[-.25,.05,3.0],[2.3,1.1,1.18]]
    route_b = [[3.95,-2.7,4.75],[2.35,-1.2,4.15],[.28,.57,3.62],[-2.4,1.8,1.16]]
    def a(t): return route_pose(route_a,.28,5.25,spin_axis=(0,1,0),rotations=5.1)(t)
    def b(t): return route_pose(route_b,1.08,5.85,spin_axis=(0,1,0),rotations=4.8)(t)
    geometry = foundations() + guide("route_a", route_a, material="brass", width=.56) + guide("route_b", route_b, material="steel", width=.56)
    geometry += [{"id":"a_bowl","shape":"hoop","radius_m":.72,"tube_radius_m":.06,"position_m":[2.3,1.1,.46],"quaternion_xyzw":[0,0,0,1],"material":"stone","role":"catcher"},
                 {"id":"b_bowl","shape":"hoop","radius_m":.72,"tube_radius_m":.06,"position_m":[-2.4,1.8,.46],"quaternion_xyzw":[0,0,0,1],"material":"wood","role":"catcher"}]
    return dict(id="04_crossing_orbits", seed=1404, duration_s=duration,
        backend="dual_independent_constrained_spheres_v1", scope="Two separately constrained rolling spheres use physically independent fixed routes. Their paths are intentionally offset in depth at convergence and no collision response is asserted or needed.",
        actors=[actor("sphere_a","sphere",a,material="gold",radius=.25), actor("sphere_b","sphere",b,material="teal",radius=.25)],geometry=geometry,
        camera=camera([10,-13,11],[0,0,2.6],9.0,[[0,[10,-13,11],[0,0,3]],[9,[8,-11,9],[0,.2,2.8]]]),
        events=[{"id":"a_release","type":"release","time_s":.28,"object_ids":["sphere_a"]},{"id":"b_release","type":"release","time_s":1.08,"object_ids":["sphere_b"]},
                {"id":"certified_crossing","type":"near_miss","time_s":3.72,"object_ids":["sphere_a","sphere_b"],"surface_gap_m":.18,"cause":"vertical route offset"},
                {"id":"separate_captures","type":"capture","time_s":5.85,"object_ids":["sphere_a","sphere_b"]}],
        requirements={"positive_gap_m":.18,"both_visible_at_s":3.72,"settled_after_s":8.0})


def tumbling_tetrahedron():
    duration = 8.9
    impacts = [(.0, [-3.2,-1.0,6.0], [.42,.28,0], .95),
               (.95, [-2.801,-.734,1.574], [2.70,1.10,4.42], .65),
               (1.60, [-1.046,-.019,2.374], [2.90,1.30,5.22], 1.00)]
    def tetra(t):
        for start, position, velocity, span in impacts:
            if start <= t < start + span:
                e = t - start
                q = q_mul(q_axis((.9,.25,.35), 4.3 * e + start), q_axis((.1,.7,.7), 2.0 * e))
                return ballistic(position, velocity, e), q
        u = clamp((t - 2.60) / 6.3)
        return cubic_path([[1.85,1.28,2.69],[2.55,1.62,1.40],[3.20,1.75,.72]], u), q_mul(q_axis((.9,.25,.35), 11.2), q_axis((.1,.7,.7), .8*(1-u)))
    geometry = foundations() + [
        box("tetra_slab_one",[-2.80,-.73,1.18],[1.1,.65,.12],"stone",quaternion=q_mul(q_axis((0,1,0),-.19),q_axis((0,0,1),.12))),
        box("tetra_slab_two",[-1.05,-.02,1.98],[.80,.70,.12],"wood",quaternion=q_mul(q_axis((0,1,0),.22),q_axis((0,0,1),-.26))),
        box("tetra_final_platform",[1.85,1.28,2.28],[1.25,.78,.12],"ceramic",quaternion=q_axis((0,1,0),-.15)),
        box("slot_left",[3.20,1.34,.62],[.38,.07,.43],"brass",quaternion=q_axis((0,1,0),-.12)),
        box("slot_right",[3.20,2.16,.62],[.38,.07,.43],"brass",quaternion=q_axis((0,1,0),-.12)),
        box("slot_base",[3.20,1.75,.36],[.46,.50,.08],"wood"),
    ]
    return dict(id="05_tumbling_tetrahedron", seed=1505, duration_s=duration,
        backend="piecewise_polyhedral_impact_v1", scope="A fixed-plane, piecewise rigid-polyhedron impact model: gravity segments preserve angular momentum, and each vertex/edge contact declares a new state. This does not inherit native-Bullet calibration.",
        actors=[actor("tumbling_tetrahedron","mesh",tetra,material="teal",mesh=tetrahedron("tumbling_tetrahedron"))],geometry=geometry,
        camera=camera([9,-12,10],[-.2,.4,2.0],8.6,[[0,[9,-12,10],[-1,-.1,2.5]],[8.9,[7.5,-10,7.2],[1.5,1.0,1.5]]]),
        events=[{"id":"vertex_contact","type":"impact","time_s":.95,"object_ids":["tumbling_tetrahedron","tetra_slab_one"],"contact_feature":"vertex","post_vertical_velocity_m_s":4.42},
                {"id":"edge_contact","type":"impact","time_s":1.60,"object_ids":["tumbling_tetrahedron","tetra_slab_two"],"contact_feature":"edge","post_vertical_velocity_m_s":5.22},
                {"id":"slot_capture","type":"capture","time_s":3.15,"object_ids":["tumbling_tetrahedron","slot_base"],"cause":"tetrahedral-width slot"}],
        requirements={"airborne_rotation_turns":1.95,"settled_after_s":8.0,"nonrepeating_impacts":True})


def rolling_torus_gate():
    duration = 9.0
    route = [[-4.25,-1.25,3.7],[-3.2,-.95,3.32],[-1.25,-.25,2.75],[.35,.25,2.35],[1.7,.75,1.25],[2.8,1.15,.76]]
    def torus(t):
        if t < .25:
            return route[0], q_axis((0,1,0),0)
        u = clamp((t-.25)/6.7)
        return cubic_path(route,u), q_mul(q_axis((0,1,0), 7*math.pi*u), q_axis((0,0,1), .62))
    def gate(t):
        return [.55,.34,2.36], q_axis((1,0,0), -1.35*smooth((t-3.65)/.80))
    geometry = foundations() + guide("torus_rail",route,material="steel",width=.68,rail=.045)
    geometry += [box("gate_mast",[.55,.34,1.22],[.08,.08,1.22],"copper"),
                 box("gate_header",[.55,.34,3.50],[.55,.08,.08],"brass"),
                 box("trigger_pedal",[.12,.21,2.16],[.16,.28,.06],"wood"),
                 box("through_hole_strut",[-1.25,.05,2.15],[.07,.07,1.30],"gold"),
                 {"id":"torus_capture","shape":"hoop","radius_m":.73,"tube_radius_m":.07,"position_m":[2.8,1.15,.43],"quaternion_xyzw":[0,0,0,1],"material":"stone","role":"catcher"}]
    return dict(id="06_rolling_torus_gate", seed=1606, duration_s=duration,
        backend="constrained_rolling_torus_v1 + driven_gate", scope="A finite torus rolls with its displayed axial orientation on an exposed fixed rail. Contact with the passive trigger is measured; the gate is a visibly powered prescribed actuator with no unclaimed dynamic hinge response.",
        actors=[actor("rolling_torus","hoop",torus,material="gold",radius=.42,extra={"tube_radius_m":.065}),
                actor("lift_gate","box",gate,material="copper",role="driven_actuator",half=[.55,.06,.08])],geometry=geometry,
        camera=camera([8.5,-11,5.0],[-.6,-.05,2.1],4.8,[[0,[8.5,-11,5],[-3.6,-1.0,3.25]],[4.4,[7.5,-9.5,4.5],[.35,.25,2.3]],[9,[7,-9,4.5],[2.1,.9,1.15]]]),
        events=[{"id":"roll_release","type":"release","time_s":.25,"object_ids":["rolling_torus"]},
                {"id":"trigger_contact","type":"contact","time_s":3.65,"object_ids":["rolling_torus","trigger_pedal"],"cause":"rail endpoint pedal"},
                {"id":"gate_open","type":"mechanical_release","time_s":4.45,"object_ids":["lift_gate"],"cause":"visible drive mast"},
                {"id":"torus_capture","type":"capture","time_s":6.95,"object_ids":["rolling_torus","torus_capture"]}],
        requirements={"visible_orientation_turns":6.0,"through_hole_strut_visible":True,"settled_after_s":8.2})


def capsule_pendulum():
    duration = 9.0
    incoming = [[-4.2,-1.1,4.9],[-2.8,-.7,3.8],[-1.2,-.25,2.72],[-.55,.02,2.22]]
    outgoing = [[-.55,.02,2.22],[.35,.55,1.75],[1.55,1.15,1.18],[2.65,1.55,.68]]
    pivot = [0.0,.0,4.35]
    def cap(t):
        if t < 2.55:
            return route_pose(incoming,.2,2.55,spin_axis=(0,1,0),rotations=2.4)(t)
        return route_pose(outgoing,2.55,7.15,spin_axis=(0,1,0),rotations=3.1)(t)
    def bob(t):
        elapsed=max(0,t-2.55)
        angle=.64*math.exp(-.30*elapsed)*math.sin(2.2*elapsed)
        return [pivot[0]+1.95*math.sin(angle),0,pivot[2]-1.95*math.cos(angle)],q_axis((0,1,0),angle)
    geometry=foundations()+guide("capsule_upper",incoming,material="brass",width=.64)+guide("capsule_lower",outgoing,material="steel",width=.65)
    geometry += [box("pendulum_frame",[0,0,4.42],[.72,.14,.12],"wood"),box("pendulum_post",[0,.5,2.2],[.10,.10,2.2],"wood"),
                 {"id":"capsule_catch","shape":"hoop","radius_m":.70,"tube_radius_m":.07,"position_m":[2.65,1.55,.40],"quaternion_xyzw":[0,0,0,1],"material":"stone","role":"catcher"}]
    bob_extra={"cable":{"radius_m":.028,"fixed_endpoint_m":pivot,"actor_attachment_local_m":[0,0,0]}}
    return dict(id="07_capsule_pendulum",seed=1707,duration_s=duration,
        backend="capsule_pendulum_transfer_v1",scope="An analytic, inelastic capsule-to-pendulum impulse initializes a damped gravity pendulum. The capsule redirects through a separate fixed lower guide; both motions remain in the same evaluated packet.",
        actors=[actor("capsule","mesh",cap,material="ceramic",mesh=capsule("capsule")),actor("pendulum_bob","sphere",bob,material="copper",role="secondary_mechanism",radius=.30,extra=bob_extra)],geometry=geometry,
        camera=camera([9,-12,8],[-.1,.2,2.3],8.3,[[0,[9,-12,8],[-1,-.3,2.7]],[9,[8,-10,7],[1,.7,1.8]]]),
        events=[{"id":"capsule_release","type":"release","time_s":.2,"object_ids":["capsule"]},{"id":"pendulum_impact","type":"impact","time_s":2.55,"object_ids":["capsule","pendulum_bob"],"post_angular_velocity_rad_s":1.41},
                {"id":"lower_track_capture","type":"capture","time_s":7.15,"object_ids":["capsule","capsule_catch"]}],
        requirements={"pendulum_visible_after_impact_s":2.3,"settled_after_s":8.4})


def cube_cascade():
    duration=9.0
    def a(t):
        if t<1.15: return ballistic([-3.6,-.9,5.2],[.3,.1,0],t),q_axis((1,.1,.2),1.2*t)
        if t<2.35: return ballistic([-3.255,-.785, -1.29],[2.05,.65,4.15],t-1.15),q_axis((1,.1,.2),1.38+1.7*(t-1.15))
        return lerp([-.80,-.02,1.9],[-.42,.18,1.42],smooth((t-2.35)/5.8)),q_axis((1,.1,.2),3.2)
    def b(t):
        if t<3.45:return [-.2,-2.5,4.5],q_axis((.2,1,.4),0)
        if t<5.25:return ballistic([-.2,-2.5,4.5],[1.5,1.9,1.0],t-3.45),q_axis((.2,1,.4),2.8*(t-3.45))
        return lerp([2.5,.92,1.42],[2.75,1.08,1.30],smooth((t-5.25)/3.5)),q_axis((.2,1,.4),5.1)
    def c(t):
        if t<6.15:return [2.55,-2.1,4.2],q_axis((.4,.2,1),0)
        if t<7.45:return ballistic([2.55,-2.1,4.2],[-.75,2.25,.65],t-6.15),q_axis((.4,.2,1),3.2*(t-6.15))
        return lerp([1.58,.82,1.12],[1.30,.98,.98],smooth((t-7.45)/1.55)),q_axis((.4,.2,1),4.2)
    geometry=foundations()+[box("cascade_slab_a",[-3.25,-.78,1.24],[1.0,.72,.12],"stone"),box("release_lever",[-.42,.15,1.75],[.52,.08,.08],"brass"),box("cascade_wall",[2.2,.45,2.55],[.10,1.0,1.6],"wood"),box("cube_a_rest",[-.42,.18,1.0],[.62,.55,.12],"ceramic"),box("cube_b_rest",[2.75,1.08,.9],[.62,.55,.12],"copper"),box("cube_c_rest",[1.30,.98,.65],[.62,.55,.12],"teal")]
    return dict(id="08_cube_cascade",seed=1808,duration_s=duration,backend="separated_three_body_impulse_sequence_v1",scope="Three rigid cuboids use separate gravity/impact segments with deliberate no-contact intervals. Release states are caused by visibly struck levers; their paths are not a calibrated general multi-body Bullet claim.",
        actors=[actor("cube_a","box",a,material="blue",half=[.36,.36,.36]),actor("cube_b","box",b,material="copper",half=[.50,.28,.30]),actor("cube_c","box",c,material="teal",half=[.28,.44,.25])],geometry=geometry,
        camera=camera([10,-13,9],[-.3,-.1,2.0],9.0,[[0,[10,-13,9],[-1,-.4,2.3]],[9,[8,-11,7],[.6,.2,1.7]]]),
        events=[{"id":"a_bounce_and_release","type":"impact","time_s":1.15,"object_ids":["cube_a","cascade_slab_a"],"post_vertical_velocity_m_s":4.15},{"id":"b_release","type":"mechanical_release","time_s":3.45,"object_ids":["cube_b","release_lever"]},{"id":"c_transfer","type":"momentum_transfer","time_s":6.15,"object_ids":["cube_c","cube_b"]}],
        requirements={"major_event_min_spacing_s":2.3,"separate_resting_states":True,"settled_after_s":8.4})


def geometric_relay():
    duration=9.0
    sphere_route=[[-4.6,-1.5,5.0],[-3.2,-1.0,4.1],[-1.8,-.45,3.28]]
    cube_route=[[-1.55,-.35,3.1],[-.3,.25,2.35],[1.15,.78,1.78],[1.72,1.05,1.31]]
    tri_start=[1.82,1.08,1.45]; tri_velocity=[2.05,1.58,6.55]; tri_land=ballistic(tri_start,tri_velocity,1.3)
    def sphere(t):return route_pose(sphere_route,.25,2.45,spin_axis=(0,1,0),rotations=3.2)(t)
    def cube(t):return route_pose(cube_route,2.55,5.35,spin_axis=(.3,1,.4),rotations=1.4)(t)
    def triangle(t):
        if t<5.45:return tri_start,q_axis((.3,.85,.4),0)
        if t<6.75:
            e=t-5.45;return ballistic(tri_start,tri_velocity,e),q_axis((.3,.85,.4),3.7*math.pi*e/1.3)
        return cubic_path([tri_land,[3.8,2.7,1.05],[4.15,2.95,.68]],clamp((t-6.75)/2.25)),q_axis((.3,.85,.4),3.7*math.pi)
    geometry=foundations((7.0,5.0))+guide("relay_upper",sphere_route,material="brass",width=.56)+guide("relay_middle",cube_route,material="steel",width=.63)
    geometry += [box("sphere_cube_trigger",[-1.65,-.4,3.0],[.18,.40,.10],"wood"),box("triangle_launcher",[1.65,1.0,.78],[.75,.60,.16],"wood"),box("relay_obstacle",[3.05,2.02,3.48],[.16,.86,.16],"charcoal"),{ "id":"relay_final_bowl","shape":"hoop","radius_m":.78,"tube_radius_m":.07,"position_m":[4.15,2.95,.42],"quaternion_xyzw":[0,0,0,1],"material":"stone","role":"catcher"}]
    return dict(id="09_geometric_relay",seed=1909,duration_s=duration,backend="three_stage_causal_relay_v1",scope="A constrained sphere triggers a gravity-driven cube release; the cube's measured terminal contact releases a triangular-prism ballistic launch. Each causal stage has separate declared states and a visible support/actuator.",
        actors=[actor("relay_sphere","sphere",sphere,material="gold",radius=.25),actor("relay_cube","box",cube,material="blue",half=[.34,.34,.34]),actor("relay_triangle","mesh",triangle,material="coral",mesh=triangle_prism("relay_triangle"))],geometry=geometry,
        camera=camera([11,-13,9],[-.2,.3,2.5],9.6,[[0,[11,-13,9],[-2,-.6,3]],[5.4,[9,-11,7],[1,.7,2]],[9,[8,-10,6],[3,2,1.5]]]),
        events=[{"id":"sphere_activates_cube","type":"contact","time_s":2.45,"object_ids":["relay_sphere","sphere_cube_trigger"]},{"id":"cube_activates_triangle","type":"mechanical_release","time_s":5.35,"object_ids":["relay_cube","triangle_launcher"]},{"id":"triangle_final_flight","type":"launch","time_s":5.45,"object_ids":["relay_triangle"],"launch_velocity_m_s":tri_velocity,"angular_turns":1.85},{"id":"relay_capture","type":"capture","time_s":6.75,"object_ids":["relay_triangle","relay_final_bowl"]}],
        requirements={"causal_order":["sphere_activates_cube","cube_activates_triangle","triangle_final_flight"],"settled_after_s":8.2})


BUILDERS = {"01_marble_helix": marble_helix, "02_cube_rebound": cube_rebound,
            "03_triangle_catapult": triangle_catapult, "04_crossing_orbits": crossing_orbits,
            "05_tumbling_tetrahedron": tumbling_tetrahedron, "06_rolling_torus_gate": rolling_torus_gate,
            "07_capsule_pendulum": capsule_pendulum, "08_cube_cascade": cube_cascade,
            "09_geometric_relay": geometric_relay}


def state_rows(packet):
    """Evaluate every actor at the identical high-rate seconds clock used in replay."""
    duration = packet["duration_s"]
    actors = packet["actors"]
    rows = []
    for tick in range(round(duration * HZ) + 1):
        time_s = tick / HZ
        objects = {}
        for spec in actors:
            position, quaternion = spec["_pose"](time_s)
            before = max(0.0, time_s - 1 / HZ)
            after = min(duration, time_s + 1 / HZ)
            p0, _ = spec["_pose"](before)
            p1, _ = spec["_pose"](after)
            dt = max(1e-12, after - before)
            norm_q = math.sqrt(sum(value * value for value in quaternion))
            if not norm_q:
                raise ValueError("zero quaternion: " + spec["id"])
            objects[spec["id"]] = {"position_m": [float(value) for value in position],
                                   "quaternion_xyzw": [float(value / norm_q) for value in quaternion],
                                   "velocity_m_s": [float((p1[i] - p0[i]) / dt) for i in range(3)],
                                   "scale": [1.0, 1.0, 1.0]}
        rows.append({"tick": tick, "time_s": time_s, "objects": objects})
    return rows


def simplified_actor(spec):
    return {key: value for key, value in spec.items() if key != "_pose"}


def validate(packet, rows):
    """Mechanical packet validation, deliberately distinct from visual/human acceptance."""
    expected_count = round(packet["duration_s"] * HZ) + 1
    failures = []
    if len(rows) != expected_count:
        failures.append("sample_count")
    actor_ids = [actor["id"] for actor in packet["actors"]]
    if len(actor_ids) != len(set(actor_ids)):
        failures.append("duplicate_actor_id")
    geometry_ids = [geometry["id"] for geometry in packet["geometry"]]
    if set(actor_ids) & set(geometry_ids) or len(geometry_ids) != len(set(geometry_ids)):
        failures.append("duplicate_geometry_id")
    max_speed = {actor_id: 0.0 for actor_id in actor_ids}
    max_q_error = 0.0
    for tick, row in enumerate(rows):
        if row["tick"] != tick or abs(row["time_s"] - tick / HZ) > 1e-12:
            failures.append("clock")
            break
        if set(row["objects"]) != set(actor_ids):
            failures.append("actor_coverage")
            break
        for actor_id, pose in row["objects"].items():
            values = pose["position_m"] + pose["velocity_m_s"] + pose["quaternion_xyzw"]
            if not all(math.isfinite(value) for value in values):
                failures.append("nonfinite:" + actor_id)
            q_error = abs(sum(value * value for value in pose["quaternion_xyzw"]) - 1)
            max_q_error = max(max_q_error, q_error)
            max_speed[actor_id] = max(max_speed[actor_id], vlen(pose["velocity_m_s"]))
    event_times = [event["time_s"] for event in packet["events"]]
    if event_times != sorted(event_times) or not all(0 <= time <= packet["duration_s"] for time in event_times):
        failures.append("event_clock")
    gap_events = [event for event in packet["events"] if event["type"] == "near_miss"]
    if any(event.get("surface_gap_m", 0) <= 0 for event in gap_events):
        failures.append("nonpositive_near_miss")
    # Continuous actor motion must occupy the majority of every clip; support/gate actors are excluded.
    hero_ids = [actor["id"] for actor in packet["actors"] if actor.get("role") == "hero"]
    moving_fraction = {}
    for actor_id in hero_ids:
        moving_fraction[actor_id] = sum(vlen(row["objects"][actor_id]["velocity_m_s"]) > .08 for row in rows) / len(rows)
    group_motion_fraction = sum(any(vlen(row["objects"][actor_id]["velocity_m_s"]) > .08 for actor_id in hero_ids)
                                for row in rows) / len(rows) if hero_ids else 0.0
    if len(hero_ids) == 1 and moving_fraction[hero_ids[0]] < .50:
        failures.append("insufficient_motion:" + hero_ids[0])
    if len(hero_ids) > 1 and group_motion_fraction < .50:
        failures.append("insufficient_group_motion")
    return {"status": "PASS" if not failures else "FAIL", "mechanics_status": "PASS" if not failures else "FAIL",
            "scope": packet["scope"], "backend": packet["backend"], "sample_rate_hz": HZ,
            "duration_s": packet["duration_s"], "samples": len(rows), "events": packet["events"],
            "max_speed_m_s": max_speed, "hero_motion_fraction": moving_fraction,
            "hero_group_motion_fraction": group_motion_fraction,
            "max_quaternion_norm_error": max_q_error, "failures": failures,
            "fresh_blender_replay": "NOT_RUN", "rendered_temporal_validation": "NOT_RUN",
            "still_proxy_review": "NOT_RUN", "continuous_motion_human_review": "NOT_RUN",
            "music_audition": "NOT_RUN", "approval": None}


def prepare(out: Path, scene_id: str):
    if scene_id not in BUILDERS:
        raise ValueError("unknown scene ID")
    if out.exists():
        raise ValueError("candidate directory already exists; preserve earlier evidence")
    packet = BUILDERS[scene_id]()
    rows = state_rows(packet)
    validation = validate(packet, rows)
    if validation["status"] != "PASS":
        raise RuntimeError("authoring validation failed: " + repr(validation["failures"]))
    out.mkdir(parents=True)
    compact = {key: value for key, value in packet.items() if key not in ("actors",)}
    compact["actors"] = [simplified_actor(spec) for spec in packet["actors"]]
    compact["hz"] = HZ
    compact["batch"] = "kinetic_geometry_01"
    compact["approval"] = None
    compact["validation"] = {"assumptions": [packet["scope"]], "status": validation["status"]}
    with (out / "mechanics_states.jsonl").open("x") as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
    write_json(out / "packet.json", compact)
    write_json(out / "validation_report.json", validation)
    intent_root = ROOT / "docs/requests/kinetic-geometry-01"
    intent_sources = sorted(path for path in intent_root.rglob(scene_id + ".*") if path.is_file())
    structured_intents = [path for path in intent_sources if path.name.endswith(".scene-intent.json") or path.name.endswith(".scene-intent-2.json")]
    intent_sources = structured_intents or intent_sources
    if len(intent_sources) != 1:
        raise RuntimeError("expected exactly one user-directed source plan for " + scene_id)
    intent_source = intent_sources[0]
    intent_target = out / ("scene_intent" + intent_source.suffix)
    shutil.copyfile(intent_source, intent_target)
    source_paths = [Path(__file__), DRIVER, CAMERA_RENDERER,
                    ROOT / "modules/blender/production/driver.py", ROOT / "modules/blender/production/common.py",
                    ROOT / "modules/blender/geometry.py", ROOT / "modules/blender/batch.py"]
    source_hashes = {}
    for source in source_paths:
        relative = source.resolve().relative_to(ROOT)
        target = out / "generation_source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        source_hashes[str(relative)] = digest(target)
    write_json(out / "provenance.json", {"batch": "kinetic_geometry_01", "id": scene_id,
        "seed": packet["seed"], "source_hashes": source_hashes,
        "input_hashes": {"packet.json": digest(out / "packet.json"), "mechanics_states.jsonl": digest(out / "mechanics_states.jsonl"),
                         intent_target.name: digest(intent_target)},
        "source_intent": str(intent_source.relative_to(ROOT)),
        "blender_driver": str(DRIVER.relative_to(ROOT)), "approval": None})
    print(json.dumps({"id": scene_id, "out": str(out), "validation": validation["status"]}, indent=2))


def verify_inputs(out: Path):
    provenance = json.loads((out / "provenance.json").read_text())
    for relative, expected in provenance["source_hashes"].items():
        if digest(ROOT / relative) != expected or digest(out / "generation_source" / relative) != expected:
            raise RuntimeError("source changed; prepare a new candidate: " + relative)
    for name, expected in provenance["input_hashes"].items():
        if digest(out / name) != expected:
            raise RuntimeError("input changed: " + name)


def run_job(out: Path, stage: str, command, timeout: int):
    verify_inputs(out)
    log = out / "jobs" / (stage + ".log")
    if log.exists():
        raise RuntimeError("job evidence exists; preserve it: " + str(log))
    if not 1 <= timeout <= 1800:
        raise ValueError("timeout must be 1..1800 seconds")
    with Path("/private/tmp/scenescore-kinetic-geometry.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = bounded(command, log, timeout)
    if result["status"] != "passed" or not result["process_group_absent"]:
        raise RuntimeError("stage failed: " + stage)
    return result


def stage(out: Path, selected: str, blender: str | None, timeout: int, job_suffix: str = ""):
    packet = json.loads((out / "packet.json").read_text())
    binary = blender_executable(blender)
    if selected in ("build", "replay", "verify"):
        command = [binary, "--background", "--factory-startup", "--python-exit-code", "1", "--threads", "2",
                   "--python", str(DRIVER), "--", selected, "--out", str(out)]
        run_job(out, selected + job_suffix, command, timeout)
        if selected == "verify":
            replay = json.loads((out / "replay_validation.json").read_text())
            report = json.loads((out / "validation_report.json").read_text())
            report["fresh_blender_replay"] = "PASS" if replay["status"] == "PASSED" else "FAIL"
            write_json(out / "validation_report.json", report)
    elif selected == "camera":
        command = [binary, "--background", "--factory-startup", "--python-exit-code", "1", "--threads", "2",
                   "--python", str(CAMERA_RENDERER), "--", "camera", "--out", str(out)]
        run_job(out, selected + job_suffix, command, timeout)
    elif selected in ("proxy", "final"):
        profile = selected
        command = [binary, "--background", "--factory-startup", "--python-exit-code", "1", "--threads", "2",
                   "--python", str(CAMERA_RENDERER), "--", "render", "--out", str(out), "--profile", profile]
        run_job(out, selected + "-render" + job_suffix, command, timeout)
        ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        frame_dir = out / ("proxy_frames" if selected == "proxy" else "final_frames")
        target = out / ("proxy.mp4" if selected == "proxy" else "final.mp4")
        count = round(packet["duration_s"] * FPS)
        run_job(out, selected + "-encode" + job_suffix, [ffmpeg, "-v", "error", "-nostdin", "-n", "-framerate", "30", "-start_number", "1",
            "-i", str(frame_dir / "frame_%04d.png"), "-frames:v", str(count), "-c:v", "libx264", "-threads", "2", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)], min(timeout, 600))
    elif selected == "media":
        ffprobe = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
        final = out / "final.mp4"
        command = [ffprobe, "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(final)]
        run_job(out, "media" + job_suffix, command, min(timeout, 180))
        media = json.loads((out / "jobs" / ("media" + job_suffix + ".log")).read_text())
        stream = next(item for item in media["streams"] if item["codec_type"] == "video")
        count = round(packet["duration_s"] * FPS)
        okay = stream["width"] == 1080 and stream["height"] == 1920 and int(stream["nb_read_frames"]) == count
        report = json.loads((out / "validation_report.json").read_text())
        report["rendered_temporal_validation"] = "PASS" if okay else "FAIL"
        report["final_media"] = {"path": str(final), "sha256": digest(final), "width": stream["width"], "height": stream["height"], "frames": int(stream["nb_read_frames"]), "duration_s": float(media["format"]["duration"])}
        write_json(out / "validation_report.json", report)
    else:
        raise ValueError("unknown stage")
    print(json.dumps({"id": packet["id"], "stage": selected, "out": str(out)}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "build", "replay", "verify", "camera", "proxy", "final", "media"))
    parser.add_argument("--id", choices=IDS)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--blender")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--job-suffix", default="", help="distinct retry receipt suffix, for example -host")
    args = parser.parse_args(argv)
    out = args.out.resolve()
    if not out.is_relative_to(ARTIFACT_ROOT):
        parser.error("out must be below " + str(ARTIFACT_ROOT))
    if args.command == "prepare":
        if not args.id:
            parser.error("--id is required for prepare")
        prepare(out, args.id)
    else:
        stage(out, args.command, args.blender, args.timeout, args.job_suffix)


if __name__ == "__main__":
    main()
