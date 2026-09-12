import type { ArrangementPlan, CompositionSpec, BrushGroove, ObjectState, SceneManifest, InteractionEvent, ScoreEvent, Approval, ControlAction } from '../contracts/generated';
import {validate} from '../contracts/validate';
export type Bundle={version:'studio-bundle-1';id:string;title:string;variant:string;video:string;video_sha256:string;plan_bytes:string;plan_sha256:string;scene_hash:string;composition_hash:string;scene:SceneManifest;composition:CompositionSpec;groove:BrushGroove;states:ObjectState[];interactions:InteractionEvent[];events:ScoreEvent[];events_sha256:string;source:string;audition_status:string};
export type Mode='KEYBOARD'|'SYNTHETIC_TEST'|'REAL_REPLAY'|'LIVE_MUSE';
export const copy=<T,>(value:T):T=>structuredClone(value);
export function stable(value:unknown):string {if(Array.isArray(value))return '['+value.map(stable).join(',')+']';if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stable((value as Record<string,unknown>)[k])).join(',')+'}';return JSON.stringify(value);}
export const bytes=(v:unknown)=>new TextEncoder().encode(stable(v)+'\n');
export async function sha(data:BufferSource):Promise<string>{return [...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(x=>x.toString(16).padStart(2,'0')).join('');}
export const hash=(v:unknown)=>sha(bytes(v));
export async function verifyBundle(b:Bundle,video?:ArrayBuffer){
 if(b.version!=='studio-bundle-1'||b.events.length>5000||b.states.length>30000||b.scene.duration_s>120)throw Error('Unsupported or oversized scene bundle');
 const p=validate(JSON.parse(b.plan_bytes)) as ArrangementPlan;
 [b.scene,b.composition,b.groove,...b.states,...b.interactions,...b.events].forEach(validate);
 if(await sha(new TextEncoder().encode(b.plan_bytes))!==b.plan_sha256||p.scene_hash!==b.scene_hash||p.composition_hash!==b.composition_hash)throw Error('Plan hash mismatch');
 // Python's exact serialization is preserved in the blob hash; events also undergo semantic checks.
 if(video&&await sha(video)!==b.video_sha256)throw Error('Video hash mismatch; playback locked');
 const ids=new Set(b.scene.objects.map(o=>o.object_id));
 if(b.states.some(s=>s.scene_id!==b.scene.id||!ids.has(s.object_id))||b.interactions.some(e=>e.scene_id!==b.scene.id||e.pair.some(id=>!ids.has(id))))throw Error('Unknown scene identity');
 if(p.groove_id!==b.groove.id||p.groove_version!==b.groove.catalog_version||b.composition.groove_id!==b.groove.id)throw Error('Groove mismatch');
 if(b.events.some(e=>e.plan_id!==p.id||!p.palette_ids.includes(e.instrument_id)))throw Error('Unknown score reference');
 return p;
}
export function seconds(c:CompositionSpec,tick:number){let sum=0;for(let i=0;i<c.tempo_map.length;i++){const t=c.tempo_map[i],end=c.tempo_map[i+1]?.tick??tick;sum+=Math.max(0,Math.min(tick,end)-t.tick)*60/t.bpm/c.ppq;}return sum;}
export function bound(p:number,lo:number,hi:number){while(p<lo)p+=12;while(p>hi)p-=12;if(p<lo||p>hi)throw Error('Invalid register');return p;}
export function direction(b:Bundle,p:ArrangementPlan,at:number):number{
 const policy=p.motion_policy,start=Math.max(0,at-policy.lookback_s);
 const rows=b.states.filter(s=>s.object_id===policy.focus_object_id&&s.scene_time_s<=at).sort((a,b)=>a.scene_time_s-b.scene_time_s);
 if(!rows.length||at<=start||rows[0].scene_time_s>start||at-rows.at(-1)!.scene_time_s>policy.lookback_s)return 0;
 let integral=0;for(let i=0;i<rows.length;i++){const duration=Math.max(0,Math.min(rows[i+1]?.scene_time_s??at,at)-Math.max(start,rows[i].scene_time_s));if(duration&&!rows[i].velocity_m_s)return 0;integral+=duration*(rows[i].velocity_m_s?.[2]??0);}
 const v=integral/(at-start);return Math.abs(v)<=policy.deadband_m_s?0:v>0?2:-2;
}
export function transition(events:ScoreEvent[],p:ArrangementPlan,c:CompositionSpec,tick:number,delta:number,tonic:number):ScoreEvent[]{
 if(!p.transitions.some(t=>t.from_pc===tonic&&t.signed_semitones===delta))throw Error('Transition not approved');
 const at=seconds(c,tick),arrival=seconds(c,tick+c.ppq),bar=c.ppq*4*c.meter[0]/c.meter[1],endBar=seconds(c,tick+bar),to=(tonic+delta+12)%12;
 const out=copy(events),intervals=[0,c.key_map[0].mode==='minor'?3:4,7];
 for(let i=0;i<out.length;i++){
  const e=out[i];if(e.midi_pitch===null)continue;
  if(e.resolved_time_s<at&&at<e.resolved_time_s+e.duration_s){const tail=copy(e);tail.id+=`:mod:${tick}`;tail.start_tick=tick;tail.duration_ticks=Math.max(1,e.start_tick!+e.duration_ticks!-tick);tail.resolved_time_s=at;tail.duration_s=e.resolved_time_s+e.duration_s-at;e.duration_ticks=Math.max(1,tick-e.start_tick!);e.duration_s=at-e.resolved_time_s;out.push(tail);}
  if(e.resolved_time_s>=at)e.midi_pitch=bound(e.midi_pitch+delta,p.register_min,p.register_max);
 }
 for(const e of out){if(e.midi_pitch===null||e.resolved_time_s<at||e.resolved_time_s>=endBar)continue;
  if(e.lane_id==='bass'||e.lane_id.startsWith('harmony-')){const index=e.lane_id.startsWith('harmony-')?Number(e.lane_id.at(-1)):-1;const root=e.resolved_time_s<arrival?(to+7)%12:to;const interval=index<0?0:(e.resolved_time_s<arrival?[0,4,7]:intervals)[index];e.midi_pitch=bound(Math.floor(e.midi_pitch/12)*12+root+interval,p.register_min,p.register_max);e.phrasing=e.resolved_time_s<arrival?'new-dominant':'new-tonic-arrival';}}
 for(const e of [...out]){if(e.phrasing!=='new-dominant'||!(e.resolved_time_s<arrival&&arrival<e.resolved_time_s+e.duration_s))continue;const tail=copy(e);tail.id+=':arrival';tail.start_tick=tick+c.ppq;tail.duration_ticks=e.start_tick!+e.duration_ticks!-tail.start_tick;tail.resolved_time_s=arrival;tail.duration_s=e.resolved_time_s+e.duration_s-arrival;const interval=e.lane_id.startsWith('harmony-')?intervals[Number(e.lane_id.at(-1))]:0;tail.midi_pitch=bound(Math.floor(e.midi_pitch!/12)*12+to+interval,p.register_min,p.register_max);tail.phrasing='new-tonic-arrival';e.duration_ticks=tick+c.ppq-e.start_tick!;e.duration_s=arrival-e.resolved_time_s;out.push(tail);}
 return out.sort((a,b)=>a.resolved_time_s-b.resolved_time_s||a.id.localeCompare(b.id));
}
export async function approve(plan:ArrangementPlan,reviewer:string,synthetic=false):Promise<{payload:string;approval:Approval}>{
 if(!reviewer.trim())throw Error('Reviewer is required');validate(plan);const payload=stable(plan)+'\n';
 const approval:Approval={kind:'Approval',schema_version:'0.1',id:crypto.randomUUID(),provenance:{...copy(plan.provenance),source_mode:synthetic?'synthetic':'manual_plan'},plan_id:plan.id,approved_payload_sha256:await sha(new TextEncoder().encode(payload)),input_hashes:[plan.scene_hash,plan.composition_hash],reviewer:reviewer.trim(),reviewed_at_utc:new Date().toISOString(),decision:'approved',audition_status:'AUDITION_PENDING'};validate(approval);return {payload,approval};
}
export async function verifyApproval(payload:string,a:Approval,b:Bundle){validate(a);const p=validate(JSON.parse(payload)) as ArrangementPlan;if(a.decision!=='approved'||a.plan_id!==p.id||a.approved_payload_sha256!==await sha(new TextEncoder().encode(payload))||stable(a.input_hashes)!==stable([b.scene_hash,b.composition_hash])||p.scene_hash!==b.scene_hash||p.composition_hash!==b.composition_hash)throw Error('Stale or unapproved plan');return p;}
export function keyboardAction(p:ArrangementPlan,planHash:string,epoch:string,now:number,sign:number,mode:Mode,gain=-18):ControlAction{
 const id=crypto.randomUUID(),lanes={master_gain_db:gain,articulation:'score',expression_preset:'neutral'};
 const a:ControlAction={kind:'ControlAction',schema_version:'0.1',id,provenance:{...copy(p.provenance),source_mode:mode==='KEYBOARD'?'keyboard':mode==='SYNTHETIC_TEST'?'synthetic':mode==='REAL_REPLAY'?'replay':'real_device'},gesture_id:id,sequence_id:id,gesture_count:2,profile:'double_modulate_mvp',action:sign?'request_modulation':'none',request:{clock:'audio',epoch,seconds:now},expires:{clock:'audio',epoch,seconds:now+6},boundary:'next_approved_bar_or_phrase',signed_semitones:sign as -2|2,scene_policy_id:p.motion_policy.id,approved_plan_hash:planHash,status:sign?'queued':'suppressed',reason:sign?null:'stationary_world_z',quality:{state:'good',reason:null},before:lanes,after:{...lanes}};
 if(!sign)a.signed_semitones=0;validate(a);return a;
}
