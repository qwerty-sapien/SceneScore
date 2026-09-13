export type SourceMode='real_device'|'synthetic';
export type Role='train'|'development'|'final_test';
export type TrialClass='double'|'single'|'triple'|'natural'|'artifact'|'keypress_only';
export interface Channel {name:string;unit:string}
export type Quality=string|{state:string;reason?:string|null};
export interface SessionSummary {id:string;participant_id:string;refit_id:string;role:Role;source_mode:SourceMode;samples:number;duration_s:number;marker_count:number;reviewed_count:number;status:string;start_s?:number;end_s?:number}
export interface ModelSummary {id:string;status:string;positive_examples:number;negative_examples:number;source_mode:SourceMode;held_out:unknown;model_kind:string;control_authority:false;[key:string]:unknown}
export interface Status {version:string;connected:boolean;mode:SourceMode|null;recording:boolean;source:unknown;channels:Channel[];sample_rate_hz:number|null;measured_rate_hz:number|null;sample_count:number;last_device_s:number|null;device_epoch:string|null;quality:Quality;reason:string|null;current_session_id:string|null;sessions:SessionSummary[];model:ModelSummary|null}
export interface Trace {channels:Channel[];times_s:number[];samples:number[][];device_epoch:string|null;source_mode:SourceMode|null;quality:Quality;prediction:{score:number;model_id:string;semantics:string}|null}
export interface Source {id:string;name:string;channels:Channel[];sample_rate_hz:number}
export interface Marker {id:string;class_name:TrialClass;start_s:number;end_s:number|null;source:string;review_required:true;[key:string]:unknown}
export interface Review {marker_id:string;start_s:number;end_s:number;class_name:TrialClass;certainty:'reviewed'|'uncertain';reviewer:string;notes:string;[key:string]:unknown}
export interface ReviewBundle {session:SessionSummary;markers:Marker[];reviews:Review[]}
export interface MarkerRequest {event:'down'|'up'|'cue';id:string;class_name:TrialClass;client_ms:number}
