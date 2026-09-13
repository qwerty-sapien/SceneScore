"""Serializable component specifications and immutable evaluated geometry."""
from dataclasses import dataclass, replace
import json
import math
import re

from .math3d import (add, sub, mul, rotate, quaternion, qmul, vector, finite, unit, corners, bounds)

VERSION = 'mechanism-components-1'
IDENTITY = (0., 0., 0., 1.)


def exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label} requires exactly {sorted(keys)}')


@dataclass(frozen=True)
class Transform:
    position_m: tuple = (0., 0., 0.)
    quaternion_xyzw: tuple = IDENTITY

    @classmethod
    def from_dict(cls, value):
        exact_keys(value, ['position_m', 'quaternion_xyzw'], 'transform')
        return cls(vector(value['position_m']), quaternion(value['quaternion_xyzw']))

    def point(self, point):
        return add(self.position_m, rotate(self.quaternion_xyzw, point))

    def direction(self, direction):
        return rotate(self.quaternion_xyzw, direction)

    def compose(self, child):
        return Transform(self.point(child.position_m), quaternion(qmul(self.quaternion_xyzw, child.quaternion_xyzw)))

    def to_dict(self):
        return {'position_m': list(self.position_m), 'quaternion_xyzw': list(self.quaternion_xyzw)}


@dataclass(frozen=True)
class Anchor:
    position_m: tuple
    direction: tuple
    clearance_radius_m: float
    surface_normal: tuple = (0., 0., 1.)

    @classmethod
    def from_dict(cls, value):
        exact_keys(value, ['position_m', 'direction', 'clearance_radius_m', 'surface_normal'], 'anchor')
        return cls(vector(value['position_m']), unit(vector(value['direction'])),
                   finite(value['clearance_radius_m'], 'clearance_radius_m'), unit(vector(value['surface_normal'])))

    def transformed(self, transform):
        return Anchor(transform.point(self.position_m), transform.direction(self.direction), self.clearance_radius_m,
                      transform.direction(self.surface_normal))

    def to_dict(self):
        return {'position_m': list(self.position_m), 'direction': list(self.direction),
                'clearance_radius_m': self.clearance_radius_m, 'surface_normal': list(self.surface_normal)}


@dataclass(frozen=True)
class BoxGeometry:
    part_id: str
    position_m: tuple
    half_extents_m: tuple
    quaternion_xyzw: tuple = IDENTITY

    def transformed(self, transform):
        return BoxGeometry(self.part_id, transform.point(self.position_m), self.half_extents_m,
                           quaternion(qmul(transform.quaternion_xyzw, self.quaternion_xyzw)))

    @property
    def vertices(self):
        return corners(self.position_m, self.half_extents_m, self.quaternion_xyzw)

    def to_dict(self):
        return {'part_id': self.part_id, 'shape': 'box', 'position_m': list(self.position_m),
                'half_extents_m': list(self.half_extents_m), 'quaternion_xyzw': list(self.quaternion_xyzw)}


