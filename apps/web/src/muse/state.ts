import type {BridgeStatus,MuseMode} from './types';
export function visibleMode(requested:MuseMode,status:BridgeStatus|null):MuseMode {
 if(requested==='KEYBOARD'||requested==='SYNTHETIC_TEST')return requested;
 if(!status?.source_available||status.mode!==requested)return 'KEYBOARD';
 if(requested==='LIVE_MUSE'&&!(status.connected&&status.hardware_verified&&status.quality==='good'&&status.warmup_ready&&status.armed))return 'KEYBOARD';
 return requested;
}
export const feedbackKinds=['performed','missed','uncertain','false positive','correct detection'] as const;
export type FeedbackKind=typeof feedbackKinds[number];
export interface Cue {id:string;instruction:string;started_ms:number;ends_ms:number;feedback_after_ms:number}
export interface Feedback {id:string;cue_id:string;kind:FeedbackKind;created_ms:number;independent_review:'pending';truth_label:null}
export function delayedFeedback(cue:Cue,kind:FeedbackKind,now:number):Feedback {
 if(now<cue.feedback_after_ms)throw Error('Wait until the cue window and quiet interval finish.');
 return {id:crypto.randomUUID(),cue_id:cue.id,kind,created_ms:now,independent_review:'pending',truth_label:null};
}
export function safeReadNotes():Feedback[]{try{const value=JSON.parse(localStorage.getItem('scenescore.muse.feedback.v1')??'[]');return Array.isArray(value)?value.filter(v=>v&&typeof v.cue_id==='string'&&feedbackKinds.includes(v.kind)&&v.independent_review==='pending'&&v.truth_label===null).slice(-100):[];}catch{return [];}}
export function saveNotes(notes:Feedback[]):boolean{try{localStorage.setItem('scenescore.muse.feedback.v1',JSON.stringify(notes.slice(-100)));return true;}catch{return false;}}
