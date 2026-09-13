import type { ArrangementPlan, CompositionSpec, BrushGroove, ObjectState, SceneManifest, InteractionEvent, ScoreEvent, Approval, ControlAction } from '../contracts/generated';
import {validate} from '../contracts/validate';
import verticalTable from '../../modules/music/fixtures/transition-table-v1.json';
import {musicalInputBytes} from './vertical-binding';
import {verifyBlenderInputs,type BlenderInputs} from './blender-inputs';
import {verifyRiffs,type RiffBinding} from './riff-binding';
export type MotionControlTrack={clock:'scene';epoch:string;duration_s:number;events:{id:string;feature:string;start_s:number;end_s:number;driver:number|null;intent:string;values:Record<string,number>}[];provenance?:unknown};
export type Bundle=BlenderInputs&RiffBinding&{version:'studio-bundle-1';id:string;title:string;variant:string;video:string;video_sha256:string;plan_bytes:string;plan_sha256:string;scene_hash:string;composition_hash:string;scene:SceneManifest;composition:CompositionSpec;groove:BrushGroove;states:ObjectState[];interactions:InteractionEvent[];events:ScoreEvent[];events_sha256:string;source:string;audition_status:string;music_vertical?:VerticalTransitionSidecar;
 holds?:readonly {start_s:number;end_s:number}[];control_track?:MotionControlTrack;
 events_bytes?:string;scene_input_bytes?:string;composition_input_bytes?:string;
 role_supplement?:unknown;playback_policy?:unknown;animation_label?:string;
 mapping_binding_bytes?:string;control_track_input_bytes?:string;holds_bytes?:string;
 mapping_provenance?:{binding_sha256:string;binding:{control_track_sha256:string;holds_sha256:string;mapped_musical_sha256:string}}};
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
 const verifyBytes=async(payload:string|undefined,expectedHash:string,value:unknown,label:string)=>{
  if(payload!==undefined&&(await sha(new TextEncoder().encode(payload))!==expectedHash||stable(JSON.parse(payload))!==stable(value)))throw Error(`${label} bytes mismatch`);
 };
 await verifyBytes(b.events_bytes,b.events_sha256,b.events,'Score');
 await verifyBlenderInputs(b,p,sha,stable);
 await verifyRiffs(b,p,sha,stable);
 const sceneInputs={scene:b.scene,states:[...b.states].sort((a,c)=>a.id<c.id?-1:a.id>c.id?1:0),interactions:[...b.interactions].sort((a,c)=>a.id<c.id?-1:a.id>c.id?1:0),
  ...(b.role_supplement==null?{}:{role_supplement:b.role_supplement}),...(b.playback_policy==null?{}:{playback_policy:b.playback_policy}),
  ...(b.music_handoff_binding==null?{}:{music_handoff_binding:b.music_handoff_binding})};
 await verifyBytes(b.scene_input_bytes,b.scene_hash,sceneInputs,'Scene');
 await verifyBytes(b.composition_input_bytes,b.composition_hash,{composition:b.composition,groove:b.groove},'Composition');
 if(b.music_vertical||b.control_track){
  const binding=b.mapping_provenance;
  if(b.music_vertical&&(!b.scene_input_bytes||!b.composition_input_bytes))throw Error('Unbound vertical scene or composition');
  if(!binding||!b.events_bytes||!b.control_track||!b.mapping_binding_bytes||!b.control_track_input_bytes||!b.holds_bytes||!b.holds||
   !p.provenance.input_hashes.includes(binding.binding_sha256)||b.control_track.clock!=='scene'||
   b.control_track.epoch!==b.scene.id||b.control_track.duration_s!==b.scene.duration_s)throw Error('Unbound music control track');
  const {provenance:_provenance,...track}=b.control_track;
  await verifyBytes(b.mapping_binding_bytes,binding.binding_sha256,binding.binding,'Mapping');
  await verifyBytes(b.control_track_input_bytes,binding.binding.control_track_sha256,track,'Control track');
  await verifyBytes(b.holds_bytes,binding.binding.holds_sha256,b.holds,'Hold');
  if(await sha(musicalInputBytes(b.events_bytes))!==binding.binding.mapped_musical_sha256)throw Error('Plan-bound musical content mismatch');
 }
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
export async function verifyApproval(payload:string,a:Approval,b:Bundle){validate(a);const p=validate(JSON.parse(payload)) as ArrangementPlan;if(a.decision!=='approved'||a.plan_id!==p.id||a.approved_payload_sha256!==await sha(new TextEncoder().encode(payload))||stable(a.input_hashes)!==stable([b.scene_hash,b.composition_hash])||p.scene_hash!==b.scene_hash||p.composition_hash!==b.composition_hash)throw Error('Stale or unapproved plan');if(b.sound_design&&p.provenance.config_hash!==b.sound_design_sha256)throw Error('Stale sound design approval');return p;}
export function keyboardAction(p:ArrangementPlan,planHash:string,epoch:string,now:number,sign:number,mode:Mode,gain=-18):ControlAction{
 const id=crypto.randomUUID(),lanes={master_gain_db:gain,articulation:'score',expression_preset:'neutral'};
 const a:ControlAction={kind:'ControlAction',schema_version:'0.1',id,provenance:{...copy(p.provenance),source_mode:mode==='KEYBOARD'?'keyboard':mode==='SYNTHETIC_TEST'?'synthetic':mode==='REAL_REPLAY'?'replay':'real_device'},gesture_id:id,sequence_id:id,gesture_count:2,profile:'double_modulate_mvp',action:sign?'request_modulation':'none',request:{clock:'audio',epoch,seconds:now},expires:{clock:'audio',epoch,seconds:now+6},boundary:'next_approved_bar_or_phrase',signed_semitones:sign as -2|2,scene_policy_id:p.motion_policy.id,approved_plan_hash:planHash,status:sign?'queued':'suppressed',reason:sign?null:'stationary_world_z',quality:{state:'good',reason:null},before:lanes,after:{...lanes}};
 if(!sign)a.signed_semitones=0;validate(a);return a;
}

