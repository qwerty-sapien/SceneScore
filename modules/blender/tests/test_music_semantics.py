"""Independent analytic controls for the v2 supplement; no Blender/recipes needed."""
import copy
import json
import math
from collections import Counter
from pathlib import Path

import pytest

from modules.blender.geometry import area, normal_speed, pair_timeline
from modules.blender.summary import MUSIC_SEMANTICS_VERSION, motion_semantics_summary, music_summary
from scenescore.contracts import validate


FIXTURE_PATH = Path(__file__).parent/'fixtures/music-semantics-v2.json'
FIXTURES = json.loads(FIXTURE_PATH.read_text())
CASES = {case['name']: case for case in FIXTURES['cases']}
SPHERE = {'shape': 'sphere', 'radius': 1.}


def run(case, **kwargs):
    return motion_semantics_summary(case['scene'], case['states'], case['events'],
                                    geometry=case['geometry'], **kwargs)


def select(result, kind):
    return [event for event in result['events'] if event['event_type'] == kind]


@pytest.mark.parametrize('name', CASES)
def test_canonical_analytic_fixture_and_supplement(name):
    case = CASES[name]
    for record in [case['scene'], *case['states'], *case['events']]:
        validate(record)
    snapshot = copy.deepcopy(case)
    result = run(case)
    assert case == snapshot
    assert result['module_version'] == MUSIC_SEMANTICS_VERSION
    assert Counter(event['event_type'] for event in result['events']) == Counter(case['expected']['types'])
    for kind, expected in case['expected'].get('drivers', {}).items():
        assert select(result, kind)[0]['driver'] == pytest.approx(expected)
    assert len(select(result, 'asymmetric_rebound')) == case['expected']['rebound_count']
    assert all(event['driver'] is not None and 0 <= event['driver'] <= 1 for event in result['events'])
    assert result['provenance']['approval'] is None
    assert result['provenance']['audition_status'] == 'AUDITION_PENDING'


@pytest.mark.parametrize('name', ['contact_episode', 'positive_near_miss', 'tunnelling_collision', 'constant_separation'])
def test_existing_pair_timeline_preserves_independent_event_times(name):
    case = CASES[name]
    _, actual = pair_timeline(SPHERE, SPHERE, case['analytic_samples'])
    expected = sorted((event['event_type'], event['onset_s'], event['duration_s']) for event in case['events'])
    observed = sorted((event['event_type'], event['onset_s'], event['duration_s']) for event in actual)
    assert [event[0] for event in observed] == [event[0] for event in expected]
    for actual_event, expected_event in zip(observed, expected):
        assert actual_event[1:] == pytest.approx(expected_event[1:])


def test_all_eight_event_types_have_portable_analytic_controls():
    assert {event['event_type'] for case in CASES.values() for event in run(case)['events']} == {
        'approach', 'near_miss', 'separation', 'contact_onset', 'contact_sustain',
        'contact_release', 'collision', 'asymmetric_rebound'}


def test_near_miss_minimum_is_not_bracket_onset_or_a_contact():
    case = CASES['positive_near_miss']
    result = run(case)
    event = select(result, 'near_miss')[0]
    assert event['onset_s'] == 0
    assert event['minimum_s'] == .125
    assert event['inputs'] == {'min_gap_m': .25, 'closeness': .5}
    assert event['certified_no_tunnelling'] is True
    assert event['certification']['source_event_id'] == event['source_event_id']
    assert not any(event['event_type'].startswith('contact') for event in result['events'])


