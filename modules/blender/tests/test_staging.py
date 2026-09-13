"""Transactional staging on synthetic bytes; no physics or media execution claim."""

import hashlib
import json

import pytest

from modules.blender import selection
from modules.blender.production import staging


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    root = tmp_path / 'artifacts/blender'
    bundle = root / 'synthetic-staging-fixture'
    bundle.mkdir(parents=True)
    for name, data in {
        'scene.blend': b'NOT BLENDER: transactional staging fixture',
        'preview.mp4': b'NOT VIDEO: transactional staging fixture',
        'physics_states.jsonl': b'{"synthetic":"not measured motion"}\n',
        'features.jsonl': b'{"synthetic":"not measured derivatives"}\n',
    }.items():
        (bundle / name).write_bytes(data)
    write(bundle / 'production.json', {'recipe_id': 'synthetic-staging', 'duration_s': 1 / 30})
    write(bundle / 'manifest.json', {'id': 'synthetic:staging', 'source_hash': sha(bundle / 'scene.blend'),
                                    'render_hash': sha(bundle / 'preview.mp4')})
    write(bundle / 'object_roles.json', {'roles_version': 'synthetic-fixture', 'scored_object_ids': ['fixture:ball']})
    write(bundle / 'handoff.json', {'handoff_version': 'synthetic-fixture', 'approval': None,
                                   'features': {'sha256': sha(bundle / 'features.jsonl')}})
    write(bundle / 'handoff_hashes.json', {'files': {name: sha(bundle / name)
                                                   for name in ('handoff.json', 'features.jsonl')}})
    # Reports below are deliberately synthetic shapes for resolver boundary tests.
    # Passing labels here never serve as actual production evidence.
    write(bundle / 'physical-validation.json', {
        'version': 'blender-independent-validation-1', 'candidate': str(bundle), 'status': 'PASSED',
        'inputs': {name: sha(bundle / name) for name in ('production.json', 'physics_states.jsonl')},
        'issues': [], 'gates': {name: {'status': 'PASSED'} for name in
                               ('asset_integrity', 'geometric_contact', 'physical_motion',
                                'fresh_process_replay', 'solver_calibration')},
    })
    for profile in ('preview', 'final'):
        media = bundle / 'renders' / profile / 'beauty'
        media.mkdir(parents=True)
        (media / 'video.mp4').write_bytes((bundle / 'preview.mp4').read_bytes())
        write(media / 'render.json', {'profile': profile, 'synthetic': True})
        inputs = {name: bundle / name for name in ('production.json', 'scene.blend', 'physics_states.jsonl')}
        inputs.update({name: media / name for name in ('render.json', 'video.mp4')})
        write(media / 'media-validation.json', {
            'media_validation_version': 'scene-production-media-validation-1', 'status': 'PASSED',
            'candidate': str(bundle), 'profile': profile, 'camera': 'beauty', 'approval': None,
            'inputs': {name: {'path': str(path), 'sha256': sha(path)} for name, path in inputs.items()},
            'checks': {name: {'status': 'PASSED'} for name in
                       ('input_integrity', 'source_motion_clock', 'presentation_timing',
                        'full_decode_and_motion_duplicates', 'immutable_inputs')},
        })
    # Use a deliberately noncanonical byte layout to catch JSON-equivalent rather
    # than exact-byte rollback. Handoff and proof files are sealed only by staging.
    names = ('manifest.json', 'scene.blend', 'preview.mp4', 'production.json',
             'physics_states.jsonl', 'object_roles.json')
    (bundle / 'bundle_hashes.json').write_text(json.dumps({
        'files': {name: sha(bundle / name) for name in names}, 'fixture_note': 'preserve original bytes',
    }, indent=4) + '\n\n')
    active_selection = root / 'accepted-candidate.json'
    active_selection.write_bytes(b'{"synthetic":"untouched active selection"}\n')
    monkeypatch.setattr(staging, 'ARTIFACT_ROOT', root)
    # The resolver's default root was bound at import. Supply this fixture root
    # explicitly while retaining its real complete verification implementation.
    monkeypatch.setattr(staging, 'staged_bundle', lambda path: selection.staged_bundle(path, artifact_root=root))
    return root, bundle, active_selection


