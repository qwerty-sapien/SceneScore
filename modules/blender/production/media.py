"""Hash-bound full-decode media checks. No physics or visual-perception verdicts.

Run ``python -m modules.blender.production.media CANDIDATE --profile diagnostic``.
Each run keeps its tool output and process cleanup records; existing reports are
never overwritten. Exact repeated pixels during >2 cm/frame world translation
are flagged. That proxy does not establish screen visibility or detect rotation.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import uuid

from modules.blender.batch import bounded
from modules.blender.executables import resolve_executable


VERSION = 'scene-production-media-validation-1'
FPS = 30
MOTION_THRESHOLD_M = .02
PTS_TOLERANCE_S = .0001
PROFILES = {'diagnostic': (640, 360), 'preview': (640, 360), 'final': (1920, 1080)}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _gate(issues, **data):
    return {'status': 'FAILED' if issues else 'PASSED', 'issues': issues, **data}


def _number(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('nonfinite number')
    return number


def inspect_probe(probe, expected_frames, expected_duration, dimensions):
    """Inspect every presentation timestamp, not container-rate assertions alone."""
    issues = []
    streams = probe.get('streams', [])
    frames = probe.get('frames', [])
    pts = []
    if len(streams) != 1:
        issues.append('expected exactly one selected video stream')
    stream = streams[0] if streams else {}
    if (stream.get('width'), stream.get('height')) != tuple(dimensions):
        issues.append('video resolution differs from production profile')
    for key in ('avg_frame_rate', 'r_frame_rate'):
        try:
            if Fraction(stream[key]) != FPS:
                issues.append(f'{key} is not native 30 fps')
        except (KeyError, ValueError, ZeroDivisionError, TypeError):
            issues.append(f'{key} missing or invalid')
    try:
        duration = _number(stream['duration'])
        if abs(duration - expected_duration) > PTS_TOLERANCE_S:
            issues.append('video stream duration differs from authoritative animation duration')
    except (KeyError, ValueError, TypeError):
        duration = None
        issues.append('video stream duration unavailable')
    for index, frame in enumerate(frames):
        try:
            # Original presentation timestamps, no synthesized best-effort fallback.
            timestamp = _number(frame['pts_time'])
            pts.append(timestamp)
            if abs(timestamp - index / FPS) > PTS_TOLERANCE_S:
                issues.append(f'frame {index} presentation timestamp is not index/30')
        except (KeyError, ValueError, TypeError):
            pts.append(None)
            issues.append(f'frame {index} original presentation timestamp unavailable')
    if len(frames) != expected_frames:
        issues.append('full FFprobe frame count differs from authoritative frame count')
    return _gate(issues, frame_count=len(frames), expected_frames=expected_frames,
                 fps=FPS, width=stream.get('width'), height=stream.get('height'),
                 duration_s=duration, pts_s=pts, tolerance_s=PTS_TOLERANCE_S,
                 stream=stream)


def parse_framehash(text):
    """Parse FFmpeg SHA256 checksums of complete decoded raw video frames."""
    rows = []
    time_base = None
    for line in text.splitlines():
        if line.startswith('#tb 0:'):
            time_base = Fraction(line.split(':', 1)[1].strip())
        if not line.strip() or line.startswith('#'):
            continue
        fields = [item.strip() for item in line.split(',')]
        if len(fields) != 6 or not re.fullmatch(r'[0-9a-fA-F]{64}', fields[-1]):
            raise ValueError('unexpected FFmpeg framehash output')
        stream, dts, pts, duration, size = map(int, fields[:5])
        if stream != 0 or duration <= 0 or size <= 0:
            raise ValueError('invalid decoded frame record')
        rows.append({'pts': pts, 'duration': duration, 'size_bytes': size,
                     'sha256': fields[5].lower()})
    if time_base is None or time_base <= 0:
        raise ValueError('decoded frame time base missing')
    for row in rows:
        row['pts_s'] = float(row['pts'] * time_base)
        row['duration_s'] = float(row['duration'] * time_base)
    return rows


def motion_frames(samples, object_ids, hz, frame_count):
    """Declare frame transitions from the exact SI state clock, failing on gaps."""
    if hz < FPS or hz % FPS:
        raise ValueError('physics Hz must be an integer multiple of 30')
    by_tick = {}
    for row in samples:
        tick = row['tick']
        if not isinstance(tick, int) or isinstance(tick, bool) or tick in by_tick:
            raise ValueError('invalid or duplicate physics tick')
        if abs(_number(row['time_s']) - tick / hz) > 1e-8:
            raise ValueError('physics time differs from integer tick clock')
        by_tick[tick] = row
    end_tick = frame_count * (hz // FPS)
    if set(by_tick) != set(range(end_tick + 1)):
        raise ValueError('physics states must contain complete inclusive source tick grid')
    if not object_ids or len(set(object_ids)) != len(object_ids):
        raise ValueError('source object identities missing or duplicated')
    positions = []
    for frame in range(frame_count):
        row = by_tick[frame * (hz // FPS)]
        current = {}
        for object_id in object_ids:
            vector = row['objects'][object_id]['position_m']
            if len(vector) != 3:
                raise ValueError('invalid source position')
            current[object_id] = tuple(_number(v) for v in vector)
        positions.append(current)
    moving = []
    for frame in range(1, frame_count):
        moved = {oid: math.dist(positions[frame - 1][oid], positions[frame][oid])
                 for oid in object_ids}
        significant = {oid: distance for oid, distance in moved.items() if distance > MOTION_THRESHOLD_M}
        if significant:
            moving.append({'frame_index': frame, 'time_s': frame / FPS,
                           'objects_displacement_m': significant})
    return moving


def inspect_decode(rows, expected_frames, moving, png_hashes):
    issues = []
    if len(rows) != expected_frames:
        issues.append('full decoded frame count differs from authoritative frame count')
    for index, row in enumerate(rows):
        if abs(row['pts_s'] - index / FPS) > PTS_TOLERANCE_S:
            issues.append(f'decoded frame {index} timestamp differs from native clock')
        if abs(row['duration_s'] - 1 / FPS) > PTS_TOLERANCE_S:
            issues.append(f'decoded frame {index} duration differs from native cadence')
    decoded_duplicates = [i for i in range(1, len(rows)) if rows[i]['sha256'] == rows[i - 1]['sha256']]
    png_duplicates = [i for i in range(1, len(png_hashes)) if png_hashes[i] == png_hashes[i - 1]]
    expected_motion = {record['frame_index'] for record in moving}
    rejected = sorted((set(decoded_duplicates) | set(png_duplicates)) & expected_motion)
    if rejected:
        issues.append('exact repeated frame during declared source translation')
    return _gate(issues, actual_frames_decoded=len(rows),
                 decoded_distinct_full_frame_hashes=len({row['sha256'] for row in rows}),
                 decoded_duplicate_transitions=decoded_duplicates,
                 png_duplicate_transitions=png_duplicates,
                 duplicate_moving_transitions=rejected,
                 moving_transition_count=len(moving), moving_transitions=moving,
                 world_translation_threshold_m=MOTION_THRESHOLD_M,
                 decoded_frames=rows,
                 scope='Full raw decoded pixel hashes and full PNG file hashes; no perceptual comparison.',
                 limitations=['World translation is a motion proxy; visibility, occlusion and rotation are not assessed.',
                              'Lossy encoding can change pixels on visually repeated frames; PNG hashes also checked.',
                              'Nonidentical frames can still be temporally or visually wrong.'])


def verify_media(candidate, profile='diagnostic', camera='beauty', *, timeout=180,
                 ffmpeg=None, ffprobe=None, report_name='media-validation.json'):
    """Write one immutable report and unique bounded-job evidence directory."""
    if profile not in PROFILES or not re.fullmatch(r'[A-Za-z0-9_-]+', camera):
        raise ValueError('invalid profile or camera')
    if not re.fullmatch(r'[A-Za-z0-9_-]+\.json', report_name):
        raise ValueError('report name must be a plain JSON basename')
    if not 0 < timeout <= 1800:
        raise ValueError('each tool timeout must be in (0, 1800] seconds')
    candidate = Path(candidate).resolve()
    directory = candidate / 'renders' / profile / camera
    report_path = directory / report_name
    if report_path.exists():
        raise FileExistsError(f'preserving existing report: {report_path}; choose --report-name')
    directory.mkdir(parents=True, exist_ok=True)
    run_dir = directory / ('media-check-' + uuid.uuid4().hex)
    run_dir.mkdir()
    report = {'media_validation_version': VERSION, 'created_at': datetime.now(timezone.utc).isoformat(),
              'status': 'FAILED', 'candidate': str(candidate), 'profile': profile, 'camera': camera,
              'approval': None, 'checks': {}, 'inputs': {}, 'jobs': [],
              'verifier_code_sha256': sha256(__file__), 'bounded_runner_sha256': sha256(Path(bounded.__code__.co_filename)),
              'physics_validation': 'NOT_ASSESSED', 'visual_quality': 'NOT_ASSESSED',
              'continuous_motion_perception': 'NOT_ASSESSED', 'audio_timing': 'NOT_ASSESSED',
              'run_directory': str(run_dir)}
    paths = {'production.json': candidate / 'production.json', 'scene.blend': candidate / 'scene.blend',
             'physics_states.jsonl': candidate / 'physics_states.jsonl', 'render.json': directory / 'render.json',
             'video.mp4': directory / 'video.mp4'}
    try:
        for name, path in paths.items():
            report['inputs'][name] = {'path': str(path), 'sha256': sha256(path), 'size_bytes': path.stat().st_size}
        production = json.loads(paths['production.json'].read_text())
        render = json.loads(paths['render.json'].read_text())
        duration = _number(production['duration_s'])
        if not 0 < duration <= 60 or abs(duration * FPS - round(duration * FPS)) > 1e-8:
            raise ValueError('production duration must be frame aligned and in (0, 60] seconds')
        count = round(duration * FPS)
        width, height = PROFILES[profile]
        issues = []
        for key, expected in {'profile': profile, 'camera': camera, 'fps': FPS, 'frame_count': count,
                              'width': width, 'height': height, 'returncode': 0}.items():
            if render.get(key) != expected:
                issues.append(f'render.json {key} differs from expected {expected!r}')
        if production.get('render_fps') != FPS:
            issues.append('production render_fps is not 30')
        for field, name in [('source_hash', 'scene.blend'), ('states_hash', 'physics_states.jsonl'),
                            ('video_hash', 'video.mp4')]:
            if render.get(field) != report['inputs'][name]['sha256']:
                issues.append(f'render.json {field} does not match actual {name}')
        lineage = production.get('lineage', {})
        if lineage.get('artifacts', {}).get('scene.blend') != report['inputs']['scene.blend']['sha256']:
            issues.append('production lineage does not bind actual scene.blend')
        if lineage.get('states_sha256') != report['inputs']['physics_states.jsonl']['sha256']:
            issues.append('production lineage does not bind actual states')
        frames = [directory / f'frame_{i:06d}.png' for i in range(1, count + 1)]
        if set(directory.glob('frame_*.png')) != set(frames):
            issues.append('recoverable PNG sequence is missing frames or contains unexpected frames')
        png_hashes = []
        for path in frames:
            if not path.is_file():
                continue
            digest = sha256(path)
            png_hashes.append(digest)
            report['inputs'][path.name] = {'path': str(path), 'sha256': digest, 'size_bytes': path.stat().st_size}
            paths[path.name] = path
        report['render_provenance'] = {'encoding_command': render.get('command'),
                                       'recorded_renderer_code_hashes': render.get('renderer_code_hashes'),
                                       'scope': 'Historical recorded renderer hashes; not asserted equal to current code.'}
        report['expected'] = {'duration_s': duration, 'frame_count': count, 'fps': FPS,
                              'width': width, 'height': height, 'audio_sample_rate_hz': 48000,
                              'audio_samples_per_video_frame': 1600, 'audio_alignment_measured': False}
        report['checks']['input_integrity'] = _gate(issues)
        if issues:
            raise ValueError('input integrity failed; no media pass may be promoted')
        samples = [json.loads(line) for line in paths['physics_states.jsonl'].read_text().splitlines() if line.strip()]
        ids = [item['object_id'] for item in production['objects']]
        moving = motion_frames(samples, ids, production['physics_hz'], count)
        report['checks']['source_motion_clock'] = _gate([], moving_transition_count=len(moving))
        ffprobe = resolve_executable('ffprobe', ffprobe)
        ffmpeg = resolve_executable('ffmpeg', ffmpeg)
        probe_command = [str(ffprobe), '-v', 'error', '-threads', '2', '-select_streams', 'v:0',
                         '-show_program_version', '-show_streams', '-show_frames',
                         '-show_entries', 'frame=pts_time,duration_time:stream=width,height,avg_frame_rate,r_frame_rate,duration,codec_name,time_base,nb_frames',
                         '-of', 'json', str(paths['video.mp4'])]
        probe_log = run_dir / 'ffprobe.log'
        job = bounded(probe_command, probe_log, timeout)
        report['jobs'].append({'operation': 'full_frame_probe', 'log': str(probe_log), **job})
        if job['status'] != 'passed' or not job['process_group_absent']:
            raise ValueError('bounded full FFprobe failed')
        probe = json.loads(probe_log.read_text())
        report['ffprobe_version'] = probe.get('program_version')
        report['checks']['presentation_timing'] = inspect_probe(probe, count, duration, (width, height))
        decode_command = [str(ffmpeg), '-v', 'error', '-nostdin', '-threads', '2', '-copyts',
                          '-i', str(paths['video.mp4']), '-map', '0:v:0', '-an', '-sn', '-dn',
                          '-fps_mode', 'passthrough', '-threads', '2', '-f', 'framehash', '-hash', 'sha256', '-']
        decode_log = run_dir / 'decode-framehash.log'
        job = bounded(decode_command, decode_log, timeout)
        report['jobs'].append({'operation': 'full_decode_framehash', 'log': str(decode_log), **job})
        if job['status'] != 'passed' or not job['process_group_absent']:
            raise ValueError('bounded full FFmpeg decode failed')
        rows = parse_framehash(decode_log.read_text())
        report['checks']['full_decode_and_motion_duplicates'] = inspect_decode(rows, count, moving, png_hashes)
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        report['error'] = f'{type(error).__name__}: {error}'
    finally:
        changed = []
        for name, record in report['inputs'].items():
            try:
                if sha256(record['path']) != record['sha256']:
                    changed.append(f'{name} changed during verification')
            except OSError:
                changed.append(f'{name} unavailable after verification')
        report['checks']['immutable_inputs'] = _gate(changed)
        for job in report['jobs']:
            path = Path(job['log'])
            if path.exists():
                job['log_sha256'] = sha256(path)
            evidence = path.with_suffix('.job.json')
            if evidence.exists():
                job['process_evidence_path'] = str(evidence)
                job['process_evidence_sha256'] = sha256(evidence)
        required = {'input_integrity', 'source_motion_clock', 'presentation_timing',
                    'full_decode_and_motion_duplicates', 'immutable_inputs'}
        if (not report.get('error') and required <= report['checks'].keys()
                and all(check['status'] == 'PASSED' for check in report['checks'].values())):
            report['status'] = 'PASSED'
        with report_path.open('x') as handle:
            json.dump(report, handle, indent=2, allow_nan=False)
            handle.write('\n')
    return report_path, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--profile', choices=PROFILES, default='diagnostic')
    parser.add_argument('--camera', default='beauty')
    parser.add_argument('--timeout', type=float, default=180, help='per-tool limit, maximum 1800 seconds')
    parser.add_argument('--ffmpeg')
    parser.add_argument('--ffprobe')
    parser.add_argument('--report-name', default='media-validation.json', help='existing reports are preserved')
    args = parser.parse_args(argv)
    path, report = verify_media(**vars(args))
    print(json.dumps({'status': report['status'], 'report': str(path), 'sha256': sha256(path)}))
    return 0 if report['status'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
