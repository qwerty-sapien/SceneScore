import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import fixture from './fixture.json';
import type {ArrangementPlan,ScoreEvent} from '../../contracts/generated';
import {Timeline} from '../transport';
import {Engine,renderPerformedOffline} from '../engine';
import {copy,keyboardAction,isVerticalVoice,VERTICAL_TABLE_SHA256,VERTICAL_TRANSITION_VERSION,type Bundle} from '../model';

function bundle(){const b=copy(fixture.bundle) as unknown as Bundle;b.music_vertical={version:VERTICAL_TRANSITION_VERSION,table_id:'scenescore-transition-table',table_version:'1',table_sha256:VERTICAL_TABLE_SHA256,eligible_arrival_ticks:[3840,7680,11520],jazz_enabled:false,audition_status:'AUDITION_PENDING',approval:null};return b;}
function setup(b=bundle(),rate=8000,prepare=true){
 const p=JSON.parse(b.plan_bytes) as ArrangementPlan,t=new Timeline(b,p,'a'.repeat(64)),e=new Engine(t);
 const starts:{at:number;offset:number;source:any}[]=[],stops:{at:number;source:any}[]=[];
 const param=()=>({value:1,values:[] as [number,number][],setValueAtTime(v:number,at:number){this.values.push([v,at]);},linearRampToValueAtTime(v:number,at:number){this.values.push([v,at]);},cancelScheduledValues(){},setTargetAtTime(){}});
 const gain=()=>({gain:param(),connect(){},disconnect(){}});
 const context={currentTime:1,sampleRate:rate,buffers:0,createGain:gain,createBuffer(_c:number,n:number,sampleRate:number){this.buffers++;const data=new Float32Array(n);return {length:n,duration:n/sampleRate,getChannelData:()=>data};},createBufferSource(){return {buffer:null,connect(){},disconnect(){},start(at:number,offset=0){starts.push({at,offset,source:this});},stop(at:number){stops.push({at,source:this});}};},async resume(){},async close(){}};
 e.context=context as unknown as AudioContext;e.buses={soundtrack:gain(),foley:gain()} as unknown as Engine['buses'];e.master=gain() as unknown as GainNode;e.anchorAudio=0;e.anchorScene=0;if(prepare)e.prepare();t.playing=true;
 return {b,p,t,e,context,starts,stops};
}
function submit(s:ReturnType<typeof setup>,sign=2){return s.e.submit(keyboardAction(s.p,s.t.planHash,s.t.epoch,s.context.currentTime,sign,'SYNTHETIC_TEST'));}

test('both guide-tone acknowledgements schedule at receipt +20 ms before any source access or synthesis',async()=>{
 const s=setup();try{
  const guarded=(events:ScoreEvent[])=>new Proxy(events,{get(target,key,receiver){assert.equal(s.starts.length,2,'score read before the two acknowledgement onsets');return Reflect.get(target,key,receiver);}});
  s.t.original=guarded(s.t.original);s.t.events=guarded(s.t.events);s.b.events=guarded(s.b.events);
  const count=s.context.buffers;s.context.createBuffer=()=>{throw Error('synthesis during submit');};
  const d=submit(s);assert.equal(d.status,'queued');assert.equal(d.ack_onset_audio_s,1.02);assert.deepEqual(s.starts.map(x=>x.at),[1.02,1.02]);assert.equal(s.context.buffers,count);
  assert.equal(d.audio_received_s,d.action.request.seconds);assert.equal(d.boundary_s,d.arrival_scene_s);assert.equal(d.boundary_audio_s,d.arrival_audio_s);assert.ok(d.progression_start_s!<d.arrival_scene_s!);assert.ok(d.arrival_scene_s!<d.progression_end_s!);assert.equal(s.t.currentTonic(),0);assert.equal(s.b.music_vertical!.approval,null);
 }finally{await s.e.close();}
});

