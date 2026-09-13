"""Selection integrity on tiny synthetic bytes; no Blender/media pass is claimed."""
from copy import deepcopy
import hashlib
import json

import pytest

from modules.blender import selection as resolver


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True)+'\n')


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reseal(bundle):
    names = ('manifest.json', 'scene.blend', 'preview.mp4', 'production.json', 'physics_states.jsonl',
             'object_roles.json', 'handoff.json', 'features.jsonl', 'handoff_hashes.json',
             'renders/final/beauty/video.mp4', 'renders/final/beauty/render.json')
    write(bundle/'bundle_hashes.json', {'hash_version': 'sha256-persisted-bytes-1',
                                      'files': {name: digest(bundle/name) for name in names}})


def fixture_selection(tmp_path, legacy=False):
    root = tmp_path/'artifacts/blender'
    root.mkdir(parents=True)
    record = {'stage': '2B', 'accepted': {}} if legacy else {'version': 'blender-accepted-candidate-1', 'accepted': {}}
    bundles = {}
    for variant in ('hero', 'near_miss'):
        bundle = root/'fixtures'/variant
        media_dir = bundle/'renders/final/beauty'
        media_dir.mkdir(parents=True)
        for name, data in {'scene.blend': b'NOT BLENDER: synthetic identity fixture '+variant.encode(),
                           'preview.mp4': b'NOT VIDEO: synthetic identity fixture '+variant.encode(),
                           'physics_states.jsonl': b'{"fixture":"not measured motion"}\n'}.items():
            (bundle/name).write_bytes(data)
        (media_dir/'video.mp4').write_bytes((bundle/'preview.mp4').read_bytes())
        write(bundle/'production.json', {'version': 'synthetic-selection-fixture', 'render_fps': 30, 'duration_s': 1/30})
        write(bundle/'manifest.json', {'id': 'synthetic:'+variant, 'source_hash': digest(bundle/'scene.blend'),
                                      'render_hash': digest(bundle/'preview.mp4')})
        write(bundle/'object_roles.json', {'roles_version': 'blender-object-roles-1', 'scene_id': 'synthetic:'+variant,
                                          'scored_object_ids': ['fixture:ball']})
        (bundle/'features.jsonl').write_bytes(b'{"fixture":"not measured features"}\n')
        write(bundle/'handoff.json', {'handoff_version': 'synthetic-handoff-fixture', 'approval': None,
                                     'features': {'sha256': digest(bundle/'features.jsonl')}})
        write(bundle/'handoff_hashes.json', {'files': {name: digest(bundle/name)
                                                     for name in ('handoff.json', 'features.jsonl')}})
        write(media_dir/'render.json', {'profile': 'final', 'camera': 'beauty', 'fps': 30, 'frame_count': 1,
              'width': 1920, 'height': 1080, 'returncode': 0, 'source_hash': digest(bundle/'scene.blend'),
              'states_hash': digest(bundle/'physics_states.jsonl'), 'video_hash': digest(bundle/'preview.mp4')})
        # These are deliberately synthetic report-shaped metadata for selector
        # boundary tests. No renderer, physics engine or decoder is invoked.
        proof = {'version': 'blender-independent-validation-1', 'candidate': str(bundle), 'status': 'PASSED',
                 'inputs': {name: digest(bundle/name) for name in ('production.json', 'physics_states.jsonl')},
                 'issues': [], 'gates': {name: {'status': 'PASSED'} for name in
                  ('asset_integrity', 'geometric_contact', 'physical_motion', 'fresh_process_replay', 'solver_calibration')}}
        write(bundle/'physical-validation.json', proof)
        media_inputs = {'production.json': bundle/'production.json', 'scene.blend': bundle/'scene.blend',
                        'physics_states.jsonl': bundle/'physics_states.jsonl', 'render.json': media_dir/'render.json',
                        'video.mp4': media_dir/'video.mp4'}
        media = {'media_validation_version': 'scene-production-media-validation-1', 'status': 'PASSED',
                 'candidate': str(bundle), 'profile': 'final', 'camera': 'beauty', 'approval': None,
                 'inputs': {name: {'path': str(path), 'sha256': digest(path), 'size_bytes': path.stat().st_size}
                            for name, path in media_inputs.items()},
                 'checks': {name: {'status': 'PASSED'} for name in
                   ('input_integrity', 'source_motion_clock', 'presentation_timing', 'full_decode_and_motion_duplicates', 'immutable_inputs')}}
        write(media_dir/'media-validation.json', media)
        reseal(bundle)
        manifest = read(bundle/'manifest.json')
        record['accepted'][variant] = {'path': str(bundle.relative_to(root)), 'scene_id': manifest['id'],
            'source_hash': manifest['source_hash'], 'video_hash': manifest['render_hash'],
            'bundle_index_hash': digest(bundle/'bundle_hashes.json'),
            'physical_validation_hash': digest(bundle/'physical-validation.json'),
            'roles_hash': digest(bundle/'object_roles.json'), 'music_handoff_hash': digest(bundle/'handoff.json'),
            'media_validation_path': 'renders/final/beauty/media-validation.json',
            'media_validation_hash': digest(media_dir/'media-validation.json')}
        bundles[variant] = bundle
    path = root/('phase2b-gate.json' if legacy else 'selection.json')
    write(path, record)
    return root, path, record, bundles


