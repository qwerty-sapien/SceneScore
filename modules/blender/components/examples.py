"""Small serialized assembly fixture; this is not a solved animation."""
import math
from . import component_spec, create_component, Transform
from .connections import ConnectionPolicy
from .math3d import forward_rotation, qmul, axis_angle, rotate, sub


def spatial_route_spec():
    """Elevation loss, curved redirection and depth travel into a lower catcher."""
    slope = forward_rotation((2., 0., -.5))
    turned = qmul(slope, axis_angle((0., 0., 1.), math.pi/2))
    specs = [component_spec('ramp', 'Ramp', transform=Transform((0., 0., 3.)))]
    for name, kind, orientation, parameters in [
        ('approach', 'StraightChannel', slope, {'length_m': 1.}),
        ('deflector', 'CurvedChannel', slope, {}),
        ('post', 'StraightChannel', turned, {'length_m': 1.}),
        ('catcher', 'Catcher', turned, {}),
    ]:
        previous = create_component(specs[-1])
        local = create_component(component_spec(name, kind, parameters=parameters))
        origin = sub(previous.exit_anchor.position_m, rotate(orientation, local.entry_anchor.position_m))
        specs.append(component_spec(name, kind, parameters=parameters, transform=Transform(origin, orientation)))
    policy = ConnectionPolicy(maximum_joint_overlap_m=.06, joint_region_radius_m=.6).to_dict()
    return {'schema_version': 'component-route-1', 'actor_radius_m': .15, 'components': specs,
            'start_component': 'ramp', 'terminal_component': 'catcher',
            'connections': [{'from': a['component_id'], 'to': b['component_id'], 'policy': dict(policy)}
                            for a, b in zip(specs, specs[1:])]}
