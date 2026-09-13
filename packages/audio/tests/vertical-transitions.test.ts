import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import fixture from './fixture.json';
import rawTable from '../../../modules/music/fixtures/transition-table-v1.json';
import type {ArrangementPlan,ScoreEvent} from '../../contracts/generated';
import {copy,prepareVerticalTable,lookupVerticalTransition,prepareVerticalTransitions,selectVerticalTransition,
 verticalPitchVariant,verticalEventFragments,clipVerticalEvent,VERTICAL_TABLE_SHA256,VERTICAL_TRANSITION_VERSION,
 VERTICAL_LANES,type Bundle} from '../model';

const table=prepareVerticalTable();
function setup(){
 const b=copy(fixture.bundle) as unknown as Bundle,p=JSON.parse(b.plan_bytes) as ArrangementPlan;
 b.music_vertical={version:VERTICAL_TRANSITION_VERSION,table_id:'scenescore-transition-table',table_version:'1',
  table_sha256:VERTICAL_TABLE_SHA256,eligible_arrival_ticks:[3840,7680,11520],jazz_enabled:false,
  audition_status:'AUDITION_PENDING',approval:null};
 return {b,p};
}
const base=setup(),prepared=prepareVerticalTransitions(base.b,base.p);
const lanes=new Set<string>(VERTICAL_LANES);

test('exact frozen 216-entry table has concrete bounded voice leading and stable arrivals',()=>{
 assert.equal(createHash('sha256').update(readFileSync(new URL('../../../modules/music/fixtures/transition-table-v1.json',import.meta.url))).digest('hex'),VERTICAL_TABLE_SHA256);
 assert.equal(table.size,216);assert.equal([...table.values()].filter(e=>e.tier==='contract_default').length,72);
 for(const e of table.values()){
  assert.equal(e.to_pc,(e.from_pc+e.signed_semitones+12)%12);assert.equal(e.slots.at(-1)!.root_pc,e.to_pc);
  assert.equal(e.slots.at(-1)!.offset_ticks,0);
  const raw=rawTable.resolved.find(r=>r.gesture_id===e.gesture_id&&r.from_pc===e.from_pc&&r.signed_semitones===e.signed_semitones&&r.lead_bars===e.lead_bars)!;
  for(let s=0;s<e.slots.length;s++){
   const pitches=e.slots[s].pitches;assert.equal(pitches[0]%12,raw.slots[s].root_pc);
   assert.ok(pitches.every(p=>p>=28&&p<=96));assert.equal(new Set(pitches.slice(1).map(p=>p%12)).size,3);
   assert.ok(pitches.slice(1).every(p=>raw.slots[s].pitch_classes.includes(p%12)));
   const defining:Record<string,number[]>={dom7:[4,10],dom7b5:[4,6,10],min7:[3,10],maj69:[4,9],dim7:[3,6,9]};
   assert.ok(defining[raw.slots[s].quality].every(interval=>pitches.some(p=>p%12===(raw.slots[s].root_pc+interval)%12)));
   if(s){const a=e.slots[s-1].pitches,b=pitches;
    assert.ok(a.slice(1).every((p,i)=>Math.abs(p-b[i+1])<=3));
    assert.ok(!((a[3]-a[0])%12===7&&(b[3]-b[0])%12===7&&(b[0]-a[0])*(b[3]-a[3])>0));
    const common=a.slice(1).some(p=>b.slice(1).some(q=>q%12===p%12));
    if(common)assert.ok(a.slice(1).some((p,i)=>p===b[i+1]));
   }
  }
 }
});

test('every enabled edge is indexed and jazz is inaccessible even for its ±2 edges',()=>{
 for(let pc=0;pc<12;pc++)for(const sign of [-2,2])for(const lead of [.5,1,2]){
  const entry=lookupVerticalTransition(table,pc,sign,lead);assert.strictEqual(table.get(entry.key),entry);
  assert.throws(()=>lookupVerticalTransition(table,pc,sign,lead,'auditioned_jazz'),/jazz_audition_required/);
 }
 assert.throws(()=>lookupVerticalTransition(table,0,5,.5),/transition_not_prepared/);
 assert.equal(selectVerticalTransition(prepared,0,5,0,10),undefined);
});

