"""Objective ending/arrival checks; no test result constitutes a listening verdict."""
from copy import deepcopy

import pytest

from modules.music.catalog import (
    BAR, VERTICAL_SOURCE_HASHES, build_vertical_score, digest,
    eligible_arrival_boundaries, get_composition, get_groove,
)
from modules.music.events import apply_swing, resolve_events, ticks_to_seconds, transpose_events
from scenescore.contracts import validate_bundle


def test_ending_retains_source_identity_rhythm_and_canonical_contracts():
    source = get_composition('tilted_blue_v1')
    score = build_vertical_score()
    composition, groove = score['composition'], score['groove']
    validate_bundle([composition, groove])
    assert digest(source) == VERTICAL_SOURCE_HASHES['composition_sha256']
    assert digest(groove) == VERTICAL_SOURCE_HASHES['groove_sha256']
    assert score == build_vertical_score()
    assert composition != source
    assert get_composition('tilted_blue_v1') == source
    assert len(composition['notes']) == len(source['notes'])
    changes = []
    for before, after in zip(source['notes'], composition['notes']):
        assert {k: v for k, v in before.items() if k != 'midi_pitch'} == {
            k: v for k, v in after.items() if k != 'midi_pitch'}
        if before != after:
            changes.append(after)
    assert len(changes) == 2
    assert 1 - len(changes) / len(source['notes']) >= .95
    assert all(n['start_tick'] >= 11 * BAR for n in changes)
    assert composition['harmony'][:-2] == source['harmony'][:-2]
    assert [(c['start_tick'], c['duration_ticks']) for c in composition['harmony']] == [
        (c['start_tick'], c['duration_ticks']) for c in source['harmony']]
    assert composition['notes'][-1]['midi_pitch'] == 60
    assert composition['harmony'][-1]['root_pc'] == 0
    assert score['sidecar']['approval'] is None
    assert score['sidecar']['audition_status'] == 'AUDITION_PENDING'
    assert composition['length_ticks'] == sum(c['duration_ticks'] for c in composition['harmony']) == 12 * BAR
    assert ticks_to_seconds(composition['length_ticks'], composition['tempo_map']) == 30


def test_arrival_coverage_uses_internal_bars_and_includes_both_edges():
    score = build_vertical_score()
    sidecar = score['sidecar']
    assert sidecar['eligible_arrival_ticks'] == list(range(BAR, 12 * BAR, BAR))
    assert sidecar['eligible_arrival_seconds'] == [2.5 * n for n in range(1, 12)]
    assert sidecar['terminal_s'] == 30 and not sidecar['terminal_is_eligible']
    assert sidecar['maximum_gap_including_edges_s'] == 2.5
    slow = deepcopy(score['composition'])
    slow['tempo_map'] = [{'tick': 0, 'bpm': 48}]
    with pytest.raises(ValueError, match='coverage_gap'):
        eligible_arrival_boundaries(slow)
    segmented = deepcopy(score['composition'])
    segmented['tempo_map'].append({'tick': 4 * BAR, 'bpm': 120})
    boundaries = eligible_arrival_boundaries(segmented)
    assert boundaries['eligible_arrival_seconds'][3:5] == [10, 12]
    assert boundaries['terminal_s'] == 26
    for bad in (0, 4.1, float('nan'), True):
        with pytest.raises(ValueError, match='gap_budget'):
            eligible_arrival_boundaries(score['composition'], max_gap_s=bad)


def test_ending_events_ranges_swing_once_and_brush_transposition_invariance():
    score = build_vertical_score()
    composition, groove = score['composition'], score['groove']
    events = resolve_events(composition, groove)
    assert events == resolve_events(composition, groove)
    for boundary in score['sidecar']['eligible_arrival_seconds']:
        assert not any(e['resolved_time_s'] < boundary - 1e-9 <
                       e['resolved_time_s'] + e['duration_s'] - 1e-9
                       for e in events if e['event_type'] == 'note')
    for event in events:
        assert 0 <= event['resolved_time_s'] < event['resolved_time_s'] + event['duration_s'] <= 30 + 1e-9
        assert 1 <= event['velocity'] <= 127
        if event['event_type'] == 'note':
            assert 28 <= event['midi_pitch'] <= 96
        if event['swing_application_count']:
            with pytest.raises(ValueError, match='already_applied'):
                apply_swing(event, composition['swing_ratio'], composition['tempo_map'])
    for shift in (-2, 2):
        for before, after in zip(events, transpose_events(events, shift)):
            if before['event_type'] == 'brush':
                assert before == after
    original_events = resolve_events(get_composition('tilted_blue_v1'), groove)
    original_brushes = [{k: v for k, v in e.items() if k != 'provenance'}
                        for e in original_events if e['event_type'] == 'brush']
    ending_brushes = [{k: v for k, v in e.items() if k != 'provenance'}
                      for e in events if e['event_type'] == 'brush']
    assert ending_brushes == original_brushes


def test_vertical_rejects_unknown_or_mismatched_catalogue_and_duration():
    for kwargs in ({'groove_id': 'missing'}, {'groove_version': 2}, {'groove_version': True},
                   {'composition_id': 'velvet_orbit_v1'}, {'duration_s': 29.99}):
        with pytest.raises(ValueError):
            build_vertical_score(**kwargs)
    score = build_vertical_score()
    with pytest.raises(ValueError, match='reference_mismatch'):
        resolve_events(score['composition'], get_groove('brush_straight_rag_v1'))