def select(fixture, variant='hero'):
    root, path, _, _ = fixture
    return resolver.selected_bundle(variant, path, artifact_root=root)


@pytest.mark.parametrize('variant, canonical', [('hero', 'hero'), ('contact', 'hero'),
                                              ('near_miss', 'near_miss'), ('near-miss', 'near_miss')])
def test_explicit_legacy_selection_retains_identity_and_label(tmp_path, variant, canonical):
    fixture = fixture_selection(tmp_path, legacy=True)
    root, path, record, bundles = fixture
    original = path.read_bytes()
    bundle, info = select(fixture, variant)
    assert bundle == bundles[canonical]
    assert info['entry'] == record['accepted'][canonical]
    assert info['label'] == 'Legacy · authored choreography'
    assert info['legacy_choreography'] and info['variant'] == canonical
    assert info['selection_sha256'] == digest(path)
    assert info['approval'] is None and path.read_bytes() == original


def test_valid_production_selection_remains_an_unapproved_draft(tmp_path):
    fixture = fixture_selection(tmp_path)
    root, path, record, bundles = fixture
    record['approval'] = {'decision': 'approved', 'reviewer': 'synthetic-not-a-human'}
    write(path, record)
    bundle, info = select(fixture)
    assert bundle == bundles['hero']
    assert info['label'] == 'Production · unapproved draft'
    assert not info['legacy_choreography'] and info['approval'] is None


@pytest.mark.parametrize('name', ['scene.blend', 'preview.mp4', 'bundle_hashes.json'])
def test_sealed_source_video_or_index_mutation_is_rejected(tmp_path, name):
    fixture = fixture_selection(tmp_path)
    path = fixture[3]['hero']/name
    path.write_bytes(path.read_bytes()+b' changed')
    with pytest.raises(ValueError):
        select(fixture)


@pytest.mark.parametrize('name, field', [('object_roles.json', 'roles_hash'), ('handoff.json', 'music_handoff_hash')])
def test_resealing_bundle_does_not_silently_reapprove_changed_roles_or_handoff(tmp_path, name, field):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    previous = record['accepted']['hero'][field]
    write(bundle/name, {**read(bundle/name), 'revision': 2})
    reseal(bundle)
    record['accepted']['hero']['bundle_index_hash'] = digest(bundle/'bundle_hashes.json')
    write(path, record)
    assert digest(bundle/name) != previous
    with pytest.raises(ValueError):
        select(fixture)


