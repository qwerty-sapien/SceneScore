import {test} from 'node:test';
import assert from 'node:assert/strict';
import {IntentMarkerController,cuePhase,sourceLabel,validateReview,reviewSegmentBounds} from '../src/interaction';
import type {MarkerRequest} from '../src/types';
const buttonTarget={closest:(selector:string)=>selector.includes('button,')?{}:null} as unknown as EventTarget;
const textTarget={closest:()=>({})} as unknown as EventTarget;
test('B down/up remains ordered, class/id stable, with repeat and text targets ignored',async()=>{
 const records:MarkerRequest[]=[],changes:boolean[]=[];let tick=0,resolveDown:()=>void=()=>{};
 const wait=new Promise<void>(resolve=>resolveDown=resolve);
 const control=new IntentMarkerController(async marker=>{if(marker.event==='down')await wait;records.push(marker);},()=>++tick,()=> 'held-interval',value=>changes.push(value));
 assert.equal(control.down({code:'KeyB',repeat:false,target:textTarget},true,'double'),false);
 assert.equal(control.down({code:'KeyB',repeat:false,target:null},false,'double'),false);
 assert.equal(control.down({code:'KeyB',repeat:false,target:buttonTarget},true,'double'),true);
 assert.equal(control.down({code:'KeyB',repeat:true,target:null},true,'single'),false);
 assert.equal(control.down({code:'KeyB',repeat:false,target:null},true,'single'),false);
 assert.equal(control.up({code:'KeyB'}),true);assert.equal(control.up({code:'KeyB'}),false);
 resolveDown();await control.flush();assert.deepEqual(records.map(record=>[record.event,record.id,record.class_name]),[['down','held-interval','double'],['up','held-interval','double']]);assert.deepEqual(changes,[true,false]);assert.ok(records[1].client_ms>records[0].client_ms);
});
test('blur release closes once and server-stop clearing creates no late marker',async()=>{
 const records:MarkerRequest[]=[];const control=new IntentMarkerController(async marker=>records.push(marker));
 control.down({code:'KeyB',repeat:false,target:null},true,'keypress_only');control.release();control.release();await control.flush();assert.deepEqual(records.map(record=>record.event),['down','up']);
 control.down({code:'KeyB',repeat:false,target:null},true,'natural');control.release(false);await control.flush();assert.deepEqual(records.map(record=>record.event),['down','up','down']);
});
test('cue state is separate timed preparation/activity/quiet; source truth needs a connection',()=>{
 assert.equal(cuePhase(100,2099),'ready');assert.equal(cuePhase(100,2100),'active');assert.equal(cuePhase(100,4100),'quiet');assert.equal(cuePhase(100,6100),'complete');assert.equal(sourceLabel('real_device',false),'NO STREAM');assert.equal(sourceLabel('synthetic',true),'SYNTHETIC REHEARSAL');assert.equal(sourceLabel('real_device',true),'LIVE EEG');
 assert.throws(()=>validateReview(2,1,'reviewer'));assert.throws(()=>validateReview(1,2,''));validateReview(1,2,'reviewer');
});

test('review trace reload follows edited bounds and clamps the recorded range and ten-second budget',()=>{
 assert.deepEqual(reviewSegmentBounds(27,29,0,40),{start:24.5,end:30});
 assert.deepEqual(reviewSegmentBounds(1,2,0,3),{start:0,end:3});
 const bounded=reviewSegmentBounds(3,29,0,40);assert.equal(bounded.end-bounded.start,10);assert.equal(bounded.end,30);
 assert.throws(()=>reviewSegmentBounds(50,51,0,40));assert.throws(()=>reviewSegmentBounds(5,4));
});
