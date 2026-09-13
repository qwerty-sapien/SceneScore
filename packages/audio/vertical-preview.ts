/** Offline TransitionPreview data only. This never accepts a ControlAction or an Approval. */
import type {ArrangementPlan,ScoreEvent} from '../contracts/generated';
import {validate} from '../contracts/validate';
import {type Bundle,type VerticalProgram,prepareVerticalTransitions,selectVerticalTransition,
 direction,isVerticalVoice,verticalPitchVariant,clipVerticalEvent} from './model';

export type PreviewHold={start_s:number;end_s:number};
export function materializeVerticalPreview(bundle:Bundle,plan:ArrangementPlan,requests:number[],holds:PreviewHold[]=[]){
 if(requests.length>2||holds.length>512||requests.some((at,i)=>!Number.isFinite(at)||at<0||at>=bundle.scene.duration_s||(i>0&&at<=requests[i-1])))throw Error('Preview request budget or order');
 if(holds.some(h=>![h.start_s,h.end_s].every(Number.isFinite)||h.start_s<0||h.end_s<=h.start_s||h.end_s>bundle.scene.duration_s))throw Error('Invalid preview hold');
 const prepared=prepareVerticalTransitions(bundle,plan),programs:VerticalProgram[]=[],acknowledgements:ScoreEvent[]=[];
 const controls:{request_scene_s:number;status:string;reason?:string;signed_semitones:number;program_id?:string;ack_scene_s?:number;progression_start_s?:number;arrival_scene_s?:number}[]=[];
 let tonic=prepared.initial_tonic;
 for(const at of requests){
  const sign=direction(bundle,plan,at),record={request_scene_s:at,status:'suppressed',signed_semitones:sign} as typeof controls[number];controls.push(record);
  const previous=programs.at(-1);
  if(previous&&at<previous.end_s){record.reason='one_pending_request_limit';continue;}
  if(!sign){record.reason='stationary_or_unknown_world_z';continue;}
  const expiry=Math.min(bundle.scene.duration_s,at+8);let earliest=at;
  let selected:VerticalProgram|undefined;
  // Offline bounded resolution: avoid layering a pivot on a pending withheld third.
  for(let attempt=0;attempt<=holds.length;attempt++){
   selected=selectVerticalTransition(prepared,tonic,sign,earliest,expiry);
   if(!selected)break;
   const conflicts=holds.filter(h=>h.start_s<selected!.end_s&&h.end_s>selected!.start_s);
   if(!conflicts.length)break;
   earliest=Math.max(...conflicts.map(h=>h.end_s));selected=undefined;
  }
  if(!selected){record.reason='no_feasible_boundary_before_expiry';continue;}
  const ackAt=at+.02;
  if(ackAt+.12>bundle.scene.duration_s){record.reason='acknowledgement_outside_scene';continue;}
  programs.push(selected);tonic=selected.to_pc;
  for(const [i,event] of selected.acknowledgement.entries()){
   const tick=Math.round(ackAt/bundle.scene.duration_s*bundle.composition.length_ticks);
   acknowledgements.push({...event,id:`preview:${at}:ack:${i}`,start_tick:tick,resolved_time_s:ackAt});
  }
  Object.assign(record,{status:'planned_preview',program_id:selected.id,ack_scene_s:ackAt,progression_start_s:selected.start_s,arrival_scene_s:selected.arrival_s});
 }
 const events:ScoreEvent[]=[];
 for(const event of bundle.events){
  if(!isVerticalVoice(event)||!programs.length){events.push(event);continue;}
  const start=event.resolved_time_s,end=start+event.duration_s;
  const cuts=[...new Set([start,end,...programs.flatMap(p=>[p.start_s,p.end_s]).filter(t=>t>start&&t<end)])].sort((a,b)=>a-b);
  for(let i=1;i<cuts.length;i++){
   const a=cuts[i-1],b=cuts[i];
   if(programs.some(p=>a>=p.start_s-1e-9&&a<p.end_s-1e-9))continue;
   let source=event;
   for(const completed of programs.filter(p=>p.end_s<=a+1e-9))source=verticalPitchVariant(prepared,source,completed.entry.signed_semitones);
   if(a===start&&b===end){events.push(source);continue;}
   const piece=clipVerticalEvent(source,a,b,`preview:${i}`);if(piece)events.push(piece);
  }
 }
 for(const program of programs)events.push(...program.events);
 events.push(...acknowledgements);events.sort((a,b)=>a.resolved_time_s-b.resolved_time_s||a.id.localeCompare(b.id));
 if(events.length>5000||new Set(events.map(e=>e.id)).size!==events.length)throw Error('Preview event budget or duplicate identity');
 for(const event of events){validate(event);if(event.resolved_time_s<0||event.duration_s<=0||event.resolved_time_s+event.duration_s>bundle.scene.duration_s+1e-9)throw Error('Preview event outside scene');}
 return {version:'music-vertical-offline-preview-1',events,controls,approval:null,audition_status:'AUDITION_PENDING',
  timing_evidence:'planned scene times only; no Timeline.submit, scheduler, detector, acoustic or human-approval measurement',
  final_tonic:tonic};
}
