"""Verify a browser export and mux the matched video; never create approval."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import wave

from modules.blender.batch import bounded
from modules.blender.selection import selected_bundle, staged_bundle


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_export(report_path, video_path):
    report = json.loads(report_path.read_text())
    if report.get('version') not in ('performance-export-2','performance-export-3'):
        raise ValueError('unsupported_export_version')
    production_selection=False
    if report.get('selection'):
        selection=report['selection']
        source=Path(selection['selection_file'])
        if sha(source)!=selection['selection_sha256']:
            raise ValueError('stale_export_selection')
        record=json.loads(source.read_text())
        production_selection=record.get('version') in ('blender-staged-candidate-1','blender-accepted-candidate-1')
        bundle,_=(staged_bundle(source) if record.get('version')=='blender-staged-candidate-1'
                  else selected_bundle(selection['variant'],source))
        if sha(bundle/'preview.mp4')!=sha(video_path):
            raise ValueError('export_video_not_selected')
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
    lead='piano'
    if report['version']=='performance-export-3':
        design=report['sound_design']
        raw=report['sound_design_bytes'].encode()
        design_hash=hashlib.sha256(raw).hexdigest()
        plan=json.loads(report['plan_bytes'])
        content=report['sound_design_event_bytes'].encode()
        source=json.loads(report['source_events_bytes'])
        if (json.loads(raw)!=design or design_hash!=report['sound_design_sha256']
                or plan['provenance']['config_hash']!=design_hash
                or design_hash not in plan['provenance']['input_hashes']
                or design['version']!='collision-riffs-1' or design['voice_version']!='collision-riff-voices-1'
                or design['lead'] not in ('guitar','vibraphone') or report.get('final_fade_s')!=.01
                or hashlib.sha256(content).hexdigest()!=design['events_content_sha256']
                or json.loads(content)!=[{k:v for k,v in e.items() if k!='plan_id'} for e in source]):
            raise ValueError('unbound_riff_export')
        lead=design['lead']
        if report['stem_layout']!=[lead,'bass','brush','foley']:
            raise ValueError('riff_stem_layout_mismatch')
    if len(report['files']) != 5 or {f['stem'] for f in report['files']} != {'mix', lead, 'bass', 'brush', 'foley'}:
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
    policy,window=report.get('playback_policy'),report.get('playback_window')
    if bool(policy)!=bool(window) or (production_selection and not window):
        raise ValueError('playback_policy_window_required')
    if window:
        expected_policy={k:window[k] for k in ('version','start_s','duration_s','render_fps','final_fade_s')}
        if policy!=expected_policy:
            raise ValueError('playback_policy_window_mismatch')
        scene_raw=report['scene_input_bytes'].encode()
        scene_inputs=json.loads(scene_raw)
        if (sha256_bytes(scene_raw)!=report['scene_hash'] or scene_inputs.get('playback_policy')!=policy
                or scene_inputs.get('role_supplement')!=report.get('role_supplement')
                or scene_inputs.get('music_handoff_binding')!=report.get('music_handoff_binding')):
            raise ValueError('unbound_export_scene_inputs')
        raw=report['playback_window_bytes'].encode()
        original=report['source_events_bytes'].encode()
        if (sha256_bytes(raw)!=report['playback_window_sha256'] or json.loads(raw)!=window
                or sha256_bytes(original)!=window['original_events_sha256']):
            raise ValueError('stale_playback_window')
        from modules.blender.production.playback import create_playback_window
        expected,_=create_playback_window(original,report['duration_s'])
        if window!=expected or rate!=48000 or frames!=window['frame_count']*1600:
            raise ValueError('playback_window_audio_contract')
    return report, mix


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('video', type=Path,nargs='?')
    selection_args=parser.add_mutually_exclusive_group()
    selection_args.add_argument('--selection',type=Path)
    selection_args.add_argument('--review-selection',type=Path)
    parser.add_argument('--variant',default='hero')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.selection or args.review_selection:
        bundle,_=(staged_bundle(args.review_selection) if args.review_selection else selected_bundle(args.variant,args.selection))
        selected_video=bundle/'preview.mp4'
        if args.video and sha(args.video)!=sha(selected_video):
            parser.error('explicit video differs from selection')
        args.video=selected_video
    if args.video is None:
        parser.error('provide an exact selection or video')
    report, mix = verify_export(args.report, args.video)
    if args.out.exists() or args.out.with_suffix('.mux.json').exists():
        raise FileExistsError('preserve_existing_mux')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    jobs=[]
    def run(command,name):
        log=args.out.with_suffix('.'+name+'.log')
        job=bounded(command,log,timeout=90)
        jobs.append({'log':str(log),'log_sha256':sha(log),**job})
        if job['status']!='passed' or not job['process_group_absent']:
            raise ValueError('mux_tool_failed:'+name)
        return log.read_text()
    encoder = shutil.which('ffmpeg')
    if not encoder:
        raise SystemExit('MUX_NOT_RUN: keep the verified separate audio/video bundle; ffmpeg unavailable')
    probe = json.loads(run(['ffprobe', '-v', 'error', '-threads','2','-show_streams', '-of', 'json', str(args.video)],'source-probe'))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    if abs(float(video.get('start_time', 0))) > .001 or abs(float(video['duration']) - report['duration_s']) > .001:
        raise ValueError('video_duration_or_timestamp_offset')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    run([encoder, '-nostdin', '-n', '-v', 'error','-threads','2', '-i', str(args.video), '-i', str(mix),
                    '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-t', str(report['duration_s']), '-movflags', '+faststart', str(args.out)],'encode')
    metadata = json.loads(run(['ffprobe', '-v', 'error','-threads','2', '-show_streams', '-show_format', '-of', 'json', str(args.out)],'mux-probe'))
    result = {'status': report['status'], 'audition_status': 'AUDITION_PENDING', 'mux_sha256': sha(args.out),
              'source_report_sha256': sha(args.report),'jobs':jobs,'approval':report['approval'],
              'selection':report.get('selection'),'playback_window_sha256':report.get('playback_window_sha256'), 'audio_encoding': 'AAC transcode; original lossless WAV retained',
              'timestamp_offset_s': 0, 'duration_s': report['duration_s'], 'probe': metadata}
    args.out.with_suffix('.mux.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'probe'}, indent=2))


if __name__ == '__main__':
    main()
