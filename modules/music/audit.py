"""Read actual exported PCM and canonical records; produce objective evidence, never an audition score."""
import argparse
import hashlib
import json
from pathlib import Path

from scenescore.contracts import validate
from .catalog import VARIATIONS, list_catalog, payload_bytes
from .render import inspect_wav


def audit_exports(root):
    root = Path(root)
    rows = []
    paths = []
    for entry in list_catalog()['compositions']:
        for variation in VARIATIONS:
            folder = root / entry['id'] / variation
            manifest_path = folder / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            for name, expected_hash in manifest['files'].items():
                path = folder / name
                if path.parent != folder or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                    raise ValueError(f'artifact_hash_mismatch: {path}')
            for name in ('composition.json', 'brush.json', 'run-manifest.json'):
                validate(json.loads((folder / name).read_text()))
            for event in json.loads((folder / 'events.json').read_text()):
                validate(event)
            rate = manifest['sample_rate_hz']
            expected_frames = round((manifest['form_duration_s'] + manifest['tail_s']) * rate)
            checks = {}
            for asset in manifest['assets']:
                validate(asset)
                path = folder / f'{asset["stem_id"]}.wav'
                actual = inspect_wav(path)
                frames = round(manifest['form_duration_s'] * rate) if asset['stem_id'] == 'brushes-loop' else expected_frames
                if (actual['sha256'] != asset['asset_hash'] or actual['frames'] != frames or
                        actual['sample_rate_hz'] != rate or actual['channels'] != 1 or
                        actual['clipped_samples'] != 0 or not 1e-5 < actual['rms'] < .9 or
                        not 0 < actual['sample_peak'] < .9 or actual['first_sample'] != 0 or actual['last_sample'] != 0):
                    raise ValueError(f'pcm_objective_failure: {path}')
                checks[asset['stem_id']] = actual
                paths.append(path)
            if len(checks) != 6 or manifest['audition_status'] != 'AUDITION_PENDING':
                raise ValueError('missing_audio_asset_or_invalid_audition_claim')
            rows.append({'composition_id': entry['id'], 'variation': variation,
                         'manifest_path': str(manifest_path),
                         'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                         'form_duration_s': manifest['form_duration_s'], 'sample_rate_hz': rate,
                         'mix_sample_peak': checks['mix']['sample_peak'], 'mix_rms': checks['mix']['rms'],
                         'mix_sha256': checks['mix']['sha256'], 'aligned_stem_frames': expected_frames,
                         'brush_loop_frames': checks['brushes-loop']['frames'],
                         'all_six_wavs_non_silent': True, 'all_six_wavs_clipping_count': 0,
                         'endpoint_samples_zero': True, 'audition_status': 'AUDITION_PENDING'})
    return {'evidence_type': 'actual_procedural_pcm_and_canonical_record_audit', 'status': 'passed',
            'renders_checked': len(rows), 'wav_files_checked': len(paths),
            'total_artifact_bytes': sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
            'renders': rows, 'human_audition': 'not_run', 'browser_audio': 'not_run',
            'physical_output_timing': 'not_run', 'model_or_device_required': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = audit_exports(args.root)
    if args.report:
        args.report.write_bytes(payload_bytes(report))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
