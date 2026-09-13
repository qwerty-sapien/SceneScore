import type {ArrangementPlan,ControlAction,ScoreEvent} from '../contracts/generated';
import {validate} from '../contracts/validate';
import {Bundle,copy,seconds,transition,prepareVerticalTransitions,selectVerticalTransition,isVerticalVoice,verticalPitchVariant,clipVerticalEvent,type PreparedVerticalTransitions,type VerticalProgram} from './model';
export type Decision={action:ControlAction;audio_received_s:number;id:string;status:string;reason?:string;requested_scene_s:number;boundary_s?:number;boundary_tick?:number;boundary_audio_s?:number;arrival_scene_s?:number;arrival_audio_s?:number;ack_onset_audio_s?:number;progression_start_s?:number;progression_end_s?:number;progression_start_audio_s?:number;progression_end_audio_s?:number;program_id?:string;signed_semitones?:number;generation:number;source:string};
export type PlaybackSlice={event:ScoreEvent;bufferEvent:ScoreEvent;source_id:string;offset_s:number};
export type VerticalPerformance={program:VerticalProgram;decision:Decision;acknowledgements:ScoreEvent[];cancelled_at_s?:number};
export type PreparedTransitions={prepared:Map<string,ScoreEvent[]>;boundaries:{tick:number;at:number;arrival:number}[]};
function* sortPrepared(events:ScoreEvent[]):Generator<void,ScoreEvent[]>{
 let source=events,target=new Array<ScoreEvent>(events.length);
 for(let width=1;width<events.length;width*=2){for(let start=0;start<events.length;start+=2*width){const mid=Math.min(start+width,events.length),end=Math.min(start+2*width,events.length);let left=start,right=mid;for(let out=start;out<end;out++){const a=source[left],b=source[right];target[out]=right>=end||(left<mid&&(a.resolved_time_s<b.resolved_time_s||(a.resolved_time_s===b.resolved_time_s&&a.id.localeCompare(b.id)<=0)))?source[left++]:source[right++];if(out%128===0)yield;}}[source,target]=[target,source];yield;}return source;
}
export class Timeline {
 events:ScoreEvent[];original:ScoreEvent[];generation=0;position=0;playing=false;tonic:number;
 beforePending:ScoreEvent[]|null=null;previousTonic=0;
 seen=new Set<string>();sequences=new Set<string>();pending:Decision[]=[];history:Decision[]=[];lastRequest=-Infinity;
 vertical:PreparedVerticalTransitions|null=null;verticalHistory:VerticalPerformance[]=[];verticalSlices=new Map<string,PlaybackSlice>();
 private verticalEventCount=0;private verticalProgramCosts=new Map<string,number>();
 private verticalIdentity:{plan:ArrangementPlan;hash:string;side:Bundle['music_vertical']}|null=null;
 preparationReady=true;preparationError:string|null=null;prepared=new Map<string,ScoreEvent[]>();boundaries:{tick:number;at:number;arrival:number}[]=[];preparationVersion=0;
 constructor(public bundle:Bundle,public plan:ArrangementPlan,public planHash:string){this.events=copy(bundle.events);this.original=copy(bundle.events);this.tonic=bundle.composition.key_map[0].tonic_pc;this.prepareTransitions();}
 prepareTransitions(){
  if(this.bundle.music_vertical){
   if(!this.vertical||this.verticalIdentity?.plan!==this.plan||this.verticalIdentity.hash!==this.planHash||this.verticalIdentity.side!==this.bundle.music_vertical){
    const prepared=prepareVerticalTransitions(this.bundle,this.plan),holds=this.bundle.holds??[];
    if(holds.length>512||holds.some(h=>![h.start_s,h.end_s].every(Number.isFinite)||h.start_s<0||h.end_s<=h.start_s||h.end_s>this.bundle.scene.duration_s))throw Error('Invalid vertical hold budget or interval');
    // Exclude every conflicting overlay once, before playback. Submit keeps its 48 x 3 bound.
    const programs=new Map([...prepared.programs].filter(([,p])=>!holds.some(h=>h.start_s<p.end_s&&h.end_s>p.start_s)));
    this.vertical=Object.freeze({...prepared,programs});
    this.verticalProgramCosts=new Map([...programs].map(([id,program])=>[id,program.events.length+2+this.original.reduce((n,e)=>n+(isVerticalVoice(e)?[program.start_s,program.end_s].filter(at=>e.resolved_time_s<at&&at<e.resolved_time_s+e.duration_s).length:0),0)]));
    this.verticalIdentity={plan:this.plan,hash:this.planHash,side:this.bundle.music_vertical};
   }
   this.prepared.clear();this.boundaries=[];this.rebuildVerticalEvents();this.preparationVersion++;this.preparationReady=true;this.preparationError=null;return;
  }
  const c=this.bundle.composition,bar=c.ppq*4*c.meter[0]/c.meter[1];
  if(this.events.length>5000||c.length_ticks/bar>64||bar<=0)throw Error('Transition preparation budget');
  this.prepared.clear();this.boundaries=[];
  for(let tick=bar;tick+c.ppq<c.length_ticks;tick+=bar){const at=seconds(c,tick);if(at<=this.position||(this.bundle.playback_window&&seconds(c,tick+c.ppq)>=this.bundle.scene.duration_s))continue;this.boundaries.push({tick,at,arrival:seconds(c,tick+c.ppq)});for(const sign of [-2,2])if(this.plan.transitions.some(t=>t.from_pc===this.tonic&&t.signed_semitones===sign))this.prepared.set(`${tick}:${sign}`,transition(this.events,this.plan,c,tick,sign,this.tonic));}
  this.preparationVersion++;this.preparationReady=true;this.preparationError=null;
 }
 *nextPreparation(events:ScoreEvent[],tonic:number,after:number):Generator<void,PreparedTransitions>{
  const c=this.bundle.composition,bar=c.ppq*4*c.meter[0]/c.meter[1],prepared=new Map<string,ScoreEvent[]>(),boundaries:PreparedTransitions['boundaries']=[];
  if(events.length>5000||c.length_ticks/bar>64||bar<=0)throw Error('Transition preparation budget');
  for(let tick=bar;tick+c.ppq<c.length_ticks;tick+=bar){const at=seconds(c,tick);if(at<=after||(this.bundle.playback_window&&seconds(c,tick+c.ppq)>=this.bundle.scene.duration_s))continue;boundaries.push({tick,at,arrival:seconds(c,tick+c.ppq)});for(const sign of [-2,2]){if(!this.plan.transitions.some(t=>t.from_pc===tonic&&t.signed_semitones===sign))continue;const changed:ScoreEvent[]=[];for(const event of events){changed.push(...transition([event],this.plan,c,tick,sign,tonic));yield;}prepared.set(`${tick}:${sign}`,yield* sortPrepared(changed));}}
  return {prepared,boundaries};
 }
 commitPreparation(result:PreparedTransitions){this.prepared=result.prepared;this.boundaries=result.boundaries;this.preparationVersion++;this.preparationReady=true;this.preparationError=null;}
 currentTonic(){return this.vertical?this.tonic:this.pending.length?this.previousTonic:this.tonic;}
 currentChord(scene=this.position):{root_pc:number;quality:string}|null{
  if(!Number.isFinite(scene)||scene<0||scene>this.bundle.scene.duration_s)return null;
  if(this.vertical){for(const performed of this.verticalHistory){const p=performed.program,end=performed.cancelled_at_s??p.end_s;if(scene>=p.start_s&&scene<Math.min(p.end_s,end)){let slot=p.entry.slots[0];for(const candidate of p.entry.slots){const at=p.arrival_s+candidate.offset_ticks*this.vertical.bar_seconds/(this.bundle.composition.ppq*4);if(at>scene)break;slot=candidate;}return {root_pc:slot.root_pc,quality:slot.quality};}}}
  const c=this.bundle.composition,tick=scene/seconds(c,c.length_ticks)*c.length_ticks;
  const chord=c.harmony.find(h=>h.start_tick<=tick&&tick<h.start_tick+h.duration_ticks);if(!chord)return null;
  let delta=0;if(this.vertical)for(const r of this.verticalHistory)if(r.program.arrival_s<=scene&&(r.cancelled_at_s===undefined||r.cancelled_at_s>=r.program.arrival_s))delta+=r.program.entry.signed_semitones;
  if(!this.vertical){
   // The prepared harmonic bar remains current during rests between its note attacks.
   const bar=c.ppq*4*c.meter[0]/c.meter[1],barTick=Math.floor(tick/bar)*bar,start=seconds(c,barTick),end=seconds(c,barTick+bar),arrival=seconds(c,barTick+c.ppq);
   const root=this.events.find(e=>(e.lane_id==='bass'||e.lane_id==='harmony-0'||e.lane_id==='piano-comp-0')&&e.midi_pitch!==null&&e.resolved_time_s>=start&&e.resolved_time_s<end&&(e.phrasing==='new-dominant'||e.phrasing==='new-tonic-arrival'));
   if(root){const to=(root.midi_pitch!+(root.phrasing==='new-dominant'?5:0))%12;return {root_pc:scene<arrival?(to+7)%12:to,quality:scene<arrival?'major':c.key_map[0].mode==='minor'?'minor':'major'};}
   delta=this.currentTonic()-c.key_map[0].tonic_pc;
  }
  return {root_pc:(chord.root_pc+delta+1200)%12,quality:chord.quality};
 }
 verticalPending(){return this.verticalHistory.find(r=>this.pending.includes(r.decision));}
 /** Called only after acknowledgement scheduling or outside playback. */
 rebuildVerticalEvents(){
  if(!this.vertical)return;const ready=this.vertical,events:ScoreEvent[]=[],slices=new Map<string,PlaybackSlice>();
  const overlays=this.verticalHistory.filter(r=>(r.cancelled_at_s??r.program.end_s)>r.program.start_s);
  for(const original of this.original){
   if(!isVerticalVoice(original)){events.push(original);slices.set(original.id,{event:original,bufferEvent:original,source_id:original.id,offset_s:0});continue;}
   const start=original.resolved_time_s,end=start+original.duration_s;
   const cuts=[...new Set([start,end,...overlays.flatMap(r=>[r.program.start_s,Math.min(r.program.end_s,r.cancelled_at_s??Infinity)]).filter(t=>t>start&&t<end)])].sort((a,b)=>a-b);
   for(let i=1;i<cuts.length;i++){const a=cuts[i-1],b=cuts[i];
    if(overlays.some(r=>a>=r.program.start_s&&a<Math.min(r.program.end_s,r.cancelled_at_s??Infinity)))continue;
    let source=original;for(const r of overlays)if(Math.min(r.program.end_s,r.cancelled_at_s??Infinity)<=a&&r.program.arrival_s<=(r.cancelled_at_s??Infinity))source=verticalPitchVariant(ready,source,r.program.entry.signed_semitones);
    const event=clipVerticalEvent(source,a,b,`performed:${b}`);if(!event)continue;
    events.push(event);slices.set(event.id,{event,bufferEvent:source,source_id:original.id,offset_s:a-start});
   }
  }
  for(const r of overlays)for(const source of r.program.events){const event=clipVerticalEvent(source,0,r.cancelled_at_s??Infinity,`cancelled:${r.cancelled_at_s}`);if(event){events.push(event);slices.set(event.id,{event,bufferEvent:source,source_id:source.id,offset_s:0});}}
  if(events.length>5000)throw Error('Performed event budget');
  events.sort((a,b)=>a.resolved_time_s-b.resolved_time_s||a.id.localeCompare(b.id));this.events=events;this.verticalSlices=slices;this.verticalEventCount=events.length+this.verticalHistory.reduce((n,r)=>n+r.acknowledgements.length,0);
 }
 /** Editable performed score, including its explicitly recorded control dyads. No approval is created. */
 performedEvents(){
  if(!this.vertical)return this.events;
  const acks=this.verticalHistory.flatMap(r=>r.acknowledgements.map(e=>clipVerticalEvent(e,0,r.cancelled_at_s??Infinity,'ack-cancelled')).filter((e):e is ScoreEvent=>e!==null));
  return [...this.events,...acks].sort((a,b)=>a.resolved_time_s-b.resolved_time_s||a.id.localeCompare(b.id));
 }
 acknowledgeVertical(d:Decision,at:number){
  const r=this.verticalPending();if(!r||r.decision!==d)throw Error('Missing pending vertical program');
  const scene=d.requested_scene_s+at-d.audio_received_s,c=this.bundle.composition,tick=Math.round(scene/seconds(c,c.length_ticks)*c.length_ticks);
  r.acknowledgements=r.program.acknowledgement.map((e,i)=>({...e,id:`${d.id}:ack:${i}`,start_tick:tick,resolved_time_s:scene}));
  d.ack_onset_audio_s=at;this.rebuildVerticalEvents();
 }
 cancelVertical(d:Decision,reason:string){this.verticalHistory=this.verticalHistory.filter(r=>r.decision!==d);this.pending=this.pending.filter(x=>x!==d);d.status='suppressed';d.reason=reason;this.preparationReady=true;}

