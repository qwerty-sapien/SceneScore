import threading
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from modules.muse.acquisition.store import Recorder, replay, recover, export_session, delete_session, manifest, encoded
from modules.muse.acquisition.tests.helpers import metadata, chunk
from modules.muse.acquisition.__main__ import main
from modules.muse.acquisition.live import capture_lsl, health
from modules.muse.acquisition.api import router


def test_roundtrip_exact_raw_values_and_distinct_sample_times(tmp_path):
    path = tmp_path / 'session'
    data = chunk(value=-15.234567890123)
    recorder = Recorder(path, metadata(), explicitly_started=True)
    recorder.append(data)
    recorder.close()
    assert list(replay(path)) == [data]
    assert len(set(data['device_times_s'])) == 64
    assert manifest(path)['status'] == 'closed'
    assert path.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize('fault', ['sequence', 'sample_start_index', 'session_id', 'channels', 'sample_rate_hz', 'timestamp', 'source', 'empty'])
def test_reject_corrupt_continuity_without_overwriting_good_chunk(tmp_path, fault):
    recorder = Recorder(tmp_path / 's', metadata(), explicitly_started=True)
    recorder.append(chunk())
    bad = chunk(1, 64)
    if fault in {'sequence', 'sample_start_index', 'sample_rate_hz'}:
        bad[fault] += 1
    elif fault == 'session_id':
        bad[fault] = 'other'
    elif fault == 'channels':
        bad['channels'][0]['name'] = 'wrong'
    elif fault == 'timestamp':
        bad['device_times_s'] = [i/256 for i in range(64)]
    elif fault == 'source':
        bad['provenance']['source_mode'] = 'replay'
    elif fault == 'empty':
        bad['samples'], bad['device_times_s'] = [], []
    with pytest.raises(ValueError):
        recorder.append(bad)
    recorder.close('rejected')
    assert len(list(replay(recorder.path))) == 1


def test_gap_and_reconnect_recorded_without_interpolation(tmp_path):
    recorder = Recorder(tmp_path/'s', metadata(), explicitly_started=True)
    recorder.append(chunk())
    recorder.append(chunk(1, 68, gap=4))
    data = chunk(2, 132, epoch='refit-2')
    data['device_times_s'] = [i/256 for i in range(64)]
    recorder.append(data)
    recorder.close('disconnect')
    result = list(replay(recorder.path))
    assert result[1]['dropped_samples_before'] == 4
    assert result[2]['device_times_s'][0] == 0
    assert sum(len(x['samples']) for x in result) == 192


def test_recover_interrupted_atomic_write(tmp_path):
    recorder = Recorder(tmp_path/'s', metadata(), explicitly_started=True)
    recorder.append(chunk())
    (recorder.path/'chunks/000000001.json.tmp').write_text('{broken')
    value = recover(recorder.path)
    assert value['committed_chunks'] == 1
    assert value['status'] == 'recovered'


def test_corrupt_committed_data_is_not_silently_recovered(tmp_path):
    recorder = Recorder(tmp_path/'s', metadata(), explicitly_started=True)
    recorder.append(chunk())
    (recorder.path/'chunks/000000000.json').write_text('{broken')
    with pytest.raises(ValueError):
        recover(recorder.path)


def test_explicit_start_exclusive_session_and_safe_delete(tmp_path):
    path = tmp_path/'s'
    with pytest.raises(ValueError):
        Recorder(path, metadata(), explicitly_started=False)
    recorder = Recorder(path, metadata(), explicitly_started=True)
    with pytest.raises(FileExistsError):
        Recorder(path, metadata(), explicitly_started=True)
    recorder.append(chunk())
    recorder.close()
    with pytest.raises(ValueError):
        delete_session(path, confirmed_session_id='wrong')
    assert export_session(path, tmp_path/'local.zip')['chunks'] == 1
    with pytest.raises(ValueError):
        export_session(path, path/'bad.zip')
    delete_session(path, confirmed_session_id='synthetic-session')
    assert not path.exists()


def test_symlink_export_or_delete_rejected(tmp_path):
    recorder = Recorder(tmp_path/'s', metadata(), explicitly_started=True)
    recorder.close()
    link = tmp_path/'link'
    link.symlink_to(recorder.path)
    with pytest.raises(ValueError):
        delete_session(link, confirmed_session_id='synthetic-session')
    (recorder.path/'secret').symlink_to('/etc/hosts')
    with pytest.raises(ValueError):
        export_session(recorder.path, tmp_path/'bad.zip')


def test_cli_record_recover_inspect_export_delete(tmp_path, capsys):
    meta, source, session = tmp_path/'meta.json', tmp_path/'input.jsonl', tmp_path/'s'
    meta.write_bytes(encoded(metadata()))
    source.write_bytes(encoded(chunk()))
    assert main(['record-file', str(session), str(meta), str(source), '--start']) == 0
    assert main(['inspect', str(session)]) == 0
    assert main(['replay', str(session)]) == 0
    assert 'synthetic' in capsys.readouterr().err
    assert main(['export', str(session), str(tmp_path/'export.zip')]) == 0
    assert main(['delete', str(session), '--confirm-session-id', 'synthetic-session']) == 0


def test_cli_failure_closes_partial_session(tmp_path):
    meta, source, session = tmp_path/'meta.json', tmp_path/'input.jsonl', tmp_path/'s'
    meta.write_bytes(encoded(metadata()))
    source.write_bytes(encoded(chunk()) + b'INVALID\n')
    assert main(['record-file', str(session), str(meta), str(source), '--start']) == 2
    assert manifest(session)['status'] == 'closed'
    assert manifest(session)['stop_reason'] == 'interrupted_or_invalid_input'


def test_live_without_explicit_verified_hardware_never_starts(tmp_path):
    with pytest.raises(ValueError):
        capture_lsl(tmp_path/'s', metadata(), source_id='unverified', seconds=1, consent=True)
    assert not (tmp_path/'s').exists()
    assert health()['code'] == 'HARDWARE_UNVERIFIED'


def test_router_no_capture_side_effects():
    app = FastAPI()
    app.include_router(router, prefix='/muse')
    before = {x.ident for x in threading.enumerate()}
    with TestClient(app) as client:
        assert client.get('/muse/health').json()['recording'] is False
        assert client.post('/muse/diagnostics', json=chunk()).json()['controls'] == 'DISARMED'
        error = client.post('/muse/diagnostics', json={})
        assert error.status_code == 422
        assert error.json()['retryable'] is False
        assert client.post('/muse/capture').status_code == 404
    assert {x.ident for x in threading.enumerate()} == before
