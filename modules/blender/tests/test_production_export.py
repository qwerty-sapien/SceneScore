"""Synthetic geometry/clock fixtures; these are not Blender production evidence."""
import itertools
import json
import math

import pytest

from modules.blender.geometry import area
from modules.blender.production.common import digest, dump, read, rows
from modules.blender.production.export import export_bundle
from scenescore.contracts import validate_bundle


def candidate(tmp_path, *, positions=None, rotated=False, initial_contact=False, radius=.25):
    positions = positions or [[i/240, 0, 1] for i in range(9)]
    shape = 'box' if rotated else 'sphere'
    bodies = [{'object_id': 'fixture:actor', 'sonic_identity_id': 'voice:actor', 'role': 'projectile',
               'mode': 'dynamic', 'scored': True, 'shape': shape, 'radius_m': radius,
               'half_extents_m': [1, .1, .1], 'collision_enabled': True}]
    if not rotated:
        bodies.append({'object_id': 'fixture:target', 'sonic_identity_id': 'silent:target', 'role': 'support',
                       'mode': 'passive', 'scored': False, 'shape': 'sphere', 'radius_m': radius,
                       'collision_enabled': True})
    quaternion = [0, 0, math.sqrt(.5), math.sqrt(.5)] if rotated else [0, 0, 0, 1]
    transform = {'position_m': [4, -6, 4], 'quaternion_xyzw': [0, 0, 0, 1],
                 'matrix_row_major': [1, 0, 0, 4, 0, 1, 0, -6, 0, 0, 1, 4, 0, 0, 0, 1]}
    production = {'version': 'blender-production-1', 'recipe_id': 'fixture', 'variant': 'contact',
                  'seed': 42, 'physics_hz': 240, 'render_fps': 30, 'duration_s': 1/30,
                  'source_mode': 'synthetic', 'blender_version': 'synthetic-fixture-not-Blender',
                  'motion_mode': 'synthetic geometry fixture', 'camera': {'id': 'fixture-camera',
                  'transform': transform}, 'objects': bodies}
    dump(tmp_path/'production.json', production)
    (tmp_path/'scene.blend').write_bytes(b'synthetic fixture, not an openable Blender scene')
    geometry = {}
    for spec in bodies:
        if spec['shape'] == 'box':
            vertices = [[a*x for a, x in zip(signs, spec['half_extents_m'])]
                        for signs in itertools.product((-1, 1), repeat=3)]
            faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
            triangles = [triangle for a, b, c, d in faces for triangle in ([a, b, c], [a, c, d])]
        else:
            r = spec['radius_m']
            vertices = [[r, 0, 0], [-r, 0, 0], [0, r, 0], [0, -r, 0], [0, 0, r], [0, 0, -r]]
            triangles = [[z, x, y] for z in (4, 5) for x, y in ((0, 2), (2, 1), (1, 3), (3, 0))]
        geometry[spec['object_id']] = {'vertices_local': vertices, 'triangles': triangles,
                                      'surface_area_m2': area(vertices, triangles), 'material_rgba': [.5]*3+[1],
                                      'method': 'synthetic explicit triangulated test mesh'}
    dump(tmp_path/'evaluated_geometry.json', geometry)
    samples = []
    for i, position in enumerate(positions):
        states = {b['object_id']: {'position_m': position if n == 0 else [0, 0, 0],
                                  'quaternion_xyzw': quaternion, 'scale': [1, 1, 1]}
                  for n, b in enumerate(bodies)}
        if initial_contact:
            states['fixture:actor']['position_m'] = [.5, 0, 0]
        samples.append({'tick': i, 'time_s': i/240, 'objects': states})
    (tmp_path/'physics_states.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in samples))
    return tmp_path


def canonical(out):
    manifest = read(out/'manifest.json')
    states = list(rows(out/'object_states.jsonl'))
    events = list(rows(out/'interactions.jsonl'))
    validate_bundle([manifest, *states, *events])
    return manifest, states, events


def test_native_clock_rotated_evaluated_bounds_and_causal_derivatives(tmp_path):
    out = candidate(tmp_path, rotated=True)
    export_bundle(out)
    manifest, states, _ = canonical(out)
    assert manifest['render_hash'] is None
    assert states[0]['velocity_m_s'] is None and states[1]['acceleration_m_s2'] is None
    assert states[1]['velocity_m_s'] == pytest.approx([1, 0, 0])
    assert states[2]['acceleration_m_s2'] == pytest.approx([0, 0, 0])
    assert states[0]['bounds_min_m'] == pytest.approx([-.1, -1, .9])
    assert states[0]['bounds_max_m'] == pytest.approx([.1, 1, 1.1])
    assert states[0]['transform']['matrix_row_major'][1] == pytest.approx(-1)
    assert states[-1]['frame'] == 2 and states[-1]['scene_time_s'] == 1/30
    assert all(s['scene_time_s'] == pytest.approx((s['frame']-1)/30) for s in states)


def test_one_contact_onset_per_episode_never_claims_impact_or_impulse(tmp_path):
    distances = [.6, .55, .5, .4998, .5, .4999, .5, .5, .5]
    out = candidate(tmp_path, positions=[[d, 0, 0] for d in distances])
    export_bundle(out)
    manifest, _, events = canonical(out)
    assert len(events) == 1
    event = events[0]
    assert event['event_type'] == 'contact_onset' and event['onset_s'] == 2/240
    assert event['method'] == 'baked' and not event['physical_impact'] and event['impulse_ns'] is None
    assert event['relative_normal_speed_m_s'] == pytest.approx(-12)
    assert len(manifest['objects']) == 2
    assert read(out/'object_roles.json')['scored_object_ids'] == ['fixture:actor']


def test_initial_support_produces_no_contact_foley(tmp_path):
    out = candidate(tmp_path, initial_contact=True)
    export_bundle(out)
    assert canonical(out)[2] == []


@pytest.mark.parametrize('signed_gap, expected_events', [(.002083, 1), (-.002083, 0)])
def test_declared_contact_margins_never_expand_penetration_cap(tmp_path, signed_gap, expected_events):
    out = candidate(tmp_path, radius=.075,
                    positions=[[.17, 0, 0]]+[[.15+signed_gap, 0, 0] for _ in range(8)])
    production = read(out/'production.json')
    for body in production['objects']:
        body['collision_margin_m'] = .0005
    production['motion_mode'] = 'analytic fixed-obstacle dynamics; evaluated replay'
    production['physics_backend'] = 'analytic-fixed-obstacle-1'
    dump(out/'production.json', production)
    export_bundle(out)
    events = canonical(out)[2]
    assert len(events) == expected_events
    pair = read(out/'geometry.json')['pairs'][0]
    assert pair['penetration_tolerance_m'] == pytest.approx(.0015)
    assert pair['contact_envelope_m'] == pytest.approx(.0025)
    if events:
        assert events[0]['surface_gap_m'] == pytest.approx(signed_gap)
        assert events[0]['uncertainty_m'] == pytest.approx(.0025)
        detail = read(out/'geometry.json')['event_details'][0]
        assert detail['physics_backend'] == 'analytic-fixed-obstacle-1'
        assert 'Bullet' not in detail['physical_dynamics']
        assert detail['validated'] is False
        assert detail['source_evidence']['physics_states.jsonl'] == digest(out/'physics_states.jsonl')


def test_validation_marker_requires_matching_report_and_independent_recomputation(tmp_path, monkeypatch):
    from modules.blender.production import export as exporter
    out = candidate(tmp_path, positions=[[d, 0, 0] for d in [.6, .5, .5, .5, .5, .5, .5, .5, .5]])
    inputs = {name: digest(out/name) for name in ('production.json', 'physics_states.jsonl')}
    gates = ('asset_integrity', 'geometric_contact', 'physical_motion', 'fresh_process_replay', 'solver_calibration')
    # Deliberately simulated report/checker results test trust boundaries only.
    report = {'version': exporter.VALIDATOR_VERSION, 'status': 'PASSED', 'candidate': str(out),
              'inputs': inputs, 'issues': [], 'gates': {g: {'status': 'PASSED'} for g in gates}}
    dump(out/'physical-validation.json', report)
    monkeypatch.setattr(exporter, 'validate_candidate', lambda root: {'status': 'FAILED', 'inputs': inputs})
    export_bundle(out)
    assert not read(out/'geometry.json')['event_details'][0]['validated']
    monkeypatch.setattr(exporter, 'validate_candidate', lambda root: {'status': 'PASSED', 'inputs': inputs})
    export_bundle(out)
    assert read(out/'geometry.json')['event_details'][0]['validated']
    report['inputs'] = {**inputs, 'production.json': '0'*64}
    dump(out/'physical-validation.json', report)
    export_bundle(out)
    assert not read(out/'geometry.json')['event_details'][0]['validated']


def test_reseparation_allows_new_episode_but_not_a_sustain_flood(tmp_path):
    out = candidate(tmp_path, positions=[[d, 0, 0] for d in [.6, .5, .5, .52, .5, .5, .5, .5, .5]])
    export_bundle(out)
    events = canonical(out)[2]
    assert [e['onset_s'] for e in events] == [1/240, 4/240]
    assert {e['event_type'] for e in events} == {'contact_onset'}


def test_bracketed_near_miss_carries_positive_clearance_and_late_confirmation(tmp_path):
    xs = [-.3, -.2, -.1, -.05, 0, .05, .1, .2, .3]
    out = candidate(tmp_path, positions=[[x, 1, 0] for x in xs])
    export_bundle(out)
    events = canonical(out)[2]
    assert len(events) == 1 and events[0]['event_type'] == 'near_miss'
    assert events[0]['surface_gap_m'] > events[0]['uncertainty_m'] > 0
    detail = read(out/'geometry.json')['event_details'][0]
    assert detail['confirmation_time_s'] > events[0]['onset_s']


def test_index_binds_chosen_video_and_excludes_future_reports(tmp_path):
    out = candidate(tmp_path, initial_contact=True)
    for profile in ('preview', 'final'):
        target = out/'renders'/profile/'beauty'
        target.mkdir(parents=True)
        (target/'video.mp4').write_bytes(profile.encode()+b' synthetic not decoded video')
        dump(target/'render.json', {'source_hash': digest(out/'scene.blend'),
             'states_hash': digest(out/'physics_states.jsonl'), 'video_hash': digest(target/'video.mp4'),
             'fps': 30, 'frame_count': 1, 'returncode': 0})
    export_bundle(out)
    index = read(out/'bundle_hashes.json')['files']
    assert (out/'preview.mp4').read_bytes().startswith(b'final')
    assert canonical(out)[0]['render_hash'] == digest(out/'preview.mp4')
    assert 'renders/final/beauty/video.mp4' in index
    assert 'renders/preview/beauty/video.mp4' not in index
    dump(out/'physical-validation.json', {'status': 'NOT_RUN'})
    export_bundle(out)
    assert read(out/'bundle_hashes.json')['files'] == index
    rendered = read(out/'renders/final/beauty/render.json')
    rendered['source_hash'] = '0'*64
    dump(out/'renders/final/beauty/render.json', rendered)
    with pytest.raises(ValueError, match='render lineage'):
        export_bundle(out)


@pytest.mark.parametrize('mutation', ['tick', 'scale', 'area', 'missing_mesh'])
def test_export_rejects_missing_or_changed_evaluated_evidence(tmp_path, mutation):
    out = candidate(tmp_path)
    if mutation in ('tick', 'scale'):
        samples = list(rows(out/'physics_states.jsonl'))
        if mutation == 'tick':
            samples[3]['tick'] = 2
        else:
            samples[3]['objects']['fixture:actor']['scale'] = [.9]*3
        (out/'physics_states.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in samples))
    elif mutation == 'area':
        geometry = read(out/'evaluated_geometry.json')
        geometry['fixture:actor']['surface_area_m2'] *= 2
        dump(out/'evaluated_geometry.json', geometry)
    else:
        (out/'evaluated_geometry.json').unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        export_bundle(out)


def interval_fixture(out, monkeypatch, *, release=False):
    """Simulated independent responses exercise binding, never actual physics."""
    from modules.blender.production import export as exporter
    from modules.blender.production.common import data_hash
    production = read(out/'production.json')
    production['motion_mode'] = exporter.contact_intervals.BACKEND
    dump(out/'production.json', production)
    for name in ('solver_calibration.json', 'replay_validation.json'):
        dump(out/name, {'status': 'UNIT_TEST_FIXTURE_ONLY'})
    inputs = {name: digest(out/name) for name in ('production.json', 'physics_states.jsonl')}
    gates = ('asset_integrity', 'geometric_contact', 'physical_motion', 'fresh_process_replay', 'solver_calibration')
    physical = {'version': exporter.VALIDATOR_VERSION, 'status': 'PASSED', 'candidate': str(out),
                'inputs': inputs, 'issues': [], 'gates': {name: {'status': 'PASSED'} for name in gates}}
    dump(out/'physical-validation.json', physical)
    monkeypatch.setattr(exporter, 'validate_candidate', lambda _: physical)
    pre, post = {'ticks': [0, 1]}, {'ticks': [3, 4, 5]}
    certificate = {'id': 'unit-contact-0', 'numerical_status': 'PASSED', 'validated': True,
                   'object_ids': ['fixture:actor', 'fixture:target'], 'sphere_id': 'fixture:actor',
                   'obstacle_id': 'fixture:target', 'tick_interval': [1, 2],
                   'physical_time_estimate_s': 1.5/240, 'time_uncertainty_s': 1/240,
                   'confirmation_time_s': 5/240, 'position_at_contact_m': [.5, 0, 0],
                   'incoming_normal_m_s': -2., 'outgoing_normal_m_s': 1.,
                   'pre_fit': pre, 'post_fit': post, 'source_hashes': inputs}
    certificate['fit_pair_sha256'] = data_hash({'pre': pre, 'post': post, 'pair': certificate['object_ids'],
                                               'time_s': certificate['physical_time_estimate_s']})
    report = {'version': exporter.contact_intervals.VERSION, 'backend': exporter.contact_intervals.BACKEND,
              'status': 'PASSED', 'coverage': {'complete': False}, 'policy': {'contact_continuity_m': .001},
              'implementation_sha256': digest(exporter.contact_intervals.__file__),
              'source_hashes': {name: digest(out/name) for name in (*inputs, 'physical-validation.json',
                                'solver_calibration.json', 'replay_validation.json')},
              'physical_evidence': {'recomputed_status': 'PASSED', 'eligible': True, 'issues': [],
                                    'gates': physical['gates']}, 'contacts': [certificate], 'releases': []}
    if release:
        import copy
        departure = copy.deepcopy(certificate)
        departure.update(id='unit-release-0', kind='supported_release', support_id='fixture:target',
                         pre_support_fit=pre, post_flight_fit={**post, 'centre_time_s': 1.5/240,
                         'position_at_centre_m': [.5, 0, 0], 'velocity_at_centre_m_s': [2, 0, 0],
                         'gravity_m_s2': [0, 0, -9.81]}, checked='measured supported departure',
                         not_checked='no launcher calibration')
        departure['fit_pair_sha256'] = data_hash({'pre': pre, 'post': departure['post_flight_fit'],
                                                 'pair': departure['object_ids'], 'time_s': 1.5/240})
        report['releases'] = [departure]
    monkeypatch.setattr(exporter.contact_intervals, 'certify_candidate', lambda _: report)
    return report


def test_certified_interval_onset_is_merged_at_fitted_time_and_source_is_immutable(tmp_path, monkeypatch):
    out = candidate(tmp_path, positions=[[d, 0, 0] for d in [.6, .55, .5, .5, .5, .5, .5, .5, .5]])
    report = interval_fixture(out, monkeypatch)
    production_hash = digest(out/'production.json')
    result = export_bundle(out)
    events = canonical(out)[2]
    assert len(events) == 1 and events[0]['onset_s'] == 1.5/240
    assert result['certified_interval_contacts'] == 1
    assert events[0]['relative_normal_speed_m_s'] == -2
    assert not events[0]['physical_impact'] and events[0]['impulse_ns'] is None
    detail = read(out/'geometry.json')['event_details'][0]
    assert detail['confirmation_time_s'] == 5/240
    assert detail['deduplicated_sampled_event']['onset_s'] == 2/240
    assert detail['interval_certificate']['sha256'] == digest(out/'contact_intervals.json')
    assert read(out/'contact_intervals.json') == report
    assert read(out/'bundle_hashes.json')['files']['contact_intervals.json'] == digest(out/'contact_intervals.json')
    assert digest(out/'production.json') == production_hash
    assert not (out/'production_events.json').exists()


def test_interval_contact_catches_unsampled_bounce_without_widening_touch_envelope(tmp_path, monkeypatch):
    out = candidate(tmp_path, positions=[[d, 0, 0] for d in [.6, .55, .53, .55, .6, .65, .7, .75, .8]])
    interval_fixture(out, monkeypatch, release=True)
    result = export_bundle(out)
    events = canonical(out)[2]
    assert [event['event_type'] for event in events] == ['contact_onset', 'contact_release']
    assert result['certified_supported_releases'] == 1
    assert read(out/'geometry.json')['pairs'][0]['contact_envelope_m'] == pytest.approx(.005)
    assert all(not event['physical_impact'] for event in events)


@pytest.mark.parametrize('fault', ['missing_physical_report', 'stale_source', 'false_physical', 'forged_fit'])
def test_interval_certificate_faults_do_not_promote_onsets(tmp_path, monkeypatch, fault):
    out = candidate(tmp_path, initial_contact=True)
    report = interval_fixture(out, monkeypatch)
    if fault == 'missing_physical_report':
        (out/'physical-validation.json').unlink()
    elif fault == 'stale_source':
        report['source_hashes']['physics_states.jsonl'] = '0'*64
    elif fault == 'false_physical':
        report['physical_evidence']['recomputed_status'] = 'NOT_RUN'
    else:
        report['contacts'][0]['physical_time_estimate_s'] += .0001
    result = export_bundle(out)
    assert result['certified_interval_contacts'] == 0
    assert canonical(out)[2] == []
    assert not (out/'contact_intervals.json').exists()


def test_sampled_envelope_contact_is_reference_only_not_independently_timed_foley(tmp_path):
    out = candidate(tmp_path, positions=[[d, 0, 0] for d in [.6, .55, .503, .502, .501, .5, .5, .5, .5]])
    export_bundle(out)
    event = canonical(out)[2][0]
    detail = read(out/'geometry.json')['event_details'][0]
    assert event['onset_s'] == 2/240 and event['surface_gap_m'] > 0
    assert detail['time_semantics'] == 'sampled_envelope_entry'
    assert detail['time_uncertainty_s'] == 1/240
    assert detail['physical_impact_time_s'] is None
    assert detail['physical_impact_time_uncertainty_s'] is None
    assert detail['foley_eligible'] is False
    assert 'does not independently certify' in detail['foley_ineligible_reason']


def test_only_certified_onset_details_are_foley_eligible(tmp_path, monkeypatch):
    out = candidate(tmp_path, initial_contact=True)
    interval_fixture(out, monkeypatch, release=True)
    export_bundle(out)
    events = {event['id']: event for event in canonical(out)[2]}
    details = read(out/'geometry.json')['event_details']
    allowed = [events[d['id']] for d in details if d['validated'] and d['foley_eligible']]
    assert [event['event_type'] for event in allowed] == ['contact_onset']
    assert all(d['foley_ineligible_reason'] for d in details if not d['foley_eligible'])
