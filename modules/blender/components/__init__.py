"""Reusable, Blender-independent fixed mechanism components."""
from .core import Component, ComponentSpec, Transform, Anchor
from .guides import Ramp, StraightChannel, CurvedChannel
from .transitions import DropTransition, Catcher
from .obstacles import FixedDeflector, ClearancePost
from .structures import Platform, SupportFrame

REGISTRY = {cls.__name__: cls for cls in (Ramp, StraightChannel, CurvedChannel, DropTransition,
            FixedDeflector, ClearancePost, Catcher, Platform, SupportFrame)}
__all__ = ['Component', 'ComponentSpec', 'Transform', 'Anchor', 'create_component', 'component_spec', *REGISTRY]


def component_spec(component_id, kind, *, parameters=None, transform=None, material_role='structure', bevel_m=0.):
    """Canonical spec template; anchors may be asserted explicitly after evaluation."""
    return {'component_id': component_id, 'type': kind, 'transform': (transform or Transform()).to_dict(),
            'entry_anchor': None, 'exit_anchor': None, 'parameters': parameters or {},
            'collision': {'mode': 'fixed', 'shape': 'obb_union', 'friction': .35, 'restitution': .55},
            'visual': {'bevel_m': bevel_m}, 'material_role': material_role}


def create_component(spec):
    spec = ComponentSpec.from_dict(spec.to_dict() if isinstance(spec, ComponentSpec) else spec)
    if spec.type not in REGISTRY:
        raise ValueError('unsupported component type: '+spec.type)
    return REGISTRY[spec.type](spec).build()
