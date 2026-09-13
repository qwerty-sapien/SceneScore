"""Fault injection mechanics and honest result accounting on synthetic fixtures."""
import copy
import json

import pytest

from tools import test_production_mutations as audit


def fixture_candidate(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    specs = [
        {'object_id': 'fixture:floor', 'shape': 'box', 'mode': 'passive', 'half_extents_m': [7, 4, .15], 'collision_enabled': True},
        {'object_id': 'fixture:projectile-deck', 'shape': 'box', 'mode': 'passive', 'half_extents_m': [.5, 1, .1]},
        {'object_id': 'fixture:tower-1', 'shape': 'box', 'mode': 'dynamic', 'half_extents_m': [.2, .2, .4]},
        {'object_id': 'fixture:ball', 'shape': 'sphere', 'mode': 'dynamic', 'radius_m': .2},
    ]
    rows = []
    for tick in range(961):
        positions = {'fixture:floor': [0, 0, -.15], 'fixture:projectile-deck': [0, 0, .7],
                     'fixture:tower-1': [1, 0, .4], 'fixture:ball': [-1 + tick / 240, 1, 1.2]}
        rows.append({'tick': tick, 'time_s': tick / 240,
                     'objects': {oid: {'position_m': p, 'quaternion_xyzw': [0, 0, 0, 1], 'scale': [1, 1, 1]}
                                 for oid, p in positions.items()}})
    audit._write_rows(source / 'physics_states.jsonl', rows)
    audit._write_rows(source / 'replay_states.jsonl', rows)
    (source / 'scene.blend').write_bytes(b'unit test fixture, not actual Blender evidence')
    audit.write_json(source / 'replay_validation.json', {'status': 'NOT_RUN', 'test_fixture': True})
    config = {'duration_s': 4, 'physics_hz': 240, 'objects': specs,
              'lineage': {'artifacts': {'scene.blend': audit.digest(source / 'scene.blend')},
                          'states_sha256': audit.digest(source / 'physics_states.jsonl'),
                          'bake_source_fingerprint': 'original-source-fingerprint'}}
    audit.write_json(source / 'production.json', config)
    return source


@pytest.mark.parametrize('name', [item[0] for item in audit.MUTATIONS])
def test_every_fault_changes_only_declared_copied_sidecars(tmp_path, name):
    source = fixture_candidate(tmp_path)
    before = audit.source_inputs(source)
    target = tmp_path / 'mutant'
    audit.clone_sidecars(source, target)
    assert (source / 'scene.blend').stat().st_ino == (target / 'scene.blend').stat().st_ino
    replay_before = (target / 'replay_validation.json').read_bytes()
    lineage_before = json.loads((target / 'production.json').read_text())['lineage']
    detail = audit.inject_fault(target, name)
    after = audit.source_inputs(target)
    changed = {key for key in after if before.get(key) != after[key]}
    assert changed == set(detail['changed_files'])
    assert audit.source_inputs(source) == before
    assert (target / 'replay_validation.json').read_bytes() == replay_before
    if name != 'stale_cache_lineage':
        assert json.loads((target / 'production.json').read_text())['lineage'] == lineage_before


def test_low_rate_mutation_keeps_clock_but_holds_all_transforms(tmp_path):
    source = fixture_candidate(tmp_path)
    target = tmp_path / 'mutant'
    audit.clone_sidecars(source, target)
    detail = audit.inject_fault(target, 'low_rate_physics')
    rows = audit._read_rows(target / 'physics_states.jsonl')
    assert rows[1]['objects'] == rows[7]['objects'] == rows[0]['objects']
    assert rows[8]['objects'] != rows[7]['objects']
    assert [row['tick'] for row in rows] == list(range(961))
    assert rows[7]['time_s'] == 7 / 240
    assert detail['consecutive_exact_object_state_repetitions'] == 840


def test_release_hold_is_past_deck_and_long_enough_to_exercise_unsupported_rest(tmp_path):
    source = fixture_candidate(tmp_path)
    target = tmp_path / 'mutant'
    audit.clone_sidecars(source, target)
    detail = audit.inject_fault(target, 'lost_release_velocity')
    rows = audit._read_rows(target / 'physics_states.jsonl')
    begin, end = [round(t * 240) for t in detail['interval_s']]
    assert rows[begin]['objects']['fixture:ball']['position_m'][0] - .2 > .5 + .025
    assert rows[begin]['objects']['fixture:ball'] == rows[end]['objects']['fixture:ball']
    assert (end - begin) / 240 == .35


def run_fixture(issues):
    return {'validation': {'status': 'FAILED' if issues else 'NOT_RUN', 'issues': issues,
                           'gates': {'solver_calibration': {'status': 'NOT_RUN'}}}}


def test_integrity_only_rejection_is_a_physical_coverage_gap():
    before = run_fixture([])
    observed = run_fixture([{'code': 'stale_state_digest', 'gate': 'asset_integrity'},
                            {'code': 'replay_evidence_mismatch', 'gate': 'fresh_process_replay'}])
    result = audit.summarize_mutation(before, observed, 'physical_motion', {'case_free_flight'})
    assert result['status'] == 'COVERAGE_GAP'
    assert result['integrity_or_replay_only'] is True
    assert result['new_physics_or_geometry_issue_codes'] == []
    assert result['gate_statuses']['solver_calibration'] == 'NOT_RUN'


def test_baseline_failures_are_not_credited_as_fault_detection():
    issue = {'code': 'solid_penetration', 'gate': 'geometric_contact'}
    baseline = run_fixture([issue])
    result = audit.summarize_mutation(baseline, copy.deepcopy(baseline), 'geometric_contact', {'solid_penetration'})
    assert result['status'] == 'COVERAGE_GAP'
    assert result['new_issue_codes'] == []
    assert audit.summarize_mutation({}, baseline, 'geometric_contact', {'solid_penetration'})['status'] == 'NOT_RUN'


def test_validator_expected_failure_exit_is_parsed_but_timeout_is_not(tmp_path, monkeypatch):
    def completed(command, log, timeout):
        audit.write_json(log, run_fixture([{'code': 'case_release', 'gate': 'physical_motion'}])['validation'])
        return {'status': 'failed', 'returncode': 1, 'process_group_absent': True}

    monkeypatch.setattr(audit, 'bounded', completed)
    report = audit.run_validation('validator.py', 'candidate', tmp_path / 'case', 1)
    assert report['validation']['status'] == 'FAILED'
    monkeypatch.setattr(audit, 'bounded', lambda *a, **k: {'status': 'timeout', 'returncode': -15, 'process_group_absent': True})
    report = audit.run_validation('validator.py', 'candidate', tmp_path / 'case', 1)
    assert 'validation' not in report
    assert 'error' in report


def test_clone_rejects_lineage_path_outside_candidate(tmp_path):
    source = fixture_candidate(tmp_path)
    external = tmp_path / 'outside.blend'
    external.write_bytes(b'do not link unrelated files')
    config = json.loads((source / 'production.json').read_text())
    config['lineage']['artifacts']['../outside.blend'] = audit.digest(external)
    audit.write_json(source / 'production.json', config)
    with pytest.raises(ValueError, match='nonlocal'):
        audit.clone_sidecars(source, tmp_path / 'mutant')
    assert not (tmp_path / 'mutant').exists()


def test_calibration_sibling_evidence_is_copied_without_rebinding_reports(tmp_path):
    source = fixture_candidate(tmp_path)
    sibling = tmp_path / 'control'
    sibling.mkdir()
    (sibling / 'physics_states.jsonl').write_text('{"independent_control_fixture": true}\n')
    (source / 'evaluated_geometry.json').write_text('{"fixture": true}\n')
    report = {'artifacts': {'../control/physics_states.jsonl': audit.digest(sibling / 'physics_states.jsonl'),
                            'evaluated_geometry.json': audit.digest(source / 'evaluated_geometry.json')}}
    audit.write_json(source / 'solver_calibration.json', report)
    target = tmp_path / 'isolated' / 'candidate'
    before = audit.source_inputs(source)
    audit.clone_sidecars(source, target)
    assert audit.source_inputs(target) == before
    assert (target / 'solver_calibration.json').read_bytes() == (source / 'solver_calibration.json').read_bytes()
    (target.parent / 'control' / 'physics_states.jsonl').write_text('changed only isolated copy')
    assert (sibling / 'physics_states.jsonl').read_text() == '{"independent_control_fixture": true}\n'


def test_low_rate_requires_a_new_physical_motion_failure():
    _, _, gate, codes = next(row for row in audit.MUTATIONS if row[0] == 'low_rate_physics')
    before = run_fixture([])
    only_integrity = run_fixture([{'code': 'stale_state_digest', 'gate': 'asset_integrity'}])
    assert audit.summarize_mutation(before, only_integrity, gate, codes)['status'] == 'COVERAGE_GAP'
    explicit_hold_fault = run_fixture([{'code': 'systematic_dynamic_pose_hold', 'gate': 'physical_motion'}])
    assert audit.summarize_mutation(before, explicit_hold_fault, gate, codes)['status'] == 'DETECTED'
