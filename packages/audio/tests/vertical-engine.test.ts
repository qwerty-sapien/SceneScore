import test from 'node:test';
import assert from 'node:assert/strict';
import {articulationEnvelope,voice} from '../engine';
import fixture from './fixture.json';
import type {ScoreEvent} from '../../contracts/generated';

test('staccato and tenuto sound differently inside the same occupied slot',()=>{
 const event=fixture.bundle.events.find(e=>e.midi_pitch!==null)! as ScoreEvent;
 const context={sampleRate:8000,createBuffer:(_channels:number,n:number)=>{const samples=new Float32Array(n);return {length:n,getChannelData:()=>samples};}} as unknown as BaseAudioContext;
 const staccato=voice(context,{...event,duration_s:1,articulation:'staccato'});
 const tenuto=voice(context,{...event,duration_s:1,articulation:'tenuto'});
 assert.equal(staccato.length,tenuto.length);
 const energy=(b:AudioBuffer)=>b.getChannelData(0).slice(4800,6400).reduce((sum,x)=>sum+x*x,0);
 assert.equal(energy(staccato),0);
 assert.ok(energy(tenuto)>0);
 for(const articulation of ['staccato','tenuto','legato']){
  assert.equal(articulationEnvelope(articulation,0,1),0);
  assert.equal(articulationEnvelope(articulation,1,1),0);
 }
});