test('all precomputed programs preserve independent lanes and acknowledgement velocity',()=>{
 assert.ok(prepared.programs.size>0);
 for(const program of prepared.programs.values()){
  assert.ok(program.events.length+program.acknowledgement.length<=24);
  assert.equal(program.acknowledgement.length,2);
  const slot=program.entry.slots[0],guides=slot.quality==='min7'?[3,10]:[4,10];
  assert.deepEqual(program.acknowledgement.map(e=>e.midi_pitch!%12).sort((a,b)=>a-b),guides.map(n=>(slot.root_pc+n)%12).sort((a,b)=>a-b));
  for(const e of program.acknowledgement){assert.ok(e.velocity<=60);assert.equal(e.resolved_time_s,0);assert.equal(e.duration_s,.12);}
  for(const e of program.events){
   assert.ok(lanes.has(e.lane_id));assert.ok(e.midi_pitch!>=base.p.register_min&&e.midi_pitch!<=base.p.register_max);
   const candidates=base.b.events.filter(x=>x.lane_id===e.lane_id&&x.event_type==='note'&&x.resolved_time_s<=e.resolved_time_s);
   const source=candidates.at(-1)??base.b.events.find(x=>x.lane_id===e.lane_id)!;
   for(const field of ['velocity','dynamics_db','articulation','timbre_id','instrument_id','object_id'] as const)assert.equal(e[field],source[field]);
   assert.ok(e.duration_s>0);assert.ok(e.resolved_time_s>=program.start_s);
  }
  assert.equal(program.events.filter(e=>e.resolved_time_s===program.arrival_s).length,4);
 }
});

test('near-boundary selection uses earliest feasible safe arrival and honours strict expiry',()=>{
 const selection=selectVerticalTransition(prepared,0,2,2.45,8.45)!;
 assert.equal(selection.arrival_s,5);assert.ok(selection.start_s>=2.45+.175);
 assert.strictEqual(selection,prepared.programs.get(selection.id));
 assert.equal(selectVerticalTransition(prepared,0,2,2.45,5),undefined);
 assert.equal(selectVerticalTransition(prepared,0,2,7,20),undefined);
 for(const [now,lead] of [[6,.5],[4,1],[2,2]]){
  const sparse={...prepared,arrivals:[{tick:11520,at:7.5}]};
  const program=selectVerticalTransition(sparse,0,2,now,10)!;assert.equal(program.entry.lead_bars,lead);
  assert.ok(program.arrival_s-program.entry.lead_bars*prepared.bar_seconds>=now+.175);
 }
});

test('accepted-path selector never traverses original score or constructs a program',()=>{
 const {b,p}=setup(),ready=prepareVerticalTransitions(b,p);
 b.events=new Proxy(b.events,{get(){throw Error('accepted path read source score');}});
 // All prepared values and their arrays are frozen; selection only returns references.
 const first=selectVerticalTransition(ready,0,2,1,7)!;
 for(let i=0;i<100;i++)assert.strictEqual(selectVerticalTransition(ready,0,2,1,7),first);
 assert.ok(Object.isFrozen(first));assert.ok(Object.isFrozen(first.events));assert.ok(Object.isFrozen(first.acknowledgement));
 assert.ok(first.start_s>1+.02); // Parent engine can safely schedule the dyad at receipt +20ms.
});

test('unaffected lead/object/brush/Foley events retain reference and all independent fields',()=>{
 const reference=base.b.events.find(e=>e.event_type==='note')!;
 const untouched:ScoreEvent[]=[
  {...reference,id:'lead',lane_id:'piano_or_lead'},
  {...reference,id:'object',lane_id:'motif-voice-a',object_id:'a'},
  {...reference,id:'brush',lane_id:'brushes',event_type:'brush',midi_pitch:null},
  {...reference,id:'foley',lane_id:'contact:a|b',event_type:'foley',midi_pitch:null},
 ];
 const program=selectVerticalTransition(prepared,0,2,1,7)!;
 for(const e of untouched){assert.strictEqual(verticalPitchVariant(prepared,e,2),e);assert.deepEqual(verticalEventFragments(prepared,e,program),[e]);assert.strictEqual(verticalEventFragments(prepared,e,program)[0],e);}
});

