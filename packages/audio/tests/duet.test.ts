import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from './duet-fixture.json';
import {voice} from '../engine';
import {stemsFor} from '../mix';
import {verifyBundle,copy,transition,type Bundle} from '../model';
const b=fixture as unknown as Bundle;
test('duet binds a separate synchronized piano stem and rejects altered backing',async()=>{
 const p=await verifyBundle(b);
 assert.deepEqual(stemsFor(b.events),['guitar','piano','bass','brush','foley']);
 const altered=copy(b);altered.events.find(e=>e.instrument_id==='piano_felt_comp_v1')!.resolved_time_s+=.02;
 await assert.rejects(verifyBundle(altered));
 const missing=copy(b);delete missing.sound_design!.piano_accompaniment;
 await assert.rejects(verifyBundle(missing));
 for(const delta of [-2,2]){
  const shifted=transition(b.events,p,b.composition,0,delta,0);
  for(const e of b.events.filter(e=>e.instrument_id==='piano_felt_comp_v1'||e.instrument_id==='guitar_fingerstyle_v1')){
   const next=shifted.find(n=>n.id===e.id)!;
   const beat=60/b.composition.tempo_map[0].bpm;
   if(e.instrument_id==='piano_felt_comp_v1'&&e.resolved_time_s<4*beat){
    // The manual/blink transition now reharmonizes the piano with bass for V → I.
    const root=(delta+(e.resolved_time_s<beat?7:0)+12)%12;
    assert.ok([0,4,7].some(interval=>(root+interval)%12===next.midi_pitch!%12));
   }else assert.equal(next.midi_pitch,e.midi_pitch!+delta);
   assert.equal(next.resolved_time_s,e.resolved_time_s);
   const fragments=shifted.filter(n=>n.id===e.id||n.id===e.id+':arrival');
   assert.ok(Math.abs(fragments.reduce((sum,n)=>sum+n.duration_s,0)-e.duration_s)<1e-9);
  }
 }
});
test('piano has a distinct deterministic, pitched decaying tone',()=>{
 const ctx={sampleRate:48000,createBuffer:(_c:number,n:number)=>{const v=new Float32Array(n);return {length:n,getChannelData:()=>v};}} as unknown as BaseAudioContext;
 const e={...b.events.find(n=>n.instrument_id==='piano_felt_comp_v1')!,duration_s:1,midi_pitch:60};
 const piano=voice(ctx,e).getChannelData(0),guitar=voice(ctx,{...e,instrument_id:'guitar_fingerstyle_v1'}).getChannelData(0);
 assert.notDeepEqual(piano,guitar);
 assert.deepEqual(piano,voice(ctx,{...e,id:'equivalent-cache-entry'}).getChannelData(0));
 const energy=(lo:number,hi:number)=>piano.slice(lo,hi).reduce((s,v)=>s+v*v,0);
 assert.ok(energy(24000,36000)<energy(1000,13000)*.2);
 assert.equal(Math.abs(piano.at(-1)!),0);
});
