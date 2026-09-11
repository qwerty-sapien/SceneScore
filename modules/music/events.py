"""Pure deterministic event materialization. No audio clock, network or approval activation."""
from copy import deepcopy
import math
import random
from scenescore.contracts import validate
from .catalog import digest, parts_for, provenance

PART_PRESETS = {'piano_or_lead': 'keyboard_damped_v1', 'bass': 'bass_pluck_v1',
                'object_motif': 'object_bell_v1', 'brushes': 'brush_noise_v1'}


def ticks_to_seconds(tick, tempo_map, ppq=960):
    if not math.isfinite(tick) or tick < 0 or type(ppq) is not int or ppq <= 0:
        raise ValueError('invalid_tick_or_ppq')
    if (not tempo_map or tempo_map[0]['tick'] != 0 or
            any(not math.isfinite(t['bpm']) or t['bpm'] <= 0 for t in tempo_map) or
            any(a['tick'] >= b['tick'] for a, b in zip(tempo_map, tempo_map[1:]))):
        raise ValueError('invalid_tempo_map')
    seconds = 0.0
    for i, tempo in enumerate(tempo_map):
        end = tempo_map[i + 1]['tick'] if i + 1 < len(tempo_map) else tick
        if tick <= tempo['tick']:
            break
        seconds += (min(tick, end) - tempo['tick']) / ppq * 60 / tempo['bpm']
    return seconds


def swung_tick(tick, ratio, ppq=960):
    if not math.isfinite(ratio) or not .5 <= ratio <= .75:
        raise ValueError('invalid_swing_ratio')
    whole, fraction = divmod(tick, ppq)
    half = ppq / 2
    resolved = fraction * 2 * ratio if fraction <= half else ratio * ppq + (fraction - half) * 2 * (1 - ratio)
    return whole * ppq + resolved


def apply_swing(event, ratio, tempo_map, ppq=960):
    """Resolve one eligible event. Already-swung events are rejected, not shifted again.

    Call only for explicitly swingable raw notes/hits. Continuous sweeps and Foley
    have protected clock semantics even if supplied accidentally.
    """
    validate(event)
    if event['swing_application_count'] != 0:
        raise ValueError('swing_already_applied')
    result = deepcopy(event)
    if event['event_type'] == 'foley' or event['articulation'] == 'sweep' or ratio == .5:
        return result
    if event['start_tick'] is None or event['duration_ticks'] is None:
        raise ValueError('swing_requires_ticks')
    start = swung_tick(event['start_tick'], ratio, ppq)
    end = swung_tick(event['start_tick'] + event['duration_ticks'], ratio, ppq)
    result.update(resolved_time_s=ticks_to_seconds(start, tempo_map, ppq),
                  duration_s=ticks_to_seconds(end, tempo_map, ppq) - ticks_to_seconds(start, tempo_map, ppq),
                  swing_applied=True, swing_application_count=1)
    return validate(result)


def resolve_events(composition, groove, plan_id='manual-audition', object_id='object-motif',
                   humanize=True, variation='base'):
    validate(composition)
    validate(groove)
    if composition['kind'] != 'CompositionSpec' or groove['kind'] != 'BrushGroove':
        raise ValueError('incorrect_record_kind')
    if (composition['groove_id'], composition['groove_version']) != (groove['id'], groove['catalog_version']):
        raise ValueError('groove_reference_mismatch')
    if composition['ppq'] != groove['ppq'] or composition['meter'] != groove['meter']:
        raise ValueError('incompatible_groove_timeline')
    if composition['length_ticks'] % groove['length_ticks']:
        raise ValueError('partial_groove_loop')
    ppq, tempos = composition['ppq'], composition['tempo_map']
    duration = ticks_to_seconds(composition['length_ticks'], tempos, ppq)
    evidence = provenance({'composition_hash': digest(composition), 'groove_hash': digest(groove),
                           'humanize': humanize, 'variation': variation},
                          inputs=[digest(composition), digest(groove)])
    events = []

    def materialize(note, part, event_type, number):
        tick, length = note['start_tick'], note['duration_ticks']
        event = {'kind': 'ScoreEvent', 'schema_version': '0.1',
                 'id': f'{plan_id}:{composition["id"]}:{variation}:{part}:{number:04d}',
                 'provenance': deepcopy(evidence), 'plan_id': plan_id,
                 'object_id': object_id if part == 'object_motif' else None, 'lane_id': part,
                 'event_type': event_type, 'instrument_id': PART_PRESETS[part],
                 'start_tick': tick, 'duration_ticks': length,
                 'resolved_time_s': ticks_to_seconds(tick, tempos, ppq),
                 'duration_s': ticks_to_seconds(tick + length, tempos, ppq) - ticks_to_seconds(tick, tempos, ppq),
                 'scene_time_s': None, 'midi_pitch': note.get('midi_pitch'), 'velocity': note['velocity'],
                 'dynamics_db': -12.0, 'articulation': note.get('articulation', note.get('technique')),
                 'phrasing': f'phrase-{tick // (ppq * 8) + 1}',
                 'ornament': 'chromatic_pickup' if note.get('articulation') == 'grace_short' else None,
                 'timbre_id': PART_PRESETS[part], 'swing_applied': False, 'swing_application_count': 0}
        if note['swingable']:
            event = apply_swing(event, composition['swing_ratio'], tempos, ppq)
        return event

    for part, notes in parts_for(composition, variation).items():
        for i, note in enumerate(notes):
            events.append(materialize(note, part, 'note', i))
    rng = random.Random(groove['provenance']['seed'])
    for loop in range(composition['length_ticks'] // groove['length_ticks']):
        for i, hit in enumerate(groove['events']):
            note = {**hit, 'start_tick': hit['start_tick'] + loop * groove['length_ticks']}
            event = materialize(note, 'brushes', 'brush', loop * len(groove['events']) + i)
            if humanize and hit['technique'] != 'sweep':
                jitter = rng.uniform(-groove['max_humanize_ms'], groove['max_humanize_ms']) / 1000
                # Keep hit ends and starts within this groove loop, never move a scene-time effect.
                lo = ticks_to_seconds(loop * groove['length_ticks'], tempos, ppq)
                hi = ticks_to_seconds((loop + 1) * groove['length_ticks'], tempos, ppq)
                event['resolved_time_s'] = max(lo, min(hi - event['duration_s'], event['resolved_time_s'] + jitter))
                event['velocity'] = max(1, min(127, event['velocity'] + rng.randint(-groove['max_velocity_delta'],
                                                                                  groove['max_velocity_delta'])))
            if event['resolved_time_s'] + event['duration_s'] > duration + 1e-9:
                raise ValueError('resolved_event_outside_form')
            events.append(event)
    for event in events:
        validate(event)
    return sorted(events, key=lambda e: (e['resolved_time_s'], e['lane_id'], e['id']))


def transpose_events(events, semitones, min_pitch=28, max_pitch=96):
    """Signed transposition of future pitched events only; waveform shifting is never used."""
    if type(semitones) is not int or not -24 <= semitones <= 24:
        raise ValueError('invalid_signed_interval')
    if not 0 <= min_pitch <= max_pitch <= 127:
        raise ValueError('invalid_register')
    output = deepcopy(events)
    for event in output:
        validate(event)
        if event['event_type'] == 'note':
            pitch = event['midi_pitch'] + semitones
            if not min_pitch <= pitch <= max_pitch:
                raise ValueError('transposition_outside_register')
            event['midi_pitch'] = pitch
    return output
