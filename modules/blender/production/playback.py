"""Hashed draft playback bounds; original canonical score events remain intact.

The shared audio runtime applies a linear master fade from duration-0.01 seconds
to zero gain at duration, identically for playback, mix and stems. This module
describes that window; it never alters notes, articulation, tempo or audio.
"""
import hashlib
import json
import math

from scenescore.contracts import validate


VERSION = 'scene-playback-window-1'
LABEL = 'Draft · existing score excerpt · adaptive scoring pending'


def encode_playback_window(window: dict) -> bytes:
    """Exact persisted-byte representation, matching arranger ``encoded``."""
    return (json.dumps(window, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def _finite_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(field+' must be a finite number')
    return value


def _invalid_constant(value):
    raise ValueError('non-finite JSON constant: '+value)


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field: '+key)
        result[key] = value
    return result


def create_playback_window(original_events_json: bytes, duration_s: float, *, frame_count: int | None = None):
    """Return ``(window, sha256(encode_playback_window(window)))``.

    ``original_events_json`` is the exact UTF-8 JSON array of complete original
    canonical ScoreEvents. Its persisted bytes, including whitespace/order, are
    hashed unchanged. Source time zero maps to scene time zero. Negative source
    times are invalid canonical events; this v1 does not introduce a score offset.
    ``frame_count`` may be supplied to check the finalized video's declared clock.
    """
    if not isinstance(original_events_json, bytes):
        raise TypeError('provide exact original event JSON bytes')
    duration_s = _finite_number(duration_s, 'duration_s')
    if duration_s <= 0:
        raise ValueError('duration_s must be positive')
    if duration_s > (2**53-1)/48000:
        raise ValueError('audio sample count exceeds exact browser integer range')
    inferred = round(duration_s*30)
    if frame_count is None:
        frame_count = inferred
    if (isinstance(frame_count, bool) or not isinstance(frame_count, int) or frame_count < 1
            or abs(frame_count/30-duration_s) > 1e-9):
        raise ValueError('scene duration/frame count must match native 30 fps')
    if frame_count*1600 > 2**53-1:
        raise ValueError('audio sample count exceeds exact browser integer range')
    try:
        events = json.loads(original_events_json, parse_constant=_invalid_constant, object_pairs_hook=_unique_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('original events must be a UTF-8 JSON array') from exc
    if not isinstance(events, list):
        raise ValueError('original events must be a canonical ScoreEvent list')
    identifiers = set()
    projections, omitted, truncated = [], [], []
    for event in events:
        if not isinstance(event, dict) or event.get('kind') != 'ScoreEvent':
            raise ValueError('original event is not a canonical ScoreEvent')
        validate(event)
        oid = event['id']
        if oid in identifiers:
            raise ValueError('duplicate source event ID: '+oid)
        identifiers.add(oid)
        start = _finite_number(event['resolved_time_s'], 'resolved_time_s')
        length = _finite_number(event['duration_s'], 'event duration_s')
        stop = _finite_number(start+length, 'source stop_s')
        if start < 0 or length <= 0:
            raise ValueError('source event times must be nonnegative with positive duration')
        if start >= duration_s:
            omitted.append({'source_event_id': oid, 'source_start_s': start, 'source_stop_s': stop,
                            'reason': 'starts_at_or_after_scene_end'})
            continue
        # Canonical source starts are >=0, hence source_offset_s is zero in v1.
        projection = {'source_event_id': oid, 'start_s': start, 'stop_s': min(stop, duration_s),
                      'source_offset_s': 0}
        projections.append(projection)
        if stop > duration_s:
            truncated.append({'source_event_id': oid, 'source_start_s': start, 'source_stop_s': stop,
                              'playback_stop_s': duration_s, 'removed_before_s': 0,
                              'removed_after_s': stop-duration_s, 'reason': 'crosses_scene_end'})
    window = {'version': VERSION, 'start_s': 0, 'duration_s': duration_s, 'frame_count': frame_count,
              'render_fps': 30, 'sample_rate_hz': 48000, 'audio_sample_count': frame_count*1600,
              'final_fade_s': .01, 'original_events_sha256': hashlib.sha256(original_events_json).hexdigest(),
              'label': LABEL, 'approval': None, 'projections': projections, 'omitted': omitted,
              'truncated': truncated}
    return window, hashlib.sha256(encode_playback_window(window)).hexdigest()
