import type {ScoreEvent} from '../../../../packages/contracts/generated';
import {keyboardVoice} from '../../../../packages/audio/keyboard-voice';
import {hash} from '../../../../packages/audio/model';
import {SCORE,trimTrack,shifted,LIMIT,type Settings,type Ornament,type Touch} from '../../../../packages/audio/keyboard-score';
import {LOOP,SCENE_EVENTS,compileTimedDuet,settingsAt,type SceneMarker,type SettingPoint} from '../../../../packages/audio/keyboard-scenes';

export class KeyboardPlayer{
 context:AudioContext|null=null;master:GainNode|null=null;
 timer:ReturnType<typeof setInterval>|null=null;
 nodes=new Set<AudioBufferSourceNode>();
 scheduled=new Map<AudioBufferSourceNode,{event:ScoreEvent;gain:GainNode}>();
 markers:SceneMarker[]=[];markerId=0;
 loopDuration=LOOP;sourceIdentity:unknown=null;
 get beatDuration(){return this.loopDuration/16;}
 get barDuration(){return this.loopDuration/4;}
 events:ScoreEvent[]=[];actions:{at:number;action:string;effective_s:number|null}[]=[];
 settings:Settings={transpose:0,ornament:'plain',touch:'detached'};
 points:SettingPoint[]=[{at:0,settings:{...this.settings}}];
 pendingKey:number|null=null;pendingAt=0;
 running=false;starting=false;generation=0;duration=0;anchor=0;configHash='';
 gainDb=-12;takeGainDb=-12;initialSettings:Settings={...this.settings};
 compiled:ScoreEvent[]=[];compiledEnd=0;cursor=0;lastFill=0;revision=0;
 onUpdate=()=>{};
 onError=(message:string)=>{};
 tick(){try{this.fill();}catch(error){this.log(`Playback error: ${String(error)}`,null);this.stop();this.onError(String(error));}}
 now(){return this.running&&this.context?Math.max(0,this.context.currentTime-this.anchor):this.duration;}
 async start(){
  if(this.running||this.starting)return;
  this.starting=true;const generation=++this.generation;
  try{
   this.context??=new AudioContext();
   if(!this.master){this.master=this.context.createGain();this.master.connect(this.context.destination);}
   await this.context.resume();this.initialSettings={...this.settings};this.takeGainDb=this.gainDb;
   this.configHash=await hash({...SCORE,settings:this.initialSettings,gainDb:this.takeGainDb,loop_duration_s:this.loopDuration,source:this.sourceIdentity});
   if(generation!==this.generation)return;
   this.events=[];this.actions=[];this.duration=0;this.pendingKey=null;
   this.points=[{at:0,settings:{...this.settings}}];this.master.gain.value=10**(this.gainDb/20);
   this.anchor=this.context.currentTime+.12;this.running=true;this.lastFill=this.context.currentTime;
   this.rebuild(0);this.context.onstatechange=()=>{if(this.context?.state!=='running'&&this.running)this.stop();};
   this.fill();this.timer=setInterval(()=>this.tick(),25);
  }finally{this.starting=false;this.onUpdate();}
 }
 rebuild(at:number){
  this.revision++;
  this.compiledEnd=(Math.floor(at/this.loopDuration)+2)*this.loopDuration;
  this.compiled=compileTimedDuet(at,this.compiledEnd,this.markers,this.points,this.configHash,this.loopDuration);
  this.cursor=0;
 }
 fill(){
  if(!this.running||!this.context||!this.master)return;
  if(this.context.currentTime-this.lastFill>.2){this.log('Stopped: scheduling interrupted',null);this.stop();this.onError('Playback stopped because audio scheduling fell behind. Your scene events are preserved; press Play to resume.');return;}
  this.lastFill=this.context.currentTime;
  const now=this.now(),horizon=this.context.currentTime-this.anchor+.09;
  if(this.pendingKey!==null&&now>=this.pendingAt){this.settings={...this.settings,transpose:this.pendingKey};this.pendingKey=null;}

  while(this.cursor<this.compiled.length&&this.compiled[this.cursor].resolved_time_s<horizon){
   const event=this.compiled[this.cursor++];if(event.resolved_time_s+event.duration_s>now)this.schedule(event);
  }
  if(horizon>=this.compiledEnd){const at=this.compiledEnd;this.rebuild(at);while(this.cursor<this.compiled.length&&this.compiled[this.cursor].resolved_time_s<horizon)this.schedule(this.compiled[this.cursor++]);}
  this.onUpdate();
 }
 schedule(raw:ScoreEvent){
  if(!this.context||!this.master)return;
  const event={...raw,id:`${raw.id}:revision:${this.revision}`};
  const buffer=keyboardVoice(this.context,event);
  const source=this.context.createBufferSource(),gain=this.context.createGain();source.buffer=buffer;
  source.connect(gain);gain.connect(this.master);
  const at=Math.max(this.context.currentTime,this.anchor+event.resolved_time_s);
  gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(1,at+.005);
  source.onended=()=>{source.disconnect();gain.disconnect();this.nodes.delete(source);this.scheduled.delete(source);};
  source.start(at);this.nodes.add(source);this.scheduled.set(source,{event,gain});
  if(event.resolved_time_s<LIMIT)this.events.push(event);
 }
 refreshFuture(at=this.now()+.012){
  if(!this.running||!this.context)return;
  for(const [source,{event,gain}] of this.scheduled){
   if(event.resolved_time_s+event.duration_s<=at)continue;
   if(event.resolved_time_s>=at){source.stop();source.disconnect();gain.disconnect();this.nodes.delete(source);this.scheduled.delete(source);}
   else{gain.gain.cancelScheduledValues(this.anchor+at-.008);gain.gain.setValueAtTime(1,this.anchor+at-.008);gain.gain.linearRampToValueAtTime(0,this.anchor+at);source.stop(this.anchor+at);}
  }
  this.events=trimTrack(this.events,at);this.rebuild(at);
 }
 log(action:string,effective_s:number|null){this.actions.push({at:this.now(),action,effective_s});this.actions=this.actions.slice(-2000);}
 addScene(kind:number,at:number){
  if(this.starting||!Number.isInteger(kind)||kind<0||kind>=7||!Number.isFinite(at)||this.markers.length>=64)return;
  const marker={id:++this.markerId,kind,at:Math.max(0,Math.min(this.loopDuration-.001,at))};this.markers=[...this.markers,marker];
  this.refreshFuture();this.log(`Replace passage: ${SCENE_EVENTS[kind].name} at ${marker.at.toFixed(3)}s`,this.running?this.now()+.012:null);this.onUpdate();
 }
 removeScene(id:number){this.markers=this.markers.filter(m=>m.id!==id);this.refreshFuture();this.log('Remove scene event',this.now()+.012);this.onUpdate();}
 clearScenes(){this.markers=[];this.refreshFuture();this.log('Clear scene events',this.now()+.012);this.onUpdate();}
 loadScene(loopDuration:number,markers:SceneMarker[],sourceIdentity:unknown=null){
  if(this.running||this.starting)throw Error('Stop playback before changing the scene');
  if(!Number.isFinite(loopDuration)||loopDuration<2||loopDuration>120||markers.length>64||markers.some(m=>!Number.isInteger(m.kind)||m.kind<0||m.kind>6||!Number.isFinite(m.at)||m.at<0||m.at>=loopDuration))throw Error('Invalid scene timeline');
  this.loopDuration=loopDuration;this.sourceIdentity=sourceIdentity;
  this.markers=markers.map((m,i)=>({...m,id:i+1}));this.markerId=this.markers.length;
  this.events=[];this.actions=[];this.duration=0;this.pendingKey=null;this.configHash='';this.onUpdate();
 }
 change(action:'keyUp'|'keyDown'|Ornament|Touch){
  if(this.starting)return;
  if(action==='keyUp'||action==='keyDown'){
   const next=shifted(this.pendingKey??this.settings.transpose,action==='keyUp'?2:-2);
   if(this.running){
    const at=Math.ceil((this.now()+.1)/this.barDuration)*this.barDuration;this.pendingKey=next;this.pendingAt=at;
    this.points=this.points.filter(p=>p.at<at);this.points.push({at,settings:{...settingsAt(this.points,at),transpose:next}});
    this.refreshFuture();
   }else this.settings={...this.settings,transpose:next};
  }else{
   const change=['plain','grace','turn','trill'].includes(action)?{ornament:action as Ornament}:{touch:action as Touch};
   this.settings={...this.settings,...change};
   if(this.running){const at=this.now()+.012;this.points=this.points.map(p=>p.at>=at?{...p,settings:{...p.settings,...change}}:p);this.points.push({at,settings:{...this.settings}});this.points.sort((a,b)=>a.at-b.at);this.refreshFuture(at);}
  }
  if(this.running)this.log(action,action==='keyUp'||action==='keyDown'?this.pendingAt:this.now()+.012);
  this.onUpdate();
 }
 stop(){
  this.generation++;this.duration=Math.min(LIMIT,this.now());this.running=false;this.pendingKey=null;
  if(this.timer!==null)clearInterval(this.timer);this.timer=null;
  for(const node of this.nodes){try{node.stop();}catch{}node.disconnect();}this.nodes.clear();
  for(const {gain} of this.scheduled.values())gain.disconnect();this.scheduled.clear();
  this.events=trimTrack(this.events,this.duration);this.onUpdate();
 }
 async close(){this.stop();await this.context?.close();this.context=null;this.master=null;}
}
