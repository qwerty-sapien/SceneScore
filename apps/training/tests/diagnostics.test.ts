import test from 'node:test';
import assert from 'node:assert/strict';
import {primaryFinding} from '../src/ConnectionDiagnostics';
import type {DiagnosticsReport} from '../src/types';

function report(source_mode:DiagnosticsReport['source_mode'],samples:'pass'|'blocked'):DiagnosticsReport {
 return {source_mode,stages:[{id:'bluetooth',label:'Bluetooth',state:'blocked',detail:'Permission denied',action:'Check permission'},
 {id:'samples',label:'Samples',state:samples,detail:'Sample evidence',action:''}]} as DiagnosticsReport;
}
test('off-line service never shows cached successful hardware as live',()=>{
 assert.match(primaryFinding(report('real_device','pass'),false),/Connect the local service/);
});
test('fresh raw samples remain usable when separate Bluetooth inspection lacks permission',()=>{
 assert.match(primaryFinding(report('real_device','pass'),true),/Fresh samples/);
 assert.match(primaryFinding(report('real_device','blocked'),true),/Permission denied/);
});
test('synthetic diagnostics stay visibly separate from hardware evidence',()=>{
 assert.match(primaryFinding(report('synthetic','pass'),true),/Synthetic rehearsal/);
});

import {sourceLabel} from '../src/interaction';
test('connected inlet is not labelled live EEG until a fresh batch arrives',()=>{
 assert.equal(sourceLabel('real_device',true,null),'WAITING FOR EEG');
 assert.equal(sourceLabel('real_device',true,1),'EEG STALLED');
 assert.equal(sourceLabel('real_device',true,.1),'LIVE EEG');
});
