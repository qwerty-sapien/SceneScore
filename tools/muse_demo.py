"""Run a bounded local Muse demo; both exact child processes are stopped on exit."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import tempfile


def signal_group(pid, sig):
    try:
        os.killpg(pid, sig)
        return True
    except ProcessLookupError:
        return False


def stop_children(processes):
    errors = []
    for process in processes:
        try:
            signal_group(process.pid, signal.SIGINT)
        except OSError as error:
            errors.append(f'Could not signal PGID={process.pid}: {type(error).__name__}')
    for process in processes:
        try:
            try:
                process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                signal_group(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
            print(f'STOPPED PID={process.pid} exit={process.returncode}', flush=True)
            if signal_group(process.pid, 0):
                signal_group(process.pid, signal.SIGKILL)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    if not signal_group(process.pid, 0):
                        break
                    time.sleep(.05)
                else:
                    errors.append(f'Task-owned process group still exists: {process.pid}')
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append(f'Could not stop PGID={process.pid}: {type(error).__name__}')
    if errors:
        raise RuntimeError('; '.join(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--port', type=int, default=8771)
    parser.add_argument('--source', choices=['synthetic', 'ble'], default='synthetic')
    parser.add_argument('--live-consent', type=Path, default=os.environ.get('MUSE_LIVE_CONSENT'))
    parser.add_argument('--quality-profile', type=Path)
    args = parser.parse_args()
    if not 10 <= args.seconds <= 3600 or not 1024 <= args.port <= 65535 or args.port == 8766:
        parser.error('Use 10..3600 seconds and a distinct unprivileged web port')
    root = Path(__file__).resolve().parents[1]
    if not (root / 'apps/web/public/studio/catalog.json').is_file():
        parser.error('Prepare the scene assets with make demo before using this companion launcher')
    consent_directory = tempfile.TemporaryDirectory(prefix='scenescore-ble-consent-')
    if args.source == 'ble' and args.live_consent is None:
        # The explicit --source ble / make muse-live invocation starts this
        # private local workflow. Retain the existing bridge CLI shape without
        # asking the operator to repeat that instruction in another prompt.
        statement = 'Operator explicitly invoked the local BLE processing launcher.'
        args.live_consent = Path(consent_directory.name) / 'consent.json'
        args.live_consent.write_text(json.dumps({'live_processing': True, 'raw_recording': False,
                                               'participant_statement': statement}))
        args.live_consent.chmod(0o600)
    origin = f'http://127.0.0.1:{args.port}'
    environment = {**os.environ, 'PYTHONPATH': str(root) + os.pathsep + str(root / 'src')}
    processes = []
    def interrupt(*_):
        raise KeyboardInterrupt
    previous_term = signal.signal(signal.SIGTERM, interrupt)
    print(f'TASK LAUNCHER PID={os.getpid()}', flush=True)
    try:
        subprocess.run(['npm', 'run', 'build'], cwd=root, check=True)
        bridge_command = [sys.executable, '-m', 'services.bridge', '--source', args.source,
                          '--seconds', str(args.seconds), '--origin', origin]
        if args.source == 'ble':
            bridge_command.extend(['--live-consent', str(args.live_consent.resolve())])
            if args.quality_profile:
                bridge_command.extend(['--quality-profile', str(args.quality_profile.resolve())])
        commands = [
            [sys.executable, '-m', 'uvicorn', 'scenescore.service:app', '--host', '127.0.0.1', '--port', str(args.port)],
            bridge_command,
        ]
        for command in commands:
            process = subprocess.Popen(command, cwd=root, env=environment, start_new_session=True)
            processes.append(process)
            print(f'TASK JOB PID={process.pid} PGID={process.pid}: {command[2]}', flush=True)
        workflow = ('Select LIVE_MUSE, paste the companion token, scan and select your headset. '
                    'Streaming starts only after Connect headset; calibrated quality and timing gates control arming. '
                    if args.source == 'ble' else
                    'The companion is SYNTHETIC_TEST. Paste its token, select Simulated, wait for warmup and arm. ')
        print(f'Open {origin}; Start blink demo. ' + workflow +
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
        try:
            stop_children(processes)
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            consent_directory.cleanup()


if __name__ == '__main__':
    main()