def test_sweep_uses_exact_contact_axis_for_normal_speed():
    # y=1 crossing a radius-2 circle: x=-sqrt(3) at entry; independent derivative.
    root = (5-math.sqrt(3))/10
    expected = -10*math.sqrt(3)/2
    assert normal_speed([-5, 1, 0], [5, 1, 0], [0, 0, 0], [0, 0, 0], 1, root) == pytest.approx(expected)
    assert normal_speed([-5, 1, 0], [5, 1, 0], [0, 0, 0], [0, 0, 0], 1) > 0
    case = copy.deepcopy(CASES['tunnelling_collision'])
    for state in case['states']:
        if state['object_id'] == 'a':
            state['transform']['position_m'][1] = 1
    case['events'][0]['onset_s'] = root*.125
    result = run(case)
    event = select(result, 'collision')[0]
    assert event['onset_s'] == root*.125
    assert event['method'] == 'swept_sphere_exact'
    assert event['inputs']['normal_before_m_s'] == pytest.approx(expected/.125)


@pytest.mark.parametrize('name,smaller,larger', [
    ('small_over_large_rebound', 'a', 'b'), ('large_over_small_rebound', 'b', 'a')])
def test_rebound_roles_area_ratio_and_retention_are_geometric(name, smaller, larger):
    case = CASES[name]
    event = select(run(case), 'asymmetric_rebound')[0]
    assert event['rebounding_object_id'] == smaller
    assert event['anchor_object_id'] == larger
    assert event['area_ratio'] == 4.
    assert event['inputs']['normal_before_m_s'] == -4.
    assert event['inputs']['normal_after_m_s'] == 2.
    assert event['speed_retention'] == .5
    assert event['method'] == 'evaluated_area_ratio_proxy'
    assert event['mass_inferred'] is False and event['restitution_claimed'] is False
    assert event['trigger_event_id'] == case['events'][0]['id']
    for obj in case['geometry']['objects']:
        mesh = obj['area_fixture']
        assert area(mesh['vertices'], mesh['triangles']) == obj['surface_area_m2']


def test_equal_area_is_not_rebound_and_subfloor_retention_is_null():
    assert not select(run(CASES['equal_area_no_rebound']), 'asymmetric_rebound')
    result = run(CASES['subfloor_rebound'])
    assert not select(result, 'asymmetric_rebound')
    rejected = next(item for item in result['suppressed'] if item['event_type'] == 'asymmetric_rebound')
    assert rejected['reason'] == 'normal_speed_below_rebound_floor'
    assert rejected['speed_retention'] is None


@pytest.mark.parametrize('mutation,reason', [
    ('null_area', 'evaluated_area_unavailable'),
    ('origin_metadata', 'evaluated_mesh_area_provenance_missing'),
    ('no_reversal', 'normal_velocity_did_not_reverse'),
    ('post_speed_floor', 'normal_speed_below_rebound_floor'),
])
def test_invalid_rebound_evidence_is_rejected(mutation, reason):
    case = copy.deepcopy(CASES['small_over_large_rebound'])
    if mutation == 'null_area':
        for state in case['states']:
            if state['object_id'] == 'a':
                state['surface_area_m2'] = None
    elif mutation == 'origin_metadata':
        case['geometry']['objects'][0]['geometry_method'] = 'object origin metadata'
    else:
        last = next(s for s in case['states'] if s['object_id'] == 'a' and s['scene_time_s'] == .25)
        last['transform']['position_m'][0] = -1.75 if mutation == 'no_reversal' else -2.003125
    result = run(case)
    assert not select(result, 'asymmetric_rebound')
    assert any(item['reason'] == reason for item in result['suppressed'])


def test_rebound_cannot_exist_without_triggering_contact():
    case = copy.deepcopy(CASES['small_over_large_rebound'])
    case['events'] = []
    case['geometry']['event_details'] = []
    assert run(case)['events'] == []
    case = copy.deepcopy(CASES['small_over_large_rebound'])
    case['events'][0]['event_type'] = 'asymmetric_rebound'
    with pytest.raises(ValueError, match='triggering canonical contact'):
        run(case)


def _duplicate_case():
    case = copy.deepcopy(CASES['tunnelling_collision'])
    onset = {**case['events'][0], 'id': 'nearby-sampled-contact', 'event_type': 'contact_onset', 'onset_s': .05}
    case['events'].append(onset)
    return case


