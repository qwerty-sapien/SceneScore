"""Numerical connection and full-route screening without Blender or a solver."""
from dataclasses import dataclass
import itertools
import json
import math

from modules.blender.production.validation import gap, swept_gap
from . import create_component
from .core import exact_keys, IDENTITY
from .math3d import finite, direction_angle_deg, bounds


@dataclass(frozen=True)
class ConnectionPolicy:
    distance_tolerance_m: float = .001
    maximum_direction_mismatch_deg: float = 10.
    radius_clearance_margin_m: float = .005
    maximum_joint_overlap_m: float = 0.
    joint_region_radius_m: float = .5
    available_entry_speed_m_s: float = 0.

    @classmethod
    def from_dict(cls, value):
        exact_keys(value, cls.__dataclass_fields__, 'connection policy')
        p = cls(**{k: finite(v, k) for k, v in value.items()})
        if not 0 < p.distance_tolerance_m <= .05 or not 0 <= p.maximum_direction_mismatch_deg <= 90:
            raise ValueError('connection distance must be (0,.05] m and direction tolerance 0..90 degrees')
        if not 0 <= p.radius_clearance_margin_m <= .1 or not 0 <= p.maximum_joint_overlap_m <= .1:
            raise ValueError('clearance margin/joint overlap must be within 0..0.1 m')
        if not 0 < p.joint_region_radius_m <= 1 or not 0 <= p.available_entry_speed_m_s <= 100:
            raise ValueError('joint region must be (0,1] m and entry speed 0..100 m/s')
        return p

    def to_dict(self):
        return dict(self.__dict__)


def _state(position, q=IDENTITY):
    return {'position_m': position, 'quaternion_xyzw': q}


def _overlaps(a, b, policy=None, joint=None):
    records = []
    for x, y in itertools.product(a.collision_geometry, b.collision_geometry):
        depth = -gap(x.to_dict(), x.to_dict(), y.to_dict(), y.to_dict())
        if depth <= 1e-8:
            continue
        near_joint = False
        extent = None
        if joint is not None:
            xb, yb = bounds(x.vertices), bounds(y.vertices)
            low = tuple(max(xb['minimum_m'][i], yb['minimum_m'][i]) for i in range(3))
            high = tuple(min(xb['maximum_m'][i], yb['maximum_m'][i]) for i in range(3))
            # The AABB of the intersection conservatively contains its OBB intersection.
            extent = max(math.dist(joint, p) for p in itertools.product(*zip(low, high)))
            near_joint = extent <= policy.joint_region_radius_m
        allowed = bool(policy and near_joint and depth <= policy.maximum_joint_overlap_m+1e-8)
        records.append({'parts': [x.part_id, y.part_id], 'penetration_depth_m': depth,
                        'joint_intersection_radius_bound_m': extent, 'allowed_static_weld': allowed})
    return records


