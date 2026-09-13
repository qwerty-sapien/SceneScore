"""Prepare and verify the three explicitly scoped animation mechanics studies."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.blender.batch import bounded  # noqa: E402
from modules.blender.production.common import digest, dump, read  # noqa: E402

ARTIFACT_ROOT = ROOT / 'artifacts/blender/revamp/directions'
BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
FFMPEG = '/opt/homebrew/bin/ffmpeg'
FFPROBE = '/opt/homebrew/bin/ffprobe'
DRIVER = ROOT / 'modules/blender/production/directions/driver.py'


def check_packet(packet):
    """Fail malformed or non-rigid body output independently of backend assertions."""
    json.dumps(packet, allow_nan=False)
    assert packet['duration_s'] == 30 and packet['hz'] == 240
    actors = {a['id']: a for a in packet['actors']}
    ids = [s['id'] for s in packet['actors'] + packet['geometry']]
    assert len(ids) == len(set(ids)), 'Duplicate object identity'
    samples = packet['states']
    assert len(samples) == 7201
    max_quaternion_error = 0.
    for tick, sample in enumerate(samples):
        assert sample['tick'] == tick and abs(sample['time_s'] - tick / 240) < 1e-10
        assert set(sample['objects']) == set(actors)
        for oid, pose in sample['objects'].items():
            assert len(pose['position_m']) == len(pose['velocity_m_s']) == 3
            quat = pose['quaternion_xyzw']
            assert len(quat) == 4
            error = abs(sum(x*x for x in quat) - 1)
            max_quaternion_error = max(max_quaternion_error, error)
            assert error < 1e-8
            scale = pose.get('scale', [1, 1, 1])
            assert len(scale) == 3 and all(x > 0 for x in scale)
            assert actors[oid].get('deformable', False) or scale == [1, 1, 1], oid + ' changes rigid size'
    for spec in packet['actors'] + packet['geometry']:
        if spec['shape'] == 'mesh':
            vertices = spec['vertices']
            assert vertices and spec['faces']
            assert all(len(v) == 3 for v in vertices)
            assert all(len(face) >= 3 and all(0 <= i < len(vertices) for i in face) for face in spec['faces'])
        if 'radius_m' in spec:
            assert spec['radius_m'] > 0
    return dict(status='PASSED', samples=7201, actors=len(actors), rigid_scales_constant=True,
                max_quaternion_norm_squared_error=max_quaternion_error,
                scope='packet identity, finiteness, dimensions, clock, quaternion and declared rigid-scale integrity')


def prepare(out, direction):
    if out.exists():
        raise ValueError('Use a new candidate directory; existing evidence is immutable')
    if direction in ('06', '08'):
        from modules.blender.production.directions.rolling import build_direction
        backend = 'rolling.py'
    else:
        from modules.blender.production.directions.puck import build_direction
        backend = 'puck.py'
    packet = build_direction(direction, hz=240, substeps=8)
    integrity = check_packet(packet)
    out.mkdir(parents=True)
    samples = packet.pop('states')
    with (out / 'mechanics_states.jsonl').open('w') as stream:
        for sample in samples:
            stream.write(json.dumps(sample, separators=(',', ':'), allow_nan=False) + '\n')
    dump(out / 'packet.json', packet)
    dump(out / 'packet_validation.json', integrity)
    paths = [DRIVER, Path(__file__),
             ROOT / ('modules/blender/production/directions/' + backend),
             ROOT / 'modules/blender/production/directions/__init__.py',
             ROOT / 'modules/blender/production/common.py', ROOT / 'modules/blender/production/driver.py',
             ROOT / 'modules/blender/batch.py', ROOT / 'modules/blender/geometry.py']
    source = {}
    for path in paths:
        relative = path.resolve().relative_to(ROOT)
        target = out / 'generation_source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        source[str(relative)] = digest(target)
    dump(out / 'provenance.json', dict(direction=direction, source_hashes=source,
        input_hashes={name: digest(out / name) for name in ('packet.json', 'mechanics_states.jsonl')},
        reference_video='artifacts/blender/revamp/analytic/05_bouncing_staircase-32/renders/diagnostic/beauty/video.mp4',
        reference_sha256=digest(ROOT / 'artifacts/blender/revamp/analytic/05_bouncing_staircase-32/renders/diagnostic/beauty/video.mp4'),
        approval=None))
    print(json.dumps(dict(out=str(out), validation=packet['validation']), indent=2))


def verify_inputs(out):
    provenance = read(out / 'provenance.json')
    for name, expected in provenance['source_hashes'].items():
        assert digest(ROOT / name) == expected, 'Source changed; create a new candidate: ' + name
        assert digest(out / 'generation_source' / name) == expected
    for name, expected in provenance['input_hashes'].items():
        assert digest(out / name) == expected, 'Computed input changed: ' + name


def job(out, stage, command, timeout):
    verify_inputs(out)
    log = out / 'jobs' / (stage + '.log')
    if log.exists():
        raise ValueError('Preserve prior job evidence; use a distinct stage suffix or new candidate')
    with Path('/private/tmp/scenescore-direction-render.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        used = sum(read(p).get('duration_s', 0) for p in ARTIFACT_ROOT.rglob('*.job.json'))
        if used + timeout > 4 * 3600:
            raise RuntimeError('Four-hour task budget would be exceeded')
        if shutil.disk_usage(out).free < 3 * 1024 ** 3:
            raise RuntimeError('Less than 3 GiB free')
        size = sum(p.stat().st_size for p in ARTIFACT_ROOT.rglob('*') if p.is_file())
        if size > 20 * 1024 ** 3:
            raise RuntimeError('20 GiB artifact budget exceeded')
        result = bounded(command, log, timeout)
    print(json.dumps(result, indent=2), flush=True)
    if result['status'] != 'passed' or not result['process_group_absent']:
        raise RuntimeError('Bounded stage failed: ' + str(log))
    return result


def media(out):
    video = out / 'renders/video.mp4'
    job(out, 'media-probe', [FFPROBE, '-v', 'error', '-count_frames', '-show_streams', '-show_format',
         '-show_frames', '-show_entries',
         'stream=codec_type,width,height,r_frame_rate,nb_read_frames,duration:format=duration:frame=best_effort_timestamp_time',
         '-of', 'json', str(video)], 180)
    result = read(out / 'jobs/media-probe.log')
    stream = next(s for s in result['streams'] if s['codec_type'] == 'video')
    timestamps = [float(f['best_effort_timestamp_time']) for f in result['frames']]
    assert len(timestamps) == int(stream['nb_read_frames']) == 900
    assert stream['r_frame_rate'] == '30/1'
    assert abs(float(result['format']['duration']) - 30) < 1e-6
    error = max(abs(t - i / 30) for i, t in enumerate(timestamps))
    assert error < 1e-6
    job(out, 'media-decode', [FFMPEG, '-v', 'error', '-nostdin', '-threads', '2', '-i', str(video), '-f', 'null', '-'], 180)
    dump(out / 'media_validation.json', dict(status='PASSED', frames=900, fps=30, duration_s=30,
        width=stream['width'], height=stream['height'], max_pts_error_s=error,
        full_decode=True, video_sha256=digest(video), scene_sha256=digest(out / 'scene.blend'),
        approval=None, perceptual_acceptance='pending human review'))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['prepare', 'build', 'replay', 'verify', 'stills', 'render', 'encode', 'media'])
    parser.add_argument('--direction', choices=['06', '08', '18'])
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--width', type=int, default=960, choices=[640, 960, 1280, 1920])
    parser.add_argument('--first', type=int, default=1)
    parser.add_argument('--last', type=int, default=900)
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out != ARTIFACT_ROOT and out.is_relative_to(ARTIFACT_ROOT)
    assert 1 <= args.timeout <= 1800 and 1 <= args.first <= args.last <= 900
    if args.stage == 'prepare':
        if not args.direction:
            parser.error('--direction is required for prepare')
        prepare(out, args.direction)
    elif args.stage == 'media':
        media(out)
    elif args.stage == 'encode':
        frames = list((out / 'renders').glob('frame_*.png'))
        assert len(frames) == 900
        assert all((out / f'renders/frame_{i:06d}.png').is_file() for i in range(1, 901))
        job(out, 'encode', [FFMPEG, '-v', 'error', '-nostdin', '-n', '-framerate', '30',
            '-start_number', '1', '-i', str(out / 'renders/frame_%06d.png'), '-frames:v', '900',
            '-c:v', 'libx264', '-threads', '2', '-crf', '18', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(out / 'renders/video.mp4')], 180)
    else:
        if args.stage in ('stills', 'render'):
            assert read(out / 'replay_validation.json')['status'] == 'PASSED'
        suffix = f'-{args.first:04d}-{args.last:04d}' if args.stage == 'render' else ''
        command = [BLENDER, '--background', '--factory-startup', '--python-exit-code', '1', '--threads', '2',
            '--python', str(DRIVER), '--', args.stage, '--out', str(out), '--width', str(args.width),
            '--first', str(args.first), '--last', str(args.last)]
        job(out, args.stage + suffix, command, args.timeout)


if __name__ == '__main__':
    main()