test('sounding lead/object/brush/Foley stay running while only the harmonic sustain is clipped',async()=>{
 const b=bundle(),ref=b.events.find(isVerticalVoice)!;const sustain={...ref,id:'long-harmony',lane_id:'harmony-0',resolved_time_s:0,start_tick:0,duration_s:9,duration_ticks:13824,articulation:'legato'};
 b.events.push(sustain,...['piano_or_lead','motif-a','brushes','contact:a|b'].map((lane_id,i)=>({...sustain,id:`protected-${i}`,lane_id,event_type:(i===2?'brush':i===3?'foley':'note') as ScoreEvent['event_type'],midi_pitch:i>=2?null:72})));
 const s=setup(b);try{
  s.e.fill();const existing=[...s.e.nodes];const before=s.stops.length;const d=submit(s);assert.equal(d.status,'queued');const added=s.stops.slice(before);
  for(const node of existing.filter(n=>n.event.id.startsWith('protected-'))){assert.ok(!added.some(x=>x.source===node.source));assert.equal((node.gain.gain as unknown as {values:unknown[]}).values.length,2,'independent voice keeps its original envelope');}
  const node=existing.find(n=>n.event.id==='long-harmony')!;assert.ok(added.some(x=>x.source===node.source&&x.at===d.progression_start_audio_s));
  const count=s.starts.length;s.e.fill();assert.equal(s.starts.length,count,'before-fragment must not duplicate a sounding sustain');
  s.context.currentTime=d.progression_end_s!+.01;s.e.fill();const resumed=s.e.nodes.find(n=>n.source_id==='long-harmony'&&n.event.resolved_time_s===d.progression_end_s)!;
  assert.ok(resumed);const start=s.starts.find(x=>x.source===resumed.source)!;assert.ok(start.offset>=d.progression_end_s!,'resume uses the original buffer phase/decay offset');
 }finally{await s.e.close();}
});

test('actual tonic updates at arrival while pending remains through the complete landing',async()=>{
 const s=setup();try{const d=submit(s);assert.equal(s.t.currentTonic(),0);s.t.advance(d.progression_start_s!);assert.equal(d.status,'transitioning');assert.equal(s.t.currentTonic(),0);
  const slot=s.t.verticalPending()!.program.entry.slots[0];assert.deepEqual(s.t.currentChord(d.progression_start_s!),{root_pc:slot.root_pc,quality:slot.quality});
  s.context.currentTime=d.arrival_scene_s!;s.t.advance(s.context.currentTime);assert.equal(s.t.currentTonic(),2);assert.equal(d.status,'executed');assert.equal(submit(s).reason,'one_pending_request_limit');
  s.context.currentTime=d.progression_end_s!+.01;s.t.advance(s.context.currentTime);assert.equal(s.t.pending.length,0);assert.equal(submit(s).status,'queued');
 }finally{await s.e.close();}
});

test('two signed modulations retain clipped timing, octave history, independent lanes and four exported acknowledgements',async()=>{
 const b=bundle(),long=b.events.find(e=>e.lane_id==='harmony-0')!;Object.assign(long,{resolved_time_s:0,start_tick:0,duration_s:9,duration_ticks:13824,articulation:'legato'});
 const s=setup(b);try{const first=submit(s);s.context.currentTime=first.progression_end_s!+.01;s.t.advance(s.context.currentTime);const second=submit(s);assert.equal(second.status,'queued');s.context.currentTime=second.progression_end_s!+.01;s.t.advance(s.context.currentTime);
  assert.equal(s.t.currentTonic(),4);const events=s.t.performedEvents();assert.equal(events.filter(e=>e.id.includes(':ack:')).length,4);assert.equal(new Set(events.map(e=>e.id)).size,events.length);
  const last=s.t.verticalSlices.get(events.find(e=>e.id.startsWith(long.id)&&e.resolved_time_s===second.progression_end_s)!.id)!;assert.equal(last.event.midi_pitch,long.midi_pitch!+4);assert.equal(last.event.duration_s,9-second.progression_end_s!);
  for(const original of s.t.original.filter(e=>!isVerticalVoice(e)))assert.strictEqual(events.find(e=>e.id===original.id),original);
  assert.ok(events.every(e=>e.resolved_time_s>=0&&e.duration_s>0&&e.resolved_time_s+e.duration_s<=s.b.scene.duration_s+1e-9));
  assert.equal(s.e.gainDb,-18);
 }finally{await s.e.close();}
});

