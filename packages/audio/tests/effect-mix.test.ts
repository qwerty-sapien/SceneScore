import test from 'node:test';
import assert from 'node:assert/strict';
import {duckAt,duckPoints,prepareEffectMix,scheduleDucking,EFFECT_MIX} from '../effect-mix';
import {createVideoScore} from '../video-accompaniment';
import type {ScoreEvent} from '../../contracts/generated';
const event=(id:string,start:number,duration:number,kind='foley')=>({id,resolved_time_s:start,duration_s:duration,event_type:kind} as ScoreEvent);
const near=(a:number,b:number)=>assert.ok(Math.abs(a-b)<1e-6,`${a} != ${b}`);
test('music fades down before contact, holds at 80%, and recovers after the tail',()=>{
 const points=duckPoints([event('hit',1,.2)],3);
 near(duckAt(points,.92),1);near(duckAt(points,.96),.9);near(duckAt(points,1),.8);near(duckAt(points,1.2),.8);near(duckAt(points,1.325),.9);near(duckAt(points,1.45),1);
});
test('overlapping and close effects share one duck; seeking reconstructs the envelope',()=>{
 const points=duckPoints([event('a',1,.4),event('b',1.2,.5),event('c',1.8,.1)],3);
 near(duckAt(points,1.75),.8);near(duckAt(points,2.15),1);
 const calls:number[][]=[],param={cancelScheduledValues:()=>{},setValueAtTime:(v:number,t:number)=>calls.push([v,t]),linearRampToValueAtTime:(v:number,t:number)=>calls.push([v,t])} as unknown as AudioParam;
 scheduleDucking(param,points,10,1.3,9.94);near(calls[0][0],.8);assert.ok(calls.every(c=>c[1]>=9.94));
 calls.length=0;scheduleDucking(param,points,10,1.3,10,false);assert.deepEqual(calls,[[1,10]]);
});
test('effect RMS is 20% above ducked music, including overlapping effects',()=>{
 const base=event('base',0,3,'note'),a=event('a',1,.2),b=event('b',1,.2),events=[base,a,b];
 const mix=prepareEffectMix(events,3,1000,e=>({data:new Float32Array(Math.ceil(e.duration_s*1000)).fill(e===base?.1:.01)}));
 const combined=.02*mix.levels.get('a')!;near(combined/(.1*.8),1.2);near(mix.levels.get('a')!,mix.levels.get('b')!);
});
test('no effects means no duck; a silent base does not erase or infinitely amplify effects',()=>{
 assert.deepEqual(duckPoints([],3),[{time:0,gain:1}]);
 const hit=event('hit',0,.2),mix=prepareEffectMix([hit],1,1000,()=>({data:new Float32Array(200).fill(.01)}));assert.equal(mix.levels.get('hit'),1);
 assert.equal(EFFECT_MIX.music_gain,.8);
});
test('all supported clip lengths receive deterministic, full-length original scores',async()=>{
 for(const duration of [2,6,8,8.7,9,30,120]){
  const score=await createVideoScore('a'.repeat(64),duration,42);assert.equal(score.approval,null);assert.equal(score.basis,'video-only');
  assert.ok(score.events.every(e=>e.resolved_time_s>=0&&e.resolved_time_s+e.duration_s<=duration+1e-8));
  assert.ok(Math.max(...score.events.map(e=>e.resolved_time_s+e.duration_s))>=duration-.3);
  assert.ok(score.tempo_bpm>65&&score.tempo_bpm<300);
  assert.deepEqual(score,await createVideoScore('a'.repeat(64),duration,42));
 }
 await assert.rejects(createVideoScore('a'.repeat(64),121));
});

test('effects at the clip edges retain the full duck without duplicate automation times',()=>{
 const points=duckPoints([event('edge',0,3)],3);
 assert.deepEqual(points,[{time:0,gain:.8},{time:3,gain:.8}]);near(duckAt(points,2.99),.8);
});
