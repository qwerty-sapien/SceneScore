"""Build and objectively inspect all 12 audition exports; no listening approval is inferred."""
import argparse
import json
import os
from pathlib import Path
import signal
import threading
import time

from .catalog import VARIATIONS, list_catalog, payload_bytes
from .render import RenderBudget, render_arrangement


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New subtree inside artifacts/music')
    parser.add_argument('--sample-rate', type=int, default=48000)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('fresh_output_tree_required')
    cancelled = threading.Event()
    def stop(signum, frame):
        cancelled.set()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    start = time.monotonic()
    print(json.dumps({'process_id': os.getpid(), 'max_wave_runtime_s': 600,
                      'sample_rate_hz': args.sample_rate}), flush=True)
    summaries = []
    for composition in list_catalog()['compositions']:
        for variation in VARIATIONS:
            remaining = 600 - (time.monotonic() - start)
            if remaining <= 0:
                raise TimeoutError('wave_runtime_budget_exceeded')
            output = args.output / composition['id'] / variation
            manifest = render_arrangement(composition['id'], output, variation, args.sample_rate,
                                          cancellation=cancelled, budget=RenderBudget(max_runtime_s=min(120, remaining)))
            row = {'composition_id': composition['id'], 'variation': variation, 'output': str(output),
                   'mix': manifest['measurements']['mix.wav'],
                   'frames_by_stem': {k: m['frames'] for k, m in manifest['measurements'].items()},
                   'manifest_path': str(output / 'manifest.json'), 'audition_status': 'AUDITION_PENDING'}
            summaries.append(row)
            (args.output / 'wave-render-report.json').write_bytes(payload_bytes({
                'process_id': os.getpid(), 'status': 'in_progress', 'renders': summaries,
                'sample_rate_hz': args.sample_rate, 'audition_status': 'AUDITION_PENDING'}))
            print(json.dumps(row), flush=True)
    (args.output / 'wave-render-report.json').write_bytes(payload_bytes({
        'process_id': os.getpid(), 'status': 'objective_checks_passed', 'renders': summaries,
        'elapsed_s': time.monotonic() - start, 'sample_rate_hz': args.sample_rate,
        'audition_status': 'AUDITION_PENDING',
        'human_audition': 'not_run', 'live_browser_playback': 'not_run'}))


if __name__ == '__main__':
    main()
