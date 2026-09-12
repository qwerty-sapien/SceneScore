import test from 'node:test';
import assert from 'node:assert/strict';
import {amplitude,polyphony,validateMix} from '../mix';
import type {ScoreEvent} from '../../contracts/generated';
import {Engine} from '../engine';
import {Timeline} from '../transport';
import {copy,keyboardAction,type Bundle} from '../model';
import fixture from './fixture.json';

test('mix journal validates time ordering and explicit mute at each point',()=>{
 const initial={scene_s:0,gain_db:-18,muted:false,lanes:{soundtrack:true,foley:true}};
 validateMix([initial,{...initial,scene_s:2,muted:true}],30);
 assert.equal(amplitude({...initial,muted:true},'foley'),0);
 assert.equal(amplitude({...initial,lanes:{soundtrack:false,foley:true}},'soundtrack'),0);
 assert.throws(()=>validateMix([{...initial,scene_s:2},initial],30));
 assert.throws(()=>validateMix([{...initial,gain_db:NaN}],30));
});
test('voice bounds count overlapping intervals and permit adjacent notes',()=>{
 const event={resolved_time_s:0,duration_s:1} as ScoreEvent;
 assert.equal(polyphony([event,{...event,resolved_time_s:1}],1),1);
 assert.throws(()=>polyphony(Array.from({length:25},()=>event)));
});
test('late buffer preparation rolls back the entire pending modulation',()=>{
 const bundle=copy(fixture.bundle) as unknown as Bundle,plan=JSON.parse(bundle.plan_bytes),timeline=new Timeline(bundle,plan,'a'.repeat(64)),engine=new Engine(timeline);
 const clock={currentTime:1};engine.context=clock as AudioContext;timeline.playing=true;
 const before=copy(timeline.events);engine.prepare=()=>{clock.currentTime=3;};
 const result=engine.submit(keyboardAction(plan,timeline.planHash,timeline.epoch,1,2,'KEYBOARD'));
 assert.equal(result.status,'suppressed');assert.match(result.reason!,/preparation_missed_boundary/);assert.deepEqual(timeline.events,before);assert.equal(timeline.pending.length,0);
});
test('completed uninterrupted run is required for performance export; mix records edits',()=>{
 const bundle=copy(fixture.bundle) as unknown as Bundle,engine=new Engine(new Timeline(bundle,JSON.parse(bundle.plan_bytes),'a'.repeat(64)));
 assert.throws(()=>engine.exportReady());engine.completed=true;assert.doesNotThrow(()=>engine.exportReady());engine.discontinuous=true;assert.throws(()=>engine.exportReady());
 engine.timeline.playing=true;engine.timeline.position=2;engine.setGain(-12);engine.setMute(true);engine.setLanes({soundtrack:true,foley:false});
 assert.equal(engine.mix.length,3);assert.equal(engine.mix[1].muted,true);assert.equal(engine.mix[2].lanes.foley,false);
});
