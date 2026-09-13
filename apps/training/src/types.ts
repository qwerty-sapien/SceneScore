export type SourceMode='real_device'|'synthetic';
export interface CheckEstimate {precision:number|null;recall:number|null;complete:boolean;target_reached:boolean;labels:number;monitored_s:number;background_s:number;availability:number}
export interface AutomaticStatus {phase:'idle'|'connecting'|'learning'|'fitting'|'checking'|'stopping'|'stopped'|'complete'|'error';active:boolean;message:string;run_id:string|null;source_mode:SourceMode;elapsed_s:number;limit_s:number;labels:number;usable_positive_windows:number;background_windows:number;checkpoint_id:string|null;training_steps:number;evaluation:CheckEstimate|null;target:number;target_advisory:true}
export type Role='train'|'development'|'final_test';
export type TrialClass='double'|'single'|'triple'|'natural'|'artifact'|'keypress_only';
export interface Channel {name:string;unit:string}
export type Quality=string|{state:string;reason?:string|null};
export interface SessionSummary {id:string;participant_id:string;refit_id:string;role:Role;source_mode:SourceMode;samples:number;duration_s:number;marker_count:number;reviewed_count:number;status:string;start_s?:number;end_s?:number}
export interface ModelSummary {id:string;status:string;positive_examples:number;negative_examples:number;source_mode:SourceMode;held_out:unknown;model_kind:string;control_authority:false;[key:string]:unknown}
export interface Status {version:string;connected:boolean;mode:SourceMode|null;recording:boolean;source:unknown;channels:Channel[];sample_rate_hz:number|null;measured_rate_hz:number|null;sample_count:number;last_device_s:number|null;sample_age_s?:number|null;device_epoch:string|null;quality:Quality;reason:string|null;current_session_id:string|null;sessions:SessionSummary[];model:ModelSummary|null}
export interface Trace {channels:Channel[];times_s:number[];samples:number[][];device_epoch:string|null;source_mode:SourceMode|null;quality:Quality;prediction:{score:number;model_id:string;semantics:string}|null}
export interface Source {id:string;name:string;channels:Channel[];sample_rate_hz:number}
export interface Marker {id:string;class_name:TrialClass;start_s:number;end_s:number|null;source:string;review_required:true;[key:string]:unknown}
export interface Review {marker_id:string;start_s:number;end_s:number;class_name:TrialClass;certainty:'reviewed'|'uncertain';reviewer:string;notes:string;[key:string]:unknown}
export interface ReviewBundle {session:SessionSummary;markers:Marker[];reviews:Review[]}
export interface MarkerRequest {event:'down'|'up'|'cue';id:string;class_name:TrialClass;client_ms:number}
export type DiagnosticState='pass'|'warning'|'blocked'|'unknown';
export interface DiagnosticsReport {
 version:string;enabled:boolean;checking:boolean;checked_at:string|null;check_age_s:number|null;
 stages:{id:string;label:string;state:DiagnosticState;detail:string;action:string}[];
 signal:{age_s:number|null;window_s:number;gaps:number;rate_hz:number|null;channels:{name:string;unit:string;min:number;max:number;peak_to_peak:number;flat:boolean}[]};
 discovery:{sources:Source[];blockers:string[];observed:{name:string;id:string;error?:string}[]};
 bluetooth:{authorization?:string;power?:string;devices?:{id:string;name:string;system_connected:boolean;advertising:boolean;rssi_dbm?:number}[];error?:string};
 events:{at:string;stage:string;state:DiagnosticState;detail:string}[];source_mode:SourceMode|null;
 configuration:{transport:string;board_id:string;units:string;env_placeholders_used:boolean};
}
