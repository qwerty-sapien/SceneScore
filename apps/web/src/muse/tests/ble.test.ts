import {test} from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {LocalMuseBridge,bridgeTimeouts} from '../bridge';
import {MuseHeadset} from '../MuseHeadset';
import type {MuseHeadsetProps} from '../MuseHeadset';
import {conductingPresentation,detectorEligible,headsetProgress,museError,sameStream} from '../headset';
import type {BluetoothState,BridgeStatus} from '../types';

const ready:BridgeStatus={version:'muse-bridge-1',mode:'LIVE_MUSE',connected:true,hardware_verified:true,quality:'good',warmup_ready:true,armed:true,reason:'armed',model_version:'fixture',config_hash:'a'.repeat(64),source_available:true,recording:false,sample_count:4608,device_epoch:'device',host_epoch:'host',transport:'bleak',bluetooth_state:'streaming',ble_connected:true,device_name:'Muse-AD3C'};
const idle:BridgeStatus={...ready,connected:false,hardware_verified:false,quality:'unverified',warmup_ready:false,armed:false,source_available:false,sample_count:0,bluetooth_state:'idle',ble_connected:false,device_name:null,reason:'waiting_for_source_samples'};
const props:MuseHeadsetProps={status:idle,companionConnected:true,devices:[],selected:'',scanned:false,operation:null,onScan:()=>{},onSelect:()=>{},onConnect:()=>{},onDisconnect:()=>{}};
const render=(patch:Partial<MuseHeadsetProps>={})=>renderToStaticMarkup(React.createElement(MuseHeadset,{...props,...patch}));
const response=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
const handshake={session:'session-fixture',cursor:3,status:idle};
const device={id:'opaque-scan-device',name:'Muse-AD3C'};

test('scan UI needs an authenticated direct-BLE companion and supports empty scans',()=>{
 assert.match(render(),/<button>Scan for Muse<\/button>/);
 assert.match(render({companionConnected:false}),/disabled="">Scan for Muse/);
 assert.match(render({status:{...idle,transport:'lsl'}}),/make muse-live/);
 assert.match(render({scanned:true}),/No advertising Muse headset found/);
 assert.match(render({scanned:true}),/>Rescan<\/button>/);
 assert.match(render(),/Companion connected/);
});

test('discovered device selection enables connect, not a raw identifier field',()=>{
 const html=render({devices:[device],selected:device.id,scanned:true});
 assert.match(html,/aria-label="Discovered Muse"/);
 assert.match(html,/<option value="opaque-scan-device" selected="">Muse-AD3C/);
 assert.match(html,/<button>Connect headset<\/button>/);
 assert.match(render({devices:[device],selected:'unknown'}),/disabled="">Connect headset/);
 assert.match(render({status:ready,devices:[device],selected:device.id}),/disabled="">Connect headset/);
 assert.match(render({status:ready}),/<button>Disconnect headset<\/button>/);
});

test('connection stages distinguish GATT connectivity from valid EEG and arm state',()=>{
 const stages:Partial<Record<BluetoothState,string>>={scanning:'Scanning…',connecting:'Connecting…',gatt_verifying:'Verifying Muse GATT…',configuring:'Configuring Muse EEG…',subscribing:'Subscribing to EEG…',starting_stream:'Starting EEG…'};
 for(const [stage,label] of Object.entries(stages)){
  const status={...idle,bluetooth_state:stage as BluetoothState,ble_connected:stage!=='scanning'&&stage!=='connecting'};
  const html=render({status,operation:stage==='scanning'?'scan':'connect'});
  assert.ok(html.includes(label),stage);assert.match(html,/disabled="">Connect headset/);
  assert.match(html,/Waiting for verified samples/);assert.doesNotMatch(html,/EEG streaming|Live stream · armed/);
 }
 assert.match(render({status:{...ready,armed:false}}),/Streaming · 4,608 samples/);
 assert.match(render({status:{...ready,armed:false}}),/BLE connected/);
});

