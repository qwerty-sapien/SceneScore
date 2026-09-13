"""Bounded offline performance edits inside already-resolved source-note slots.

No rendering, approval, model call or real-time scheduling occurs here. Optional runs
and duration-extending figures are deliberately absent from this version.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
import math
import random
from typing import Literal

from scenescore.contracts import validate
from .catalog import digest
from .events import ticks_to_seconds

VERSION = 'music-ornament-1'
Kind = Literal['articulation', 'velocity', 'grace', 'mordent', 'turn', 'trill',
               'tremolo', 'octave_doubling', 'chord_redistribution', 'arpeggio']
KINDS = tuple(Kind.__args__)
DECORATIONS = frozenset(KINDS) - {'articulation', 'velocity'}
ARTICULATIONS = ('detached', 'staccato', 'tenuto', 'legato')


@dataclass(frozen=True)
class TransformRequest:
    event_id: str
    kind: Kind
    preserves_duration: bool = True
    articulation: str | None = None
    velocity_delta: int = 0
    direction: int = 1
    subdivisions: int = 4
    probability: float = 1.0
    related_event_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.event_id, str) or not self.event_id or self.kind not in KINDS:
            raise ValueError('invalid_transform_target_or_kind')
        if self.preserves_duration is not True:
            raise ValueError('duration_extending_transform_not_enabled')
        if self.kind == 'articulation':
            if self.articulation not in ARTICULATIONS:
                raise ValueError('unsupported_articulation')
        elif self.articulation is not None:
            raise ValueError('articulation_parameter_on_other_lane')
        if type(self.velocity_delta) is not int or not -32 <= self.velocity_delta <= 32:
            raise ValueError('invalid_velocity_delta')
        if self.kind != 'velocity' and self.velocity_delta:
            raise ValueError('velocity_parameter_on_other_lane')
        if type(self.direction) is not int or self.direction not in (-1, 1):
            raise ValueError('invalid_ornament_direction')
        if type(self.subdivisions) is not int or not 2 <= self.subdivisions <= 8:
            raise ValueError('invalid_ornament_subdivisions')
        if (isinstance(self.probability, bool) or not isinstance(self.probability, (int, float)) or
                not math.isfinite(self.probability) or not 0 <= self.probability <= 1):
            raise ValueError('invalid_transform_probability')
        if (not isinstance(self.related_event_ids, (tuple, list)) or
                any(not isinstance(x, str) or not x for x in self.related_event_ids)):
            raise ValueError('invalid_related_event_ids')
        object.__setattr__(self, 'related_event_ids', tuple(self.related_event_ids))
        if len(set((self.event_id, *self.related_event_ids))) != 1 + len(self.related_event_ids):
            raise ValueError('duplicate_transform_target')
        if self.related_event_ids and self.kind not in ('chord_redistribution', 'arpeggio'):
            raise ValueError('group_parameter_on_single_note_transform')
        if len(self.related_event_ids) > 3:
            raise ValueError('chord_voice_budget')


@dataclass(frozen=True)
class TransformBudgets:
    max_events_per_second_added: int = 12
    max_simultaneous_ornaments: int = 2
    max_events_per_bar: int = 96
    min_pitch: int = 28
    max_pitch: int = 96
    low_register_floor: int = 48
    min_low_interval: int = 5
    min_note_duration_s: float = .025
    max_requests: int = 256

    def __post_init__(self):
        bounds = {'max_events_per_second_added': (0, 12), 'max_simultaneous_ornaments': (1, 2),
                  'max_events_per_bar': (1, 256), 'min_pitch': (28, 96), 'max_pitch': (28, 96),
                  'low_register_floor': (36, 60), 'min_low_interval': (3, 12), 'max_requests': (1, 512)}
        for name, (lo, hi) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not lo <= value <= hi:
                raise ValueError('invalid_transform_budget:' + name)
        if self.min_pitch > self.max_pitch:
            raise ValueError('invalid_transform_register')
        if (isinstance(self.min_note_duration_s, bool) or
                not math.isfinite(self.min_note_duration_s) or not .015 <= self.min_note_duration_s <= .1):
            raise ValueError('invalid_minimum_note_duration')


@dataclass(frozen=True)
class TransformResult:
    events: list[dict]
    audit: dict


def _bar_ticks(composition):
    return composition['ppq'] * 4 * composition['meter'][0] // composition['meter'][1]


def _chord(composition, tick):
    return next(c for c in composition['harmony']
                if c['start_tick'] <= tick < c['start_tick'] + c['duration_ticks'])


def _neighbor(event, composition, direction, budgets):
    tick, pitch = event['start_tick'], event['midi_pitch']
    key = next(k for k in reversed(composition['key_map']) if k['tick'] <= tick)
    scale = {'major': (0, 2, 4, 5, 7, 9, 11), 'minor': (0, 2, 3, 5, 7, 8, 10),
             'blues_centre': (0, 2, 3, 4, 5, 6, 7, 9, 10)}.get(key['mode'])
    if scale is None:
        raise ValueError('unsupported_ornament_key_mode')
    chord = _chord(composition, tick)
    allowed = {(key['tonic_pc'] + pc) % 12 for pc in scale}
    allowed.update((chord['root_pc'] + pc) % 12 for pc in chord['intervals_semitones'])
    for step in range(1, 4):
        candidate = pitch + direction * step
        if candidate % 12 in allowed and budgets.min_pitch <= candidate <= budgets.max_pitch:
            return candidate
    raise ValueError('no_neighbor_in_register')


def _partition(event, pitches, lengths, kind):
    """Subdivide the once-resolved interval; ornament subdivisions are not swung again."""
    if sum(lengths) != event['duration_ticks'] or any(n <= 0 for n in lengths):
        raise ValueError('invalid_ornament_partition')
    result, offset = [], 0
    for index, (pitch, length) in enumerate(zip(pitches, lengths)):
        start_s = event['resolved_time_s'] + event['duration_s'] * offset / event['duration_ticks']
        end_s = event['resolved_time_s'] + event['duration_s'] * (offset + length) / event['duration_ticks']
        note = {**deepcopy(event),
                'id': event['id'] if index == len(pitches) - 1 else f'{event["id"]}:{VERSION}:{kind}:{index}',
                'start_tick': event['start_tick'] + offset, 'duration_ticks': length,
                'resolved_time_s': start_s, 'duration_s': end_s - start_s,
                'midi_pitch': pitch, 'ornament': kind}
        result.append(note)
        offset += length
    return result


def _equal_lengths(total, count):
    short, remainder = divmod(total, count)
    return [short + (i < remainder) for i in range(count)]


def _propose(group, request, composition, budgets):
    event = group[0]
    kind, pitch, length = request.kind, event['midi_pitch'], event['duration_ticks']
    if kind == 'articulation':
        return [{**deepcopy(event), 'articulation': request.articulation}]
    if kind == 'velocity':
        velocity = event['velocity'] + request.velocity_delta
        if not 1 <= velocity <= 127:
            raise ValueError('velocity_outside_range')
        return [{**deepcopy(event), 'velocity': velocity}]
    if kind == 'octave_doubling':
        return [{**deepcopy(event), 'ornament': kind},
                {**deepcopy(event), 'id': f'{event["id"]}:{VERSION}:octave',
                 'midi_pitch': pitch + request.direction * 12, 'ornament': kind}]
    if kind in ('chord_redistribution', 'arpeggio'):
        if not 2 <= len(group) <= 4:
            raise ValueError('chord_requires_two_to_four_voices')
        slot = (event['start_tick'], event['duration_ticks'], event['resolved_time_s'], event['duration_s'],
                event['plan_id'], event['object_id'], event['timbre_id'])
        for note in group:
            if (note['start_tick'], note['duration_ticks'], note['resolved_time_s'], note['duration_s'],
                    note['plan_id'], note['object_id'], note['timbre_id']) != slot:
                raise ValueError('chord_group_slot_mismatch')
            if note['articulation'] != 'soft_comp' and not note['lane_id'].startswith('harmony-'):
                raise ValueError('chord_redistribution_requires_accompaniment')
        chord = _chord(composition, event['start_tick'])
        pcs = {(chord['root_pc'] + pc) % 12 for pc in chord['intervals_semitones']}
        if any(n['midi_pitch'] % 12 not in pcs for n in group):
            raise ValueError('chord_voice_outside_current_harmony')
        if event['start_tick'] + length > chord['start_tick'] + chord['duration_ticks']:
            raise ValueError('chord_group_crosses_harmonic_slot')
        ordered = sorted(deepcopy(group), key=lambda e: (e['midi_pitch'], e['id']), reverse=request.direction < 0)
        if kind == 'chord_redistribution':
            target = ordered[-1]
            target['midi_pitch'] += 12 * request.direction
        else:
            step = min(120, length // (len(group) + 1))
            for index, note in enumerate(ordered):
                offset = index * step
                shift_s = event['duration_s'] * offset / length
                note.update(start_tick=note['start_tick'] + offset, duration_ticks=length - offset,
                            resolved_time_s=note['resolved_time_s'] + shift_s,
                            duration_s=note['duration_s'] - shift_s)
        return [{**n, 'ornament': kind} for n in ordered]
    short = min(120, length // 4)
    if kind == 'grace':
        return _partition(event, [pitch - request.direction, pitch], [short, length - short], kind)
    if kind == 'mordent':
        neighbor = _neighbor(event, composition, -request.direction, budgets)
        return _partition(event, [pitch, neighbor, pitch], [short, short, length - 2 * short], kind)
    if kind == 'turn':
        upper = _neighbor(event, composition, request.direction, budgets)
        lower = _neighbor(event, composition, -request.direction, budgets)
        return _partition(event, [upper, pitch, lower, pitch], _equal_lengths(length, 4), kind)
    if kind == 'trill':
        neighbor = _neighbor(event, composition, request.direction, budgets)
        pitches = [pitch if i % 2 == 0 else neighbor for i in range(request.subdivisions)]
        pitches[-1] = pitch
    else:  # tremolo
        pitches = [pitch] * request.subdivisions
    return _partition(event, pitches, _equal_lengths(length, len(pitches)), kind)


def _validate_events(events, composition, budgets, *, ornament_minimum=False):
    duration = ticks_to_seconds(composition['length_ticks'], composition['tempo_map'], composition['ppq'])
    ids = set()
    for event in events:
        validate(event)
        if event['id'] in ids:
            raise ValueError('duplicate_score_event_id')
        ids.add(event['id'])
        if event['event_type'] == 'foley':
            continue
        if not 0 <= event['resolved_time_s'] < event['resolved_time_s'] + event['duration_s'] <= duration + 1e-9:
            raise ValueError('event_outside_score_duration')
        if event['start_tick'] is None or event['duration_ticks'] is None:
            raise ValueError('music_event_requires_tick_slot')
        if not 0 <= event['start_tick'] < event['start_tick'] + event['duration_ticks'] <= composition['length_ticks']:
            raise ValueError('event_outside_score_ticks')
        if event['event_type'] == 'note':
            if not budgets.min_pitch <= event['midi_pitch'] <= budgets.max_pitch:
                raise ValueError('ornament_outside_register')
            if ornament_minimum and event['duration_s'] < budgets.min_note_duration_s - 1e-9:
                raise ValueError('ornament_too_short_for_renderer')


def _low_cluster(events, budgets):
    active = []
    for event in sorted((e for e in events if e['event_type'] == 'note'), key=lambda e: e['resolved_time_s']):
        active = [e for e in active if e['resolved_time_s'] + e['duration_s'] > event['resolved_time_s'] + 1e-9]
        for other in active:
            a, b = event['midi_pitch'], other['midi_pitch']
            if max(a, b) < budgets.low_register_floor and 0 < abs(a - b) < budgets.min_low_interval:
                return True
        active.append(event)
    return False


def _max_overlapping(intervals):
    endpoints = [(start, 1) for start, _ in intervals] + [(end, -1) for _, end in intervals]
    count = maximum = 0
    for _, delta in sorted(endpoints):  # Half-open slots: endings sort before arrivals.
        count += delta
        maximum = max(maximum, count)
    return maximum


def _max_in_second(starts):
    starts = sorted(starts)
    left = maximum = 0
    for right, start in enumerate(starts):
        while starts[left] <= start - 1 + 1e-9:
            left += 1
        maximum = max(maximum, right - left + 1)
    return maximum


def apply_transforms(events, requests, composition, seed=42, budgets=None):
    """Return independent canonical events and a deterministic module audit.

    Invalid records raise; a musically unsafe/budgeted request is suppressed atomically.
    Brush/Foley records and source inputs are unchanged. Existing swing resolution is
    inherited, and no transform may extend or move outside the occupied source slot.
    """
    budgets = budgets or TransformBudgets()
    if not isinstance(budgets, TransformBudgets) or type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('invalid_transform_budget_or_seed')
    validate(composition)
    if composition['kind'] != 'CompositionSpec' or not 0 < len(events) <= 5000:
        raise ValueError('invalid_transform_source')
    if len(requests) > budgets.max_requests:
        raise ValueError('transform_request_budget')
    typed = []
    for request in requests:
        try:
            typed.append(request if isinstance(request, TransformRequest) else TransformRequest(**request))
        except (TypeError, AttributeError) as error:
            raise ValueError('invalid_transform_request') from error
    original = sorted(deepcopy(events), key=lambda e: (e['resolved_time_s'], e['lane_id'], e['id']))
    _validate_events(original, composition, budgets)
    bar_ticks = _bar_ticks(composition)
    if not bar_ticks or composition['length_ticks'] % bar_ticks:
        raise ValueError('transform_requires_complete_bars')
    base_counts = Counter(e['start_tick'] // bar_ticks for e in original if e['event_type'] != 'foley')
    if max(base_counts.values(), default=0) > budgets.max_events_per_bar:
        raise ValueError('source_exceeds_bar_event_budget')
    if _low_cluster(original, budgets):
        raise ValueError('source_low_register_cluster')
    original_ids = {e['id'] for e in original}
    eligibility = Counter((e['lane_id'], e['start_tick'] // bar_ticks) for e in original
                          if e['event_type'] == 'note' and not e['ornament'])
    current, entries = original, []
    existing_groups = {}
    used_kinds = set()
    for event in original:
        if event['event_type'] == 'note' and event['ornament'] in DECORATIONS:
            identity = (event['ornament'], event['provenance']['config_hash'])
            existing_groups.setdefault(identity, []).append(event)
            used_kinds.add((event['lane_id'], event['start_tick'] // bar_ticks, event['ornament']))
    ornament_intervals = [(min(e['resolved_time_s'] for e in group),
                           max(e['resolved_time_s'] + e['duration_s'] for e in group))
                          for group in existing_groups.values()]
    if _max_overlapping(ornament_intervals) > budgets.max_simultaneous_ornaments:
        raise ValueError('source_exceeds_simultaneous_ornament_budget')
    decorated, seen_requests = set(), set()
    source_lookup = {e['id']: e for e in original}
    # Stable event/time ordering makes arbitration independent of request delivery order.
    typed.sort(key=lambda r: (source_lookup.get(r.event_id, {}).get('resolved_time_s', math.inf),
                             r.event_id, r.kind, digest(asdict(r))))
    for request in typed:
        record = {**asdict(request), 'related_event_ids': list(request.related_event_ids)}
        entry = {'request': record, 'status': 'suppressed', 'reason': None}
        entries.append(entry)
        identity = digest(record)
        if identity in seen_requests:
            entry['reason'] = 'duplicate_transform_request'
            continue
        seen_requests.add(identity)
        lookup = {e['id']: e for e in current}
        targets = (request.event_id, *request.related_event_ids)
        if any(ident not in lookup for ident in targets):
            entry['reason'] = 'unknown_event_id'
            continue
        group = [lookup[ident] for ident in targets]
        if any(e['event_type'] != 'note' for e in group):
            entry['reason'] = 'protected_unpitched_or_foley'
            continue
        if any(e['ornament'] for e in group):
            entry['reason'] = 'ornament_already_present'
            continue
        decision_seed = int(digest({'version': VERSION, 'seed': seed, 'request': asdict(request),
                                    'source': digest(group)})[:16], 16)
        if random.Random(decision_seed).random() >= request.probability:
            entry['reason'] = 'seeded_density_skip'
            continue
        keys = {(e['lane_id'], e['start_tick'] // bar_ticks) for e in group}
        slot = (min(e['resolved_time_s'] for e in group),
                max(e['resolved_time_s'] + e['duration_s'] for e in group))
        if request.kind in DECORATIONS:
            if any((lane, bar, request.kind) in used_kinds for lane, bar in keys):
                entry['reason'] = 'same_kind_lane_bar'
                continue
            proposal_decorated = decorated | set(targets)
            counts = Counter((source_lookup[x]['lane_id'], source_lookup[x]['start_tick'] // bar_ticks)
                             for x in proposal_decorated if x in source_lookup)
            if any(counts[key] >= eligibility[key] for key in keys):
                entry['reason'] = 'every_eligible_note_would_be_decorated'
                continue
            if _max_overlapping([*ornament_intervals, slot]) > budgets.max_simultaneous_ornaments:
                entry['reason'] = 'simultaneous_ornament_budget'
                continue
        try:
            proposed = _propose(group, request, composition, budgets)
            _validate_events(proposed, composition, budgets, ornament_minimum=request.kind in DECORATIONS)
            for event in proposed:
                if not slot[0] - 1e-9 <= event['resolved_time_s'] < (
                        event['resolved_time_s'] + event['duration_s']) <= slot[1] + 1e-9:
                    raise ValueError('ornament_outside_occupied_slot')
            if (abs(min(e['resolved_time_s'] for e in proposed) - slot[0]) > 1e-9 or
                    abs(max(e['resolved_time_s'] + e['duration_s'] for e in proposed) - slot[1]) > 1e-9):
                raise ValueError('ornament_changed_occupied_duration')
            candidate = [e for e in current if e['id'] not in targets] + proposed
            counts = Counter(e['start_tick'] // bar_ticks for e in candidate if e['event_type'] != 'foley')
            if max(counts.values(), default=0) > budgets.max_events_per_bar:
                raise ValueError('bar_event_budget')
            added_times = [e['resolved_time_s'] for e in candidate
                           if e['id'] not in original_ids or f':{VERSION}:' in e['id']]
            if _max_in_second(added_times) > budgets.max_events_per_second_added:
                raise ValueError('added_event_rate_budget')
            if _low_cluster(candidate, budgets):
                raise ValueError('low_register_cluster')
            if len({e['id'] for e in candidate}) != len(candidate):
                raise ValueError('generated_event_id_collision')
        except ValueError as error:
            entry['reason'] = str(error)
            continue
        inputs = [digest(group), digest(composition)]
        for event in proposed:
            event['provenance'] = {**deepcopy(event['provenance']), 'tool_version': VERSION,
                                   'seed': seed, 'config_hash': digest(asdict(request)),
                                   'input_hashes': inputs}
        current = sorted(candidate, key=lambda e: (e['resolved_time_s'], e['lane_id'], e['id']))
        if request.kind in DECORATIONS:
            ornament_intervals.append(slot)
            decorated.update(targets)
            used_kinds.update((lane, bar, request.kind) for lane, bar in keys)
        entry.update(status='applied', reason=None, source_slot_s=list(slot),
                     output_event_ids=[e['id'] for e in proposed], events_added=len(proposed) - len(group),
                     pitch_rule='chromatic_approach' if request.kind == 'grace' else
                                ('current_key_and_chord' if request.kind in ('mordent', 'turn', 'trill')
                                 else 'source_pitch_or_octave'),
                     decision_seed=decision_seed)
    _validate_events(current, composition, budgets)
    # Check protected records by complete bytes, not merely their pitch or onset.
    protected = [e for e in original if e['event_type'] != 'note']
    if protected != [e for e in current if e['event_type'] != 'note']:
        raise ValueError('protected_stream_changed')
    return TransformResult(current, {
        'document_type': 'SceneScoreTransformAudit', 'document_version': 1, 'version': VERSION,
        'seed': seed, 'budgets': asdict(budgets), 'requests': entries,
        'source_events_sha256': digest(original), 'output_events_sha256': digest(current),
        'composition_sha256': digest(composition),
        'score_duration_s': ticks_to_seconds(composition['length_ticks'], composition['tempo_map'], composition['ppq']),
        'events_added': len(current) - len(original), 'decorated_source_events': len(decorated),
        'maximum_added_events_per_second': _max_in_second(
            [e['resolved_time_s'] for e in current if e['id'] not in original_ids or f':{VERSION}:' in e['id']]),
        'maximum_simultaneous_ornaments': _max_overlapping(ornament_intervals),
        'maximum_events_per_bar': max(Counter(e['start_tick'] // bar_ticks for e in current
                                             if e['event_type'] != 'foley').values(), default=0),
        'timing_policy': 'subdivide_inside_once_resolved_slot; never apply swing again',
        'preserves_duration': True, 'protected_streams_unchanged': True,
        'approval': None, 'audition_status': 'AUDITION_PENDING',
        'renderer_limits': ['Browser articulation envelopes require the integrated engine version.',
                            'Python candidate renderer distinguishes legato; staccato/tenuto tokens alone do not change it.',
                            'No acoustic or perceptual quality is established by this audit.'],
    })
