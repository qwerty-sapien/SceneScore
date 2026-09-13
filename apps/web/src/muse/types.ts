import type {ClockMapping,ControlAction,GestureEvent} from '../../../../packages/contracts/generated';
export type MuseMode='KEYBOARD'|'SYNTHETIC_TEST'|'REAL_REPLAY'|'LIVE_MUSE';
export interface ModelEvaluation {precision:number|null;recall:number|null;complete:boolean;target_reached:boolean}
export interface CheckpointCatalog {selection:string;active_checkpoint_id:string|null;checkpoints:{id:string;created_ns:number;parent_id:string|null;training_steps:number;source_mode:string;evaluation:ModelEvaluation|null}[];invalid_checkpoint_ids:string[]}
export interface BridgeStatus {active_checkpoint_id?:string|null;checkpoint_selection?:string;evaluation?:ModelEvaluation|null;accuracy_target_advisory?:boolean;arming?:boolean}
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
export type BluetoothState='idle'|'scanning'|'connecting'|'gatt_verifying'|'configuring'|'subscribing'|'starting_stream'|'streaming'|'disconnecting'|'disconnected'|'error';
export interface BridgeStatus {
 transport?:string;device_name?:string|null;bluetooth_state?:BluetoothState;ble_connected?:boolean;
 reconnect_required?:boolean;last_error?:string|null;last_operation?:string|null;disconnect_stage?:string|null;
 connected_for_s?:number;streaming_for_s?:number;notification_rate_hz?:number;packet_rate_hz?:number;last_packet_age_s?:number|null;
}
export interface MuseDevice {id:string;name:string}
export interface MuseScan {devices:MuseDevice[];status?:BridgeStatus}
export type MuseOperation='scan'|'connect'|'disconnect';
export interface ClockProbe {device_s:number;device_epoch:string;host_s:number;host_epoch:string;uncertainty_s:number;config_hash:string;source_mode:'real_device'|'replay'|'synthetic'}
export type BridgeEvent={id:number;kind:'candidate'|'rejection'|'status';at_s:number;reason?:string;candidate_id?:string}|{id:number;kind:'gesture';gesture:GestureEvent;host_dispatch_s:number;host_epoch:string};
export interface BridgeBatch {cursor:number;events:BridgeEvent[];status:BridgeStatus;overflow:boolean}
