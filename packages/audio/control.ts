/** Semantic controls only. Device samples and training never enter the audio path. */
import type {ClockMapping,ControlAction,GestureEvent} from '../contracts/generated';
import {validate} from '../contracts/validate';
import type {Engine} from './engine';
import type {Bundle} from './model';
import type {ArrangementPlan} from '../contracts/generated';

export type MusicControlContext={audio_s:number;audio_epoch:string;approved_plan_hash:string|null;scene_policy_id:string|null;signed_semitones:-2|0|2;lanes:ControlAction['before'];expires_after_s?:number;suppression_reason?:string|null};
export type ControlEnvelope={version:'muse-control-envelope-1';action:ControlAction;detector:{version:string;model_version:string;grammar_hash:string};timing:{t0_final_blink_s:number|null;t1_decision_s:number|null;t2_dispatch_s:number|null;t3_request_s:number;t4_received_s:number|null;t5_ack_onset_s:number|null;t6_boundary_s:number|null;device_epoch:string|null;host_epoch:string|null;audio_epoch:string;clock_mapping_id:string|null;unavailable_reasons:Record<string,string>}};
const ZERO='0'.repeat(64);
/** Prepared causal world-Z integral. Query cost is logarithmic, with no score allocation. */
export function prepareMotionReader(bundle:Bundle,plan:ArrangementPlan){
 const policy=plan.motion_policy,rows=bundle.states.filter(s=>s.object_id===policy.focus_object_id).sort((a,b)=>a.scene_time_s-b.scene_time_s);
 const times=rows.map(r=>r.scene_time_s),integrals=[0],unknown=[0];
 for(let i=1;i<rows.length;i++){const dt=times[i]-times[i-1];integrals.push(integrals[i-1]+dt*(rows[i-1].velocity_m_s?.[2]??0));unknown.push(unknown[i-1]+(rows[i-1].velocity_m_s?0:dt));}
 function index(t:number){let lo=0,hi=times.length;while(lo<hi){const mid=(lo+hi)>>>1;if(times[mid]<=t)lo=mid+1;else hi=mid;}return lo-1;}
 function value(t:number,i:number){return {motion:integrals[i]+(t-times[i])*(rows[i].velocity_m_s?.[2]??0),unknown:unknown[i]+(rows[i].velocity_m_s?0:t-times[i])};}
 return (at:number):-2|0|2=>{if(!Number.isFinite(at)||!times.length)return 0;const start=Math.max(0,at-policy.lookback_s),i=index(at),j=index(start);if(i<0||j<0||at<=start||at-times[i]>policy.lookback_s)return 0;const end=value(at,i),begin=value(start,j);if(end.unknown-begin.unknown>1e-9)return 0;const speed=(end.motion-begin.motion)/(at-start);return Math.abs(speed)<=policy.deadband_m_s?0:speed>0?2:-2;};
}
function action(context:MusicControlContext,id:string,provenance:ControlAction['provenance']):ControlAction{
 const sign=context.signed_semitones,reason=context.suppression_reason??(!sign?'stationary_world_z':null);
 const record:ControlAction={kind:'ControlAction',schema_version:'0.1',id:`control-${id}`,gesture_id:id,sequence_id:id,provenance,gesture_count:2,profile:'double_modulate_mvp',action:sign?'request_modulation':'none',request:{clock:'audio',epoch:context.audio_epoch,seconds:context.audio_s},expires:{clock:'audio',epoch:context.audio_epoch,seconds:context.audio_s+(context.expires_after_s??6)},boundary:'next_approved_bar_or_phrase',signed_semitones:sign,approved_plan_hash:context.approved_plan_hash,scene_policy_id:context.scene_policy_id,status:reason?'suppressed':'queued',reason,quality:{state:'good',reason:null},before:{...context.lanes},after:{...context.lanes}};
 validate(record);return record;
}
export function createSimulation(context:MusicControlContext,source:'synthetic'|'keyboard'='synthetic'):ControlEnvelope{
 const id=crypto.randomUUID(),provenance:ControlAction['provenance']={source_mode:source,creator:'scenescore-semantic-control',tool_version:'muse-control-1',config_hash:ZERO,input_hashes:[],seed:null};
 return {version:'muse-control-envelope-1',action:action(context,id,provenance),detector:{version:'explicit-accepted-event-simulator-1',model_version:'none',grammar_hash:ZERO},timing:{t0_final_blink_s:null,t1_decision_s:null,t2_dispatch_s:null,t3_request_s:context.audio_s,t4_received_s:null,t5_ack_onset_s:null,t6_boundary_s:null,device_epoch:null,host_epoch:null,audio_epoch:context.audio_epoch,clock_mapping_id:null,unavailable_reasons:{detector_latency:'Explicit semantic simulation; no sampled blink or detector',host_dispatch:'Browser-only event; no host monotonic stamp',physical_output:'No acoustic measurement'}}};
}
export function mappedRequest(gesture:GestureEvent,mapping:ClockMapping,audioEpoch:string){
 validate(gesture);validate(mapping);
 if(mapping.source_clock!=='device'||mapping.destination_clock!=='audio'||mapping.source_epoch!==gesture.decision.epoch||mapping.destination_epoch!==audioEpoch||gesture.decision.clock!=='device'||gesture.decision.seconds<mapping.valid_from_s||gesture.decision.seconds>mapping.valid_until_s||mapping.uncertainty_s>.02)throw Error('unmapped_or_stale_clock');
 return mapping.destination_anchor_s+(gesture.decision.seconds-mapping.source_anchor_s)*mapping.rate;
}
export function createFromGesture(gesture:GestureEvent,mapping:ClockMapping,hostDispatchS:number,hostEpoch:string,context:MusicControlContext):ControlEnvelope{
 const request=mappedRequest(gesture,mapping,context.audio_epoch);
 if(gesture.status!=='accepted'||gesture.gesture_count!==2||gesture.quality.state!=='good')throw Error(gesture.reason??'single_triple_or_ambiguous_train');
 if(gesture.closure_delay_s<=.5||gesture.decision.seconds-gesture.final_blink.seconds<.5)throw Error('sequence_not_closed');
 if(!Number.isFinite(hostDispatchS)||hostDispatchS<0||!hostEpoch)throw Error('invalid_host_clock');
 if(Math.abs(context.audio_s-request)>1e-6)throw Error('music_context_not_at_request');
 return {version:'muse-control-envelope-1',action:action(context,gesture.id,gesture.provenance),detector:{version:'scenescore-causal-pipeline',model_version:'scenescore-new-causal-median/1',grammar_hash:gesture.grammar_hash},timing:{t0_final_blink_s:gesture.final_blink.seconds,t1_decision_s:gesture.decision.seconds,t2_dispatch_s:hostDispatchS,t3_request_s:request,t4_received_s:null,t5_ack_onset_s:null,t6_boundary_s:null,device_epoch:gesture.decision.epoch,host_epoch:hostEpoch,audio_epoch:context.audio_epoch,clock_mapping_id:mapping.id,unavailable_reasons:{physical_blink:'t0 is algorithmic candidate end, not independently observed physical blink',physical_output:'No acoustic measurement'}}};
}
export function dispatchControl(engine:Engine,envelope:ControlEnvelope){
 if(envelope.version!=='muse-control-envelope-1')throw Error('unsupported_control_envelope');
 const decision=engine.submit(envelope.action);
 Object.assign(envelope.timing,{t4_received_s:decision.audio_received_s,t5_ack_onset_s:decision.ack_onset_audio_s??null,t6_boundary_s:decision.arrival_audio_s??null});
 if(decision.ack_onset_audio_s===undefined)envelope.timing.unavailable_reasons.acknowledgement=decision.reason??'not_scheduled';
 return {...decision,t4_received_s:decision.audio_received_s,t5_ack_onset_s:decision.ack_onset_audio_s??null,t6_boundary_s:decision.arrival_audio_s??null};
}
export function latencyIntervals(envelope:ControlEnvelope){const t=envelope.timing;return {detector_closure_ms:t.t0_final_blink_s===null||t.t1_decision_s===null?null:1000*(t.t1_decision_s-t.t0_final_blink_s),mapped_request_to_receipt_ms:t.t4_received_s===null?null:1000*(t.t4_received_s-t.t3_request_s),accepted_to_scheduled_ack_ms:t.t4_received_s===null||t.t5_ack_onset_s===null?null:1000*(t.t5_ack_onset_s-t.t4_received_s),musical_arrival_wait_ms:t.t4_received_s===null||t.t6_boundary_s===null?null:1000*(t.t6_boundary_s-t.t4_received_s),ack_to_arrival_wait_ms:t.t5_ack_onset_s===null||t.t6_boundary_s===null?null:1000*(t.t6_boundary_s-t.t5_ack_onset_s),host_to_browser_ms:null,physical_output_measured:false};}
