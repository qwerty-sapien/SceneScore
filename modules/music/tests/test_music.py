"""Independent musical invariants and actual PCM/MIDI checks; never an audition surrogate."""
from array import array
import hashlib
import json
from pathlib import Path
import struct
import sys
import threading
import wave

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from scenescore.contracts import validate, validate_bundle
from modules.music.catalog import (ROOT, BAR, VARIATIONS, build_score, get_composition, get_groove,
                                    list_catalog, payload_bytes, rests_for)
from modules.music.events import apply_swing, resolve_events, ticks_to_seconds, transpose_events
from modules.music.render import (RenderBudget, RenderCancelled, inspect_wav, render_arrangement,
                                  synthesize, write_midi, write_wav, _RENDER_LOCK)

IDS = [c['id'] for c in list_catalog()['compositions']]
GOLDEN = Path(__file__).resolve().parents[1] / 'fixtures'


@pytest.mark.parametrize('ident,bars,bpm,ratio', [
    ('tilted_blue_v1', 12, 96, 2 / 3), ('almost_then_away_v1', 8, 96, .625),
    ('corner_pocket_rag_v1', 8, 120, .5), ('velvet_orbit_v1', 8, 80, .5)])
@pytest.mark.parametrize('variation', VARIATIONS)
def test_complete_forms(ident, bars, bpm, ratio, variation):
    c = get_composition(ident, variation=variation)
    validate_bundle([get_groove(c['groove_id']), c])
    assert c['length_ticks'] == bars * BAR
    assert c['tempo_map'] == [{'tick': 0, 'bpm': bpm}]
    assert c['swing_ratio'] == ratio
    assert c['pitch_convention'] == 'C4=MIDI60'
    assert sum(h['duration_ticks'] for h in c['harmony']) == bars * BAR
    assert all(sum(min(h['start_tick'] + h['duration_ticks'], (b + 1) * BAR) - max(h['start_tick'], b * BAR)
                   for h in c['harmony'] if h['start_tick'] < (b + 1) * BAR and h['start_tick'] + h['duration_ticks'] > b * BAR)
               == BAR for b in range(bars))
    assert {n['start_tick'] // (2 * BAR) for n in c['notes']} == set(range(bars // 2))
    assert c['audition_status'] == 'AUDITION_PENDING'
    assert len(c['creative_traits']) == 8
    for notes in build_score(ident, variation=variation)['parts'].values():
        assert all(28 <= n['midi_pitch'] <= 96 and 1 <= n['velocity'] <= 92 and
                   0 <= n['start_tick'] < n['start_tick'] + n['duration_ticks'] <= bars * BAR for n in notes)


@pytest.mark.parametrize('ident', IDS)
def test_seed_call_contrasting_answer_and_explicit_rests(ident):
    c = get_composition(ident)
    seed = next(s for s in json.loads((ROOT / '.brief/seeds/compositions.json').read_text())['compositions'] if s['id'] == ident)
    assert [n for n in c['notes'] if n['start_tick'] < 2 * BAR] == seed['motif']
    answer = [{**n, 'start_tick': n['start_tick'] - 2 * BAR} for n in c['notes'] if 2 * BAR <= n['start_tick'] < 4 * BAR]
    assert [n['midi_pitch'] for n in answer] != [n['midi_pitch'] for n in seed['motif']]
    assert rests_for(c['notes'], c['length_ticks'])
    assert sum(n['duration_ticks'] for n in c['notes']) + sum(r['duration_ticks'] for r in rests_for(c['notes'], c['length_ticks'])) == c['length_ticks']
    sparse, animated = [get_composition(ident, variation=v) for v in ('sparse', 'animated')]
    assert len(sparse['notes']) < len(c['notes']) <= len(animated['notes'])
    assert sum(n['velocity'] for n in sparse['notes']) < sum(n['velocity'] for n in c['notes'])
    assert all(0 <= n['start_tick'] and n['duration_ticks'] <= 120 for n in animated['notes'] if n['articulation'] == 'grace_short')
    assert sum(n['articulation'] == 'grace_short' for n in animated['notes']) <= 2


def test_exact_catalog_lookup_and_copy_isolation():
    catalogue = list_catalog()
    assert len(catalogue['grooves']) == 3
    assert {e['technique'] for g in catalogue['grooves'] for e in get_groove(g['id'])['events']} == {'sweep', 'tap', 'accented_swish', 'chick'}
    for bad in ('brush_swing', 'brush_swing_light_v1 ', 'unknown'):
        with pytest.raises(ValueError):
            get_groove(bad)
    for bad in (2, True, '1'):
        with pytest.raises(ValueError):
            get_groove('brush_swing_light_v1', bad)
    with pytest.raises(ValueError):
        get_composition('missing')
    with pytest.raises(ValueError):
        get_composition(IDS[0], variation='wild')
    g = get_groove('brush_swing_light_v1')
    g['events'][0]['velocity'] = 1
    assert get_groove(g['id'])['events'][0]['velocity'] == 40


def test_tempo_segments_and_invalid_values():
    tempo = [{'tick': 0, 'bpm': 120}, {'tick': 1920, 'bpm': 60}]
    assert ticks_to_seconds(3840, tempo) == 3
    assert ticks_to_seconds(1920, tempo) == 1
    assert ticks_to_seconds(480, [{'tick': 0, 'bpm': 96}]) == .3125
    for tick in (-1, float('inf'), float('nan')):
        with pytest.raises(ValueError):
            ticks_to_seconds(tick, tempo)
    with pytest.raises(ValueError):
        ticks_to_seconds(1, [{'tick': 1, 'bpm': 96}])
    with pytest.raises(ValueError):
        ticks_to_seconds(1, [{'tick': 0, 'bpm': 0}])


def _hero_events(humanize=True):
    c = get_composition('tilted_blue_v1')
    return c, resolve_events(c, get_groove(c['groove_id']), humanize=humanize)


def test_swing_once_and_scene_clock_foley():
    c, events = _hero_events(False)
    first = next(e for e in events if e['lane_id'] == 'piano_or_lead' and e['start_tick'] == 480 and e['midi_pitch'] == 63)
    assert first['resolved_time_s'] == pytest.approx(60 / 96 * 2 / 3)
    assert first['duration_s'] == pytest.approx(60 / 96 / 3)
    assert first['swing_application_count'] == 1
    with pytest.raises(ValueError, match='already_applied'):
        apply_swing(first, 2 / 3, c['tempo_map'])
    sweep = next(e for e in events if e['articulation'] == 'sweep')
    assert sweep['swing_application_count'] == 0
    assert apply_swing(sweep, 2 / 3, c['tempo_map']) == sweep
    foley = {**sweep, 'event_type': 'foley', 'start_tick': None, 'duration_ticks': None,
             'scene_time_s': .123456, 'resolved_time_s': .123456, 'articulation': 'collision'}
    assert apply_swing(foley, 2 / 3, c['tempo_map']) == foley
    assert transpose_events([foley], 2)[0] == foley
    rag = get_composition('corner_pocket_rag_v1')
    assert all(e['swing_application_count'] == 0 for e in resolve_events(rag, get_groove(rag['groove_id'])))


def test_humanization_determinism_bounds_and_sweep_invariance():
    c, events = _hero_events()
    assert events == _hero_events()[1]
    raw = {e['id']: e for e in _hero_events(False)[1]}
    delta_count = 0
    for e in events:
        r = raw[e['id']]
        if e['event_type'] == 'brush' and e['articulation'] != 'sweep':
            assert abs(e['resolved_time_s'] - r['resolved_time_s']) <= .006 + 1e-9
            assert abs(e['velocity'] - r['velocity']) <= 3
            delta_count += e['resolved_time_s'] != r['resolved_time_s']
        else:
            assert e['resolved_time_s'] == r['resolved_time_s']
            assert e['velocity'] == r['velocity']
        assert 0 <= e['resolved_time_s'] < e['resolved_time_s'] + e['duration_s'] <= 30 + 1e-9
    assert delta_count > 0
    assert len({e['id'] for e in events}) == len(events)


def test_signed_transpose_only_pitch_and_register_rejection():
    _, events = _hero_events()
    moved = transpose_events(events, -2)
    for before, after in zip(events, moved):
        if before['event_type'] == 'note':
            assert after == {**before, 'midi_pitch': before['midi_pitch'] - 2}
        else:
            assert before == after
    assert {e['object_id'] for e in moved if e['lane_id'] == 'object_motif'} == {'object-motif'}
    with pytest.raises(ValueError, match='register'):
        transpose_events(events, 24, max_pitch=79)
    with pytest.raises(ValueError):
        transpose_events(events, True)


def test_exact_golden_symbolic_catalogue():
    for ident in IDS:
        assert payload_bytes(get_composition(ident)) == (GOLDEN / f'{ident}.json').read_bytes()
    for groove in list_catalog()['grooves']:
        assert payload_bytes(get_groove(groove['id'])) == (GOLDEN / f'{groove["id"]}.json').read_bytes()
    _, events = _hero_events(False)
    assert payload_bytes(events[:12]) == (GOLDEN / 'hero-events-first12.json').read_bytes()


def _parse_midi(path):
    data = path.read_bytes()
    assert data[:4] == b'MThd'
    size, fmt, count, ppq = struct.unpack('>IHHH', data[4:14])
    assert (size, fmt, count, ppq) == (6, 1, 5, 960)
    cursor, tracks = 14, []
    for _ in range(count):
        assert data[cursor:cursor + 4] == b'MTrk'
        length = int.from_bytes(data[cursor + 4:cursor + 8], 'big')
        end, i, tick, messages = cursor + 8 + length, cursor + 8, 0, []
        def vlq():
            nonlocal i
            value = 0
            while True:
                byte = data[i]
                i += 1
                value = value * 128 + (byte & 127)
                if byte < 128:
                    return value
        while i < end:
            tick += vlq()
            status = data[i]
            i += 1
            if status == 255:
                kind = data[i]
                i += 1
                n = vlq()
                payload = data[i:i + n]
                i += n
                messages.append((tick, status, kind, payload))
            else:
                n = 1 if status & 240 == 192 else 2
                payload = data[i:i + n]
                i += n
                messages.append((tick, status, None, payload))
        assert i == end
        tracks.append(messages)
        cursor = end
    assert cursor == len(data)
    return tracks


@pytest.fixture(scope='module')
def actual_render(tmp_path_factory):
    scope = tmp_path_factory.mktemp('music-actual-pcm')
    output = scope / 'hero'
    manifest = render_arrangement('tilted_blue_v1', output, sample_rate=8000, output_root=scope)
    return output, manifest


def test_actual_pcm_non_silent_clipping_alignment_and_mix_sum(actual_render):
    output, manifest = actual_render
    arrays = {}
    for name in ('piano_or_lead', 'bass', 'brushes', 'object_motif', 'mix'):
        stats = inspect_wav(output / f'{name}.wav')
        assert stats['frames'] == round(30.35 * 8000)
        assert stats['channels'] == 1
        assert stats['rms'] > 1e-5
        assert 0 < stats['sample_peak'] < .9
        assert stats['clipped_samples'] == 0
        assert stats['first_sample'] == stats['last_sample'] == 0
        with wave.open(str(output / f'{name}.wav')) as wav:
            pcm = array('h', wav.readframes(wav.getnframes()))
            if sys.byteorder != 'little':
                pcm.byteswap()
            arrays[name] = pcm
    for i in range(len(arrays['mix'])):
        # Independent PCM quantization has at most 2 integer units summation error.
        assert abs(arrays['mix'][i] - sum(arrays[k][i] for k in ('piano_or_lead', 'bass', 'brushes', 'object_motif'))) <= 2
    loop = inspect_wav(output / 'brushes-loop.wav')
    assert loop['frames'] == 30 * 8000 and loop['first_sample'] == loop['last_sample'] == 0
    for asset in manifest['assets']:
        validate(asset)
        assert asset['asset_hash'] == hashlib.sha256((output / f'{asset["stem_id"]}.wav').read_bytes()).hexdigest()
    assert manifest['audition_status'] == 'AUDITION_PENDING'
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected


def test_midi_independent_parse_notes_tempo_and_track_boundaries(actual_render):
    output, _ = actual_render
    tracks = _parse_midi(output / 'score.mid')
    assert any(status == 255 and kind == 81 and int.from_bytes(data, 'big') == 625000
               for _, status, kind, data in tracks[0])
    for track in tracks:
        assert track[-1][:3] == (46080, 255, 47)
    notes_on = sum(status & 240 == 144 for track in tracks for _, status, _, _ in track)
    assert notes_on == len(json.loads((output / 'events.json').read_text()))
    brush = tracks[3]
    assert all((status & 15) == 9 for _, status, _, _ in brush if status != 255)


def test_wav_repeatability_and_golden_measurement(tmp_path):
    c, events = _hero_events(False)
    event = next(e for e in events if e['lane_id'] == 'piano_or_lead' and e['midi_pitch'] == 63)
    event = {**event, 'resolved_time_s': 0, 'duration_s': .25}
    first = synthesize([event], .5, 8000)['mix']
    second = synthesize([event], .5, 8000)['mix']
    assert first == second
    path = tmp_path / 'golden.wav'
    write_wav(path, first, 8000)
    stats = inspect_wav(path)
    golden = json.loads((GOLDEN / 'render-golden.json').read_text())
    assert stats['frames'] == golden['frames']
    assert stats['sample_peak'] == pytest.approx(golden['sample_peak'], abs=1 / 32768)
    assert stats['rms'] == pytest.approx(golden['rms'], abs=1 / 32768)
    assert stats['clipped_samples'] == 0
    assert stats['first_sample'] == stats['last_sample'] == 0


def test_render_budgets_cancel_scope_concurrency_and_existing_data(tmp_path):
    output = tmp_path / 'render'
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(RenderCancelled):
        render_arrangement(IDS[0], output, output_root=tmp_path, cancellation=cancelled)
    assert not output.exists()
    with pytest.raises(TimeoutError):
        render_arrangement(IDS[0], output, output_root=tmp_path, budget=RenderBudget(max_runtime_s=1e-10))
    for budget in (RenderBudget(max_events=1), RenderBudget(max_duration_s=1), RenderBudget(max_bytes=1)):
        with pytest.raises(ValueError):
            render_arrangement(IDS[0], output, output_root=tmp_path, budget=budget)
    with pytest.raises(ValueError, match='sample_rate'):
        render_arrangement(IDS[0], output, sample_rate=96000, output_root=tmp_path)
    with pytest.raises(ValueError, match='scope'):
        render_arrangement(IDS[0], tmp_path.parent / 'outside', output_root=tmp_path)
    target = tmp_path / 'existing'
    target.mkdir()
    (target / 'preserve.txt').write_text('user-owned')
    with pytest.raises(FileExistsError):
        render_arrangement(IDS[0], target, output_root=tmp_path)
    assert (target / 'preserve.txt').read_text() == 'user-owned'
    link = tmp_path / 'alias'
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        render_arrangement(IDS[0], link / 'child', output_root=tmp_path)
    _RENDER_LOCK.acquire()
    try:
        with pytest.raises(RuntimeError, match='busy'):
            render_arrangement(IDS[0], output, output_root=tmp_path)
    finally:
        _RENDER_LOCK.release()
    assert not output.exists()


def test_readonly_api_and_unknown_entry_errors():
    from modules.music.api import router
    app = FastAPI()
    app.include_router(router, prefix='/music')
    with TestClient(app) as client:
        assert client.get('/music/health').json()['human_audition'] == 'unverified'
        assert len(client.get('/music/catalog').json()['compositions']) == 4
        assert client.get('/music/compositions/tilted_blue_v1').json()['kind'] == 'CompositionSpec'
        assert client.get('/music/scores/tilted_blue_v1?variation=sparse').json()['variation'] == 'sparse'
        response = client.get('/music/grooves/brush_swing_light_v1?version=2')
        assert response.status_code == 404
        assert response.json()['detail']['retryable'] is False


@pytest.mark.parametrize('ident', IDS)
@pytest.mark.parametrize('variation', VARIATIONS)
def test_midi_no_pitched_voice_collision_or_stuck_notes(tmp_path, ident, variation):
    c = get_composition(ident, variation=variation)
    events = resolve_events(c, get_groove(c['groove_id']), variation=variation)
    path = tmp_path / 'score.mid'
    write_midi(path, c, events)
    for track in _parse_midi(path):
        active = set()
        for _, status, _, data in track:
            if status == 255 or (status & 15) == 9:
                continue  # Brush channel explicitly approximates continuous technique as hits.
            key = (status & 15, data[0])
            if status & 240 == 144:
                assert key not in active, 'overlapping same-channel/pitch note would truncate another voice'
                active.add(key)
            elif status & 240 == 128:
                assert key in active, 'unpaired MIDI note-off'
                active.remove(key)
        assert not active, 'stuck MIDI note'


def test_mid_render_cancellation_removes_only_partial_output(tmp_path, monkeypatch):
    import modules.music.render as renderer
    cancelled = threading.Event()
    original = renderer.write_wav
    def cancel_after_first_file(*args, **kwargs):
        original(*args, **kwargs)
        cancelled.set()
    monkeypatch.setattr(renderer, 'write_wav', cancel_after_first_file)
    output = tmp_path / 'partial'
    sentinel = tmp_path / 'unrelated.txt'
    sentinel.write_text('preserve')
    with pytest.raises(RenderCancelled):
        render_arrangement('corner_pocket_rag_v1', output, sample_rate=8000,
                           output_root=tmp_path, cancellation=cancelled)
    assert not output.exists()
    assert sentinel.read_text() == 'preserve'



def test_candidate_event_adapter_preserves_inputs_and_records_pcm(tmp_path):
    from copy import deepcopy
    from modules.music.render import render_events
    _, events = _hero_events(False)
    event = next(e for e in events if e['event_type'] == 'note')
    candidate = [{**event, 'lane_id': 'arbitrary-owner:source-object-42', 'resolved_time_s': 0, 'duration_s': .25}]
    original = deepcopy(candidate)
    output = tmp_path / 'candidate.wav'
    rendered = render_events(candidate, output, duration_s=.5, sample_rate=8000, output_root=tmp_path)
    validate(rendered['asset'])
    assert rendered['measurements']['rms'] > 1e-5
    assert rendered['measurements']['frames'] == 6800
    assert rendered['audition_status'] == 'AUDITION_PENDING'
    assert candidate == original
    with pytest.raises(FileExistsError):
        render_events(candidate, output, duration_s=.5, sample_rate=8000, output_root=tmp_path)
    foley = {**event, 'event_type': 'foley', 'midi_pitch': None, 'start_tick': None,
             'duration_ticks': None, 'scene_time_s': 0, 'resolved_time_s': 0, 'duration_s': .1,
             'swing_applied': False, 'swing_application_count': 0}
    with pytest.raises(ValueError, match='foley_unsupported'):
        render_events([foley], tmp_path / 'foley.wav', duration_s=.5, sample_rate=8000, output_root=tmp_path)
    with pytest.raises(ValueError, match='outside_candidate'):
        render_events(candidate, tmp_path / 'short.wav', duration_s=.1, sample_rate=8000, output_root=tmp_path)
    with pytest.raises(ValueError, match='sample_work_budget'):
        render_events(candidate, tmp_path / 'overbudget.wav', duration_s=.5, sample_rate=8000,
                      output_root=tmp_path, budget=RenderBudget(max_bytes=1))
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(RenderCancelled):
        render_events(candidate, tmp_path / 'cancel.wav', duration_s=.5, sample_rate=8000,
                      output_root=tmp_path, cancellation=cancel)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['candidate.wav']



@pytest.mark.parametrize('preset', ['keyboard_damped_v1', 'bass_pluck_v1', 'object_bell_v1'])
@pytest.mark.parametrize('duration', [.625, 6.875])
def test_candidate_exact_end_pcm_and_long_legato_sustain(tmp_path, preset, duration):
    import math
    from modules.music.render import render_events
    _, events = _hero_events(False)
    event = next(e for e in events if e['event_type'] == 'note')
    # Deliberately noninteger-sample onset exercises independent onset/end rounding.
    start = .125043
    candidate = [{**event, 'instrument_id': preset, 'timbre_id': preset,
                  'resolved_time_s': start, 'duration_s': duration, 'articulation': 'legato'}]
    path = tmp_path / 'exact-end.wav'
    result = render_events(candidate, path, duration_s=start + duration + .25,
                           sample_rate=8000, output_root=tmp_path)
    with wave.open(str(path)) as audio:
        pcm = array('h', audio.readframes(audio.getnframes()))
    if sys.byteorder != 'little':
        pcm.byteswap()
    end = math.ceil((start + duration) * 8000)
    assert all(value == 0 for value in pcm[end:]), 'old pitched envelope must not ring beyond declared end'
    # The held legato tone must still sound near the end, including the long tonic sustain
    # that the catalogue gate previously cut more than one second early.
    late = pcm[round((start + duration - .1) * 8000):round((start + duration - .02) * 8000)]
    assert max(abs(value) for value in late) > 10
    assert sum(value * value for value in late) / len(late) > 4
    assert abs(pcm[end - 1]) <= 1, 'final in-interval fade should reach silence at the boundary'
    assert result['pitched_envelope_mode'] == 'exact_event_ends_v1'
    assert result['asset']['renderer_version'] == 'stdlib-procedural-1-event-ends-1'


def test_candidate_mode_explicit_and_catalogue_default_preserved(tmp_path):
    from modules.music.render import render_events
    _, events = _hero_events(False)
    event = next(e for e in events if e['event_type'] == 'note')
    event = {**event, 'resolved_time_s': 0, 'duration_s': .625, 'articulation': 'legato'}
    catalogue_default = synthesize([event], 1, 8000)['mix']
    catalogue_explicit = synthesize([event], 1, 8000, exact_event_ends=False)['mix']
    assert catalogue_default == catalogue_explicit
    old = render_events([event], tmp_path / 'catalogue.wav', duration_s=1, sample_rate=8000,
                        output_root=tmp_path, exact_event_ends=False)
    new = render_events([event], tmp_path / 'exact.wav', duration_s=1, sample_rate=8000, output_root=tmp_path)
    assert old['pitched_envelope_mode'] == 'catalogue_gate_release_v1'
    assert old['asset']['asset_hash'] != new['asset']['asset_hash']
    assert old['asset']['id'] != new['asset']['id']
    assert old['asset']['provenance']['config_hash'] != new['asset']['provenance']['config_hash']
    with pytest.raises(ValueError, match='invalid_event_end_mode'):
        render_events([event], tmp_path / 'bad.wav', duration_s=1, sample_rate=8000,
                      output_root=tmp_path, exact_event_ends='true')
