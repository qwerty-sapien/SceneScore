"""Authoring-only synthetic plans; no Blender, motion or human approval evidence."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

from modules.blender.scene_intent import (
    SceneIntent, IntentValidationError, json_schema,
)

FIXTURES = Path(__file__).resolve().parents[1]/'fixtures'


@pytest.fixture
def plan():
    return json.loads((FIXTURES/'scene-intent-2.example.json').read_text())


def test_typed_serialization_is_stable_and_unmeasured(plan):
    intent = SceneIntent.from_dict(plan)
    assert intent.actors[0].sonic_identity_id == 'voice:marble'
    assert intent.events[2].clearance.target_m == .035
    assert SceneIntent.from_json(intent.to_json()) == intent
    assert SceneIntent.from_json(intent.to_json()).to_json() == intent.to_json()
    assert intent.to_dict() == plan
    assert intent.validation_warnings() == ()
    assert intent.status == 'DESIGN_INTENT_NOT_MEASURED'
    with pytest.raises(FrozenInstanceError):
        intent.duration_s = 10
    with pytest.raises(IntentValidationError):
        replace(intent, duration_s=float('nan')).to_json()


def test_serialized_json_schema_is_current_and_accepts_example(plan):
    schema = json_schema()
    assert json.loads((FIXTURES/'scene-intent-2.schema.json').read_text()) == schema
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(plan)
    plan['events'][0]['extra'] = 1
    assert list(Draft202012Validator(schema).iter_errors(plan))


@pytest.mark.parametrize(('path', 'value'), [
    (('schema_version',), 'scene-intent-1'),
    (('status',), 'APPROVED'),
    (('duration_s',), True),
    (('duration_s',), float('inf')),
    (('duration_s',), 0),
    (('duration_s',), 31),
    (('events', 0, 'kind'), 'teleport'),
    (('events', 0, 'kind'), 'continuous_support'),
    (('events', 0, 'actor_ids'), ['unknown']),
    (('events', 1, 'actor_ids'), ['marble']),
    (('events', 1, 'actor_ids'), ['marble', 'marble']),
    (('events', 0, 'actor_ids'), ['ramp']),
    (('events', 0, 'stage_id'), 'unknown'),
    (('events', 0, 'physical_cause'), '  '),
    (('events', 0, 'measurement_required'), ''),
    (('events', 0, 'target_window', 'end_s'), 1),
    (('events', 0, 'target_window', 'start_s'), float('nan')),
    (('events', 0, 'target_window', 'end_s'), 5),
    (('events', 2, 'clearance'), None),
    (('events', 2, 'clearance', 'minimum_m'), 0),
    (('events', 2, 'clearance', 'maximum_m'), .01),
    (('events', 2, 'clearance', 'target_m'), .2),
    (('events', 2, 'clearance', 'target_m'), float('inf')),
    (('events', 2, 'clearance', 'minimum_m'), True),
    (('event_order',), ['clearance', 'redirect', 'sustained-speedup']),
    (('event_order',), ['sustained-speedup', 'redirect']),
    (('event_order',), ['redirect', 'redirect', 'clearance']),
    (('route_stages', 1, 'window', 'start_s'), 3),
    (('route_stages', 1, 'window', 'start_s'), 5),
    (('route_stages', 0, 'actor_ids'), ['marble']),
    (('mechanics', 'backend'), 'magic'),
    (('mechanics', 'limitations'), []),
    (('mechanics', 'gravity_m_s2'), [0, 0]),
    (('mechanics', 'model_version'), 'invented-version'),
    (('actors', 3, 'motion'), 'prescribed'),
    (('actors', 1, 'shape'), 'sphere'),
    (('actors', 0, 'sonic_identity_id'), None),
    (('actors', 2, 'sonic_identity_id'), 'voice:marble'),
    (('actors', 0, 'collision_enabled'), False),
    (('salience_policy', 'maximum_simultaneous_events'), True),
    (('salience_policy', 'maximum_events'), 2),
    (('salience_policy', 'maximum_events'), 4.0),
    (('salience_policy', 'maximum_duty_cycle'), .01),
    (('salience_policy', 'minimum_gap_s'), 10),
    (('salience_policy', 'minimum_distinct_kinds'), 4),
    (('camera', 'readable_event_ids'), ['redirect']),
    (('camera', 'focus_actor_ids'), ['unknown']),
    (('ending', 'window', 'end_s'), 15),
    (('ending', 'support_ids'), ['unknown']),
    (('music_hints', 0, 'actor_id'), 'ramp'),
    (('music_hints', 0, 'kind'), 'impact_foley'),
    (('music_hints', 0, 'status'), 'APPROVED'),
    (('music_hints', 0, 'event_id'), 'unknown'),
    (('reference_lessons', 0, 'source_sha256'), 'not-a-hash'),
])
def test_invalid_or_contradictory_definitions_rejected(plan, path, value):
    target = plan
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(IntentValidationError):
        SceneIntent.from_dict(plan)


@pytest.mark.parametrize('invalid', [None, [], True, 'not an object'])
def test_invalid_root_rejected(invalid):
    with pytest.raises(IntentValidationError):
        SceneIntent.from_dict(invalid)


def test_missing_and_unknown_fields_are_not_silently_dropped(plan):
    del plan['events'][1]['measurement_required']
    with pytest.raises(IntentValidationError, match='missing'):
        SceneIntent.from_dict(plan)
    plan['events'][1]['measurement_required'] = 'Measure contact and outgoing motion.'
    plan['events'][1]['forced_velocity'] = [1, 0, 0]
    with pytest.raises(IntentValidationError, match='unknown'):
        SceneIntent.from_dict(plan)


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(IntentValidationError, match='duplicate JSON key'):
        SceneIntent.from_json('{"id":"one","id":"two"}')


def test_support_intervals_do_not_consume_salient_duty_cycle(plan):
    # The ramp alone exceeds the salience limit, but is continuous raw support.
    plan['salience_policy']['maximum_duty_cycle'] = .12
    intent = SceneIntent.from_dict(plan)
    assert len(intent.support_contacts) == 2 and len(intent.events) == 3


def test_near_miss_rejects_simultaneous_support_for_same_pair(plan):
    contact = plan['support_contacts'][0]
    contact.update(support_id='post', stage_id='clearance-route', window={'start_s': 10, 'end_s': 11})
    with pytest.raises(IntentValidationError, match='contradicts continuous support'):
        SceneIntent.from_dict(plan)
    # Later contact is a different episode; it does not contradict the miss window.
    contact['window'] = {'start_s': 11, 'end_s': 12}
    SceneIntent.from_dict(plan)


def test_range_only_clearance_is_supported(plan):
    plan['events'][2]['clearance']['target_m'] = None
    assert SceneIntent.from_dict(plan).events[2].clearance.target_m is None


def test_contact_event_cannot_claim_positive_clearance(plan):
    plan['events'][1]['clearance'] = plan['events'][2]['clearance']
    with pytest.raises(IntentValidationError, match='only belongs to a near miss'):
        SceneIntent.from_dict(plan)


def test_overlapping_salient_events_are_not_double_counted(plan):
    plan['events'][1].update(stage_id='descent', target_window={'start_s': 2.5, 'end_s': 3.2})
    plan['route_stages'][0]['actor_ids'].append('deflector')
    with pytest.raises(IntentValidationError, match='overlap'):
        SceneIntent.from_dict(plan)


def test_silent_support_cannot_own_voice(plan):
    plan['actors'][1].update(scored=True, sonic_identity_id='voice:ramp')
    with pytest.raises(IntentValidationError, match='silent support'):
        SceneIntent.from_dict(plan)


def test_extra_dynamic_body_exceeds_analytic_scope(plan):
    plan['actors'].append({**plan['actors'][0], 'id': 'second-ball', 'sonic_identity_id': 'voice:second'})
    with pytest.raises(IntentValidationError, match='exactly one'):
        SceneIntent.from_dict(plan)


def test_unsupported_merge_requires_explicit_separate_model_and_warning(plan):
    plan['events'][1]['kind'] = 'merge'
    with pytest.raises(IntentValidationError, match='unsupported'):
        SceneIntent.from_dict(plan)
    plan['mechanics'].update(backend='other_explicit', model_version='unimplemented-adhesion-study',
                             contact_model='Proposed adhesion/deformation model, not implemented.')
    warnings = SceneIntent.from_dict(plan).validation_warnings()
    assert any('UNIMPLEMENTED_MECHANICS_SCOPE' in warning for warning in warnings)
    assert any('UNIMPLEMENTED_EVENT_MODEL' in warning for warning in warnings)


def test_native_intent_warns_without_repairing_or_promoting_backend(plan):
    plan['mechanics'].update(backend='native_bullet', model_version='Blender-native-study')
    assert any('NATIVE_CALIBRATION_REQUIRED' in w for w in SceneIntent.from_dict(plan).validation_warnings())


def test_missing_references_and_visibility_are_explicit_warnings(plan):
    plan['reference_lessons'] = []
    plan['ending']['keep_visible'] = False
    warnings = SceneIntent.from_dict(plan).validation_warnings()
    assert any('NO_REFERENCE_LESSONS' in w for w in warnings)
    assert any('ENDING_VISIBILITY_UNRESOLVED' in w for w in warnings)


def test_unbound_exemplar_is_rejected_but_visual_note_warned(plan):
    plan['reference_lessons'][0]['source_sha256'] = None
    assert any('REFERENCE_UNBOUND' in w for w in SceneIntent.from_dict(plan).validation_warnings())
    plan['reference_lessons'][0]['status'] = 'implementation_exemplar'
    with pytest.raises(IntentValidationError, match='bound source'):
        SceneIntent.from_dict(plan)


def test_foley_proposal_requires_contact_and_scene_time(plan):
    hint = plan['music_hints'][0]
    hint.update(event_id='redirect', kind='impact_foley', timing='approved_musical_boundary')
    with pytest.raises(IntentValidationError, match='scene-time'):
        SceneIntent.from_dict(plan)
    hint['timing'] = 'scene_time'
    assert SceneIntent.from_dict(plan).music_hints[0].status == 'PROPOSAL_REQUIRES_APPROVAL'


def test_validation_cli_reports_plan_only_and_nonzero_for_failure(tmp_path, plan):
    fixture = tmp_path/'plan.json'
    fixture.write_text(json.dumps(plan))
    command = [sys.executable, '-m', 'modules.blender.scene_intent', str(fixture)]
    valid = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert valid.returncode == 0
    result = json.loads(valid.stdout)
    assert result['status'] == 'PLAN_VALID_NOT_PHYSICS_VALIDATED' and result['physics_validated'] is False
    plan['event_order'].reverse()
    fixture.write_text(json.dumps(plan))
    invalid = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert invalid.returncode == 1 and json.loads(invalid.stdout)['status'] == 'PLAN_INVALID'