test('near-miss holds are filtered before playback and no candidate overlaps them',async()=>{
 const b=bundle();b.holds=[{start_s:1.1,end_s:3}];const s=setup(b);try{const d=submit(s);assert.equal(d.arrival_scene_s,5);assert.ok(d.progression_start_s!>=3);assert.deepEqual(s.starts.map(x=>x.at),[1.02,1.02]);
  assert.ok([...s.t.vertical!.programs.values()].every(p=>p.end_s<=1.1||p.start_s>=3));
 }finally{await s.e.close();}
 const invalid=bundle();invalid.holds=Array.from({length:513},()=>({start_s:0,end_s:1}));assert.throws(()=>new Timeline(invalid,JSON.parse(invalid.plan_bytes),'a'.repeat(64)),/hold budget/);
});

test('pause cancels both acknowledgement sources and a pending program; seek clears performed history',async()=>{
 const s=setup();try{const d=submit(s),ackSources=s.starts.map(x=>x.source);s.context.currentTime=1.01;s.e.pause();assert.equal(s.t.pending.length,0);assert.equal(d.status,'cancelled_on_transport_reset');assert.equal(s.t.tonic,0);assert.equal(s.e.nodes.length,0);for(const source of ackSources)assert.ok(s.stops.some(x=>x.source===source&&x.at===1.02));assert.equal(s.t.performedEvents().filter(e=>e.id.includes(':ack:')).length,0);
  s.t.playing=true;s.context.currentTime=1.02;submit(s);s.e.seek(0);assert.equal(s.t.verticalHistory.length,0);assert.deepEqual(s.t.performedEvents(),s.t.original);assert.equal(s.t.currentTonic(),0);assert.equal(s.e.refreshTimer,null);
 }finally{await s.e.close();}
});

test('pause after actual arrival retains the executed key and completed past audio in the editable export',async()=>{
 const s=setup();try{const d=submit(s);s.context.currentTime=d.arrival_scene_s!+.05;s.e.pause();assert.equal(s.t.currentTonic(),2);assert.equal(s.t.pending.length,0);assert.equal(s.t.performedEvents().filter(e=>e.id.includes(':ack:')).length,2);assert.ok(s.t.performedEvents().some(e=>e.phrasing==='new-tonic-arrival'));assert.equal(s.e.discontinuous,true);assert.throws(()=>s.e.exportReady());
 }finally{await s.e.close();}
});

test('partial acknowledgement scheduling failure fails closed and stops the first source',async()=>{
 const s=setup();try{const source=s.context.createBufferSource.bind(s.context);let count=0;s.context.createBufferSource=()=>{if(++count===2)throw Error('fixture scheduling failure');return source();};const d=submit(s);assert.equal(d.status,'suppressed');assert.match(d.reason!,/fixture scheduling failure/);assert.equal(s.t.pending.length,0);assert.equal(s.t.verticalHistory.length,0);assert.equal(s.t.tonic,0);assert.ok(s.stops.some(x=>x.source===s.starts[0].source&&x.at===1));
 }finally{await s.e.close();}
});

test('cooperative pre-play cache has bounded slices and cancellation cannot publish stale readiness',async()=>{
 const s=setup(bundle(),8000,false);try{const preparing=s.e.prepareAsync();assert.equal(s.t.preparationReady,false);await preparing;assert.ok(s.e.refreshStats.slices>1);assert.ok([...s.e.cache.values()].reduce((sum,b)=>sum+b.length*4,0)<128*1024*1024);assert.equal(s.t.preparationReady,true);
  const second=s.e.prepareAsync();s.e.cancelRefresh();await assert.rejects(second,/cancelled/);assert.equal(s.e.refreshTimer,null);assert.equal(s.t.preparationReady,false);
 }finally{await s.e.close();}
});

