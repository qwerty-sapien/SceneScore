import {test} from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {TapLabelController,progressText} from '../src/automatic';
import {TrainingView} from '../src/TrainingView';
import {TrainingAPI} from '../src/api';
import type {AutomaticStatus} from '../src/types';

const status:AutomaticStatus={phase:'learning',active:true,message:'Learning',run_id:'one',source_mode:'synthetic',elapsed_s:65,limit_s:600,labels:5,usable_positive_windows:4,background_windows:20,checkpoint_id:null,training_steps:0,evaluation:null,target:.93,target_advisory:true};
test('one keydown is one persisted label; repeat, held key and modifiers are ignored',async()=>{
 const sent:any[]=[],acks:number[]=[];let time=0;
 const controller=new TapLabelController(async value=>sent.push(value),()=>acks.push(sent.length),error=>assert.fail(String(error)),()=>++time,()=>String(time));
 const event={code:'KeyB',repeat:false,target:null};
 assert.equal(controller.down(event,status),true);
 assert.equal(controller.down({...event,repeat:true},status),false);
 assert.equal(controller.down(event,status),false);
 assert.equal(acks.length,0);
 await controller.flush();assert.equal(acks.length,1);assert.equal(sent[0].run_id,'one');
 controller.up('KeyB');assert.equal(controller.down({...event,metaKey:true},status),false);
 assert.equal(controller.down(event,{...status,phase:'stopped',active:false}),false);
 controller.release();controller.down(event,status);await controller.flush();assert.equal(sent.length,2);
});
test('failed delivery never acknowledges a label and queue can recover',async()=>{
 let calls=0,ack=0,fail=0;const controller=new TapLabelController(async()=>{if(++calls===1)throw Error('fixture disconnected');},()=>ack++,()=>fail++);
 controller.down({code:'KeyB',repeat:false,target:null},status);await controller.flush();assert.equal(ack,0);assert.equal(fail,1);
 controller.release();controller.down({code:'KeyB',repeat:false,target:null},status);await controller.flush();assert.equal(ack,1);
});
test('only Train/Stop and concise notices appear; no controls to configure',()=>{
 for(const active of [false,true]){const html=renderToStaticMarkup(React.createElement(TrainingView,{active,busy:false,text:'Model saved',error:false,labelSaved:false,onAction:()=>{}}));
 assert.equal((html.match(/<button/g)||[]).length,1);assert.ok(html.includes(active?'>Stop<':'>Train<'));assert.ok(!/<(input|select|textarea|canvas|svg)/.test(html));assert.ok(html.includes('within 1 second after the second blink'));}
});
test('absence of evaluation is never 0%, incomplete estimates and synthetic mode remain visible',()=>{
 const noCheck=progressText({...status,checkpoint_id:'saved'});assert.ok(noCheck.includes('Not yet evaluated'));assert.ok(!noCheck.includes('0%'));assert.ok(noCheck.includes('Synthetic rehearsal'));
 const below=progressText({...status,evaluation:{precision:.8,recall:.7,complete:false,target_reached:false,labels:30,monitored_s:100,background_s:40,availability:1}});assert.ok(below.includes('80.0%'));assert.ok(below.includes('incomplete'));
});
test('automatic consent only goes with Train; server owns source, budgets and labels',async()=>{
 const sent:any[]=[];const api=new TrainingAPI(async(url,options)=>{sent.push({url:String(url),body:options?.body?JSON.parse(String(options.body)):null});return new Response(JSON.stringify(String(url).endsWith('/session')?{session:'token',status:{}}:status));});
 await api.authenticate('startup-token-abcdefghijkl');await api.automaticStatus();await api.startAutomatic();await api.labelAutomatic({id:'tap',client_ms:1,run_id:'one'});await api.stopAutomatic();
 assert.equal(sent[1].body,null);assert.deepEqual(sent[2].body,{consent:true});assert.deepEqual(sent[3].body,{id:'tap',client_ms:1,run_id:'one'});assert.deepEqual(sent[4].body,{});
});
test('connection and EEG check precede the Train button without adding dashboard controls',()=>{
 for(const [step,button] of [[1,'Connect headset'],[2,'Cancel'],[3,'Train']] as const){
  const html=renderToStaticMarkup(React.createElement(TrainingView,{active:false,busy:false,text:'Local fixture',error:false,labelSaved:false,onAction:()=>{},step,button}));
  assert.equal((html.match(/<button/g)||[]).length,1);assert.ok(html.includes('>'+button+'<'));
  assert.ok(!/<(input|select|textarea|canvas)/.test(html));
  if(step===3)assert.ok(html.includes('within 1 second after the second blink'));
 }
});
