import json
import sys
import pytest
from fastapi import HTTPException
from modules.blender import api
from modules.blender.batch import bounded
from modules.blender.summary import event_query,state_query


def test_scoped_readonly_api(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'ARTIFACT_ROOT',tmp_path)
    with pytest.raises(HTTPException):
        api.scope('../')
    bundle=tmp_path/'valid'
    bundle.mkdir()
    (bundle/'summary.json').write_text('{"summary_version":"blender-summary-1"}')
    assert api.get_summary('valid')['summary_version']=='blender-summary-1'


def test_exact_queries_no_nearest_fabrication(tmp_path):
    for name in ['interactions','object_states']:
        (tmp_path/(name+'.jsonl')).write_text(json.dumps({'id':'known'})+'\n')
    assert event_query(tmp_path,'known')=={'id':'known'}
    assert state_query(tmp_path,'known')=={'id':'known'}
    with pytest.raises(KeyError):
        event_query(tmp_path,'unknown')


def test_bounded_job_exit_and_timeout_cleanup(tmp_path):
    ok=bounded([sys.executable,'-c','print("ok")'],tmp_path/'ok.log',timeout=3)
    assert ok['status']=='passed' and ok['process_group_absent']
    timeout=bounded([sys.executable,'-c','import time; time.sleep(10)'],tmp_path/'timeout.log',timeout=.05)
    assert timeout['status']=='timeout' and timeout['process_group_absent']


def test_health_does_not_spawn_blender(monkeypatch):
    monkeypatch.delenv('BLENDER_BIN',raising=False)
    assert api.health()['status']=='unavailable'


def test_runner_sigterm_cleans_owned_child(tmp_path):
    import os
    import signal
    import subprocess
    import time
    log=tmp_path/'cancel.log'
    command=[sys.executable,'-c',
        'import sys; from modules.blender.batch import bounded; '
        'bounded([sys.executable,"-c","import time; time.sleep(30)"],sys.argv[1],20)',str(log)]
    proc=subprocess.Popen(command)
    try:
        deadline=time.monotonic()+5
        evidence=log.with_suffix('.job.json')
        while not evidence.exists() and time.monotonic()<deadline:
            time.sleep(.02)
        assert evidence.exists()
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
        result=json.loads(evidence.read_text())
        assert result['status']=='cancelled' and result['process_group_absent']
        with pytest.raises(ProcessLookupError):
            os.kill(result['pid'],0)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_captured_summary_is_canonical_and_compact():
    from pathlib import Path
    from scenescore.contracts import validate
    summary=json.loads(Path('modules/blender/fixtures/hero-summary.json').read_text())
    assert summary['summary_version']=='blender-summary-1'
    validate(summary['scene'])
    for obj in summary['objects']:
        assert len(obj['keyframes'])<=5
        for state in obj['keyframes']:
            validate(state)
    for event in summary['events']:
        validate(event)
    assert not any('vertices' in obj for obj in summary['objects'])