@dataclass(frozen=True)
class ComponentSpec:
    component_id: str
    type: str
    transform: Transform
    entry_anchor: Anchor | None
    exit_anchor: Anchor | None
    parameters: tuple
    friction: float
    restitution: float
    bevel_m: float
    material_role: str

    @classmethod
    def from_dict(cls, value):
        exact_keys(value, ['component_id', 'type', 'transform', 'entry_anchor', 'exit_anchor', 'parameters',
                           'collision', 'visual', 'material_role'], 'component')
        if not isinstance(value['component_id'], str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]*', value['component_id']):
            raise ValueError('invalid component_id')
        if not isinstance(value['type'], str) or not isinstance(value['material_role'], str) or not value['material_role'].strip():
            raise ValueError('component type and material_role must be nonempty strings')
        p = value['parameters']
        if not isinstance(p, dict) or not all(isinstance(k, str) for k in p):
            raise ValueError('parameters must be a named numeric object')
        collision = value['collision']
        exact_keys(collision, ['mode', 'shape', 'friction', 'restitution'], 'collision')
        if collision['mode'] != 'fixed' or collision['shape'] != 'obb_union':
            raise ValueError('only fixed OBB unions are supported; beauty meshes are never collision surfaces')
        friction, restitution = (finite(collision[key], key) for key in ('friction', 'restitution'))
        if not 0 <= friction <= 1 or not 0 <= restitution <= 1:
            raise ValueError('material coefficients must be within [0,1]')
        exact_keys(value['visual'], ['bevel_m'], 'visual')
        bevel = finite(value['visual']['bevel_m'], 'bevel_m')
        if not 0 <= bevel <= .005:
            raise ValueError('bevel_m must be 0..0.005; collision/beauty discrepancy must remain bounded')
        return cls(value['component_id'], value['type'], Transform.from_dict(value['transform']),
                   Anchor.from_dict(value['entry_anchor']) if value['entry_anchor'] is not None else None,
                   Anchor.from_dict(value['exit_anchor']) if value['exit_anchor'] is not None else None,
                   tuple(sorted((k, finite(v, k)) for k, v in p.items())), friction, restitution, bevel, value['material_role'])

    def to_dict(self):
        return {'component_id': self.component_id, 'type': self.type, 'transform': self.transform.to_dict(),
                'entry_anchor': self.entry_anchor.to_dict() if self.entry_anchor else None,
                'exit_anchor': self.exit_anchor.to_dict() if self.exit_anchor else None,
                'parameters': dict(self.parameters), 'collision': {'mode': 'fixed', 'shape': 'obb_union',
                'friction': self.friction, 'restitution': self.restitution}, 'visual': {'bevel_m': self.bevel_m},
                'material_role': self.material_role}


@dataclass(frozen=True)
class LocalGeometry:
    boxes: tuple
    entry: Anchor
    exit: Anchor
    centerline: tuple
    route_capable: bool = True
    notes: tuple = ()
    approximation_m: float = 0.