def test_source_and_video_identity_are_checked_even_if_index_omits_them(tmp_path):
    fixture = fixture_selection(tmp_path, legacy=True)
    bundle = fixture[3]['hero']
    write(bundle/'bundle_hashes.json', {'files': {'manifest.json': digest(bundle/'manifest.json')}})
    for name in ('scene.blend', 'preview.mp4'):
        original = (bundle/name).read_bytes()
        (bundle/name).write_bytes(original+b' changed')
        with pytest.raises(ValueError):
            resolver.verify_bundle(bundle)
        (bundle/name).write_bytes(original)


@pytest.mark.parametrize('escape', ['relative', 'absolute'])
def test_selection_bundle_cannot_escape_artifact_root(tmp_path, escape):
    fixture = fixture_selection(tmp_path)
    _, path, record, _ = fixture
    record['accepted']['hero']['path'] = '../outside' if escape == 'relative' else str(tmp_path/'outside')
    write(path, record)
    with pytest.raises(ValueError, match='selection_escapes'):
        select(fixture)


def test_bundle_index_cannot_reference_an_external_file(tmp_path):
    fixture = fixture_selection(tmp_path, legacy=True)
    bundle = fixture[3]['hero']
    outside = bundle.parent/'external.json'
    write(outside, {'fixture': 'outside candidate'})
    write(bundle/'bundle_hashes.json', {'files': {'../external.json': digest(outside)}})
    with pytest.raises(ValueError):
        resolver.verify_bundle(bundle)


@pytest.mark.parametrize('status', ['FAILED', 'NOT_RUN'])
def test_new_production_requires_passing_physical_proof(tmp_path, status):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    proof = read(bundle/'physical-validation.json')
    proof['status'] = status
    write(bundle/'physical-validation.json', proof)
    record['accepted']['hero']['physical_validation_hash'] = digest(bundle/'physical-validation.json')
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


@pytest.mark.parametrize('missing', ['all', 'production.json', 'physics_states.jsonl'])
def test_passing_label_without_required_current_physics_inputs_is_rejected(tmp_path, missing):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    proof = read(bundle/'physical-validation.json')
    if missing == 'all':
        proof['inputs'] = {}
    else:
        proof['inputs'].pop(missing)
    write(bundle/'physical-validation.json', proof)
    record['accepted']['hero']['physical_validation_hash'] = digest(bundle/'physical-validation.json')
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


def test_resealed_current_states_do_not_match_an_old_physical_proof(tmp_path):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    (bundle/'physics_states.jsonl').write_bytes(b'{"fixture":"changed state"}\n')
    reseal(bundle)
    record['accepted']['hero']['bundle_index_hash'] = digest(bundle/'bundle_hashes.json')
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


def test_physical_proof_input_paths_cannot_escape_candidate(tmp_path):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    external = bundle.parent/'external.json'
    write(external, {'fixture': 'outside candidate'})
    proof = read(bundle/'physical-validation.json')
    proof['inputs']['../external.json'] = digest(external)
    write(bundle/'physical-validation.json', proof)
    record['accepted']['hero']['physical_validation_hash'] = digest(bundle/'physical-validation.json')
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


@pytest.mark.parametrize('mutation', ['missing_binding', 'changed_report', 'failed', 'empty_inputs', 'stale_video_input'])
def test_production_selection_requires_exact_passing_current_media_evidence(tmp_path, mutation):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    entry = record['accepted']['hero']
    media_path = bundle/entry['media_validation_path']
    media = read(media_path)
    if mutation == 'missing_binding':
        entry.pop('media_validation_hash')
    else:
        if mutation == 'failed':
            media['status'] = 'FAILED'
        elif mutation == 'empty_inputs':
            media['inputs'] = {}
        elif mutation == 'stale_video_input':
            media['inputs']['video.mp4']['sha256'] = '0'*64
        else:
            media['unbound_change'] = True
        write(media_path, media)
        if mutation != 'changed_report':
            entry['media_validation_hash'] = digest(media_path)
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


