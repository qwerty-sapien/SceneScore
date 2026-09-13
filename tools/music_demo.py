"""Serve the frozen music candidate in the existing studio for a bounded interval."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path('artifacts/music-vertical/candidate-v1'))
    parser.add_argument('--port', type=int, default=8772)
    parser.add_argument('--seconds', type=float, default=600)
    args = parser.parse_args()
    if not 10 <= args.seconds <= 3600 or not 1024 <= args.port <= 65535:
        parser.error('Use 10..3600 seconds and an unprivileged loopback port')
    root = Path(__file__).resolve().parents[1]
    candidate = args.candidate.resolve()
    if not (candidate / 'catalog.json').is_file():
        subprocess.run([sys.executable, 'tools/prepare_music_vertical.py', '--out', str(candidate)],
                       cwd=root, check=True, timeout=120)
    catalog = json.loads((candidate / 'catalog.json').read_text())
    if len(catalog['entries']) != 1:
        raise ValueError('one_frozen_music_candidate_required')
    entry = catalog['entries'][0]
    if Path(entry['url']).name != entry['url']:
        raise ValueError('local_candidate_filename_required')
    raw = (candidate / entry['url']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError('candidate_hash_mismatch')
    bundle = json.loads(raw)
    if Path(bundle['video']).name != bundle['video']:
        raise ValueError('local_video_filename_required')
    if hashlib.sha256((candidate / bundle['video']).read_bytes()).hexdigest() != bundle['video_sha256']:
        raise ValueError('candidate_video_hash_mismatch')
    public = root / 'apps/web/public/music-vertical'
    public.mkdir(parents=True, exist_ok=True)
    for name in {'catalog.json', entry['url'], bundle['video']}:
        shutil.copy2(candidate / name, public / name)
    subprocess.run(['npm', 'run', 'build'], cwd=root, check=True, timeout=120)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', args.port))
    process = None
    try:
        process = subprocess.Popen([sys.executable, '-m', 'http.server', str(args.port), '--bind',
                                    '127.0.0.1', '--directory', str(root / 'artifacts/web-dist')],
                                   cwd=root, start_new_session=True)
        print(json.dumps({'job_pid': process.pid, 'job_pgid': process.pid,
                          'url': f'http://127.0.0.1:{args.port}/?music=1',
                          'seconds': args.seconds, 'approval': None,
                          'instruction': 'Start music demo; M requests a scene-directed key change.'}), flush=True)
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'Music web process exited {process.returncode}')
            time.sleep(.2)
    except KeyboardInterrupt:
        pass
    finally:
        if process is not None:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
            print(json.dumps({'stopped_pid': process.pid, 'exit_code': process.returncode}), flush=True)


if __name__ == '__main__':
    main()
