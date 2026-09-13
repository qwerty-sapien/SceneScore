"""Independent timestamp/hash mutations; no fixtures asserted as real video evidence."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from modules.blender.production import media


def probe_fixture(count=3):
    return {'streams': [{'width': 640, 'height': 360, 'avg_frame_rate': '30/1',
                         'r_frame_rate': '30/1', 'duration': str(count / 30)}],
            'frames': [{'pts_time': str(i / 30)} for i in range(count)]}


def decoded_fixture(count=3):
    return [{'pts_s': i / 30, 'duration_s': 1 / 30, 'sha256': str(i) * 64} for i in range(count)]


def states_fixture(count=3):
    return [{'tick': i, 'time_s': i / 240,
             'objects': {'ball': {'position_m': [i / 240, 0, 0]}}} for i in range(count * 8 + 1)]


def test_every_original_pts_and_stream_rate_are_checked():
    probe = probe_fixture()
    assert media.inspect_probe(probe, 3, .1, (640, 360))['status'] == 'PASSED'
    for mutate in [lambda x: x['frames'][1].update(pts_time='0'),
                   lambda x: x['frames'][1].update(pts_time='0.0666666667'),
                   lambda x: x['frames'][0].update(pts_time='nan'),
                   lambda x: x['streams'][0].update(avg_frame_rate='15/1'),
                   lambda x: x['streams'][0].update(height=720),
                   lambda x: x['streams'][0].update(duration='.2'),
                   lambda x: x['frames'].pop()]:
        broken = copy.deepcopy(probe)
        mutate(broken)
        assert media.inspect_probe(broken, 3, .1, (640, 360))['status'] == 'FAILED'
    del probe['frames'][1]['pts_time']
    probe['frames'][1]['best_effort_timestamp_time'] = str(1 / 30)
    assert media.inspect_probe(probe, 3, .1, (640, 360))['status'] == 'FAILED'


def test_framehash_uses_complete_decoded_records_and_original_time_base():
    text = '#format: frame checksums\n#tb 0: 1/15360\n0, 0, 0, 512, 345600, ' + 'a' * 64
    text += '\n0, 512, 512, 512, 345600, ' + 'b' * 64
    rows = media.parse_framehash(text)
    assert rows[1]['pts_s'] == pytest.approx(1 / 30)
    assert rows[1]['size_bytes'] == 345600
    assert len(rows) == 2
    with pytest.raises(ValueError, match='unexpected'):
        media.parse_framehash(text + '\ndecode error')
    with pytest.raises(ValueError, match='time base'):
        media.parse_framehash('0, 0, 0, 1, 123, ' + 'a' * 64)


def test_motion_clock_requires_all_ticks_and_finite_positions():
    samples = states_fixture()
    moving = media.motion_frames(samples, ['ball'], 240, 3)
    assert [item['frame_index'] for item in moving] == [1, 2]
    assert moving[0]['objects_displacement_m']['ball'] == pytest.approx(1 / 30)
    for broken in [samples[:-1], samples[:7] + samples[8:], samples + samples[:1]]:
        with pytest.raises(ValueError):
            media.motion_frames(broken, ['ball'], 240, 3)
    broken = copy.deepcopy(samples)
    broken[8]['objects']['ball']['position_m'][0] = float('nan')
    with pytest.raises(ValueError):
        media.motion_frames(broken, ['ball'], 240, 3)
    broken = copy.deepcopy(samples)
    broken[8]['time_s'] += .001
    with pytest.raises(ValueError):
        media.motion_frames(broken, ['ball'], 240, 3)


def test_low_rate_repeat_is_rejected_during_movement_and_rest_is_allowed():
    rows = decoded_fixture()
    rows[1]['sha256'] = rows[0]['sha256']
    moving = [{'frame_index': 1}]
    result = media.inspect_decode(rows, 3, moving, ['a', 'b', 'c'])
    assert result['status'] == 'FAILED'
    assert result['actual_frames_decoded'] == 3
    assert result['decoded_distinct_full_frame_hashes'] == 2
    assert result['duplicate_moving_transitions'] == [1]
    assert media.inspect_decode(rows, 3, [], ['a', 'a', 'c'])['status'] == 'PASSED'
    # Lossy decode can differ on an exactly copied PNG: both streams are checked.
    result = media.inspect_decode(decoded_fixture(), 3, moving, ['same', 'same', 'new'])
    assert result['duplicate_moving_transitions'] == [1]


def test_partial_decode_or_retimed_decode_cannot_pass():
    assert media.inspect_decode(decoded_fixture()[:2], 3, [], [])['status'] == 'FAILED'
    rows = decoded_fixture()
    rows[1]['duration_s'] = 1 / 15
    assert media.inspect_decode(rows, 3, [], [])['status'] == 'FAILED'


def candidate_fixture(tmp_path):
    candidate = tmp_path / 'candidate'
    render_dir = candidate / 'renders' / 'diagnostic' / 'beauty'
    render_dir.mkdir(parents=True)
    (candidate / 'scene.blend').write_bytes(b'synthetic source hash fixture, not an actual blend')
    (candidate / 'physics_states.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in states_fixture()))
    (render_dir / 'video.mp4').write_bytes(b'synthetic encoded-byte fixture, not an actual video')
    for i in range(1, 4):
        (render_dir / f'frame_{i:06d}.png').write_bytes(str(i).encode())
    state_hash = media.sha256(candidate / 'physics_states.jsonl')
    blend_hash = media.sha256(candidate / 'scene.blend')
    production = {'duration_s': .1, 'render_fps': 30, 'physics_hz': 240,
                  'objects': [{'object_id': 'ball'}],
                  'lineage': {'artifacts': {'scene.blend': blend_hash}, 'states_sha256': state_hash}}
    (candidate / 'production.json').write_text(json.dumps(production))
    render = {'camera': 'beauty', 'profile': 'diagnostic', 'fps': 30, 'frame_count': 3,
              'width': 640, 'height': 360, 'returncode': 0, 'source_hash': blend_hash,
              'states_hash': state_hash, 'video_hash': media.sha256(render_dir / 'video.mp4')}
    (render_dir / 'render.json').write_text(json.dumps(render))
    return candidate, render_dir


def fake_tools(command, log, timeout):
    """Synthetic process responses only, distinctly local to these unit tests."""
    if '-show_frames' in command:
        Path(log).write_text(json.dumps(probe_fixture()))
    else:
        text = '#tb 0: 1/30\n' + '\n'.join(
            f'0, {i}, {i}, 1, 345600, ' + hashlib.sha256(str(i).encode()).hexdigest() for i in range(3))
        Path(log).write_text(text)
    return {'status': 'passed', 'process_group_absent': True, 'command': command,
            'timeout_s': timeout, 'returncode': 0, 'synthetic_test_fixture': True}


def test_report_binds_inputs_and_does_not_promote_other_gates(tmp_path, monkeypatch):
    candidate, directory = candidate_fixture(tmp_path)
    monkeypatch.setattr(media, 'bounded', fake_tools)
    path, report = media.verify_media(candidate, ffmpeg='fake-ffmpeg', ffprobe='fake-ffprobe')
    assert path == directory / 'media-validation.json'
    assert report['status'] == 'PASSED'
    assert report['approval'] is None
    assert report['continuous_motion_perception'] == 'NOT_ASSESSED'
    assert report['physics_validation'] == 'NOT_ASSESSED'
    assert report['expected']['audio_samples_per_video_frame'] == 1600
    assert len(report['jobs']) == 2
    for job in report['jobs']:
        assert job['timeout_s'] == 180
        assert job['command'][job['command'].index('-threads') + 1] == '2'
        assert job['process_group_absent'] is True
    with pytest.raises(FileExistsError, match='preserving'):
        media.verify_media(candidate)


def test_stale_render_source_fails_before_tools(tmp_path, monkeypatch):
    candidate, _ = candidate_fixture(tmp_path)
    (candidate / 'scene.blend').write_bytes(b'changed')
    monkeypatch.setattr(media, 'bounded', lambda *a, **k: pytest.fail('must not run tools'))
    _, report = media.verify_media(candidate)
    assert report['status'] == 'FAILED'
    assert report['checks']['input_integrity']['status'] == 'FAILED'
    assert report['jobs'] == []


@pytest.mark.parametrize('failure', ['timeout', 'failed', 'cancelled', 'group_remains'])
def test_failed_or_unclean_process_never_passes(tmp_path, monkeypatch, failure):
    candidate, _ = candidate_fixture(tmp_path)

    def fail_tool(command, log, timeout):
        return {'status': 'passed' if failure == 'group_remains' else failure,
                'process_group_absent': failure != 'group_remains'}

    monkeypatch.setattr(media, 'bounded', fail_tool)
    _, report = media.verify_media(candidate, ffmpeg='fake', ffprobe='fake')
    assert report['status'] == 'FAILED'
    assert len(report['jobs']) == 1


def test_input_changes_during_decode_invalidate_report(tmp_path, monkeypatch):
    candidate, _ = candidate_fixture(tmp_path)

    def mutate_after_decode(command, log, timeout):
        result = fake_tools(command, log, timeout)
        if '-show_frames' not in command:
            (candidate / 'scene.blend').write_bytes(b'concurrently replaced')
        return result

    monkeypatch.setattr(media, 'bounded', mutate_after_decode)
    _, report = media.verify_media(candidate, ffmpeg='fake', ffprobe='fake')
    assert report['status'] == 'FAILED'
    assert report['checks']['immutable_inputs']['status'] == 'FAILED'


def test_missing_recoverable_frame_fails_and_unsafe_paths_rejected(tmp_path):
    candidate, directory = candidate_fixture(tmp_path)
    (directory / 'frame_000002.png').unlink()
    _, report = media.verify_media(candidate)
    assert report['status'] == 'FAILED'
    assert 'recoverable PNG' in ' '.join(report['checks']['input_integrity']['issues'])
    for kwargs in [{'camera': '../other'}, {'report_name': '../other.json'}, {'timeout': 1801}]:
        with pytest.raises(ValueError):
            media.verify_media(candidate, **kwargs)