def test_media_report_path_cannot_escape_candidate(tmp_path):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    entry = record['accepted']['hero']
    external = bundle.parent/'outside-media.json'
    external.write_bytes((bundle/entry['media_validation_path']).read_bytes())
    entry['media_validation_path'] = '../outside-media.json'
    entry['media_validation_hash'] = digest(external)
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


@pytest.mark.parametrize('location', ['outside_candidate', 'wrong_in_candidate_path'])
def test_media_inputs_must_resolve_to_the_declared_candidate_locations(tmp_path, location):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    entry = record['accepted']['hero']
    media_path = bundle/entry['media_validation_path']
    media = read(media_path)
    other = (bundle.parent if location == 'outside_candidate' else bundle)/'other-video.mp4'
    other.write_bytes((bundle/'preview.mp4').read_bytes())
    media['inputs']['video.mp4'] = {'path': str(other), 'sha256': digest(other), 'size_bytes': other.stat().st_size}
    write(media_path, media)
    entry['media_validation_hash'] = digest(media_path)
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


def test_matching_media_report_cannot_certify_a_different_video_than_the_selection(tmp_path):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    entry = record['accepted']['hero']
    media_path = bundle/entry['media_validation_path']
    media = read(media_path)
    video = media_path.parent/'video.mp4'
    video.write_bytes(b'NOT VIDEO: different synthetic reviewed identity')
    media['inputs']['video.mp4'] = {'path': str(video), 'sha256': digest(video), 'size_bytes': video.stat().st_size}
    write(media_path, media)
    reseal(bundle)
    entry['bundle_index_hash'] = digest(bundle/'bundle_hashes.json')
    entry['media_validation_hash'] = digest(media_path)
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


def test_unknown_production_version_cannot_downgrade_to_legacy(tmp_path):
    fixture = fixture_selection(tmp_path)
    _, path, record, _ = fixture
    record['version'] = 'blender-accepted-candidate-999'
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


def test_entry_identity_cannot_change_without_changing_exact_bundle(tmp_path):
    fixture = fixture_selection(tmp_path, legacy=True)
    _, path, record, _ = fixture
    previous = deepcopy(record['accepted']['hero'])
    record['accepted']['hero']['scene_id'] = 'another-scene'
    write(path, record)
    with pytest.raises(ValueError, match='selection_identity_mismatch'):
        select(fixture)
    assert record['accepted']['hero']['source_hash'] == previous['source_hash']


@pytest.mark.parametrize('kind', ['physical', 'media'])
@pytest.mark.parametrize('defect', ['failed_gate', 'missing_gate', 'wrong_version', 'wrong_candidate'])
def test_passing_report_label_cannot_override_contradictory_or_missing_proof_fields(tmp_path, kind, defect):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    entry = record['accepted']['hero']
    is_physical = kind == 'physical'
    proof_path = bundle/('physical-validation.json' if is_physical else entry['media_validation_path'])
    proof = read(proof_path)
    key, gate = ('gates', 'geometric_contact') if is_physical else ('checks', 'presentation_timing')
    if defect == 'failed_gate':
        proof[key][gate]['status'] = 'FAILED'
    elif defect == 'missing_gate':
        proof[key].pop(gate)
    elif defect == 'wrong_version':
        proof['version' if is_physical else 'media_validation_version'] = 'unknown-proof-999'
    else:
        proof['candidate'] = str(bundle.parent/'different-candidate')
    write(proof_path, proof)
    entry['physical_validation_hash' if is_physical else 'media_validation_hash'] = digest(proof_path)
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


@pytest.mark.parametrize('missing', ['handoff.json', 'features.jsonl', 'handoff_hashes.json'])
def test_production_selection_requires_complete_sealed_music_handoff(tmp_path, missing):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    index = read(bundle/'bundle_hashes.json')
    index['files'].pop(missing)
    write(bundle/'bundle_hashes.json', index)
    record['accepted']['hero']['bundle_index_hash'] = digest(bundle/'bundle_hashes.json')
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


