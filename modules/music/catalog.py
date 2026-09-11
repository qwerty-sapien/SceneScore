"""Exact versioned catalogues built from immutable project seeds, with original answers."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from scenescore.contracts import validate

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'music-0.2.0'
PPQ = 960
BAR = 3840
VARIATIONS = ('base', 'sparse', 'animated')
PRESETS = {
    'keyboard_damped_v1': {'family': 'damped multi-partial keyboard', 'partials': [1, 2, 3],
                           'relative_amplitudes': [1, .22, .08], 'attack_s': .006, 'release_s': .18},
    'bass_pluck_v1': {'family': 'short plucked bass', 'partials': [1, 2],
                      'relative_amplitudes': [1, .18], 'attack_s': .008, 'release_s': .12},
    'object_bell_v1': {'family': 'soft mallet marker', 'partials': [1, 3],
                      'relative_amplitudes': [1, .12], 'attack_s': .004, 'release_s': .22},
    'brush_noise_v1': {'family': 'seeded filtered noise approximation', 'attack_s': .012,
                       'release_s': .04, 'sweep_boundary_fade_s': .015},
}
TRAITS = [
    'Original blues/ragtime-derived phrasing; no borrowed tune or recording',
    'Brubeck: selective displaced accents while retaining the written meter',
    'Evans: spacious three-note voicings with economical inner-voice movement',
    'Mingus: blues call/response and contrasting ensemble density',
    'Carmichael: clear singable original melodic arcs',
    'Monk: purposeful rests, angular answers and selective chromatic approaches',
    'Gilberto: restrained steady bossa-inflected accompaniment color',
    'Lyra: lyrical answers over gently syncopated accompaniment',
]
# Hand-authored answer phrases: (onset, duration, pitch, velocity), over two bars.
# Seed melodies are retained verbatim in each opening call; these answers are new drafts.
ANSWERS = {
    'tilted_blue_v1': [(0, 960, 67, 69), (1440, 480, 64, 65), (2400, 480, 63, 68),
                      (2880, 480, 60, 64), (3840, 960, 62, 69), (5280, 480, 66, 70),
                      (5760, 960, 64, 62)],
    'almost_then_away_v1': [(480, 960, 70, 63), (1920, 480, 67, 61), (2400, 960, 65, 58),
                           (4320, 480, 64, 59), (4800, 960, 67, 64), (6240, 480, 62, 55)],
    'corner_pocket_rag_v1': [(0, 480, 77, 73), (960, 480, 74, 70), (1440, 960, 72, 74),
                            (2880, 480, 69, 67), (4320, 480, 71, 74), (4800, 480, 74, 78),
                            (5760, 480, 68, 72), (6720, 960, 67, 65)],
    'velvet_orbit_v1': [(480, 1440, 67, 55), (2400, 960, 64, 51), (4320, 960, 61, 54),
                       (5760, 480, 64, 55), (6240, 960, 67, 52)],
}


def payload_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(payload_bytes(value)).hexdigest()


def provenance(config, *, seed=104729, inputs=None):
    return {'source_mode': 'manual_plan', 'creator': 'SceneScore original draft authoring',
            'tool_version': VERSION, 'config_hash': digest(config),
            'input_hashes': inputs or [], 'seed': seed}


def _seeds(name):
    path = ROOT / '.brief/seeds' / name
    return json.loads(path.read_text()), hashlib.sha256(path.read_bytes()).hexdigest()


def _seed(composition_id, version=1):
    data, source_hash = _seeds('compositions.json')
    if type(version) is not int or version != 1:
        raise ValueError('unknown_composition_version')
    for seed in data['compositions']:
        if seed['id'] == composition_id:
            return seed, source_hash
    raise ValueError('unknown_composition_id')


def get_groove(groove_id, version=1):
    data, source_hash = _seeds('brush_catalog.json')
    if type(version) is not int:
        raise ValueError('unknown_groove_version')
    for seed in data['grooves']:
        if (seed['id'], seed['version']) == (groove_id, version):
            record = {'kind': 'BrushGroove', 'schema_version': '0.1', 'id': seed['id'],
                      'provenance': provenance(seed, seed=seed['seed'], inputs=[source_hash]),
                      'catalog_version': version, 'ppq': seed['ppq'], 'length_ticks': seed['length_ticks'],
                      'meter': seed['meter'], 'pitched': False, 'events': deepcopy(seed['events']),
                      'max_humanize_ms': seed['humanization']['max_onset_ms'],
                      'max_velocity_delta': seed['humanization']['max_velocity_delta']}
            return validate(record)
    raise ValueError('unknown_groove_id_or_version')


def _note(start, duration, pitch, velocity, articulation='light_detached', swingable=True):
    return {'start_tick': start, 'duration_ticks': duration, 'midi_pitch': pitch,
            'velocity': velocity, 'articulation': articulation, 'swingable': swingable}


def get_composition(composition_id, version=1, variation='base'):
    seed, source_hash = _seed(composition_id, version)
    if variation not in VARIATIONS:
        raise ValueError('unknown_variation')
    notes = deepcopy(seed['motif'])
    answer = ANSWERS[composition_id]
    notes += [_note(t + 2 * BAR, d, p, v) for t, d, p, v in answer]
    # The middle return is harmonically adjusted; contour and rhythmic identity remain explicit.
    shift = 5 if composition_id == 'tilted_blue_v1' else (-3 if composition_id == 'almost_then_away_v1' else 0)
    notes += [{**n, 'start_tick': n['start_tick'] + 4 * BAR, 'midi_pitch': n['midi_pitch'] + shift,
               'velocity': max(40, n['velocity'] - 5)} for n in seed['motif']]
    notes += [_note(t + 6 * BAR, d, p + (2 if composition_id == 'velvet_orbit_v1' else 0), v - 4)
              for t, d, p, v in answer]
    if seed['bars'] == 12:
        notes += [_note(8 * BAR + t, d, p, v) for t, d, p, v in
                  [(0, 960, 65, 70), (1440, 480, 69, 73), (2400, 480, 72, 76),
                   (2880, 960, 69, 68), (4320, 480, 71, 74), (4800, 960, 69, 69),
                   (6240, 480, 65, 64), (6720, 960, 62, 63)]]
        notes += [_note(10 * BAR + t, d, p, v) for t, d, p, v in
                  [(0, 960, 64, 69), (1440, 480, 67, 71), (2400, 960, 69, 68),
                   (3840, 960, 65, 66), (5280, 480, 62, 63), (5760, 960, 59, 59)]]
    # The two-bar call stays intact. Sparse answers suspend selected pickups; animated
    # answers add at most one short chromatic pickup per two-bar answer.
    if variation == 'sparse':
        notes = [n for i, n in enumerate(notes) if n['start_tick'] < 2 * BAR or i % 2 == 0]
        notes = [{**n, 'velocity': max(30, n['velocity'] - 9)} for n in notes]
    elif variation == 'animated':
        notes = [{**n, 'velocity': min(92, n['velocity'] + (7 if n['start_tick'] % BAR in (0, 1440) else 2))}
                 for n in notes]
        for block in (2, 6):
            target = next(n for n in notes if n['start_tick'] >= block * BAR)
            if target['start_tick'] >= 120 and not any(n['start_tick'] <= target['start_tick'] - 120 <
                                                     n['start_tick'] + n['duration_ticks'] for n in notes):
                notes.append(_note(target['start_tick'] - 120, 120, target['midi_pitch'] - 1, 48,
                                   'grace_short', False))
    harmony = []
    cursor = 0
    for bar in seed['harmony_bars']:
        if sum(c['duration_ticks'] for c in bar) != BAR:
            raise ValueError('invalid_seed_bar_length')
        for chord in bar:
            harmony.append({k: v for k, v in {'start_tick': cursor, **chord}.items() if k != 'symbol'})
            cursor += chord['duration_ticks']
    composition = {'kind': 'CompositionSpec', 'schema_version': '0.1', 'id': composition_id,
                   'provenance': provenance({'variation': variation, 'answers': ANSWERS, 'version': VERSION},
                                            inputs=[source_hash]),
                   'catalog_version': version, 'title': seed['title'], 'ppq': PPQ, 'meter': seed['meter'],
                   'length_ticks': seed['bars'] * BAR, 'tempo_map': [{'tick': 0, 'bpm': seed['bpm']}],
                   'key_map': [{'tick': 0, **seed['key']}], 'harmony': harmony,
                   'notes': sorted(notes, key=lambda n: (n['start_tick'], n['midi_pitch'])),
                   'pitch_convention': 'C4=MIDI60', 'timing': 'unswung_quarter_note_ticks',
                   'swing_ratio': seed['swing_ratio'], 'groove_id': seed['groove_id'], 'groove_version': 1,
                   'creative_traits': TRAITS.copy(), 'audition_status': 'AUDITION_PENDING'}
    return validate(composition)


def _voicing(chord, previous):
    # Preserve extension intervals as voicing inputs; each voice chooses its nearest octave.
    intervals = chord['intervals_semitones']
    chosen = [intervals[1], intervals[-1], intervals[-2]]
    voiced = []
    for i, interval in enumerate(chosen):
        raw = 48 + chord['root_pc'] + interval
        candidates = [raw + 12 * k for k in range(-3, 3) if 48 <= raw + 12 * k <= 76]
        pitch = min(candidates, key=lambda p: (abs(p - previous[i]), p))
        while pitch in voiced and pitch + 12 <= 76:
            pitch += 12
        voiced.append(pitch)
    return voiced


def parts_for(composition, variation='base'):
    """Derive original accompaniment. Supplied canonical lead edits are honored verbatim."""
    validate(composition)
    if composition['kind'] != 'CompositionSpec' or variation not in VARIATIONS:
        raise ValueError('invalid_composition_or_variation')
    lead = deepcopy(composition['notes'])
    parts = {'piano_or_lead': lead, 'bass': [], 'object_motif': []}
    previous = [52, 58, 67]
    color = composition['id'] in ('almost_then_away_v1', 'velvet_orbit_v1')
    for chord in composition['harmony']:
        start, duration = chord['start_tick'], chord['duration_ticks']
        bar_number = start // BAR
        voiced = _voicing(chord, previous)
        previous = voiced
        # Bossa color is limited to selected accompaniment bars, never rewrites lead swing.
        offsets = [0, 1440, 2880] if color and bar_number in (3, 5) else [480, 2400]
        if variation == 'sparse':
            offsets = offsets[:1]
        for offset in offsets:
            if offset + 360 <= duration:
                parts['piano_or_lead'] += [_note(start + offset, min(720, duration - offset), p,
                                                38 if variation == 'sparse' else 47,
                                                'soft_comp', not color) for p in voiced]
        bass_offsets = [0, 1920] if variation != 'animated' else [0, 960, 1920, 2880]
        if variation == 'sparse':
            bass_offsets = [0]
        for i, offset in enumerate(bass_offsets):
            if offset < duration:
                root = 36 + chord['root_pc']
                pitch = root + ([0, 7, 0, intervals_third(chord)][i % 4])
                parts['bass'].append(_note(start + offset, min(720, duration - offset), pitch,
                                          53 if variation == 'sparse' else 64, 'bass_pluck', False))
    # A stable three-note sonic identity answers in every other bar, leaving a final beat rest.
    tonic = composition['key_map'][0]['tonic_pc']
    for bar in range(1, composition['length_ticks'] // BAR, 2):
        if variation == 'sparse' and bar % 4 == 3:
            continue
        for i, offset in enumerate((0, 960, 1920)):
            parts['object_motif'].append(_note(bar * BAR + offset, 360, 72 + tonic + (0, 3, 7)[i],
                                              40 if variation == 'sparse' else 49, 'soft_marker', True))
    return {part: sorted(notes, key=lambda n: (n['start_tick'], n['midi_pitch'])) for part, notes in parts.items()}


def intervals_third(chord):
    return chord['intervals_semitones'][1]


def rests_for(notes, length_ticks):
    intervals = sorted((n['start_tick'], n['start_tick'] + n['duration_ticks']) for n in notes)
    rests, cursor = [], 0
    for start, end in intervals:
        if start > cursor:
            rests.append({'start_tick': cursor, 'duration_ticks': start - cursor})
        cursor = max(cursor, end)
    if cursor < length_ticks:
        rests.append({'start_tick': cursor, 'duration_ticks': length_ticks - cursor})
    return rests


def build_score(composition_id, version=1, variation='base'):
    composition = get_composition(composition_id, version, variation)
    seed, _ = _seed(composition_id, version)
    parts = parts_for(composition, variation)
    phrases = [{'start_tick': b * BAR, 'duration_ticks': 2 * BAR,
                'role': 'call' if b in (0, 4) else ('turnaround' if b + 2 == seed['bars'] else 'answer'),
                'motif_id': f'{composition_id}:object-three-note-v1' if b == 4 else
                            f'{composition_id}:{"seed-call" if b == 0 else "original-answer"}-v1'}
               for b in range(0, seed['bars'], 2)]
    return {'document_type': 'SceneScoreMusicScore', 'document_version': 1, 'variation': variation,
            'composition': composition, 'parts': parts, 'presets': deepcopy(PRESETS),
            'motif_ids': [f'{composition_id}:seed-call-v1', f'{composition_id}:original-answer-v1',
                          f'{composition_id}:object-three-note-v1'],
            'lanes': {'phrasing': {'phrases': phrases, 'lead_rests': rests_for(composition['notes'],
                                                                           composition['length_ticks']),
                                  'density': variation, 'cadence_tick': (seed['bars'] - 1) * BAR},
                      'dynamics': {'master_gain_db': -12, 'velocity_bounds': [28, 92],
                                   'normalization': 'none'},
                      'articulation': {'gate_ratio': .82, 'attack_release_from': 'presets'},
                      'ornamentation': {'max_per_two_bars': 1, 'max_duration_ticks': 120,
                                        'enabled': variation == 'animated', 'register': [28, 96]},
                      'timbre': {'part_presets': {'piano_or_lead': 'keyboard_damped_v1',
                                                 'bass': 'bass_pluck_v1', 'object_motif': 'object_bell_v1',
                                                 'brushes': 'brush_noise_v1'}}},
            'chord_symbols': [c['symbol'] for bar in seed['harmony_bars'] for c in bar],
            'loop': {'start_tick': 0, 'end_tick': composition['length_ticks'],
                     'ending': 'seed harmonic turnaround; next loop supplies tonic',
                     'audio_tail_policy': '350 ms release tail; loop uses score boundary, not end of WAV'},
            'audition_status': 'AUDITION_PENDING'}


def list_catalog():
    compositions, _ = _seeds('compositions.json')
    grooves, _ = _seeds('brush_catalog.json')
    return {'catalog_version': 1, 'compositions': [{'id': c['id'], 'version': 1, 'title': c['title'],
                                                   'variations': list(VARIATIONS)} for c in compositions['compositions']],
            'grooves': [{'id': g['id'], 'version': g['version']} for g in grooves['grooves']],
            'presets': deepcopy(PRESETS), 'audition_status': 'AUDITION_PENDING'}
