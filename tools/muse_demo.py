"""Run a bounded local Muse demo; both exact child processes are stopped on exit."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--port', type=int, default=8771)
    args = parser.parse_args()
    if not 10 <= args.seconds <= 3600 or not 1024 <= args.port <= 65535 or args.port == 8766:
        parser.error('Use 10..3600 seconds and a distinct unprivileged web port')
    root = Path(__file__).resolve().parents[1]
    if not (root / 'apps/web/public/studio/catalog.json').is_file():
        parser.error('Prepare the scene assets with make demo before using this companion launcher')
    subprocess.run(['npm', 'run', 'build'], cwd=root, check=True)
    origin = f'http://127.0.0.1:{args.port}'
    environment = {**os.environ, 'PYTHONPATH': str(root) + os.pathsep + str(root / 'src')}
    processes = []
    try:
        commands = [
            [sys.executable, '-m', 'uvicorn', 'scenescore.service:app', '--host', '127.0.0.1', '--port', str(args.port)],
            [sys.executable, '-m', 'services.bridge', '--source', 'synthetic', '--seconds', str(args.seconds), '--origin', origin],
        ]
        for command in commands:
            process = subprocess.Popen(command, cwd=root, env=environment, start_new_session=True)
            processes.append(process)
            print(f'TASK JOB PID={process.pid} PGID={process.pid}: {command[2]}', flush=True)
        print(f'Open {origin}; Start blink demo. The companion is SYNTHETIC_TEST. '
              'Paste its ephemeral token, select Simulated, wait for warmup and arm. '
              'Ctrl-C stops both jobs; raw EEG is never recorded.', flush=True)
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            for process in processes:
                if process.poll() is not None:
                    raise RuntimeError(f'Child PID={process.pid} exited {process.returncode}')
            time.sleep(.2)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
        for process in processes:
            try:
                process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
            print(f'STOPPED PID={process.pid} exit={process.returncode}', flush=True)


if __name__ == '__main__':
    main()
