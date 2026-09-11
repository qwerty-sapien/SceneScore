"""Bounded stdlib-only offline audition renderer; no external model calls or sample files."""
from array import array
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import sys
import threading
import time
import wave

from scenescore.contracts import validate
from .catalog import ROOT, PRESETS, build_score, digest, get_groove, payload_bytes, provenance
from .events import resolve_events, ticks_to_seconds

RENDERER_VERSION = 'stdlib-procedural-1'
CANDIDATE_RENDERER_VERSION = 'stdlib-procedural-1-event-ends-1'
TAIL_S = .35
STEMS = ('piano_or_lead', 'bass', 'brushes', 'object_motif')
_RENDER_LOCK = threading.Lock()


@dataclass(frozen=True)
class RenderBudget:
    max_runtime_s: float = 120
    max_duration_s: float = 61
    max_sample_rate: int = 48000
    max_events: int = 5000
    max_bytes: int = 64 * 1024 * 1024


class RenderCancelled(RuntimeError):
    pass


def _check(deadline, cancellation):
    if cancellation is not None and cancellation.is_set():
        raise RenderCancelled('render_cancelled')
    if time.monotonic() > deadline:
        raise TimeoutError('render_runtime_budget_exceeded')


def _tone(pitch, seconds, preset_id, rate, deadline, cancellation, *, exact_event_end=False, sustain=False):
    preset = PRESETS[preset_id]
    # Catalogue defaults retain the audited gated/release envelope. Candidate mode puts
    # both fades inside the declared event interval and sustains explicit legato notes.
    gate_s = seconds * (.7 if preset_id == 'bass_pluck_v1' else .82)
    duration_s = seconds if exact_event_end else gate_s + preset['release_s']
    frames = int(math.ceil(duration_s * rate))
    frequency = 440 * 2 ** ((pitch - 69) / 12)
    partials = [(h, a) for h, a in zip(preset['partials'], preset['relative_amplitudes'])
                if h * frequency < rate * .45]
    samples = array('f', [0]) * frames
    norm = sum(a for _, a in partials) or 1
    decay = 3.5 if preset_id == 'bass_pluck_v1' else 1.7
    for i in range(frames):
        if i % 4096 == 0:
            _check(deadline, cancellation)
        t = i / rate
        if exact_event_end:
            attack_s = min(preset['attack_s'], duration_s / 4)
            release_s = min(preset['release_s'], duration_s / 4)
            attack = min(1, t / attack_s)
            # Last allocated sample is exactly zero, including noninteger sample lengths.
            release = max(0, min(1, (frames - 1 - i) / (release_s * rate)))
        else:
            attack = min(1, t / preset['attack_s'])
            release = max(0, min(1, (duration_s - t) / preset['release_s']))
        value = sum(a * math.sin(2 * math.pi * frequency * h * t) for h, a in partials) / norm
        decay_gain = math.exp(-decay * t)
        if exact_event_end and sustain:
            decay_gain = .35 + .65 * decay_gain
        samples[i] = value * attack * release * decay_gain
    return samples


def _add(target, start, source, gain, deadline, cancellation):
    count = min(len(source), len(target) - start)
    for i in range(count):
        if i % 8192 == 0:
            _check(deadline, cancellation)
        target[start + i] += source[i] * gain


def _brush_hit(event, rate, seed):
    rng = random.Random(seed)
    duration = event['duration_s'] + .04
    n = max(1, int(duration * rate))
    result = array('f', [0]) * n
    filtered = 0.0
    previous = 0.0
    for i in range(n):
        raw = rng.uniform(-1, 1)
        filtered += .25 * (raw - filtered)
        sample = raw - filtered if event['articulation'] == 'chick' else filtered
        sample = .65 * sample + .35 * previous
        previous = sample
        t = i / rate
        envelope = min(1, t / .004) * max(0, 1 - t / duration) ** 2
        result[i] = sample * envelope
    return result


