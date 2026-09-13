"""Compact local geometry views. No vertices or EEG are sent to a model."""
import json
import hashlib
import math
from bisect import bisect_left, bisect_right
from collections import defaultdict
from pathlib import Path

from modules.blender.geometry import gap, norm, normal_speed, sphere_sweep, sub


def _lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def compact_summary(bundle_dir):
    return json.loads((Path(bundle_dir)/'summary.json').read_text())


def event_query(bundle_dir, event_id):
    matches=[e for e in _lines(Path(bundle_dir)/'interactions.jsonl') if e['id']==event_id]
    if len(matches)!=1:
        raise KeyError(event_id)
    return matches[0]


def state_query(bundle_dir, state_id):
    matches=[e for e in _lines(Path(bundle_dir)/'object_states.jsonl') if e['id']==state_id]
    if len(matches)!=1:
        raise KeyError(state_id)
    return matches[0]


# Module supplement only: canonical ObjectState/InteractionEvent 0.1 is unchanged.
MUSIC_SEMANTICS_VERSION = 'blender-music-semantics-2'
MUSIC_SEMANTICS_DEFAULTS = {
    'approach_ref_speed_m_s': 2.0,
    'near_miss_ref_gap_m': 0.5,
    'contact_ref_speed_m_s': 3.0,
    'sustain_ref_s': 1.0,
    'contact_dedupe_s': 0.03,
    'rebound_min_area_ratio': 4.0,
    'rebound_min_speed_m_s': 0.05,
    'rebound_window_s': 0.25,
}
_EVENT_TYPES = frozenset(('approach', 'near_miss', 'separation', 'contact_onset',
                          'contact_sustain', 'contact_release', 'collision'))
_EVALUATED_METHODS = frozenset((
    'evaluated dependency graph, transformed mesh loop triangles',
    'synthetic evaluated world mesh triangles',
))


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _number(value, name, *, nullable=False, minimum=None):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite')
    if minimum is not None and value < minimum:
        raise ValueError(f'{name} must be >= {minimum}')
    return value


def _configuration(config):
    config = {} if config is None else dict(config)
    if set(config) - MUSIC_SEMANTICS_DEFAULTS.keys():
        raise ValueError('unknown music-semantics configuration field')
    result = {**MUSIC_SEMANTICS_DEFAULTS, **config}
    for name, value in result.items():
        _number(value, name, minimum=0)
        if value == 0 and name != 'contact_dedupe_s':
            raise ValueError(f'{name} must be positive')
    if result['rebound_min_area_ratio'] <= 1:
        raise ValueError('rebound_min_area_ratio must distinguish smaller and larger areas')
    return result


def _clamp(value, upper=1.0):
    return min(upper, max(0.0, value))


def _state_index(scene, states):
    known = {obj['object_id'] for obj in scene['objects']}
    if len(known) != len(scene['objects']):
        raise ValueError('duplicate scene object id')
    index = defaultdict(dict)
    ids = set()
    for state in states:
        if state.get('schema_version') != '0.1' or state.get('kind') != 'ObjectState':
            raise ValueError('music semantics requires canonical ObjectState 0.1')
        if state['scene_id'] != scene['id'] or state['object_id'] not in known:
            raise ValueError('unknown state scene/object reference')
        t = _number(state['scene_time_s'], 'state scene seconds', minimum=0)
        if t > scene['duration_s']:
            raise ValueError('state outside scene coverage')
        if state['id'] in ids or t in index[state['object_id']]:
            raise ValueError('duplicate state id/time')
        ids.add(state['id'])
        pos = state['transform']['position_m']
        if len(pos) != 3:
            raise ValueError('state position must be world XYZ metres')
        for value in pos:
            _number(value, 'state position')
        _number(state.get('surface_area_m2'), 'evaluated surface area', nullable=True, minimum=0)
        index[state['object_id']][t] = state
    return index


def _pair_samples(pair, state_index):
    first, second = (state_index[oid] for oid in pair)
    times = sorted(first.keys() & second.keys())
    return times, [(first[t], second[t]) for t in times]


def _segment_motion(times, samples, t, side, max_gap):
    """No extrapolation, nearest unrelated state or skipped missing interval."""
    if side == 'before':
        right = bisect_left(times, t)
        # An exact first state has no incoming segment.
        if right == 0:
            return None, None, 'normal_before_out_of_coverage'
    else:
        right = bisect_right(times, t)
    if right >= len(times) or t < times[right-1] or t > times[right]:
        return None, None, f'normal_{side}_out_of_coverage'
    left = right-1
    duration = times[right]-times[left]
    if duration > max_gap+1e-9:
        return None, None, 'state_sampling_gap'
    fraction = (t-times[left])/duration
    a0, b0 = (state['transform']['position_m'] for state in samples[left])
    a1, b1 = (state['transform']['position_m'] for state in samples[right])
    value = normal_speed(a0, a1, b0, b1, duration, fraction)
    evidence = {'interval_s': [times[left], times[right]], 'fraction': fraction,
                'state_ids': [s['id'] for row in samples[left:right+1] for s in row]}
    return value, evidence, 'normal_axis_undefined' if value is None else None


