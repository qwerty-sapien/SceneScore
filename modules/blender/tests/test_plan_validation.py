"""Synthetic feasibility plans; passing is not simulated physical evidence."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from modules.blender.planning import validate_plan, verify_resolved
from modules.blender.planning.io import load_plan
from modules.blender.planning.contracts import SCHEMA

FIXTURES = Path(__file__).resolve().parents[1]/'fixtures'


@pytest.fixture
def plan():
    return json.loads((FIXTURES/'scene-feasibility-plan.example.json').read_text())


def test_valid_plan_has_six_answers_and_consumable_constraints(plan):
    report, resolved = validate_plan(plan)
    assert report['status'] == 'PASSED' and report['physics_validated'] is False
    assert len(report['answers']) == 6 and all(v == 'YES_AT_PLANNING_LEVEL' for v in report['answers'].values())
    constraints = verify_resolved(json.loads(json.dumps(resolved)))
    assert constraints['dynamic_actor'] == 'marble'
    assert constraints['events'][1]['success_all'][1]['metric'] == 'heading_change_deg'
    assert constraints['events'][2]['success_all'][0]['unit'] == 'm'
    assert not constraints['events'][2]['foley_eligible']
    assert all(e['emit_once_per_episode'] for e in constraints['events'])
    assert constraints['support_contact_music_policy'] == 'retain_raw_do_not_emit_per_sample'
    assert validate_plan(plan) == (report, resolved)
    assert json.loads((FIXTURES/'scene-feasibility-plan.schema.json').read_text()) == SCHEMA


@pytest.mark.parametrize(('path', 'value', 'reason'), [
    (('events', 0, 'after'), 'clearance', 'EVENT_ORDER_CONTRADICTION'),
    (('events', 1, 'after'), 'redirect', 'EVENT_ORDER_CONTRADICTION'),
    (('events', 1, 'after'), 'ghost', 'EVENT_ORDER_CONTRADICTION'),
    (('events', 1, 'actor'), 'ramp', 'EVENT_ACTOR_MISMATCH'),
    (('events', 1, 'target'), 'ghost', 'EVENT_TARGET_MISMATCH'),
    (('events', 1, 'time_window'), [2.1, 2.6], 'EVENT_WINDOW_CONTRADICTION'),
    (('events', 0, 'success_condition'), {}, 'UNMEASURABLE_EVENT'),
    (('events', 0, 'success_condition'), {'speed_gain_min': -.4}, 'UNMEASURABLE_EVENT'),
    (('events', 0, 'success_condition'), {'speed_gain_min': True}, 'INVALID_STRUCTURE'),
    (('events', 2, 'success_condition'), {}, 'UNMEASURABLE_EVENT'),
    (('events', 2, 'success_condition'), {'surface_clearance_pixels': {'min': 10, 'max': 20}}, 'INVALID_STRUCTURE'),
    (('events', 2, 'success_condition'), {'surface_clearance_m': {'min': 0, 'max': .05}}, 'UNMEASURABLE_EVENT'),
    (('events', 2, 'success_condition'), {'surface_clearance_m': {'min': .06, 'max': .02}}, 'UNMEASURABLE_EVENT'),
    (('events', 2, 'success_condition'), {'surface_clearance_m': {'min': .01, 'max': .1}}, 'CLEARANCE_CONTRADICTION'),
    (('events', 1, 'success_condition'), {'target_contact': False}, 'UNMEASURABLE_EVENT'),
    (('events', 1, 'failure_conditions'), ['wrong_target'], 'FAILURE_CRITERIA_MISSING'),
    (('events', 0, 'type'), 'continuous_rolling_contact', 'UNSUPPORTED_EVENT'),
    (('events', 1, 'type'), 'soft_body_merge', 'UNSUPPORTED_EVENT'),
    (('events', 1, 'type'), 'fluid_coalescence', 'UNSUPPORTED_EVENT'),
    (('motion_contract', 'trajectory_source'), 'manual_keyframes', 'TRAJECTORY_OVERRIDE'),
    (('motion_contract', 'post_release_animation'), 'manual', 'TRAJECTORY_OVERRIDE'),
    (('motion_contract', 'teleportation'), True, 'HIDDEN_TELEPORT_OR_CONTROL'),
    (('motion_contract', 'overrides_after_release'), ['motor_impulse'], 'HIDDEN_TELEPORT_OR_CONTROL'),
    (('motion_contract', 'actor_radius_m'), 0, 'INVALID_ACTOR_RADIUS'),
    (('route', 'start', 'support'), 'ghost', 'UNDEFINED_START'),
    (('route', 'terminal', 'target'), 'ghost', 'UNDEFINED_TERMINAL'),
    (('route', 'terminal'), None, 'INVALID_STRUCTURE'),
    (('route', 'stages', 1, 'position_m'), [0, 0, 100], 'INSUFFICIENT_GRAVITATIONAL_ENERGY'),
    (('events', 0, 'success_condition'), {'speed_gain_min': 100}, 'INFEASIBLE_SPEED_GAIN'),
])
def test_invalid_plans_fail_with_explicit_reasons(plan, path, value, reason):
    current = plan
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    report, resolved = validate_plan(plan)
    assert report['status'] == 'FAILED'
    assert reason in {e['code'] for e in report['errors']}
    assert resolved['status'] == 'BLOCKED' and resolved['constraints'] is None


def test_two_dynamic_bodies_and_moving_obstacles_are_rejected(plan):
    second = copy.deepcopy(plan['intent']['actors'][0])
    second.update(id='second', sonic_identity_id='voice:second')
    plan['intent']['actors'].append(second)
    report, _ = validate_plan(plan)
    assert report['status'] == 'FAILED' and 'exactly one' in str(report['errors'])
    plan['intent']['actors'].pop()
    plan['intent']['actors'][3]['motion'] = 'prescribed'
    assert validate_plan(plan)[0]['status'] == 'FAILED'
    plan['intent']['mechanics']['backend'] = 'native_bullet'
    report, _ = validate_plan(plan)
    assert 'UNSUPPORTED_MECHANICS' in {e['code'] for e in report['errors']}


def test_support_contact_is_not_repeated_salience(plan):
    report, resolved = validate_plan(plan)
    assert report['metrics']['salient_duty_cycle'] < .12
    assert len(resolved['constraints']['continuous_support']) == 2
    plan['events'].append(copy.deepcopy(plan['events'][1]))
    assert validate_plan(plan)[0]['status'] == 'FAILED'


def test_all_soft_warnings_and_no_input_mutation(plan):
    for stage in plan['route']['stages']:
        stage['position_m'] = [1, 0, 3]
    plan['route']['terminal']['position_m'] = [5, 0, 3]
    plan['route']['start']['position_m'] = [0, 0, 4]
    plan['intent']['ending']['keep_visible'] = False
    plan['intent']['camera']['readable_event_ids'] = ['sustained-speedup']
    original = copy.deepcopy(plan)
    report, resolved = validate_plan(plan)
    assert report['status'] == 'PASSED'
    codes = {w['code'] for w in report['warnings']}
    assert {'NEARLY_PLANAR_ROUTE', 'EVENTS_SPATIALLY_CLUSTERED', 'UNIFORM_EVENT_SPACING',
            'VISUALLY_WEAK_ENDING', 'CAMERA_INTERACTION_HIDDEN'} <= codes
    assert plan == original and resolved['source_plan'] == original


def test_json_yaml_cli_and_failed_outputs_are_never_stale(tmp_path, plan):
    source = tmp_path/'scene_intent.yaml'
    source.write_text(yaml.safe_dump(plan, sort_keys=False))
    assert load_plan(source) == plan
    out = tmp_path/'valid'
    command = [sys.executable, '-m', 'modules.blender.planning', str(source), '--out', str(out)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert verify_resolved(json.loads((out/'resolved_constraints.json').read_text()))
    original = (out/'resolved_constraints.json').read_bytes()
    source.write_text('{broken')
    assert subprocess.run(command, capture_output=True, timeout=15).returncode != 0
    assert (out/'resolved_constraints.json').read_bytes() == original
    failed = tmp_path/'failed'
    result = subprocess.run(command[:-1]+[str(failed)], capture_output=True, timeout=15)
    assert result.returncode == 1
    assert json.loads((failed/'resolved_constraints.json').read_text())['constraints'] is None


@pytest.mark.parametrize(('extension', 'text'), [('json', '{"x":1,"x":2}'), ('yaml', 'x: 1\nx: 2\n'),
    ('yaml', 'x: &a [1]\ny: *a\n'), ('yaml', 'x: !!python/object/apply:os.system ["false"]')])
def test_ambiguous_and_unsafe_input_rejected(tmp_path, extension, text):
    path = tmp_path/('plan.'+extension)
    path.write_text(text)
    with pytest.raises((ValueError, TypeError)):
        load_plan(path)


def test_constraints_reject_edits_resealing_and_blocked_documents(plan):
    _, resolved = validate_plan(plan)
    altered = copy.deepcopy(resolved)
    altered['constraints']['actor_radius_m'] = .01
    with pytest.raises(ValueError, match='stale'):
        verify_resolved(altered)
    from modules.blender.planning.validator import canonical_hash
    altered['sha256'] = canonical_hash({k: v for k, v in altered.items() if k != 'sha256'})
    with pytest.raises(ValueError, match='stale'):
        verify_resolved(altered)
    with pytest.raises(ValueError, match='blocked'):
        verify_resolved({'status': 'BLOCKED'})


def test_nonfinite_and_old_abstract_only_inputs_fail(plan):
    plan['route']['start']['position_m'][0] = float('nan')
    assert validate_plan(plan)[0]['errors'][0]['code'] == 'INVALID_JSON_VALUE'
    report, _ = validate_plan(plan['intent'])
    assert 'A3_INTENT_REQUIRES_RESOLUTION' in {e['code'] for e in report['errors']}


def test_empty_camera_coverage_is_soft_but_unknown_references_fail(plan):
    plan['intent']['camera']['readable_event_ids'] = []
    plan['intent']['camera']['focus_actor_ids'] = []
    report, resolved = validate_plan(plan)
    assert report['status'] == 'PASSED'
    assert resolved['constraints']['camera_intent']['readable_event_ids'] == []
    assert 'CAMERA_INTERACTION_HIDDEN' in {w['code'] for w in report['warnings']}
    plan['intent']['camera']['readable_event_ids'] = ['ghost']
    assert validate_plan(plan)[0]['status'] == 'FAILED'


def test_overlap_in_abstract_plan_and_nonfinite_scale_rejected(plan):
    plan['intent']['events'][1]['target_window'] = {'start_s': 2.1, 'end_s': 2.5}
    report, _ = validate_plan(plan)
    assert report['status'] == 'FAILED' and len(report['answers']) == 6
    plan['route']['start']['position_m'][0] = 10**400
    report, _ = validate_plan(plan)
    assert report['status'] == 'FAILED' and report['errors'][0]['code'] == 'INVALID_STRUCTURE'


def test_valid_supported_catch_compiles_all_measurable_conditions(plan):
    # A catch may be the final sparse event as well as the terminal state.
    last = plan['intent']['events'][-1]
    last.update(kind='settle', actor_ids=['marble'], stage_id='catch', clearance=None)
    last['target_window'] = {'start_s': 12.5, 'end_s': 13.1}
    plan['events'][-1]['time_window'] = [12.5, 13.1]
    plan['events'][-1].update(type='supported_catch', target='catcher', success_condition={
        'target_contact': True, 'speed_max_m_s': .02, 'supported_duration_min_s': .25})
    report, resolved = validate_plan(plan)
    assert report['status'] == 'PASSED', report
    assert len(resolved['constraints']['events'][-1]['success_all']) == 3
    plan['events'][-1]['success_condition']['supported_duration_min_s'] = 1
    assert 'CATCH_WINDOW_TOO_SHORT' in {e['code'] for e in validate_plan(plan)[0]['errors']}
