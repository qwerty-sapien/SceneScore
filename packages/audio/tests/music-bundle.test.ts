import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from './fixture.json';
import {copy,stable,hash,sha,verifyBundle,type Bundle} from '../model';
import {createSimulation,latencyIntervals} from '../control';
import {musicalInputBytes} from '../vertical-binding';
import {VERTICAL_TABLE_SHA256,VERTICAL_TRANSITION_VERSION} from '../model';

async function boundBundle(){
 const b=copy(fixture.bundle) as unknown as Bundle,p=JSON.parse(b.plan_bytes);
 const sort=(a:{id:string},c:{id:string})=>a.id<c.id?-1:a.id>c.id?1:0;
 b.scene_input_bytes=stable({scene:b.scene,states:[...b.states].sort(sort),interactions:[...b.interactions].sort(sort)})+'\n';
 b.composition_input_bytes=stable({composition:b.composition,groove:b.groove})+'\n';
 b.events_bytes=stable(b.events)+'\n';
 b.scene_hash=await sha(new TextEncoder().encode(b.scene_input_bytes));
 b.composition_hash=await sha(new TextEncoder().encode(b.composition_input_bytes));
 b.events_sha256=await hash(b.events);
 Object.assign(p,{scene_hash:b.scene_hash,composition_hash:b.composition_hash});
 b.plan_bytes=stable(p)+'\n';b.plan_sha256=await hash(p);return b;
}

test('exact prepared bytes accept an intact bundle and reject mutated parsed score or scene',async()=>{
 const b=await boundBundle();await verifyBundle(b);
 const score=copy(b);score.events[0].velocity--;
 await assert.rejects(verifyBundle(score),/Score bytes mismatch/);
 const scene=copy(b);scene.states[0].transform.position_m[2]+=.1;
 await assert.rejects(verifyBundle(scene),/Scene bytes mismatch/);
 const composition=copy(b);composition.composition.tempo_map[0].bpm++;
 await assert.rejects(verifyBundle(composition),/Composition bytes mismatch/);
});

test('changed encoded source bytes cannot retain an earlier approval input hash',async()=>{
 const b=await boundBundle();b.scene_input_bytes+=' ';
 await assert.rejects(verifyBundle(b),/Scene bytes mismatch/);
});

test('bound motion controls and holds cannot change while the exact plan remains unchanged',async()=>{
 const b=await boundBundle();b.holds=[{start_s:1,end_s:2}];
 const track={clock:'scene' as const,epoch:b.scene.id,duration_s:b.scene.duration_s,events:[]};
 b.control_track=track;b.control_track_input_bytes=stable(track)+'\n';b.holds_bytes=stable(b.holds)+'\n';
 const binding={control_track_sha256:await hash(track),holds_sha256:await hash(b.holds),mapped_musical_sha256:await sha(musicalInputBytes(b.events_bytes!))};
 b.mapping_binding_bytes=stable(binding)+'\n';b.mapping_provenance={binding,binding_sha256:await hash(binding)};
 const p=JSON.parse(b.plan_bytes);p.provenance.input_hashes.push(b.mapping_provenance.binding_sha256);
 b.plan_bytes=stable(p)+'\n';b.plan_sha256=await hash(p);await verifyBundle(b);
 const changed=copy(b);changed.holds=[{start_s:1,end_s:3}];
 await assert.rejects(verifyBundle(changed),/Hold bytes mismatch/);
 const unbound=copy(b);unbound.mapping_binding_bytes=undefined;
 await assert.rejects(verifyBundle(unbound),/Unbound music control track/);
 const edited=copy(b);edited.events[0].velocity--;
 edited.events_bytes=stable(edited.events)+'\n';edited.events_sha256=await hash(edited.events);
 await assert.rejects(verifyBundle(edited),/Plan-bound musical content mismatch/);
 const missing=copy(b);missing.control_track=undefined;missing.music_vertical={version:VERTICAL_TRANSITION_VERSION,
  table_id:'scenescore-transition-table',table_version:'1',table_sha256:VERTICAL_TABLE_SHA256,
  eligible_arrival_ticks:[3840,7680,11520],jazz_enabled:false,audition_status:'AUDITION_PENDING',approval:null};
 await assert.rejects(verifyBundle(missing),/Unbound music control track/);
 const missingScene=copy(b);missingScene.music_vertical=missing.music_vertical;missingScene.scene_input_bytes=undefined;
 await assert.rejects(verifyBundle(missingScene),/Unbound vertical scene or composition/);
 const missingComposition=copy(b);missingComposition.music_vertical=missing.music_vertical;missingComposition.composition_input_bytes=undefined;
 await assert.rejects(verifyBundle(missingComposition),/Unbound vertical scene or composition/);
});

test('musical projection preserves Python numeric tokens and strips only circular top-level fields',()=>{
 const source=' [ {"plan_id":"x","resolved_time_s":1.0,"id":"b","provenance":{"keep":0.0}}, {"id":"a","resolved_time_s":0.0,"duration_s":1.0,"plan_id":"y","provenance":{}} ] ';
 assert.equal(new TextDecoder().decode(musicalInputBytes(source)), '[{"duration_s":1.0,"id":"a","resolved_time_s":0.0},{"id":"b","resolved_time_s":1.0}]\n');
});

test('acknowledgement interval and musical wait are separate clock intervals',()=>{
 const envelope=createSimulation({audio_s:100,audio_epoch:'test',approved_plan_hash:'a'.repeat(64),
  scene_policy_id:'test',signed_semitones:2,lanes:{master_gain_db:-18,articulation:'score',expression_preset:'neutral'}});
 Object.assign(envelope.timing,{t4_received_s:100.004,t5_ack_onset_s:100.024,t6_boundary_s:102.5});
 const result=latencyIntervals(envelope);
 assert.ok(Math.abs(result.mapped_request_to_receipt_ms!-4)<1e-8);
 assert.ok(Math.abs(result.accepted_to_scheduled_ack_ms!-20)<1e-8);
 assert.ok(Math.abs(result.ack_to_arrival_wait_ms!-2476)<1e-8);
 assert.equal(result.detector_closure_ms,null);assert.equal(result.physical_output_measured,false);
});