test('a long affected sustain is split around the program without gap or double coverage',()=>{
 const {b,p}=setup();const source=b.events.find(e=>e.lane_id==='harmony-0')!;
 Object.assign(source,{resolved_time_s:0,start_tick:0,duration_s:6,duration_ticks:9216,articulation:'legato',phrasing:'near_miss:hold'});
 const ready=prepareVerticalTransitions(b,p),program=selectVerticalTransition(ready,0,2,1,7)!;
 const pieces=verticalEventFragments(ready,source,program);
 assert.equal(pieces.length,2);assert.equal(pieces[0].resolved_time_s+pieces[0].duration_s,program.start_s);
 assert.equal(pieces[1].resolved_time_s,program.end_s);assert.equal(pieces[1].resolved_time_s+pieces[1].duration_s,6);
 const laneProgram=program.events.filter(e=>e.lane_id==='harmony-0');
 const sequence=[pieces[0],...laneProgram,pieces[1]];
 for(let i=1;i<sequence.length;i++)assert.equal(sequence[i-1].resolved_time_s+sequence[i-1].duration_s,sequence[i].resolved_time_s);
 assert.equal(sequence.reduce((n,e)=>n+e.duration_s,0),6);
 assert.equal(laneProgram.at(-1)!.phrasing,'new-tonic-arrival');
 assert.equal(laneProgram.at(-1)!.resolved_time_s,program.arrival_s);
 for(const e of pieces)assert.equal(e.articulation,'legato');
 assert.equal(clipVerticalEvent(source,6,7),null);
});

test('two signed modulations resolve sequentially and tonic variants remain bounded',()=>{
 const first=selectVerticalTransition(prepared,0,2,1,7)!;
 const second=selectVerticalTransition(prepared,first.to_pc,-2,first.end_s+.05,10)!;
 assert.equal(second.from_pc,2);assert.equal(second.to_pc,0);
 for(const e of base.b.events){let variant=e;
  for(const sign of [2,2,2,2,2,2,-2,-2,-2,-2,-2,-2]){
   const before=variant;variant=verticalPitchVariant(prepared,variant,sign);
   if(lanes.has(e.lane_id)){
    assert.ok(variant.midi_pitch!>=28&&variant.midi_pitch!<=96);
    if(before.midi_pitch!+sign>=28&&before.midi_pitch!+sign<=96)assert.equal(variant.midi_pitch,before.midi_pitch!+sign);
   }else assert.strictEqual(variant,e);
  }
 }
 assert.equal(base.b.music_vertical!.approval,null);
});

test('successive overlays preserve a clipped sustain identity, timing and signed pitch history',()=>{
 const {b,p}=setup(),source=b.events.find(e=>e.lane_id==='harmony-0')!;
 Object.assign(source,{resolved_time_s:0,start_tick:0,duration_s:9,duration_ticks:13824,articulation:'legato'});
 const ready=prepareVerticalTransitions(b,p),first=selectVerticalTransition(ready,0,2,1,7)!,
  second=selectVerticalTransition(ready,first.to_pc,2,first.end_s+.05,10)!;
 const firstTail=verticalEventFragments(ready,source,first).at(-1)!;
 const pieces=verticalEventFragments(ready,firstTail,second);
 assert.equal(pieces[0].resolved_time_s,first.end_s);
 assert.equal(pieces[0].resolved_time_s+pieces[0].duration_s,second.start_s);
 assert.equal(pieces[0].midi_pitch,source.midi_pitch!+2);
 assert.equal(pieces[1].resolved_time_s,second.end_s);
 assert.equal(pieces[1].resolved_time_s+pieces[1].duration_s,9);
 assert.equal(pieces[1].midi_pitch,source.midi_pitch!+4);
 assert.equal(pieces[1].articulation,'legato');
 assert.equal(pieces[1].velocity,source.velocity);
});

test('preparation rejects terminal or unordered arrivals, wrong table, and jazz activation',()=>{
 for(const mutate of [
  (b:Bundle)=>b.music_vertical!.eligible_arrival_ticks.push(b.composition.length_ticks),
  (b:Bundle)=>b.music_vertical!.eligible_arrival_ticks.reverse(),
  (b:Bundle)=>b.music_vertical!.eligible_arrival_ticks=[11520],
  (b:Bundle)=>b.music_vertical!.table_sha256='f'.repeat(64),
  (b:Bundle)=>(b.music_vertical as unknown as {jazz_enabled:boolean}).jazz_enabled=true,
  (b:Bundle)=>b.composition.tempo_map.push({tick:3840,bpm:120}),
 ]){const {b,p}=setup();mutate(b);assert.throws(()=>prepareVerticalTransitions(b,p));}
});