// Opt-in music vertical. Keep legacy transition() unchanged for frozen golden parity.
export const VERTICAL_TRANSITION_VERSION='music-vertical-transitions-2' as const;
export const VERTICAL_TABLE_SHA256='abc0f83a5cadfbc7919d8c6e75731e52f8fe6d8af70f30078ebb3f5e932a00ba';
export const VERTICAL_LANES=['bass','harmony-0','harmony-1','harmony-2'] as const;
export type VerticalTransitionSidecar={
 version:typeof VERTICAL_TRANSITION_VERSION;table_id:'scenescore-transition-table';table_version:'1';
 table_sha256:string;eligible_arrival_ticks:number[];jazz_enabled:false;audition_status:'AUDITION_PENDING';approval:null;
};
export type VerticalSlot={offset_ticks:number;root_pc:number;quality:string;pitches:readonly number[]};
export type VerticalEntry={key:string;tier:'contract_default'|'auditioned_jazz';gesture_id:string;
 from_pc:number;to_pc:number;signed_semitones:number;lead_bars:number;lead_ticks:number;
 acknowledgement:string;slots:readonly VerticalSlot[]};
export type VerticalProgram={id:string;entry:VerticalEntry;from_pc:number;to_pc:number;
 start_s:number;arrival_s:number;end_s:number;arrival_tick:number;events:readonly ScoreEvent[];
 acknowledgement:readonly ScoreEvent[]};
export type PreparedVerticalTransitions={entries:ReadonlyMap<string,VerticalEntry>;
 programs:ReadonlyMap<string,VerticalProgram>;variants:ReadonlyMap<string,ReadonlyMap<number,ScoreEvent>>;
 variant_origins:ReadonlyMap<string,string>;register_min:number;register_max:number;
 acknowledgements:readonly ScoreEvent[];arrivals:readonly {tick:number;at:number}[];
 bar_seconds:number;initial_tonic:number;affected_ids:ReadonlySet<string>};
