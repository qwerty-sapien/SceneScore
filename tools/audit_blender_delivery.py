"""Audit exact staged browser exports, sample alignment and contact-frame mapping."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import wave

from modules.blender.selection import staged_bundle
from tools.mux_performance import verify_export


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(selection, reports):
    candidate, binding = staged_bundle(selection)
    handoff = json.loads((candidate / 'handoff.json').read_text())
    result = {'version': 'blender-delivery-audit-1', 'selection': binding,
              'approval': None, 'exports': [], 'marker_frames': [],
              'scope': 'Byte, clock, PCM and declared contact correspondence. No auditory or continuous-motion perception.'}
    bundle_ids=set()
    for report_path in reports:
        report, _ = verify_export(report_path, candidate / 'preview.mp4')
        if report['bundle_id'] in bundle_ids:
            raise ValueError('duplicate_export_bundle_identity')
        bundle_ids.add(report['bundle_id'])
        if report['selection'] != binding:
            raise ValueError('different_export_selection')
        pcm, dimensions = {}, {}
        for item in report['files']:
            with wave.open(str(report_path.parent / item['filename'])) as stream:
                dimensions[item['stem']] = [stream.getnchannels(), stream.getsampwidth(),
                                            stream.getframerate(), stream.getnframes()]
                pcm[item['stem']] = array.array('h', stream.readframes(stream.getnframes()))
        errors = [mix-piano-bass-brush-foley for mix, piano, bass, brush, foley in
                  zip(pcm['mix'], pcm['piano'], pcm['bass'], pcm['brush'], pcm['foley'])]
        max_error = max(map(abs, errors))
        if max_error > 2 or any(abs(v) > 1 for samples in pcm.values() for v in samples[-2:]):
            raise ValueError('stem_sum_or_final_sample')
        contacts = [m for m in handoff['markers'] if m['type'] == 'contact' and m['status'] == 'VALIDATED']
        foley = [e for e in report['events'] if e['event_type'] == 'foley']
        if len(foley) != len(contacts) or any(sum(abs(e['resolved_time_s']-m['time_s']) < 1e-10
                                               for m in contacts) != 1 for e in foley):
            raise ValueError('foley_not_exact_certified_contacts')
        source_events = json.loads(report['source_events_bytes'])
        if report['events'] != source_events:
            raise ValueError('this_unmodified_draft_must_preserve_source_events')
        result['exports'].append({'report': str(report_path), 'sha256': sha(report_path),
                                  'dimensions': dimensions, 'max_stem_sum_error_lsb': max_error,
                                  'rms_stem_sum_error_lsb': math.sqrt(sum(v*v for v in errors)/len(errors)),
                                  'final_samples_lsb': {k: list(v[-2:]) for k, v in pcm.items()},
                                  'original_events': len(source_events), 'certified_foley_events': len(foley),
                                  'window_events': len(report['playback_window']['projections']),
                                  'files': report['files']})
    duration = handoff['clock']['duration_s']
    for marker in handoff['markers']:
        if marker['status'] != 'VALIDATED' or not 0 <= marker['time_s'] < duration:
            continue
        frame = math.floor(marker['time_s']*30)+1
        path = candidate / 'renders/preview/beauty' / f'frame_{frame:06d}.png'
        # A frame contains an interval; an inferred subframe contact is not a photographed impulse.
        result['marker_frames'].append({'id': marker['id'], 'type': marker['type'],
                                        'time_s': marker['time_s'], 'uncertainty_s': marker['uncertainty_s'],
                                        'confirmation_time_s': marker['confirmation_time_s'],
                                        'frame': frame, 'frame_interval_s': [(frame-1)/30, frame/30],
                                        'nearest_audio_sample': round(marker['time_s']*48000),
                                        'image': str(path), 'image_sha256': sha(path)})
    result['status'] = 'PASSED'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('preserve_prior_delivery_audit')
    result = audit(args.selection, args.report)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'exports': len(result['exports']),
                      'marker_frames': len(result['marker_frames']), 'out': str(args.out)}))


if __name__ == '__main__':
    main()
