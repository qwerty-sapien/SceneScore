"""Independent transform boundaries and negative controls; not a perceptual verdict."""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from modules.music.catalog import build_vertical_score, digest
from modules.music.events import apply_swing, resolve_events, ticks_to_seconds, transpose_events
from modules.music.ornament import KINDS, TransformBudgets, TransformRequest, apply_transforms


@pytest.fixture(scope='module')
def hero():
    score = build_vertical_score()
    return score['composition'], resolve_events(score['composition'], score['groove'])


def lead(events):
    return next(e for e in events if e['event_type'] == 'note' and e['articulation'] == 'light_detached')


def miniature(hero, lanes=1, count=3, pitch=64):
    c, events = hero
    template = lead(events)
    notes = []
    for lane in range(lanes):
        for i in range(count):
            tick = i * 960
            notes.append({**deepcopy(template), 'id': f'fixture-{lane}-{i}', 'lane_id': f'fixture-{lane}',
                          'object_id': f'object-{lane}', 'start_tick': tick, 'duration_ticks': 960,
                          'resolved_time_s': ticks_to_seconds(tick, c['tempo_map']), 'duration_s': .625,
                          'midi_pitch': pitch + lane * 12, 'swing_applied': False,
                          'swing_application_count': 0, 'ornament': None})
    return notes


@pytest.mark.parametrize('kind', ['grace', 'mordent', 'turn', 'trill', 'tremolo', 'octave_doubling'])
def test_required_note_vocabulary_preserves_slot_identity_and_all_other_events(hero, kind):
    c, events = hero
    before = deepcopy(events)
    target = lead(events)
    result = apply_transforms(events, [TransformRequest(target['id'], kind)], c)
    row = result.audit['requests'][0]
    assert row['status'] == 'applied', row
    changed = [e for e in result.events if e['id'] in row['output_event_ids']]
    assert min(e['resolved_time_s'] for e in changed) == target['resolved_time_s']
    assert max(e['resolved_time_s'] + e['duration_s'] for e in changed) == pytest.approx(
        target['resolved_time_s'] + target['duration_s'])
    assert min(e['start_tick'] for e in changed) == target['start_tick']
    assert max(e['start_tick'] + e['duration_ticks'] for e in changed) == (
        target['start_tick'] + target['duration_ticks'])
    assert {e['object_id'] for e in changed} == {target['object_id']}
    main = next(e for e in changed if e['id'] == target['id'])
    assert main['midi_pitch'] == target['midi_pitch']
    assert all(e['swing_application_count'] == target['swing_application_count'] for e in changed)
    if target['swing_applied']:
        for event in changed:
            with pytest.raises(ValueError, match='already_applied'):
                apply_swing(event, c['swing_ratio'], c['tempo_map'])
    untouched = {e['id']: e for e in result.events if e['id'] not in row['output_event_ids']}
    assert untouched == {e['id']: e for e in events if e['id'] != target['id']}
    assert events == before
    assert result.audit['score_duration_s'] == 30
    assert result.audit['approval'] is None


@pytest.mark.parametrize('articulation', ['detached', 'staccato', 'tenuto', 'legato'])
def test_articulation_is_independent_of_gain_pitch_velocity_and_occupied_duration(hero, articulation):
    c, events = hero
    target = lead(events)
    result = apply_transforms(events, [TransformRequest(target['id'], 'articulation', articulation=articulation)], c)
    assert result.audit['requests'][0]['status'] == 'applied'
    after = next(e for e in result.events if e['id'] == target['id'])
    assert after == {**target, 'articulation': articulation, 'provenance': after['provenance']}
    assert result.audit['events_added'] == 0


def test_velocity_changes_only_its_lane_and_rejects_overflow(hero):
    c, events = hero
    target = lead(events)
    result = apply_transforms(events, [TransformRequest(target['id'], 'velocity', velocity_delta=9)], c)
    after = next(e for e in result.events if e['id'] == target['id'])
    assert after == {**target, 'velocity': target['velocity'] + 9, 'provenance': after['provenance']}
    fixture = miniature(hero)
    fixture[0]['velocity'] = 125
    rejected = apply_transforms(fixture, [TransformRequest(fixture[0]['id'], 'velocity', velocity_delta=9)], c)
    assert rejected.audit['requests'][0]['reason'] == 'velocity_outside_range'
    assert rejected.events == fixture