test('normalized pitched buffers reuse velocity variants with exact independent gain restoration',async()=>{
 const b=bundle(),source=b.events.find(isVerticalVoice)!;b.events.push({...source,id:'gain-variant',velocity:37,dynamics_db:-7});const s=setup(b);try{
  const variant=s.t.original.find(e=>e.id==='gain-variant')!,original=s.t.original.find(e=>e.id===source.id)!;assert.equal(s.e.key(original),s.e.key(variant));s.context.currentTime=source.resolved_time_s;s.e.fill();const node=s.e.nodes.find(n=>n.event.id==='gain-variant')!;assert.ok(node);assert.equal(node.level,37/127*10**(-7/20));assert.equal(s.e.gainDb,-18);
 }finally{await s.e.close();}
});

const candidate=process.env.SCENESCORE_MUSIC_BUNDLE;
test('exact prepared music candidate fits the real 48kHz cache and two controls',{skip:!candidate||!existsSync(candidate)},async()=>{
 const s=setup(JSON.parse(readFileSync(candidate!,'utf8')),48000,false);try{await s.e.prepareAsync();const bytes=[...s.e.cache.values()].reduce((sum,b)=>sum+b.length*4,0);assert.ok(bytes<128*1024*1024);s.context.currentTime=19;const first=submit(s,-2);assert.equal(first.status,'queued');s.context.currentTime=first.progression_end_s!+.01;s.t.advance(s.context.currentTime);s.context.currentTime=24.5;const second=submit(s,2);assert.equal(second.status,'queued');console.log('SYNTHETIC_TEST music runtime evidence',JSON.stringify({bytes,buffers:s.e.cache.size,stats:s.e.refreshStats,first,second}));
 }finally{await s.e.close();}
});


test('restart from the completed end prepares the restored generation before accepting another control',async()=>{
 const s=setup();try{s.context.currentTime=s.b.scene.duration_s;s.e.fill();assert.equal(s.e.completed,true);assert.equal(s.t.position,s.b.scene.duration_s);await s.e.play();assert.equal(s.e.preparedVersion,s.t.preparationVersion);assert.equal(s.t.position,0);assert.equal(submit(s).reason,'transport_preroll');s.context.currentTime=s.e.anchorAudio+1;const d=submit(s);assert.equal(d.status,'queued');assert.equal(d.arrival_audio_s,s.e.anchorAudio+d.arrival_scene_s!);assert.equal(d.ack_onset_audio_s,s.context.currentTime+.02);
 }finally{await s.e.close();}
});


test('offline performed rendering uses full prepared source buffers and preserved fragment offsets',async()=>{
 const b=bundle(),long=b.events.find(e=>e.lane_id==='harmony-0')!;Object.assign(long,{resolved_time_s:0,start_tick:0,duration_s:9,duration_ticks:13824,articulation:'legato'});
 const s=setup(b),previous=globalThis.OfflineAudioContext;try{const d=submit(s);const slice=[...s.t.verticalSlices.values()].find(x=>x.source_id===long.id&&x.event.resolved_time_s===d.progression_end_s)!;const observed:{offset:number;buffer:any}[]=[];
  globalThis.OfflineAudioContext=class {sampleRate=8000;destination={};createGain=()=>s.context.createGain();createBuffer=(c:number,n:number,rate:number)=>s.context.createBuffer(c,n,rate);createBufferSource(){return {buffer:null as any,connect(){},start(_at:number,offset=0){observed.push({offset,buffer:this.buffer});},stop(){}};}async startRendering(){return {} as AudioBuffer;}} as unknown as typeof OfflineAudioContext;
  await renderPerformedOffline(s.t,s.b.scene.duration_s,-18,{soundtrack:true,foley:true},8000,undefined,'piano');const resumed=observed.find(x=>x.offset===slice.offset_s&&x.buffer.duration===9);assert.ok(resumed);assert.equal(resumed.offset,d.progression_end_s);
 }finally{globalThis.OfflineAudioContext=previous;await s.e.close();}
});

test('oversized pre-play cache fails before allocating buffers or making playback ready',async()=>{
 const s=setup(bundle(),1000000,false);try{await assert.rejects(s.e.prepareAsync(),/memory budget/);assert.equal(s.context.buffers,0);assert.equal(s.e.cache.size,0);assert.equal(s.t.preparationReady,false);assert.equal(s.e.refreshTimer,null);
 }finally{await s.e.close();}
});
