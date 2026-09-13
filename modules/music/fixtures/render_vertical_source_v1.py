"""Reproduce the two bounded source-node PCM evidence renders, never an audition."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from modules.music.catalog import build_score, build_vertical_score, digest, get_groove, payload_bytes
from modules.music.events import resolve_events, ticks_to_seconds
from modules.music.render import RenderBudget, RENDERER_VERSION, inspect_wav, synthesize, write_midi, write_wav


def render_one(score, output, budget):
    started = time.monotonic()
    deadline = started + budget.max_runtime_s
    if output.exists():
        raise FileExistsError('output_already_exists')
    composition = score['composition']
    groove = get_groove(composition['groove_id'], composition['groove_version'])
    events = resolve_events(composition, groove)
    duration = ticks_to_seconds(composition['length_ticks'], composition['tempo_map'], composition['ppq'])
    rate = 48000
    if duration != 30 or rate > budget.max_sample_rate or len(events) > budget.max_events:
        raise ValueError('source_render_budget')
    # Existing natural gated/release renderer is retained. Only its demonstrably
    # all-zero allocation after scene end may be omitted; no music is truncated.
    audio = synthesize(events, duration, rate, deadline=deadline)
    frame_count = round(duration * rate)
    tail = {part: max((abs(x) for x in samples[frame_count:]), default=0)
            for part, samples in audio.items()}
    if any(tail.values()):
        raise ValueError('non_silent_tail_would_be_truncated')
    if sum(frame_count * 2 for _ in audio) + len(payload_bytes(events)) > budget.max_bytes:
        raise ValueError('source_render_output_budget')
    output.mkdir(parents=True, exist_ok=False)
    for name, value in {'score.json': score, 'composition.json': composition,
                        'brush.json': groove, 'events.json': events}.items():
        (output / name).write_bytes(payload_bytes(value))
    write_midi(output / 'score.mid', composition, events)
    measurements = {}
    for part, samples in audio.items():
        if time.monotonic() > deadline:
            raise TimeoutError('source_render_runtime_budget')
        path = output / f'{part}.wav'
        write_wav(path, samples[:frame_count], rate)
        measured = inspect_wav(path)
        if measured['frames'] != frame_count or measured['rms'] <= 1e-5 or measured['clipped_samples']:
            raise ValueError('source_pcm_objective_gate')
        if measured['sample_peak'] >= .9 or measured['last_sample'] != 0:
            raise ValueError('source_pcm_peak_or_endpoint_gate')
        measurements[path.name] = measured
    (output / 'measurements.json').write_bytes(payload_bytes(measurements))
    manifest = {
        'document_type': 'SceneScoreVerticalSourceRender', 'document_version': 1,
        'renderer_version': RENDERER_VERSION, 'sample_rate_hz': rate, 'duration_s': duration,
        'envelope_mode': 'unchanged_catalogue_gate_release_v1',
        'discarded_zero_buffer_s': .35, 'discarded_buffer_peak_by_stem': tail,
        'composition_sha256': digest(composition), 'groove_sha256': digest(groove),
        'score_sha256': digest(score), 'events_sha256': digest(events),
        'code_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            Path('modules/music/catalog.py'), Path('modules/music/events.py'),
            Path('modules/music/render.py'), Path(__file__).relative_to(Path.cwd()))},
        'measurements': measurements, 'budget': budget.__dict__, 'seed': 42,
        'source_brush_humanization_seed': groove['provenance']['seed'],
        'generation_mode': 'manual_plan', 'approval': None, 'audition_status': 'AUDITION_PENDING',
        'human_reviewer': None, 'human_review_date': None,
        'listening': {'status': 'not_run', 'reason': 'No human listening judgment was supplied'},
        'process_id': os.getpid(), 'elapsed_s': time.monotonic() - started,
        'command': 'PYTHONPATH=.:src /Users/agent/Desktop/SceneScore/.venv/bin/python '
                   'modules/music/fixtures/render_vertical_source_v1.py',
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
    }
    (output / 'manifest.json').write_bytes(payload_bytes(manifest))
    print(json.dumps({'output': str(output), 'process_id': os.getpid(),
                      'elapsed_s': manifest['elapsed_s'], 'mix': measurements['mix.wav']}), flush=True)
    return manifest


if __name__ == '__main__':
    print(json.dumps({'process_id': os.getpid(), 'max_runtime_per_render_s': 120}), flush=True)
    root = Path('artifacts/music/music-vertical-source').resolve()
    if root.exists():
        raise FileExistsError('vertical_source_output_exists')
    budget = RenderBudget(max_runtime_s=120, max_duration_s=31, max_events=1000)
    original = render_one(build_score('tilted_blue_v1'), root / 'unmodified', budget)
    ending_score = build_vertical_score()
    ending = render_one(ending_score, root / 'authored-ending', budget)
    fixture = {'document_type': 'SceneScoreVerticalSourceEvidence', 'document_version': 1,
               'source': ending_score['sidecar'],
               'unmodified_mix': original['measurements']['mix.wav'],
               'authored_ending_mix': ending['measurements']['mix.wav'],
               'python_version': sys.version.split()[0],
               'human_audition': 'AUDITION_PENDING', 'approval': None}
    Path('modules/music/fixtures/music-vertical-source-v1.json').write_bytes(payload_bytes(fixture))