 get epoch(){return `transport-${this.generation}`;}
 reset(position:number,restore=false){if(!Number.isFinite(position)||position<0||position>this.bundle.scene.duration_s)throw Error('Invalid seek');
  if(this.vertical){this.advance(position);for(const d of this.pending){const r=this.verticalHistory.find(x=>x.decision===d);if(r)r.cancelled_at_s=position;d.status='cancelled_on_transport_reset';}this.pending=[];this.beforePending=null;this.generation++;this.position=position;this.playing=false;this.lastRequest=-Infinity;if(restore){this.verticalHistory=[];this.tonic=this.bundle.composition.key_map[0].tonic_pc;}this.prepareTransitions();return;}
if(this.pending.length&&this.beforePending){this.events=this.beforePending;this.tonic=this.previousTonic;}this.beforePending=null;for(const d of this.pending)d.status='cancelled_on_transport_reset';this.pending=[];this.generation++;this.position=position;this.playing=false;this.lastRequest=-Infinity;if(restore){this.events=copy(this.original);this.tonic=this.bundle.composition.key_map[0].tonic_pc;}this.prepareTransitions();}
 submit(action:ControlAction,audioNow:number,sceneNow:number,horizon=.15):Decision{
  validate(action);const d:Decision={action:copy(action),audio_received_s:audioNow,id:action.id,status:'suppressed',requested_scene_s:sceneNow,generation:this.generation,source:action.provenance.source_mode};
  const reject=(reason:string)=>{d.reason=reason;this.history.push(d);return d;};
  if(action.status==='suppressed')return reject(action.reason??'upstream_suppression');
  if(!this.playing)return reject('transport_not_playing');
  if(action.request.clock!=='audio'||action.request.epoch!==this.epoch)return reject('unmapped_or_stale_clock');
  if(action.approved_plan_hash!==this.planHash||action.scene_policy_id!==this.plan.motion_policy.id)return reject('stale_plan');
  if(action.request.seconds>audioNow+.001||action.expires.seconds<=audioNow||action.request.seconds<this.lastRequest)return reject('future_expired_or_out_of_order');
  if(this.seen.has(action.id)||this.sequences.has(action.sequence_id))return reject('duplicate');
  this.seen.add(action.id);this.sequences.add(action.sequence_id);this.lastRequest=action.request.seconds;
  if(action.gesture_count!==2||action.profile!=='double_modulate_mvp'||action.action!=='request_modulation')return reject('experimental_or_invalid_action');
  if(this.pending.length)return reject('one_pending_request_limit');
  if(!this.preparationReady)return reject(this.preparationError??'transition_preparation_pending');
  if(this.vertical){
   if(this.verticalHistory.length>=48)return reject('vertical_performance_budget');
   const program=selectVerticalTransition(this.vertical,this.tonic,action.signed_semitones!,sceneNow,sceneNow+action.expires.seconds-audioNow,horizon+.025);
   if(!program||audioNow+.02+.12>audioNow+this.bundle.scene.duration_s-sceneNow)return reject('no_feasible_boundary_before_expiry');
   if(this.verticalEventCount+(this.verticalProgramCosts.get(program.id)??5001)>5000)return reject('vertical_performance_budget');
   this.previousTonic=this.tonic;
   Object.assign(d,{status:'queued',program_id:program.id,boundary_s:program.arrival_s,boundary_tick:program.arrival_tick,boundary_audio_s:audioNow+program.arrival_s-sceneNow,arrival_scene_s:program.arrival_s,arrival_audio_s:audioNow+program.arrival_s-sceneNow,progression_start_s:program.start_s,progression_end_s:program.end_s,progression_start_audio_s:audioNow+program.start_s-sceneNow,progression_end_audio_s:audioNow+program.end_s-sceneNow,signed_semitones:action.signed_semitones!,reason:action.request.seconds<audioNow-.15?'late_deferred':undefined});
   this.verticalHistory.push({program,decision:d,acknowledgements:[]});this.pending.push(d);this.history.push(d);return d;
  }
  const boundary=this.boundaries.find(b=>b.at>=sceneNow+horizon+.025);
  if(!boundary||audioNow+boundary.arrival-sceneNow>=action.expires.seconds)return reject('no_feasible_boundary_before_expiry');
  const {tick,at,arrival}=boundary,changed=this.prepared.get(`${tick}:${action.signed_semitones}`);
  if(!changed)return reject('transition_not_prepared');
  this.preparationReady=false;this.beforePending=this.events;this.previousTonic=this.tonic;this.events=changed;this.tonic=(this.tonic+action.signed_semitones!+12)%12;
  Object.assign(d,{status:'queued',boundary_s:at,boundary_tick:tick,boundary_audio_s:audioNow+at-sceneNow,arrival_scene_s:arrival,arrival_audio_s:audioNow+arrival-sceneNow,signed_semitones:action.signed_semitones!,reason:action.request.seconds<audioNow-.15?'late_deferred':undefined});this.pending.push(d);this.history.push(d);return d;
 }
 advance(scene:number){this.position=scene;if(this.vertical){for(const d of this.pending){if(d.arrival_scene_s!<=scene){this.tonic=(this.verticalHistory.find(r=>r.decision===d))!.program.to_pc;d.status='executed';}else if(d.progression_start_s!<=scene)d.status='transitioning';}this.pending=this.pending.filter(d=>d.progression_end_s!>scene);return;}for(const d of this.pending){if(d.arrival_scene_s!<=scene){d.status='executed';}else if(d.boundary_s!<=scene)d.status='transitioning';}this.pending=this.pending.filter(d=>d.status!=='executed');if(!this.pending.length)this.beforePending=null;}
}
export function videoCorrection(drift:number,sinceSeek:number){if(Math.abs(drift)>.25&&sinceSeek>2)return {seek:true,rate:1};return {seek:false,rate:Math.abs(drift)<.025?1:Math.max(.97,Math.min(1.03,1-drift*.15))};}
