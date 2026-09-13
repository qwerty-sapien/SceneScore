"""Mutated production sidecar fault injection, never Blender-generated faults.

Validate fresh baselines and isolated mutations with an exact snapshot of the
requested validator. Immutable blends are hard-linked; JSON evidence is copied.
No lineage or fresh-process report is rewritten to make a mutation look genuine.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

from modules.blender.batch import bounded


VERSION = 'production-sidecar-fault-injection-1'
MUTATIONS = [
    ('disabled_floor', 'contact', 'asset_integrity', {'disabled_consequential_collider'}),
    ('deep_penetration', 'contact', 'geometric_contact', {'solid_penetration'}),
    ('unsupported_hover', 'contact', 'physical_motion', {'unsupported_rest'}),
    ('scale_growth', 'staircase', 'physical_motion', {'rigid_scale_drift'}),
    ('lost_release_velocity', 'near_miss', 'physical_motion', {'unsupported_rest', 'case_release'}),
    ('fabricated_miss_impact', 'near_miss', 'physical_motion', {'spurious_impact'}),
    ('stale_cache_lineage', 'contact', 'asset_integrity', {'stale_bake_source'}),
    ('low_rate_physics', 'staircase', 'physical_motion', set()),
]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def _write_rows(path, rows):
    Path(path).write_text(''.join(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n' for row in rows))


def source_inputs(source):
    source = Path(source).resolve()
    config = json.loads((source / 'production.json').read_text())
    names = {'production.json', 'physics_states.jsonl', 'replay_states.jsonl', 'replay_validation.json'}
    names.update(config.get('lineage', {}).get('artifacts', {}))
    names.update(name for name in ['production_events.json', 'solver_calibration.json'] if (source / name).exists())
    calibration_names = set()
    if (source / 'solver_calibration.json').is_file():
        calibration_names = set(json.loads((source / 'solver_calibration.json').read_text()).get('artifacts', {}))
    names.update(calibration_names)
    result = {}
    for name in sorted(names):
        path = (source / name).resolve()
        allowed_root = source.parent if name in calibration_names else source
        if Path(name).is_absolute() or not path.is_relative_to(allowed_root) or not path.is_file():
            raise ValueError(f'nonlocal or missing source input: {name}')
        result[name] = {'sha256': digest(path), 'size_bytes': path.stat().st_size}
    return result


def clone_sidecars(source, target):
    source, target = Path(source).resolve(), Path(target)
    inputs = source_inputs(source)
    target.mkdir(parents=True, exist_ok=False)
    for name in inputs:
        destination = (target / name).resolve()
        if not destination.is_relative_to(target.resolve().parent):
            raise ValueError('calibration copy leaves isolated scratch root')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if digest(destination) != inputs[name]['sha256']:
                raise ValueError('conflicting isolated calibration evidence')
            continue
        if Path(name).suffix == '.blend':
            os.link(source / name, destination)
        else:
            shutil.copyfile(source / name, destination)
    return inputs


def inject_fault(directory, name):
    """Mutate only copied sidecars; derive locations from baseline SI transforms."""
    directory = Path(directory)
    config = json.loads((directory / 'production.json').read_text())
    rows = _read_rows(directory / 'physics_states.jsonl')
    specs = config['objects']
    specs = specs if isinstance(specs, dict) else {obj['object_id']: obj for obj in specs}
    ball = next(oid for oid, spec in specs.items() if spec['shape'] == 'sphere' and spec['mode'] == 'dynamic')
    floor = next(oid for oid in specs if oid.endswith(':floor'))
    hz, duration = config['physics_hz'], config['duration_s']
    detail = {'mutation': name, 'scope': 'copied production sidecar fault, not Blender-generated physics',
              'object_id': ball, 'changed_files': []}
    if name == 'disabled_floor':
        specs[floor]['collision_enabled'] = False
        detail.update(object_id=floor, changed_files=['production.json'])
    elif name == 'stale_cache_lineage':
        config['lineage']['bake_source_fingerprint'] = '0' * 64
        detail['changed_files'] = ['production.json']
    elif name in {'deep_penetration', 'unsupported_hover'}:
        begin = round((duration - .5) * hz)
        fixed = copy.deepcopy(rows[begin]['objects'][ball])
        if name == 'deep_penetration':
            floor_state = rows[begin]['objects'][floor]
            if math.dist(floor_state['quaternion_xyzw'], [0, 0, 0, 1]) > 1e-4:
                raise ValueError('this bounded floor mutation requires an axis-aligned floor')
            fixed['position_m'][2] = floor_state['position_m'][2] + specs[floor]['half_extents_m'][2] + specs[ball]['radius_m'] - .08
            detail['penetration_depth_m'] = .08
        else:
            fixed['position_m'][2] += 2
            detail['vertical_offset_m'] = 2
        for row in rows[begin:]:
            row['objects'][ball] = copy.deepcopy(fixed)
        detail.update(interval_s=[begin / hz, duration], changed_files=['physics_states.jsonl'])
    elif name == 'scale_growth':
        begin = round((duration - 1) * hz)
        for row in rows[begin:]:
            factor = 1 + .2 * (row['time_s'] - begin / hz)
            row['objects'][ball]['scale'] = [factor] * 3
        detail.update(interval_s=[begin / hz, duration], ending_scale=1.2, changed_files=['physics_states.jsonl'])
    elif name == 'lost_release_velocity':
        deck = next(oid for oid in specs if oid.endswith(':projectile-deck'))
        radius = specs[ball]['radius_m']
        # Visible workshop deck faces +X; do not reuse validator collision logic.
        def past_deck(row):
            body, support = row['objects'][ball]['position_m'], row['objects'][deck]['position_m']
            return body[0] - radius > support[0] + specs[deck]['half_extents_m'][0] + .025 and body[2] > .7
        begin = next((i for i, row in enumerate(rows) if past_deck(row)), None)
        if begin is None:
            raise ValueError('no observed outbound release past deck')
        end = min(len(rows) - 1, begin + round(.35 * hz))
        fixed = copy.deepcopy(rows[begin]['objects'][ball])
        for row in rows[begin:end + 1]:
            row['objects'][ball] = copy.deepcopy(fixed)
        detail.update(interval_s=[begin / hz, end / hz], hold_s=(end - begin) / hz,
                      changed_files=['physics_states.jsonl'],
                      limitation='Zero sampled outgoing velocity imposed after deck clearance; no new release mechanism simulated.')
    elif name == 'fabricated_miss_impact':
        tower = next(oid for oid in specs if oid.endswith(':tower-1'))
        closest = min(rows, key=lambda row: math.dist(row['objects'][ball]['position_m'], row['objects'][tower]['position_m']))
        path = directory / 'production_events.json'
        document = json.loads(path.read_text()) if path.exists() else {'events': []}
        event = {'id': 'sidecar-fault-injected-impact', 'type': 'impact', 'time_s': closest['time_s'],
                 'object_ids': [ball, tower]}
        if isinstance(document, list):
            document.append(event)
        else:
            document.setdefault('events', []).append(event)
        write_json(path, document)
        detail.update(event=event, changed_files=['production_events.json'])
    elif name == 'low_rate_physics':
        stride = hz // 30
        original = copy.deepcopy(rows)
        for i, row in enumerate(rows):
            row['objects'] = copy.deepcopy(original[(i // stride) * stride]['objects'])
        repeated = sum(rows[i]['objects'] == rows[i - 1]['objects'] for i in range(1, len(rows)))
        detail.update(changed_files=['physics_states.jsonl'], source_hz=hz, held_sampling_hz=30,
                      consecutive_exact_object_state_repetitions=repeated,
                      limitation='Tick/time fields preserved; transforms held between 30 Hz samples.')
    else:
        raise ValueError(f'unknown mutation: {name}')
    if 'production.json' in detail['changed_files']:
        write_json(directory / 'production.json', config)
    if 'physics_states.jsonl' in detail['changed_files']:
        _write_rows(directory / 'physics_states.jsonl', rows)
    detail['lineage_policy'] = 'Original hash claims and fresh-process replay report preserved unchanged; never rebound to synthetic data.'
    return detail


def run_validation(validator, candidate, output, timeout):
    log = Path(output).with_suffix('.log')
    command = [sys.executable, str(validator), str(candidate)]
    job = bounded(command, log, timeout)
    record = {'command': command, 'job': job, 'log': str(log)}
    if log.is_file():
        record['log_sha256'] = digest(log)
    if job.get('process_group_absent') and job.get('returncode') in {0, 1} and job['status'] in {'passed', 'failed'}:
        try:
            result = json.loads(log.read_text())
            if not isinstance(result.get('gates'), dict) or not isinstance(result.get('issues'), list):
                raise ValueError('invalid validator result')
            record['validation'] = result
        except (ValueError, AttributeError) as exc:
            record['error'] = str(exc)
    else:
        record['error'] = 'validator did not complete with a verified absent process group'
    return record


def summarize_mutation(baseline, observed, expected_gate, expected_codes):
    if 'validation' not in baseline or 'validation' not in observed:
        return {'status': 'NOT_RUN', 'reason': 'complete baseline and mutation validator outputs required'}
    before, after = baseline['validation'], observed['validation']
    baseline_codes = {issue['code'] for issue in before['issues']}
    new_issues = [issue for issue in after['issues'] if issue['code'] not in baseline_codes]
    codes = {issue['code'] for issue in new_issues}
    detected = any(issue['gate'] == expected_gate and (not expected_codes or issue['code'] in expected_codes)
                   for issue in new_issues)
    return {'status': 'DETECTED' if detected else 'COVERAGE_GAP',
            'expected_gate': expected_gate, 'expected_fault_codes': sorted(expected_codes),
            'new_issue_codes': sorted(codes),
            'relevant_fault_detected': detected,
            'new_physics_or_geometry_issue_codes': sorted({issue['code'] for issue in new_issues
                if issue['gate'] in {'physical_motion', 'geometric_contact'}}),
            'integrity_or_replay_only': bool(new_issues) and all(issue['gate'] in {'asset_integrity', 'fresh_process_replay'} for issue in new_issues),
            'gate_statuses': {key: value['status'] for key, value in after['gates'].items()},
            'overall_candidate_status': after['status'],
            'baseline_failures_are_not_credited': sorted(baseline_codes)}


def audit(candidates, validator, output, *, timeout=180, mutation_names=None):
    if not 0 < timeout <= 1800 or set(candidates) != {'contact', 'near_miss', 'staircase'}:
        raise ValueError('three named candidates and timeout in (0, 1800] required')
    selected = [row for row in MUTATIONS if mutation_names is None or row[0] in mutation_names]
    if not selected or (mutation_names is not None and set(mutation_names) - {row[0] for row in MUTATIONS}):
        raise ValueError('at least one known mutation required')
    source_names = {row[1] for row in selected}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    validator = Path(validator).resolve()
    frozen = output / 'validator_snapshot.py'
    shutil.copyfile(validator, frozen)
    report = {'version': VERSION, 'description': 'Mutated production sidecar fault injection',
              'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'INCOMPLETE', 'approval': None,
              'source_validator': str(validator), 'validator_sha256': digest(frozen),
              'mutator_sha256': digest(__file__), 'blender_jobs_started': 0,
              'baselines': {}, 'mutations': [], 'sources': {},
              'limitations': ['These faults are injected into copied sidecars; no claim Blender generated them.',
                              'Baseline NOT_RUN gates remain unverified; no baseline is promoted by fault rejection.',
                              'Integrity-only rejection does not establish physical detection of a fault.',
                              'Rendering, continuous-motion perception and native solver calibration are not run.']}
    scratch_root = None
    try:
        for name, candidate in candidates.items():
            if name not in source_names:
                continue
            report['sources'][name] = {'path': str(Path(candidate).resolve()), 'inputs': source_inputs(candidate)}
            report['baselines'][name] = run_validation(frozen, candidate, output / ('baseline-' + name), timeout)
        with tempfile.TemporaryDirectory(prefix='scenescore-sidecar-faults-') as scratch:
            scratch_root = Path(scratch)
            for name, source_name, gate, codes in selected:
                directory = scratch_root / name
                clone_sidecars(candidates[source_name], directory)
                detail = inject_fault(directory, name)
                record = {'name': name, 'source': source_name, 'mutation': detail,
                          'copied_mutant_input_hashes': source_inputs(directory)}
                # Keep the actual small altered sidecars; never copy a fake .blend or fake replay report into evidence.
                evidence_dir = output / 'mutated-sidecars' / name
                evidence_dir.mkdir(parents=True)
                for relative in detail['changed_files']:
                    shutil.copyfile(directory / relative, evidence_dir / relative)
                observed = run_validation(frozen, directory, output / name, timeout)
                record['run'] = observed
                record['outcome'] = summarize_mutation(report['baselines'][source_name], observed, gate, codes)
                report['mutations'].append(record)
                write_json(output / 'audit.json', report)
        report['temporary_mutant_directories_removed'] = not scratch_root.exists()
        report['source_inputs_unchanged'] = all(source_inputs(candidates[name]) == item['inputs'] for name, item in report['sources'].items())
        report['validator_source_unchanged'] = digest(validator) == report['validator_sha256']
        all_runs = list(report['baselines'].values()) + [row['run'] for row in report['mutations']]
        report['owned_process_groups_absent'] = all(row['job'].get('process_group_absent') for row in all_runs)
        gaps = [row['name'] for row in report['mutations'] if row['outcome']['status'] != 'DETECTED']
        report['coverage_gaps'] = gaps
        report['status'] = 'COMPLETED_WITH_COVERAGE_GAPS' if gaps else 'COMPLETED'
        if not report['source_inputs_unchanged'] or not report['owned_process_groups_absent']:
            report['status'] = 'INCOMPLETE'
    finally:
        if scratch_root is not None:
            report['temporary_mutant_directories_removed'] = not scratch_root.exists()
        write_json(output / 'audit.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contact', required=True, type=Path)
    parser.add_argument('--near-miss', required=True, type=Path)
    parser.add_argument('--staircase', required=True, type=Path)
    parser.add_argument('--validator', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--mutation', action='append', choices=[row[0] for row in MUTATIONS],
                        help='limit a repair audit to specific faults; default is the complete suite')
    args = parser.parse_args(argv)
    report = audit({'contact': args.contact, 'near_miss': args.near_miss, 'staircase': args.staircase},
                   args.validator, args.out, timeout=args.timeout, mutation_names=args.mutation)
    print(json.dumps({'status': report['status'], 'report': str(args.out / 'audit.json'),
                      'coverage_gaps': report.get('coverage_gaps')}))
    return 0 if report['status'] == 'COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
