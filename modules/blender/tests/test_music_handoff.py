"""Motion-feature math and exact-evidence handoff tests; no media approval claims."""
import hashlib
import json
import math
from pathlib import Path

import pytest

from modules.blender.production.handoff import build_handoff, generate_features, main


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True)+'\n')


def sample(tick, hz=240, position=None, quaternion=None):
    t = tick/hz
    return {'tick': tick, 'time_s': t, 'objects': {'ball': {
        'position_m': [3*t, 0, 2*t*t] if position is None else position,
        'quaternion_xyzw': [0, 0, 0, 1] if quaternion is None else quaternion,
        'scale': [1, 1, 1]}}}


def test_causal_linear_features_follow_independent_polynomial():
    rows = list(generate_features([sample(i) for i in range(8)], ['ball']))
    initial = rows[0]['objects']['ball']
    assert initial['speed_m_s'] is None
    assert initial['reasons']['speed_m_s'] == 'initial_sample'
    for i, row in enumerate(rows[1:], 1):
        f = row['objects']['ball']
        average_vz = 4*(i-.5)/240
        assert f['velocity_world_m_s'] == pytest.approx([3, 0, average_vz])
        assert f['speed_m_s'] == pytest.approx(math.sqrt(9+average_vz**2))
        assert f['derivative_interval_s'] == [(i-1)/240, i/240]
        if i >= 2:
            assert f['acceleration_world_m_s2'] == pytest.approx([0, 0, 4], abs=1e-10)
            assert f['acceleration_m_s2'] == pytest.approx(4, abs=1e-10)
            assert f['acceleration_interval_s'] == [(i-2)/240, i/240]
    assert rows[1]['objects']['ball']['acceleration_m_s2'] is None


def test_world_angular_velocity_and_sign_flips_are_not_body_rotation():
    states = []
    # q(t) = world-Z rotation times a fixed 90-degree X tilt. In a body frame
    # the rotation axis would differ; the requested WORLD result remains +Z.
    k = math.sqrt(.5)
    for tick in range(8):
        half = tick/240  # angular speed = 2 rad/s
        sine, cosine = math.sin(half), math.cos(half)
        q = [k*cosine, k*sine, k*sine, k*cosine]
        if tick % 2:
            q = [-x for x in q]
        states.append(sample(tick, quaternion=q))
    features = list(generate_features(states, ['ball']))
    for row in features[1:]:
        f = row['objects']['ball']
        assert f['angular_velocity_world_rad_s'] == pytest.approx([0, 0, 2], abs=1e-12)
        assert f['angular_speed_rad_s'] == pytest.approx(2, abs=1e-12)
        assert f['reasons']['angular_velocity_world_rad_s'] is None


def test_exact_half_turn_is_ambiguous_but_sign_only_flip_is_zero():
    rows = list(generate_features([sample(0), sample(1, quaternion=[0, 0, 0, -1]),
                                   sample(2, quaternion=[0, 0, 1, 0])], ['ball']))
    assert rows[1]['objects']['ball']['angular_velocity_world_rad_s'] == [0, 0, 0]
    assert rows[2]['objects']['ball']['angular_velocity_world_rad_s'] is None
    assert rows[2]['objects']['ball']['reasons']['angular_speed_rad_s'] == 'ambiguous_half_turn'


def test_missing_samples_and_object_fields_do_not_bridge_derivatives():
    states = [sample(i) for i in (0, 1, 2, 4, 5, 6)]
    states[1]['objects']['ball']['quaternion_xyzw'] = None
    rows = list(generate_features(states, ['ball']))
    assert len(rows) == 7
    assert rows[1]['objects']['ball']['speed_m_s'] is not None
    assert rows[1]['objects']['ball']['angular_speed_rad_s'] is None
    assert rows[3]['objects']['ball']['reasons']['speed_m_s'] == 'sample_missing'
    assert rows[4]['objects']['ball']['reasons']['speed_m_s'] == 'previous_sample_missing'
    assert rows[5]['objects']['ball']['speed_m_s'] is not None
    assert rows[5]['objects']['ball']['acceleration_m_s2'] is None
    assert rows[6]['objects']['ball']['acceleration_m_s2'] == pytest.approx(4)
    states = [sample(i) for i in range(3)]
    states[1]['objects'] = {}
    rows = list(generate_features(states, ['ball']))
    assert rows[1]['objects']['ball']['reasons']['speed_m_s'] == 'object_state_missing'
    assert rows[2]['objects']['ball']['speed_m_s'] is None


