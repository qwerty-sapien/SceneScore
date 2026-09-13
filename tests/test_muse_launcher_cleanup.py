"""Task-owned process-group teardown races without starting child processes."""
import signal
import subprocess

from tools import muse_demo


def test_cleanup_tolerates_exited_group_and_still_stops_other_child(monkeypatch):
    calls = []
    class Child:
        def __init__(self, pid):
            self.pid, self.returncode = pid, 0
        def wait(self, timeout):
            calls.append(('wait', self.pid))
            return 0
    def killpg(pid, sig):
        calls.append(('signal', pid, sig))
        if pid == 101 or sig == 0:
            raise ProcessLookupError
    monkeypatch.setattr(muse_demo.os, 'killpg', killpg)
    muse_demo.stop_children([Child(101), Child(202)])
    assert ('signal', 202, signal.SIGINT) in calls
    assert ('wait', 101) in calls and ('wait', 202) in calls


def test_cleanup_forces_exact_unresponsive_group(monkeypatch):
    calls = []
    class Child:
        pid, returncode, waits = 303, -9, 0
        def wait(self, timeout):
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired('fixture', timeout)
    def killpg(pid, sig):
        assert pid == 303
        calls.append(sig)
        if sig == 0:
            raise ProcessLookupError
    monkeypatch.setattr(muse_demo.os, 'killpg', killpg)
    muse_demo.stop_children([Child()])
    assert calls == [signal.SIGINT, signal.SIGKILL, 0]