@pytest.mark.parametrize('profile', ['preview', 'final'])
def test_success_seals_all_handoff_and_proof_bytes_without_accepting_or_changing_active_selection(candidate, profile):
    root, bundle, active = candidate
    active_bytes = active.read_bytes()
    old_index = read(bundle / 'bundle_hashes.json')
    output = root / 'reviews' / (profile + '.json')

    record = staging.stage_review(bundle, output, profile)

    sealed = read(bundle / 'bundle_hashes.json')
    expected_added = {'handoff.json', 'features.jsonl', 'handoff_hashes.json', 'physical-validation.json',
                      f'renders/{profile}/beauty/media-validation.json'}
    assert set(sealed['files']) == set(old_index['files']) | expected_added
    assert all(sealed['files'][name] == sha(bundle / name) for name in sealed['files'])
    assert record == read(output)
    assert record['candidate']['bundle_index_hash'] == sha(bundle / 'bundle_hashes.json')
    assert record['candidate']['media_validation_path'] == f'renders/{profile}/beauty/media-validation.json'
    assert record['approval'] is None
    assert record['acceptance'] == 'PENDING_CONTINUOUS_MOTION_AND_INDEPENDENT_REVIEW'
    resolved, info = selection.staged_bundle(output, artifact_root=root)
    assert resolved == bundle and info['approval'] is None
    assert active.read_bytes() == active_bytes


@pytest.mark.parametrize('failure', ['physical_gate', 'media_check'])
def test_downstream_verification_failure_rolls_back_exact_index_bytes_and_removes_selection(candidate, monkeypatch, failure):
    root, bundle, active = candidate
    if failure == 'physical_gate':
        evidence_path = bundle / 'physical-validation.json'
        evidence = read(evidence_path)
        evidence['gates']['physical_motion']['status'] = 'NOT_RUN'
        expected_error = 'selection_physics_inconsistent'
    else:
        evidence_path = bundle / 'renders/preview/beauty/media-validation.json'
        evidence = read(evidence_path)
        evidence['checks']['full_decode_and_motion_duplicates']['status'] = 'FAILED'
        expected_error = 'selection_media_inconsistent'
    write(evidence_path, evidence)
    before = snapshot(bundle)
    active_bytes = active.read_bytes()
    output = root / 'reviews' / 'failed.json'
    verifier_calls = []

    def verify_after_writes(path):
        # Prove the test fails downstream of both mutations, rather than during
        # initial validation before transactional cleanup is needed.
        assert path == output and output.is_file()
        assert (bundle / 'bundle_hashes.json').read_bytes() != before['bundle_hashes.json']
        assert {'handoff.json', 'features.jsonl', 'handoff_hashes.json'} <= read(bundle / 'bundle_hashes.json')['files'].keys()
        verifier_calls.append(path)
        return selection.staged_bundle(path, artifact_root=root)

    monkeypatch.setattr(staging, 'staged_bundle', verify_after_writes)
    with pytest.raises(ValueError, match=expected_error):
        staging.stage_review(bundle, output)

    assert verifier_calls == [output]
    assert not output.exists()
    assert snapshot(bundle) == before
    assert active.read_bytes() == active_bytes


def test_existing_selection_output_is_never_replaced(candidate):
    root, bundle, _ = candidate
    output = root / 'existing-review.json'
    output.write_bytes(b'{"synthetic":"preserve previous review"}\n')
    existing = output.read_bytes()
    before = snapshot(bundle)

    with pytest.raises(ValueError, match='new_review_selection_and_local_candidate_required'):
        staging.stage_review(bundle, output)

    assert output.read_bytes() == existing
    assert snapshot(bundle) == before
