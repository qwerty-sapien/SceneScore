"""Production process ownership and render-profile regression checks."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from modules.blender import batch


def assert_absent(result):
    assert result['process_group_absent']
    if 'pgid' in result:
        with pytest.raises(ProcessLookupError):
            os.killpg(result['pgid'], 0)


def test_launch_failure_restores_handlers(tmp_path):
    before = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    result = batch.bounded([str(tmp_path / 'missing-executable')], tmp_path / 'launch.log')
    assert result['status'] == 'failed'
    assert 'FileNotFoundError' in result['error']
    assert_absent(result)
    assert {s: signal.getsignal(s) for s in before} == before
    assert json.loads((tmp_path / 'launch.job.json').read_text()) == result


def test_log_open_failure_never_launches(tmp_path, monkeypatch):
    log = tmp_path / 'log-is-a-directory'
    log.mkdir()
    def unexpected_launch(*args, **kwargs):
        pytest.fail('must not launch when log cannot be opened')
    monkeypatch.setattr(batch.subprocess, 'Popen', unexpected_launch)
    result = batch.bounded([sys.executable, '-c', 'pass'], log)
    assert result['status'] == 'failed'
    assert_absent(result)


@pytest.mark.parametrize('fail_at', [1, 2])
def test_evidence_write_failure_still_reaps_process(tmp_path, monkeypatch, fail_at):
    original = Path.write_text
    calls = 0
    def failing_write(path, *args, **kwargs):
        nonlocal calls
        if path.suffixes[-2:] == ['.job', '.json']:
            calls += 1
            if calls == fail_at:
                raise OSError('injected evidence storage failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', failing_write)
    result = batch.bounded([sys.executable, '-c', 'pass'], tmp_path / 'evidence.log')
    assert result['status'] == 'failed'
    assert_absent(result)
    key = 'error' if fail_at == 1 else 'evidence_write_error'
    assert 'injected evidence storage failure' in result[key]


def test_ignoring_child_is_killed_after_leader_exits(tmp_path):
    ready = tmp_path / 'child-ready'
    child_code = ('import signal,time; from pathlib import Path; '
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                  f'Path({str(ready)!r}).write_text("ready"); time.sleep(30)')
    parent_code = ('import subprocess,sys,time; from pathlib import Path; '
                   f'subprocess.Popen([sys.executable,"-c",{child_code!r}]); '
                   f'p=Path({str(ready)!r}); '
                   '\nwhile not p.exists(): time.sleep(.005)\n')
    result = batch.bounded([sys.executable, '-c', parent_code], tmp_path / 'descendant.log',
                           timeout=5, cleanup_grace=.2)
    assert result['status'] == 'passed'
    assert 'SIGKILL' in result['cleanup_signals']
    assert_absent(result)


def test_cancellation_during_cleanup_does_not_abandon_group(tmp_path):
    log = tmp_path / 'repeat-cancel.log'
    ready = tmp_path / 'ready'
    child_code = ('import signal,time; from pathlib import Path; '
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                  f'Path({str(ready)!r}).write_text("ready"); time.sleep(30)')
    runner_code = ('from modules.blender.batch import bounded; import sys; '
                   f'bounded([sys.executable,"-c",{child_code!r}],sys.argv[1],10,cleanup_grace=.3)')
    runner = subprocess.Popen([sys.executable, '-c', runner_code, str(log)], start_new_session=True)
    evidence = log.with_suffix('.job.json')
    try:
        deadline = time.monotonic() + 5
        while not (ready.exists() and evidence.exists()) and time.monotonic() < deadline:
            time.sleep(.01)
        assert ready.exists() and evidence.exists()
        runner.send_signal(signal.SIGTERM)
        time.sleep(.1)
        runner.send_signal(signal.SIGINT)
        runner.wait(timeout=5)
        result = json.loads(evidence.read_text())
        assert result['status'] == 'cancelled'
        assert 'SIGKILL' in result['cleanup_signals']
        assert_absent(result)
    finally:
        if runner.poll() is None:
            runner.kill()
            runner.wait(timeout=5)
        # Failure-path test cleanup uses only the exact identity recorded above.
        if evidence.exists():
            record = json.loads(evidence.read_text())
            try:
                os.killpg(record['pgid'], signal.SIGKILL)
            except ProcessLookupError:
                pass


@pytest.mark.parametrize(('arguments', 'dimensions'), [
    ([], ['1920', '1080']),
    (['--profile', 'preview'], ['640', '360']),
    (['--profile', 'final', '--resolution', '1280', '720'], ['1280', '720']),
])
def test_profile_preserves_native_cadence_and_final_dimensions(tmp_path, monkeypatch, arguments, dimensions):
    commands = []
    def capture(command, log, timeout):
        commands.append(command)
        return {'status': 'passed', 'process_group_absent': True}
    monkeypatch.setattr(batch, 'bounded', capture)
    assert batch.main(['--blender', sys.executable, '--out', str(tmp_path / 'output'),
                       '--recipe', '10_projectile_tower', '--render', *arguments]) == 0
    command = commands[0]
    assert command[command.index('--resolution') + 1:command.index('--resolution') + 3] == dimensions
    assert command[command.index('--fps') + 1] == '30'
    assert '--preview' not in command and '--export-only' not in command


def test_invalid_profile_dimension_fails_before_launch(tmp_path, monkeypatch):
    def unexpected_launch(*args, **kwargs):
        pytest.fail('invalid bounds must be rejected before launching')
    monkeypatch.setattr(batch, 'bounded', unexpected_launch)
    with pytest.raises(SystemExit):
        batch.main(['--blender', sys.executable, '--out', str(tmp_path), '--resolution', '9999', '1080'])


def test_launch_cancellation_records_identity_before_cleanup(tmp_path, monkeypatch):
    original = subprocess.Popen
    def cancel_during_launch(*args, **kwargs):
        child = original(*args, **kwargs)
        os.kill(os.getpid(), signal.SIGTERM)
        return child
    monkeypatch.setattr(batch.subprocess, 'Popen', cancel_during_launch)
    result = batch.bounded([sys.executable, '-c', 'import time; time.sleep(30)'],
                           tmp_path / 'launch-cancel.log')
    assert result['status'] == 'cancelled'
    assert_absent(result)


def test_log_close_failure_occurs_after_owned_process_cleanup(tmp_path, monkeypatch):
    log = tmp_path / 'close.log'
    original = Path.open
    class FailingClose:
        def __init__(self, stream):
            self.stream = stream
        def fileno(self):
            return self.stream.fileno()
        def close(self):
            self.stream.close()
            raise OSError('injected close failure')
    def failing_open(path, *args, **kwargs):
        stream = original(path, *args, **kwargs)
        return FailingClose(stream) if path == log else stream
    monkeypatch.setattr(Path, 'open', failing_open)
    result = batch.bounded([sys.executable, '-c', 'pass'], log)
    assert result['status'] == 'failed'
    assert 'injected close failure' in result['log_close_error']
    assert_absent(result)