def test_collision_dedupe_keeps_swept_timestamp_and_source_references():
    case = _duplicate_case()
    result = run(case)
    assert len(result['events']) == 1
    kept = result['events'][0]
    assert kept['event_type'] == 'collision'
    assert kept['onset_s'] == .0375
    assert kept['method'] == 'swept_sphere_exact'
    assert set(kept['source_event_ids']) == {event['id'] for event in case['events']}
    assert next(item for item in result['suppressed'] if item['reason'] == 'deduplicated_contact_onset')['kept_event_id'] == kept['source_event_id']
    assert len(case['events']) == 2  # Canonical stream is untouched.


@pytest.mark.parametrize('change', ['outside_window', 'different_loop', 'different_pair'])
def test_distinct_contacts_are_not_deduplicated(change):
    case = _duplicate_case()
    onset = case['events'][-1]
    if change == 'outside_window':
        onset['onset_s'] = .08
    elif change == 'different_loop':
        onset['loop_instance'] = 1
    else:
        case['scene']['objects'].append({'object_id': 'c', 'sonic_identity_id': 'voice:c'})
        onset['pair'] = ['a', 'c']
        onset['pair_id'] = 'a|c'
    result = run(case)
    assert len(select(result, 'collision')) == len(select(result, 'contact_onset')) == 1
    assert not any(item['reason'] == 'deduplicated_contact_onset' for item in result['suppressed'])


def test_one_sampled_contact_is_matched_to_only_one_sweep():
    case = _duplicate_case()
    case['events'].append({**case['events'][0], 'id': 'second-sweep', 'onset_s': .04})
    result = run(case)
    assert len(select(result, 'collision')) == 2
    assert len([item for item in result['suppressed'] if item['reason'] == 'deduplicated_contact_onset']) == 1
    assert sum('nearby-sampled-contact' in event['source_event_ids'] for event in result['events']) == 1


def test_null_driver_returns_explicit_unmodified_score_fallback():
    case = copy.deepcopy(CASES['contact_episode'])
    case['states'] = []
    case['events'][0]['relative_normal_speed_m_s'] = None
    result = run(case)
    for kind in ('approach', 'contact_onset', 'separation', 'contact_release'):
        assert select(result, kind)[0]['driver'] is None
        assert any(item['event_type'] == kind and item['fallback'] == 'unmodified_score' for item in result['suppressed'])


def test_missing_near_miss_minimum_does_not_fabricate_resolution():
    case = copy.deepcopy(CASES['positive_near_miss'])
    case['geometry']['event_details'] = []
    event = select(run(case), 'near_miss')[0]
    assert event['driver'] is None and event['minimum_s'] is None
    assert event['certified_no_tunnelling'] is False


def test_forged_positive_minimum_cannot_hide_segment_tunnelling():
    case = copy.deepcopy(CASES['positive_near_miss'])
    for state in case['states']:
        if state['object_id'] == 'a':
            pos = [{0: -5, .125: 3, .25: 5}[state['scene_time_s']], 0, 0]
            state['transform']['position_m'] = pos
            state['bounds_min_m'] = [x-1 for x in pos]
            state['bounds_max_m'] = [x+1 for x in pos]
    for event in case['events']:
        event['surface_gap_m'] = 1.
    event = select(run(case), 'near_miss')[0]
    assert event['driver'] is None
    assert event['certified_no_tunnelling'] is False
    assert event['driver_reason'] == 'near_miss_segment_not_certified'


def test_missing_segment_coverage_cannot_certify_near_miss():
    case = copy.deepcopy(CASES['positive_near_miss'])
    case['states'] = [state for state in case['states'] if state['scene_time_s'] != .125]
    event = select(run(case), 'near_miss')[0]
    assert event['driver'] is None and event['certified_no_tunnelling'] is False


