import type {ScoreEvent,ControlAction} from '../contracts/generated';
import {Timeline,type Decision,type PlaybackSlice} from './transport';
import {isVerticalVoice} from './model';
import {scheduleWindowFade,validateWindow,type PlaybackWindow} from './window';
import {amplitude,polyphony,validateMix,stemFor,type MixPoint,type Lanes} from './mix';
export type {Lanes} from './mix';
import {riffVoice} from './riff-voices';
const seedFor=(id:string)=>[...id].reduce((n,c)=>Math.imul(n^c.charCodeAt(0),16777619)>>>0,2166136261);
// Articulation changes the envelope inside the occupied slot, never the score clock.
export function articulationEnvelope(articulation:string,t:number,duration:number){
 const gate=duration*(articulation==='staccato'?.45:articulation==='tenuto'?.94:1);
 return Math.max(0,Math.min(1,t/.005,(gate-t)/Math.min(.012,gate/4)));
}
function* voiceSteps(ctx:BaseAudioContext,e:ScoreEvent):Generator<void,AudioBuffer>{
 const n=Math.max(1,Math.ceil(e.duration_s*ctx.sampleRate));if(n>ctx.sampleRate*120)throw Error('Voice budget');
 const b=ctx.createBuffer(1,n,ctx.sampleRate),v=b.getChannelData(0);let rng=seedFor(e.id),filtered=0;
 const freq=e.midi_pitch===null?0:440*2**((e.midi_pitch-69)/12);
 const riff=riffVoice(e,ctx.sampleRate);
 for(let i=0;i<n;i++){const t=i/ctx.sampleRate,remain=(n-1-i)/ctx.sampleRate;const fade=Math.min(1,t/.005,remain/.012);let sample=0;
  if(riff){sample=riff(t);}
  else if(e.midi_pitch!==null){const harmonic=Math.sin(2*Math.PI*freq*t)+.23*Math.sin(4*Math.PI*freq*t)+.07*Math.sin(6*Math.PI*freq*t);const decay=e.articulation==='legato'?Math.max(.35,Math.exp(-t*1.5)):Math.exp(-t*(e.instrument_id.includes('bass')?5:3));sample=harmonic*decay*.2;}
  else{rng^=rng<<13;rng^=rng>>>17;rng^=rng<<5;const noise=(rng>>>0)/4294967296*2-1;filtered+=.18*(noise-filtered);sample=filtered*(e.event_type==='foley'?.4:.16)*(e.articulation.includes('sustain')||e.articulation==='sweep'?1:Math.exp(-t*18));}
  v[i]=sample*Math.max(0,fade)*(e.midi_pitch===null?1:articulationEnvelope(e.articulation,t,n/ctx.sampleRate))*e.velocity/127*10**(e.dynamics_db/20);
  if(i%1024===1023)yield;
 }return b;
}
export function voice(ctx:BaseAudioContext,e:ScoreEvent):AudioBuffer{const steps=voiceSteps(ctx,e);let next=steps.next();while(!next.done)next=steps.next();return next.value;}
export async function renderOffline(events:ScoreEvent[],duration:number,gainDb=-18,lanes:Lanes={soundtrack:true,foley:true},rate=48000,journal?:MixPoint[],playbackSlices?:ReadonlyMap<string,PlaybackSlice>,window?:PlaybackWindow,finalFade=false):Promise<AudioBuffer>{
 if(events.length>5000||duration>120||duration<=0||rate<8000||rate>96000)throw Error('Offline render budget');
 polyphony(events);const points=journal??[{scene_s:0,gain_db:gainDb,muted:false,lanes}];validateMix(points,duration);
 if(window)validateWindow(window,duration);
 if(window&&(window.duration_s!==duration||rate!==48000))throw Error('Playback window output clock mismatch');
 const ctx=new OfflineAudioContext(2,window?window.audio_sample_count:Math.ceil(duration*rate),rate),buses={soundtrack:ctx.createGain(),foley:ctx.createGain()};
 const output=window||finalFade?ctx.createGain():null;
 if(output){output.connect(ctx.destination);scheduleWindowFade(output.gain,duration,0,0,0);}
 for(const lane of ['soundtrack','foley'] as const){const gain=buses[lane];gain.gain.value=amplitude(points[0],lane);gain.connect(output??ctx.destination);for(const p of points.slice(1))gain.gain.setTargetAtTime(amplitude(p,lane),p.scene_s,.008);}
 const cache=playbackSlices?new Map<string,AudioBuffer>():null;let preparedBytes=0;
 for(const e of events){if(e.resolved_time_s>=duration)continue;const node=ctx.createBufferSource(),slice=playbackSlices?.get(e.id),input=slice?.bufferEvent??e;
  if(cache){const key=JSON.stringify([input.midi_pitch===null?input.id:'pitched',input.instrument_id,input.midi_pitch,Math.ceil(input.duration_s*rate),input.velocity,input.dynamics_db,input.articulation,input.timbre_id]);let buffer=cache.get(key);if(!buffer){preparedBytes+=Math.max(1,Math.ceil(input.duration_s*rate))*4;if(preparedBytes>128*1024*1024)throw Error('Offline preparation memory budget');buffer=voice(ctx,input);cache.set(key,buffer);}node.buffer=buffer;}else node.buffer=voice(ctx,input);
  if(slice){const gain=ctx.createGain(),end=e.resolved_time_s+e.duration_s;node.connect(gain);gain.connect(buses[e.event_type==='foley'?'foley':'soundtrack']);gain.gain.setValueAtTime(0,e.resolved_time_s);gain.gain.linearRampToValueAtTime(1,e.resolved_time_s+.003);if(end<slice.bufferEvent.resolved_time_s+slice.bufferEvent.duration_s-1e-9){gain.gain.setValueAtTime(1,Math.max(e.resolved_time_s+.003,end-.008));gain.gain.linearRampToValueAtTime(0,end);}node.start(e.resolved_time_s,slice.offset_s);node.stop(end+.001);}
  else{node.connect(buses[e.event_type==='foley'?'foley':'soundtrack']);node.start(e.resolved_time_s);}
 }
 return ctx.startRendering();
}
/** Offline score render using the same source phase/decay offsets as vertical playback.
 * This reproduces the score schedule, not hardware output or live scheduling jitter. */
