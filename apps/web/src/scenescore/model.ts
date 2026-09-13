import {compileDuet, LOOP, SCENE_EVENTS} from '../../../../packages/audio/keyboard-scenes';
import type {Settings} from '../../../../packages/audio/keyboard-score';

export const KINDS=['approach','near_miss','separation','contact','sustained_contact','contact_release','rebound'] as const;
export type Marker={id:number;kind:number;at:number;enabled:boolean;objects:string[];evidence:string;start_s:number;end_s:number;confidence:'observed'|'uncertain'|'manual'};
export type MusicSettings=Settings & {gainDb:number;effects:boolean};
export const DEFAULT_SETTINGS:MusicSettings={transpose:0,ornament:'plain',touch:'legato',gainDb:-9,effects:true};
export function durationCheck(duration:number){if(!Number.isFinite(duration)||duration<=0||duration>=30)throw Error('Choose a video shorter than 30 seconds.');}
export function validateMarkers(value:unknown,duration:number):Marker[]{
 durationCheck(duration);
 if(!Array.isArray(value)||value.length>64)throw Error('Use at most 64 events.');
 const ids=new Set<number>();
 for(const m of value){
  if(!m||!Number.isSafeInteger(m.id)||ids.has(m.id)||!Number.isInteger(m.kind)||m.kind<0||m.kind>6||!Number.isFinite(m.at)||m.at<0||m.at>=duration||typeof m.enabled!=='boolean'||!Array.isArray(m.objects)||m.objects.length>10||m.objects.some((o:unknown)=>typeof o!=='string'||o.length>100)||typeof m.evidence!=='string'||m.evidence.length>2000||!['observed','uncertain','manual'].includes(m.confidence)||!Number.isFinite(m.start_s)||!Number.isFinite(m.end_s)||m.start_s<0||m.end_s<m.start_s||m.end_s>duration)throw Error('Invalid event: check its type, timestamp and evidence.');
  ids.add(m.id);
 }
 return value as Marker[];
}
export function validateSettings(s:MusicSettings){
 if(!s||!Number.isInteger(s.transpose)||Math.abs(s.transpose)>12||!['plain','grace','turn','trill'].includes(s.ornament)||!['detached','staccato','legato'].includes(s.touch)||!Number.isFinite(s.gainDb)||s.gainDb< -24||s.gainDb> -6||typeof s.effects!=='boolean')throw Error('Invalid music settings.');
 return s;
}
export function parseAnalysis(raw:any,duration:number){
 if(!raw||typeof raw.summary!=='string'||raw.summary.length>4000||!Array.isArray(raw.objects)||raw.objects.length>30||!Array.isArray(raw.events)||raw.events.length>64||!Array.isArray(raw.limitations)||raw.limitations.some((s:unknown)=>typeof s!=='string'||s.length>2000))throw Error('The model returned an invalid analysis. No events were applied.');
 const ids=new Set<string>();
 for(const o of raw.objects){if(!o||typeof o.id!=='string'||o.id.length>100||ids.has(o.id)||typeof o.description!=='string'||o.description.length>1000)throw Error('Invalid object identity.');ids.add(o.id);}
 const markers=raw.events.map((e:any,i:number)=>{
  if(!e||!['observed','uncertain'].includes(e.confidence)||!Array.isArray(e.object_ids)||e.object_ids.some((id:string)=>!ids.has(id))||new Set(e.object_ids).size!==e.object_ids.length)throw Error('Invalid event object reference.');
  const kind=KINDS.indexOf(e.kind),at=kind===0?e.end_s:e.start_s;
  return {id:i+1,kind,at,enabled:e.confidence==='observed',objects:e.object_ids,evidence:e.explanation,start_s:e.start_s,end_s:e.end_s,confidence:e.confidence};
 });
 return {summary:raw.summary,objects:raw.objects as {id:string;description:string}[],limitations:raw.limitations as string[],markers:validateMarkers(markers,duration)};
}
export function compose(duration:number,markers:Marker[],settings:MusicSettings,hash:string){
 validateMarkers(markers,duration);validateSettings(settings);
 // Choose complete original four-bar phrases near 96 BPM. Short clips receive a
 // clipped phrase at 96 BPM instead of an implausibly accelerated full phrase.
 const phrases=Math.max(1,Math.round(duration/LOOP));
 const scale=duration<5?1:duration/(phrases*LOOP),end=duration/scale;
 const selected=settings.effects?markers.filter(m=>m.enabled).map(m=>({id:m.id,kind:m.kind,at:m.at/scale})):[];
 const events=compileDuet(0,end,selected,[{at:0,settings}],hash,false).map(e=>({...e,resolved_time_s:e.resolved_time_s*scale,duration_s:e.duration_s*scale,scene_time_s:e.scene_time_s===null?null:e.scene_time_s*scale}));
 return {title:'Little Signals · scene arrangement',bpm:96/scale,phrases,events,effects:SCENE_EVENTS.map((e,i)=>({kind:KINDS[i],...e})),mapping:'Stable piano/guitar voices; event types replace passages. No inferred object-specific instruments. Near-miss silence wins overlaps, then higher marker ID. Approach anticipates by two beats; near miss silences the preceding half beat; other effects last up to two beats, clipped at video boundaries.'};
}
