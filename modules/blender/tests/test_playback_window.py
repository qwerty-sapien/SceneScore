"""Synthetic canonical score fixtures; no music audition or audio render claim."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from modules.blender.production.playback import create_playback_window, encode_playback_window


def event(ident, start, length):
    source = Path(__file__).resolve().parents[3]/'fixtures/contracts/ScoreEvent.json'
    item = json.loads(source.read_text())
    item.update(id=ident, resolved_time_s=start, duration_s=length)
    return item


def encoded(events):
    return (json.dumps(events, sort_keys=True, separators=(',', ':'))+'\n').encode()


def test_half_open_window_preserves_events_and_records_end_truncation():
    events = [event('starts-at-zero', 0, .25), event('ends-at-right', .75, .25),
              event('crosses-right', .9, .3), event('at-right', 1, .1), event('after', 2, 1)]
    original = deepcopy(events)
    raw = encoded(events)
    window, sha = create_playback_window(raw, 1, frame_count=30)
    assert events == original and raw == encoded(original)
    assert window['projections'] == [
        {'source_event_id': 'starts-at-zero', 'start_s': 0, 'stop_s': .25, 'source_offset_s': 0},
        {'source_event_id': 'ends-at-right', 'start_s': .75, 'stop_s': 1., 'source_offset_s': 0},
        {'source_event_id': 'crosses-right', 'start_s': .9, 'stop_s': 1, 'source_offset_s': 0}]
    assert [x['source_event_id'] for x in window['omitted']] == ['at-right', 'after']
    assert len(window['truncated']) == 1
    assert window['truncated'][0]['removed_after_s'] == pytest.approx(.2)
    assert window['audio_sample_count'] == 48000
    assert window['final_fade_s'] == .01 and window['approval'] is None
    assert window['label'] == 'Draft · existing score excerpt · adaptive scoring pending'
    assert sha == hashlib.sha256(encode_playback_window(window)).hexdigest()
    assert window['original_events_sha256'] == hashlib.sha256(raw).hexdigest()


def test_hash_binds_exact_source_bytes_and_is_repeatable():
    events = [event('whole', 0, 4)]
    raw = encoded(events)
    compact = json.dumps(events).encode()
    first, first_hash = create_playback_window(raw, 1/30)
    assert create_playback_window(raw, 1/30) == (first, first_hash)
    second, second_hash = create_playback_window(compact, 1/30)
    assert first['projections'] == second['projections']
    assert first_hash != second_hash
    assert first['audio_sample_count'] == 1600 and first['frame_count'] == 1


def test_empty_original_score_is_a_valid_silent_window():
    window, _ = create_playback_window(b'[]\n', 2)
    assert window['projections'] == window['omitted'] == window['truncated'] == []


@pytest.mark.parametrize('duration, frames', [(0, None), (-1, None), (.05, None),
                                            (1, 29), (1, True), (float('nan'), None),
                                            (float('inf'), None), (1e308, None)])
def test_rejects_invalid_or_mismatched_native_clock(duration, frames):
    with pytest.raises(ValueError):
        create_playback_window(b'[]', duration, frame_count=frames)


def test_negative_start_is_not_rewritten_into_valid_canonical_music():
    # Crossing a nonzero excerpt origin is out of this v1. Canonical events cannot
    # begin before zero, so refuse rather than silently repairing the source.
    with pytest.raises(ValueError):
        create_playback_window(encoded([event('crosses-left', -.1, .5)]), 1)


@pytest.mark.parametrize('change', ['duplicate_id', 'zero_duration', 'nonfinite', 'wrong_kind'])
def test_rejects_invalid_original_events(change):
    events = [event('a', 0, .5)]
    if change == 'duplicate_id':
        events.append(deepcopy(events[0]))
    elif change == 'zero_duration':
        events[0]['duration_s'] = 0
    elif change == 'nonfinite':
        events[0]['resolved_time_s'] = float('nan')
    else:
        events[0]['kind'] = 'ObjectState'
    with pytest.raises(ValueError):
        create_playback_window(encoded(events), 1)


def test_only_exact_json_array_bytes_are_accepted():
    with pytest.raises(TypeError):
        create_playback_window([], 1)
    for raw in (b'{"events":[]}', b'null', b'not JSON', b'[{}]\n[{}]'):
        with pytest.raises(ValueError):
            create_playback_window(raw, 1)
