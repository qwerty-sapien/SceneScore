import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from './fixture.json';
import {bytes,sha,stable,copy,type Bundle} from '../model';
import {verifyPianoMix,type PianoMix} from '../piano-binding';
import {scenePianoVoice,PIANO_VOICE_VERSION} from '../piano-voices';
import {riffVoice} from '../riff-voices';
import {defaultPlaybackGain} from '../../../apps/web/src/library/playback-gain';

async function bound(){
 const b=copy(fixture.bundle) as unknown as Bundle,p=JSON.parse(b.plan_bytes);
 b.events=[{...b.events.find(e=>e.midi_pitch!==null)!,instrument_id:'scene_piano_v1'}];
 b.piano_event_bytes=new TextDecoder().decode(bytes(b.events.map(({plan_id:_id,...e})=>e)));
 b.piano_mix={version:'scene-piano-mix-1',voice_version:PIANO_VOICE_VERSION,default_gain_db:-6,source_bundle_sha256:'a'.repeat(64),
  events_content_sha256:await sha(new TextEncoder().encode(b.piano_event_bytes)),brush_attenuation_db:18,approval:null,label:'Synthetic binding test'} satisfies PianoMix;
 b.piano_mix_bytes=new TextDecoder().decode(bytes(b.piano_mix));b.piano_mix_sha256=await sha(new TextEncoder().encode(b.piano_mix_bytes));
 p.provenance.config_hash=b.piano_mix_sha256;p.provenance.input_hashes.push(b.piano_mix_sha256);return {b,p};
}
test('clean piano edition is explicitly bound to its score and plan',async()=>{const {b,p}=await bound();await verifyPianoMix(b,p,sha,stable);assert.equal(defaultPlaybackGain(b),-6);});
test('unbound voices and tampered score, design or approval configuration are rejected',async()=>{
 const {b,p}=await bound();
 const missing=copy(b);delete missing.piano_mix;await assert.rejects(verifyPianoMix(missing,p,sha,stable));
 const event=copy(b);event.events[0].velocity++;await assert.rejects(verifyPianoMix(event,p,sha,stable),/score binding/);
 const design=copy(b);design.piano_mix!.label='changed';await assert.rejects(verifyPianoMix(design,p,sha,stable),/mix hash/);
 const plan=copy(p);plan.provenance.config_hash='0'.repeat(64);await assert.rejects(verifyPianoMix(b,plan,sha,stable),/mix hash/);
});
test('new piano voice uses the dedicated clean piano waveform, not noise or legacy keyboard fallback',async()=>{
 const {b}=await bound(),e=b.events[0],clean=scenePianoVoice(e,48000)!,reference=riffVoice({...e,instrument_id:'piano_felt_comp_v1'},48000)!;
 for(let i=0;i<2000;i++)assert.equal(clean(i/48000),reference(i/48000));
 assert.equal(scenePianoVoice({...e,instrument_id:'keyboard_damped_v1'},48000),null);
});
test('contact voice uses deterministic damped wooden modes without a noise source',async()=>{
 const {b}=await bound(),e={...b.events[0],instrument_id:'scene_wood_contact_v1',midi_pitch:null},f=scenePianoVoice(e,48000)!;
 const reference=riffVoice({...e,instrument_id:'wood_contact_v1',timbre_id:'wood-low'},48000)!;
 for(let i=0;i<1000;i++)assert.equal(f(i/48000),reference(i/48000));
});
