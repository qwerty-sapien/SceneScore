import type {ScoreEvent} from '../contracts/generated';

export type Ornament='plain'|'grace'|'turn'|'trill';
export type Touch='detached'|'staccato'|'legato';
export type Settings={transpose:number;ornament:Ornament;touch:Touch};
export const BPM=96, BEAT=60/BPM, BAR=4*BEAT, LIMIT=120;
// An original four-bar call/answer. Nulls preserve deliberate rests.
export const PHRASE=[[60,63,65,null,67,66,65,63],[60,null,63,65,67,null,70,67],[65,68,69,null,72,69,68,65],[67,66,65,63,62,null,60,null]];
export const SCORE={version:'keyboard-duet-2',title:'Little Signals',bpm:BPM,meter:[4,4],phrase:PHRASE,swing:2/3};
export const stepTime=(step:number)=>Math.floor(step/2)*BEAT+(step%2?BEAT*2/3:0);
export const keyName=(transpose:number)=>['C','D♭','D','E♭','E','F','G♭','G','A♭','A','B♭','B'][((transpose%12)+12)%12];
export function shifted(current:number,delta:number){return Math.max(-12,Math.min(12,current+delta));}

export function scoreStep(step:number,settings:Settings,configHash:string):ScoreEvent[]{
 const bar=Math.floor(step/8),slot=step%8,at=stepTime(step),span=stepTime(step+1)-at;
 const root=[0,0,5,7][bar%4],events:ScoreEvent[]=[];
 const add=(lane:string,pitch:number|null,offset:number,duration:number,velocity:number,articulation:string,ornament:string|null=null)=>{
  const instrument=lane==='guitar'?'guitar_fingerstyle_v1':'piano_felt_comp_v1';
  events.push({kind:'ScoreEvent',schema_version:'0.1',id:`keyboard:${step}:${events.length}`,plan_id:SCORE.version,object_id:null,lane_id:lane,event_type:pitch===null?'brush':'note',instrument_id:instrument,timbre_id:instrument,start_tick:null,duration_ticks:null,resolved_time_s:at+offset,duration_s:duration,scene_time_s:null,midi_pitch:pitch===null?null:pitch+settings.transpose,velocity,dynamics_db:lane==='guitar'?-4:-11,articulation,phrasing:'original-four-bar-call-response',ornament,swing_applied:false,swing_application_count:0,provenance:{source_mode:'manual_plan',creator:'keyboard-playground',tool_version:SCORE.version,config_hash:configHash,input_hashes:[],seed:17}});
 };
 if(slot%2===0)add('piano',36+root+(slot===4?7:0),0,BEAT*.8,65,'detached');
 if(slot===0||slot===5)for(const p of [48+root,52+root,58+root])add('piano',p,0,span*.85,53,'detached');
 const pitch=PHRASE[bar%4][slot];
 if(pitch!==null){
  const pattern=settings.ornament==='grace'?[-1,0]:settings.ornament==='turn'?[2,0,-1,0]:settings.ornament==='trill'?[0,2,0,2]:[0];
  const lengths=settings.ornament==='grace'?[.22,.78]:pattern.map(()=>1/pattern.length);
  let offset=0;
  pattern.forEach((delta,i)=>{const duration=span*lengths[i];add('guitar',pitch+delta,offset,duration*.93,i===pattern.length-1?92:78,settings.touch,settings.ornament==='plain'?null:settings.ornament);offset+=duration;});
 }
 return events;
}

export function trimTrack(events:ScoreEvent[],duration:number){return events.filter(e=>e.resolved_time_s<duration).map(e=>({...e,duration_s:Math.min(e.duration_s,duration-e.resolved_time_s)}));}
