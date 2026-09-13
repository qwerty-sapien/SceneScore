import type {ScoreEvent} from '../contracts/generated';
import {validate} from '../contracts/validate';
import {sha,stable} from './model';
import {voice} from './engine';
import {polyphony} from './mix';

export const VIDEO_ACCOMPANIMENT_VERSION='video-accompaniment-2';
export type VideoScore={version:typeof VIDEO_ACCOMPANIMENT_VERSION;video_sha256:string;duration_s:number;seed:number;tempo_bpm:number;title:string;basis:'video-only';approval:null;events:ScoreEvent[]};

/** Original two-bar piano sketch. No inferred geometry, collision or object binding. */
export async function createVideoScore(videoHash:string,duration:number,seed=42):Promise<VideoScore>{
 if(!/^[a-f0-9]{64}$/.test(videoHash)||!Number.isFinite(duration)||duration<2||duration>120||!Number.isSafeInteger(seed)||seed<0||seed>0xffffffff)throw Error('Invalid video accompaniment input');
 const config={version:VIDEO_ACCOMPANIMENT_VERSION,videoHash,duration,seed};
 const config_hash=await sha(new TextEncoder().encode(stable(config)));
 const provenance={source_mode:'manual_plan' as const,creator:'SceneScore original piano grammar',tool_version:VIDEO_ACCOMPANIMENT_VERSION,config_hash,input_hashes:[videoHash],seed};
 const phrases=Math.max(1,Math.round((duration-.15)/5)),beat=(duration-.15)/(phrases*8),events:ScoreEvent[]=[];
 const transpose=[0,2,-2][seed%3];
 const motifs=[[72,74,76,79,77,74,71,72],[76,79,74,72,77,76,71,72],[79,76,74,76,77,74,71,72]];
 const melody=motifs[Math.floor(seed/3)%motifs.length];
 function note(at:number,pitch:number,length:number,lane:string,velocity:number,articulation:string){
  const e:ScoreEvent={kind:'ScoreEvent',schema_version:'0.1',id:`video-piano:${config_hash.slice(0,16)}:${events.length}`,provenance,plan_id:`video-piano:${config_hash}`,object_id:null,lane_id:lane,event_type:'note',instrument_id:'scene_piano_v1',start_tick:Math.round(at*960),duration_ticks:Math.round(length*960),resolved_time_s:at*beat,duration_s:Math.min(length*beat,duration-at*beat),scene_time_s:null,midi_pitch:pitch+transpose,velocity,dynamics_db:-5,articulation,phrasing:at<4?'question':'answer',ornament:null,timbre_id:'scene_piano_v1',swing_applied:true,swing_application_count:1};
  validate(e);events.push(e);
 }
 for(let phrase=0;phrase<phrases;phrase++){
 const base=phrase*8;
 // The offbeats are materialized once at a 2:1 swing ratio.
 [0,2,4,6].forEach((at,i)=>note(base+at,[48,55,50,43][i],.85,'piano-bass',59,'tenuto'));
 [[52,55,59],[53,57,60],[53,57,60],[53,59,62]].forEach((chord,i)=>chord.forEach(p=>note(base+i*2+2/3,p,.48,'piano-chords',43+(seed%4),'staccato')));
 [0,2/3,1+2/3,2.5,4,4+2/3,5+2/3,7].forEach((at,i)=>note(base+at,melody[(i+phrase%2*2)%8],i===7?1.2:i%2?.4:.65,'piano-melody',64+((seed+i*3)%7),i===7?'tenuto':i%2?'staccato':'legato'));
 [48,52,55,59].forEach(p=>note(base+7,p,1.2,'piano-cadence',42,'tenuto'));
 }
 events.sort((a,b)=>a.resolved_time_s-b.resolved_time_s||a.id.localeCompare(b.id));polyphony(events,8);
 return {version:VIDEO_ACCOMPANIMENT_VERSION,video_sha256:videoHash,duration_s:duration,seed,tempo_bpm:60/beat,title:'Turning Glass',basis:'video-only',approval:null,events};
}

/** Audio clock owns this bounded draft audition. Video follows it in the player. */
export class VideoMusicTransport{
 playing=false;position=0;anchorAudio=0;anchorScene=0;master:GainNode;
 nodes:{source:AudioBufferSourceNode;gain:GainNode}[]=[];buffers:AudioBuffer[];
 constructor(readonly context:AudioContext,readonly score:VideoScore,volume=.35){
  this.master=context.createGain();this.master.gain.value=volume;this.master.connect(context.destination);
  this.buffers=score.events.map(e=>voice(context,e));
 }
 now(){return this.playing?Math.min(this.score.duration_s,this.anchorScene+Math.max(0,this.context.currentTime-this.anchorAudio)):this.position;}
 play(position=this.position){
  if(!Number.isFinite(position)||position<0||position>=this.score.duration_s)throw Error('Invalid playback position');
  this.pause();this.position=position;this.anchorScene=position;this.anchorAudio=this.context.currentTime+.08;this.playing=true;
  this.score.events.forEach((e,i)=>{const end=e.resolved_time_s+e.duration_s;if(end<=position)return;
   const source=this.context.createBufferSource(),gain=this.context.createGain(),offset=Math.max(0,position-e.resolved_time_s),when=this.anchorAudio+Math.max(0,e.resolved_time_s-position);
   source.buffer=this.buffers[i];source.connect(gain);gain.connect(this.master);
   gain.gain.setValueAtTime(0,when);gain.gain.linearRampToValueAtTime(1,when+.005);
   source.onended=()=>{source.disconnect();gain.disconnect();};
   source.start(when,offset,Math.min(e.duration_s-offset,this.score.duration_s-Math.max(position,e.resolved_time_s)));
   this.nodes.push({source,gain});
  });
 }
 pause(){this.position=this.now();this.playing=false;for(const n of this.nodes){n.gain.gain.cancelScheduledValues(this.context.currentTime);n.gain.gain.setTargetAtTime(0,this.context.currentTime,.003);try{n.source.stop(this.context.currentTime+.015);}catch{/* already ended */}}this.nodes=[];}
 seek(position:number){if(!Number.isFinite(position)||position<0||position>this.score.duration_s)throw Error('Invalid seek');this.pause();this.position=position;}
 volume(level:number){if(!Number.isFinite(level)||level<0||level>1)throw Error('Invalid volume');this.master.gain.setTargetAtTime(level,this.context.currentTime,.008);}
 async close(){this.pause();this.master.disconnect();if(this.context.state!=='closed')await this.context.close();}
}
