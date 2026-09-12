import type {ScoreEvent,ControlAction} from '../contracts/generated';
import {Timeline} from './transport';
import {amplitude,polyphony,validateMix,type MixPoint,type Lanes} from './mix';
export type {Lanes} from './mix';
const seedFor=(id:string)=>[...id].reduce((n,c)=>Math.imul(n^c.charCodeAt(0),16777619)>>>0,2166136261);
export function voice(ctx:BaseAudioContext,e:ScoreEvent):AudioBuffer{
 const n=Math.max(1,Math.ceil(e.duration_s*ctx.sampleRate));if(n>ctx.sampleRate*120)throw Error('Voice budget');
 const b=ctx.createBuffer(1,n,ctx.sampleRate),v=b.getChannelData(0);let rng=seedFor(e.id),filtered=0;
 const freq=e.midi_pitch===null?0:440*2**((e.midi_pitch-69)/12);
 for(let i=0;i<n;i++){const t=i/ctx.sampleRate,remain=(n-1-i)/ctx.sampleRate;const fade=Math.min(1,t/.005,remain/.012);let sample=0;
  if(e.midi_pitch!==null){const harmonic=Math.sin(2*Math.PI*freq*t)+.23*Math.sin(4*Math.PI*freq*t)+.07*Math.sin(6*Math.PI*freq*t);const decay=e.articulation==='legato'?Math.max(.35,Math.exp(-t*1.5)):Math.exp(-t*(e.instrument_id.includes('bass')?5:3));sample=harmonic*decay*.2;}
  else{rng^=rng<<13;rng^=rng>>>17;rng^=rng<<5;const noise=(rng>>>0)/4294967296*2-1;filtered+=.18*(noise-filtered);sample=filtered*(e.event_type==='foley'?.4:.16)*(e.articulation.includes('sustain')||e.articulation==='sweep'?1:Math.exp(-t*18));}
  v[i]=sample*Math.max(0,fade)*e.velocity/127*10**(e.dynamics_db/20);
 }return b;
}
export async function renderOffline(events:ScoreEvent[],duration:number,gainDb=-18,lanes:Lanes={soundtrack:true,foley:true},rate=48000,journal?:MixPoint[]):Promise<AudioBuffer>{
 if(events.length>5000||duration>120||duration<=0||rate<8000||rate>96000)throw Error('Offline render budget');
 polyphony(events);const points=journal??[{scene_s:0,gain_db:gainDb,muted:false,lanes}];validateMix(points,duration);
 const ctx=new OfflineAudioContext(2,Math.ceil(duration*rate),rate),buses={soundtrack:ctx.createGain(),foley:ctx.createGain()};
 for(const lane of ['soundtrack','foley'] as const){const gain=buses[lane];gain.gain.value=amplitude(points[0],lane);gain.connect(ctx.destination);for(const p of points.slice(1))gain.gain.setTargetAtTime(amplitude(p,lane),p.scene_s,.008);}
 for(const e of events){if(e.resolved_time_s>=duration)continue;const node=ctx.createBufferSource();node.buffer=voice(ctx,e);node.connect(buses[e.event_type==='foley'?'foley':'soundtrack']);node.start(e.resolved_time_s);}
 return ctx.startRendering();
}
export function pcmWav(b:AudioBuffer):ArrayBuffer{const channels=b.numberOfChannels,n=b.length,bytes=new ArrayBuffer(44+n*channels*2),v=new DataView(bytes);const str=(at:number,s:string)=>[...s].forEach((c,i)=>v.setUint8(at+i,c.charCodeAt(0)));str(0,'RIFF');v.setUint32(4,bytes.byteLength-8,true);str(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,channels,true);v.setUint32(24,b.sampleRate,true);v.setUint32(28,b.sampleRate*channels*2,true);v.setUint16(32,channels*2,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,n*channels*2,true);for(let i=0;i<n;i++)for(let c=0;c<channels;c++)v.setInt16(44+(i*channels+c)*2,Math.round(Math.max(-1,Math.min(1,b.getChannelData(c)[i]))*32767),true);return bytes;}
export function measurements(b:AudioBuffer){let peak=0,sum=0,clipped=0;for(let c=0;c<b.numberOfChannels;c++)for(const s of b.getChannelData(c)){peak=Math.max(peak,Math.abs(s));sum+=s*s;if(Math.abs(s)>=1)clipped++;}return {peak,rms:Math.sqrt(sum/(b.length*b.numberOfChannels)),clipped,sample_rate:b.sampleRate,duration_s:b.duration,channels:b.numberOfChannels};}
type Scheduled={source:AudioBufferSourceNode;gain:GainNode;event:ScoreEvent;end:number};
export class Engine{
 context:AudioContext|null=null;master:GainNode|null=null;timer:ReturnType<typeof setInterval>|null=null;nodes:Scheduled[]=[];cache=new Map<string,AudioBuffer>();scheduled=new Set<string>();anchorAudio=0;anchorScene=0;gainDb=-18;mute=false;lanes:Lanes={soundtrack:true,foley:true};metrics:{scene_s:number;audio_s:number;event_id:string;generation:number}[]=[];onTick:()=>void=()=>{};onSuspend:()=>void=()=>{};
 buses:Record<keyof Lanes,GainNode>|null=null;mix:MixPoint[]=[];completed=false;discontinuous=false;historyStart=0;
 constructor(public timeline:Timeline){}
 recordMix(){const point={scene_s:this.now(),gain_db:this.gainDb,muted:this.mute,lanes:{...this.lanes}};if(this.timeline.playing)this.mix.push(point);}
 exportMix(){return this.mix.length?this.mix:[{scene_s:0,gain_db:this.gainDb,muted:this.mute,lanes:{...this.lanes}}];}
 exportReady(){if(!this.completed||this.discontinuous)throw Error('Play one complete performance from the start without seeking before exporting an approved performance.');}