@pytest.mark.parametrize('kind', ['chord_redistribution', 'arpeggio'])
def test_accompaniment_group_stays_inside_existing_harmonic_slot(hero, kind):
    c, events = hero
    first = next(e for e in events if e['articulation'] == 'soft_comp')
    group = [e for e in events if e['articulation'] == 'soft_comp' and e['start_tick'] == first['start_tick']]
    request = TransformRequest(first['id'], kind, related_event_ids=tuple(e['id'] for e in group[1:]))
    result = apply_transforms(events, [request], c)
    row = result.audit['requests'][0]
    assert row['status'] == 'applied', row
    changed = [e for e in result.events if e['id'] in row['output_event_ids']]
    assert len(changed) == len(group)
    assert min(e['resolved_time_s'] for e in changed) == first['resolved_time_s']
    assert max(e['resolved_time_s'] + e['duration_s'] for e in changed) == pytest.approx(
        first['resolved_time_s'] + first['duration_s'])
    assert Counter(e['midi_pitch'] % 12 for e in changed) == Counter(e['midi_pitch'] % 12 for e in group)


def test_group_transform_rejects_melody_unknown_target_and_slot_mismatch(hero):
    c, events = hero
    fixture = miniature(hero, lanes=2)
    for event in fixture:
        event['articulation'] = 'soft_comp'
    bad = TransformRequest(fixture[0]['id'], 'arpeggio', related_event_ids=(fixture[3]['id'],))
    result = apply_transforms(fixture, [bad], c)
    assert result.audit['requests'][0]['reason'] == 'chord_group_slot_mismatch'
    result = apply_transforms(events, [TransformRequest('absent', 'grace')], c)
    assert result.audit['requests'][0]['reason'] == 'unknown_event_id'
    fixture[3]['object_id'] = fixture[0]['object_id']
    fixture[0]['articulation'] = 'light_detached'
    result = apply_transforms(fixture, [bad], c)
    assert result.audit['requests'][0]['reason'] == 'chord_redistribution_requires_accompaniment'


def test_protected_brush_and_foley_are_byte_identical_for_every_transform(hero):
    c, events = hero
    brush = next(e for e in events if e['event_type'] == 'brush')
    foley = {**deepcopy(brush), 'id': 'fixture-foley', 'event_type': 'foley',
             'start_tick': None, 'duration_ticks': None, 'scene_time_s': .12345,
             'resolved_time_s': .12345, 'duration_s': .01, 'articulation': 'collision'}
    source = [*miniature(hero), brush, foley]
    requests = [TransformRequest(e['id'], kind, articulation='legato' if kind == 'articulation' else None)
                for e in (brush, foley) for kind in KINDS]
    result = apply_transforms(source, requests, c)
    assert all(r['reason'] == 'protected_unpitched_or_foley' for r in result.audit['requests'])
    assert {e['id']: e for e in source} == {e['id']: e for e in result.events}
    assert result.audit['protected_streams_unchanged']


def test_fixed_seed_and_request_reordering_are_byte_deterministic(hero):
    c, _ = hero
    events = miniature(hero)
    requests = [TransformRequest(events[0]['id'], 'grace', probability=.5),
                TransformRequest(events[1]['id'], 'velocity', velocity_delta=4, probability=.5)]
    one = apply_transforms(events, requests, c, seed=19)
    two = apply_transforms(list(reversed(events)), list(reversed(requests)), c, seed=19)
    assert asdict(one) == asdict(two)
    zero = apply_transforms(events, [TransformRequest(events[0]['id'], 'grace', probability=0)], c)
    assert zero.audit['requests'][0]['reason'] == 'seeded_density_skip'


def test_repeat_stack_and_every_note_decoration_guards(hero):
    c, _ = hero
    events = miniature(hero)
    duplicate = [TransformRequest(events[0]['id'], 'grace'), TransformRequest(events[0]['id'], 'turn')]
    result = apply_transforms(events, duplicate, c)
    assert [r['status'] for r in result.audit['requests']] == ['applied', 'suppressed']
    assert result.audit['requests'][1]['reason'] == 'ornament_already_present'
    repeats = [TransformRequest(events[i]['id'], 'grace') for i in (0, 1)]
    result = apply_transforms(events, repeats, c)
    assert result.audit['requests'][1]['reason'] == 'same_kind_lane_bar'
    requests = [TransformRequest(events[i]['id'], kind) for i, kind in enumerate(('grace', 'mordent', 'turn'))]
    result = apply_transforms(events, requests, c)
    assert result.audit['requests'][-1]['reason'] == 'every_eligible_note_would_be_decorated'


def test_two_simultaneous_ornaments_is_hard_ceiling(hero):
    c, _ = hero
    events = miniature(hero, lanes=3, pitch=60)
    requests = [TransformRequest(events[i * 3]['id'], 'grace') for i in range(3)]
    result = apply_transforms(events, requests, c)
    assert Counter(r['status'] for r in result.audit['requests']) == {'applied': 2, 'suppressed': 1}
    assert result.audit['requests'][-1]['reason'] == 'simultaneous_ornament_budget'
    assert result.audit['maximum_simultaneous_ornaments'] == 2