type TableRow=(typeof verticalTable.resolved)[number];
const verticalKey=(tier:string,pc:number,delta:number,lead:number)=>`${tier}:${pc}:${delta}:${lead}`;
const affected=(e:ScoreEvent)=>e.event_type==='note'&&e.midi_pitch!==null&&(VERTICAL_LANES as readonly string[]).includes(e.lane_id);
export const isVerticalVoice=affected;

function voicingCandidates(s:TableRow['slots'][number],lo:number,hi:number):number[][]{
 let upperLo=Math.max(lo,52),upperHi=Math.min(hi,80);if(upperHi-upperLo<12){upperLo=lo;upperHi=hi;}
 const notes:number[]=[],roots:number[]=[];for(let p=upperLo;p<=upperHi;p++)if(s.pitch_classes.includes(p%12))notes.push(p);
 for(let p=lo;p<=Math.min(hi,52);p++)if(p%12===s.root_pc)roots.push(p);
 if(!roots.length)for(let p=lo;p<=hi;p++)if(p%12===s.root_pc)roots.push(p);
 const result:number[][]=[],defining:Record<string,number[]>={dom7:[4,10],dom7b5:[4,6,10],min7:[3,10],maj69:[4,9],dim7:[3,6,9]};
 const required=defining[s.quality].map(interval=>(s.root_pc+interval)%12);
 for(let a=0;a<notes.length;a++)for(let b=a+1;b<notes.length;b++)for(let c=b+1;c<notes.length;c++){
  const pcs=[notes[a]%12,notes[b]%12,notes[c]%12];
  if(notes[c]-notes[a]>16||new Set(pcs).size!==3||!required.every(pc=>pcs.includes(pc)))continue;
  for(const bass of roots)if(bass<notes[a])result.push([bass,notes[a],notes[b],notes[c]]);
 }return result;
}
function validVoicingPair(a:readonly number[],b:readonly number[]){
 if(a.slice(1).some((p,i)=>Math.abs(p-b[i+1])>3))return false;
 return !((a[3]-a[0])%12===7&&(b[3]-b[0])%12===7&&(b[0]-a[0])*(b[3]-a[3])>0);
}
function pathCompare(a:readonly number[][],b:readonly number[][]){for(let i=0;i<a.length;i++)for(let j=0;j<4;j++){const d=a[i][j]-b[i][j];if(d)return d;}return 0;}
function voiceVerticalRow(row:TableRow,lo:number,hi:number):number[][]{
 const options=row.slots.map(s=>voicingCandidates(s,lo,hi)),target=[40,60,64,67];
 let paths=options[0].map(v=>({v,cost:v.reduce((n,p,i)=>n+Math.abs(p-target[i]),0),path:[v]}));
 for(const choices of options.slice(1)){
  const next:typeof paths=[];
  for(const v of choices){let best:(typeof paths)[number]|undefined;
   for(const prev of paths){if(!validVoicingPair(prev.v,v))continue;
    const held=v.slice(1).filter((p,i)=>p===prev.v[i+1]).length;
    const cost=prev.cost+v.reduce((n,p,i)=>n+Math.abs(p-prev.v[i]),0)-12*held,path=[...prev.path,v];
    if(!best||cost<best.cost||(cost===best.cost&&pathCompare(path,best.path)<0))best={v,cost,path};
   }if(best)next.push(best);
  }paths=next;
 }
 if(!paths.length)throw Error('transition_register_has_no_voice_leading');
 paths.sort((a,b)=>a.cost-b.cost||pathCompare(a.path,b.path));return paths[0].path;
}