test('safe failures explain Bluetooth off, permission, expired discovery, and disconnect stages',()=>{
 const cases=[['bluetooth_powered_off','Bluetooth is off on this computer.'],['bluetooth_permission_denied','Bluetooth permission is unavailable for the local Python process.'],['connect_timeout','Muse connection timed out.'],['unexpected_disconnect_reconnect_required','Muse disconnected. Detector disarmed; reconnect required.']];
 for(const [error,message] of cases)assert.ok(render({status:{...idle,bluetooth_state:'error',last_error:error,disconnect_stage:'subscribing'}}).includes(message));
 assert.match(render({status:{...idle,reconnect_required:true,disconnect_stage:'starting_stream',last_operation:'start'}}),/Disconnect stage: starting_stream · Last operation: start/);
 assert.match(museError('scan_result_expired'),/Rescan/);
 for(const [code,message] of [
  ['operation_in_progress','Wait for it to finish'],
  ['unknown_device_id','current scan'],
  ['invalid_device_id','selection is invalid'],
  ['stream_timeout_reconnect_required','stopped sending EEG samples'],
  ['bluetooth_unavailable','Bluetooth is unavailable to the local companion'],
  ['malformed_eeg_packet','waiting for a continuous valid stream'],
 ])assert.ok(museError(code).includes(message),code);
 assert.doesNotMatch(museError('malformed_eeg_packet'),/reconnect required/);
 assert.doesNotMatch(museError(new Error('Native traceback containing private values')),/Native traceback|private values/);
 assert.match(museError(new DOMException('timed out','TimeoutError')),/timed out/);
});

test('missing profile, warmup, quality failure and every gate suppress arming',()=>{
 assert.match(render({status:{...ready,armed:false,quality:'unverified',reason:'calibrated_quality_profile_missing'}}),/Quality profile missing · detector remains disarmed/);
 assert.match(render({status:{...ready,armed:false,warmup_ready:false}}),/Warming up on source samples/);
 for(const patch of [{connected:false},{hardware_verified:false},{quality:'unverified' as const},{quality:'bad' as const},{warmup_ready:false},{source_available:false},{reconnect_required:true}]){
  assert.equal(detectorEligible({...ready,...patch}),false);
  assert.doesNotMatch(render({status:{...ready,...patch}}),/<dd>Armed<\/dd>/);
 }
 assert.equal(detectorEligible(ready),true);
 assert.equal(detectorEligible({...ready,mode:'SYNTHETIC_TEST',hardware_verified:false}),true);
});

test('BLE clock caution identifies the uncalibrated allowance without claiming measured latency',()=>{
 const html=render({status:ready});
 assert.match(html,/uncalibrated one-way delay allowance of at least 25 ms/);
 assert.match(html,/This is not a latency measurement/);
 assert.match(html,/conducting limit remains 20 ms/);
 assert.match(html,/clock uncertainty can block blink controls even when signal quality and warmup pass/);
 assert.doesNotMatch(render({status:{...ready,transport:'lsl'}}),/uncalibrated one-way delay allowance/);
});

test('LIVE_MUSE selection remains visible with keyboard fallback and never claims a false live stream',()=>{
 for(const status of [null,idle,{...ready,quality:'unverified' as const},{...ready,armed:false},{...ready,reconnect_required:true}]){
  const view=conductingPresentation('LIVE_MUSE',status,null);
  assert.equal(view.title,'LIVE_MUSE');assert.equal(view.active,'KEYBOARD');assert.equal(view.subtitle,'Live Muse selected · detector disarmed');
 }
 assert.equal(conductingPresentation('LIVE_MUSE',ready,'disconnect').active,'KEYBOARD');
 assert.equal(conductingPresentation('LIVE_MUSE',ready,null).subtitle,'Live stream · armed');
 assert.equal(conductingPresentation('KEYBOARD',ready,null).active,'KEYBOARD');
 assert.equal(conductingPresentation('SYNTHETIC_TEST',null,null).active,'SYNTHETIC_TEST');
 assert.equal(sameStream(ready,{...ready,device_epoch:'reconnected'}),false);
 assert.equal(sameStream(ready,{...ready,host_epoch:'new-host'}),false);
 assert.equal(sameStream(ready,{...ready,config_hash:'b'.repeat(64)}),false);
 assert.equal(sameStream(ready,{...ready,sample_count:5000}),true);
 assert.equal(headsetProgress(idle,'scan'),'Scanning…');
});