export async function renderPerformedOffline(timeline:Timeline,duration:number,gainDb=-18,lanes:Lanes={soundtrack:true,foley:true},rate=48000,journal?:MixPoint[],stem?:ReturnType<typeof stemFor>){
 const performed=timeline.performedEvents(),events=stem?performed.filter(e=>stemFor(e)===stem):performed;
 return renderOffline(events,duration,gainDb,lanes,rate,journal,timeline.vertical?timeline.verticalSlices:undefined,timeline.bundle.playback_window,Boolean(timeline.bundle.sound_design));
}

export function pcmWav(b:AudioBuffer):ArrayBuffer{const channels=b.numberOfChannels,n=b.length,bytes=new ArrayBuffer(44+n*channels*2),v=new DataView(bytes);const str=(at:number,s:string)=>[...s].forEach((c,i)=>v.setUint8(at+i,c.charCodeAt(0)));str(0,'RIFF');v.setUint32(4,bytes.byteLength-8,true);str(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,channels,true);v.setUint32(24,b.sampleRate,true);v.setUint32(28,b.sampleRate*channels*2,true);v.setUint16(32,channels*2,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,n*channels*2,true);for(let i=0;i<n;i++)for(let c=0;c<channels;c++)v.setInt16(44+(i*channels+c)*2,Math.round(Math.max(-1,Math.min(1,b.getChannelData(c)[i]))*32767),true);return bytes;}
export function measurements(b:AudioBuffer){let peak=0,sum=0,clipped=0;for(let c=0;c<b.numberOfChannels;c++)for(const s of b.getChannelData(c)){peak=Math.max(peak,Math.abs(s));sum+=s*s;if(Math.abs(s)>=1)clipped++;}return {peak,rms:Math.sqrt(sum/(b.length*b.numberOfChannels)),clipped,sample_rate:b.sampleRate,duration_s:b.duration,channels:b.numberOfChannels};}
type Scheduled={source:AudioBufferSourceNode;gain:GainNode;event:ScoreEvent;end:number;source_id?:string;level?:number};
export class Engine{
 context:AudioContext|null=null;master:GainNode|null=null;timer:ReturnType<typeof setInterval>|null=null;nodes:Scheduled[]=[];cache=new Map<string,AudioBuffer>();scheduled=new Set<string>();anchorAudio=0;anchorScene=0;gainDb=-18;mute=false;lanes:Lanes={soundtrack:true,foley:true};metrics:{scene_s:number;audio_s:number;event_id:string;generation:number}[]=[];onTick:()=>void=()=>{};onSuspend:()=>void=()=>{};
 windowBus:GainNode|null=null;
 buses:Record<keyof Lanes,GainNode>|null=null;mix:MixPoint[]=[];completed=false;discontinuous=false;historyStart=0;
 refreshTimer:ReturnType<typeof setTimeout>|null=null;refreshToken=0;refreshStats={slices:0,max_slice_ms:0};
 private refreshCancelled:(()=>void)|null=null;
 preparedVersion=-1;acknowledgements=new Map<number,AudioBuffer>();
 constructor(public timeline:Timeline){}
 recordMix(){const point={scene_s:this.now(),gain_db:this.gainDb,muted:this.mute,lanes:{...this.lanes}};if(this.timeline.playing)this.mix.push(point);}
 exportMix(){return this.mix.length?this.mix:[{scene_s:0,gain_db:this.gainDb,muted:this.mute,lanes:{...this.lanes}}];}
 exportReady(){if(!this.completed||this.discontinuous)throw Error('Play one complete performance from the start without seeking before exporting an approved performance.');}