def test_added_events_use_a_rolling_second_and_bar_total_budget(hero):
    c, _ = hero
    events = miniature(hero, lanes=2)
    requests = [TransformRequest(events[i * 3]['id'], 'trill', subdivisions=8) for i in range(2)]
    result = apply_transforms(events, requests, c)
    assert result.audit['requests'][-1]['reason'] == 'added_event_rate_budget'
    assert result.audit['maximum_added_events_per_second'] == 7
    result = apply_transforms(events, requests[:1], c, budgets=TransformBudgets(max_events_per_bar=6))
    assert result.audit['requests'][0]['reason'] == 'bar_event_budget'
    result = apply_transforms(events, requests[:1], c, budgets=TransformBudgets(max_events_per_second_added=0))
    assert result.audit['requests'][0]['reason'] == 'added_event_rate_budget'


def test_low_register_cluster_guard_and_register_after_signed_transposition(hero):
    c, _ = hero
    events = miniature(hero, lanes=2, pitch=35)
    # A chromatic upper grace narrows an acceptable fifth to a sub-floor cluster.
    for event in events[3:]:
        event['midi_pitch'] = 40
    result = apply_transforms(events, [TransformRequest(events[0]['id'], 'grace', direction=-1)], c)
    assert result.audit['requests'][0]['reason'] == 'low_register_cluster'
    high = miniature(hero, pitch=90)
    result = apply_transforms(high, [TransformRequest(high[0]['id'], 'octave_doubling')], c)
    assert result.audit['requests'][0]['reason'] == 'ornament_outside_register'
    for shift in (-2, 2):
        changed = apply_transforms(miniature(hero), [TransformRequest('fixture-0-0', 'turn')], c).events
        assert all(28 <= e['midi_pitch'] <= 96 for e in transpose_events(changed, shift))
    with pytest.raises(ValueError, match='register'):
        transpose_events(high, 12)


def test_short_notes_and_invalid_source_cannot_make_hanging_or_outside_events(hero):
    c, _ = hero
    events = miniature(hero)
    events[0].update(duration_ticks=30, duration_s=.02)
    result = apply_transforms(events, [TransformRequest(events[0]['id'], 'turn')], c)
    assert result.audit['requests'][0]['reason'] == 'ornament_too_short_for_renderer'
    invalid = deepcopy(events)
    invalid[0]['duration_ticks'] = 0
    with pytest.raises(ValueError):
        apply_transforms(invalid, [], c)
    invalid = deepcopy(events)
    invalid[0]['resolved_time_s'] = 30
    with pytest.raises(ValueError, match='outside_score_duration'):
        apply_transforms(invalid, [], c)


def test_duplicate_requests_and_repeated_calls_do_not_reset_ornament_budgets(hero):
    c, _ = hero
    events = miniature(hero, lanes=2)
    request = TransformRequest(events[0]['id'], 'trill', subdivisions=8)
    one = apply_transforms(events, [request, request], c)
    assert one.audit['requests'][1]['reason'] == 'duplicate_transform_request'
    two = apply_transforms(one.events, [TransformRequest(events[3]['id'], 'trill', subdivisions=8)], c)
    assert two.audit['requests'][0]['reason'] == 'added_event_rate_budget'
    repeated_kind = apply_transforms(one.events, [TransformRequest(events[1]['id'], 'trill')], c)
    assert repeated_kind.audit['requests'][0]['reason'] == 'same_kind_lane_bar'


@pytest.mark.parametrize('kwargs', [
    {'kind': 'unknown'}, {'preserves_duration': False}, {'velocity_delta': True},
    {'direction': 0}, {'subdivisions': 9}, {'probability': float('nan')},
    {'related_event_ids': ('x',)}, {'kind': 'articulation', 'articulation': 'unsupported'},
])
def test_typed_requests_reject_malformed_or_duration_extending_controls(kwargs):
    with pytest.raises(ValueError):
        TransformRequest('x', **{'kind': 'grace', **kwargs})


def test_frozen_variation_fixture(hero):
    path = Path(__file__).parents[1] / 'fixtures/music-ornament-v1.json'
    fixture = json.loads(path.read_text())
    c, events = hero
    result = apply_transforms(events, fixture['requests'], c, seed=fixture['seed'])
    assert digest(result.events) == fixture['output_events_sha256']
    assert result.audit == fixture['audit']
