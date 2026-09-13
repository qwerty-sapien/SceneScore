/** Local integration tests; reuses saved analysis and makes zero model calls. */
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const root='http://127.0.0.1:5188/api/scenescore';
const [a,b]=process.argv.slice(2);if(!a||!b)throw Error('Pass A and B session IDs');
const headers={'X-SceneScore':'1','Content-Type':'application/json'};
async function get(id:string){return await (await fetch(`${root}/${id}`)).json() as any;}
async function post(route:string,data:any){const response=await fetch(`${root}/${route}`,{method:'POST',headers,body:JSON.stringify(data)});return {status:response.status,body:await response.json() as any};}
async function ready(id:string,expected='Ready'){const start=Date.now();while(Date.now()-start<120000){const job=await get(id);if(['Ready','Failed'].includes(job.stage)){assert.equal(job.stage,expected,job.error);return job;}await new Promise(r=>setTimeout(r,500));}throw Error('Job exceeded test timeout');}
const before=await get(a),markers=structuredClone(before.result.markers),settings=structuredClone(before.result.settings);
markers[0].at=Math.max(0,markers[0].at-.2);markers[0].confidence='manual';
const changed=await post(`${a}/render`,{markers,settings:{...settings,transpose:2,ornament:'turn'}});assert.equal(changed.status,202);assert.notEqual(changed.body.stage,'Ready');
assert.equal((await post(`${a}/render`,{markers,settings})).status,409);
const after=await ready(a);assert.notEqual(after.revision,before.revision);assert.notEqual(after.result.audio[0].sha256,before.result.audio[0].sha256);assert.equal(after.result.api_response_id,before.result.api_response_id);assert.equal(after.result.markers[0].at,markers[0].at);
console.log('Event/ornament/key edit changed rendered audio; existing API response preserved.');
assert.equal((await post(`${a}/render`,{markers:[{...markers[0],at:40}],settings})).status,400);
assert.equal((await post(`${a}/render`,{markers,settings:{...settings,gainDb:0}})).status,400);
assert.equal((await post(`${a}/render`,{markers:before.result.markers,settings})).status,202);
const restored=await ready(a);assert.equal(restored.result.audio[0].sha256,before.result.audio[0].sha256);
const jobB=await get(b);assert.equal((await post(`${b}/render`,{markers:jobB.result.markers,settings:jobB.result.settings})).status,202);await ready(b);
console.log('Restoring events/settings restored byte-identical audio. Both final scores rebuilt.');
const invalid=await fetch(`${root}/upload`,{method:'POST',headers:{'X-SceneScore':'1','Content-Type':'application/octet-stream','X-File-Name':'broken.mp4'},body:new Uint8Array([0,1,2,3])});assert.equal(invalid.status,202);const broken:any=await invalid.json();await ready(broken.id,'Failed');
const longSource=await fs.readFile('../B.mov');
const oversized=await fetch(`${root}/upload`,{method:'POST',headers:{'X-SceneScore':'1','Content-Type':'application/octet-stream','X-File-Name':'B-full-41s.mov'},body:longSource});assert.equal(oversized.status,202);const long:any=await oversized.json();const failed=await ready(long.id,'Failed');assert.match(failed.error,/shorter than 30/);await assert.rejects(fs.stat(`artifacts/scenescore/${long.id}/api-response.json`));
console.log('Malformed upload and full 41-second B rejected before API analysis.');
const cancellation=await fetch(`${root}/upload`,{method:'POST',headers:{'X-SceneScore':'1','Content-Type':'application/octet-stream','X-File-Name':'cancel-test.mov'},body:longSource});assert.equal(cancellation.status,202);const cancel:any=await cancellation.json();assert.equal((await post(`${cancel.id}/cancel`,{})).status,200);await ready(cancel.id,'Failed');
const health=await get('health');assert.equal(health.active,null);
const page=await fetch('http://127.0.0.1:5188/scenescore.html');assert.equal(page.status,200);assert.ok((await page.text()).includes('/src/scenescore/main.tsx'));
const sessions=await get('sessions');assert.ok(sessions.some((s:any)=>s.id===a&&s.ready));assert.ok(sessions.some((s:any)=>s.id===b&&s.ready));
await fs.mkdir('reports/scenescore-demo',{recursive:true});await fs.writeFile('reports/scenescore-demo/flow-checks.json',JSON.stringify({utc:new Date().toISOString(),status:'passed',model_calls:0,edits_change_audio:true,restore_audio_byte_identical:true,api_response_reused:true,concurrent_request_rejected:true,invalid_events_rejected:true,invalid_gain_rejected:true,malformed_upload_rejected:broken.id,overlength_upload_rejected:long.id,cancelled_job:cancel.id,active_job_after_tests:health.active,saved_sessions_reopenable:true,browser_interaction:'NOT_RUN'},null,2));
console.log('Cancellation released the job slot; saved drafts and HTML route available.');
