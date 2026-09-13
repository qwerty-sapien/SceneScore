import test from 'node:test';
import assert from 'node:assert/strict';
import {compileTimedDuet,LOOP} from '../../../../packages/audio/keyboard-scenes';
import type {Settings} from '../../../../packages/audio/keyboard-score';
import {KeyboardPlayer} from './player';
import {KeyboardVideoSync,type VideoTarget} from './video-sync';
import preset from './assets/c-video.json';
const settings:Settings={transpose:0,touch:'detached',ornament:'plain'};

test('video-length score preserves scene timestamps, pitches and the loop boundary',()=>{
 const d=preset.duration_s,scale=d/LOOP;
 const normalized=compileTimedDuet(0,LOOP,preset.markers.map(m=>({...m,at:m.at/scale})),[{at:0,settings}],'test');
 const timed=compileTimedDuet(0,d,preset.markers,[{at:0,settings}],'test',d);
 assert.equal(timed.length,normalized.length);
 timed.forEach((e,i)=>{assert.equal(e.midi_pitch,normalized[i].midi_pitch);assert.ok(Math.abs(e.resolved_time_s-normalized[i].resolved_time_s*scale)<1e-8);assert.ok(e.resolved_time_s+e.duration_s<=d+1e-8);});
 const twice=compileTimedDuet(0,d*2,preset.markers,[{at:0,settings}],'test',d);
 for(const time of [1,1.05,1.1,2.3,2.35,2.4])assert.ok(twice.some(e=>e.scene_time_s!==null&&Math.abs(e.scene_time_s-(time+d))<1e-8));
});

test('scene loading clears the prior take and sets video-length key boundaries',()=>{
 const p=new KeyboardPlayer();p.loadScene(preset.duration_s,preset.markers,preset);
 assert.equal(p.markers.length,6);assert.equal(p.sourceIdentity,preset);assert.equal(p.barDuration,preset.duration_s/4);
 p.running=true;p.now=()=>.8;p.refreshFuture=()=>{};p.change('keyUp');
 assert.equal(p.pendingAt,p.barDuration);assert.equal(p.settings.transpose,0);
 assert.throws(()=>p.loadScene(LOOP,[]),/Stop playback/);
 p.running=false;p.loadScene(LOOP,[]);assert.equal(p.duration,0);assert.equal(p.events.length,0);assert.equal(p.sourceIdentity,null);assert.equal(p.pendingKey,null);
 assert.throws(()=>p.loadScene(0,[]),/Invalid scene/);
});

test('video waits for the audio anchor, follows audio across wraps, and stops with audio',async()=>{
 let plays=0;const video:VideoTarget={currentTime:2,paused:true,seeking:false,readyState:4,playbackRate:1,play:async()=>{plays++;video.paused=false;},pause:()=>{video.paused=true;}};
 const sync=new KeyboardVideoSync(video,()=>assert.fail('unexpected playback error'));
 sync.update(true,-.05,preset.duration_s);assert.equal(plays,0);assert.equal(video.currentTime,0);
 sync.update(true,.4,preset.duration_s);await Promise.resolve();assert.equal(video.currentTime,.4);assert.equal(plays,1);
 video.currentTime=preset.duration_s-.03;sync.update(true,preset.duration_s+.02,preset.duration_s);assert.ok(Math.abs(video.currentTime-.02)<1e-8);
 sync.update(false,0,preset.duration_s);assert.equal(video.paused,true);
});

test('stopped pending video play is paused when its promise resolves',async()=>{
 let resolve!:()=>void;const video:VideoTarget={currentTime:0,paused:true,seeking:false,readyState:4,playbackRate:1,play:()=>new Promise<void>(r=>{resolve=()=>{video.paused=false;r();};}),pause:()=>{video.paused=true;}};
 const sync=new KeyboardVideoSync(video,()=>{});sync.update(true,.1,6);sync.pause();resolve();await Promise.resolve();assert.equal(video.paused,true);
});

test('video failure is surfaced and no repeated play request runs while one is pending',async()=>{
 let calls=0,message='';const video:VideoTarget={currentTime:0,paused:true,seeking:false,readyState:4,playbackRate:1,play:async()=>{calls++;throw Error('blocked');},pause:()=>{}};
 const sync=new KeyboardVideoSync(video,m=>{message=m;});sync.update(true,.1,6);sync.update(true,.12,6);await Promise.resolve();await Promise.resolve();
 assert.equal(calls,1);assert.match(message,/blocked/);
});