 key(e:ScoreEvent){const normalized=this.timeline.vertical&&e.midi_pitch!==null;return JSON.stringify([e.midi_pitch===null?e.id:'pitched',e.instrument_id,e.midi_pitch,Math.ceil(e.duration_s*(this.context?.sampleRate??48000)),normalized?127:e.velocity,normalized?0:e.dynamics_db,e.articulation,e.timbre_id]);}
 private bufferEvent(e:ScoreEvent){return this.timeline.vertical&&e.midi_pitch!==null?{...e,velocity:127,dynamics_db:0}:e;}
 private noteLevel(e:ScoreEvent){return this.timeline.vertical&&e.midi_pitch!==null?e.velocity/127*10**(e.dynamics_db/20):1;}
 *verticalBuffers():Generator<void>{
  const context=this.context,ready=this.timeline.vertical;if(!context||!ready)return;
  polyphony(this.timeline.original,22);polyphony(this.timeline.original.filter(e=>!isVerticalVoice(e)),18);
  const required=new Map<string,ScoreEvent>();let bytes=0;
  function* inputs(engine:Engine){yield* engine.timeline.original;for(const row of ready!.variants.values())yield* row.values();for(const program of ready!.programs.values())yield* program.events;yield* ready!.acknowledgements;}
  for(const e of inputs(this)){const key=this.key(e);if(!required.has(key)){required.set(key,e);bytes+=Math.max(1,Math.ceil(e.duration_s*context.sampleRate))*4;if(bytes>128*1024*1024)throw Error('Audio preparation memory budget');}yield;}
  // Reconcile the resident cache before allocating replacement buffers.
  for(const key of this.cache.keys()){if(!required.has(key))this.cache.delete(key);yield;}
  for(const [key,e] of required){if(!this.cache.has(key))this.cache.set(key,yield* voiceSteps(context,this.bufferEvent(e)));yield;}
 }
 async prepareAsync(){
  if(!this.timeline.vertical){this.prepare();return;}
  if(!this.context)return;this.cancelRefresh();const token=this.refreshToken,epoch=this.timeline.epoch,context=this.context,plan=this.timeline.plan,hash=this.timeline.planHash,version=this.timeline.preparationVersion;
  this.timeline.preparationReady=false;this.timeline.preparationError=null;const steps=this.verticalBuffers();this.refreshStats={slices:0,max_slice_ms:0};
  await new Promise<void>((resolve,reject)=>{
   const fail=(error:unknown)=>{this.refreshCancelled=null;this.refreshTimer=null;this.timeline.preparationReady=false;this.timeline.preparationError=String(error);reject(error);};
   this.refreshCancelled=()=>fail(Error('audio_preparation_cancelled'));
   const valid=()=>token===this.refreshToken&&epoch===this.timeline.epoch&&context===this.context&&plan===this.timeline.plan&&hash===this.timeline.planHash&&version===this.timeline.preparationVersion;
   const run=()=>{this.refreshTimer=null;if(!valid()){fail(Error('audio_preparation_cancelled'));return;}const start=performance.now();let done=false;
    try{do{done=Boolean(steps.next().done);}while(!done&&performance.now()-start<4&&valid());}catch(error){fail(error);return;}
    this.refreshStats.slices++;this.refreshStats.max_slice_ms=Math.max(this.refreshStats.max_slice_ms,performance.now()-start);
    if(!valid()){fail(Error('audio_preparation_cancelled'));return;}if(done){this.refreshCancelled=null;this.preparedVersion=version;this.timeline.preparationReady=true;this.timeline.preparationError=null;resolve();}else this.refreshTimer=setTimeout(run,0);
   };this.refreshTimer=setTimeout(run,0);
  });
 }

