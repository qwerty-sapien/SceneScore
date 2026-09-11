"""Independent bundle QA in service Python; never labels visuals as reviewed."""
import argparse
import json
import itertools
from pathlib import Path
import subprocess
from scenescore.contracts import validate
from modules.blender.exporter import digest
from modules.blender.summary import _lines
from modules.blender.geometry import norm, sub, pair_timeline
from modules.blender.recipes import recipe, position


def validate_bundle(path):
    root=Path(path)
    manifest=json.loads((root/'manifest.json').read_text())
    states=_lines(root/'object_states.jsonl')
    events=_lines(root/'interactions.jsonl')
    for r in [manifest,*states,*events]:
        validate(r)
    assert manifest['source_hash']==digest(root/'scene.blend'), 'source hash mismatch'
    hashes=json.loads((root/'bundle_hashes.json').read_text())['files']
    for name,sha in hashes.items():
        file=(root/name).resolve()
        assert file.is_relative_to(root.resolve()),'escaping bundle hash path'
        assert digest(file)==sha, 'bundle hash mismatch: '+name
    ids={o['object_id'] for o in manifest['objects']}
    assert len({s['id'] for s in states})==len(states),'duplicate state'
    assert len({s['id'] for s in events})==len(events),'duplicate event'
    for oid in ids:
        ss=[s for s in states if s['object_id']==oid]
        assert ss and all(b['scene_time_s']>a['scene_time_s'] for a,b in zip(ss,ss[1:]))
        assert abs(ss[-1]['scene_time_s']-manifest['duration_s'])<1e-8
    for s in states:
        assert s['object_id'] in ids and s['scene_id']==manifest['id']
        expected=(s['frame']-manifest['start_frame'])*manifest['fps_base']/manifest['fps']
        assert abs(s['scene_time_s']-expected)<1e-8
    for e in events:
        assert set(e['pair'])<=ids and e['scene_id']==manifest['id']
        assert e['onset_s']+e['duration_s']<=manifest['duration_s']+1e-8
    config=json.loads((root/'config.json').read_text())
    specs=recipe(config['recipe_id'],config['seed'],config['variant'])
    grouped={spec['object_id']:[s for s in states if s['object_id']==spec['object_id']] for spec in specs}
    for spec in specs:
        for state in grouped[spec['object_id']]:
            expected=position(spec,state['scene_time_s']/manifest['duration_s'])
            assert norm(sub(state['transform']['position_m'],expected))<1e-4, 'trajectory mismatch'
    certified=set()
    for a,b in itertools.combinations(specs,2):
        samples=[(x['scene_time_s'],x['transform']['position_m'],y['transform']['position_m'])
                 for x,y in zip(grouped[a['object_id']],grouped[b['object_id']])]
        _,derived=pair_timeline(a,b,samples)
        certified.update((tuple(sorted([a['object_id'],b['object_id']])),e['onset_s'])
                         for e in derived if e['event_type']=='near_miss')
    for event in events:
        if event['event_type']=='near_miss':
            assert (tuple(event['pair']),event['onset_s']) in certified, 'uncertified continuous near miss'
    video='NOT_RUN'
    if manifest['render_hash']:
        assert digest(root/'preview.mp4')==manifest['render_hash']
        proc=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0',
              '-show_entries','stream=nb_read_frames,duration','-of','json',str(root/'preview.mp4')],
              capture_output=True,text=True,timeout=30,check=True)
        stream=json.loads(proc.stdout)['streams'][0]
        expected=round(manifest['duration_s']*manifest['fps']/manifest['fps_base'])
        assert int(stream['nb_read_frames'])==expected
        assert abs(float(stream['duration'])-manifest['duration_s'])<.01
        video='FRAME_COUNT_DURATION_HASH_PASSED'
    return dict(status='PASSED',canonical_records=1+len(states)+len(events),video=video,
                visual_qa='SEPARATE_REVIEW_REQUIRED',physical_impact_validation='NOT_CLAIMED',
                evaluated_trajectory='PASSED',continuous_near_miss_certificate='PASSED')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('bundle',type=Path)
    print(json.dumps(validate_bundle(p.parse_args().bundle),indent=2))
