import type {MarkerRequest,TrialClass} from './types';
export const TRIALS:Record<TrialClass,{label:string;instruction:string}>={double:{label:'Double blink',instruction:'Deliberately double blink once.'},single:{label:'Single blink',instruction:'Blink once, comfortably.'},triple:{label:'Triple blink · negative',instruction:'If comfortable, blink three times. This is a negative comparison.'},natural:{label:'Natural activity',instruction:'Rest and blink naturally.'},artifact:{label:'Movement / speaking',instruction:'Move or speak normally.'},keypress_only:{label:'Keypress only',instruction:'Press B without deliberately blinking.'}};
export function editableTarget(target:EventTarget|null):boolean {const element=target as Element|null;return !!element&&typeof element.closest==='function'&&!!element.closest('textarea,select,input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=button]):not([type=submit]),[contenteditable=""],[contenteditable="true"],[role="textbox"]');}
export class IntentMarkerController {
 private held:{id:string;class_name:TrialClass}|null=null;
 private queue:Promise<unknown>=Promise.resolve();
 constructor(private send:(marker:MarkerRequest)=>Promise<unknown>,private clock=()=>performance.now(),private id:()=>string=()=>crypto.randomUUID(),private changed:(held:boolean)=>void=()=>{},private failed:(error:unknown)=>void=()=>{}){}
 private enqueue(marker:MarkerRequest){this.queue=this.queue.then(()=>this.send(marker)).catch(error=>this.failed(error));}
 down(event:{code:string;repeat:boolean;target:EventTarget|null},recording:boolean,className:TrialClass):boolean{
  if(event.code!=='KeyB'||event.repeat||this.held||!recording||editableTarget(event.target))return false;
  this.held={id:this.id(),class_name:className};this.changed(true);this.enqueue({event:'down',...this.held,client_ms:this.clock()});return true;
 }
 up(event:{code:string}):boolean{if(event.code!=='KeyB'||!this.held)return false;this.release();return true;}
 release(send=true){if(!this.held)return;const held=this.held;this.held=null;this.changed(false);if(send)this.enqueue({event:'up',...held,client_ms:this.clock()});}
 flush(){return this.queue;}
}
export type CuePhase='ready'|'active'|'quiet'|'complete';
export function cuePhase(start:number,now:number):CuePhase {const elapsed=now-start;return elapsed<2000?'ready':elapsed<4000?'active':elapsed<6000?'quiet':'complete';}
export function validateReview(start:number,end:number,reviewer:string){if(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end<=start)throw Error('Enter a valid device-time interval with end after start.');if(!reviewer.trim())throw Error('Add a reviewer name or initials.');}
export function sourceLabel(mode:string|null|undefined,connected:boolean,age:number|null=0){if(!connected)return 'NO STREAM';if(mode==='synthetic')return 'SYNTHETIC REHEARSAL';if(mode==='real_device')return age===null?'WAITING FOR EEG':age>.5?'EEG STALLED':'LIVE EEG';return 'UNVERIFIED SOURCE';}

export function reviewSegmentBounds(start:number,end:number,recordedStart=0,recordedEnd=Infinity){
 if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)throw Error('Enter valid interval bounds before loading its trace.');
 const upper=Math.min(recordedEnd,end+1),lower=Math.max(recordedStart,0,start-2.5,upper-10);
 if(upper<=lower)throw Error('The requested interval is outside this recording.');
 return {start:lower,end:upper};
}
