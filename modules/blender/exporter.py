"""Blender-only entrypoint. Imports bpy only when execution is requested."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

from modules.blender.geometry import area, norm, pair_timeline, sub
from modules.blender.recipes import position, recipe
from modules.blender.executables import resolve_executable

VERSION='blender-export-1.1'


def dump(path, value):
    Path(path).write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transform(matrix):
    q=matrix.to_quaternion()
    return dict(position_m=list(matrix.translation),quaternion_xyzw=[q.x,q.y,q.z,q.w],
                matrix_row_major=[v for row in matrix for v in row])


def arguments(recipe_id):
    p=argparse.ArgumentParser()
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--variant',choices=['default','near_miss','contact'],default='default')
    p.add_argument('--duration',type=float,default=30 if recipe_id.startswith('10') else 20)
    p.add_argument('--fps',type=int,default=30)
    p.add_argument('--fps-base',type=int,default=1)
    p.add_argument('--resolution',type=int,nargs=2,default=[640,360])
    p.add_argument('--substeps',type=int,default=4)
    p.add_argument('--preview',action='store_true',help='Modest 320x180 full-duration preview')
    p.add_argument('--export-only',action='store_true')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not (0<a.duration<=60 and 1<=a.fps<=32767 and 1<=a.fps_base<=1001 and
            0<a.fps/a.fps_base<=120 and
            1<=a.substeps<=16 and all(32<=x<=1920 for x in a.resolution)):
        p.error('duration/fps/resolution/substeps exceed bounded budget')
    if a.preview:
        a.resolution=[320,180]
    if a.duration*a.fps/a.fps_base < 2:
        p.error('need at least two frames')
    return a


def run(recipe_id):
    import bpy
    from mathutils import Vector
    a=arguments(recipe_id)
    out=a.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('output directory must be empty; stale bundles are never overwritten')
    out.mkdir(parents=True,exist_ok=True)
    config={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items() if k!='out'}
    config['recipe_id']=recipe_id
    config_hash=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    scene_id=recipe_id+':'+a.variant+':'+config_hash[:12]
    prov=dict(source_mode='synthetic',creator=VERSION,tool_version=bpy.app.version_string,
              config_hash=config_hash,input_hashes=[],seed=a.seed)
    def record(kind, rid, **kw):
        return dict(kind=kind,schema_version='0.1',id=rid,provenance=prov,**kw)
    specs=recipe(recipe_id,a.seed,a.variant)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'
    scene.unit_settings.scale_length=1
    scene.render.fps=a.fps
    scene.render.fps_base=a.fps_base
    count=round(a.duration*a.fps/a.fps_base)
    duration=count*a.fps_base/a.fps
    scene.frame_start=1
    scene.frame_end=count
    # Confirm supported engine dynamically; selection is never a guessed string.
    engines=list(scene.render.bl_rna.properties['engine'].enum_items.keys())
    engine=next((e for e in engines if 'EEVEE' in e),None)
    if engine is None:
        raise RuntimeError('No supported fast render engine: '+repr(engines))
    scene.render.engine=engine
    scene.render.resolution_x,scene.render.resolution_y=a.resolution
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    if hasattr(bpy.context.preferences.edit,'keyframe_new_interpolation_type'):
        bpy.context.preferences.edit.keyframe_new_interpolation_type='LINEAR'
    else:
        raise RuntimeError('Cannot verify linear keyframe insertion preference')
    def material_color(mat, rgba):
        mat.diffuse_color=rgba
        mat.use_nodes=True
        bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value=rgba
        bsdf.inputs['Roughness'].default_value=.62
    objs=[]
    for spec in specs:
        if spec['shape']=='sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=spec['radius'])
        else:
            bpy.ops.mesh.primitive_cube_add(size=2)
        obj=bpy.context.object
        obj.name=spec['object_id']
        obj['scenescore_id']=spec['object_id']
        obj['sonic_identity_id']=spec['sonic_identity_id']
        if spec['shape']=='box':
            obj.scale=spec['half']
        mat=bpy.data.materials.new(spec['object_id']+':material')
        material_color(mat,(*spec['color'],1))
        obj.data.materials.append(mat)
        for u,pos in spec['keys']:
            obj.location=pos
            obj.keyframe_insert(data_path='location',frame=1+u*count)
        action=obj.animation_data.action
        # Blender 5.2 layered actions: insertion preference does not govern Python insertion.
        for layer in action.layers:
            for strip in layer.strips:
                bag=strip.channelbag(obj.animation_data.action_slot)
                if bag is not None:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation='LINEAR'
        objs.append(obj)
    # Neutral floor is visual-only and explicitly excluded from interaction claims.
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-1.1))
    floor=bpy.context.object
    floor.name='visual_floor_not_contact_geometry'
    mat=bpy.data.materials.new('floor')
    material_color(mat,(.035,.045,.065,1))
    floor.data.materials.append(mat)
    bpy.ops.object.camera_add(location=(11,-19,12))
    camera=bpy.context.object
    camera.rotation_euler=(Vector((0,0,1.3))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'
    camera.data.ortho_scale=17
    scene.camera=camera
    for loc,power,size in [((0,-5,10),1800,8),((4,5,7),1300,7)]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        light=bpy.context.object
        light.data.energy=power
        light.data.shape='DISK'
        light.data.size=size
        light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
    # Static object labels allow frame inspection without opening Blender.
    for obj,spec in zip(objs,specs):
        bpy.ops.object.text_add()
        label=bpy.context.object
        label.data.body=spec['object_id'].split(':')[-1]
        label.data.size=.26
        label.parent=obj
        label.location=(0,-.6,1.3)
        label.rotation_euler=camera.rotation_euler
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'),check_existing=False)
    source_hash=digest(out/'scene.blend')
    code_files=sorted(Path(__file__).parent.glob('*.py'))+sorted((Path(__file__).parent/'scenes').glob('*.py'))
    dump(out/'generator.json',dict(version=VERSION,files={p.name:digest(p) for p in code_files},config=config))
    dump(out/'config.json',config)
    states=[]
    frames=[]
    static={}
    previous={}
    # Include right endpoint as audit sample only. Render is half-open [0,duration).
    for step in range(count*a.substeps+1):
        f=1+step/a.substeps
        scene.frame_set(math.floor(f),subframe=f-math.floor(f))
        deps=bpy.context.evaluated_depsgraph_get()
        t=step*a.fps_base/(a.fps*a.substeps)
        positions={}
        for obj,spec in zip(objs,specs):
            ev=obj.evaluated_get(deps)
            matrix=ev.matrix_world.copy()
            mesh=ev.to_mesh()
            mesh.calc_loop_triangles()
            vertices=[tuple(matrix@v.co) for v in mesh.vertices]
            triangles=[tuple(tr.vertices) for tr in mesh.loop_triangles]
            oid=spec['object_id']
            if oid not in static:
                static[oid]=dict(object_id=oid,sonic_identity_id=spec['sonic_identity_id'],shape=spec['shape'],
                    role=spec['role'],material_rgba=[*spec['color'],1],scale=list(matrix.to_scale()),
                    surface_area_m2=area(vertices,triangles),volume_m3=None,
                    volume_reason='watertightness/orientation not certified',
                    geometry_method='evaluated dependency graph, transformed mesh loop triangles',
                    contact_proxy='sphere' if spec['shape']=='sphere' else 'axis_aligned_box',
                    proxy_note='analytic smooth sphere bounds differ from triangulated display mesh' if spec['shape']=='sphere' else None)
            pos=tuple(matrix.translation)
            expected=position(spec,t/duration)
            if norm(sub(pos,expected))>1e-4:
                raise RuntimeError(f'evaluated trajectory mismatch {oid} at {t}: {pos} != {expected}')
            velocity=None if oid not in previous else [x/(t-previous[oid][0]) for x in sub(pos,previous[oid][1])]
            acceleration=None
            if oid in previous and previous[oid][2] is not None:
                acceleration=[x/(t-previous[oid][0]) for x in sub(velocity,previous[oid][2])]
            previous[oid]=(t,pos,velocity)
            state=record('ObjectState',f'{scene_id}:{oid}:s{step}',scene_id=scene_id,object_id=oid,
                scene_time_s=t,frame=f,transform=transform(matrix),velocity_m_s=velocity,acceleration_m_s2=acceleration,
                derivative_method=f'backward finite difference dt={a.fps_base/(a.fps*a.substeps):.12g}s; corners nondifferentiable',
                bounds_min_m=[min(v[i] for v in vertices) for i in range(3)],
                bounds_max_m=[max(v[i] for v in vertices) for i in range(3)],surface_area_m2=static[oid]['surface_area_m2'],
                volume_m3=None,unavailable_reason='volume not certified; initial derivatives unavailable')
            states.append(state)
            positions[oid]=pos
            ev.to_mesh_clear()
        frames.append((t,positions))
    events=[]
    details=[]
    pair_summaries=[]
    for sa,sb in itertools.combinations(specs,2):
        oa,ob=sa['object_id'],sb['object_id']
        pair=sorted([oa,ob])
        rows,eps=pair_timeline(sa,sb,[(t,p[oa],p[ob]) for t,p in frames])
        minimum=min(rows,key=lambda r:r['gap'])
        pair_summaries.append(dict(pair=pair,pair_id='|'.join(pair),minimum_gap_m=minimum['gap'],
                                   minimum_gap_time_s=minimum['t'],method=minimum['method']))
        for i,episode in enumerate(eps):
            sample=episode.pop('sample')
            eid=f'{scene_id}:{"|".join(pair)}:e{i}'
            # Contact geometry is scripted; it does not establish a measured rigid-body impact.
            event=record('InteractionEvent',eid,scene_id=scene_id,pair=pair,pair_id='|'.join(pair),loop_instance=0,
                         **episode,centre_distance_m=sample['distance'],surface_gap_m=sample['gap'],
                         relative_normal_speed_m_s=sample['normal'],relative_tangential_speed_m_s=sample['tangent'],
                         method='scripted',physical_impact=False,impulse_ns=None,uncertainty_m=1e-5)
            events.append(event)
            details.append(dict(id=eid,minimum_gap_time_s=sample['t'],end_s=event['onset_s']+event['duration_s'],
                                geometry_method=sample['method'],physical_dynamics='not simulated'))
    for name,values in [('object_states',states),('interactions',events)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(v,sort_keys=True,allow_nan=False)+'\n' for v in values))
    dump(out/'geometry.json',dict(geometry_version='blender-geometry-1',objects=list(static.values()),
                                 pairs=pair_summaries,event_details=details,substeps=a.substeps,
                                 end_convention='render [0,duration), audit includes right endpoint',
                                 browser_conversion='(x,y,z) Blender -> (x,z,-y) browser Y-up; determinant +1',
                                 simulation='scripted linear transforms; no dynamics solver; no impulse',
                                 contact_uncertainty='1e-5 m numeric proxy tolerance, not display mesh fidelity',
                                 substep_limit='sphere sweep exact linear; sphere/box and box/box sampled, not continuous guarantee'))
    render_hash=None
    render_status='RENDER_NOT_RUN'
    encode_status='NOT_RUN'
    if not a.export_only:
        (out/'frames').mkdir()
        scene.render.filepath=str(out/'frames'/'frame_')
        bpy.ops.render.render(animation=True)
        pngs=sorted((out/'frames').glob('*.png'))
        if len(pngs)!=count:
            raise RuntimeError('incomplete frame render')
        for label,index in [('start',0),('approach',int(count*.4)),('event',int(count*.5)),('ending',count-1)]:
            shutil.copyfile(pngs[index],out/(label+'.png'))
        render_status='FRAME_SEQUENCE_RENDERED'
        encoder=resolve_executable('ffmpeg', required=False)
        if encoder:
            command=[encoder,'-v','error','-nostdin','-n','-framerate',f'{a.fps}/{a.fps_base}',
                '-start_number','1','-i',str(out/'frames'/'frame_%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(out/'preview.mp4')]
            encoded=subprocess.run(command,capture_output=True,text=True,timeout=120)
            dump(out/'encode.json',dict(command=command,returncode=encoded.returncode,stderr=encoded.stderr))
            if encoded.returncode==0:
                render_hash=digest(out/'preview.mp4')
                encode_status='ENCODED'
            else:
                encode_status='FAILED'
    manifest=record('SceneManifest',scene_id,source_hash=source_hash,render_hash=render_hash,generator_version=VERSION,
                    fps=a.fps,fps_base=a.fps_base,start_frame=1,duration_s=duration,units='metres',up_axis='Z',
                    handedness='right',quaternion_order='xyzw',matrix_layout='row_major_column_vectors',
                    camera=dict(id='camera',transform=transform(camera.matrix_world)),
                    objects=[dict(object_id=s['object_id'],sonic_identity_id=s['sonic_identity_id']) for s in specs])
    dump(out/'manifest.json',manifest)
    summaries=[]
    for oid,geo in static.items():
        ss=[s for s in states if s['object_id']==oid]
        summaries.append(dict(geo,motion_envelope=dict(
            min_m=[min(s['transform']['position_m'][i] for s in ss) for i in range(3)],
            max_m=[max(s['transform']['position_m'][i] for s in ss) for i in range(3)],
            max_speed_m_s=max(norm(s['velocity_m_s'] or (0,0,0)) for s in ss)),
            keyframes=[ss[i] for i in sorted(set([0,len(ss)//4,len(ss)//2,3*len(ss)//4,len(ss)-1]))]))
    dump(out/'summary.json',dict(summary_version='blender-summary-1',scene=manifest,objects=summaries,
                               events=events,event_details=details,provenance=prov))
    dump(out/'qa.json',dict(export_status='EXPORTED_NOT_YET_VALIDATED',render_status=render_status,
         encode_status=encode_status,visual_qa='REVIEW_PENDING' if not a.export_only else 'NOT_RUN',
         frame_count=count if not a.export_only else 0,expected_frame_count=count,duration_s=duration,
         geometry_samples=len(states),interaction_count=len(events),blender_version=bpy.app.version_string,
         engine=engine,engines=engines,source_mode='synthetic',physical_impact_claim=False))
    files=[p for p in out.rglob('*') if p.is_file()]
    dump(out/'bundle_hashes.json',dict(hash_version='sha256-persisted-bytes-1',files={str(p.relative_to(out)):digest(p) for p in files}))
    print('SCENESCORE_EXPORT_COMPLETE',str(out),flush=True)
