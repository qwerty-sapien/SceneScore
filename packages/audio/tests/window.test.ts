import test from 'node:test';
import assert from 'node:assert/strict';
import {scheduleWindowFade,windowGain,validateWindow,selectWindowEvents,type PlaybackWindow} from '../window';
import type {ScoreEvent} from '../../contracts/generated';

const w:PlaybackWindow={version:'scene-playback-window-1',start_s:0,duration_s:2,frame_count:60,render_fps:30,
 sample_rate_hz:48000,audio_sample_count:96000,final_fade_s:.01,original_events_sha256:'a'.repeat(64),
 label:'Draft · existing score excerpt · adaptive scoring pending',approval:null,
 projections:[{source_event_id:'sustain',start_s:1.5,stop_s:2,source_offset_s:0}],
 omitted:[{source_event_id:'omitted',source_start_s:2,source_stop_s:3,reason:'starts_at_or_after_scene_end'}],
 truncated:[{source_event_id:'sustain',source_start_s:1.5,source_stop_s:5.5,playback_stop_s:2,removed_before_s:0,removed_after_s:3.5,reason:'crosses_scene_end'}]};

test('native frame and sample clocks cannot silently differ',()=>{
 assert.equal(validateWindow(w,2),w);
 for(const altered of [{frame_count:59},{audio_sample_count:95999},{final_fade_s:.02},{duration_s:2.001}])
  assert.throws(()=>validateWindow({...w,...altered} as PlaybackWindow,2));
});
test('selection preserves complete sustained event and source bytes',()=>{
 const events=[{id:'sustain',resolved_time_s:1.5,duration_s:4},{id:'omitted',resolved_time_s:2,duration_s:1}] as ScoreEvent[];
 const before=JSON.stringify(events);
 assert.deepEqual(selectWindowEvents(events,w),[events[0]]);
 assert.equal(JSON.stringify(events),before);
 assert.throws(()=>selectWindowEvents([{...events[0],duration_s:.1}],w));
});
test('fade has same physical endpoint after resume inside final ten milliseconds',()=>{
 const calls:(number|string)[][]=[];
 const param={cancelScheduledValues:(t:number)=>calls.push(['cancel',t]),setValueAtTime:(v:number,t:number)=>calls.push(['set',v,t]),linearRampToValueAtTime:(v:number,t:number)=>calls.push(['ramp',v,t])};
 assert.equal(scheduleWindowFade(param,2,10,0,10),12);
 assert.deepEqual(calls,[['cancel',10],['set',1,10],['set',1,11.99],['ramp',0,12]]);
 calls.length=0;
 scheduleWindowFade(param,2,20,1.995,20);
 assert.ok(Math.abs(Number(calls[1][1])-.5)<1e-10);
 assert.deepEqual(calls[2],['ramp',0,20.005]);
 assert.equal(windowGain(2,2),0);
});

test('omitted and truncated ledgers must cover the exact complete source',()=>{
 const events=[{id:'sustain',resolved_time_s:1.5,duration_s:4},{id:'omitted',resolved_time_s:2,duration_s:1}] as ScoreEvent[];
 for(const changed of [{projections:[]},{omitted:[]},{truncated:[]}])assert.throws(()=>selectWindowEvents(events,{...w,...changed}));
});