 key(e:ScoreEvent){return JSON.stringify([e.id,e.midi_pitch,e.duration_s,e.dynamics_db,e.articulation,e.timbre_id]);}
 async unlock(){if(!this.context){this.context=new AudioContext();this.master=this.context.createGain();this.master.connect(this.context.destination);this.buses={soundtrack:this.context.createGain(),foley:this.context.createGain()};for(const lane of ['soundtrack','foley'] as const){this.buses[lane].gain.value=amplitude({scene_s:0,gain_db:this.gainDb,muted:this.mute,lanes:this.lanes},lane);this.buses[lane].connect(this.master);}this.context.onstatechange=()=>{if(this.context?.state==='suspended'&&this.timeline.playing){this.pause();this.onSuspend();}};}await this.context.resume();this.setGain(this.gainDb);this.prepare();}
 prepare(){if(!this.context)return;polyphony(this.timeline.events);let frames=0;const needed=new Set<string>();for(const e of this.timeline.events){const k=this.key(e);needed.add(k);if(!this.cache.has(k))this.cache.set(k,voice(this.context,e));frames+=this.cache.get(k)!.length;if(frames*4>128*1024*1024)throw Error('Audio preparation memory budget');}for(const k of this.cache.keys())if(!needed.has(k))this.cache.delete(k);}
 now(){return this.timeline.playing&&this.context?Math.min(this.timeline.bundle.scene.duration_s,this.anchorScene+Math.max(0,this.context.currentTime-this.anchorAudio)):this.timeline.position;}
 async play(){await this.unlock();if(this.timeline.position>=this.timeline.bundle.scene.duration_s)this.timeline.reset(0,true);if(this.timeline.position===0){this.completed=false;this.discontinuous=false;this.historyStart=this.timeline.history.length;this.mix=[{scene_s:0,gain_db:this.gainDb,muted:this.mute,lanes:{...this.lanes}}];}this.anchorScene=this.timeline.position;this.anchorAudio=this.context!.currentTime+.06;this.timeline.playing=true;this.fill();if(this.timer)clearInterval(this.timer);this.timer=setInterval(()=>this.fill(),25);}
 fill(){if(!this.context||!this.master||!this.timeline.playing)return;const pos=this.now();this.timeline.advance(pos);if(pos>=this.timeline.bundle.scene.duration_s){this.completed=true;this.pause();this.onTick();return;}const now=this.context.currentTime,horizon=now+.15;
  this.nodes=this.nodes.filter(n=>n.end>now);
  for(const e of this.timeline.events){if(this.scheduled.has(e.id))continue;const start=this.anchorAudio+e.resolved_time_s-this.anchorScene,end=start+e.duration_s;if(end<=now){this.scheduled.add(e.id);continue;}if(start>horizon)continue;this.scheduled.add(e.id);
   const source=this.context.createBufferSource(),gain=this.context.createGain();source.buffer=this.cache.get(this.key(e))!;source.connect(gain);gain.connect(this.buses![e.event_type==='foley'?'foley':'soundtrack']);const at=Math.max(now+.002,start),offset=Math.max(0,at-start);if(offset>=e.duration_s)continue;gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(1,at+.003);source.start(at,offset);source.stop(end+.001);source.onended=()=>{source.disconnect();gain.disconnect();};this.nodes.push({source,gain,event:e,end});this.metrics.push({scene_s:e.resolved_time_s,audio_s:at,event_id:e.id,generation:this.timeline.generation});
  }this.onTick();
 }
 clear(at?:number){if(!this.context)return;const t=at??this.context.currentTime;for(const n of this.nodes){try{n.gain.gain.cancelScheduledValues(t);n.gain.gain.setValueAtTime(n.gain.gain.value,t);n.gain.gain.linearRampToValueAtTime(0,t+.008);n.source.stop(t+.01);}catch{/*already ended*/}}this.nodes=[];this.scheduled.clear();if(this.timer)clearInterval(this.timer);this.timer=null;}
 pause(){const pos=this.now();this.clear();this.timeline.reset(pos);this.prepare();this.onTick();}
 seek(at:number){this.completed=false;this.discontinuous=at!==0;this.mix=[];this.clear();this.timeline.reset(at,true);this.prepare();this.onTick();}
 applyMix(){if(!this.context||!this.buses)return;const point={scene_s:this.now(),gain_db:this.gainDb,muted:this.mute,lanes:this.lanes};for(const lane of ['soundtrack','foley'] as const)this.buses[lane].gain.setTargetAtTime(amplitude(point,lane),this.context.currentTime,.008);}
 setGain(db:number){if(!Number.isFinite(db)||db< -36||db>0)throw Error('Gain range');this.gainDb=db;this.recordMix();this.applyMix();}
 setMute(mute:boolean){this.mute=mute;this.setGain(this.gainDb);}
 setLanes(lanes:Lanes){this.lanes=lanes;this.recordMix();this.applyMix();}
 submit(action:ControlAction){const result=this.timeline.submit(action,this.context!.currentTime,this.now());if(result.status==='queued'){
   try{this.prepare();if(this.context!.currentTime+.02>=this.anchorAudio+result.boundary_s!-this.anchorScene)throw Error('preparation_missed_boundary');}catch(error){this.timeline.events=this.timeline.beforePending!;this.timeline.tonic=this.timeline.previousTonic;this.timeline.beforePending=null;this.timeline.pending=[];result.status='suppressed';result.reason=String(error);this.prepare();return result;}
   const at=this.anchorAudio+result.boundary_s!-this.anchorScene;
   // Previously scheduled sustains end at the future boundary; replacements start there.
   for(const n of this.nodes)if(n.event.midi_pitch!==null&&n.end>at){try{n.gain.gain.setValueAtTime(1,at-.008);n.gain.gain.linearRampToValueAtTime(0,at);n.source.stop(at);}catch{/*already stopped*/}}
   for(const e of this.timeline.events)if(e.resolved_time_s>=result.boundary_s!)this.scheduled.delete(e.id);
  }this.onTick();return result;}
 async close(){this.clear();this.timeline.playing=false;this.cache.clear();await this.context?.close();this.context=null;}
}