def synthesize(events, duration_s, sample_rate=48000, *, deadline=None, cancellation=None, exact_event_ends=False):
    deadline = deadline if deadline is not None else time.monotonic() + 120
    frame_count = round((duration_s + TAIL_S) * sample_rate)
    stems = {part: array('f', [0]) * frame_count for part in STEMS}
    cache = {}
    sweeps = []
    for event in events:
        _check(deadline, cancellation)
        validate(event)
        if event['lane_id'] not in stems:
            raise ValueError('unknown_stem')
        start = round(event['resolved_time_s'] * sample_rate)
        gain = 10 ** (event['dynamics_db'] / 20) * event['velocity'] / 127
        if event['event_type'] == 'note':
            if event['timbre_id'] not in PRESETS or event['timbre_id'] == 'brush_noise_v1':
                raise ValueError('unknown_pitched_preset')
            sustain = exact_event_ends and event['articulation'] == 'legato'
            key = (event['midi_pitch'], event['duration_s'], event['timbre_id'], sustain)
            if key not in cache:
                cache[key] = _tone(*key[:2], key[2], sample_rate, deadline, cancellation,
                                   exact_event_end=exact_event_ends, sustain=sustain)
            samples = cache[key]
            if exact_event_ends:
                # Independently rounded onset and duration can otherwise leak one sample
                # beyond the absolute event end. Clip only this instance, never the cache.
                end = math.ceil((event['resolved_time_s'] + event['duration_s']) * sample_rate)
                count = max(0, end - start)
                if len(samples) > count:
                    samples = samples[:count]
                    if samples:
                        samples[-1] = 0
            part_gain = .26 if event['lane_id'] == 'piano_or_lead' else .33
            _add(stems[event['lane_id']], start, samples, gain * part_gain, deadline, cancellation)
        elif event['event_type'] == 'brush':
            if event['articulation'] == 'sweep':
                sweeps.append(event)
            else:
                seed = int(hashlib.sha256(event['id'].encode()).hexdigest()[:16], 16)
                _add(stems['brushes'], start, _brush_hit(event, sample_rate, seed), gain * .6,
                     deadline, cancellation)
        else:
            raise ValueError('foley_requires_separate_scene_renderer')
    # One noise stream spans the entire prepared sweep, never resets at each bar.
    # Smooth interpolation follows the recipe's velocities and removes artificial attacks.
    rng = random.Random(13007)
    filtered = 0.0
    smooth_gain = 0.0
    sweep_index = 0
    sweeps.sort(key=lambda e: e['resolved_time_s'])
    for i in range(round(duration_s * sample_rate)):
        if i % 8192 == 0:
            _check(deadline, cancellation)
        t = i / sample_rate
        while sweep_index + 1 < len(sweeps) and sweeps[sweep_index + 1]['resolved_time_s'] <= t:
            sweep_index += 1
        active = sweeps[sweep_index] if sweeps else None
        target = 0.0
        if active and active['resolved_time_s'] <= t < active['resolved_time_s'] + active['duration_s']:
            target = active['velocity'] / 127 * 10 ** (active['dynamics_db'] / 20) * .38
        smooth_gain += min(1, 1 / (.01 * sample_rate)) * (target - smooth_gain)
        filtered += .18 * (rng.uniform(-1, 1) - filtered)
        fade = max(0, min(1, t / .015, (duration_s - t) / .015))
        stems['brushes'][i] += filtered * smooth_gain * fade
    mix = array('f', [0]) * frame_count
    for part in STEMS:
        _add(mix, 0, stems[part], 1, deadline, cancellation)
    return {**stems, 'mix': mix}