def check_connection(a, b, actor_radius_m, policy=None):
    """Static weld allowances never excuse sphere penetration at the connecting seam."""
    radius = finite(actor_radius_m, 'actor_radius_m')
    if not .001 <= radius <= 10:
        raise ValueError('actor radius must be .001..10 m')
    policy = policy or ConnectionPolicy()
    policy = ConnectionPolicy.from_dict(policy.to_dict() if isinstance(policy, ConnectionPolicy) else policy)
    x, y = a.exit_anchor, b.entry_anchor
    errors = []
    def require(condition, code):
        if not condition:
            errors.append(code)
    distance = math.dist(x.position_m, y.position_m)
    angle = direction_angle_deg(x.direction, y.direction)
    capacity = min(x.clearance_radius_m, y.clearance_radius_m)
    rise = y.position_m[2]-x.position_m[2]
    min_speed = max(math.sqrt(2*9.81*max(0., rise)), b.feasibility_constraints['minimum_entry_speed_m_s'])
    require(a.feasibility_constraints['route_capable'] and b.feasibility_constraints['route_capable'], 'NOT_TRAVEL_PORT')
    require(not a.feasibility_constraints.get('terminal_only', False), 'TERMINAL_HAS_OUTGOING_CONNECTION')
    require(distance < policy.distance_tolerance_m, 'ANCHOR_DISTANCE')
    require(angle <= policy.maximum_direction_mismatch_deg+1e-8, 'DIRECTION_MISMATCH')
    require(radius+policy.radius_clearance_margin_m <= capacity+1e-9, 'ACTOR_RADIUS_CLEARANCE')
    require(all(abs(c.parameters['actor_radius_m']-radius) < 1e-9 for c in (a, b)), 'ACTOR_RADIUS_SPEC_MISMATCH')
    require(policy.available_entry_speed_m_s+1e-9 >= min_speed, 'INSUFFICIENT_HEIGHT_ENERGY')
    joint = tuple((u+v)/2 for u, v in zip(x.position_m, y.position_m))
    overlaps = _overlaps(a, b, policy, joint)
    require(all(o['allowed_static_weld'] for o in overlaps), 'ILLEGAL_COMPONENT_PENETRATION')
    sphere = {'shape': 'sphere', 'radius_m': radius}
    seam_gap = min(swept_gap(sphere, _state(x.position_m), _state(y.position_m),
                            box.to_dict(), box.to_dict(), box.to_dict())['gap_m']
                   for box in (*a.collision_geometry, *b.collision_geometry))
    require(seam_gap >= -1e-7, 'ACTOR_PENETRATES_SEAM')
    return {'from': a.spec.component_id, 'to': b.spec.component_id, 'status': 'FAILED' if errors else 'PASSED',
            'errors': errors, 'policy': policy.to_dict(), 'metrics': {'anchor_distance_m': distance,
            'direction_mismatch_deg': angle, 'available_clearance_radius_m': capacity,
            'required_clearance_radius_m': radius+policy.radius_clearance_margin_m,
            'height_change_m': rise, 'minimum_entry_speed_m_s': min_speed,
            'minimum_seam_surface_gap_m': seam_gap, 'solid_overlaps': overlaps}, 'physics_validated': False}


@dataclass
class AssembledRoute:
    components: dict
    connection_reports: list
    start_component: str
    terminal_component: str
    actor_radius_m: float

    def to_dict(self):
        return {'schema_version': 'assembled-component-route-1', 'status': 'READY_FOR_PARAMETER_SOLUTION',
                'physics_validated': False, 'actor_radius_m': self.actor_radius_m,
                'start_component': self.start_component, 'terminal_component': self.terminal_component,
                'components': [c.to_dict() for c in self.components.values()],
                'connections': self.connection_reports,
                'analytic_obstacles': [o for c in self.components.values() for o in c.analytic_obstacles()]}

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, allow_nan=False)+'\n'


class RouteValidationError(ValueError):
    def __init__(self, reports):
        self.reports = reports
        super().__init__('route rejected: '+json.dumps(reports, sort_keys=True, allow_nan=False))


