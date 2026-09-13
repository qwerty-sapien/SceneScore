"""Bounded trusted-script runner; serial jobs, scoped output, no arbitrary .blend input."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from modules.blender.recipes import IDS


def _group_exists(pgid):
    """A process group is owned from start_new_session until verified absent."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Some hosts briefly deny probes while a signalled process exits.
        # This is never evidence of absence; retry until the bounded deadline.
        return True
    return True


def _stop_group(proc, grace):
    """Reap the leader and confirm descendants exited, even if the leader exited first."""
    signals = []
    warnings = []
    for signum in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, signum)
        except ProcessLookupError:
            pass
        except PermissionError as error:
            warnings.append(f'{signal.Signals(signum).name}: {error}')
        else:
            signals.append(signal.Signals(signum).name)
        deadline = time.monotonic() + grace
        while True:
            # poll reaps the leader; wait alone cannot detect surviving descendants.
            proc.poll()
            if not _group_exists(proc.pid):
                proc.wait(timeout=grace)
                return True, signals, warnings
            if time.monotonic() >= deadline:
                break
            time.sleep(min(.02, max(0, deadline - time.monotonic())))
    proc.poll()
    return not _group_exists(proc.pid), signals, warnings


def bounded(command, log, timeout=600, *, cleanup_grace=2):
    """Run one owned group and return evidence; any setup/evidence failure fails closed.

    SIGINT/SIGTERM cancellation is deferred during launch until the group's identity
    is captured. Repeated cancellation cannot interrupt the bounded cleanup. Use
    the main thread when signal-based cancellation is required.
    """
    if timeout <= 0 or cleanup_grace <= 0:
        raise ValueError('timeout and cleanup_grace must be positive')
    log = Path(log)
    evidence = log.with_suffix('.job.json')
    started = time.monotonic()
    result = {'command': list(map(os.fspath, command)), 'timeout_s': timeout,
              'status': 'running', 'process_group_absent': True}
    proc = None
    output = None
    phase = 'setup'
    cancelled = False
    handlers = {}

    def interrupted(signum, frame):
        nonlocal cancelled
        cancelled = True
        if phase not in ('launch', 'cleanup'):
            raise InterruptedError('task cancellation')

    try:
        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGTERM, signal.SIGINT):
                handlers[signum] = signal.signal(signum, interrupted)
        log.parent.mkdir(parents=True, exist_ok=True)
        output = log.open('w')
        phase = 'launch'
        proc = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                start_new_session=True)
        result.update(pid=proc.pid, pgid=proc.pid, process_group_absent=False)
        phase = 'running'
        if cancelled:
            raise InterruptedError('task cancellation during launch')
        evidence.write_text(json.dumps(result, indent=2) + '\n')
        result['returncode'] = proc.wait(timeout=timeout)
        result['status'] = 'passed' if proc.returncode == 0 else 'failed'
    except subprocess.TimeoutExpired:
        result['status'] = 'timeout'
    except (KeyboardInterrupt, InterruptedError):
        result['status'] = 'cancelled'
    except Exception as error:
        result.update(status='failed', error=f'{type(error).__name__}: {error}')
    finally:
        phase = 'cleanup'
        try:
            if proc is not None:
                try:
                    absent, sent, warnings = _stop_group(proc, cleanup_grace)
                    result.update(process_group_absent=absent, cleanup_signals=sent,
                                  returncode=proc.returncode)
                    if warnings:
                        result['cleanup_warnings'] = warnings
                    if not absent:
                        result.update(status='failed', cleanup_error='owned process group remains')
                except Exception as error:
                    result.update(status='failed', process_group_absent=False,
                                  cleanup_error=f'{type(error).__name__}: {error}')
            if output is not None:
                try:
                    output.close()
                except Exception as error:
                    result.update(status='failed', log_close_error=f'{type(error).__name__}: {error}')
            result['duration_s'] = time.monotonic() - started
            try:
                evidence.write_text(json.dumps(result, indent=2) + '\n')
            except Exception as error:
                # The caller can persist this return value elsewhere. A missing
                # evidence record must never masquerade as a successful job.
                result.update(status='failed', evidence_write_error=f'{type(error).__name__}: {error}')
        finally:
            for signum, handler in handlers.items():
                signal.signal(signum, handler)
    return result


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--blender', default=os.environ.get('BLENDER_BIN'))
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--recipe', choices=IDS, action='append')
    p.add_argument('--duration', type=float)
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--render', action='store_true')
    p.add_argument('--profile', choices=['preview', 'final'], default='final',
                   help='preview: 640x360; final: 1920x1080; both retain requested cadence')
    p.add_argument('--resolution', type=int, nargs=2, metavar=('WIDTH', 'HEIGHT'),
                   help='explicit resolution overrides profile dimensions')
    p.add_argument('--variant', choices=['default', 'near_miss', 'contact'], default='default')
    a = p.parse_args(argv)
    if not a.blender or not Path(a.blender).is_file():
        p.error('verified --blender or BLENDER_BIN required')
    if not 1 <= a.timeout <= 1800:
        p.error('timeout must be 1..1800 seconds')
    if not 1 <= a.fps <= 120 or (a.duration is not None and not 0 < a.duration <= 60):
        p.error('duration must be 0..60 seconds and fps must be 1..120')
    resolution = a.resolution or ([640, 360] if a.profile == 'preview' else [1920, 1080])
    if not all(32 <= dimension <= 1920 for dimension in resolution):
        p.error('resolution dimensions must be 32..1920')
    root = Path(__file__).resolve().parents[2]
    out = a.out.resolve()
    # Caller chooses an owned artifact scope. The entrypoint rejects stale outputs.
    if out in (Path('/'), Path.home(), root):
        p.error('unsafe output root')
    result = []
    for rid in a.recipe or IDS:
        dest = out / (rid + '-' + a.variant)
        command = [a.blender, '--background', '--factory-startup', '--python-exit-code', '1',
                   '--threads', '2', '--python', str(root / 'modules/blender/scenes' / f'{rid}.py'),
                   '--', '--out', str(dest), '--seed', '42', '--fps', str(a.fps),
                   '--variant', a.variant, '--resolution', *map(str, resolution)]
        if a.duration is not None:
            command += ['--duration', str(a.duration)]
        if not a.render:
            command += ['--export-only']
        r = bounded(command, out / (rid + '.log'), a.timeout)
        result.append(r)
        if r['status'] != 'passed' or not r['process_group_absent']:
            break
    out.mkdir(parents=True, exist_ok=True)
    (out / 'batch.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if all(r['status'] == 'passed' and r['process_group_absent'] for r in result) else 1


if __name__ == '__main__':
    raise SystemExit(main())