test('client uses narrow authenticated requests and individual deadlines; poll stays available during scan',async()=>{
 const calls:{url:string;init:RequestInit|undefined}[]=[];
 const timeouts:number[]=[];const originalTimeout=AbortSignal.timeout;
 let finishScan:(value:Response)=>void=()=>{};
 const scanResult=new Promise<Response>(resolve=>{finishScan=resolve;});
 try{
  AbortSignal.timeout=(ms:number)=>{timeouts.push(ms);return originalTimeout(ms);};
  const bridge=new LocalMuseBridge(async(input,init)=>{
   const url=String(input);calls.push({url,init});
   if(url.endsWith('/session'))return response(handshake);
   if(url.endsWith('/scan'))return scanResult;
   if(url.includes('/events'))return response({cursor:3,events:[],status:idle,overflow:false});
   return response(ready);
  });
  await bridge.connect('a'.repeat(43));const scan=bridge.scan();
  await assert.rejects(bridge.connectHeadset(device.id),/muse_operation_in_progress/);
  await assert.rejects(bridge.arm(),/muse_operation_in_progress/);
  await bridge.events(3,new AbortController().signal);
  finishScan(response({devices:[device],status:idle}));assert.deepEqual((await scan).devices,[device]);
  await bridge.connectHeadset(device.id);await bridge.disconnectHeadset();await bridge.status();bridge.close();
  assert.deepEqual(timeouts,[3500,15000,3500,25000,8000,3500]);
  assert.deepEqual(bridgeTimeouts,{normal:3500,scan:15000,connect:25000,disconnect:8000});
  for(const {init} of calls){assert.equal(init?.cache,'no-store');assert.equal(init?.credentials,'omit');assert.equal(init?.redirect,'error');assert.ok(init?.signal);}
  const connectCall=calls.find(call=>call.url.endsWith('/muse/connect'))!;
  assert.equal(connectCall.init?.body,JSON.stringify({device_id:device.id}));
  assert.equal((connectCall.init?.headers as Record<string,string>).Authorization,'Bearer session-fixture');
  assert.equal(calls.find(call=>call.url.endsWith('/scan'))?.init?.body,'{}');
  assert.equal(calls.find(call=>call.url.endsWith('/disconnect'))?.init?.body,'{}');
 }finally{AbortSignal.timeout=originalTimeout;}
});

test('closed or superseded companion sessions reject late operations even when a fetcher ignores abort',async()=>{
 let finish:(value:Response)=>void=()=>{};
 const late=new Promise<Response>(resolve=>{finish=resolve;});
 let handshakes=0;
 const bridge=new LocalMuseBridge(async input=>String(input).endsWith('/session')?response({...handshake,session:'session-'+(++handshakes)}):late);
 await bridge.connect('a'.repeat(43));const scan=bridge.scan();
 await bridge.connect('b'.repeat(43));finish(response({devices:[device]}));
 await assert.rejects(scan,/companion_session_changed/);
 bridge.close();await assert.rejects(bridge.scan(),/companion_session_required/);
});

test('arm/disarm serialize so a delayed arm cannot override a newer disarm',async()=>{
 const paths:string[]=[];let finish:(value:Response)=>void=()=>{};
 const pending=new Promise<Response>(resolve=>{finish=resolve;});
 const bridge=new LocalMuseBridge(async input=>{const path=String(input).split('/v1')[1];paths.push(path);if(path==='/session')return response(handshake);if(path==='/arm')return pending;return response({...ready,armed:false});});
 await bridge.connect('a'.repeat(43));const arm=bridge.arm();await Promise.resolve();const disarm=bridge.disarm();
 assert.ok(!paths.includes('/disarm'));finish(response(ready));await arm;assert.equal((await disarm).armed,false);
 assert.deepEqual(paths,['/session','/arm','/disarm']);bridge.close();
});

test('client refuses invalid discovery and uses safe error codes without native error traces',async()=>{
 const bodies=[{devices:[{id:'x',name:'Unrelated device'}]},{error:'bluetooth_powered_off'},{error:'native trace with sensitive values'}];
 let index=0;
 const bridge=new LocalMuseBridge(async input=>String(input).endsWith('/session')?response(handshake):response(bodies[index],index++?500:200));
 await bridge.connect('a'.repeat(43));
 await assert.rejects(bridge.scan(),/invalid_muse_scan_response/);
 await assert.rejects(bridge.scan(),/bluetooth_powered_off/);
 await assert.rejects(bridge.scan(),error=>error instanceof Error&&error.message==='companion_request_failed');
 await assert.rejects(bridge.connectHeadset('x'.repeat(129)),/invalid_muse_device_id/);bridge.close();
});