class Component:
    """Each subclass owns a small mechanism; build() needs no Blender import."""
    defaults = {}

    def __init__(self, spec):
        spec = ComponentSpec.from_dict(spec.to_dict() if isinstance(spec, ComponentSpec) else spec)
        if spec.type != type(self).__name__:
            raise ValueError('component class does not match serialized type')
        supplied = dict(spec.parameters)
        if set(supplied)-set(self.defaults):
            raise ValueError(f'unknown {spec.type} parameters: {sorted(set(supplied)-set(self.defaults))}')
        parameters = {**self.defaults, **supplied}
        if any(v <= 0 for k, v in parameters.items() if k not in {'drop_m', 'turn_deg', 'deflection_deg'}):
            raise ValueError('component dimensions and radius must be positive')
        if parameters.get('drop_m', 0) < 0:
            raise ValueError('drop_m must not be negative')
        if not .001 <= parameters.get('actor_radius_m', .15) <= 10:
            raise ValueError('actor radius outside component scope')
        self.spec = replace(spec, parameters=tuple(sorted(parameters.items())))
        self._local = self.describe(parameters)
        if not self._local.boxes or len(self._local.boxes) > 128:
            raise ValueError('component must contain 1..128 fixed boxes')
        if len({b.part_id for b in self._local.boxes}) != len(self._local.boxes):
            raise ValueError('duplicate collider part ID')
        if any(min(b.half_extents_m) <= 0 for b in self._local.boxes):
            raise ValueError('collider dimensions must be positive')
        if any(spec.bevel_m > min(b.half_extents_m)/2 for b in self._local.boxes):
            raise ValueError('bevel is too large for a component part')
        for declared, measured in [(spec.entry_anchor, self._local.entry), (spec.exit_anchor, self._local.exit)]:
            if declared is not None and (math.dist(declared.position_m, measured.position_m) > 1e-7
                    or math.dist(declared.direction, measured.direction) > 1e-7
                    or abs(declared.clearance_radius_m-measured.clearance_radius_m) > 1e-7
                    or math.dist(declared.surface_normal, measured.surface_normal) > 1e-7):
                raise ValueError('declared local anchor contradicts generated component geometry')
        if self._local.route_capable and self.feasibility_constraints['gravity_support_dot_min'] <= 0:
            raise ValueError('route support surfaces face away from gravity support')
        if parameters.get('actor_radius_m', .15) > min(self.entry_anchor.clearance_radius_m, self.exit_anchor.clearance_radius_m):
            raise ValueError('actor radius does not fit component clearance')

    def describe(self, parameters):
        raise NotImplementedError

    @property
    def parameters(self):
        return dict(self.spec.parameters)

    @property
    def entry_anchor(self):
        return self._local.entry.transformed(self.spec.transform)

    @property
    def exit_anchor(self):
        return self._local.exit.transformed(self.spec.transform)

    @property
    def travel_direction(self):
        return self.entry_anchor.direction

    @property
    def collision_geometry(self):
        return tuple(b.transformed(self.spec.transform) for b in self._local.boxes)

    @property
    def visual_geometry(self):
        # Separate Blender objects use these boxes plus bounded visual bevels.
        return tuple(b.transformed(self.spec.transform) for b in self._local.boxes)

    @property
    def bounds(self):
        return bounds(tuple(p for b in self.collision_geometry for p in b.vertices))

    @property
    def centerline(self):
        return tuple(self.spec.transform.point(p) for p in self._local.centerline)

    @property
    def feasibility_constraints(self):
        rise = max(p[2] for p in self.centerline)-self.entry_anchor.position_m[2]
        return {'backend': 'fixed-obb-sphere-mechanics-1', 'route_capable': self._local.route_capable,
                'actor_radius_m': self.parameters.get('actor_radius_m', .15),
                'minimum_entry_speed_m_s': math.sqrt(2*9.81*max(0., rise)),
                'gravity_support_dot_min': min(self.entry_anchor.surface_normal[2], self.exit_anchor.surface_normal[2]),
                'collision_representation': 'fixed_obb_union', 'collider_count': len(self._local.boxes),
                'visual_collision_discrepancy_bound_m': math.sqrt(3)*self.spec.bevel_m,
                'route_approximation_bound_m': self._local.approximation_m,
                'motion_solution_required': True, 'notes': list(self._local.notes)}

    def analytic_obstacles(self):
        return [{**b.to_dict(), 'object_id': self.spec.component_id+':'+b.part_id, 'mode': 'fixed',
                 'friction': self.spec.friction, 'restitution': self.spec.restitution} for b in self.collision_geometry]

    def build(self):
        """Return complete numerical geometry, suitable for the separate Blender adapter."""
        return self

    def build_blender(self, collection=None, palette=None):
        from .blender import build_component
        return build_component(self, collection=collection, palette=palette)

    def to_dict(self):
        return {'schema_version': VERSION, 'spec': self.spec.to_dict(), 'entry_anchor': self.entry_anchor.to_dict(),
                'exit_anchor': self.exit_anchor.to_dict(), 'travel_direction': list(self.travel_direction),
                'bounds': self.bounds, 'collision_geometry': [b.to_dict() for b in self.collision_geometry],
                'visual_geometry': [b.to_dict() for b in self.visual_geometry],
                'parameters': self.parameters, 'feasibility_constraints': self.feasibility_constraints}

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, allow_nan=False)+'\n'


def channel_segment(name, start, end, width, thickness, wall, wall_height):
    from .math3d import forward_rotation
    delta = sub(end, start)
    q = forward_rotation(delta)
    midpoint = mul(add(start, end), .5)
    transform = Transform(midpoint, q)
    length = math.dist(start, end)
    boxes = [BoxGeometry(name+'-floor', transform.point((0, 0, -thickness/2)),
                         (length/2, width/2+wall, thickness/2), q)]
    if wall:
        boxes += [BoxGeometry(name+'-wall-'+str(sign), transform.point((0, sign*(width+wall)/2, wall_height/2)),
                              (length/2, wall/2, wall_height/2), q) for sign in (-1, 1)]
    return boxes, q