def _area_at(times, samples, t, max_gap, geometry_objects):
    right = bisect_left(times, t)
    if right < len(times) and times[right] == t:
        rows = [samples[right]]
    elif right and right < len(times) and times[right]-times[right-1] <= max_gap+1e-9:
        rows = samples[right-1:right+1]
    else:
        return None, 'evaluated_area_out_of_coverage'
    result = {}
    for column in (0, 1):
        states = [row[column] for row in rows]
        oid = states[0]['object_id']
        meta = geometry_objects.get(oid, {})
        if meta.get('geometry_method') not in _EVALUATED_METHODS:
            return None, 'evaluated_mesh_area_provenance_missing'
        values = [state.get('surface_area_m2') for state in states]
        if any(value is None or value <= 0 for value in values):
            return None, 'evaluated_area_unavailable'
        # Never interpolate a changing mesh area to a swept sub-sample contact.
        if any(value != values[0] for value in values):
            return None, 'changing_evaluated_area_at_subsample'
        result[oid] = values[0]
    return result, None


def _near_miss_certificate(event, minimum, times, samples, max_gap, geometry_objects):
    """Recheck the bracket and every segment; positive samples alone prove nothing."""
    start, end = event['onset_s'], event['onset_s']+event['duration_s']
    if minimum is None or not start < minimum < end:
        return False, 'positive_bracketed_near_miss_evidence_missing', None
    left, right = bisect_left(times, start), bisect_left(times, end)
    if right >= len(times) or times[left] != start or times[right] != end or minimum not in times[left:right+1]:
        return False, 'near_miss_bracket_out_of_coverage', None
    if any(b-a > max_gap+1e-9 for a, b in zip(times[left:right], times[left+1:right+1])):
        return False, 'state_sampling_gap', None
    tolerance = event.get('uncertainty_m')
    if tolerance is None:
        return False, 'near_miss_uncertainty_unavailable', None
    _number(tolerance, 'near-miss uncertainty metres', minimum=0)
    tolerance = max(tolerance, 1e-9)
    proxies, positions, gaps = [], [], []
    for row in samples[left:right+1]:
        proxy_row, position_row = [], []
        for state in row:
            meta = geometry_objects.get(state['object_id'], {})
            if meta.get('geometry_method') not in _EVALUATED_METHODS or meta.get('shape') not in ('sphere', 'box'):
                return False, 'near_miss_proxy_provenance_missing', None
            lo, hi = state.get('bounds_min_m'), state.get('bounds_max_m')
            if lo is None or hi is None or len(lo) != 3 or len(hi) != 3:
                return False, 'near_miss_evaluated_bounds_missing', None
            for value in [*lo, *hi]:
                _number(value, 'evaluated world bounds')
            half = [(high-low)/2 for low, high in zip(lo, hi)]
            if min(half) <= 0:
                return False, 'near_miss_proxy_bounds_degenerate', None
            proxy_row.append({'shape': 'sphere', 'radius': max(half)} if meta['shape'] == 'sphere'
                             else {'shape': 'box', 'half': half})
            position_row.append([(low+high)/2 for low, high in zip(lo, hi)])
        proxies.append(proxy_row)
        positions.append(position_row)
        value, _ = gap(proxy_row[0], position_row[0], proxy_row[1], position_row[1])
        gaps.append(value)
    minimum_index = times[left:right+1].index(minimum)
    claimed_gap = event.get('surface_gap_m')
    if (claimed_gap is None or min(gaps) <= tolerance or gaps[0] <= gaps[minimum_index]+tolerance
            or gaps[-1] <= gaps[minimum_index]+tolerance
            or abs(gaps[minimum_index]-min(gaps)) > tolerance
            or abs(gaps[minimum_index]-claimed_gap) > 4*tolerance):
        return False, 'positive_bracketed_near_miss_evidence_missing', None
    sphere_pair = all(proxy['shape'] == 'sphere' for proxy in proxies[0])
    for i in range(1, len(positions)):
        # A rotating/deforming AABB is not a fixed shape proxy. No such claim.
        for before, after in zip(proxies[i-1], proxies[i]):
            a = [before['radius']] if before['shape'] == 'sphere' else before['half']
            b = [after['radius']] if after['shape'] == 'sphere' else after['half']
            if any(abs(x-y) > tolerance for x, y in zip(a, b)):
                return False, 'changing_proxy_bounds_not_certified', None
        a0, b0 = positions[i-1]
        a1, b1 = positions[i]
        if sphere_pair:
            radius = max(proxies[i-1][0]['radius'], proxies[i][0]['radius'])+max(proxies[i-1][1]['radius'], proxies[i][1]['radius'])
            safe = sphere_sweep(a0, a1, b0, b1, radius) is None
        else:
            displacement = norm(sub(sub(a1, a0), sub(b1, b0)))
            safe = min(gaps[i-1], gaps[i])-displacement > tolerance
        if not safe:
            return False, 'near_miss_segment_not_certified', None
    return True, None, {'method': 'sphere_sweep_exact' if sphere_pair else 'fixed_proxy_lipschitz_gap_bound',
                        'segment_count': len(positions)-1, 'interval_s': [start, end],
                        'minimum_sample_gap_m': gaps[minimum_index], 'uncertainty_m': tolerance,
                        'scope': 'piecewise linear evaluated segments; no sub-frame perceptual timing claim'}