def assemble_route(document):
    exact_keys(document, ['schema_version', 'actor_radius_m', 'components', 'connections', 'start_component', 'terminal_component'], 'route')
    if document['schema_version'] != 'component-route-1':
        raise ValueError('unsupported component route version')
    radius = finite(document['actor_radius_m'], 'actor_radius_m')
    if not .001 <= radius <= 10:
        raise ValueError('actor radius must be .001..10 m')
    if not isinstance(document['components'], list) or not 1 <= len(document['components']) <= 32:
        raise ValueError('route must contain 1..32 components')
    components = [create_component(spec) for spec in document['components']]
    by_id = {c.spec.component_id: c for c in components}
    if len(by_id) != len(components):
        raise ValueError('duplicate component ID')
    if any(abs(c.parameters['actor_radius_m']-radius) > 1e-9 for c in components):
        raise ValueError('every component must declare the route actor radius')
    if sum(len(c.collision_geometry) for c in components) > 128:
        raise ValueError('route exceeds analytic backend limit of 128 fixed OBBs')
    start, terminal = document['start_component'], document['terminal_component']
    if not isinstance(start, str) or not isinstance(terminal, str):
        raise ValueError('start and terminal component references must be strings')
    if start not in by_id or terminal not in by_id or not by_id[terminal].feasibility_constraints.get('terminal_only'):
        raise ValueError('route requires an existing start and terminal Catcher')
    if not isinstance(document['connections'], list) or len(document['connections']) > 31:
        raise ValueError('connections must be a list with at most 31 entries')
    outgoing, incoming, reports = {}, {}, []
    for connection in document['connections']:
        exact_keys(connection, ['from', 'to', 'policy'], 'connection')
        a, b = connection['from'], connection['to']
        if not isinstance(a, str) or not isinstance(b, str):
            raise ValueError('connection references must be strings')
        if a not in by_id or b not in by_id or a == b or a in outgoing or b in incoming:
            raise ValueError('connection references are unknown, self-connected or branching')
        outgoing[a], incoming[b] = b, a
        reports.append(check_connection(by_id[a], by_id[b], radius, connection['policy']))
    visited, node = [], start
    while node is not None:
        if node in visited:
            raise ValueError('cyclic component route')
        visited.append(node)
        node = outgoing.get(node)
    route_ids = {c.spec.component_id for c in components if c.feasibility_constraints['route_capable']}
    if visited[-1] != terminal or set(visited) != route_ids or start in incoming or terminal in outgoing:
        raise ValueError('all travel components must form one connected start-to-catcher route')
    connected_pairs = {frozenset((r['from'], r['to'])) for r in reports}
    for a, b in itertools.combinations(components, 2):
        if frozenset((a.spec.component_id, b.spec.component_id)) not in connected_pairs:
            overlaps = _overlaps(a, b)
            if overlaps:
                reports.append({'from': a.spec.component_id, 'to': b.spec.component_id, 'status': 'FAILED',
                                'errors': ['NONADJACENT_COMPONENT_PENETRATION'], 'solid_overlaps': overlaps})
    if any(r['status'] != 'PASSED' for r in reports):
        raise RouteValidationError(reports)
    return AssembledRoute(by_id, reports, start, terminal, radius)


def assemble_resolved(resolved, layout):
    """Bind A4 constraints to a proposed layout, retaining unresolved event measurements."""
    from modules.blender.planning import verify_resolved
    constraints = verify_resolved(resolved)
    route = assemble_route(layout)
    fixed = {a['id'] for a in constraints['actors'] if a['motion'] == 'fixed' and a['collision_enabled']}
    if set(route.components) != fixed:
        raise ValueError('component IDs must match every declared fixed collision actor')
    if abs(route.actor_radius_m-constraints['actor_radius_m']) > 1e-9:
        raise ValueError('layout radius contradicts resolved constraints')
    start, end = constraints['route']['start'], constraints['route']['terminal']
    if route.start_component != start['support'] or route.terminal_component != end['target']:
        raise ValueError('layout start/terminal contradicts resolved constraints')
    for point, anchor in [(start['position_m'], route.components[route.start_component].entry_anchor),
                           (end['position_m'], route.components[route.terminal_component].exit_anchor)]:
        if math.dist(point, anchor.position_m) > 1e-6:
            raise ValueError('resolved start/terminal positions do not match component sphere-center anchors')
    result = route.to_dict()
    result.update(resolved_constraints_sha256=resolved['sha256'], event_constraints=constraints['events'],
                  planning_constraints=constraints,
                  gravity_m_s2=constraints['gravity_m_s2'], sphere_material=constraints['sphere_material'],
                  initial_state=start, terminal_state=end, duration_s=constraints['duration_s'])
    result['collider_actor_map'] = {o['object_id']: key for key, c in route.components.items() for o in c.analytic_obstacles()}
    return result