def test_rebound_sign_samples_must_fit_declared_window():
    result = run(CASES['small_over_large_rebound'], config={'rebound_window_s': .03})
    assert not select(result, 'asymmetric_rebound')
    assert any(item['reason'] == 'rebound_velocity_window_out_of_coverage' for item in result['suppressed'])


def test_config_and_inputs_are_hashed_and_order_independent():
    case = copy.deepcopy(CASES['contact_episode'])
    baseline = run(case)
    case['states'].reverse()
    case['events'].reverse()
    assert run(case) == baseline
    changed = run(case, config={'contact_ref_speed_m_s': 16.})
    assert changed['config_hash'] != baseline['config_hash']
    assert select(changed, 'contact_onset')[0]['driver'] == .5
    assert select(changed, 'approach')[0] == select(baseline, 'approach')[0]
    case['states'][0]['surface_area_m2'] = 2
    assert run(case)['provenance']['states_hash'] != baseline['provenance']['states_hash']


@pytest.mark.parametrize('config', [{'contact_ref_speed_m_s': 0}, {'sustain_ref_s': float('nan')},
                                   {'approach_ref_speed_m_s': float('inf')}, {'new_unknown_config': 2},
                                   {'rebound_min_area_ratio': 1}, {'contact_dedupe_s': -1}])
def test_invalid_configuration_is_rejected(config):
    with pytest.raises(ValueError):
        run(CASES['contact_episode'], config=config)


@pytest.mark.parametrize('mutation', ['nonfinite_position', 'unknown_object', 'wrong_units', 'wrong_major', 'duplicate_state'])
def test_invalid_input_is_rejected(mutation):
    case = copy.deepcopy(CASES['contact_episode'])
    if mutation == 'nonfinite_position':
        case['states'][0]['transform']['position_m'][0] = float('nan')
    elif mutation == 'unknown_object':
        case['states'][0]['object_id'] = 'unknown'
    elif mutation == 'wrong_units':
        case['scene']['units'] = 'centimetres'
    elif mutation == 'wrong_major':
        case['scene']['schema_version'] = '2.0'
    else:
        case['states'].append(copy.deepcopy(case['states'][0]))
    with pytest.raises(ValueError):
        run(case)


def test_convenience_loader_binds_exact_input_bytes(tmp_path):
    case = CASES['small_over_large_rebound']
    for name, value in [('manifest.json', case['scene']), ('geometry.json', case['geometry'])]:
        (tmp_path/name).write_text(json.dumps(value))
    for name, values in [('object_states.jsonl', case['states']), ('interactions.jsonl', case['events'])]:
        (tmp_path/name).write_text(''.join(json.dumps(value)+'\n' for value in values))
    result = music_summary(tmp_path)
    assert result['events'] == run(case)['events']
    assert len(result['provenance']['input_file_hashes']) == 4
    (tmp_path/'geometry.json').unlink()
    missing = music_summary(tmp_path)
    assert not select(missing, 'asymmetric_rebound')
    assert any(item['reason'] == 'evaluated_mesh_area_provenance_missing' for item in missing['suppressed'])


def test_sweep_tunnelling_is_never_certified_as_near_miss():
    # All three sampled gaps are positive, but first segment crosses both spheres.
    _, events = pair_timeline(SPHERE, SPHERE, [(0, [-5, 0, 0], [0, 0, 0]),
                                              (.125, [3, 0, 0], [0, 0, 0]),
                                              (.25, [5, 0, 0], [0, 0, 0])])
    assert any(event['event_type'] == 'collision' for event in events)
    assert not any(event['event_type'] == 'near_miss' for event in events)


def test_undefined_normal_and_invalid_segment_are_not_zero():
    assert normal_speed([0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], .125) is None
    with pytest.raises(ValueError):
        normal_speed([0, 0, 0], [1, 0, 0], [0, 0, 0], [0, 0, 0], 0)
