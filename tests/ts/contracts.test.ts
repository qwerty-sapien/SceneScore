import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { validate, validateBundle } from '../../packages/contracts/validate';
import { contentHash } from '../../packages/contracts/hash-node';
import type { ClockMapping, ControlAction } from '../../packages/contracts/generated';
import { mapClock, FakeScheduler, classifyClosedSequence } from '../../packages/audio/clock';
const fixture = (name: string): unknown => JSON.parse(fs.readFileSync(`fixtures/contracts/${name}.json`, 'utf8'));
const cases: {path: string;valid: boolean}[] = JSON.parse(fs.readFileSync('fixtures/manifest.json','utf8'));
for(const c of cases) test(c.path,()=> {
  const data: unknown=JSON.parse(fs.readFileSync(c.path,'utf8'));
  if(c.valid) assert.deepEqual(validate(data),data);
  else assert.throws(()=>validate(data));
});
test('nonfinite scores fail',()=> {
  const d=validate(fixture('BlinkCandidate'));
  assert.equal(d.kind,'BlinkCandidate');
  if(d.kind==='BlinkCandidate') { d.score=NaN; assert.throws(()=>validate(d)); }
});
test('clock and gesture boundary discipline',()=> {
  const m=validate(fixture('ClockMapping')) as ClockMapping;
  assert.ok(Math.abs(mapClock(m,10,'fixture-1')-20.01)<1e-9);
  assert.throws(()=>mapClock(m,10,'stale'));
  assert.throws(()=>mapClock(m,101,'fixture-1'));
  for(const count of [1,2,3]) assert.equal(classifyClosedSequence(count,'double_modulate_mvp',false),'pending');
  assert.equal(classifyClosedSequence(1),'none');
  assert.equal(classifyClosedSequence(2),'request_modulation');
  assert.equal(classifyClosedSequence(3),'none');
  assert.equal(classifyClosedSequence(3,'multi_count_expression_experiment'),'toggle_approved_expression_preset');
});
test('scheduler deduplicates sequence, preserves lanes and drops old epochs',()=> {
  const a=validate(fixture('ControlAction')) as ControlAction;
  const scheduler=new FakeScheduler();
  assert.equal(scheduler.submit(a,2,10),'queued');
  assert.equal(scheduler.queue[0].time_s,2.5);
  assert.deepEqual(scheduler.queue[0].lanes,a.before);
  assert.equal(scheduler.submit(a,2,10),'duplicate');
  assert.equal(scheduler.submit({...a,id:'other'},2,10),'duplicate');
  scheduler.reset('new',0);
  assert.deepEqual(scheduler.queue,[]);
  assert.equal(scheduler.submit(a,2,10),'stale_epoch');
  assert.equal(new FakeScheduler('fixture-1',9.99).submit(a,2,10),'expired_before_boundary');
});
test('content hashing is exact bytes',()=> {
  assert.equal(contentHash(Buffer.from('abc')),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  assert.notEqual(contentHash(Buffer.from('{}')),contentHash(Buffer.from('{} ')));
});

test('bundle rejects unknown references and catalogue versions',()=> {
  const names=['SceneManifest','ObjectState','InteractionEvent','BrushGroove','CompositionSpec','ArrangementPlan','ScoreEvent'];
  const records=validateBundle(names.map(fixture));
  const composition=records.find(r=>r.kind==='CompositionSpec')!;
  if(composition.kind==='CompositionSpec') composition.groove_version=99;
  assert.throws(()=>validateBundle(records));
});
