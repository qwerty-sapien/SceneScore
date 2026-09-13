import type {ClockMapping,ControlAction,GestureEvent} from '../../../../packages/contracts/generated';
export type MuseMode='KEYBOARD'|'SYNTHETIC_TEST'|'REAL_REPLAY'|'LIVE_MUSE';
export interface MuseControlEnvelope {
 version:'muse-control-envelope-1'; action:ControlAction;
 detector:{version:string;model_version:string;grammar_hash:string};
 timing:{t0_final_blink_s:number|null;t1_decision_s:number|null;t2_dispatch_s:number|null;t3_request_s:number;t4_received_s:number|null;t5_ack_onset_s:number|null;t6_boundary_s:number|null;device_epoch:string|null;host_epoch:string|null;audio_epoch:string;clock_mapping_id:string|null;unavailable_reasons:Record<string,string>};
}
export interface MusicControlContext {audio_s:number;audio_epoch:string;approved_plan_hash:string|null;scene_policy_id:string|null;signed_semitones:-2|0|2;lanes:ControlAction['before'];expires_after_s?:number;suppression_reason?:string|null}
export interface MuseDecision {status:string;reason?:string|null;t4_received_s?:number|null;t5_ack_onset_s?:number|null;t6_boundary_s?:number|null}
export interface MusePanelProps {
 onEnvelope:(envelope:MuseControlEnvelope)=>MuseDecision;
 onKeyboardRequest:()=>void;
 getMusicContext:(requestAudioS?:number)=>MusicControlContext|null;
 createSimulation:(context:MusicControlContext)=>MuseControlEnvelope;
 createFromGesture:(gesture:GestureEvent,mapping:ClockMapping,hostDispatchS:number,hostEpoch:string,context:MusicControlContext)=>MuseControlEnvelope;
 transportStatus?:string;
}
export interface BridgeStatus {version:'muse-bridge-1';mode:MuseMode;connected:boolean;hardware_verified:boolean;quality:'good'|'bad'|'unverified';warmup_ready:boolean;armed:boolean;reason:string;model_version:string;config_hash:string;source_available:boolean;recording:false;sample_count:number;device_epoch:string;host_epoch:string}
export interface ClockProbe {device_s:number;device_epoch:string;host_s:number;host_epoch:string;uncertainty_s:number;config_hash:string;source_mode:'real_device'|'replay'|'synthetic'}
export type BridgeEvent={id:number;kind:'candidate'|'rejection'|'status';at_s:number;reason?:string;candidate_id?:string}|{id:number;kind:'gesture';gesture:GestureEvent;host_dispatch_s:number;host_epoch:string};
export interface BridgeBatch {cursor:number;events:BridgeEvent[];status:BridgeStatus;overflow:boolean}
