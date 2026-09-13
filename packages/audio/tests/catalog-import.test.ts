import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from './fixture.json';
import {copy,stable,hash,sha,type Bundle} from '../model';
import {inspectImport,MAX_JSON_BYTES,MAX_VIDEO_BYTES} from '../../../apps/web/src/library/catalog';

async function prepared(){
 const b=copy(fixture.bundle) as unknown as Bundle,p=JSON.parse(b.plan_bytes),media=new Blob(['fixture media bytes, not a real rendered animation']);
 const sort=(a:{id:string},c:{id:string})=>a.id<c.id?-1:a.id>c.id?1:0;
 b.video_sha256=await sha(await media.arrayBuffer());
 b.scene_input_bytes=stable({scene:b.scene,states:[...b.states].sort(sort),interactions:[...b.interactions].sort(sort)})+'\n';
 b.composition_input_bytes=stable({composition:b.composition,groove:b.groove})+'\n';
 b.events_bytes=stable(b.events)+'\n';b.events_sha256=await hash(b.events);
 b.scene_hash=await sha(new TextEncoder().encode(b.scene_input_bytes));b.composition_hash=await sha(new TextEncoder().encode(b.composition_input_bytes));
 Object.assign(p,{scene_hash:b.scene_hash,composition_hash:b.composition_hash});b.plan_bytes=stable(p)+'\n';b.plan_sha256=await hash(p);
 return {b,media};
}
const json=(b:unknown)=>new Blob([JSON.stringify(b)]);
test('local import retains exact source and video, without creating approval',async()=>{
 const {b,media}=await prepared(),raw=JSON.stringify({...b,approval:{decision:'approved',reviewer:'untrusted file'}});
 const r=await inspectImport(new Blob([raw]),media);
 assert.equal(r.raw,raw);assert.equal(r.media,media);assert.equal(r.item.source,'imported');
 assert.equal(r.item.entries.length,1);assert.equal(r.item.entries[0].url,'');assert.equal('approval' in r,false);
});
test('wrong video and mutated score or scene cannot enter the library',async()=>{
 const {b,media}=await prepared();await assert.rejects(inspectImport(json(b),new Blob(['wrong video'])),/Video hash mismatch/);
 const score=copy(b);score.events[0].velocity--;await assert.rejects(inspectImport(json(score),media),/Score bytes mismatch/);
 const scene=copy(b);scene.states[0].transform.position_m[0]++;await assert.rejects(inspectImport(json(scene),media),/Scene bytes mismatch/);
});
test('video-only, raw Blender metadata and unbound prepared data give actionable errors',async()=>{
 const {b,media}=await prepared();await assert.rejects(inspectImport(new Blob(['bad json']),media),/not valid JSON/);
 await assert.rejects(inspectImport(json(b.scene),media),/prepared SceneScore sidecar/);
 const score=copy(b);delete score.events_bytes;delete score.source_events_bytes;await assert.rejects(inspectImport(json(score),media),/Score is missing/);
 const scene=copy(b);delete scene.scene_input_bytes;await assert.rejects(inspectImport(json(scene),media),/Scene is missing/);
});
test('oversized files fail before reading their content',async()=>{
 const {media}=await prepared();const forbidden={size:MAX_JSON_BYTES+1,text(){throw Error('must not read');}} as unknown as Blob;
 await assert.rejects(inspectImport(forbidden,media),/under 64 MB/);
 await assert.rejects(inspectImport(json({}),{size:MAX_VIDEO_BYTES+1} as Blob),/under 256 MB/);
});
test('duplicate scheduled IDs are rejected even with a matching score digest',async()=>{
 const {b,media}=await prepared();b.events.push(copy(b.events[0]));b.events_bytes=stable(b.events)+'\n';b.events_sha256=await hash(b.events);
 await assert.rejects(inspectImport(json(b),media),/duplicate event IDs/);
});
