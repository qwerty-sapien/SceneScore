import {BAR, BEAT, PHRASE, scoreStep, type Settings} from './keyboard-score';
import type {ScoreEvent} from '../contracts/generated';

export const LOOP=BAR*4;
export const SCENE_EVENTS=[
 {name:'Approach',effect:'Piano rises into the marker'},
 {name:'Near miss',effect:'Both tracks pause just before'},
 {name:'Separation',effect:'Piano descends from the marker'},
 {name:'Contact',effect:'Guitar chord'},
 {name:'Sustained contact',effect:'Hold piano + guitar'},
 {name:'Contact release',effect:'Light guitar motif'},
 {name:'Rebound',effect:'Guitar turn / trill'},
] as const;
export type SceneMarker={id:number;kind:number;at:number};
export type SettingPoint={at:number;settings:Settings};
export function settingsAt(points:SettingPoint[],at:number):Settings{
 for(let i=points.length-1;i>=0;i--)if(points[i].at<=at+1e-8)return points[i].settings;
 return points[0].settings;
}
export function eventWindow(kind:number,at:number){
 return {start:at-(kind===0?2*BEAT:kind===1?BEAT/2:0),end:at+(kind===1?0:kind===0?BEAT/2:2*BEAT)};
}
type Episode={id:string;marker:SceneMarker;at:number;start:number;end:number;lanes:string[]};
const rootAt=(at:number)=>[0,0,5,7][((Math.floor(at/BAR)%4)+4)%4];
function heldMelody(at:number){
 let step=Math.floor(at/BEAT)*2;
 for(let i=0;i<32;i++,step--){const index=((step%32)+32)%32,pitch=PHRASE[Math.floor(index/8)][index%8];if(pitch!==null)return pitch;}
 return 60;
}
function replacement(ep:Episode,hash:string):ScoreEvent[]{
 const {kind}=ep.marker,root=rootAt(ep.at),events:ScoreEvent[]=[];
 const template=scoreStep(0,{transpose:0,ornament:'plain',touch:'legato'},hash)[0];
 const add=(lane:string,pitch:number,at:number,duration:number,velocity=76)=>{
  const instrument=lane==='guitar'?'guitar_fingerstyle_v1':'piano_felt_comp_v1';
  events.push({...template,id:`replacement:${ep.id}:${events.length}`,lane_id:lane,instrument_id:instrument,timbre_id:instrument,
   resolved_time_s:at,scene_time_s:ep.at,duration_s:duration,midi_pitch:pitch,velocity,
   dynamics_db:lane==='piano'?-11:-6,articulation:kind===4?'legato':kind===3?'tenuto':'detached',
   phrasing:`scene-replacement:${SCENE_EVENTS[kind].name}`,ornament:kind===6?'turn':null});
 };
 if(kind===0||kind===2){
  const spacing=BEAT*(kind===0?.5:.4);
  for(let i=0;i<5;i++)add('piano',48+root+(kind===0?i-4:4-i),ep.start+i*spacing,spacing*.96,kind===0?60+i*4:76-i*4);
 }else if(kind===3){
  for(const pitch of [48,52,55,58])add('guitar',pitch+root,ep.at,BEAT*1.7,64);
 }else if(kind===4){
  add('piano',48+root,ep.at,2*BEAT,72);add('guitar',heldMelody(ep.at),ep.at,2*BEAT,80);
 }else if(kind===5||kind===6){
  const pitches=kind===5?[7,4,2,0]:[0,2,0,-1,0,2,0];
  pitches.forEach((pitch,i)=>add('guitar',60+root+pitch,ep.at+i*BEAT*(kind===5?.4:.25),BEAT*(i===pitches.length-1?.48:.22),kind===5?62-i*3:78-i*3));
 }
 return events;
}
// Compile complete passages; no independent cue layer. Bounds include neighboring
// cycles so anticipations and sustained notes cross the loop seam correctly.
export function compileDuet(start:number,end:number,markers:SceneMarker[],points:SettingPoint[],hash:string):ScoreEvent[]{
 const episodes:Episode[]=[];
 for(let cycle=Math.floor(start/LOOP)-1;cycle<=Math.floor(end/LOOP)+1;cycle++)for(const marker of markers){
  const at=cycle*LOOP+marker.at,window=eventWindow(marker.kind,at);
  if(window.end<=start||window.start>=end)continue;
  episodes.push({id:`${cycle}:${marker.id}`,marker,at,...window,lanes:marker.kind===1||marker.kind===4?['piano','guitar']:marker.kind===0||marker.kind===2?['piano']:['guitar']});
 }
 const candidates:{event:ScoreEvent;owner:string|null}[]=[];
 for(let step=Math.max(0,Math.floor((start-BAR)/BEAT)*2);step<Math.ceil(end/BEAT)*2;step++){
  const settings=settingsAt(points,Math.floor(step/2)*BEAT);
  for(const event of scoreStep(step,{...settings,transpose:0},hash))candidates.push({event,owner:null});
 }
 for(const ep of episodes)for(const event of replacement(ep,hash))candidates.push({event,owner:ep.id});
 const result:ScoreEvent[]=[];
 for(const {event,owner} of candidates){
  const from=Math.max(start,0,event.resolved_time_s),to=Math.min(end,event.resolved_time_s+event.duration_s);
  if(to<=from)continue;
  const relevant=episodes.filter(e=>e.lanes.includes(event.lane_id)&&e.end>from&&e.start<to);
  const cuts=[from,to,...relevant.flatMap(e=>[e.start,e.end]),...points.map(p=>p.at)].filter(t=>t>=from&&t<=to).sort((a,b)=>a-b);
  for(let i=0;i<cuts.length-1;i++){
   const a=cuts[i],b=cuts[i+1];if(b-a<1e-7)continue;
   const middle=(a+b)/2,winner=relevant.filter(e=>e.start<=middle&&e.end>middle).sort((x,y)=>(Number(y.marker.kind===1)-Number(x.marker.kind===1))||y.marker.id-x.marker.id)[0];
   if((winner?.id??null)!==owner)continue;
   // Anticipation aims at the arrival key, including an already queued modulation.
   const transpose=settingsAt(points,winner?.marker.kind===0?winner.at:a).transpose;
   const pitch=event.midi_pitch===null?null:event.midi_pitch+transpose;
   const previous=result[result.length-1];
   if(previous&&previous.id.startsWith(`${event.id}@`)&&previous.midi_pitch===pitch&&Math.abs(previous.resolved_time_s+previous.duration_s-a)<1e-8)previous.duration_s+=b-a;
   else result.push({...event,id:`${event.id}@${a.toFixed(6)}`,resolved_time_s:a,duration_s:b-a,midi_pitch:pitch});
  }
 }
 return result.sort((a,b)=>a.resolved_time_s-b.resolved_time_s||a.id.localeCompare(b.id));
}
