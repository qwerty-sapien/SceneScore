import test from 'node:test';
import assert from 'node:assert/strict';
import {SCORE,BAR,scoreStep,stepTime,trimTrack,shifted,type Settings} from '../keyboard-score';
import {voice} from '../engine';
import {hash} from '../model';

const base:Settings={transpose:0,ornament:'plain',touch:'detached'};
test('key change preserves timing, gain and touch, transposing every pitched lane',()=>{
 for(let step=0;step<32;step++){
  const a=scoreStep(step,base,'a'.repeat(64)),b=scoreStep(step,{...base,transpose:2},'a'.repeat(64));
  assert.deepEqual(b,a.map(e=>({...e,midi_pitch:e.midi_pitch===null?null:e.midi_pitch+2})));
 }
 assert.equal(shifted(12,2),12);assert.equal(shifted(-12,-2),-12);
});
test('ornaments preserve rests and accompaniment, and remain inside their swung note slot',()=>{
 for(const ornament of ['plain','grace','turn','trill'] as const)for(let step=0;step<32;step++){
  const original=scoreStep(step,base,'a'.repeat(64)),events=scoreStep(step,{...base,ornament},'a'.repeat(64));
  assert.deepEqual(events.filter(e=>e.lane_id!=='guitar'),original.filter(e=>e.lane_id!=='guitar'));
  assert.equal(events.some(e=>e.lane_id==='guitar'),original.some(e=>e.lane_id==='guitar'));
  for(const e of events.filter(e=>e.lane_id==='guitar')){assert.ok(e.duration_s>0);assert.ok(e.resolved_time_s>=stepTime(step));assert.ok(e.resolved_time_s+e.duration_s<=stepTime(step+1)+1e-8);}
 }
 assert.equal(stepTime(8),BAR);assert.equal(stepTime(32),BAR*4);
});
test('trim excludes future events and shortens sounding notes at stop',()=>{
 const events=scoreStep(0,base,'a'.repeat(64));const trimmed=trimTrack(events,.1);
 assert.ok(trimmed.length>0);assert.ok(trimmed.every(e=>e.resolved_time_s+e.duration_s<=.1));
 assert.equal(trimTrack(events,0).length,0);assert.ok(events.some(e=>e.duration_s>.1));
});
test('actual procedural PCM is non-silent and unclipped for all ornaments and touches',async()=>{
 const rate=8000,configHash=await hash(SCORE);
 const context={sampleRate:rate,createBuffer:(_channels:number,n:number)=>{const values=new Float32Array(n);return {length:n,getChannelData:()=>values};}} as unknown as BaseAudioContext;
 let minRms=Infinity,maxPeak=0;
 for(const ornament of ['plain','grace','turn','trill'] as const)for(const touch of ['detached','staccato','legato'] as const){
  const samples=new Float32Array(Math.ceil(BAR*4*rate));
  for(let step=0;step<32;step++)for(const event of scoreStep(step,{...base,ornament,touch},configHash)){
   const data=voice(context,event).getChannelData(0),start=Math.round(event.resolved_time_s*rate);
   for(let i=0;i<data.length&&start+i<samples.length;i++)samples[start+i]+=data[i]*10**(-6/20);
  }
  let sum=0,peak=0;for(const value of samples){assert.ok(Number.isFinite(value));sum+=value*value;peak=Math.max(peak,Math.abs(value));}
  const rms=Math.sqrt(sum/samples.length);assert.ok(rms>.001);assert.ok(peak<1);minRms=Math.min(minRms,rms);maxPeak=Math.max(maxPeak,peak);
 }
 console.log(JSON.stringify({mode:'procedural_pcm_array',sample_rate:rate,variants:12,duration_s:BAR*4,maxPeak,minRms,physical_output:'NOT_RUN'}));
});
