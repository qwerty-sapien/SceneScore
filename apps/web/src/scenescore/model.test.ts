import test from 'node:test';
import assert from 'node:assert/strict';
import {compose,parseAnalysis,validateMarkers,durationCheck,DEFAULT_SETTINGS,type Marker} from './model';
const marker:Marker={id:1,kind:3,at:12,enabled:true,objects:['ball','floor'],evidence:'Apparent touch',start_s:12,end_s:12.2,confidence:'observed'};
test('strict duration and event bounds',()=>{
 for(const n of [0,-1,30,31,NaN,Infinity])assert.throws(()=>durationCheck(n));
 durationCheck(29.99);durationCheck(.2);
 for(const bad of [{...marker,at:30},{...marker,kind:7},{...marker,at:NaN},{...marker,end_s:31}])assert.throws(()=>validateMarkers([bad],29));
 assert.throws(()=>validateMarkers([marker,marker],29));
});
test('uncertain proposals remain disabled and unknown identities fail',()=>{
 const raw={summary:'Bouncing',objects:[{id:'ball',description:'red ball'},{id:'floor',description:'floor'}],events:[{kind:'contact',start_s:12,end_s:12.2,object_ids:['ball','floor'],confidence:'uncertain',explanation:'occlusion'}],limitations:[]};
 assert.equal(parseAnalysis(raw,20).markers[0].enabled,false);
 raw.events[0].object_ids=['invented'];assert.throws(()=>parseAnalysis(raw,20));
});
test('numeric model IDs normalize consistently; normalization collisions fail',()=>{
 const raw:any={summary:'contact',objects:[{id:1,description:'ball'},{id:2,description:'floor'}],events:[{kind:'contact',start_s:1,end_s:1.2,object_ids:[1,2],confidence:'observed',explanation:'touch'}],limitations:[]};
 assert.deepEqual(parseAnalysis(raw,2).markers[0].objects,['object-1','object-2']);
 raw.objects.push({id:'object-1',description:'collision'});assert.throws(()=>parseAnalysis(raw,2));
});
test('incomplete interaction pairs are retained but disabled for review',()=>{
 const raw={summary:'moving',objects:[{id:'ball',description:'ball'}],events:[{kind:'approach',start_s:0,end_s:1,object_ids:['ball'],confidence:'observed',explanation:'moving'}],limitations:[]};
 const marker=parseAnalysis(raw,2).markers[0];assert.equal(marker.enabled,false);assert.equal(marker.confidence,'uncertain');assert.match(marker.evidence,/distinct object pair/);
});
test('nonlooping events apply once across phrases and do not leak into earlier cycles',()=>{
 const score=compose(25,[marker],DEFAULT_SETTINGS,'a'.repeat(64));
 const effected=score.events.filter(e=>e.phrasing.startsWith('scene-replacement'));
 assert.ok(effected.length>0);assert.ok(effected.every(e=>e.resolved_time_s>=12));
 assert.ok(score.events.every(e=>e.resolved_time_s>=0&&e.duration_s>0&&e.resolved_time_s+e.duration_s<=25+1e-8));
 assert.deepEqual(score,compose(25,[marker],DEFAULT_SETTINGS,'a'.repeat(64)));
});
test('effect bypass and disabled events preserve original score; short clips work',()=>{
 const bare=compose(25,[],DEFAULT_SETTINGS,'x').events;
 assert.deepEqual(compose(25,[{...marker,enabled:false}],DEFAULT_SETTINGS,'x').events,bare);
 assert.deepEqual(compose(25,[marker],{...DEFAULT_SETTINGS,effects:false},'x').events,bare);
 assert.ok(compose(.3,[],DEFAULT_SETTINGS,'x').events.length>0);
});
test('key changes preserve gain, articulation, timing and velocity',()=>{
 const a=compose(25,[marker],DEFAULT_SETTINGS,'x').events,b=compose(25,[marker],{...DEFAULT_SETTINGS,transpose:2},'x').events;
 assert.equal(a.length,b.length);a.forEach((e,i)=>assert.deepEqual({...e,midi_pitch:e.midi_pitch===null?null:e.midi_pitch+2},b[i]));
});
