import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from './fixture.json';
import {copy,VERTICAL_TABLE_SHA256,VERTICAL_TRANSITION_VERSION,type Bundle,isVerticalVoice} from '../model';
import {materializeVerticalPreview} from '../vertical-preview';
import type {ArrangementPlan} from '../../contracts/generated';
const setup=()=>{const b=copy(fixture.bundle) as unknown as Bundle,p=JSON.parse(b.plan_bytes) as ArrangementPlan;
 b.music_vertical={version:VERTICAL_TRANSITION_VERSION,table_id:'scenescore-transition-table',table_version:'1',table_sha256:VERTICAL_TABLE_SHA256,eligible_arrival_ticks:[3840,7680,11520],jazz_enabled:false,audition_status:'AUDITION_PENDING',approval:null};return {b,p};};
test('offline preview is deterministic, preserves unrelated voices and never creates approval',()=>{
 const {b,p}=setup(),first=materializeVerticalPreview(b,p,[1]);
 assert.deepEqual(first,materializeVerticalPreview(b,p,[1]));assert.equal(first.approval,null);
 assert.equal(first.controls[0].status,'planned_preview');assert.equal(first.controls[0].ack_scene_s,1.02);
 for(const event of b.events.filter(e=>!isVerticalVoice(e)))assert.strictEqual(first.events.find(e=>e.id===event.id),event);
 assert.match(first.timing_evidence,/no Timeline.submit/);
});
test('offline near-miss hold cannot stack with an unresolved transition',()=>{
 const {b,p}=setup(),result=materializeVerticalPreview(b,p,[1],[{start_s:1.1,end_s:3}]);
 assert.equal(result.controls[0].arrival_scene_s,5);assert.ok(result.controls[0].progression_start_s!>=3);
 assert.equal(result.controls[0].ack_scene_s,1.02);
});
test('preview rejects overlapping requests and holds on unknown motion',()=>{
 const {b,p}=setup(),result=materializeVerticalPreview(b,p,[1,1.1]);
 assert.equal(result.controls[1].reason,'one_pending_request_limit');
 b.states=[];assert.equal(materializeVerticalPreview(b,p,[1]).controls[0].reason,'stationary_or_unknown_world_z');
});