 async unlock(){if(!this.context){this.context=new AudioContext();this.master=this.context.createGain();if(this.timeline.bundle.playback_window||this.timeline.bundle.sound_design){this.windowBus=this.context.createGain();this.master.connect(this.windowBus);this.windowBus.connect(this.context.destination);}else this.master.connect(this.context.destination);this.buses={soundtrack:this.context.createGain(),foley:this.context.createGain()};for(const lane of ['soundtrack','foley'] as const){this.buses[lane].gain.value=amplitude({scene_s:0,gain_db:this.gainDb,muted:this.mute,lanes:this.lanes},lane);this.buses[lane].connect(this.master);}this.context.onstatechange=()=>{if(this.context?.state==='suspended'&&this.timeline.playing){this.pause();this.onSuspend();}};}await this.context.resume();this.setGain(this.gainDb);if(this.timeline.vertical)await this.prepareAsync();else this.prepare();}
 prepare(){if(!this.context)return;if(this.timeline.vertical){const steps=this.verticalBuffers();let next=steps.next();while(!next.done)next=steps.next();this.preparedVersion=this.timeline.preparationVersion;this.timeline.preparationReady=true;this.timeline.preparationError=null;return;}polyphony(this.timeline.events);let frames=0;const needed=new Set<string>();for(const events of [this.timeline.events,...this.timeline.prepared.values()])for(const e of events){const k=this.key(e);if(needed.has(k))continue;needed.add(k);if(!this.cache.has(k))this.cache.set(k,voice(this.context,e));frames+=this.cache.get(k)!.length;if(frames*4>128*1024*1024)throw Error('Audio preparation memory budget');}for(const k of this.cache.keys())if(!needed.has(k))this.cache.delete(k);
  const reference=this.timeline.original.find(e=>e.midi_pitch!==null&&e.event_type==='note');
  if(reference&&!this.acknowledgements.size)for(let pc=0;pc<12;pc++)this.acknowledgements.set(pc,voice(this.context,{...reference,id:`control-ack-${pc}`,midi_pitch:60+pc,duration_s:.12,velocity:65,articulation:'staccato'}));
  this.preparedVersion=this.timeline.preparationVersion;
 }
 cancelRefresh(){this.refreshToken++;const timer=this.refreshTimer;this.refreshTimer=null;if(timer!==null)clearTimeout(timer);const cancelled=this.refreshCancelled;this.refreshCancelled=null;cancelled?.();}
 startRefresh(){
  this.cancelRefresh();const token=this.refreshToken,epoch=this.timeline.epoch,events=this.timeline.events,tonic=this.timeline.tonic,context=this.context,plan=this.timeline.plan,planHash=this.timeline.planHash,version=this.timeline.preparationVersion;
  const after=this.timeline.pending.at(-1)?.arrival_scene_s??this.timeline.position;
  const valid=()=>token===this.refreshToken&&context===this.context&&epoch===this.timeline.epoch&&events===this.timeline.events&&plan===this.timeline.plan&&planHash===this.timeline.planHash&&version===this.timeline.preparationVersion;
  const engine=this;
  function* work():Generator<void>{
   const result=yield* engine.timeline.nextPreparation(events,tonic,after);
   const needed=new Set<string>();let frames=0;let resident=0;for(const buffer of engine.cache.values()){resident+=buffer.length;yield;}
   for(const list of [events,...result.prepared.values()])for(const event of list){const key=engine.key(event);if(needed.has(key)){yield;continue;}needed.add(key);let buffer=engine.cache.get(key);if(!buffer){const length=Math.max(1,Math.ceil(event.duration_s*context!.sampleRate));if((resident+length)*4>128*1024*1024)throw Error('Audio preparation memory budget');buffer=yield* voiceSteps(context!,event);engine.cache.set(key,buffer);resident+=buffer.length;}frames+=buffer.length;if(frames*4>128*1024*1024)throw Error('Audio preparation memory budget');yield;}
   for(const key of engine.cache.keys()){if(!needed.has(key))engine.cache.delete(key);yield;}
   if(valid()){engine.timeline.commitPreparation(result);engine.preparedVersion=engine.timeline.preparationVersion;}
  }
  const steps=work();this.refreshStats={slices:0,max_slice_ms:0};
  const run=()=>{this.refreshTimer=null;if(!valid())return;const start=performance.now();let done=false;try{do{done=Boolean(steps.next().done);}while(!done&&performance.now()-start<4&&valid());}catch{if(valid()){this.timeline.preparationError='transition_preparation_failed';this.timeline.preparationReady=false;}this.onTick();return;}const elapsed=performance.now()-start;this.refreshStats.slices++;this.refreshStats.max_slice_ms=Math.max(this.refreshStats.max_slice_ms,elapsed);if(!done&&valid())this.refreshTimer=setTimeout(run,0);else this.onTick();};
  this.refreshTimer=setTimeout(run,0);
 }
 now(){return this.timeline.playing&&this.context?Math.min(this.timeline.bundle.scene.duration_s,this.anchorScene+Math.max(0,this.context.currentTime-this.anchorAudio)):this.timeline.position;}
 async play(){if(this.timeline.position>=this.timeline.bundle.scene.duration_s)this.timeline.reset(0,true);await this.unlock();if(this.timeline.position===0){this.completed=false;this.discontinuous=false;this.historyStart=this.timeline.history.length;this.mix=[{scene_s:0,gain_db:this.gainDb,muted:this.mute,lanes:{...this.lanes}}];}this.anchorScene=this.timeline.position;this.anchorAudio=this.context!.currentTime+.06;if(this.windowBus)scheduleWindowFade(this.windowBus.gain,this.timeline.bundle.scene.duration_s,this.anchorAudio,this.anchorScene,this.context!.currentTime);this.timeline.playing=true;this.fill();if(this.timer)clearInterval(this.timer);this.timer=setInterval(()=>this.fill(),25);}
 fill(){if(!this.context||!this.master||!this.timeline.playing)return;const pos=this.now();this.timeline.advance(pos);if(pos>=this.timeline.bundle.scene.duration_s){this.completed=true;this.pause();this.onTick();return;}const now=this.context.currentTime,horizon=now+.15;
  this.nodes=this.nodes.filter(n=>n.end>now);
  for(const e of this.timeline.events){if(e.resolved_time_s>=this.timeline.bundle.scene.duration_s||this.scheduled.has(e.id))continue;const start=this.anchorAudio+e.resolved_time_s-this.anchorScene,end=start+e.duration_s;if(end<=now){this.scheduled.add(e.id);continue;}if(start>horizon)continue;this.scheduled.add(e.id);
   const slice=this.timeline.verticalSlices.get(e.id),bufferEvent=slice?.bufferEvent??e,level=this.noteLevel(e);
   const source=this.context.createBufferSource(),gain=this.context.createGain();source.buffer=this.cache.get(this.key(bufferEvent))!;if(!source.buffer)throw Error('Audio buffer was not prepared');source.connect(gain);gain.connect(this.buses![e.event_type==='foley'?'foley':'soundtrack']);const at=Math.max(now+.002,start),offset=Math.max(0,at-start);if(offset>=e.duration_s)continue;gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(level,at+.003);if(slice&&e.resolved_time_s+e.duration_s<bufferEvent.resolved_time_s+bufferEvent.duration_s-1e-9){gain.gain.setValueAtTime(level,Math.max(at+.003,end-.008));gain.gain.linearRampToValueAtTime(0,end);}source.start(at,offset+(slice?.offset_s??0));source.stop(end+.001);source.onended=()=>{source.disconnect();gain.disconnect();};this.nodes.push({source,gain,event:e,end,source_id:slice?.source_id??e.id,level});this.metrics.push({scene_s:e.resolved_time_s,audio_s:at,event_id:e.id,generation:this.timeline.generation});
  }this.onTick();
 }
 clear(at?:number){this.cancelRefresh();if(!this.context)return;const t=at??this.context.currentTime;for(const n of this.nodes){try{n.gain.gain.cancelScheduledValues(t);n.gain.gain.setValueAtTime(n.gain.gain.value,t);n.gain.gain.linearRampToValueAtTime(0,t+.008);n.source.stop(t+.01);}catch{/*already ended*/}}this.nodes=[];this.scheduled.clear();if(this.timer)clearInterval(this.timer);this.timer=null;}
 pause(){const pos=this.now(),ready=this.preparedVersion===this.timeline.preparationVersion&&this.timeline.preparationReady;if(this.timeline.vertical&&!this.completed&&pos>0)this.discontinuous=true;this.clear();this.timeline.reset(pos);if(this.timeline.vertical){if(ready)this.preparedVersion=this.timeline.preparationVersion;else this.timeline.preparationReady=false;}else this.prepare();this.onTick();}
 seek(at:number){const ready=this.preparedVersion===this.timeline.preparationVersion&&this.timeline.preparationReady;this.completed=false;this.discontinuous=at!==0;this.mix=[];this.clear();this.timeline.reset(at,true);if(this.timeline.vertical){if(ready)this.preparedVersion=this.timeline.preparationVersion;else this.timeline.preparationReady=false;}else this.prepare();this.onTick();}
 applyMix(){if(!this.context||!this.buses)return;const point={scene_s:this.now(),gain_db:this.gainDb,muted:this.mute,lanes:this.lanes};for(const lane of ['soundtrack','foley'] as const)this.buses[lane].gain.setTargetAtTime(amplitude(point,lane),this.context.currentTime,.008);}
 setGain(db:number){if(!Number.isFinite(db)||db< -36||db>0)throw Error('Gain range');this.gainDb=db;this.recordMix();this.applyMix();}
 setMute(mute:boolean){this.mute=mute;this.setGain(this.gainDb);}
 setLanes(lanes:Lanes){this.lanes=lanes;this.recordMix();this.applyMix();}
 private submitVertical(result:Decision){
  const context=this.context!,record=this.timeline.verticalPending(),started:Scheduled[]=[];
  const cancelDyad=()=>{for(const n of started){try{n.source.stop(context.currentTime);}catch{/* not started or already ended */}try{n.source.disconnect();n.gain.disconnect();}catch{/* already disconnected */}}this.nodes=this.nodes.filter(n=>!started.includes(n));};
  try{
   if(this.preparedVersion!==this.timeline.preparationVersion||!this.buses||!record)throw Error('audio_not_prepared');
   if(context.currentTime<this.anchorAudio)throw Error('transport_preroll');
   result.progression_start_audio_s=this.anchorAudio+record.program.start_s-this.anchorScene;
   result.progression_end_audio_s=this.anchorAudio+record.program.end_s-this.anchorScene;
   result.boundary_audio_s=result.arrival_audio_s=this.anchorAudio+record.program.arrival_s-this.anchorScene;
   const at=result.audio_received_s+.02;
   if(context.currentTime>=at||at>=result.progression_start_audio_s!)throw Error('preparation_missed_boundary');
   // The only work before both onsets are scheduled is two cached buffer lookups and two sources.
   for(const event of record.program.acknowledgement){const buffer=this.cache.get(this.key(event));if(!buffer)throw Error('acknowledgement_not_prepared');
    const source=context.createBufferSource(),gain=context.createGain(),level=this.noteLevel(event);source.buffer=buffer;source.connect(gain);gain.connect(this.buses.soundtrack);gain.gain.setValueAtTime(level,at);started.push({source,gain,event,end:at+event.duration_s,level});source.start(at);source.stop(at+event.duration_s+.001);source.onended=()=>{source.disconnect();gain.disconnect();};
   }
   this.nodes.push(...started);result.ack_onset_audio_s=at;
  }catch(error){cancelDyad();this.timeline.cancelVertical(result,error instanceof Error?error.message:String(error));return result;}
  // Full editable score work happens only after both acknowledgement sources have started scheduling.
  try{this.timeline.acknowledgeVertical(result,result.ack_onset_audio_s!);}catch(error){this.timeline.cancelVertical(result,error instanceof Error?error.message:String(error));cancelDyad();this.timeline.rebuildVerticalEvents();return result;}
  const at=result.progression_start_audio_s!;
  for(const n of this.nodes)if(!started.includes(n)&&isVerticalVoice(n.event)&&n.end>at){try{n.gain.gain.setValueAtTime(n.level??1,at-.008);n.gain.gain.linearRampToValueAtTime(0,at);n.source.stop(at);n.end=at;}catch{/* already stopped */}}
  // A sounding original now ends at the overlay. Mark its before-fragment as already covered.
  for(const slice of this.timeline.verticalSlices.values())if(slice.event.resolved_time_s<result.progression_start_s!)for(const n of this.nodes)if(n.source_id===slice.source_id&&n.event.resolved_time_s<=slice.event.resolved_time_s&&n.end>=this.anchorAudio+slice.event.resolved_time_s+slice.event.duration_s-this.anchorScene-1e-9)this.scheduled.add(slice.event.id);
  return result;
 }
 submit(action:ControlAction){if(!this.context)throw Error('Audio context unavailable');const result=this.timeline.submit(action,this.context.currentTime,this.now());if(result.status==='queued'&&this.timeline.vertical){this.submitVertical(result);this.onTick();return result;}if(result.status==='queued'){
   try{if(this.preparedVersion!==this.timeline.preparationVersion||!this.buses)throw Error('audio_not_prepared');if(this.context.currentTime+.02>=this.anchorAudio+result.boundary_s!-this.anchorScene)throw Error('preparation_missed_boundary');const buffer=this.acknowledgements.get(this.timeline.previousTonic);if(!buffer)throw Error('acknowledgement_not_prepared');
    const node=this.context.createBufferSource(),gain=this.context.createGain(),at=this.context.currentTime+.01;node.buffer=buffer;node.connect(gain);gain.connect(this.buses.soundtrack);node.start(at);node.onended=()=>{node.disconnect();gain.disconnect();};this.nodes.push({source:node,gain,event:{midi_pitch:null} as ScoreEvent,end:at+buffer.duration});result.ack_onset_audio_s=at;
    result.boundary_audio_s=this.anchorAudio+result.boundary_s!-this.anchorScene;result.arrival_audio_s=this.anchorAudio+result.arrival_scene_s!-this.anchorScene;
   }catch(error){this.timeline.events=this.timeline.beforePending!;this.timeline.tonic=this.timeline.previousTonic;this.timeline.beforePending=null;this.timeline.pending=[];this.timeline.preparationReady=true;result.status='suppressed';result.reason=String(error);return result;}
   const at=this.anchorAudio+result.boundary_s!-this.anchorScene;
   // Previously scheduled sustains end at the future boundary; replacements start there.
   for(const n of this.nodes)if(n.event.midi_pitch!==null&&n.end>at){try{n.gain.gain.setValueAtTime(1,at-.008);n.gain.gain.linearRampToValueAtTime(0,at);n.source.stop(at);}catch{/*already stopped*/}}
   // Boundary lies beyond the scheduling horizon; its replacement IDs have not been scheduled.
   this.startRefresh();
  }this.onTick();return result;}
 async close(){this.clear();this.timeline.playing=false;this.cache.clear();this.acknowledgements.clear();await this.context?.close();this.context=null;}
}
