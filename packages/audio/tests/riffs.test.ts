import test from 'node:test';
import assert from 'node:assert/strict';
import {voice} from '../engine';
import {stemsFor,stemFor,polyphony} from '../mix';
import {verifyBundle,verifyApproval,approve,transition,copy,type Bundle} from '../model';
import fixture from './riff-fixture.json';
import legacy from './fixture.json';
import type {ScoreEvent} from '../../contracts/generated';
const b=fixture as unknown as Bundle;
const ctx={sampleRate:48000,createBuffer:(_c:number,n:number)=>{const v=new Float32Array(n);return {length:n,getChannelData:()=>v};}} as unknown as BaseAudioContext;
const note={...b.events.find(e=>e.midi_pitch!==null)!,midi_pitch:69,duration_s:.5,velocity:100,dynamics_db:0,articulation:'ring'};
const energy=(v:Float32Array)=>v.reduce((s,x)=>s+x*x,0);

test('bound original score verifies and changed audio or recipe fails closed',async()=>{
 await verifyBundle(b);
 for(const mutate of [(c:Bundle)=>c.events[0].velocity--,(c:Bundle)=>{c.sound_design!.lead='vibraphone';},(c:Bundle)=>{delete c.sound_design;}]){
  const c=copy(b);mutate(c);await assert.rejects(verifyBundle(c));
 }
 const p=JSON.parse(b.plan_bytes),approval=await approve(p,'fixture',true);
 const c=copy(b);c.sound_design_sha256='f'.repeat(64);
 await assert.rejects(verifyApproval(approval.payload,approval.approval,c),/Stale sound design/);
});
test('guitar and mallet presets have distinct decays and a correctly pitched fundamental',()=>{
 const guitar=voice(ctx,{...note,instrument_id:'guitar_fingerstyle_v1'}).getChannelData(0);
 const vibes=voice(ctx,{...note,instrument_id:'vibraphone_soft_v1'}).getChannelData(0);
 assert.notDeepEqual(guitar,vibes);
 assert.deepEqual(guitar,voice(ctx,{...note,id:'cache-equivalent',instrument_id:'guitar_fingerstyle_v1'}).getChannelData(0));
 const power=(v:Float32Array,f:number)=>{let re=0,im=0;for(let i=240;i<12000;i++){re+=v[i]*Math.cos(2*Math.PI*f*i/48000);im+=v[i]*Math.sin(2*Math.PI*f*i/48000);}return re*re+im*im;};
 for(const samples of [guitar,vibes]){assert.ok(power(samples,440)>power(samples,420)*20);assert.ok(power(samples,440)>power(samples,460)*20);assert.equal(samples[0],0);assert.equal(Math.abs(samples.at(-1)!),0);}
 const muted=voice(ctx,{...note,instrument_id:'guitar_fingerstyle_v1',articulation:'palm_mute'}).getChannelData(0);
 assert.ok(energy(muted.slice(12000))<energy(guitar.slice(12000))*.1);
});
test('collision voice decays instead of looping static and material colors differ',()=>{
 const event={...note,event_type:'foley',midi_pitch:null,instrument_id:'wood_contact_v1',duration_s:.2} as ScoreEvent;
 const low=voice(ctx,{...event,timbre_id:'wood-low'}).getChannelData(0);
 const high=voice(ctx,{...event,timbre_id:'wood-high'}).getChannelData(0);
 assert.notDeepEqual(low,high);
 assert.ok(energy(low.slice(7200))<energy(low.slice(0,2400))*.002);
});
test('transposition keeps exact unpitched contact times and meaningful stem names',()=>{
 const p=JSON.parse(b.plan_bytes),shifted=transition(b.events,p,b.composition,0,2,0);
 assert.deepEqual(shifted.filter(e=>e.event_type==='foley'),b.events.filter(e=>e.event_type==='foley'));
 assert.deepEqual(stemsFor(b.events),['guitar','bass','brush','foley']);
 assert.deepEqual(stemsFor(legacy.bundle.events as ScoreEvent[]),['piano','bass','brush','foley']);
 assert.equal(stemFor({...note,instrument_id:'vibraphone_soft_v1'}),'vibraphone');
 assert.ok(polyphony(b.events)<=12);
});
