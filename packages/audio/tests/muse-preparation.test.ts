import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Engine} from '../engine';
import {Timeline} from '../transport';
import {copy,keyboardAction,transition,type Bundle} from '../model';
import fixture from './fixture.json';

function setup(bundle=copy(fixture.bundle) as unknown as Bundle,rate=8000){
 const plan=JSON.parse(bundle.plan_bytes),timeline=new Timeline(bundle,plan,'a'.repeat(64)),engine=new Engine(timeline),starts:number[]=[];
 const parameter=()=>({value:1,setValueAtTime(){},linearRampToValueAtTime(){},cancelScheduledValues(){},setTargetAtTime(){}});
 const gain=()=>({gain:parameter(),connect(){},disconnect(){}});
 const context={currentTime:1,sampleRate:rate,createGain:gain,createBuffer:(_channels:number,n:number,sampleRate:number)=>{const samples=new Float32Array(n);return {length:n,duration:n/sampleRate,getChannelData:()=>samples};},createBufferSource:()=>({connect(){},disconnect(){},start(at:number){starts.push(at);},stop(){}}),async close(){}};
 engine.context=context as unknown as AudioContext;engine.buses={soundtrack:gain(),foley:gain()} as unknown as Engine['buses'];engine.master=gain() as unknown as GainNode;engine.anchorAudio=0;engine.anchorScene=0;engine.prepare();timeline.playing=true;
 return {engine,timeline,plan,context,starts};
}
async function ready(engine:Engine){const until=Date.now()+15000;while(engine.refreshTimer!==null&&Date.now()<until)await new Promise(resolve=>setTimeout(resolve,5));assert.equal(engine.refreshTimer,null,'bounded preparation must finish');assert.equal(engine.timeline.preparationReady,true,engine.timeline.preparationError??'preparation incomplete');}
function submit(s:ReturnType<typeof setup>,sign=2){return s.engine.submit(keyboardAction(s.plan,s.timeline.planHash,s.timeline.epoch,s.context.currentTime,sign,'KEYBOARD'));}

test('cooperative tables exactly match synchronous transition output',()=>{
 const s=setup();try{const d=submit(s);s.engine.cancelRefresh();const steps=s.timeline.nextPreparation(s.timeline.events,s.timeline.tonic,d.arrival_scene_s!);let next=steps.next();while(!next.done)next=steps.next();for(const [key,events] of next.value.prepared){const [tick,sign]=key.split(':').map(Number);assert.deepEqual(events,transition(s.timeline.events,s.plan,s.timeline.bundle.composition,tick,sign,s.timeline.tonic));}}finally{s.engine.clear();}
});

test('ack returns before preparation and arrival never runs synchronous refresh',async()=>{
 const s=setup();try{
  const d=submit(s);assert.equal(d.status,'queued');assert.equal(d.ack_onset_audio_s,1.01);assert.equal(s.engine.refreshStats.slices,0);assert.equal(s.timeline.preparationReady,false);
  s.context.currentTime=d.arrival_scene_s!;s.engine.prepare=()=>{throw Error('forbidden synchronous arrival preparation');};s.engine.fill();assert.equal(d.status,'executed');assert.equal(submit(s).reason,'transition_preparation_pending');
  await ready(s.engine);assert.ok(s.engine.refreshStats.slices>1);s.context.currentTime+=.01;assert.equal(submit(s).status,'queued');
 }finally{await s.engine.close();}
});

test('pause and seek cancel staged buffers/tables without a stale commit',async()=>{
 const s=setup();try{
  submit(s);s.context.currentTime=1.1;s.engine.pause();const pauseVersion=s.timeline.preparationVersion;assert.equal(s.engine.refreshTimer,null);assert.equal(s.timeline.tonic,0);await new Promise(resolve=>setTimeout(resolve,20));assert.equal(s.timeline.preparationVersion,pauseVersion);
  s.timeline.playing=true;submit(s);s.engine.seek(0);const seekVersion=s.timeline.preparationVersion;await new Promise(resolve=>setTimeout(resolve,20));assert.equal(s.timeline.preparationVersion,seekVersion);assert.deepEqual(s.timeline.events,s.timeline.original);assert.equal(s.engine.refreshTimer,null);
 }finally{await s.engine.close();}
});

test('direct epoch reset invalidates staged preparation',async()=>{
 const s=setup();try{submit(s);s.timeline.reset(0,true);const version=s.timeline.preparationVersion;await new Promise(resolve=>setTimeout(resolve,20));assert.equal(s.timeline.preparationVersion,version);assert.equal(s.engine.refreshTimer,null);assert.deepEqual(s.timeline.events,s.timeline.original);}finally{await s.engine.close();}
});

test('new plan identity cancels staged preparation without publication',async()=>{
 const s=setup();try{submit(s);const version=s.timeline.preparationVersion;s.timeline.plan=copy(s.plan);s.timeline.planHash='b'.repeat(64);await new Promise(resolve=>setTimeout(resolve,20));assert.equal(s.timeline.preparationVersion,version);assert.equal(s.engine.refreshTimer,null);assert.equal(s.timeline.preparationReady,false);}finally{await s.engine.close();}
});

const defaultPath=process.env.SCENESCORE_DEFAULT_BUNDLE??new URL('../../../apps/web/public/studio/contact-brush_swing_light_v1.json',import.meta.url).pathname;
test('actual default bundle stays within memory across two async modulations and reset',{skip:!fs.existsSync(defaultPath)},async()=>{
 const s=setup(JSON.parse(fs.readFileSync(defaultPath,'utf8')),48000);try{
  const bytes=()=>[...s.engine.cache.values()].reduce((sum,b)=>sum+b.length*4,0);
  assert.ok(bytes()<128*1024*1024);const first=submit(s);s.context.currentTime=first.arrival_scene_s!;s.timeline.advance(s.context.currentTime);await ready(s.engine);s.context.currentTime+=.01;
  const second=submit(s);assert.equal(second.status,'queued');s.context.currentTime=second.arrival_scene_s!;s.timeline.advance(s.context.currentTime);await ready(s.engine);
  assert.equal(s.timeline.tonic,4);assert.ok(bytes()<128*1024*1024);assert.ok(s.timeline.events.every(e=>s.engine.cache.has(s.engine.key(e))));assert.equal(s.engine.gainDb,-18);
  const stats={events:s.timeline.original.length,bytes:bytes(),slices:s.engine.refreshStats.slices,max_slice_ms:s.engine.refreshStats.max_slice_ms};s.engine.seek(0);assert.equal(s.timeline.tonic,0);assert.deepEqual(s.timeline.events,s.timeline.original);assert.equal(s.engine.refreshTimer,null);console.log('synthetic AudioContext preparation evidence',JSON.stringify(stats));
 }finally{await s.engine.close();}
});
