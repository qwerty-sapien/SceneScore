"""Bounded 0–10s A/B draft evidence: source versus grace/velocity/legato performance."""
from array import array
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import time

from modules.music.catalog import build_vertical_score, digest, payload_bytes
from modules.music.events import resolve_events
from modules.music.ornament import TransformRequest, apply_transforms
from modules.music.render import CANDIDATE_RENDERER_VERSION, RenderBudget, inspect_wav, synthesize, write_wav


def prepare():
    score = build_vertical_score()
    source = resolve_events(score['composition'], score['groove'])
    notes = [e for e in source if e['articulation'] == 'light_detached' and 5 <= e['resolved_time_s'] < 10]
    requests = [TransformRequest(notes[0]['id'], 'grace'),
                TransformRequest(notes[1]['id'], 'velocity', velocity_delta=12),
                TransformRequest(notes[4]['id'], 'articulation', articulation='legato')]
    result = apply_transforms(source, requests, score['composition'], seed=42)
    if any(r['status'] != 'applied' for r in result.audit['requests']):
        raise ValueError('ab_request_not_applied')
    return score, source, requests, result


def render_excerpt(events, path, budget):
    duration, rate = 10.0, 48000
    selected = [e for e in events if 0 <= e['resolved_time_s'] < duration]
    if any(e['resolved_time_s'] + e['duration_s'] > duration + 1e-9 for e in selected):
        raise ValueError('excerpt_would_cut_a_note')
    if len(selected) > budget.max_events:
        raise ValueError('excerpt_event_budget')
    started = time.monotonic()
    audio = synthesize(selected, duration, rate, deadline=started + budget.max_runtime_s,
                       exact_event_ends=True)
    frames = round(duration * rate)
    tails = {part: max((abs(x) for x in samples[frames:]), default=0) for part, samples in audio.items()}
    if any(tails.values()):
        raise ValueError('excerpt_would_cut_nonzero_release')
    if frames * 2 + len(payload_bytes(selected)) > budget.max_bytes:
        raise ValueError('excerpt_byte_budget')
    write_wav(path, audio['mix'][:frames], rate)
    stats = inspect_wav(path)
    if (stats['frames'] != frames or stats['rms'] <= 1e-5 or stats['sample_peak'] >= .9 or
            stats['clipped_samples'] or stats['first_sample'] or stats['last_sample']):
        raise ValueError('excerpt_pcm_gate')
    path.with_suffix('.events.json').write_bytes(payload_bytes(selected))
    return audio['mix'][:frames], {'measurements': stats, 'discarded_zero_tail_peak': tails,
                                   'events_sha256': digest(selected), 'elapsed_s': time.monotonic() - started}


if __name__ == '__main__':
    print(json.dumps({'process_id': os.getpid(), 'max_runtime_per_render_s': 60}), flush=True)
    output = Path('artifacts/music/music-vertical-ornaments').resolve()
    if output.exists():
        raise FileExistsError('ornament_output_already_exists')
    score, source, requests, result = prepare()
    fixture = {'document_type': 'SceneScoreOrnamentFixture', 'document_version': 1, 'seed': 42,
               'requests': [asdict(r) for r in requests], 'audit': result.audit,
               'output_events_sha256': digest(result.events)}
    fixture_path = Path('modules/music/fixtures/music-ornament-v1.json')
    fixture_path.write_bytes(payload_bytes(fixture))
    output.mkdir(parents=True, exist_ok=False)
    budget = RenderBudget(max_runtime_s=60, max_duration_s=11, max_events=1000)
    baseline, a = render_excerpt(source, output / 'A-source.wav', budget)
    transformed, b = render_excerpt(result.events, output / 'B-variation.wav', budget)
    difference = array('f', (x - y for x, y in zip(baseline, transformed)))
    rms_difference = math.sqrt(sum(x * x for x in difference) / len(difference))
    if rms_difference <= 1e-5:
        raise ValueError('ab_waveforms_not_distinct')
    (output / 'transform-audit.json').write_bytes(payload_bytes(result.audit))
    manifest = {
        'document_type': 'SceneScoreOrnamentABRender', 'document_version': 1,
        'renderer_version': CANDIDATE_RENDERER_VERSION,
        'window': {'clock': 'scene', 'epoch': 'scene_start', 'start_s': 0, 'end_s': 10,
                   'full_source_duration_s': 30, 'note_cut': False},
        'fade_provenance': 'Existing exact-event-end pitched fades and renderer 15-ms outer brush fade; no extra mix fade.',
        'empty_buffer_omitted_s': .35, 'source': a, 'variation': b,
        'difference_rms_float': rms_difference,
        'different_float_samples': sum(x != y for x, y in zip(baseline, transformed)),
        'composition_sha256': digest(score['composition']), 'source_events_sha256': digest(source),
        'variation_events_sha256': digest(result.events), 'fixture_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        'code_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            Path('modules/music/ornament.py'), Path('modules/music/events.py'), Path('modules/music/render.py'),
            Path(__file__).relative_to(Path.cwd()))},
        'seed': 42, 'generation_mode': 'manual_plan', 'approval': None,
        'audition_status': 'AUDITION_PENDING', 'human_reviewer': None, 'human_review_date': None,
        'renderer_limits': result.audit['renderer_limits'],
        'claim': 'Measured distinct draft PCM for one grace, one velocity and one legato edit; no listening-quality verdict.',
        'budget': budget.__dict__, 'process_id': os.getpid(),
        'command': 'PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python '
                   'modules/music/fixtures/render_ornament_v1.py',
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
    }
    (output / 'manifest.json').write_bytes(payload_bytes(manifest))
    print(json.dumps({'output': str(output), 'source': a['measurements'], 'variation': b['measurements'],
                      'difference_rms_float': rms_difference, 'process_id': os.getpid()}), flush=True)
