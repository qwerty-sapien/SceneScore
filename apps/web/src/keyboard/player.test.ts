import test from 'node:test';
import assert from 'node:assert/strict';
import {KeyboardPlayer} from './player';
import {BAR,BEAT,type Settings} from '../../../../packages/audio/keyboard-score';
import {LOOP,compileDuet,eventWindow,type SceneMarker} from '../../../../packages/audio/keyboard-scenes';
import {voice} from '../../../../packages/audio/engine';
import {keyboardVoice} from '../../../../packages/audio/keyboard-voice';
const base:Settings={transpose:0,ornament:'plain',touch:'detached'};
const compile=(markers:SceneMarker[]=[],transpose=0)=>compileDuet(0,LOOP,markers,[{at:0,settings:{...base,transpose}}],'a'.repeat(64));
test('contact chord at browser sample rates preserves the existing guitar waveform',()=>{
 for(const rate of [44100,48000]){
  const context={sampleRate:rate,createBuffer:(_c:number,n:number)=>{const data=new Float32Array(n);return {getChannelData:()=>data};}} as unknown as BaseAudioContext;
  const notes=compile([{id:1,kind:3,at:BAR}]).filter(e=>e.phrasing.includes('Contact'));
  const start=performance.now(),actual=notes.map(e=>keyboardVoice(context,e).getChannelData(0)),elapsed=performance.now()-start;
  let maxError=0;
  notes.forEach((e,j)=>{const expected=voice(context,e).getChannelData(0);for(let i=0;i<expected.length;i++)maxError=Math.max(maxError,Math.abs(expected[i]-actual[j][i]));});
  assert.ok(maxError<1e-6,`waveform error ${maxError}`);
  console.log(JSON.stringify({contact_sample_rate:rate,optimized_ms:elapsed,maxError}));
 }
});
function rig(){
 const sources:{stopped:boolean;start:number}[]=[];
 const gain=()=>({gain:{value:1,setValueAtTime(){},linearRampToValueAtTime(){},cancelScheduledValues(){}},connect(){},disconnect(){}});
 const ctx={currentTime:10,state:'running',sampleRate:8000,createGain:gain,createBuffer:(_c:number,n:number)=>{const data=new Float32Array(n);return {length:n,getChannelData:()=>data};},createBufferSource:()=>{
  const record={stopped:false,start:0};sources.push(record);return {buffer:null,connect(){},disconnect(){},start(at:number){record.start=at;},stop(){record.stopped=true;}};
 }};
 const player=new KeyboardPlayer();player.context=ctx as unknown as AudioContext;player.master=gain() as unknown as GainNode;
 player.anchor=10;player.lastFill=10;player.running=true;player.configHash='a'.repeat(64);player.rebuild(0);return {player,ctx,sources};
}
test('baseline contains only piano accompaniment and guitar melody',()=>{
 const events=compile();assert.deepEqual([...new Set(events.map(e=>e.lane_id))].sort(),['guitar','piano']);
 assert.ok(events.every(e=>e.event_type==='note'&&e.instrument_id===(e.lane_id==='piano'?'piano_felt_comp_v1':'guitar_fingerstyle_v1')));
});
test('approach rises chromatically before marker, separation descends after it',()=>{
 for(const kind of [0,2]){
  const marker={id:1,kind,at:BAR},events=compile([marker]).filter(e=>e.phrasing.startsWith('scene-replacement'));
  assert.equal(events.length,5);assert.equal(events[0].resolved_time_s,kind===0?BAR-2*BEAT:BAR);
  for(let i=1;i<events.length;i++)assert.equal(events[i].midi_pitch!-events[i-1].midi_pitch!,kind===0?1:-1);
  const window=eventWindow(kind,BAR);
  assert.ok(!compile([marker]).some(e=>e.lane_id==='piano'&&!e.phrasing.startsWith('scene-replacement')&&e.resolved_time_s<window.end&&e.resolved_time_s+e.duration_s>window.start+1e-8));
 }
});
test('near miss cuts sounding notes as well as onsets, including across the loop seam',()=>{
 for(const at of [BAR,.1]){
  const events=compile([{id:1,kind:1,at}]);
  for(const e of events)for(const markerAt of [at,at+LOOP])assert.ok(!(e.resolved_time_s<markerAt-1e-8&&e.resolved_time_s+e.duration_s>markerAt-BEAT/2+1e-8));
 }
});
test('contact is a guitar chord; hold is one sustained note per part; riffs replace guitar',()=>{
 for(const kind of [3,4,5,6]){
  const events=compile([{id:1,kind,at:BAR}]),replacement=events.filter(e=>e.phrasing.startsWith('scene-replacement'));
  assert.ok(replacement.length);assert.ok(!events.some(e=>e.lane_id==='guitar'&&!e.phrasing.startsWith('scene-replacement')&&e.resolved_time_s>=BAR&&e.resolved_time_s<BAR+2*BEAT));
  if(kind===3){assert.equal(replacement.length,4);assert.ok(replacement.every(e=>e.lane_id==='guitar'&&e.resolved_time_s===BAR));}
  if(kind===4){assert.equal(replacement.length,2);assert.ok(replacement.every(e=>e.duration_s===2*BEAT));}
 }
});
test('silence wins overlaps, key changes retune every replacement and split holds',()=>{
 const markers=[{id:1,kind:4,at:BAR-.2},{id:2,kind:1,at:BAR+.5}];
 const events=compileDuet(0,LOOP,markers,[{at:0,settings:base},{at:BAR,settings:{...base,transpose:2}}],'a'.repeat(64));
 assert.ok(!events.some(e=>e.resolved_time_s<BAR+.5&&e.resolved_time_s+e.duration_s>BAR+.5-BEAT/2+1e-8));
 for(let kind=0;kind<7;kind++){
  const markers=[{id:1,kind,at:BAR}];const a=compile(markers),b=compile(markers,2);
  assert.deepEqual(b,a.map(e=>({...e,midi_pitch:e.midi_pitch!+2})));
 }
 const held=compileDuet(0,LOOP,[{id:1,kind:4,at:BAR-.2}],[{at:0,settings:base},{at:BAR,settings:{...base,transpose:2}}],'a'.repeat(64)).filter(e=>e.phrasing.startsWith('scene-replacement')&&e.lane_id==='guitar');
 assert.equal(held[1].midi_pitch!-held[0].midi_pitch!,2);assert.equal(held[1].resolved_time_s,BAR);
});
test('live edits cut queued/active audio and replace the passage without extra cues',()=>{
 const {player,ctx,sources}=rig();player.fill();ctx.currentTime+=.05;player.addScene(1,.2);player.fill();
 assert.ok(sources.some(s=>s.stopped));assert.ok(!player.events.some(e=>e.id.includes('scene:edit')));
 assert.ok(!player.compiled.some(e=>e.resolved_time_s<.2));
 player.clearScenes();assert.ok(player.compiled.some(e=>e.resolved_time_s<.2));player.stop();
 assert.equal(player.nodes.size,0);assert.equal(player.scheduled.size,0);
});
test('approach resolves chromatically into a queued arrival key',()=>{
 const events=compileDuet(0,LOOP,[{id:1,kind:0,at:BAR}],[{at:0,settings:base},{at:BAR,settings:{...base,transpose:-2}}],'a'.repeat(64)).filter(e=>e.phrasing.startsWith('scene-replacement'));
 assert.equal(events.length,5);for(let i=1;i<events.length;i++)assert.equal(events[i].midi_pitch!-events[i-1].midi_pitch!,1);
 assert.equal(events[4].midi_pitch,46);
});
test('key controls stay at bar boundary and preserve guitar touch',()=>{
 const {player,ctx}=rig();player.fill();player.change('legato');player.change('keyUp');assert.equal(player.settings.transpose,0);
 for(let t=10.025;t<10+BAR+.05;t+=.025){ctx.currentTime=t;player.fill();}
 assert.equal(player.settings.transpose,2);assert.equal(player.settings.touch,'legato');assert.equal(player.pendingKey,null);player.stop();
});
test('loop playback continues beyond 120 seconds, while stall guard and export bound remain',()=>{
 const {player,ctx}=rig();for(let t=10;t<132;t+=.05){ctx.currentTime=t;player.fill();}
 assert.equal(player.running,true);assert.ok(player.events.every(e=>e.resolved_time_s<120));
 ctx.currentTime+=1;player.fill();assert.equal(player.running,false);assert.equal(player.duration,120);
});
test('scheduler exceptions stop cleanly and reach the visible error callback',()=>{
 const {player}=rig();let message='';player.onError=m=>{message=m;};
 player.schedule=()=>{throw Error('test audio failure');};player.tick();
 assert.equal(player.running,false);assert.match(message,/test audio failure/);assert.equal(player.nodes.size,0);
});
test('seven replaced duet mixes render finite, non-silent and unclipped at maximum gain',()=>{
 const rate=8000,context={sampleRate:rate,createBuffer:(_c:number,n:number)=>{const data=new Float32Array(n);return {getChannelData:()=>data};}} as unknown as BaseAudioContext;
 let maximumPeak=0,minimumRms=Infinity;
 for(let kind=0;kind<7;kind++){
  const samples=new Float32Array(rate*LOOP);
  for(const e of compile([{id:1,kind,at:BAR}])){
   const pcm=voice(context,e).getChannelData(0),start=Math.round(e.resolved_time_s*rate);
   for(let i=0;i<pcm.length&&start+i<samples.length;i++)samples[start+i]+=pcm[i]*10**(-6/20);
  }
  let sum=0;for(const value of samples){assert.ok(Number.isFinite(value));assert.ok(Math.abs(value)<1);sum+=value*value;maximumPeak=Math.max(maximumPeak,Math.abs(value));}
  const rms=Math.sqrt(sum/samples.length);assert.ok(rms>.001);minimumRms=Math.min(minimumRms,rms);
 }
 console.log(JSON.stringify({duet_variants:7,mode:'procedural_pcm_array',maximumPeak,minimumRms,physical_output:'NOT_RUN'}));
});