def write_wav(path, samples, sample_rate):
    pcm = array('h')
    for value in samples:
        if not math.isfinite(value) or abs(value) >= 1:
            raise ValueError('nonfinite_or_clipping_audio')
        pcm.append(round(value * 32767))
    if sys.byteorder != 'little':
        pcm.byteswap()
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def inspect_wav(path):
    with wave.open(str(path), 'rb') as audio:
        channels, rate, width, frames = audio.getnchannels(), audio.getframerate(), audio.getsampwidth(), audio.getnframes()
        if width != 2:
            raise ValueError('expected_pcm16')
        pcm = array('h', audio.readframes(frames))
    if sys.byteorder != 'little':
        pcm.byteswap()
    peak = max((abs(x) for x in pcm), default=0) / 32768
    rms = math.sqrt(sum((x / 32768) ** 2 for x in pcm) / len(pcm)) if pcm else 0
    return {'sample_rate_hz': rate, 'channels': channels, 'frames': frames, 'duration_s': frames / rate,
            'sample_peak': peak, 'rms': rms, 'clipped_samples': sum(abs(x) >= 32767 for x in pcm),
            'first_sample': pcm[0] if pcm else None, 'last_sample': pcm[-1] if pcm else None,
            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def _varlen(number):
    if number < 0 or number >= 1 << 28:
        raise ValueError('invalid_midi_delta')
    data = [number & 127]
    while number >> 7:
        number >>= 7
        data.insert(0, (number & 127) | 128)
    return bytes(data)


def _track(events, end_tick):
    result, cursor = bytearray(), 0
    for tick, order, data in sorted(events, key=lambda e: (e[0], e[1], e[2])):
        result += _varlen(tick - cursor) + data
        cursor = tick
    result += _varlen(max(0, end_tick - cursor)) + b'\xff\x2f\x00'
    return b'MTrk' + struct.pack('>I', len(result)) + result


def write_midi(path, composition, events):
    """Format 1 MIDI includes resolved swing/humanization; sweeps are declared hit approximations."""
    if len(composition['tempo_map']) != 1:
        raise ValueError('midi_export_constant_tempo_only')
    bpm, ppq = composition['tempo_map'][0]['bpm'], composition['ppq']
    def seconds_to_ticks(seconds):
        return round(seconds * bpm / 60 * ppq)
    tempo = round(60_000_000 / bpm)
    numerator, denominator = composition['meter']
    if denominator & (denominator - 1):
        raise ValueError('midi_meter_denominator')
    conductor = [(0, 0, b'\xff\x51\x03' + tempo.to_bytes(3, 'big')),
                 (0, 1, b'\xff\x58\x04' + bytes([numerator, denominator.bit_length() - 1, 24, 8]))]
    tracks = [_track(conductor, composition['length_ticks'])]
    for part, channel, program in [('piano_or_lead', 0, 0), ('bass', 1, 32), ('brushes', 9, 0), ('object_motif', 2, 11)]:
        data = [(0, 0, b'\xff\x03' + _varlen(len(part)) + part.encode()),
                (0, 1, bytes([0xC0 + channel, program]))]
        if part == 'piano_or_lead':
            data.append((0, 1, bytes([0xC3, program])))
        for event in events:
            if event['lane_id'] != part:
                continue
            pitch = event['midi_pitch'] if event['event_type'] == 'note' else {
                'sweep': 38, 'tap': 38, 'accented_swish': 40, 'chick': 44}[event['articulation']]
            start = seconds_to_ticks(event['resolved_time_s'])
            gate_ratio = .7 if part == 'bass' else .82
            end = max(start + 1, seconds_to_ticks(event['resolved_time_s'] + event['duration_s'] * gate_ratio))
            # Separate comping channel avoids a chord note-off truncating a coincident lead pitch.
            event_channel = 3 if part == 'piano_or_lead' and event['articulation'] == 'soft_comp' else channel
            data += [(start, 3, bytes([0x90 + event_channel, pitch, event['velocity']])),
                     (end, 2, bytes([0x80 + event_channel, pitch, 0]))]
        tracks.append(_track(data, composition['length_ticks']))
    Path(path).write_bytes(b'MThd' + struct.pack('>IHHH', 6, 1, len(tracks), ppq) + b''.join(tracks))


def _lead_sheet(score):
    composition = score['composition']
    lines = [f'# {composition["title"]} — {score["variation"]}', '',
             '**AUDITION_PENDING.** Original editable draft; generated timbres are technical approximations.', '',
             f'{composition["tempo_map"][0]["bpm"]} BPM; {composition["meter"][0]}/{composition["meter"][1]}; '
             f'{composition["length_ticks"] // 3840} bars; PPQ 960; C4=MIDI60; swing ratio {composition["swing_ratio"]:.4f}.',
             'The straight rag remains straight. Key map and chord map are separate; chord intervals retain extensions.', '',
             '| Bar | Chords | Phrase |', '|---|---|---|']
    for bar in range(composition['length_ticks'] // 3840):
        indices = [i for i, c in enumerate(composition['harmony']) if c['start_tick'] // 3840 == bar]
        phrase = score['lanes']['phrasing']['phrases'][bar // 2]['role']
        lines.append(f'| {bar + 1} | {" / ".join(score["chord_symbols"][i] for i in indices)} | {phrase} |')
    lines += ['', 'Opening two-bar call preserves the supplied new motif. Contrasting answers, middle return,',
              'turnaround, comping and bass are authored for this project. Generic harmonic forms are not claimed novel.',
              'Stable object marker: tonic, minor third, fifth in the mallet register; its identity survives signed transposition.',
              '', 'Lead melody (unswung integer ticks; rests are explicit in score.json):', '',
              '| Onset tick | Duration | MIDI pitch | Velocity |', '|---|---|---|---|']
    lines += [f'| {n["start_tick"]} | {n["duration_ticks"]} | {n["midi_pitch"]} | {n["velocity"]} |'
              for n in composition['notes']]
    lines += ['', 'Independent lanes: phrasing/rests, dynamics (-12 dB initial gain), articulation, ornaments, timbre.',
              'Audio has a 350 ms release tail after the score loop boundary. Brush-loop.wav is exactly form length,',
              'with 15 ms boundary fades; continuous sweep noise does not reset at intermediate recipe boundaries.',
              'MIDI approximates continuous brushes as percussion hits; brush JSON and resolved events are authoritative.',
              'No normalization is applied. Do not infer listening quality or physical output level from file peaks.', '',
              '## Human audition record', '',
              'Reviewer: pending. Date: pending. Exact mix hash: see manifest.json. Status: AUDITION_PENDING.',
              'Compare base/sparse/animated A/B: melodic coherence; call and answer; cadence/loop; space for scene events;',
              'object marker identity; near-miss tension; brush approximation; balance; clicks; dynamics; articulation;',
              'prepared ±2 modulation boundaries (future arranger integration). Record approved/changes requested with hashes.', '']
    return '\n'.join(lines)


def render_arrangement(composition_id, output_dir, variation='base', sample_rate=48000, *,
                       output_root=None, budget=None, cancellation=None):
    """Offline authoring only. Scoped path, cooperative cancellation, no overwrite, one process-local render."""
    budget = budget or RenderBudget()
    if (not math.isfinite(budget.max_runtime_s) or not 0 < budget.max_runtime_s <= 600 or
            not math.isfinite(budget.max_duration_s) or not 0 < budget.max_duration_s <= 120 or
            not 0 < budget.max_events <= 10000 or not 0 < budget.max_bytes <= 256 * 1024 * 1024):
        raise ValueError('invalid_render_budget')
    if type(sample_rate) is not int or not 8000 <= sample_rate <= min(48000, budget.max_sample_rate):
        raise ValueError('sample_rate_budget')
    scope = Path(output_root or ROOT / 'artifacts/music').resolve()
    requested = Path(output_dir)
    if any(p.is_symlink() for p in [requested, *requested.parents]):
        raise ValueError('symlink_output_disallowed')
    output = requested.resolve()
    if not output.is_relative_to(scope) or output == scope:
        raise ValueError('output_outside_scope')
    if output.exists():
        raise FileExistsError('output_already_exists')
    if not _RENDER_LOCK.acquire(blocking=False):
        raise RuntimeError('render_busy')
    deadline = time.monotonic() + budget.max_runtime_s
    started = time.monotonic()
    created = False
    try:
        _check(deadline, cancellation)
        score = build_score(composition_id, variation=variation)
        composition = score['composition']
        groove = get_groove(composition['groove_id'], composition['groove_version'])
        events = resolve_events(composition, groove, variation=variation)
        duration = ticks_to_seconds(composition['length_ticks'], composition['tempo_map'], composition['ppq'])
        if duration + TAIL_S > budget.max_duration_s or len(events) > budget.max_events:
            raise ValueError('render_size_budget')
        expected_bytes = math.ceil((duration + TAIL_S) * sample_rate) * 2 * 6 + len(payload_bytes(events))
        if expected_bytes > budget.max_bytes:
            raise ValueError('render_byte_budget')
        audio = synthesize(events, duration, sample_rate, deadline=deadline, cancellation=cancellation)
        _check(deadline, cancellation)
        output.mkdir(parents=True, exist_ok=False)
        created = True
        metadata = {'score.json': score, 'composition.json': composition, 'brush.json': groove, 'events.json': events}
        for name, record in metadata.items():
            (output / name).write_bytes(payload_bytes(record))
        write_midi(output / 'score.mid', composition, events)
        (output / 'lead-sheet.md').write_text(_lead_sheet(score))
        measured, assets = {}, []
        for part, samples in audio.items():
            _check(deadline, cancellation)
            path = output / f'{part}.wav'
            write_wav(path, samples, sample_rate)
            stats = inspect_wav(path)
            if stats['rms'] <= 1e-5 or stats['clipped_samples'] != 0 or stats['sample_peak'] >= .9:
                raise ValueError('audio_objective_gate_failed')
            measured[path.name] = stats
            record = {'kind': 'AudioAssetManifest', 'schema_version': '0.1',
                      'id': f'{composition_id}:{variation}:{part}:audio-v1',
                      'provenance': provenance({'renderer': RENDERER_VERSION, 'sample_rate': sample_rate,
                                                'variation': variation}, inputs=[digest(score), digest(events)]),
                      'asset_hash': stats['sha256'], 'stem_id': part, 'sample_rate_hz': sample_rate, 'channels': 1,
                      'duration_s': stats['duration_s'], 'timeline_origin_s': 0,
                      'source': 'Original symbolic draft rendered by local procedural synthesis; no sample downloads',
                      'license': 'Project-authored procedural output; distribution terms unspecified; no third-party samples',
                      'renderer_version': RENDERER_VERSION, 'pitched': part != 'brushes',
                      'sample_peak': stats['sample_peak'], 'measurement_status': 'measured'}
            assets.append(validate(record))
        loop = audio['brushes'][:round(duration * sample_rate)]
        fade_frames = round(.015 * sample_rate)
        for i in range(fade_frames):
            loop[i] *= i / fade_frames
            loop[-1 - i] *= i / fade_frames
        write_wav(output / 'brushes-loop.wav', loop, sample_rate)
        measured['brushes-loop.wav'] = inspect_wav(output / 'brushes-loop.wav')
        loop_stats = measured['brushes-loop.wav']
        loop_asset = {**next(a for a in assets if a['stem_id'] == 'brushes'),
                      'id': f'{composition_id}:{variation}:brushes-loop:audio-v1', 'stem_id': 'brushes-loop',
                      'asset_hash': loop_stats['sha256'], 'duration_s': loop_stats['duration_s'],
                      'sample_peak': loop_stats['sample_peak']}
        assets.append(validate(loop_asset))
        (output / 'measurements.json').write_bytes(payload_bytes(measured))
        code_files = sorted(Path(__file__).parent.glob('*.py'))
        code_hash = hashlib.sha256(b''.join(p.name.encode() + b'\0' + p.read_bytes() for p in code_files)).hexdigest()
        run = {'kind': 'RunManifest', 'schema_version': '0.1',
               'id': f'{composition_id}:{variation}:render-run-v1',
               'provenance': provenance({'renderer': RENDERER_VERSION, 'rate': sample_rate, 'variation': variation}),
               'code_hash': code_hash, 'config_hash': digest({'budget': budget.__dict__, 'rate': sample_rate,
                                                            'variation': variation}),
               'data_hashes': [digest(score), digest(events)],
               'schema_hash': hashlib.sha256((ROOT / 'contracts/0.1/schema.json').read_bytes()).hexdigest(),
               'model_hash': None,
               'split': {'train_sessions': [], 'development_sessions': [], 'final_sessions': []},
               'commands': [f'Python function call: modules.music.render.render_arrangement('
                            f'{composition_id!r}, {str(output_dir)!r}, variation={variation!r}, sample_rate={sample_rate})'],
               'runtime': {'python': sys.version.split()[0], 'node': None,
                           'host_profile_id': 'local-control-host; immutable profile not re-inspected by music worker'},
               'results': [{'test_id': 'music.real_pcm_non_silence_peak_alignment', 'status': 'passed',
                            'evidence_paths': ['measurements.json'], 'reason': None},
                           {'test_id': 'music.human_audition', 'status': 'not_run',
                            'evidence_paths': ['lead-sheet.md'], 'reason': 'AUDITION_PENDING; no listening judgment'}]}
        (output / 'run-manifest.json').write_bytes(payload_bytes(validate(run)))
        if len({m['frames'] for name, m in measured.items() if name != 'brushes-loop.wav'}) != 1:
            raise ValueError('unaligned_stems')
        manifest = {'document_type': 'SceneScoreMusicRender', 'document_version': 1,
                    'composition_id': composition_id, 'composition_version': 1, 'variation': variation,
                    'sample_rate_hz': sample_rate, 'channels': 1, 'timeline_origin_s': 0,
                    'form_duration_s': duration, 'tail_s': TAIL_S, 'loop': score['loop'],
                    'tempo_map': composition['tempo_map'], 'meter': composition['meter'],
                    'key_map': composition['key_map'], 'harmony': composition['harmony'],
                    'motif_ids': score['motif_ids'], 'presets': PRESETS, 'seed': 104729,
                    'groove': {'id': groove['id'], 'version': groove['catalog_version'], 'seed': 13007},
                    'assets': assets, 'measurements': measured, 'audition_status': 'AUDITION_PENDING',
                    'generation_mode': 'manual_plan', 'renderer': RENDERER_VERSION,
                    'normalization': 'none', 'midi_brushes': 'Declared hit approximation; JSON envelopes authoritative',
                    'determinism_scope': 'Same code, CPython math/array runtime and sample rate; cross-platform hash not promised',
                    'limitations': ['Procedural keyboard/bass/noise timbres; realism unverified',
                                    'No human listening review', 'Mono aligned stems; live browser audio untested'],
                    'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
                    'elapsed_s': time.monotonic() - started, 'process_id': os.getpid()}
        (output / 'manifest.json').write_bytes(payload_bytes(manifest))
        if sum(p.stat().st_size for p in output.iterdir()) > budget.max_bytes:
            raise ValueError('render_actual_byte_budget_exceeded')
        _check(deadline, cancellation)
        return manifest
    except BaseException:
        # Remove only the directory this invocation created, never pre-existing user material.
        if created:
            import shutil
            shutil.rmtree(output)
        raise
    finally:
        _RENDER_LOCK.release()


def render_events(events, output_wav, *, duration_s, sample_rate=48000, output_root=None,
                  budget=None, cancellation=None, exact_event_ends=True):
    """Render short canonical candidates to one local mix; caller owns plan approval/run evidence.

    Arbitrary lane IDs are retained in input and mapped in a copy by exact timbre ID.
    Foley is rejected because this music renderer cannot establish scene-effect semantics.
    Default exact_event_ends=True confines pitched fades to each declared event duration;
    legato holds a sustained level until its final in-interval fade. Brushes are unchanged.
    """
    budget = budget or RenderBudget()
    if type(exact_event_ends) is not bool:
        raise ValueError('invalid_event_end_mode')
    envelope_mode = 'exact_event_ends_v1' if exact_event_ends else 'catalogue_gate_release_v1'
    renderer_version = CANDIDATE_RENDERER_VERSION if exact_event_ends else RENDERER_VERSION
    if (not math.isfinite(duration_s) or not 0 < duration_s + TAIL_S <= min(61, budget.max_duration_s) or
            type(sample_rate) is not int or not 8000 <= sample_rate <= min(48000, budget.max_sample_rate) or
            not math.isfinite(budget.max_runtime_s) or not 0 < budget.max_runtime_s <= 600 or
            not 0 < len(events) <= min(5000, budget.max_events)):
        raise ValueError('candidate_render_budget')
    scope = Path(output_root or ROOT / 'artifacts/music').resolve()
    requested = Path(output_wav)
    if any(p.is_symlink() for p in [requested, *requested.parents]):
        raise ValueError('symlink_output_disallowed')
    output = requested.resolve()
    if not output.is_relative_to(scope) or output == scope or output.suffix.lower() != '.wav':
        raise ValueError('output_outside_scope_or_not_wav')
    if output.exists():
        raise FileExistsError('output_already_exists')
    mapping = {'keyboard_damped_v1': 'piano_or_lead', 'bass_pluck_v1': 'bass',
               'object_bell_v1': 'object_motif', 'brush_noise_v1': 'brushes'}
    prepared = []
    for event in events:
        validate(event)
        if event['event_type'] == 'foley':
            raise ValueError('scene_time_foley_unsupported_by_music_renderer')
        if event['timbre_id'] not in mapping:
            raise ValueError('unknown_timbre_preset')
        if (event['event_type'] == 'brush') != (event['timbre_id'] == 'brush_noise_v1'):
            raise ValueError('pitched_unpitched_preset_mismatch')
        if event['resolved_time_s'] + event['duration_s'] > duration_s + 1e-9:
            raise ValueError('event_outside_candidate_duration')
        if event['event_type'] == 'note' and not 28 <= event['midi_pitch'] <= 96:
            raise ValueError('candidate_register_limit')
        prepared.append({**event, 'lane_id': mapping[event['timbre_id']]})
    # Bound both output bytes and a conservative uncached sample-work estimate.
    memory_estimate = ((duration_s + TAIL_S) * 6 + sum(e['duration_s'] + .35 for e in events)) * sample_rate * 4
    if not 0 < budget.max_bytes <= 256 * 1024 * 1024 or memory_estimate > budget.max_bytes:
        raise ValueError('candidate_sample_work_budget')
    if not _RENDER_LOCK.acquire(blocking=False):
        raise RuntimeError('render_busy')
    deadline = time.monotonic() + budget.max_runtime_s
    created = False
    try:
        _check(deadline, cancellation)
        mix = synthesize(prepared, duration_s, sample_rate, deadline=deadline, cancellation=cancellation,
                         exact_event_ends=exact_event_ends)['mix']
        _check(deadline, cancellation)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive reservation prevents concurrent invocations overwriting an existing artifact.
        with output.open('xb'):
            pass
        created = True
        write_wav(output, mix, sample_rate)
        _check(deadline, cancellation)
        stats = inspect_wav(output)
        if stats['rms'] <= 1e-5 or stats['sample_peak'] >= .9 or stats['clipped_samples']:
            raise ValueError('candidate_pcm_objective_gate')
        asset = {'kind': 'AudioAssetManifest', 'schema_version': '0.1',
                 'id': 'candidate-mix-' + digest({'events': events, 'envelope_mode': envelope_mode,
                                                   'sample_rate': sample_rate, 'duration_s': duration_s})[:16],
                 'provenance': provenance({'renderer': renderer_version, 'sample_rate': sample_rate,
                                           'duration_s': duration_s, 'pitched_envelope_mode': envelope_mode},
                                          inputs=[digest(events)]),
                 'asset_hash': stats['sha256'], 'stem_id': 'candidate_mix', 'sample_rate_hz': sample_rate,
                 'channels': 1, 'duration_s': stats['duration_s'], 'timeline_origin_s': 0,
                 'source': 'Procedural canonical-event audition candidate; original lane IDs retained in event provenance',
                 'license': 'Project-authored procedural synthesis; caller must establish supplied event rights',
                 'renderer_version': renderer_version, 'pitched': any(e['event_type'] == 'note' for e in events),
                 'sample_peak': stats['sample_peak'], 'measurement_status': 'measured'}
        return {'asset': validate(asset), 'measurements': stats, 'audition_status': 'AUDITION_PENDING',
                'tail_s': TAIL_S, 'input_events_sha256': digest(events),
                'pitched_envelope_mode': envelope_mode}
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    finally:
        _RENDER_LOCK.release()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--composition', default='tilted_blue_v1')
    parser.add_argument('--variation', choices=['base', 'sparse', 'animated'], default='base')
    parser.add_argument('--sample-rate', type=int, default=48000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({'render_process_id': os.getpid(), 'bounded_runtime_s': 120}), flush=True)
    manifest = render_arrangement(args.composition, args.output, args.variation, args.sample_rate)
    print(json.dumps({'output': str(args.output), 'elapsed_s': manifest['elapsed_s'],
                      'process_id': manifest['process_id'], 'mix': manifest['measurements']['mix.wav'],
                      'audition_status': 'AUDITION_PENDING'}, indent=2))


if __name__ == '__main__':
    main()