/** Bounded voice-leading search is preparation work, never called by submit. */
export function prepareVerticalTable(lo=28,hi=96):ReadonlyMap<string,VerticalEntry>{
 if(!Number.isInteger(lo)||!Number.isInteger(hi)||lo<0||lo>=hi||hi>127)throw Error('Invalid transition register');
 const entries=new Map<string,VerticalEntry>();
 for(const row of verticalTable.resolved){
  const tier=(Object.keys(verticalTable.tiers) as VerticalEntry['tier'][]).find(name=>{
   const spec=verticalTable.tiers[name];return spec.eligible_signed_semitones.includes(row.signed_semitones)&&
    (spec.gesture_by_lead_bars as Record<string,string>)[String(row.lead_bars)]===row.gesture_id;
  });
  if(!tier)throw Error('Unindexed transition');const key=verticalKey(tier,row.from_pc,row.signed_semitones,row.lead_bars);
  if(entries.has(key)||row.to_pc!==(row.from_pc+row.signed_semitones+12)%12)throw Error('Invalid transition key');
  const voices=voiceVerticalRow(row,lo,hi);
  const slots=row.slots.map((s,i)=>Object.freeze({offset_ticks:s.offset_ticks,root_pc:s.root_pc,quality:s.quality,pitches:Object.freeze(voices[i])}));
  entries.set(key,Object.freeze({key,tier,gesture_id:row.gesture_id,from_pc:row.from_pc,to_pc:row.to_pc,
   signed_semitones:row.signed_semitones,lead_bars:row.lead_bars,lead_ticks:row.lead_ticks,
   acknowledgement:(verticalTable.gestures as Record<string,{acknowledgement:string}>)[row.gesture_id].acknowledgement,
   slots:Object.freeze(slots)}));
 }
 if(entries.size!==216)throw Error('Unsupported transition table');return entries;
}
/** Both tiers load for audit. Jazz cannot execute in this unauditioned edition. */
export function lookupVerticalTransition(entries:ReadonlyMap<string,VerticalEntry>,pc:number,delta:number,lead:number,tier='contract_default'){
 if(tier!=='contract_default')throw Error('jazz_audition_required');
 const entry=entries.get(verticalKey(tier,pc,delta,lead));if(!entry)throw Error('transition_not_prepared');return entry;
}

