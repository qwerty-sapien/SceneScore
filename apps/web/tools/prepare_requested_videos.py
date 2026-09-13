"""Prepare requested Blender directions with bound editable music/Foley. C is excluded."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import shutil
import numpy as np
from modules.arranger.core import Context, baseline, compile_preview, encoded
from modules.blender.production.export import _transform
from modules.blender.production.playback import create_playback_window
from modules.music.catalog import get_composition, get_groove
from scenescore.contracts import validate

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'apps/web/public/requested-animations'
EVIDENCE = ROOT/'artifacts/direction-music'
VERSION = 'direction-replay-music-1'
SOURCES = [
 ('06-three-ways-down', '6 — Three Ways Down', '06_three_ways_down-v4', ['sphere','cylinder','hoop']),
 ('08-spiral-observatory', '8 — Spiral Observatory', '08_spiral_observatory-v3', ['bead']),
 ('18-billiard-greenhouse', '18 — The Billiard Greenhouse', '18_billiard_greenhouse-v3', ['ceramic-puck']),
]

def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(path, data): path.write_bytes(encoded(data))

def camera_transform(camera):
    # Fixed -Z tracking, Y-up basis used by the Blender builder.
    p=np.array(camera['position'],dtype=float)
    z=p-np.array(camera['look_at'],dtype=float); z/=np.linalg.norm(z)
    x=np.cross([0.,0.,1.],z); x/=np.linalg.norm(x)
    m=np.column_stack([x,np.cross(z,x),z]); w=math.sqrt(1+np.trace(m))/2
    q=[(m[2,1]-m[1,2])/(4*w),(m[0,2]-m[2,0])/(4*w),(m[1,0]-m[0,1])/(4*w),w]
    return _transform(dict(position_m=p.tolist(),quaternion_xyzw=q,scale=[1,1,1]))

def inputs(name, folder, leads):
    source=ROOT/'artifacts/blender/revamp/directions'/folder
    packet=json.loads((source/'packet.json').read_text())
    geometry=json.loads((source/'evaluated_geometry.json').read_text())
    replay=[json.loads(s) for s in (source/'replay_states.jsonl').read_text().splitlines()]
    video_hash=sha((source/'renders/video.mp4').read_bytes())
    check=json.loads((source/'media_validation.json').read_text())
    assert check['status']=='PASSED' and check['video_sha256']==video_hash
    hashes={p:sha((source/p).read_bytes()) for p in ['packet.json','replay_states.jsonl','evaluated_geometry.json','scene.blend','media_validation.json']}
    config=dict(version=VERSION,scored_objects=leads,sample_stride=8,source_hashes=hashes,
      event_rule='Recorded contact/recontact/compliant-contact onsets only; near misses have no Foley; recoil/checkpoint/latch/settled markers are not impacts.',
      timing='Unquantized solver timestamps. Rolling precision 1/240 s; puck substeps 1/1920 s.',
      kinematics='Causal 240 Hz replay centre differences, sampled at 30 Hz for scoring.',
      scope='Original stylized wood-like contact cues, not measured material acoustics. Supports omitted from musical state stream.')
    prov=dict(source_mode='synthetic',creator=VERSION,tool_version=VERSION,config_hash=sha(encoded(config)),input_hashes=list(hashes.values()),seed=42)
    sid=name+':'+hashes['packet.json'][:16]
    def record(kind,ident,**fields):
        return dict(kind=kind,schema_version='0.1',id=ident,provenance=deepcopy(prov),**fields)
    raw=[]
    for index,e in enumerate(packet['events']):
        if e['type'] in ('receiver-contact','receiver-recontact'):
            actor=e['actor_id']; pair=[actor,'observatory-plunger' if actor=='bead' else actor+'-plunger']
        elif e['type'] in ('contact','compliant_contact','near_miss'): pair=e['actors']
        else: continue
        raw.append((index,e,sorted(pair)))
    known=sorted(set(leads)|{o for _,_,pair in raw for o in pair})
    scene=record('SceneManifest',sid,source_hash=hashes['scene.blend'],render_hash=video_hash,generator_version=VERSION,
      fps=30,fps_base=1,start_frame=1,duration_s=30,units='metres',up_axis='Z',handedness='right',quaternion_order='xyzw',matrix_layout='row_major_column_vectors',
      camera=dict(id='direction-camera',transform=camera_transform(packet['camera'])),
      objects=[dict(object_id=o,sonic_identity_id=('voice:' if o in leads else 'silent:')+o) for o in known])
    states=[]
    for o in leads:
        verts=np.asarray(geometry[o]['vertices_local']); initial=np.array(replay[0]['objects'][o]['scale'])
        for i in range(0,len(replay),8):
            sample=replay[i]; pose=sample['objects'][o]
            assert np.max(np.abs(np.array(pose['scale'])-initial))<1e-5,'Scored body must remain rigid'
            transform=_transform(pose); m=np.array(transform['matrix_row_major']).reshape(4,4)
            world=verts@m[:3,:3].T+m[:3,3]
            v=None if i==0 else ((np.array(pose['position_m'])-replay[i-1]['objects'][o]['position_m'])*packet['hz']).tolist()
            states.append(record('ObjectState',f'{sid}:{o}:{i:05d}',scene_id=sid,object_id=o,scene_time_s=sample['time_s'],frame=1+sample['time_s']*30,
              transform=transform,velocity_m_s=v,acceleration_m_s2=None,derivative_method='Causal backward centre difference at 240 Hz; score decimated to 30 Hz',
              bounds_min_m=world.min(axis=0).tolist(),bounds_max_m=world.max(axis=0).tolist(),surface_area_m2=geometry[o]['world_surface_area_m2'],volume_m3=None,
              unavailable_reason='Volume and acceleration not exported; initial velocity unavailable.'))
    interactions=[]; details=[]
    for index,e,pair in raw:
        t=e['time_s']; tick=min(len(replay)-1,max(1,math.floor(t*packet['hz'])))
        def position(o,i): return np.array(replay[i]['objects'].get(o,geometry[o]['transform'])['position_m'])
        a,b=(position(o,tick) for o in pair); distance=np.linalg.norm(b-a); normal=(b-a)/distance
        relative=((position(pair[1],tick)-position(pair[1],tick-1))-(position(pair[0],tick)-position(pair[0],tick-1)))*packet['hz']
        radial=float(relative@normal); ident=f'{sid}:event:{index:03d}'
        kind='near_miss' if e['type']=='near_miss' else 'contact_onset'; hard=e['type']=='contact'
        interactions.append(record('InteractionEvent',ident,scene_id=sid,pair=pair,pair_id='|'.join(pair),loop_instance=0,event_type=kind,
          onset_s=t,duration_s=0,centre_distance_m=float(distance),surface_gap_m=e.get('surface_clearance_m',0.),relative_normal_speed_m_s=radial,
          relative_tangential_speed_m_s=float(np.linalg.norm(relative-radial*normal)),method='analytic',physical_impact=hard,
          impulse_ns=e['impulse_n_s'] if hard else None,uncertainty_m=.0002))
        details.append(dict(id=ident,packet_event_index=index,source_event=e,foley_eligible=kind=='contact_onset',
          gap_semantics='Zero gap is the solver onset; near miss uses recorded positive clearance.',
          velocity_semantics='Centre radial/tangential motion; not contact-point velocity.',source_packet_sha256=hashes['packet.json']))
    roles=dict(roles_version='blender-object-roles-1',scene_id=sid,scored_object_ids=leads,
      validated_contact_ids=[e['id'] for e in interactions if e['event_type']=='contact_onset'],approval=None,event_source=VERSION,scope=config['scope'])
    evidence=EVIDENCE/name; evidence.mkdir(parents=True,exist_ok=True)
    for file,data in [('source-binding.json',config),('scene.json',scene),('event-details.json',details),('interactions.json',interactions)]: write(evidence/file,data)
    return source,scene,states,interactions,roles

def piano_edition(b,leads):
    source_hash=sha(encoded(b)); plan=json.loads(b['plan_bytes']); plan['id']+=':direction-piano-v1'; events=[]
    for original in b['events']:
        e=deepcopy(original)
        if e['resolved_time_s']>=30: continue
        if e['event_type']=='brush':
            if e['articulation']=='sweep' or 'sustain' in e['articulation']: continue
            e['dynamics_db']-=18
        elif e['event_type']=='foley': e.update(instrument_id='scene_wood_contact_v1',timbre_id='wood-low',duration_s=.12)
        elif e['instrument_id']=='keyboard_damped_v1':
            e.update(instrument_id='scene_piano_v1',timbre_id='scene_piano_v1')
            if e['object_id'] in leads:
                vi=leads.index(e['object_id'])
                if len(leads)==3:
                    ni=int(e['id'].rsplit(':',1)[1])
                    if ni%3!=vi: continue
                    e['midi_pitch']=max(plan['register_min'],min(plan['register_max'],e['midi_pitch']+[0,-12,12][vi]))
                e['articulation']=['detached','legato','staccato'][vi] if len(leads)==3 else ('legato' if leads==['bead'] else 'detached')
        e['duration_s']=min(e['duration_s'],30-e['resolved_time_s']); e['plan_id']=plan['id']; validate(e); events.append(e)
    content=encoded([{k:v for k,v in e.items() if k!='plan_id'} for e in events])
    mix=dict(version='scene-piano-mix-1',voice_version='scene-piano-voices-1',default_gain_db=-6,source_bundle_sha256=source_hash,
      events_content_sha256=sha(content),brush_attenuation_db=18,approval=None,label='Draft · piano, bass, quiet brush taps and scene-timed contact effects')
    mb=encoded(mix); plan['palette_ids']=sorted({e['instrument_id'] for e in events})
    plan['provenance'].update(creator=VERSION,tool_version=VERSION,config_hash=sha(mb),input_hashes=[b['scene_hash'],b['composition_hash'],source_hash,sha(mb)])
    plan['uncertainties']+=['Stylized contact sound, not acoustic material simulation.','Race voices alternate written notes with distinct registers/articulations; human audition pending.']
    validate(plan); eb=encoded(events); window,wh=create_playback_window(eb,30)
    b.update(events=events,events_bytes=eb.decode(),source_events_bytes=eb.decode(),events_sha256=sha(eb),plan_bytes=encoded(plan).decode(),plan_sha256=sha(encoded(plan)),
      playback_window=window,playback_window_bytes=encoded(window).decode(),playback_window_sha256=wh,piano_mix=mix,piano_mix_bytes=mb.decode(),piano_mix_sha256=sha(mb),
      piano_event_bytes=content.decode(),approval=None,label=mix['label'])
    return b

def main():
    OUT.mkdir(exist_ok=True); entries=[]
    for name,title,folder,leads in SOURCES:
        source,scene,states,interactions,roles=inputs(name,folder,leads)
        shutil.copy2(source/'renders/video.mp4',OUT/(name+'.mp4'))
        for gid in ['brush_swing_light_v1','brush_ballad_sparse_v1','brush_straight_rag_v1']:
            c=deepcopy(get_composition('tilted_blue_v1')); c['groove_id']=gid; g=get_groove(gid)
            playback=dict(version='scene-playback-window-1',start_s=0,duration_s=30,final_fade_s=.01,render_fps=30)
            ctx=Context(scene,states,interactions,c,g,role_supplement=roles,playback_policy=playback)
            plan=baseline(ctx); events=compile_preview(ctx,plan); ident=name+'-'+gid
            b=dict(version='studio-bundle-1',id=ident,title=title,variant=name,video=name+'.mp4',video_sha256=scene['render_hash'],
              plan_bytes=encoded(plan).decode(),plan_sha256=sha(encoded(plan)),scene_hash=ctx.scene_hash,composition_hash=ctx.composition_hash,
              scene=scene,composition=c,groove=g,states=states,interactions=interactions,events=events,events_sha256=sha(encoded(events)),source='SYNTHETIC_TEST',audition_status='AUDITION_PENDING',
              role_supplement=roles,playback_policy=playback,scene_input_bytes=encoded(ctx.scene_inputs).decode(),composition_input_bytes=encoded(dict(composition=c,groove=g)).decode(),
              animation_label='Blender physics · recorded motion and contacts',approval=None)
            write(EVIDENCE/name/(ident+'-source.json'),b); b=piano_edition(b,leads); write(OUT/(ident+'.json'),b)
            entries.append(dict(id=ident,title=title,variant=name,groove=gid,url=ident+'.json',sha256=sha(encoded(b)),arrangement='clean-piano',composition=c['title']))
        print(json.dumps(dict(video=name,states=len(states),contact_effects=sum(e['event_type']=='contact_onset' for e in interactions),grooves=3)),flush=True)
    write(OUT/'catalog.json',dict(version='studio-catalog-1',entries=entries))
    (OUT/'c.mp4').unlink(missing_ok=True)  # Only this task's former public copy, never original C.mp4.

if __name__=='__main__': main()
