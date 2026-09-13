import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from './fixture.json';
import {copy,direction,type Bundle} from '../model';
import {prepareMotionReader,createSimulation,latencyIntervals,mappedRequest,createFromGesture} from '../control';
import type {ClockMapping,GestureEvent} from '../../contracts/generated';
import envelopeFixture from '../../../modules/muse/runtime/tests/control-envelope.json';

test('prepared motion reader matches the causal reference across covered, missing and future times',()=>{
 const b=copy(fixture.bundle) as unknown as Bundle,p=JSON.parse(b.plan_bytes);
 for(const omit of [false,true]){const source=copy(b);if(omit)source.states=source.states.filter(s=>s.scene_time_s>.5);const read=prepareMotionReader(source,p);for(let t=0;t<6;t+=.013)assert.equal(read(t),direction(source,p,t),`t=${t}`);}
 const read=prepareMotionReader(b,p),atOne=read(1);b.states.filter(s=>s.scene_time_s>1).forEach(s=>s.velocity_m_s=[0,0,-1000]);assert.equal(read(1),atOne);
});
test('explicit semantic simulation has no invented detector latency and preserves lanes',()=>{
 const a=envelopeFixture.action;
 const e=createSimulation({audio_s:10,audio_epoch:'test',approved_plan_hash:a.approved_plan_hash,scene_policy_id:a.scene_policy_id,signed_semitones:2,lanes:a.before});
 assert.equal(e.action.provenance.source_mode,'synthetic');assert.deepEqual(e.action.before,e.action.after);assert.equal(latencyIntervals(e).detector_closure_ms,null);
});
test('browser adapter rejects stale clock, excessive uncertainty and preclosure gesture',()=>{
 const p=envelopeFixture.action.provenance;
 const g:GestureEvent={kind:'GestureEvent',schema_version:'0.1',id:'test-closed-pair',session_id:'test',provenance:p,candidate_ids:['a','b'],gesture_count:2,start:{clock:'device',epoch:'device-1',seconds:1},end:{clock:'device',epoch:'device-1',seconds:1.4},final_blink:{clock:'device',epoch:'device-1',seconds:1.4},decision:{clock:'device',epoch:'device-1',seconds:1.91},closure_delay_s:.51,grammar_hash:p.config_hash,status:'accepted',reason:null,quality:{state:'good',reason:null}} as GestureEvent;
 const m:ClockMapping={kind:'ClockMapping',schema_version:'0.1',id:'mapping',provenance:p,source_clock:'device',destination_clock:'audio',source_epoch:'device-1',destination_epoch:'audio-1',source_anchor_s:1,destination_anchor_s:10,rate:1,uncertainty_s:.01,valid_from_s:1,valid_until_s:2} as ClockMapping;
 const ctx={audio_s:10.91,audio_epoch:'audio-1',approved_plan_hash:envelopeFixture.action.approved_plan_hash,scene_policy_id:envelopeFixture.action.scene_policy_id,signed_semitones:2 as const,lanes:envelopeFixture.action.before};
 assert.equal(mappedRequest(g,m,'audio-1'),10.91);assert.equal(createFromGesture(g,m,100,'host-1',ctx).action.request.seconds,10.91);
 assert.throws(()=>mappedRequest(g,{...m,valid_until_s:1.5},'audio-1'),/stale_clock/);assert.throws(()=>mappedRequest(g,{...m,uncertainty_s:.2},'audio-1'),/stale_clock/);
 assert.throws(()=>createFromGesture({...g,decision:{...g.decision,seconds:1.8},closure_delay_s:.4},m,100,'host-1',{...ctx,audio_s:10.8}),/sequence_not_closed/);
});