/** Constructor/unlock-only preparation. Memory is bounded independently of playback. */
export function prepareVerticalTransitions(b:Bundle,p:ArrangementPlan):PreparedVerticalTransitions{
 const side=b.music_vertical,c=b.composition,barTicks=c.ppq*4*c.meter[0]/c.meter[1];
 if(!side||side.version!==VERTICAL_TRANSITION_VERSION||side.table_id!==verticalTable.id||side.table_version!=='1'||
  side.jazz_enabled!==false||side.approval!==null||side.audition_status!=='AUDITION_PENDING'||side.table_sha256!==VERTICAL_TABLE_SHA256)throw Error('Unsupported vertical transition sidecar');
 if(c.ppq!==verticalTable.ppq||c.meter[0]!==4||c.meter[1]!==4||c.tempo_map.length!==1||
  b.events.length>5000||b.scene.duration_s>120||!side.eligible_arrival_ticks.length||side.eligible_arrival_ticks.length>48)throw Error('Vertical transition preparation budget');
 const barSeconds=seconds(c,barTicks),secondsPerTick=barSeconds/barTicks;
 if(!Number.isFinite(barSeconds)||barSeconds<=0||Math.abs(seconds(c,c.length_ticks)-b.scene.duration_s)>1e-6)throw Error('Invalid vertical timing');
 const arrivals=side.eligible_arrival_ticks.map((tick,i)=>{
  if(!Number.isInteger(tick)||tick<=0||tick>=c.length_ticks||tick%barTicks||
   (i>0&&tick<=side.eligible_arrival_ticks[i-1])||seconds(c,tick)>=b.scene.duration_s)throw Error('Invalid vertical arrival');
  return Object.freeze({tick,at:seconds(c,tick)});
 });
 const edges=[0,...arrivals.map(a=>a.at),b.scene.duration_s];
 if(edges.slice(1).some((at,i)=>at-edges[i]>4+1e-9))throw Error('Vertical arrival coverage gap');
 const entries=prepareVerticalTable(p.register_min,p.register_max),programs=new Map<string,VerticalProgram>();
 const variants=new Map<string,ReadonlyMap<number,ScoreEvent>>(),origins=new Map<string,string>(),initial=c.key_map[0].tonic_pc,affectedIds=new Set<string>();
 const voices=new Map<string,ScoreEvent[]>();for(const lane of VERTICAL_LANES)voices.set(lane,[]);
 for(const event of b.events){if(!affected(event))continue;affectedIds.add(event.id);voices.get(event.lane_id)!.push(event);
  if(affectedIds.size>512)throw Error('Vertical harmonic variant budget');
  const pitches=new Map<number,ScoreEvent>();origins.set(event.id,event.id);
  for(let pitch=p.register_min;pitch<=p.register_max;pitch++){
   const variant=pitch===event.midi_pitch?event:Object.freeze({...event,id:`${event.id}:mv:p${pitch}`,midi_pitch:pitch});
   pitches.set(pitch,variant);origins.set(variant.id,event.id);
  }variants.set(event.id,pitches);
 }
 for(const rows of voices.values()){rows.sort((a,b)=>a.resolved_time_s-b.resolved_time_s);if(!rows.length)throw Error('Missing vertical harmonic voice');}
 const reference=(lane:string,at:number)=>{const rows=voices.get(lane)!;let ref=rows[0];for(const e of rows){if(e.resolved_time_s>at)break;ref=e;}return ref;};
 const acks=new Map<string,readonly ScoreEvent[]>();
 for(const entry of entries.values()){
  if(entry.tier!=='contract_default')continue;
  if(!p.transitions.some(t=>t.from_pc===entry.from_pc&&t.signed_semitones===entry.signed_semitones&&t.to_pc===entry.to_pc))continue;
  const first=entry.slots[0],guideIntervals=first.quality==='min7'?[3,10]:[4,10];
  const guidePitches=guideIntervals.map(interval=>first.pitches.slice(1).find(pitch=>pitch%12===(first.root_pc+interval)%12));
  if(guidePitches.some(pitch=>pitch===undefined))throw Error('Declared guide-tone dyad unavailable');
  const ack=Object.freeze([1,2].map((v)=>Object.freeze({...reference(VERTICAL_LANES[v],0),id:`${entry.key}:ack:${v}`,
   start_tick:0,duration_ticks:Math.max(1,Math.round(.12/secondsPerTick)),resolved_time_s:0,duration_s:.12,
   midi_pitch:guidePitches[v-1]!,velocity:Math.min(60,reference(VERTICAL_LANES[v],0).velocity),
   phrasing:`transition-ack:${entry.gesture_id}`})));
  acks.set(entry.key,ack);
  for(const arrival of arrivals){
   const start=arrival.at-entry.lead_ticks*secondsPerTick;if(start<0||arrival.at-entry.lead_bars*barSeconds<0)continue;
   const end=Math.min(b.scene.duration_s,arrival.at+barSeconds/4),id=`${arrival.tick}:${entry.key}`,events:ScoreEvent[]=[];
   for(let s=0;s<entry.slots.length;s++){
    const slot=entry.slots[s],at=arrival.at+slot.offset_ticks*secondsPerTick;
    const until=s+1<entry.slots.length?arrival.at+entry.slots[s+1].offset_ticks*secondsPerTick:end;
    for(let v=0;v<4;v++){const ref=reference(VERTICAL_LANES[v],at);events.push(Object.freeze({...ref,id:`${id}:slot:${s}:${v}`,
     start_tick:arrival.tick+slot.offset_ticks,duration_ticks:Math.round((until-at)/secondsPerTick),resolved_time_s:at,
     duration_s:until-at,midi_pitch:slot.pitches[v],phrasing:s===entry.slots.length-1?'new-tonic-arrival':`transition:${entry.gesture_id}`}));}
   }
   if(events.length+ack.length>24)throw Error('Vertical transition event budget');
   programs.set(id,Object.freeze({id,entry,from_pc:entry.from_pc,to_pc:entry.to_pc,start_s:start,arrival_s:arrival.at,
    end_s:end,arrival_tick:arrival.tick,events:Object.freeze(events),acknowledgement:ack}));
  }
 }
 return Object.freeze({entries,programs,variants,variant_origins:origins,register_min:p.register_min,register_max:p.register_max,acknowledgements:Object.freeze([...acks.values()].flat()),
  arrivals:Object.freeze(arrivals),bar_seconds:barSeconds,initial_tonic:initial,affected_ids:affectedIds});
}

