"""Build bounded offline studio data from actually verified local Phase 2 assets."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from modules.arranger.core import Context, baseline, compile_preview, encoded
from modules.music.catalog import get_composition, get_groove
from modules.blender.summary import compact_summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    index=[]
    for variant,relative in [('contact','validated-hero/10_projectile_tower-default'),('near-miss','final-near-miss/10_projectile_tower-near_miss')]:
        source=args.assets_root/'blender'/relative
        summary=compact_summary(source)
        states=[json.loads(s) for s in (source/'object_states.jsonl').read_text().splitlines()]
        videos=list(source.glob('*.mp4'))
        if len(videos)!=1:raise ValueError('expected_one_verified_video')
        video=videos[0];video_hash=hashlib.sha256(video.read_bytes()).hexdigest()
        if summary['scene']['render_hash']!=video_hash:raise ValueError('stale_video_hash')
        shutil.copyfile(video,args.out/(variant+'.mp4'))
        for groove_id in ['brush_swing_light_v1','brush_ballad_sparse_v1','brush_straight_rag_v1']:
            composition=deepcopy(get_composition('tilted_blue_v1'))
            composition['groove_id']=groove_id
            groove=get_groove(groove_id)
            ctx=Context(summary['scene'],states,summary['events'],composition,groove)
            plan=baseline(ctx)
            events=compile_preview(ctx,plan)
            ident=variant+'-'+groove_id
            data={'version':'studio-bundle-1','id':ident,'title':'Projectile & tower' if variant=='contact' else 'A near miss',
                  'variant':variant,'video':variant+'.mp4','video_sha256':video_hash,
                  'plan_bytes':encoded(plan).decode(),'plan_sha256':hashlib.sha256(encoded(plan)).hexdigest(),
                  'scene_hash':ctx.scene_hash,'composition_hash':ctx.composition_hash,
                  'scene':ctx.scene,'composition':composition,'groove':groove,'states':states,'interactions':ctx.interactions,
                  'events':events,'events_sha256':hashlib.sha256(encoded(events)).hexdigest(),
                  'source':'SYNTHETIC_TEST','audition_status':'AUDITION_PENDING'}
            payload=encoded(data)
            (args.out/(ident+'.json')).write_bytes(payload)
            index.append({'id':ident,'title':data['title'],'variant':variant,'groove':groove_id,'url':ident+'.json','sha256':hashlib.sha256(payload).hexdigest()})
    (args.out/'catalog.json').write_bytes(encoded({'version':'studio-catalog-1','entries':index}))
    print(json.dumps({'status':'prepared','entries':len(index),'output':str(args.out)}))


if __name__=='__main__':main()