def _dedupe_contacts(events, window):
    """One-to-one same-pair/same-loop match; a sweep keeps its exact timestamp."""
    removed = {}
    for collision in (e for e in events if e['event_type'] == 'collision'):
        choices = [e for e in events if e['event_type'] == 'contact_onset'
                   and e['id'] not in removed and e['pair_id'] == collision['pair_id']
                   and e['loop_instance'] == collision['loop_instance']
                   and abs(e['onset_s']-collision['onset_s']) <= window+1e-12]
        if choices:
            onset = min(choices, key=lambda e: (abs(e['onset_s']-collision['onset_s']), e['id']))
            removed[onset['id']] = collision['id']
    return removed


def motion_semantics_summary(scene, states, events, *, geometry=None, config=None):
    """Build deterministic music drivers over evaluated canonical records, offline.

    Output events are module-versioned supplements, never canonical records. The
    caller binds the returned input/config hashes in its plan. A null driver MUST
    leave the original score unchanged. `near_miss.minimum_s` is the resolution
    time; its canonical `onset_s` is the earlier bracket start. `geometry` is the
    exact evaluated bundle's geometry.json, required to establish mesh-area and
    bracket provenance. This function does not rerun recipes or alter input data.
    """
    config = _configuration(config)
    if scene.get('schema_version') != '0.1' or scene.get('kind') != 'SceneManifest':
        raise ValueError('music semantics requires canonical SceneManifest 0.1')
    if (scene.get('units'), scene.get('handedness'), scene.get('up_axis')) != ('metres', 'right', 'Z'):
        raise ValueError('music semantics requires right-handed world XYZ metres, Z up')
    _number(scene['duration_s'], 'scene duration', minimum=0)
    for name in ('fps', 'fps_base'):
        if _number(scene[name], name, minimum=0) == 0:
            raise ValueError('source cadence must be positive')
    max_gap = scene['fps_base']/scene['fps']
    states = sorted(states, key=lambda s: (s['object_id'], s['scene_time_s'], s['id']))
    events = sorted(events, key=lambda e: (e['onset_s'], e['pair_id'], e['event_type'], e['id']))
    state_index = _state_index(scene, states)
    known = {obj['object_id'] for obj in scene['objects']}
    event_ids = set()
    for event in events:
        if event.get('schema_version') != '0.1' or event.get('kind') != 'InteractionEvent':
            raise ValueError('music semantics requires canonical InteractionEvent 0.1')
        if event['event_type'] not in _EVENT_TYPES:
            raise ValueError('rebound must be derived from a triggering canonical contact')
        pair = event['pair']
        if (event['scene_id'] != scene['id'] or len(pair) != 2 or pair != sorted(set(pair))
                or set(pair)-known or event['pair_id'] != '|'.join(pair)):
            raise ValueError('unknown/invalid event scene or pair reference')
        if event['id'] in event_ids:
            raise ValueError('duplicate event id')
        event_ids.add(event['id'])
        _number(event['onset_s'], 'event onset', minimum=0)
        _number(event['duration_s'], 'event duration', minimum=0)
        if event['onset_s']+event['duration_s'] > scene['duration_s']+1e-9:
            raise ValueError('event outside scene coverage')
        for field in ('relative_normal_speed_m_s', 'surface_gap_m'):
            _number(event.get(field), field, nullable=True)
    geometry = {} if geometry is None else geometry
    if geometry and geometry.get('geometry_version') != 'blender-geometry-1':
        raise ValueError('unsupported geometry supplement version')
    geometry_objects = {obj['object_id']: obj for obj in geometry.get('objects', [])}
    details = {item['id']: item for item in geometry.get('event_details', [])}
    if (len(geometry_objects) != len(geometry.get('objects', []))
            or len(details) != len(geometry.get('event_details', []))
            or set(geometry_objects)-known or set(details)-event_ids):
        raise ValueError('duplicate/unknown geometry supplement reference')
    removed = _dedupe_contacts(events, config['contact_dedupe_s'])
    supplements, suppressed = [], []
    pairs = {}
    for event in events:
        if event['id'] in removed:
            suppressed.append({'source_event_id': event['id'], 'event_type': 'contact_onset',
                               'reason': 'deduplicated_contact_onset', 'kept_event_id': removed[event['id']]})
            continue
        pair_id, t, kind = event['pair_id'], event['onset_s'], event['event_type']
        if pair_id not in pairs:
            pairs[pair_id] = _pair_samples(event['pair'], state_index)
        times, samples = pairs[pair_id]
        before, before_evidence, before_reason = _segment_motion(times, samples, t, 'before', max_gap)
        after, after_evidence, after_reason = _segment_motion(times, samples, t, 'after', max_gap)
        source_ids = [event['id']] + sorted(key for key, value in removed.items() if value == event['id'])
        out = {'id': f'{event["id"]}:music-v2', 'source_event_id': event['id'], 'source_event_ids': source_ids,
               'event_type': kind, 'scene_id': scene['id'], 'pair': list(event['pair']), 'pair_id': pair_id,
               'loop_instance': event['loop_instance'], 'onset_s': t, 'duration_s': event['duration_s'],
               'driver': None, 'driver_reason': None, 'inputs': {},
               'method': 'swept_sphere_exact' if kind == 'collision' else 'canonical_event_evaluated_states',
               'clock': 'scene', 'epoch': scene['id'], 'mass_inferred': False, 'restitution_claimed': False}
        if kind == 'approach':
            # pair_timeline's approach scalar is sampled at the bracket minimum.
            value = event.get('relative_normal_speed_m_s')
            out['inputs'] = {'normal_m_s': value, 'closing_rate_m_s': None if value is None else max(0., -value),
                             'sample_origin': 'canonical bracket-minimum sample; offline episode descriptor',
                             'causal_conducting_input': False}
            out['driver'] = None if value is None else _clamp(-value/config['approach_ref_speed_m_s'])
            out['driver_reason'] = 'normal_before_unavailable' if value is None else None
        elif kind == 'near_miss':
            gap = event.get('surface_gap_m')
            minimum = details.get(event['id'], {}).get('minimum_gap_time_s')
            if minimum is not None:
                _number(minimum, 'near-miss minimum scene seconds')
            certified, reason, certificate = _near_miss_certificate(event, minimum, times, samples, max_gap, geometry_objects)
            out['minimum_s'] = minimum
            out['certified_no_tunnelling'] = certified
            out['certification'] = {**(certificate or {}), 'source_event_id': event['id'],
                                    'geometry_method': details.get(event['id'], {}).get('geometry_method')}
            out['inputs'] = {'min_gap_m': gap, 'closeness': _clamp(1-gap/config['near_miss_ref_gap_m']) if certified else None}
            out['driver'] = out['inputs']['closeness']
            out['driver_reason'] = reason
        elif kind == 'contact_sustain':
            out['inputs'] = {'duration_s': event['duration_s']}
            out['driver'] = _clamp(event['duration_s']/config['sustain_ref_s'])
        else:
            use_after = kind == 'separation'
            # Release is the first sample AFTER contact: its incoming interval
            # contains the opening motion, not its following (possibly idle) one.
            value, evidence, reason = (after, after_evidence, after_reason) if use_after else (before, before_evidence, before_reason)
            name = 'normal_after_m_s' if kind in ('separation', 'contact_release') else 'normal_before_m_s'
            out['inputs'] = {name: value, 'motion_evidence': evidence}
            ref = config['approach_ref_speed_m_s'] if use_after else config['contact_ref_speed_m_s']
            out['driver'] = None if value is None else _clamp((max(0., value) if use_after else abs(value))/ref)
            out['driver_reason'] = reason
        if out['driver'] is None:
            suppressed.append({'source_event_id': event['id'], 'event_type': kind, 'reason': out['driver_reason'],
                               'fallback': 'unmodified_score'})
        supplements.append(out)
        if kind not in ('contact_onset', 'collision'):
            continue
        areas, area_reason = _area_at(times, samples, t, max_gap, geometry_objects)
        retention = None if before is None or abs(before) < config['rebound_min_speed_m_s'] or after is None else _clamp(abs(after)/abs(before), 1.5)
        ratio = None if areas is None else max(areas.values())/min(areas.values())
        reason = area_reason or before_reason or after_reason
        if reason is None and (t-before_evidence['interval_s'][0] > config['rebound_window_s']+1e-9
                               or after_evidence['interval_s'][1]-t > config['rebound_window_s']+1e-9):
            reason = 'rebound_velocity_window_out_of_coverage'
        if reason is None and ratio < config['rebound_min_area_ratio']:
            reason = 'area_ratio_below_rebound_threshold'
        if reason is None and (before >= 0 or after <= 0):
            reason = 'normal_velocity_did_not_reverse'
        if reason is None and min(abs(before), abs(after)) < config['rebound_min_speed_m_s']:
            reason = 'normal_speed_below_rebound_floor'
        evidence = {'normal_before_m_s': before, 'normal_after_m_s': after,
                    'before': before_evidence, 'after': after_evidence, 'evaluated_areas_m2': areas}
        if reason:
            suppressed.append({'source_event_id': event['id'], 'event_type': 'asymmetric_rebound',
                               'reason': reason, 'speed_retention': retention, 'area_ratio': ratio,
                               'inputs': evidence, 'fallback': 'no_rebound_decoration'})
            continue
        smaller, larger = sorted(areas, key=lambda oid: (areas[oid], oid))
        supplements.append({**out, 'id': f'{event["id"]}:rebound-v2', 'event_type': 'asymmetric_rebound',
                            'duration_s': 0., 'driver': _clamp(abs(before)/config['contact_ref_speed_m_s']),
                            'driver_reason': None, 'inputs': evidence, 'trigger_event_id': event['id'],
                            'rebounding_object_id': smaller, 'anchor_object_id': larger, 'area_ratio': ratio,
                            'speed_retention': retention, 'method': 'evaluated_area_ratio_proxy',
                            'mass_inferred': False, 'restitution_claimed': False})
    # A chain annotation is a downstream budget hint, never an additional event.
    chains = {}
    for out in sorted(supplements, key=lambda e: (e['onset_s'], e['event_type'], e['id'])):
        if out['event_type'] == 'asymmetric_rebound':
            key = (out['pair_id'], out['loop_instance'])
            previous = chains.get(key)
            ordinal = previous['chain_index']+1 if previous and out['onset_s']-previous['onset_s'] <= config['rebound_window_s'] else 0
            out['chain_index'] = ordinal
            out['chain_id'] = previous['chain_id'] if ordinal else out['id']
            chains[key] = out
    return {'module_version': MUSIC_SEMANTICS_VERSION, 'scene_id': scene['id'], 'config': config,
            'config_hash': _hash(config), 'events': sorted(supplements, key=lambda e: (e['onset_s'], e['event_type'], e['id'])),
            'suppressed': suppressed,
            'provenance': {'creator': MUSIC_SEMANTICS_VERSION, 'source_mode': scene['provenance']['source_mode'],
                           'source_cadence_fps': scene['fps']/scene['fps_base'], 'clock': 'scene', 'epoch': scene['id'],
                           'source_generator_version': scene.get('generator_version'),
                           'source_exporter_hash': scene.get('source_hash'),
                           'scene_hash': _hash(scene), 'states_hash': _hash(states), 'events_hash': _hash(events),
                           'geometry_hash': _hash(geometry), 'config_hash': _hash(config),
                           'mapping': 'explicit creative kinematics, no inferred physics or emotion',
                           'approval': None, 'audition_status': 'AUDITION_PENDING'}}


def music_summary(bundle_dir, config=None):
    """Load a local bundle for the pure music-semantics supplement function."""
    bundle = Path(bundle_dir)
    geometry_path = bundle/'geometry.json'
    result = motion_semantics_summary(json.loads((bundle/'manifest.json').read_text()),
                                      _lines(bundle/'object_states.jsonl'), _lines(bundle/'interactions.jsonl'),
                                      geometry=json.loads(geometry_path.read_text()) if geometry_path.is_file() else None,
                                      config=config)
    names = ['manifest.json', 'object_states.jsonl', 'interactions.jsonl']
    if geometry_path.is_file():
        names.append('geometry.json')
    result['provenance']['input_file_hashes'] = {
        name: hashlib.sha256((bundle/name).read_bytes()).hexdigest() for name in names}
    return result
