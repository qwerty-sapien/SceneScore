import {test} from 'node:test';
import assert from 'node:assert/strict';
import {traceLanes} from '../src/trace';
import type {Trace} from '../src/types';
const empty:Trace={channels:[{name:'AF7',unit:'uV'}],times_s:[],samples:[],device_epoch:'fixture',source_mode:'synthetic',quality:'unverified',prediction:null};
test('disconnected/empty input never creates synthetic traces',()=>{assert.equal(traceLanes(null).lanes.length,0);assert.equal(traceLanes(empty).lanes.length,0);});
test('display is bounded, large DC is centered without editing raw samples',()=>{
 const trace={...empty,times_s:Array.from({length:5000},(_,i)=>i/256),samples:Array.from({length:5000},(_,i)=>[10000+(i%400===200?20:0)])};const before=JSON.stringify(trace);const chart=traceLanes(trace);assert.ok(chart.points<=2048);assert.equal(chart.lanes[0].offset,10000);assert.equal(chart.lanes[0].scale,20);assert.ok(chart.lanes[0].path.includes(',12.88'));assert.equal(JSON.stringify(trace),before);
});
test('nonfinite samples break paths instead of drawing invented continuity',()=>{
 const trace={...empty,times_s:[0,.01,.02,.03,.04],samples:[[1],[2],[NaN],[3],[2]]};const lane=traceLanes(trace).lanes[0];assert.equal((lane.path.match(/M/g)??[]).length,2);assert.ok(!lane.path.includes('NaN'));
});
