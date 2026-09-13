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
from modules.blender.selection import selected_bundle, staged_bundle
from modules.blender.production.playback import create_playback_window


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    selection_args=parser.add_mutually_exclusive_group()
    selection_args.add_argument('--selection',type=Path)
    selection_args.add_argument('--review-selection',type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    index=[]
    candidates=([staged_bundle(args.review_selection,artifact_root=args.assets_root/'blender')] if args.review_selection else
                [selected_bundle(variant,args.selection,artifact_root=args.assets_root/'blender') for variant in ('contact','near-miss')])
    for source,selection in candidates:
        variant={'hero':'contact','near_miss':'near-miss'}.get(selection['variant'],selection['variant'])
        summary=compact_summary(source)
        states=[json.loads(s) for s in (source/'object_states.jsonl').read_text().splitlines()]
        roles=None
        if (source/'object_roles.json').is_file():
            roles=json.loads((source/'object_roles.json').read_text())
            geometry=json.loads((source/'geometry.json').read_text())
            contacts={e['id'] for e in summary['events'] if e['event_type']=='contact_onset'}
            roles={**roles,'validated_contact_ids':sorted(e['id'] for e in geometry['event_details']
                                                        if e.get('validated') and e.get('foley_eligible') and e['id'] in contacts)}
            states=[s for s in states if s['object_id'] in roles['scored_object_ids']]
        handoff=None
        handoff_binding=None
        handoff_bytes=None
        if (source/'handoff.json').is_file():
            handoff_bytes=(source/'handoff.json').read_bytes()
            handoff=json.loads(handoff_bytes)
            handoff_binding={'version':'scene-music-input-binding-1',
                             'handoff_sha256':hashlib.sha256(handoff_bytes).hexdigest(),
                             'features_sha256':hashlib.sha256((source/'features.jsonl').read_bytes()).hexdigest(),
                             'handoff_index_sha256':hashlib.sha256((source/'handoff_hashes.json').read_bytes()).hexdigest()}
            if handoff['features']['sha256']!=handoff_binding['features_sha256']:
                raise ValueError('stale_motion_feature_stream')
        playback_policy={'version':'scene-playback-window-1','start_s':0,
                         'duration_s':summary['scene']['duration_s'],'final_fade_s':.01,'render_fps':30}
        videos=list(source.glob('*.mp4'))
        if len(videos)!=1:
            raise ValueError('expected_one_verified_video')
        video=videos[0]
        video_hash=hashlib.sha256(video.read_bytes()).hexdigest()
        if summary['scene']['render_hash']!=video_hash:
            raise ValueError('stale_video_hash')
        shutil.copyfile(video,args.out/(variant+'.mp4'))
        for groove_id in ['brush_swing_light_v1','brush_ballad_sparse_v1','brush_straight_rag_v1']:
            composition=deepcopy(get_composition('tilted_blue_v1'))
            composition['groove_id']=groove_id
            groove=get_groove(groove_id)
            ctx=Context(summary['scene'],states,summary['events'],composition,groove,
                        role_supplement=roles,playback_policy=playback_policy if not selection['legacy_choreography'] else None,
                        music_handoff_binding=handoff_binding)
            plan=baseline(ctx)
            events=compile_preview(ctx,plan)
            ident=variant+'-'+groove_id
            data={'version':'studio-bundle-1','id':ident,'title':({'contact':'Projectile & tower','near-miss':'A near miss'}.get(variant,variant.replace('_',' '))),
                  'variant':variant,'video':variant+'.mp4','video_sha256':video_hash,
                  'plan_bytes':encoded(plan).decode(),'plan_sha256':hashlib.sha256(encoded(plan)).hexdigest(),
                  'scene_hash':ctx.scene_hash,'composition_hash':ctx.composition_hash,
                  'scene':ctx.scene,'composition':composition,'groove':groove,'states':states,'interactions':ctx.interactions,
                  'events':events,'events_sha256':hashlib.sha256(encoded(events)).hexdigest(),
                  'source':'SYNTHETIC_TEST','audition_status':'AUDITION_PENDING'}
            data.update(selection=selection,role_supplement=roles,playback_policy=ctx.playback_policy,
                        music_handoff_binding=handoff_binding,
                        source_events_bytes=encoded(events).decode(),events_bytes=encoded(events).decode(),approval=None,
                        composition_input_bytes=encoded({'composition':composition,'groove':groove}).decode(),
                        scene_input_bytes=encoded(ctx.scene_inputs).decode(),
                        animation_label=selection['label'])
            if not selection['legacy_choreography']:
                window,window_hash=create_playback_window(encoded(events),ctx.scene['duration_s'])
                data.update(playback_window=window,playback_window_sha256=window_hash,
                            playback_window_bytes=encoded(window).decode(),label=window['label'])
            if handoff is not None:
                data.update(music_handoff=handoff,music_handoff_bytes=handoff_bytes.decode(),
                            music_handoff_sha256=handoff_binding['handoff_sha256'],
                            fixture_markers=handoff.get('markers',[]))
            payload=encoded(data)
            (args.out/(ident+'.json')).write_bytes(payload)
            index.append({'id':ident,'title':data['title'],'variant':variant,'groove':groove_id,'url':ident+'.json','sha256':hashlib.sha256(payload).hexdigest()})
    (args.out/'catalog.json').write_bytes(encoded({'version':'studio-catalog-1','entries':index}))
    print(json.dumps({'status':'prepared','entries':len(index),'output':str(args.out)}))


if __name__=='__main__':
    main()
