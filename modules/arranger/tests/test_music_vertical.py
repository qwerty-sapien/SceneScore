"""Portable synthetic music-vertical controls, independent of Blender or playback."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

import pytest

from modules.arranger.core import (Context, Policy, VERTICAL_LANES, _causal_pair_closing,
                                  _vertical_withhold_thirds, compile_vertical_preview, digest,
                                  encoded, motion_direction, validate_vertical_result)
from modules.music.catalog import build_vertical_score
from modules.music.events import transpose_events
from scenescore.contracts import validate

FIXTURE = json.loads((Path(__file__).parents[2]/'blender/tests/fixtures/music-semantics-v2.json').read_text())
CASES = {case['name']: case for case in FIXTURE['cases']}


def fixture(name='positive_near_miss', offset=12.5):
    case = deepcopy(CASES[name])
    case['scene']['duration_s'] = 30.
    for state in case['states']:
        state['scene_time_s'] += offset
        state['frame'] += offset*8
    for event in case['events']:
        event['onset_s'] += offset
    for detail in case['geometry']['event_details']:
        detail['minimum_gap_time_s'] += offset
        detail['end_s'] += offset
    source = build_vertical_score()
    ctx = Context(case['scene'], case['states'], case['events'], source['composition'], source['groove'])
    return ctx, case['geometry']


def run(name='positive_near_miss', offset=12.5, **kwargs):
    ctx, geometry = fixture(name, offset)
    return compile_vertical_preview(ctx, geometry=geometry, **kwargs)


def notes(result):
    return [event for event in result['events'] if event['event_type'] == 'note']


def sound(event):
    return {key: value for key, value in event.items() if key not in ('plan_id', 'provenance')}


def test_complete_bound_canonical_candidate_is_deterministic():
    ctx, geometry = fixture()
    before = deepcopy((ctx, geometry))
    result = compile_vertical_preview(ctx, geometry=geometry)
    assert result == compile_vertical_preview(ctx, geometry=geometry)
    assert (ctx, geometry) == before
    validate(result['plan'])
    assert result['plan_payload'].encode() == encoded(result['plan'])
    assert result['plan_payload_sha256'] == hashlib.sha256(result['plan_payload'].encode()).hexdigest()
    assert result['provenance']['binding_sha256'] in result['plan']['provenance']['input_hashes']
    for event in [*result['source_events'], *result['events']]:
        validate(event)
        assert event['plan_id'] == result['plan']['id']
        assert event['instrument_id'] in result['plan']['palette_ids']
        assert 0 <= event['resolved_time_s'] < event['resolved_time_s']+event['duration_s'] <= 30.+1e-9
    assert result['approval'] is None and result['audition_status'] == 'AUDITION_PENDING'
    assert result['audit']['identity']['unchanged_note_fraction'] >= .95
    assert result['audit']['identity']['unchanged_lead_fraction'] >= .9


def test_original_voice_slots_are_not_duplicated_and_harmony_reaches_transition_lanes():
    result = run('constant_separation', 0.)
    source = result['source_events']
    assert len(source) == 258
    assert sum(e['event_type'] == 'note' for e in source) == 162
    owners = [e['object_id'] for e in source if e['lane_id'] == 'object_motif']
    assert owners == ['a', 'b']*9
    comp = [e for e in source if e['articulation'] == 'soft_comp']
    assert len(comp) == 72
    assert {e['lane_id'] for e in comp} == {'harmony-0', 'harmony-1', 'harmony-2'}
    assert all(e['object_id'] is None for e in source if e['lane_id'] != 'object_motif')
    assert [sound(e) for e in source] == [sound(e) for e in result['events']]


def test_near_miss_holds_thirds_after_minimum_and_never_triggers_accent_foley_or_key():
    result = run()
    hold = result['holds'][0]
    assert hold['start_s'] == 12.625
    assert hold['end_s'] == 13.25
    assert hold['withheld_pitch_classes'] == [9]
    assert not result['foley_events']
    assert all(e['event_type'] != 'foley' for e in result['events'])
    control = next(row for row in result['control_track']['events'] if row['feature'] == 'near_miss')
    assert control['start_s'] == hold['start_s']
    assert not {'accent', 'key'}.intersection(control['values'])
    for event in notes(result):
        if event['resolved_time_s'] < hold['end_s'] and event['resolved_time_s']+event['duration_s'] > hold['start_s']:
            assert event['midi_pitch'] % 12 not in hold['withheld_pitch_classes']
    assert result['audit']['hold_edits']
    assert result['plan']['transitions'] == run('constant_separation', 0.)['plan']['transitions']


def test_approach_uses_only_causal_pair_samples_and_never_the_minimum_scalar():
    ctx, geometry = fixture('small_over_large_rebound', 12.375)
    t = 12.5
    before = _causal_pair_closing(ctx, ['a', 'b'], t, 2.)
    assert before == 1.
    for state in ctx.states:
        if state['scene_time_s'] > t:
            state['transform']['position_m'][0] = 10000.
    assert _causal_pair_closing(ctx, ['a', 'b'], t, 2.) == before
    assert _causal_pair_closing(ctx, ['a', 'b'], 25., 2.) is None


def test_future_outcome_cannot_change_identical_approach_prefix():
    ctx, geometry = fixture('contact_episode', 12.5)
    # Move the common approach interval to span two existing catalogue slots.
    approach = next(e for e in ctx.interactions if e['event_type'] == 'approach')
    approach.update(onset_s=12.5, duration_s=.25)
    all_times = [12.375, 12.5, 12.625, 12.75]
    template = deepcopy(ctx.states[:2])
    ctx.states = []
    for index, t in enumerate(all_times):
        for original in template:
            row = deepcopy(original)
            row.update(id=f"prefix:{original['object_id']}:{index}", scene_time_s=t, frame=1+t*8)
            row['transform']['position_m'] = [-3+index*.25, 0, 0] if row['object_id'] == 'a' else [0, 0, 0]
            ctx.states.append(row)
    ctx.interactions = [approach]
    geometry['event_details'] = [d for d in geometry['event_details'] if d['id'] == approach['id']]
    one = compile_vertical_preview(ctx, geometry=geometry)
    other = deepcopy(ctx)
    other.interactions[0]['relative_normal_speed_m_s'] = 0.  # Future-minimum scalar differs.
    two = compile_vertical_preview(other, geometry=geometry)
    def prefix(result):
        return [sound(e) for e in result['events'] if e['resolved_time_s'] < 12.75]
    assert prefix(one) == prefix(two)
    assert any(row['feature'] == 'approach' and row['driver'] > 0 for row in one['control_track']['events'])
    assert all(row.get('motion_sample_latest_s', row['start_s']) <= row['start_s'] for row in one['control_track']['events'])


def test_null_driver_and_missing_coverage_leave_original_score_with_reason():
    ctx, geometry = fixture('contact_episode', 12.5)
    ctx.interactions = [next(e for e in ctx.interactions if e['event_type'] == 'approach')]
    ctx.interactions[0]['relative_normal_speed_m_s'] = None
    geometry['event_details'] = [d for d in geometry['event_details'] if d['id'] == ctx.interactions[0]['id']]
    ctx.states = []
    result = compile_vertical_preview(ctx, geometry=geometry)
    assert [sound(e) for e in result['events']] == [sound(e) for e in result['source_events']]
    assert not result['control_track']['events']
    assert result['control_track']['suppressed'][0]['fallback'] == 'unmodified_score'


@pytest.mark.parametrize('name', ['contact_episode', 'positive_near_miss', 'tunnelling_collision',
                                  'small_over_large_rebound', 'large_over_small_rebound', 'equal_area_no_rebound'])
def test_each_semantic_fixture_has_bounded_control_lanes(name):
    result = run(name, 12.375)
    for row in result['control_track']['events']:
        assert 0 <= row['driver'] <= 1
        assert 0 <= row['start_s'] < row['end_s'] <= result['duration_s']
        for lane, value in row['values'].items():
            lo, hi = VERTICAL_LANES[(row['feature'], lane)]
            assert lo <= value <= hi
    assert result['audit']['realization']['transform']['maximum_added_events_per_second'] <= 12
    assert result['audit']['realization']['transform']['maximum_simultaneous_ornaments'] <= 2


def test_all_eight_types_in_one_second_respect_combined_density():
    combined, geometry = fixture('contact_episode', 12.45)
    combined.scene['id'] = 'synthetic-all-eight'
    combined.scene['objects'] = []
    combined.states, combined.interactions = [], []
    geometry['objects'], geometry['event_details'] = [], []
    for prefix, name, offset in [('p', 'contact_episode', 12.45), ('q', 'positive_near_miss', 12.375),
                                  ('r', 'tunnelling_collision', 12.45), ('s', 'small_over_large_rebound', 12.375)]:
        ctx, geom = fixture(name, offset)
        if name == 'contact_episode':
            # Independently extend the known incoming linear trajectory by one sample.
            for state in list(ctx.states[:2]):
                previous = deepcopy(state)
                previous.update(id=state['id']+':prior', scene_time_s=offset-.125)
                if previous['object_id'] == 'a':
                    previous['transform']['position_m'][0] = -4.
                ctx.states.append(previous)
        for obj in ctx.scene['objects']:
            obj['object_id'] = prefix+obj['object_id']
            obj['sonic_identity_id'] = prefix+obj['sonic_identity_id']
        for state in ctx.states:
            state.update(id=prefix+state['id'], scene_id=combined.scene['id'], object_id=prefix+state['object_id'])
        for event in ctx.interactions:
            event.update(id=prefix+event['id'], scene_id=combined.scene['id'],
                         pair=[prefix+oid for oid in event['pair']], pair_id='|'.join(prefix+oid for oid in event['pair']))
        for obj in geom['objects']:
            obj['object_id'] = prefix+obj['object_id']
        for detail in geom['event_details']:
            detail['id'] = prefix+detail['id']
        combined.scene['objects'].extend(ctx.scene['objects'])
        combined.states.extend(ctx.states)
        combined.interactions.extend(ctx.interactions)
        geometry['objects'].extend(geom['objects'])
        geometry['event_details'].extend(geom['event_details'])
    result = compile_vertical_preview(combined, geometry=geometry)
    assert {row['feature'] for row in result['control_track']['events']} == {feature for feature, _ in VERTICAL_LANES}
    assert all(12 <= row['start_s'] < 13 for row in result['control_track']['events'])
    assert result['audit']['density']['maximum_added_events_per_second'] <= 12
    assert result['audit']['density']['maximum_music_events_per_bar'] <= 96


def test_rebound_decorates_smaller_owner_and_records_quantization():
    result = run('small_over_large_rebound', 12.375)
    control = next(row for row in result['control_track']['events'] if row['feature'] == 'asymmetric_rebound')
    assert control['rebounding_object_id'] == 'a' and control['anchor_object_id'] == 'b'
    assert control['quantization_delay_s'] == 0.
    decorated = [e for e in notes(result) if e['ornament'] == 'grace']
    assert decorated and all(e['object_id'] == 'a' for e in decorated)
    assert all(e['object_id'] != 'b' for e in decorated)
    source = {e['id']: e for e in result['source_events']}
    main = next(e for e in decorated if e['id'] in source)
    assert main['velocity'] < source[main['id']]['velocity']
    assert main['articulation'] == 'tenuto'
    assert any(value > 0 for value in control['source_slot_delays_s'].values())
    assert control['mass_inferred'] is False and control['restitution_claimed'] is False
    equal = run('equal_area_no_rebound', 12.375)
    assert not any(e['ornament'] == 'grace' for e in notes(equal))
    assert not any(row['feature'] == 'asymmetric_rebound' for row in equal['control_track']['events'])


def test_object_identity_survives_transposition_and_style_lanes_remain_independent():
    result = run('small_over_large_rebound', 12.375)
    shifted = transpose_events(result['events'], 2)
    for before, after in zip(result['events'], shifted):
        assert before['object_id'] == after['object_id']
        for field in ('articulation', 'velocity', 'dynamics_db', 'ornament', 'lane_id'):
            assert before[field] == after[field]
        if before['event_type'] != 'note':
            assert before == after


def test_unchanged_velocity_and_brushes_without_explicit_rebound_velocity_mapping():
    result = run('contact_episode', 12.5)
    source = {e['id']: e for e in result['source_events']}
    for event in result['events']:
        if event['id'] in source:
            assert event['velocity'] == source[event['id']]['velocity']
            if event['event_type'] == 'brush':
                assert event == source[event['id']]
    requests = result['audit']['realization']['style_transform']['requests']
    assert any(row['status'] == 'applied' and row['request']['kind'] == 'articulation' for row in requests)
    assert not any(row['request']['kind'] == 'velocity' for row in requests)


def test_focus_config_and_sidecar_changes_invalidate_exact_plan():
    ctx, geometry = fixture()
    a = compile_vertical_preview(ctx, geometry=geometry, mapping_config={'focus_object_id': 'a'})
    b = compile_vertical_preview(ctx, geometry=geometry, mapping_config={'focus_object_id': 'b'})
    assert a['plan_payload_sha256'] != b['plan_payload_sha256']
    assert b['plan']['motion_policy']['focus_object_id'] == 'b'
    c = compile_vertical_preview(ctx, geometry=geometry, mapping_config={'dynamics_enabled': False})
    assert a['provenance']['binding_sha256'] != c['provenance']['binding_sha256']
    assert a['plan']['provenance']['config_hash'] != c['plan']['provenance']['config_hash']


def test_manual_focus_uses_existing_causal_world_z_policy():
    ctx, geometry = fixture('small_over_large_rebound', 12.375)
    for state in ctx.states:
        state['velocity_m_s'] = [0., 0., .2 if state['object_id'] == 'b' else 0.]
    policy = Policy(lookback_s=.1)
    result = compile_vertical_preview(ctx, geometry=geometry, policy=policy,
                                      mapping_config={'focus_object_id': 'b'})
    assert motion_direction(ctx, result['plan'], 12.5) == 2
    assert result['plan']['motion_policy']['axis'] == 'Z'


def test_source_order_cannot_change_candidate_or_hashes():
    ctx, geometry = fixture('contact_episode', 12.5)
    a = compile_vertical_preview(ctx, geometry=geometry)
    ctx.states.reverse()
    ctx.interactions.reverse()
    assert compile_vertical_preview(ctx, geometry=geometry) == a


def test_sidecar_and_score_tampering_invalidates_the_exact_candidate():
    source = run()
    for field in ('hold', 'control', 'note', 'plan'):
        changed = deepcopy(source)
        if field == 'hold':
            changed['holds'][0]['end_s'] += .1
        elif field == 'control':
            changed['control_track']['events'][0]['driver'] = .123
        elif field == 'note':
            next(e for e in changed['events'] if e['event_type'] == 'note')['midi_pitch'] += 1
        else:
            changed['plan']['motion_policy']['focus_object_id'] = 'b'
        with pytest.raises(ValueError, match='stale_vertical_candidate_binding'):
            validate_vertical_result(changed)


def test_hold_split_retains_only_original_intervals_outside_hold():
    result = run('constant_separation', 0.)
    original = deepcopy(next(e for e in result['source_events'] if e['event_type'] == 'note'))
    original.update(resolved_time_s=1., duration_s=2., start_tick=1536, duration_ticks=3072, midi_pitch=64)
    hold = {'id': 'hold', 'start_s': 1.5, 'end_s': 2.25, 'withheld_pitch_classes': [4]}
    events, audit = _vertical_withhold_thirds([original], [hold])
    assert [(e['resolved_time_s'], e['duration_s']) for e in events] == [(1., .5), (2.25, .75)]
    assert all(e['midi_pitch'] == 64 and e['velocity'] == original['velocity'] for e in events)
    assert audit[0]['duration_preserving'] is False
    assert audit[0]['unchanged_before_minimum'] is True
    assert original['duration_s'] == 2.


def test_short_end_coverage_fails_without_truncating_one_beat_hold():
    with pytest.raises(ValueError, match='one_beat_hold_exceeds_media'):
        run('positive_near_miss', 29.75)


@pytest.mark.parametrize('config', [{'unknown': True}, {'hold_beats': .5}, {'max_quantization_s': float('nan')},
                                   {'focus_object_id': 'missing'}, {'articulation_enabled': 1},
                                   {'max_changed_note_fraction': .5}])
def test_invalid_mapping_configs_fail(config):
    with pytest.raises(ValueError):
        run(mapping_config=config)


def test_zero_identity_budget_fails_instead_of_hiding_missing_hold():
    with pytest.raises(ValueError, match='source_note_identity_budget'):
        run(mapping_config={'max_changed_note_fraction': 0.})


def test_music_vertical_golden_fixture():
    result = run()
    actual = {'fixture_version': 1, 'source_note_count': result['audit']['identity']['source_note_count'],
              'identity': result['audit']['identity'], 'holds': result['holds'],
              'control_features': sorted({row['feature'] for row in result['control_track']['events']}),
              'musical_output_sha256': digest([sound(e) for e in result['events']]),
              'source_musical_sha256': digest([sound(e) for e in result['source_events']]),
              'approval': None, 'audition_status': 'AUDITION_PENDING'}
    golden = Path(__file__).with_name('fixtures')/'music-vertical-v1.json'
    assert actual == json.loads(golden.read_text())
