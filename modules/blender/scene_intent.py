"""Typed, strict, unmeasured authoring intent; never a production renderer input.

scene-intent-2 is a module supplement, separate from canonical 0.1 and the pack's
scene-intent-1 linter. Seconds are relative to scene start; clearance is signed
surface separation in metres. All windows are approximate half-open intervals.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, fields, is_dataclass
import json
import math
from pathlib import Path
import re
from types import UnionType
from typing import Literal, get_args, get_origin, get_type_hints

VERSION = 'scene-intent-2'
PLAN_STATUS = 'PLAN_VALID_NOT_PHYSICS_VALIDATED'
INTERACTIONS = {'collision', 'bounce', 'near_miss', 'graze', 'merge', 'release'}


class IntentValidationError(ValueError):
    """An invalid structure or contradictory/underspecified authoring plan."""


@dataclass(frozen=True)
class TimeWindow:
    start_s: float
    end_s: float


@dataclass(frozen=True)
class ClearanceIntent:
    minimum_m: float
    maximum_m: float
    target_m: float | None


@dataclass(frozen=True)
class ActorIntent:
    id: str
    role: Literal['actor', 'silent_support', 'interaction_surface', 'visible_actuator']
    shape: Literal['sphere', 'obb', 'convex_mesh', 'mesh', 'deformable']
    motion: Literal['dynamic', 'fixed', 'prescribed']
    collision_enabled: bool
    scored: bool
    sonic_identity_id: str | None


@dataclass(frozen=True)
class MechanicsScope:
    backend: Literal['fixed-obb-sphere-mechanics-1', 'native_bullet', 'prescribed_mechanism', 'other_explicit']
    model_version: str
    scope: str
    gravity_m_s2: tuple[float, float, float]
    contact_model: str
    material_model: str
    actuation_model: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class RouteStage:
    id: str
    actor_ids: tuple[str, ...]
    window: TimeWindow
    entry_intent: str
    exit_intent: str
    mechanism: str


@dataclass(frozen=True)
class SupportContactIntent:
    id: str
    kind: Literal['continuous_support']
    actor_id: str
    support_id: str
    stage_id: str
    window: TimeWindow
    evidence_required: str


@dataclass(frozen=True)
class EventIntent:
    id: str
    kind: Literal['collision', 'bounce', 'near_miss', 'graze', 'acceleration', 'deceleration', 'release', 'settle', 'merge']
    actor_ids: tuple[str, ...]
    stage_id: str
    target_window: TimeWindow
    physical_cause: str
    measurement_required: str
    clearance: ClearanceIntent | None


@dataclass(frozen=True)
class SaliencePolicy:
    minimum_gap_s: float
    maximum_duty_cycle: float
    maximum_events: int
    minimum_distinct_kinds: int
    maximum_simultaneous_events: Literal[1]
    support_contact_policy: Literal['retain_raw_do_not_count_as_salient']


@dataclass(frozen=True)
class CameraIntent:
    mode: Literal['fixed', 'tracking', 'staged']
    focus_actor_ids: tuple[str, ...]
    readable_event_ids: tuple[str, ...]
    framing_intent: str


@dataclass(frozen=True)
class EndingIntent:
    kind: Literal['supported_rest', 'supported_exit', 'continued_supported_motion']
    actor_ids: tuple[str, ...]
    support_ids: tuple[str, ...]
    window: TimeWindow
    keep_visible: bool
    reset_policy: Literal['no_teleport']
    description: str


@dataclass(frozen=True)
class ReferenceLesson:
    id: str
    source: str
    status: Literal['visual_reference', 'reconstructed_example', 'implementation_exemplar']
    lesson: str
    evidence_note: str
    source_sha256: str | None
    consumed_interval: TimeWindow | None


@dataclass(frozen=True)
class MusicHint:
    actor_id: str
    event_id: str | None
    kind: Literal['phrase_contour', 'ornament', 'space', 'harmonic_tension', 'impact_foley']
    timing: Literal['scene_time', 'approved_musical_boundary']
    intent: str
    status: Literal['PROPOSAL_REQUIRES_APPROVAL']


@dataclass(frozen=True)
class SceneIntent:
    schema_version: Literal['scene-intent-2']
    status: Literal['DESIGN_INTENT_NOT_MEASURED']
    id: str
    duration_s: float
    clock: Literal['scene_seconds_zero_at_start']
    mechanics: MechanicsScope
    actors: tuple[ActorIntent, ...]
    route_stages: tuple[RouteStage, ...]
    support_contacts: tuple[SupportContactIntent, ...]
    events: tuple[EventIntent, ...]
    event_order: tuple[str, ...]
    salience_policy: SaliencePolicy
    camera: CameraIntent
    ending: EndingIntent
    reference_lessons: tuple[ReferenceLesson, ...]
    music_hints: tuple[MusicHint, ...]

    @classmethod
    def from_dict(cls, value):
        intent = _decode(cls, value, '$')
        _validate(intent)
        return intent

    @classmethod
    def from_json(cls, text):
        def unique_object(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise IntentValidationError(f'duplicate JSON key: {key}')
                value[key] = item
            return value
        try:
            return cls.from_dict(json.loads(text, object_pairs_hook=unique_object))
        except (ValueError, TypeError) as error:
            raise IntentValidationError(str(error)) from error

    def to_dict(self):
        value = _encode(self)
        # Validate direct dataclass construction as well as parsed input.
        self.from_dict(value)
        return value

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, allow_nan=False) + '\n'

    def validation_warnings(self):
        return _validate(self.from_dict(_encode(self)))


def _decode(hint, value, path):
    """Strict JSON-to-dataclass boundary: no coercion of strings, bools or extras."""
    origin, args = get_origin(hint), get_args(hint)
    if origin is Literal:
        if not any(type(value) is type(item) and value == item for item in args):
            raise IntentValidationError(f'{path}: expected one of {args}')
    elif origin is UnionType:
        for option in args:
            try:
                return _decode(option, value, path)
            except IntentValidationError:
                pass
        raise IntentValidationError(f'{path}: invalid optional value')
    elif origin is tuple:
        if not isinstance(value, (list, tuple)):
            raise IntentValidationError(f'{path}: expected array')
        variable = len(args) == 2 and args[1] is Ellipsis
        if not variable and len(value) != len(args):
            raise IntentValidationError(f'{path}: expected {len(args)} elements')
        return tuple(_decode(args[0] if variable else args[i], item, f'{path}[{i}]') for i, item in enumerate(value))
    elif is_dataclass(hint):
        if not isinstance(value, dict):
            raise IntentValidationError(f'{path}: expected object')
        if not all(isinstance(key, str) for key in value):
            raise IntentValidationError(f'{path}: object keys must be strings')
        hints = get_type_hints(hint)
        if set(value) != set(hints):
            raise IntentValidationError(f'{path}: missing {sorted(set(hints)-set(value))}; unknown {sorted(set(value)-set(hints))}')
        return hint(**{key: _decode(kind, value[key], f'{path}.{key}') for key, kind in hints.items()})
    elif hint is float:
        try:
            finite = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise IntentValidationError(f'{path}: expected finite number, not boolean')
        return float(value)
    elif hint is str:
        if not isinstance(value, str) or not value.strip():
            raise IntentValidationError(f'{path}: expected nonempty string')
    elif hint is type(None):
        if value is not None:
            raise IntentValidationError(f'{path}: expected null')
    elif type(value) is not hint:
        raise IntentValidationError(f'{path}: expected {hint.__name__}')
    return value


def _encode(value):
    if is_dataclass(value):
        return {field.name: _encode(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_encode(item) for item in value]
    return value


def _require(condition, message):
    if not condition:
        raise IntentValidationError(message)


def _ids(items, label, *, nonempty=True):
    _require(bool(items) or not nonempty, f'{label}: must not be empty')
    values = [item.id for item in items]
    _require(all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', v) for v in values), f'{label}: invalid persistent ID')
    _require(len(set(values)) == len(values), f'{label}: duplicate ID')
    return {item.id: item for item in items}


def _refs(values, known, label, *, nonempty=True):
    _require(bool(values) or not nonempty, f'{label}: must not be empty')
    _require(len(set(values)) == len(values), f'{label}: duplicate reference')
    _require(set(values) <= set(known), f'{label}: unknown reference')


def _window(window, duration, label):
    _require(0 <= window.start_s < window.end_s <= duration, f'{label}: window must be ordered inside duration')


def _inside(window, outer, label):
    _require(outer.start_s <= window.start_s < window.end_s <= outer.end_s, f'{label}: window outside route stage')


def _overlap(a, b):
    return max(a.start_s, b.start_s) < min(a.end_s, b.end_s)


def _validate(plan):
    warnings = []
    _require(0 < plan.duration_s <= 30, 'duration_s must be in (0, 30]')
    actors = _ids(plan.actors, 'actors')
    stages = _ids(plan.route_stages, 'route_stages')
    events = _ids(plan.events, 'events')
    supports = _ids(plan.support_contacts, 'support_contacts', nonempty=False)
    _require(not set(events).intersection(supports), 'support contacts and salient events must have distinct IDs')
    voices = []
    for actor in plan.actors:
        _require(actor.scored == (actor.sonic_identity_id is not None), f'{actor.id}: scored actor needs a persistent voice; unscored actor must have none')
        _require(not (actor.role == 'silent_support' and actor.scored), f'{actor.id}: silent support cannot own a voice')
        if actor.sonic_identity_id:
            voices.append(actor.sonic_identity_id)
    _require(len(set(voices)) == len(voices), 'actors must have distinct persistent sonic identities')
    moving = [a for a in plan.actors if a.motion != 'fixed']
    _require(bool(moving), 'at least one moving actor required')
    mechanics = plan.mechanics
    _require(bool(mechanics.limitations), 'mechanics limitations must be explicit')
    if mechanics.backend == 'fixed-obb-sphere-mechanics-1':
        _require(mechanics.model_version == mechanics.backend, 'analytic model version must match its declared scope')
        _require(len(moving) == 1 and moving[0].motion == 'dynamic' and moving[0].shape == 'sphere'
                 and moving[0].collision_enabled, 'fixed-OBB scope requires exactly one dynamic colliding sphere')
        _require(all(a.shape == 'obb' for a in plan.actors if a.motion == 'fixed' and a.collision_enabled),
                 'fixed-OBB scope requires fixed OBB colliders')
    elif mechanics.backend == 'prescribed_mechanism':
        _require(all(a.motion == 'prescribed' for a in moving), 'prescribed scope cannot certify free dynamic actors')
    elif mechanics.backend == 'native_bullet':
        warnings.append('NATIVE_CALIBRATION_REQUIRED: historical native controls failed; this intent does not repair them.')
    else:
        warnings.append('UNIMPLEMENTED_MECHANICS_SCOPE: other_explicit needs a tested backend and adapter before execution.')

    previous_end = 0.0
    for stage in plan.route_stages:
        _refs(stage.actor_ids, actors, stage.id)
        _window(stage.window, plan.duration_s, stage.id)
        _require(abs(stage.window.start_s - previous_end) < 1e-9, 'route stages must be contiguous and ordered from scene zero')
        previous_end = stage.window.end_s
    _require(abs(previous_end - plan.duration_s) < 1e-9, 'route stages must cover the complete duration')
    for contact in plan.support_contacts:
        _refs((contact.actor_id, contact.support_id), actors, contact.id)
        _require(contact.stage_id in stages, f'{contact.id}: unknown stage')
        stage = stages[contact.stage_id]
        _refs((contact.actor_id, contact.support_id), stage.actor_ids, contact.id)
        _window(contact.window, plan.duration_s, contact.id)
        _inside(contact.window, stage.window, contact.id)
        _require(actors[contact.actor_id].motion != 'fixed', f'{contact.id}: support actor must move')
        _require(actors[contact.support_id].role in {'silent_support', 'interaction_surface', 'visible_actuator'},
                 f'{contact.id}: support must have an explicit support/surface/actuator role')
        _require(all(actors[a].collision_enabled for a in (contact.actor_id, contact.support_id)),
                 f'{contact.id}: support requires physical colliders')
    for event in plan.events:
        _refs(event.actor_ids, actors, event.id)
        _require(event.stage_id in stages, f'{event.id}: unknown stage')
        stage = stages[event.stage_id]
        _refs(event.actor_ids, stage.actor_ids, event.id)
        _window(event.target_window, plan.duration_s, event.id)
        _inside(event.target_window, stage.window, event.id)
        _require(any(actors[a].motion != 'fixed' for a in event.actor_ids), f'{event.id}: event needs a moving actor')
        _require(len(event.actor_ids) == (2 if event.kind in INTERACTIONS else 1), f'{event.id}: wrong event participant count')
        if event.kind in INTERACTIONS:
            _require(all(actors[a].collision_enabled for a in event.actor_ids), f'{event.id}: interaction requires physical colliders')
        if event.kind == 'near_miss':
            c = event.clearance
            _require(c is not None, f'{event.id}: near miss requires a physical clearance range in metres')
            _require(0 < c.minimum_m <= c.maximum_m, f'{event.id}: clearance must be positive and ordered')
            _require(c.target_m is None or c.minimum_m <= c.target_m <= c.maximum_m, f'{event.id}: clearance target outside range')
            for contact in plan.support_contacts:
                _require(set(event.actor_ids) != {contact.actor_id, contact.support_id}
                         or not _overlap(event.target_window, contact.window),
                         f'{event.id}: near miss contradicts continuous support contact')
        else:
            _require(event.clearance is None, f'{event.id}: clearance only belongs to a near miss')
        if event.kind == 'merge':
            _require(mechanics.backend == 'other_explicit', f'{event.id}: merge is unsupported by current rigid-body scopes')
            warnings.append(f'{event.id}: UNIMPLEMENTED_EVENT_MODEL; adhesion/deformation must be independently implemented and tested.')

    _refs(plan.event_order, events, 'event_order')
    _require(set(plan.event_order) == set(events), 'event_order must name every salient event exactly once')
    policy = plan.salience_policy
    _require(policy.minimum_gap_s >= 0 and 0 < policy.maximum_duty_cycle <= 1, 'invalid salience spacing/duty policy')
    _require(1 <= policy.minimum_distinct_kinds <= policy.maximum_events <= 32, 'invalid salience count policy')
    _require(len(events) <= policy.maximum_events, 'too many salient events')
    _require(len({e.kind for e in plan.events}) >= policy.minimum_distinct_kinds, 'insufficient event-kind diversity')
    ordered = [events[e] for e in plan.event_order]
    for previous, current in zip(ordered, ordered[1:]):
        _require(current.target_window.start_s - previous.target_window.end_s >= policy.minimum_gap_s - 1e-9,
                 f'{previous.id} -> {current.id}: contradictory event order, overlap or insufficient gap')
    duty = sum(e.target_window.end_s-e.target_window.start_s for e in plan.events) / plan.duration_s
    _require(duty <= policy.maximum_duty_cycle + 1e-9, 'salient-event duty cycle exceeds policy')

    _refs(plan.camera.focus_actor_ids, actors, 'camera focus')
    _refs(plan.camera.readable_event_ids, events, 'camera readable events')
    _require(set(plan.camera.readable_event_ids) == set(events), 'camera must intend coverage of every salient event')
    ending = plan.ending
    _window(ending.window, plan.duration_s, 'ending')
    _inside(ending.window, plan.route_stages[-1].window, 'ending')
    _require(ending.window.end_s == plan.duration_s, 'ending must reach the scene endpoint')
    _require(ending.window.start_s >= ordered[-1].target_window.end_s, 'ending must follow the last salient event')
    _refs(ending.actor_ids, actors, 'ending actors')
    _refs(ending.support_ids, actors, 'ending supports')
    _refs(ending.actor_ids + ending.support_ids, plan.route_stages[-1].actor_ids, 'ending stage')
    _require(all(actors[a].motion != 'fixed' for a in ending.actor_ids), 'ending must identify moving actors')
    _require(all(actors[a].role in {'silent_support', 'interaction_surface', 'visible_actuator'}
                 and actors[a].collision_enabled for a in ending.support_ids), 'ending requires physical supports')
    if not ending.keep_visible:
        warnings.append('ENDING_VISIBILITY_UNRESOLVED: ending intentionally permits leaving the frame; review required.')

    _ids(plan.reference_lessons, 'reference_lessons', nonempty=False)
    if not plan.reference_lessons:
        warnings.append('NO_REFERENCE_LESSONS: no reference lessons supplied.')
    for reference in plan.reference_lessons:
        if reference.source_sha256 is not None:
            _require(re.fullmatch('[0-9a-f]{64}', reference.source_sha256), f'{reference.id}: invalid reference SHA-256')
        else:
            warnings.append(f'{reference.id}: REFERENCE_UNBOUND; source bytes were not identified.')
        if reference.status == 'implementation_exemplar':
            _require(reference.source_sha256 is not None, f'{reference.id}: implementation exemplar requires bound source evidence')
        if reference.consumed_interval is not None:
            _window(reference.consumed_interval, float('inf'), reference.id)
    for hint in plan.music_hints:
        _require(hint.actor_id in actors and actors[hint.actor_id].scored, 'music hints require a scored persistent actor')
        if hint.event_id is not None:
            _require(hint.event_id in events and hint.actor_id in events[hint.event_id].actor_ids, 'music hint event/actor mismatch')
        if hint.kind == 'impact_foley':
            _require(hint.event_id is not None and events[hint.event_id].kind in {'collision', 'bounce', 'graze'},
                     'impact Foley requires a contact event; a near miss is not impact')
            _require(hint.timing == 'scene_time', 'physical Foley must retain scene-time onset')
    return tuple(warnings)


def json_schema():
    """JSON Schema for structure; SceneIntent.from_dict also checks plan semantics."""
    definitions = {}
    def describe(hint):
        origin, args = get_origin(hint), get_args(hint)
        if origin is Literal:
            return {'enum': list(args), 'type': 'integer' if type(args[0]) is int else 'string'}
        if origin is UnionType:
            return {'anyOf': [describe(kind) for kind in args]}
        if origin is tuple:
            if len(args) == 2 and args[1] is Ellipsis:
                return {'type': 'array', 'items': describe(args[0])}
            return {'type': 'array', 'prefixItems': [describe(kind) for kind in args], 'items': False,
                    'minItems': len(args), 'maxItems': len(args)}
        if is_dataclass(hint):
            if hint.__name__ not in definitions:
                hints = get_type_hints(hint)
                definitions[hint.__name__] = {'type': 'object', 'additionalProperties': False,
                                             'required': list(hints), 'properties': {k: describe(v) for k, v in hints.items()}}
            return {'$ref': '#/$defs/' + hint.__name__}
        return {str: {'type': 'string', 'minLength': 1}, float: {'type': 'number'}, int: {'type': 'integer'},
                bool: {'type': 'boolean'}, type(None): {'type': 'null'}}[hint]
    root = describe(SceneIntent)
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': VERSION,
            'description': 'Unmeasured intent only. Run SceneIntent.from_dict for semantic validation.',
            **root, '$defs': definitions}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('intent', type=Path, nargs='?')
    parser.add_argument('--schema', action='store_true')
    args = parser.parse_args(argv)
    if args.schema:
        print(json.dumps(json_schema(), indent=2))
        return 0
    if args.intent is None:
        parser.error('intent path or --schema required')
    try:
        intent = SceneIntent.from_json(args.intent.read_text())
        print(json.dumps({'status': PLAN_STATUS, 'warnings': intent.validation_warnings(), 'physics_validated': False}, indent=2))
        return 0
    except (OSError, IntentValidationError) as error:
        print(json.dumps({'status': 'PLAN_INVALID', 'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