def test_bad_clock_or_duplicate_tick_cannot_fabricate_rates():
    states = [sample(0), sample(1)]
    states[1]['time_s'] = 99
    rows = list(generate_features(states, ['ball']))
    assert rows[1]['objects']['ball']['reasons']['speed_m_s'] == 'invalid_sample_clock'
    with pytest.raises(ValueError, match='unique, increasing'):
        list(generate_features([sample(0), sample(0)], ['ball']))


def candidate(tmp_path):
    root = tmp_path/'candidate'
    root.mkdir()
    objects = [
        {'object_id': 'ball', 'sonic_identity_id': 'voice:ball', 'role': 'projectile',
         'scored': True, 'mode': 'dynamic', 'shape': 'sphere', 'radius_m': .25},
        {'object_id': 'floor', 'sonic_identity_id': 'silent:floor', 'role': 'support',
         'scored': False, 'mode': 'passive', 'shape': 'box', 'half_extents_m': [5, 5, .5]}]
    cases = [{'id': 'release-case', 'kind': 'release', 'object_id': 'ball',
              'release_time_s': .2, 'start_s': .1, 'end_s': .3, 'expected_velocity_m_s': [1, 0, 0]},
             {'id': 'miss-case', 'kind': 'near_miss', 'object_ids': ['ball', 'floor'], 'start_s': .1, 'end_s': .8},
             {'id': 'rest-case', 'kind': 'supported_rest', 'object_id': 'ball', 'start_s': .8, 'end_s': 1.}]
    production = {'physics_hz': 240, 'render_fps': 30, 'duration_s': 1., 'objects': objects,
                  'source_fingerprint': 'unit-fixture-source', 'source_mode': 'synthetic',
                  'validation_cases': cases, 'require_settled_end': True}
    dump(root/'production.json', production)
    # Deliberately a unit fixture, not a claimed Blender-generated source.
    (root/'scene.blend').write_bytes(b'UNIT TEST FIXTURE ONLY')
    manifest = {'id': 'fixture-scene', 'fps': 30, 'fps_base': 1, 'duration_s': 1.,
                'source_hash': digest(root/'scene.blend')}
    dump(root/'manifest.json', manifest)
    roles = {'roles_version': 'blender-object-roles-1', 'scene_id': 'fixture-scene',
             'scored_object_ids': ['ball'], 'objects': [{key: obj[key] for key in
              ('object_id', 'sonic_identity_id', 'role', 'scored', 'mode')} for obj in objects], 'approval': None}
    dump(root/'object_roles.json', roles)
    states = [sample(i) for i in range(241)]
    for row in states:
        row['objects']['floor'] = {'position_m': [0, 0, -.5], 'quaternion_xyzw': [0, 0, 0, 1], 'scale': [1, 1, 1]}
    (root/'physics_states.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in states))
    dump(root/'production_events.json', {'events': [{'id': 'contact-fixture', 'type': 'contact',
          'object_ids': ['ball', 'floor'], 'time_s': .4}]})
    report = {'status': 'PASSED', 'gates': {name: {'status': 'PASSED'} for name in
               ('asset_integrity', 'geometric_contact', 'physical_motion')},
              'inputs': {name: digest(root/name) for name in
                         ('production.json', 'physics_states.jsonl', 'production_events.json')},
              'metrics': {'cases': [
                  {'id': 'release-case', 'kind': 'release', 'status': 'PASSED', 'metrics': {}},
                  {'id': 'miss-case', 'kind': 'near_miss', 'status': 'PASSED',
                   'metrics': {'time_s': .5, 'minimum_sampled_gap_m': .2, 'uncertainty_m': .002}},
                  {'id': 'rest-case', 'kind': 'supported_rest', 'status': 'PASSED', 'metrics': {}}],
                  'event_validation': {'status': 'CHECKED', 'events_checked': 1}}}
    dump(root/'physical-validation.json', report)
    return root


def test_handoff_clock_roles_markers_and_exact_persisted_hashes(tmp_path):
    root = candidate(tmp_path)
    payload, index = build_handoff(root)
    assert payload['handoff_version'] == 'scene-music-handoff-1'
    assert payload['approval'] is None
    assert payload['clock']['video_frame_count'] == 30
    assert payload['clock']['physics_ticks_per_video_frame'] == 8
    assert payload['clock']['audio_samples_per_video_frame'] == 1600
    assert payload['clock']['audio_sample_count'] == 30*1600 == 48000
    assert payload['clock']['physics_tick_count_including_endpoint'] == 241
    assert payload['features']['row_count'] == 241
    assert payload['role_hash'] == digest(root/'object_roles.json')
    assert payload['objects'][1]['scored'] is False
    assert [marker['type'] for marker in payload['markers']] == ['release', 'contact', 'near_miss', 'settling']
    assert payload['marker_validation']['status'] == 'PASSED'
    for marker in payload['markers']:
        assert marker['confirmation_time_s'] >= marker['time_s']
        assert marker['uncertainty_s'] == 1/240
        for evidence in marker['evidence']:
            assert evidence['sha256'] == digest(root/evidence['path'])
    assert all(value == digest(root/name) for name, value in index['files'].items())
    again, again_index = build_handoff(root)
    assert again == payload and again_index == index


def test_stale_validation_suppresses_markers_but_preserves_raw_features(tmp_path):
    root = candidate(tmp_path)
    original, _ = build_handoff(root)
    path = root/'physics_states.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[30]['objects']['ball']['position_m'][0] += .01
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    result, _ = build_handoff(root)
    assert result['markers'] == []
    assert result['marker_validation']['status'] == 'UNVERIFIED'
    assert result['features']['sha256'] != original['features']['sha256']
    assert result['approval'] is None


def test_unbound_or_changed_event_bytes_never_become_validated_contacts(tmp_path):
    root = candidate(tmp_path)
    report = json.loads((root/'physical-validation.json').read_text())
    del report['inputs']['production_events.json']
    dump(root/'physical-validation.json', report)
    result, _ = build_handoff(root)
    assert 'contact' not in [marker['type'] for marker in result['markers']]
    assert 'release' in [marker['type'] for marker in result['markers']]
    assert any('exact event-file hash' in reason for reason in result['unavailable_markers'])
    report['inputs']['production_events.json'] = digest(root/'production_events.json')
    dump(root/'physical-validation.json', report)
    dump(root/'production_events.json', {'events': [{'type': 'contact', 'pair': ['ball', 'floor'], 'time_s': .9}]})
    result, _ = build_handoff(root)
    assert result['markers'] == []
    assert result['marker_validation']['status'] == 'UNVERIFIED'


def test_unknown_report_status_does_not_promote_passed_subcase(tmp_path):
    root = candidate(tmp_path)
    report = json.loads((root/'physical-validation.json').read_text())
    report['status'] = 'NOT_RUN'
    dump(root/'physical-validation.json', report)
    result, _ = build_handoff(root)
    assert result['markers'] == []
    assert result['marker_validation']['reported_status'] == 'NOT_RUN'


def test_role_or_scene_source_mismatch_fails_before_writing_handoff(tmp_path):
    root = candidate(tmp_path)
    roles = json.loads((root/'object_roles.json').read_text())
    roles['objects'][1]['scored'] = True
    dump(root/'object_roles.json', roles)
    with pytest.raises(ValueError, match='roles differ'):
        build_handoff(root)
    assert not (root/'handoff.json').exists()


def test_cli_and_missing_report_export_unapproved_with_no_markers(tmp_path, capsys):
    root = candidate(tmp_path)
    (root/'physical-validation.json').unlink()
    destination = tmp_path/'handoff'
    assert main([str(root), '--out', str(destination)]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'EXPORTED_UNAPPROVED'
    result = json.loads((destination/'handoff.json').read_text())
    assert result['marker_validation']['status'] == 'NOT_RUN'
    assert result['markers'] == []
    assert result['approval'] is None


def test_missing_state_grid_is_explicit_even_if_a_fixture_report_claims_pass(tmp_path):
    root = candidate(tmp_path)
    path = root/'physics_states.jsonl'
    rows = path.read_text().splitlines()
    del rows[100]
    path.write_text('\n'.join(rows)+'\n')
    report = json.loads((root/'physical-validation.json').read_text())
    report['inputs']['physics_states.jsonl'] = digest(path)
    dump(root/'physical-validation.json', report)
    result, _ = build_handoff(root)
    assert result['markers'] == []
    features = [json.loads(line) for line in (root/'features.jsonl').read_text().splitlines()]
    assert len(features) == 241
    assert features[100]['objects']['ball']['speed_m_s'] is None
    assert features[100]['objects']['ball']['reasons']['speed_m_s'] == 'sample_missing'


def test_handoff_imports_contact_and_supported_release_only_from_exact_recomputed_certificate(tmp_path, monkeypatch):
    from modules.blender.tests.test_production_export import candidate as export_candidate, interval_fixture
    from modules.blender.production.export import export_bundle
    root = export_candidate(tmp_path, initial_contact=True)
    interval_fixture(root, monkeypatch, release=True)
    export_bundle(root)
    original_production = digest(root/'production.json')
    payload, _ = build_handoff(root)
    assert {marker['type'] for marker in payload['markers']} == {'contact', 'release'}
    assert payload['interval_contact_provenance']['status'] == 'PASSED'
    assert payload['interval_contact_provenance']['coverage']['complete'] is False
    assert payload['input_hashes']['contact_intervals.json'] == digest(root/'contact_intervals.json')
    for marker in payload['markers']:
        assert marker['time_s'] == 1.5/240
        assert marker['confirmation_time_s'] == 5/240
        assert marker['uncertainty_s'] == 1/240
        assert not marker['physical_impulse_claim']
        assert marker['evidence'][0]['sha256'] == digest(root/'contact_intervals.json')
    assert digest(root/'production.json') == original_production
    assert not (root/'production_events.json').exists()


@pytest.mark.parametrize('fault', ['missing', 'stale_source', 'edited_after_certification', 'false_physical'])
def test_handoff_never_trusts_interval_flags_without_current_proof(tmp_path, monkeypatch, fault):
    from modules.blender.tests.test_production_export import candidate as export_candidate, interval_fixture
    from modules.blender.production.export import export_bundle
    root = export_candidate(tmp_path, initial_contact=True)
    interval_fixture(root, monkeypatch)
    export_bundle(root)
    path = root/'contact_intervals.json'
    if fault == 'missing':
        path.unlink()
    else:
        report = json.loads(path.read_text())
        if fault == 'stale_source':
            report['source_hashes']['physics_states.jsonl'] = '0'*64
        elif fault == 'false_physical':
            report['physical_evidence']['recomputed_status'] = 'NOT_RUN'
        else:
            # Plausible, still-PASSED metadata differs from fresh proof.
            report['contacts'][0]['incoming_normal_m_s'] = -100
        dump(path, report)
    payload, _ = build_handoff(root)
    assert payload['markers'] == []
    assert payload['interval_contact_provenance']['status'] != 'PASSED'
    assert payload['features']['row_count'] == 9


@pytest.mark.parametrize('mode', ['passive', 'driven'])
def test_nondynamic_rest_cases_and_report_windows_do_not_become_settling_markers(tmp_path, mode):
    root = candidate(tmp_path)
    production = json.loads((root/'production.json').read_text())
    production['objects'][1]['mode'] = mode
    production['validation_cases'].append({'id': 'support-rest', 'kind': 'supported_rest',
                                           'object_id': 'floor', 'start_s': 0, 'end_s': 1})
    dump(root/'production.json', production)
    roles = json.loads((root/'object_roles.json').read_text())
    roles['objects'][1]['mode'] = mode
    dump(root/'object_roles.json', roles)
    report = json.loads((root/'physical-validation.json').read_text())
    report['inputs']['production.json'] = digest(root/'production.json')
    report['metrics']['cases'].append({'id': 'support-rest', 'kind': 'supported_rest', 'status': 'PASSED'})
    report['metrics']['rest'] = {'floor': {'window_s': [.75, 1], 'supported_at_end': True,
                                           'max_final_speed_m_s': 0, 'max_final_angular_speed_rad_s': 0}}
    report['tolerance_policy'] = {'rest_speed_m_s': .02, 'rest_angular_speed_rad_s': .05}
    dump(root/'physical-validation.json', report)
    payload, _ = build_handoff(root)
    settling = [marker for marker in payload['markers'] if marker['type'] == 'settling']
    assert len(settling) == 1 and settling[0]['object_ids'] == ['ball']
    assert any('Nondynamic supported-rest' in reason for reason in payload['unavailable_markers'])
