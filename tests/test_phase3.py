import hashlib
import json
import wave

from fastapi.testclient import TestClient
import pytest

from scenescore.service import app
from tools.mux_performance import verify_export


def test_local_origin_http_and_websocket():
    with TestClient(app, base_url='http://127.0.0.1:8765') as client:
        assert client.get('/health', headers={'Origin': 'http://127.0.0.1:8765'}).status_code == 200
        for origin in ('https://example.org', 'null', 'http://127.0.0.1:5173'):
            assert client.get('/health', headers={'Origin': origin}).status_code == 403
        assert client.get('/health').status_code == 200
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/ws/fixtures', headers={'Origin': 'https://example.org'}):
                pass


def test_mux_requires_matching_bytes_and_aligned_stems(tmp_path):
    video = tmp_path / 'video.mp4'
    video.write_bytes(b'synthetic container stand-in; not a rendered video')
    files = []
    for stem in ('mix', 'piano', 'bass', 'brush', 'foley'):
        path = tmp_path / f'{stem}.wav'
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((2, 2, 8000, 0, 'NONE', 'not compressed'))
            stream.writeframes(bytes(8000 * 4))
        files.append({'stem': stem, 'filename': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    report = dict(version='performance-export-2', status='DRAFT_NOT_APPROVED', approval=None,
                  video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(), duration_s=1, files=files,
                  events=[], event_bytes='[]\n', event_hash=hashlib.sha256(b'[]\n').hexdigest())
    path = tmp_path / 'report.json'
    path.write_text(json.dumps(report))
    assert verify_export(path, video)[1].name == 'mix.wav'
    video.write_bytes(b'changed')
    with pytest.raises(ValueError, match='stale_video'):
        verify_export(path, video)
    report['video_sha256'] = hashlib.sha256(video.read_bytes()).hexdigest()
    report['files'][0]['filename'] = '../outside.wav'
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='local_filename'):
        verify_export(path, video)
