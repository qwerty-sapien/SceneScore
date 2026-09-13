"""Seal one explicit production review bundle without changing active selection."""
import argparse
from pathlib import Path

from modules.blender.selection import ARTIFACT_ROOT, staged_bundle
from .common import digest, dump, read


def stage_review(candidate, output, profile='preview'):
    candidate,output=Path(candidate).resolve(),Path(output).resolve()
    if not candidate.is_relative_to(ARTIFACT_ROOT.resolve()) or output.exists():
        raise ValueError('new_review_selection_and_local_candidate_required')
    manifest=read(candidate/'manifest.json')
    index=read(candidate/'bundle_hashes.json')
    for name,expected in index['files'].items():
        path=(candidate/name).resolve()
        if not path.is_relative_to(candidate) or digest(path)!=expected:
            raise ValueError('stale_bundle_before_staging')
    # Handoff is derived after canonical export; bind its complete stream and index.
    handoff_index=read(candidate/'handoff_hashes.json')
    if not {'handoff.json','features.jsonl'}<=handoff_index.get('files',{}).keys():
        raise ValueError('incomplete_music_handoff_index')
    handoff=read(candidate/'handoff.json')
    if handoff.get('features',{}).get('sha256')!=digest(candidate/'features.jsonl'):
        raise ValueError('stale_motion_features')
    for name,expected in handoff_index['files'].items():
        path=(candidate/name).resolve()
        if not path.is_relative_to(candidate) or digest(path)!=expected:
            raise ValueError('stale_music_handoff')
        index['files'][name]=expected
    media_path=candidate/'renders'/profile/'beauty/media-validation.json'
    names=['handoff_hashes.json','physical-validation.json',str(media_path.relative_to(candidate))]
    for name in names:
        index['files'][name]=digest(candidate/name)
    original_index=(candidate/'bundle_hashes.json').read_bytes()
    try:
        dump(candidate/'bundle_hashes.json',index)
        entry={'path':str(candidate.relative_to(ARTIFACT_ROOT)), 'scene_id':manifest['id'],
               'source_hash':manifest['source_hash'],'video_hash':manifest['render_hash'],
               'bundle_index_hash':digest(candidate/'bundle_hashes.json'),
               'physical_validation_hash':digest(candidate/'physical-validation.json'),
               'roles_hash':digest(candidate/'object_roles.json'), 'music_handoff_hash':digest(candidate/'handoff.json'),
               'media_validation_path':str(media_path.relative_to(candidate)), 'media_validation_hash':digest(media_path)}
        record={'version':'blender-staged-candidate-1','recipe':read(candidate/'production.json')['recipe_id'],
                'candidate':entry,'approval':None,'acceptance':'PENDING_CONTINUOUS_MOTION_AND_INDEPENDENT_REVIEW',
                'scope':'Explicit scoped candidate; active hero/control selection remains separate.'}
        output.parent.mkdir(parents=True,exist_ok=True)
        dump(output,record)
        staged_bundle(output)
        return record
    except Exception:
        (candidate/'bundle_hashes.json').write_bytes(original_index)
        if output.exists():
            output.unlink()
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--profile',choices=['preview','final'],default='preview')
    args=parser.parse_args()
    record=stage_review(args.candidate,args.out,args.profile)
    print({'status':'STAGED_NOT_ACCEPTED','selection':str(args.out),'scene_id':record['candidate']['scene_id']})


if __name__=='__main__':
    main()
