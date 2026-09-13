import type {ArrangementPlan,ScoreEvent,SceneManifest} from '../contracts/generated';
import {validateWindow,selectWindowEvents,type PlaybackWindow} from './window';

export type MusicHandoffBinding={version:'scene-music-input-binding-1';handoff_sha256:string;features_sha256:string;handoff_index_sha256:string};
export type RoleSupplement={scene_id:string;scored_object_ids:string[];validated_contact_ids:string[];[key:string]:unknown};
export type BlenderInputs={
 playback_window?:PlaybackWindow;playback_window_bytes?:string;playback_window_sha256?:string;
 source_events_bytes?:string;music_handoff_binding?:MusicHandoffBinding|null;
 music_handoff?:{scene_id:string;features:{sha256:string};clock:{duration_s:number;video_frame_count:number};approval:null};
 music_handoff_bytes?:string;music_handoff_sha256?:string;fixture_markers?:{type:string;time_s:number;confirmation_time_s?:number}[];label?:string;
 selection?:{selection_file:string;selection_sha256:string;variant:string;[key:string]:unknown};
};

/** Validate exact prepared bytes before audio unlock; no scoring or timing changes. */
export async function verifyBlenderInputs(b:BlenderInputs&{scene:SceneManifest;events:ScoreEvent[];events_sha256:string;scene_input_bytes?:string;role_supplement?:unknown;playback_policy?:unknown},
 plan:ArrangementPlan,sha:(bytes:BufferSource)=>Promise<string>,stable:(value:unknown)=>string){
 const exact=async(raw:string|undefined,expected:string|undefined,value:unknown,label:string)=>{
  if(typeof raw!=='string'||typeof expected!=='string'||await sha(new TextEncoder().encode(raw))!==expected||stable(JSON.parse(raw))!==stable(value))throw Error(label+' bytes mismatch');
 };
 const policy=b.playback_policy as Record<string,unknown>|null|undefined;
 if(Boolean(policy)!==Boolean(b.playback_window))throw Error('Playback policy and window must be paired');
 if(policy&&b.playback_window){
  const w=b.playback_window;
  if(stable(policy)!==stable({version:w.version,start_s:w.start_s,duration_s:w.duration_s,render_fps:w.render_fps,final_fade_s:w.final_fade_s}))throw Error('Playback policy differs from window');
 }
 if(b.playback_window){
  if(!b.scene_input_bytes)throw Error('Unbound playback scene inputs');
  await exact(b.source_events_bytes,b.events_sha256,b.events,'Original score');
  await exact(b.playback_window_bytes,b.playback_window_sha256,b.playback_window,'Playback window');
  const window=validateWindow(b.playback_window,b.scene.duration_s);
  if(window.original_events_sha256!==b.events_sha256)throw Error('Playback window source mismatch');
  selectWindowEvents(b.events,window);
 }
 if(b.role_supplement!=null){
  const roles=b.role_supplement as RoleSupplement,ids=roles.scored_object_ids;
  if(roles.scene_id!==b.scene.id||!Array.isArray(ids)||!ids.length||new Set(ids).size!==ids.length||
     ids.some(id=>!b.scene.objects.some(o=>o.object_id===id))||!ids.includes(plan.motion_policy.focus_object_id)||
     stable([...ids].sort())!==stable(plan.motif_owners.map(o=>o.object_id).sort()))throw Error('Scored role ownership mismatch');
 }
 const binding=b.music_handoff_binding;
 if(binding||b.music_handoff){
  if(!binding||binding.version!=='scene-music-input-binding-1'||!b.scene_input_bytes||
     ![binding.handoff_sha256,binding.features_sha256,binding.handoff_index_sha256].every(x=>/^[0-9a-f]{64}$/.test(x)))throw Error('Unbound music handoff');
  await exact(b.music_handoff_bytes,binding.handoff_sha256,b.music_handoff,'Music handoff');
  const handoff=b.music_handoff;
  if(!handoff||b.music_handoff_sha256!==binding.handoff_sha256||handoff.features.sha256!==binding.features_sha256||
     handoff.scene_id!==b.scene.id||handoff.clock.duration_s!==b.scene.duration_s||handoff.approval!==null||
     (b.playback_window&&handoff.clock.video_frame_count!==b.playback_window.frame_count))throw Error('Music handoff source mismatch');
 }
}