def test_handoff_must_reference_the_sealed_feature_stream(tmp_path):
    fixture = fixture_selection(tmp_path)
    _, path, record, bundles = fixture
    bundle = bundles['hero']
    handoff = read(bundle/'handoff.json')
    handoff['features']['sha256'] = '0'*64
    write(bundle/'handoff.json', handoff)
    reseal(bundle)
    record['accepted']['hero']['bundle_index_hash'] = digest(bundle/'bundle_hashes.json')
    record['accepted']['hero']['music_handoff_hash'] = digest(bundle/'handoff.json')
    write(path, record)
    with pytest.raises(ValueError):
        select(fixture)


def staged_selection(fixture):
    root, _, record, _ = fixture
    path = root/'staged-selection.json'
    write(path, {'version': 'blender-staged-candidate-1', 'recipe': 'fixture-recipe',
                 'candidate': deepcopy(record['accepted']['near_miss']), 'approval': None})
    return path


def test_staged_review_uses_same_identity_without_replacing_default_active_selection(tmp_path, monkeypatch):
    fixture = fixture_selection(tmp_path)
    root, active, _, bundles = fixture
    staged = staged_selection(fixture)
    monkeypatch.delenv('SCENESCORE_SELECTION', raising=False)
    monkeypatch.setattr(resolver, 'DEFAULT_SELECTION', active)
    before = active.read_bytes()
    active_before = resolver.selected_bundle(artifact_root=root)
    bundle, info = resolver.staged_bundle(staged, artifact_root=root)
    assert bundle == bundles['near_miss'] and info['variant'] == 'fixture-recipe'
    assert info['label'] == 'Staged production review · acceptance pending'
    assert info['approval'] is None and not info['legacy_choreography']
    assert active.read_bytes() == before
    assert resolver.selected_bundle(artifact_root=root) == active_before


@pytest.mark.parametrize('defect', ['physics', 'media', 'roles', 'features', 'index', 'path', 'approval'])
def test_staged_selection_preserves_all_production_gates(tmp_path, defect):
    fixture = fixture_selection(tmp_path)
    root, active, _, bundles = fixture
    staged = staged_selection(fixture)
    record = read(staged)
    entry = record['candidate']
    bundle = bundles['near_miss']
    before = active.read_bytes()
    if defect in ('physics', 'media'):
        physical = defect == 'physics'
        proof_path = bundle/('physical-validation.json' if physical else entry['media_validation_path'])
        proof = read(proof_path)
        proof['gates' if physical else 'checks'].pop('physical_motion' if physical else 'input_integrity')
        write(proof_path, proof)
        entry['physical_validation_hash' if physical else 'media_validation_hash'] = digest(proof_path)
    elif defect in ('roles', 'features'):
        target = bundle/('object_roles.json' if defect == 'roles' else 'features.jsonl')
        target.write_bytes(target.read_bytes()+b' changed')
    elif defect == 'index':
        entry['bundle_index_hash'] = '0'*64
    elif defect == 'path':
        entry['path'] = '../outside-candidate'
    else:
        record['approval'] = {'decision': 'approved', 'reviewer': 'synthetic-not-human'}
    write(staged, record)
    with pytest.raises(ValueError):
        resolver.staged_bundle(staged, artifact_root=root)
    assert active.read_bytes() == before


def test_optional_render_verification_retains_nonrendered_legacy_query(tmp_path):
    fixture = fixture_selection(tmp_path, legacy=True)
    bundle = fixture[3]['hero']
    manifest = read(bundle/'manifest.json')
    manifest['render_hash'] = None
    write(bundle/'manifest.json', manifest)
    write(bundle/'bundle_hashes.json', {'files': {'manifest.json': digest(bundle/'manifest.json'),
                                               'scene.blend': digest(bundle/'scene.blend')}})
    assert resolver.verify_bundle(bundle, require_render=False) == manifest
    with pytest.raises(ValueError):
        resolver.verify_bundle(bundle)
