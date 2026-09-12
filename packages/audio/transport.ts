import type {ArrangementPlan,ControlAction,ScoreEvent} from '../contracts/generated';
import {validate} from '../contracts/validate';
import {Bundle,copy,seconds,transition} from './model';
export type Decision={id:string;status:string;reason?:string;requested_scene_s:number;boundary_s?:number;boundary_tick?:number;signed_semitones?:number;generation:number;source:string};
export class Timeline {
 events:ScoreEvent[];original:ScoreEvent[];generation=0;position=0;playing=false;tonic:number;
 beforePending:ScoreEvent[]|null=null;previousTonic=0;
 seen=new Set<string>();sequences=new Set<string>();pending:Decision[]=[];history:Decision[]=[];lastRequest=-Infinity;
 constructor(public bundle:Bundle,public plan:ArrangementPlan,public planHash:string){this.events=copy(bundle.events);this.original=copy(bundle.events);this.tonic=bundle.composition.key_map[0].tonic_pc;}
 get epoch(){return `transport-${this.generation}`;}
 reset(position:number,restore=false){if(!Number.isFinite(position)||position<0||position>this.bundle.scene.duration_s)throw Error('Invalid seek');if(this.pending.length&&this.beforePending){this.events=this.beforePending;this.tonic=this.previousTonic;}this.beforePending=null;for(const d of this.pending)d.status='cancelled_on_transport_reset';this.pending=[];this.generation++;this.position=position;this.playing=false;this.lastRequest=-Infinity;if(restore){this.events=copy(this.original);this.tonic=this.bundle.composition.key_map[0].tonic_pc;}}
 submit(action:ControlAction,audioNow:number,sceneNow:number,horizon=.15):Decision{
  validate(action);const d:Decision={id:action.id,status:'suppressed',requested_scene_s:sceneNow,generation:this.generation,source:action.provenance.source_mode};
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
  const c=this.bundle.composition,bar=c.ppq*4*c.meter[0]/c.meter[1];let tick=bar;
  while(tick<c.length_ticks&&seconds(c,tick)<sceneNow+horizon+.025)tick+=bar;
  const at=seconds(c,tick);
  if(tick>=c.length_ticks||audioNow+at-sceneNow>=action.expires.seconds)return reject('no_feasible_boundary_before_expiry');
  const changed=transition(this.events,this.plan,c,tick,action.signed_semitones!,this.tonic);
  this.beforePending=copy(this.events);this.previousTonic=this.tonic;this.events=changed;this.tonic=(this.tonic+action.signed_semitones!+12)%12;
  Object.assign(d,{status:'queued',boundary_s:at,boundary_tick:tick,signed_semitones:action.signed_semitones!,reason:action.request.seconds<audioNow-.15?'late_deferred':undefined});this.pending.push(d);this.history.push(d);return d;
 }
 advance(scene:number){this.position=scene;for(const d of this.pending)if(d.boundary_s!<=scene)d.status='executed';this.pending=this.pending.filter(d=>d.status==='queued');if(!this.pending.length)this.beforePending=null;}
}
export function videoCorrection(drift:number,sinceSeek:number){if(Math.abs(drift)>.25&&sinceSeek>2)return {seek:true,rate:1};return {seek:false,rate:Math.abs(drift)<.025?1:Math.max(.97,Math.min(1.03,1-drift*.15))};}
