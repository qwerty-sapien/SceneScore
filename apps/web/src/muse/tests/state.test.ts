import {test} from 'node:test';
import assert from 'node:assert/strict';
import {visibleMode,delayedFeedback} from '../state';
import {LocalMuseBridge,anchorFromProbe,mappingFromProbe,sameClockSource} from '../bridge';
import type {BridgeStatus,MusicControlContext} from '../types';
const ready:BridgeStatus={version:'muse-bridge-1',mode:'LIVE_MUSE',connected:true,hardware_verified:true,quality:'good',warmup_ready:true,armed:true,reason:'armed',model_version:'fixture-model',config_hash:'a'.repeat(64),source_available:true,recording:false,sample_count:1000,device_epoch:'device',host_epoch:'host'};
test('all four modes retain provenance and every live gate is required',()=>{
 assert.equal(visibleMode('KEYBOARD',null),'KEYBOARD');assert.equal(visibleMode('SYNTHETIC_TEST',null),'SYNTHETIC_TEST');assert.equal(visibleMode('REAL_REPLAY',{...ready,mode:'REAL_REPLAY'}),'REAL_REPLAY');assert.equal(visibleMode('LIVE_MUSE',ready),'LIVE_MUSE');
 for(const patch of [{connected:false},{hardware_verified:false},{quality:'unverified' as const},{warmup_ready:false},{armed:false},{source_available:false},{mode:'REAL_REPLAY' as const}])assert.equal(visibleMode('LIVE_MUSE',{...ready,...patch}),'KEYBOARD');
 assert.equal(visibleMode('REAL_REPLAY',null),'KEYBOARD');
});
test('feedback delayed beyond gesture and quiet window remains unreviewed, not truth',()=>{
 const cue={id:'cue',instruction:'Double blink',started_ms:0,ends_ms:4000,feedback_after_ms:6000};
 assert.throws(()=>delayedFeedback(cue,'performed',5999));
 const note=delayedFeedback(cue,'uncertain',6000);assert.equal(note.independent_review,'pending');assert.equal(note.truth_label,null);assert.equal(note.kind,'uncertain');
});
test('clock requires two anchors, estimates rate, propagates uncertainty and rejects stale/skewed sources',()=>{
 const context:MusicControlContext={audio_s:10,audio_epoch:'audio',approved_plan_hash:null,scene_policy_id:null,signed_semitones:0,lanes:{master_gain_db:-18,articulation:'score',expression_preset:'neutral'}};
 const probe={device_s:100,device_epoch:'device',host_s:200,host_epoch:'host',uncertainty_s:.0005,config_hash:'a'.repeat(64),source_mode:'replay' as const};
 const first=anchorFromProbe(probe,context,{...context,audio_s:10.002});
 assert.throws(()=>mappingFromProbe(probe,context,{...context,audio_s:10.002}),/calibration_pending/);
 const next={...probe,device_s:102,host_s:202};
 const mapping=mappingFromProbe(next,{...context,audio_s:12.0002},{...context,audio_s:12.0022},first);
 assert.ok(Math.abs(mapping.rate-1.0001)<1e-9);assert.ok(mapping.uncertainty_s>.0015);assert.ok(mapping.uncertainty_s<.02);assert.equal(mapping.provenance.source_mode,'replay');assert.equal(mapping.valid_until_s-mapping.valid_from_s,2.5);
 assert.throws(()=>mappingFromProbe(next,context,{...context,audio_epoch:'new'},first));
 assert.throws(()=>mappingFromProbe(next,context,{...context,audio_s:11},first));
 assert.throws(()=>mappingFromProbe({...next,device_epoch:'new'},{...context,audio_s:12},{...context,audio_s:12.002},first),/source_changed/);
 assert.throws(()=>mappingFromProbe(next,{...context,audio_s:12.5},{...context,audio_s:12.502},first),/skew/);
 assert.throws(()=>mappingFromProbe({...next,uncertainty_s:.02},{...context,audio_s:12},{...context,audio_s:12.002},first),/20ms/);
 assert.equal(sameClockSource(first,{...first,probe:{...probe,source_mode:'real_device'}}),false);
});

test('default fetch retains browser global receiver through authenticated handshake',async()=>{
 const original=globalThis.fetch;
 try{
  globalThis.fetch=async function(this:unknown){assert.equal(this,globalThis);return new Response(JSON.stringify({session:'session-fixture',cursor:7,status:ready}),{status:200,headers:{'Content-Type':'application/json'}});};
  const bridge=new LocalMuseBridge();const status=await bridge.connect('a'.repeat(43));assert.equal(status.mode,'LIVE_MUSE');assert.equal(bridge.initialCursor,7);bridge.close();
 }finally{globalThis.fetch=original;}
});
