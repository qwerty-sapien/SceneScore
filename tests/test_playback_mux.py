"""Playback-window identity remains bound through lossless stem export."""
import hashlib
import json
import wave

import pytest

from modules.blender.production.playback import create_playback_window, encode_playback_window
from tools.mux_performance import verify_export


def bundle(tmp_path):
    source=b'[]\n'
    window,_=create_playback_window(source,1)
    raw=encode_playback_window(window)
    video=tmp_path/'video.mp4'
    video.write_bytes(b'fixture bytes, not a rendered clip')
    files=[]
    for stem in ('mix','piano','bass','brush','foley'):
        path=tmp_path/(stem+'.wav')
        with wave.open(str(path),'wb') as stream:
            stream.setparams((2,2,48000,0,'NONE','not compressed'))
            stream.writeframes(bytes(48000*4))
        files.append(dict(stem=stem,filename=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    data=dict(version='performance-export-2',status='DRAFT_NOT_APPROVED',approval=None,
              video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),duration_s=1,files=files,
              events=[],event_bytes=source.decode(),event_hash=hashlib.sha256(source).hexdigest(),
              playback_window=window,playback_window_bytes=raw.decode(),playback_window_sha256=hashlib.sha256(raw).hexdigest(),
              source_events_bytes=source.decode())
    policy={k:window[k] for k in ('version','start_s','duration_s','render_fps','final_fade_s')}
    scene_raw=json.dumps({'playback_policy':policy})
    data.update(playback_policy=policy,scene_input_bytes=scene_raw,scene_hash=hashlib.sha256(scene_raw.encode()).hexdigest())
    report=tmp_path/'report.json'
    report.write_text(json.dumps(data))
    return report,video,data


def test_exact_frame_audio_window(tmp_path):
    report,video,_=bundle(tmp_path)
    actual,_=verify_export(report,video)
    assert actual['playback_window']['audio_sample_count']==30*1600


@pytest.mark.parametrize('mutation',['window_bytes','source_bytes','duration','policy'])
def test_changed_projection_rejects_stems(tmp_path,mutation):
    report,video,data=bundle(tmp_path)
    if mutation=='window_bytes':
        data['playback_window_bytes']+=' '
    elif mutation=='source_bytes':
        data['source_events_bytes']='[] '
    elif mutation=='duration':
        data['duration_s']=2
    else:
        data['playback_window']['final_fade_s']=.02
        raw=encode_playback_window(data['playback_window'])
        data['playback_window_bytes']=raw.decode()
        data['playback_window_sha256']=hashlib.sha256(raw).hexdigest()
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        verify_export(report,video)

@pytest.mark.parametrize('field',['playback_window','playback_policy','scene_input_bytes'])
def test_missing_bound_runtime_policy_rejects_export(tmp_path,field):
    report,video,data=bundle(tmp_path)
    data[field]=None if field!='scene_input_bytes' else '{}'
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        verify_export(report,video)
