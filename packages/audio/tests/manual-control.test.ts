import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from './fixture.json';
import {readFileSync} from 'node:fs';
import {copy,VERTICAL_TABLE_SHA256,VERTICAL_TRANSITION_VERSION,type Bundle} from '../model';
import {Timeline} from '../transport';
import {createManualKeyChange,manualChoices} from '../manual-control';
import type {ArrangementPlan} from '../../contracts/generated';
import {museDetected} from '../../../apps/web/src/muse/headset';
import type {BridgeStatus} from '../../../apps/web/src/muse/types';

const lanes={master_gain_db:-18,articulation:'score',expression_preset:'neutral'};
function setup(vertical=false){
 const b=copy(fixture.bundle) as unknown as Bundle,p=JSON.parse(b.plan_bytes) as ArrangementPlan;
 if(vertical)b.music_vertical={version:VERTICAL_TRANSITION_VERSION,table_id:'scenescore-transition-table',table_version:'1',table_sha256:VERTICAL_TABLE_SHA256,eligible_arrival_ticks:[3840,7680,11520],jazz_enabled:false,audition_status:'AUDITION_PENDING',approval:null};
 const t=new Timeline(b,p,'a'.repeat(64));t.playing=true;return t;
}
for(const vertical of [false,true])test(`manual seeded choice executes prepared harmony, preserves lanes (${vertical?'vertical':'standard'})`,()=>{
 for(const [seed,sign] of [[0,-2],[0xffffffff,2]]){
  const t=setup(vertical),original=copy(t.events),a=createManualKeyChange(t,1,1,lanes,seed)!;
  assert.equal(a.action.signed_semitones,sign);assert.equal(a.action.provenance.source_mode,'keyboard');assert.equal(a.action.provenance.seed,seed);
  assert.deepEqual(a.action.before,a.action.after);assert.equal(a.timing.t0_final_blink_s,null);
  const d=t.submit(a.action,1,1);assert.equal(d.status,'queued');assert.deepEqual(manualChoices(t,1),[]);
  if(vertical)t.acknowledgeVertical(d,1.02);
  assert.notDeepEqual(t.events,original);
  for(const e of original.filter(e=>e.midi_pitch===null))assert.deepEqual(t.events.find(after=>after.id===e.id),e);
  t.advance(d.arrival_scene_s!);assert.equal(t.currentTonic(),(sign+12)%12);assert.equal(d.status,'executed');
  assert.equal(t.currentChord()!.root_pc,(sign+12)%12);
 }
});
test('manual availability handles pause, ending, preparation, unsupported edges and reset',()=>{
 const t=setup();t.playing=false;assert.deepEqual(manualChoices(t,1),[]);t.playing=true;
 assert.deepEqual(manualChoices(t,t.bundle.scene.duration_s-.1),[]);
 t.preparationReady=false;assert.equal(createManualKeyChange(t,1,1,lanes,0),null);t.preparationReady=true;
 for(const key of t.prepared.keys())if(key.endsWith(':-2'))t.prepared.delete(key);
 assert.deepEqual(manualChoices(t,1),[2]);const a=createManualKeyChange(t,1,1,lanes,0)!;assert.equal(a.action.signed_semitones,2);
 t.submit(a.action,1,1);t.reset(1.1);assert.equal(t.currentTonic(),0);assert.equal(t.pending.length,0);
 assert.equal(t.history[0].status,'cancelled_on_transport_reset');
});
test('library piano-comp lanes reharmonize with bass and display the transition through rests',()=>{
 const b=JSON.parse(readFileSync('apps/web/public/riff-studio/contact-brush_swing_light_v1-guitar-piano-v2.json','utf8')) as Bundle;
 const t=new Timeline(b,JSON.parse(b.plan_bytes),'a'.repeat(64));t.playing=true;
 const a=createManualKeyChange(t,1,1,lanes,0xffffffff)!;const d=t.submit(a.action,1,1);
 assert.equal(d.status,'queued');
 const dominant=t.events.filter(e=>e.lane_id.startsWith('piano-comp-')&&e.phrasing==='new-dominant');
 const tonic=t.events.filter(e=>e.lane_id.startsWith('piano-comp-')&&e.phrasing==='new-tonic-arrival');
 assert.ok(dominant.length>0);assert.ok(tonic.length>0);
 for(const e of dominant)assert.equal(e.midi_pitch!%12,(9+[0,4,7][Number(e.lane_id.at(-1))])%12);
 for(const e of tonic)assert.equal(e.midi_pitch!%12,(2+[0,4,7][Number(e.lane_id.at(-1))])%12);
 assert.equal(t.currentChord(d.boundary_s!+.55)!.root_pc,9);
 t.advance(d.arrival_scene_s!+.01);assert.equal(t.currentChord()!.root_pc,2);
});
test('headset presence uses hardware detection even disarmed or bad quality, never simulated mode',()=>{
 const status={mode:'LIVE_MUSE',connected:true,hardware_verified:true,ble_connected:true,armed:false,quality:'bad'} as BridgeStatus;
 assert.equal(museDetected(status),true);assert.equal(museDetected(null),false);
 assert.equal(museDetected({...status,mode:'SYNTHETIC_TEST'}),false);
 assert.equal(museDetected({...status,mode:'REAL_REPLAY'}),false);
 assert.equal(museDetected({...status,connected:false,ble_connected:false}),false);
 assert.equal(museDetected({...status,connected:false,hardware_verified:false}),true);
});