/** At most 48 arrivals × 3 fixed lead options; table access itself is O(1).
 * Returns an existing program and allocates no score-sized data. */
export function selectVerticalTransition(prepared:PreparedVerticalTransitions,fromPc:number,sign:number,sceneNow:number,
 expiresScene:number,margin=.175):VerticalProgram|undefined{
 if(![sceneNow,expiresScene,margin].every(Number.isFinite)||margin<.02)return undefined;
 for(const arrival of prepared.arrivals){
  if(arrival.at>=expiresScene)break;const available=arrival.at-sceneNow-margin;
  for(const lead of [2,1,.5]){
   if(lead*prepared.bar_seconds>available+1e-9)continue;
   const program=prepared.programs.get(`${arrival.tick}:${verticalKey('contract_default',fromPc,sign,lead)}`);
   if(program&&program.start_s>=sceneNow+margin-1e-9)return program;
  }
 }return undefined;
}

// Export-only fragments retain their prepared identity without extending schema 0.1.
// Weak keys release this bookkeeping when the performed export is discarded.
const verticalFragmentSources=new WeakMap<ScoreEvent,ScoreEvent>();

/** Apply one signed step to the CURRENT event, preserving octave history until a bound requires folding.
 * Prepared events return cached references. Export fragments allocate only outside submit. */
export function verticalPitchVariant(prepared:PreparedVerticalTransitions,event:ScoreEvent,signedStep:number):ScoreEvent{
 if(!affected(event))return event;
 if(signedStep!==2&&signedStep!==-2)throw Error('Only declared signed steps may select pitch variants');
 const source=verticalFragmentSources.get(event),original=prepared.variant_origins.get((source??event).id),
  pitch=bound(event.midi_pitch!+signedStep,prepared.register_min,prepared.register_max);
 const result=original===undefined?undefined:prepared.variants.get(original)?.get(pitch);
 if(!result)throw Error('Current harmonic event was not prepared');
 if(!source)return result;
 const fragment={...event,id:`${event.id}:mv-step:${signedStep}`,midi_pitch:result.midi_pitch};
 verticalFragmentSources.set(fragment,result);return fragment;
}

/** Fill/export-only clipping. Never call during submit before the acknowledgement.
 * The interval is half-open so adjoining pieces neither double nor drop a sample. */
export function clipVerticalEvent(event:ScoreEvent,start:number,end:number,idSuffix='clip'):ScoreEvent|null{
 const at=Math.max(start,event.resolved_time_s),until=Math.min(end,event.resolved_time_s+event.duration_s);
 if(until<=at)return null;if(at===event.resolved_time_s&&until===event.resolved_time_s+event.duration_s)return event;
 const rate=event.duration_ticks===null?null:event.duration_ticks/event.duration_s;
 const fragment={...event,id:`${event.id}:${idSuffix}:${at}`,resolved_time_s:at,duration_s:until-at,
  start_tick:event.start_tick===null||rate===null?null:Math.round(event.start_tick+(at-event.resolved_time_s)*rate),
  duration_ticks:rate===null?null:Math.max(1,Math.round((until-at)*rate))};
 verticalFragmentSources.set(fragment,verticalFragmentSources.get(event)??event);return fragment;
}

/** An affected sustain spanning an overlay is retained before and after it.
 * The program itself provides all four harmonic voices within its interval. */
export function verticalEventFragments(prepared:PreparedVerticalTransitions,event:ScoreEvent,program:VerticalProgram):ScoreEvent[]{
 if(!affected(event))return [event];
 const before=clipVerticalEvent(event,0,program.start_s,'before');
 const after=clipVerticalEvent(verticalPitchVariant(prepared,event,program.entry.signed_semitones),program.end_s,Infinity,'after');
 return [before,after].filter((e):e is ScoreEvent=>e!==null);
}
