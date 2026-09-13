"""Resolve one exact scene selection, retaining the historical legacy selection."""
import os
from pathlib import Path

from .production.common import digest, read

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT/'artifacts/blender'
DEFAULT_SELECTION = ARTIFACT_ROOT/'revamp/accepted-candidate.json'
LEGACY_SELECTION = ARTIFACT_ROOT/'phase2b-gate.json'


def verify_bundle(path, *, require_render=True):
    path = Path(path).resolve()
    index = read(path/'bundle_hashes.json')
    if not index.get('files'):
        raise ValueError('empty_bundle_index')
    for relative, expected in index['files'].items():
        source = (path/relative).resolve()
        if not source.is_relative_to(path) or not source.is_file() or digest(source) != expected:
            raise ValueError('bundle_hash_mismatch:'+relative)
    manifest = read(path/'manifest.json')
    if digest(path/'scene.blend') != manifest['source_hash']:
        raise ValueError('source_hash_mismatch')
    if (require_render or manifest.get('render_hash')) and (not manifest.get('render_hash') or digest(path/'preview.mp4') != manifest['render_hash']):
        raise ValueError('render_hash_mismatch')
    return manifest


def _verify_production_entry(bundle, entry, manifest):
    # Exact stored numerical proof must still match current source states.
    proof = read(bundle/'physical-validation.json')
    if proof.get('status')!='PASSED' or digest(bundle/'physical-validation.json')!=entry.get('physical_validation_hash'):
        raise ValueError('selection_physics_not_passed')
    gates=('asset_integrity','geometric_contact','physical_motion','fresh_process_replay','solver_calibration')
    if (proof.get('version')!='blender-independent-validation-1' or proof.get('candidate')!=str(bundle)
            or proof.get('issues') or any(proof.get('gates',{}).get(g,{}).get('status')!='PASSED' for g in gates)):
        raise ValueError('selection_physics_inconsistent')
    if not {'production.json','physics_states.jsonl'}<=proof.get('inputs',{}).keys():
        raise ValueError('selection_physics_inputs_missing')
    for name, expected in proof.get('inputs',{}).items():
        target=(bundle/name).resolve()
        if not target.is_relative_to(bundle) or digest(target)!=expected:
            raise ValueError('selection_physics_stale')
    if digest(bundle/'object_roles.json')!=entry.get('roles_hash'):
        raise ValueError('selection_roles_stale')
    if digest(bundle/'handoff.json')!=entry.get('music_handoff_hash'):
        raise ValueError('selection_handoff_stale')
    index=read(bundle/'bundle_hashes.json')
    handoff=read(bundle/'handoff.json')
    if not {'handoff.json','features.jsonl','handoff_hashes.json'}<=index['files'].keys():
        raise ValueError('selection_handoff_index_incomplete')
    if handoff.get('features',{}).get('sha256')!=index['files']['features.jsonl']:
        raise ValueError('selection_features_stale')
    relative=entry.get('media_validation_path')
    if not isinstance(relative,str):
        raise ValueError('selection_media_missing')
    media_path=(bundle/relative).resolve()
    if not media_path.is_relative_to(bundle) or digest(media_path)!=entry.get('media_validation_hash'):
        raise ValueError('selection_media_stale')
    media=read(media_path)
    required={'production.json','scene.blend','physics_states.jsonl','render.json','video.mp4'}
    if media.get('status')!='PASSED' or not required<=media.get('inputs',{}).keys():
        raise ValueError('selection_media_not_passed')
    checks=('input_integrity','source_motion_clock','presentation_timing','full_decode_and_motion_duplicates','immutable_inputs')
    if (media.get('media_validation_version')!='scene-production-media-validation-1' or media.get('candidate')!=str(bundle)
            or any(media.get('checks',{}).get(c,{}).get('status')!='PASSED' for c in checks)):
        raise ValueError('selection_media_inconsistent')
    for name,item in media['inputs'].items():
        target=Path(item['path']).resolve()
        expected_path=(bundle/name if name in ('production.json','scene.blend','physics_states.jsonl') else media_path.parent/name).resolve()
        if not target.is_relative_to(bundle) or target!=expected_path or digest(target)!=item['sha256']:
            raise ValueError('selection_media_input_stale')
    if media['inputs']['video.mp4']['sha256']!=manifest['render_hash']:
        raise ValueError('selection_media_video_mismatch')


def selected_bundle(variant='hero', selection=None, *, artifact_root=ARTIFACT_ROOT):
    variant = {'contact':'hero','near-miss':'near_miss'}.get(variant,variant)
    if variant not in ('hero','near_miss'):
        raise ValueError('unknown_selection_variant')
    selected = selection or os.environ.get('SCENESCORE_SELECTION')
    path = Path(selected) if selected else DEFAULT_SELECTION if DEFAULT_SELECTION.is_file() else LEGACY_SELECTION
    record = read(path)
    entry = record['accepted'][variant]
    root = Path(artifact_root).resolve()
    bundle = (root/entry['path']).resolve()
    if not bundle.is_relative_to(root):
        raise ValueError('selection_escapes_artifacts')
    if digest(bundle/'bundle_hashes.json') != entry['bundle_index_hash']:
        raise ValueError('stale_selection_index')
    manifest = verify_bundle(bundle)
    for key, value in [('scene_id',manifest['id']),('source_hash',manifest['source_hash']),('video_hash',manifest['render_hash'])]:
        if entry.get(key)!=value:
            raise ValueError('selection_identity_mismatch:'+key)
    legacy = record.get('version') is None and record.get('stage')=='2B'
    if not legacy and record.get('version')!='blender-accepted-candidate-1':
        raise ValueError('unsupported_selection_version')
    if not legacy:
        _verify_production_entry(bundle, entry, manifest)
    return bundle, {'selection_file':str(path.resolve()),'selection_sha256':digest(path),
                    'variant':variant,'entry':entry,'legacy_choreography':legacy,
                    'label':'Legacy · authored choreography' if legacy else 'Production · unapproved draft',
                    'approval':None}


def staged_bundle(selection, *, artifact_root=ARTIFACT_ROOT):
    """Explicit review candidate; never replaces the active hero/control selection."""
    path = Path(selection).resolve()
    record = read(path)
    if record.get('version') != 'blender-staged-candidate-1' or record.get('approval') is not None:
        raise ValueError('unsupported_staged_selection')
    entry = record['candidate']
    root = Path(artifact_root).resolve()
    bundle = (root/entry['path']).resolve()
    if not bundle.is_relative_to(root):
        raise ValueError('selection_escapes_artifacts')
    if digest(bundle/'bundle_hashes.json') != entry.get('bundle_index_hash'):
        raise ValueError('stale_selection_index')
    manifest = verify_bundle(bundle)
    for key, value in [('scene_id',manifest['id']),('source_hash',manifest['source_hash']),('video_hash',manifest['render_hash'])]:
        if entry.get(key) != value:
            raise ValueError('selection_identity_mismatch:'+key)
    _verify_production_entry(bundle, entry, manifest)
    return bundle, {'selection_file':str(path),'selection_sha256':digest(path),
                    'variant':record['recipe'],'entry':entry,'legacy_choreography':False,
                    'label':'Staged production review · acceptance pending','approval':None}
