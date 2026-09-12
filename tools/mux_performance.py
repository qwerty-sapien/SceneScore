"""Verify a browser export and mux the matched video; never create approval."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_export(report_path, video_path):
    report = json.loads(report_path.read_text())
    if report.get('version') != 'performance-export-2':
        raise ValueError('unsupported_export_version')
    if sha(video_path) != report['video_sha256']:
        raise ValueError('stale_video_hash')
    if report['status'] == 'DRAFT_NOT_APPROVED':
        if report['approval'] is not None:
            raise ValueError('draft_must_not_claim_approval')
    elif report['status'] == 'APPROVED_PERFORMANCE':
        # Reuse exact canonical approval validation, including its original bytes.
        from scenescore.contracts import validate
        approval = validate(report['approval'])
        if approval['decision'] != 'approved':
            raise ValueError('approval_required')
        if hashlib.sha256(report['plan_bytes'].encode()).hexdigest() != approval['approved_payload_sha256']:
            raise ValueError('approval_payload_hash_mismatch')
        plan = validate(json.loads(report['plan_bytes']))
        if approval['plan_id'] != plan['id'] or approval['input_hashes'] != [report['scene_hash'], report['composition_hash']]:
            raise ValueError('approval_input_mismatch')
        if plan['scene_hash'] != report['scene_hash'] or plan['composition_hash'] != report['composition_hash']:
            raise ValueError('plan_inputs_mismatch')
    else:
        raise ValueError('unknown_export_status')
    if hashlib.sha256(report['event_bytes'].encode()).hexdigest() != report['event_hash'] or json.loads(report['event_bytes']) != report['events']:
        raise ValueError('event_log_hash_mismatch')
    if len(report['files']) != 5 or {f['stem'] for f in report['files']} != {'mix', 'piano', 'bass', 'brush', 'foley'}:
        raise ValueError('five_aligned_outputs_required')
    dimensions = set()
    mix = None
    for item in report['files']:
        if Path(item['filename']).name != item['filename']:
            raise ValueError('local_filename_required')
        path = report_path.parent / item['filename']
        if sha(path) != item['sha256']:
            raise ValueError('audio_hash_mismatch')
        with wave.open(str(path)) as audio:
            dimensions.add((audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()))
        if item['stem'] == 'mix':
            mix = path
    if len(dimensions) != 1:
        raise ValueError('unaligned_stems')
    channels, width, rate, frames = dimensions.pop()
    if channels != 2 or width != 2 or abs(frames / rate - report['duration_s']) > 1 / rate:
        raise ValueError('export_audio_contract')
    return report, mix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('video', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report, mix = verify_export(args.report, args.video)
    encoder = shutil.which('ffmpeg')
    if not encoder:
        raise SystemExit('MUX_NOT_RUN: keep the verified separate audio/video bundle; ffmpeg unavailable')
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(args.video)]))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    if abs(float(video.get('start_time', 0))) > .001 or abs(float(video['duration']) - report['duration_s']) > .001:
        raise ValueError('video_duration_or_timestamp_offset')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([encoder, '-nostdin', '-n', '-v', 'error', '-i', str(args.video), '-i', str(mix),
                    '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-t', str(report['duration_s']), '-movflags', '+faststart', str(args.out)], check=True, timeout=90)
    metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(args.out)]))
    result = {'status': report['status'], 'audition_status': 'AUDITION_PENDING', 'mux_sha256': sha(args.out),
              'source_report_sha256': sha(args.report), 'audio_encoding': 'AAC transcode; original lossless WAV retained',
              'timestamp_offset_s': 0, 'duration_s': report['duration_s'], 'probe': metadata}
    args.out.with_suffix('.mux.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'probe'}, indent=2))


if __name__ == '__main__':
    main()
