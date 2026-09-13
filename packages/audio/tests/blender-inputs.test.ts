import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {verifyBlenderInputs} from '../blender-inputs';
import {sha,stable,hash} from '../model';
import type {ArrangementPlan} from '../../contracts/generated';

async function fixture(){
 const scene=JSON.parse(fs.readFileSync('fixtures/contracts/SceneManifest.json','utf8'));
 const plan=JSON.parse(fs.readFileSync('fixtures/contracts/ArrangementPlan.json','utf8')) as ArrangementPlan;
 scene.duration_s=1;
 const raw='[]\n',events_sha256=await sha(new TextEncoder().encode(raw));
 const window={version:'scene-playback-window-1',start_s:0,duration_s:1,frame_count:30,render_fps:30,
  sample_rate_hz:48000,audio_sample_count:48000,final_fade_s:.01,original_events_sha256:events_sha256,
  label:'Draft · existing score excerpt · adaptive scoring pending',approval:null,projections:[],omitted:[],truncated:[]};
 const handoff={scene_id:scene.id,features:{sha256:'a'.repeat(64)},clock:{duration_s:1,video_frame_count:30},approval:null};
 const music_handoff_bytes=stable(handoff)+'\n',music_handoff_sha256=await hash(handoff);
 const b={scene,events:[],events_sha256,scene_input_bytes:'{}\n',source_events_bytes:raw,
  playback_policy:{version:window.version,start_s:0,duration_s:1,render_fps:30,final_fade_s:.01},
  playback_window:window,playback_window_bytes:stable(window)+'\n',playback_window_sha256:await hash(window),
  music_handoff:handoff,music_handoff_bytes,music_handoff_sha256,
  music_handoff_binding:{version:'scene-music-input-binding-1',handoff_sha256:music_handoff_sha256,
   features_sha256:'a'.repeat(64),handoff_index_sha256:'b'.repeat(64)}};
 return {b,plan};
}

test('exact playback and handoff bytes pass preparation without claiming actual media',async()=>{
 const {b,plan}=await fixture();await verifyBlenderInputs(b as any,plan,sha,stable);
});
for(const field of ['source_events_bytes','playback_window_bytes','music_handoff_bytes'])test('changed exact '+field+' rejects before unlock',async()=>{
 const {b,plan}=await fixture();(b as any)[field]+=' ';await assert.rejects(verifyBlenderInputs(b as any,plan,sha,stable));
});
test('feature binding and handoff scene must agree',async()=>{
 const {b,plan}=await fixture();b.music_handoff_binding.features_sha256='c'.repeat(64);
 await assert.rejects(verifyBlenderInputs(b as any,plan,sha,stable),/Music handoff source/);
});
test('silent support cannot become focus or motif owner',async()=>{
 const {b,plan}=await fixture();(b as any).role_supplement={scene_id:b.scene.id,scored_object_ids:[],validated_contact_ids:[]};
 await assert.rejects(verifyBlenderInputs(b as any,plan,sha,stable),/Scored role/);
});
test('optional exact prepared Blender review candidate', {skip:!process.env.SCENESCORE_REVIEW_BUNDLE},async()=>{
 const b=JSON.parse(fs.readFileSync(process.env.SCENESCORE_REVIEW_BUNDLE!,'utf8'));
 await verifyBlenderInputs(b,JSON.parse(b.plan_bytes),sha,stable);
});

for(const mutation of ['remove_window','remove_policy','different_policy'] as const)test('bound runtime policy rejects '+mutation,async()=>{
 const {b,plan}=await fixture();
 if(mutation==='remove_window')delete (b as any).playback_window;
 if(mutation==='remove_policy')delete (b as any).playback_policy;
 if(mutation==='different_policy')b.playback_policy.final_fade_s=.02;
 await assert.rejects(verifyBlenderInputs(b as any,plan,sha,stable),/Playback policy/);
});
