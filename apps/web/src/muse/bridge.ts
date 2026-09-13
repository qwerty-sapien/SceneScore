import type {ClockMapping} from '../../../../packages/contracts/generated';
import type {CheckpointCatalog} from './types';
import type {BridgeBatch,BridgeStatus,ClockProbe,MusicControlContext,MuseOperation,MuseScan} from './types';
const endpoint='http://127.0.0.1:8766/v1';
export const bridgeTimeouts={normal:3500,scan:15000,connect:25000,disconnect:8000} as const;
export class LocalMuseBridge {
 private session:string|null=null;
 private lifecycle=new AbortController();
 private operation:MuseOperation|null=null;
 private controlQueue:Promise<unknown>=Promise.resolve();
 initialCursor=0;
 constructor(private readonly fetcher:typeof fetch=globalThis.fetch.bind(globalThis)){}
 private async request(path:string,method='GET',body?:unknown,token?:string,signal?:AbortSignal,timeoutMs:number=bridgeTimeouts.normal){
  const lifecycle=this.lifecycle;
  const bounded=AbortSignal.any([lifecycle.signal,AbortSignal.timeout(timeoutMs),...(signal?[signal]:[])]);
  const response=await this.fetcher(endpoint+path,{method,headers:{Authorization:'Bearer '+(token??this.session??''),...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body),signal:bounded,cache:'no-store',credentials:'omit',redirect:'error'});
  if(lifecycle!==this.lifecycle||lifecycle.signal.aborted)throw Error('companion_session_changed');
  if(!response.ok){let message='companion_request_failed';try{const data=await response.json();if(typeof data.error==='string'&&/^[a-z][a-z0-9_]{0,95}$/.test(data.error))message=data.error;}catch{/* The body is optional; native exception text is never shown. */}throw Error(message);}
  const data=await response.json();
  if(lifecycle!==this.lifecycle||lifecycle.signal.aborted)throw Error('companion_session_changed');
  return data;
 }
 async connect(token:string):Promise<BridgeStatus>{
  if(!/^[A-Za-z0-9_-]{32,128}$/.test(token.trim()))throw Error('Paste the session token printed by the local companion.');
  this.close();this.lifecycle=new AbortController();
  const data=await this.request('/session','POST',{},token.trim());
  if(typeof data.session!=='string')throw Error('Invalid companion handshake');
  this.session=data.session;this.initialCursor=Number.isSafeInteger(data.cursor)?data.cursor:0;return data.status;
 }
 async status():Promise<BridgeStatus>{return this.request('/status');}
 async models():Promise<CheckpointCatalog>{return this.request('/models');}
 async selectModel(selection:string):Promise<CheckpointCatalog>{return this.request('/models/select','POST',{selection});}
 private controlRequest(path:'/arm'|'/disarm'):Promise<BridgeStatus>{
  const lifecycle=this.lifecycle;
  const pending=this.controlQueue.catch(()=>{}).then(()=>{
   if(lifecycle!==this.lifecycle||lifecycle.signal.aborted)throw Error('companion_session_changed');
   if(path==='/arm'&&this.operation)throw Error('muse_operation_in_progress');
   return this.request(path,'POST',{});
  });
  this.controlQueue=pending;return pending;
 }
 async arm():Promise<BridgeStatus>{return this.controlRequest('/arm');}
 async disarm():Promise<BridgeStatus>{return this.controlRequest('/disarm');}
 async events(cursor:number,signal:AbortSignal):Promise<BridgeBatch>{return this.request('/events?cursor='+cursor,'GET',undefined,undefined,signal);}
 async probe():Promise<ClockProbe>{return this.request('/clock','POST',{});}
 private async museRequest<T>(operation:MuseOperation,body:unknown):Promise<T>{
  if(!this.session)throw Error('companion_session_required');
  if(this.operation)throw Error('muse_operation_in_progress');
  this.operation=operation;const lifecycle=this.lifecycle;
  try{return await this.request('/muse/'+operation,'POST',body,undefined,undefined,bridgeTimeouts[operation]);}
  finally{if(lifecycle===this.lifecycle)this.operation=null;}
 }
 async scan():Promise<MuseScan>{
  const data=await this.museRequest<MuseScan>('scan',{});
  if(!Array.isArray(data.devices)||data.devices.length>64||data.devices.some(device=>!device||typeof device.id!=='string'||device.id.length<1||device.id.length>128||typeof device.name!=='string'||device.name.length>128||!/^Muse/i.test(device.name)))throw Error('invalid_muse_scan_response');
  return data;
 }
 async connectHeadset(deviceId:string):Promise<BridgeStatus>{
  if(typeof deviceId!=='string'||!deviceId.length||deviceId.length>128)throw Error('invalid_muse_device_id');
  return this.museRequest('connect',{device_id:deviceId});
 }
 async disconnectHeadset():Promise<BridgeStatus>{return this.museRequest('disconnect',{});}
 close(){this.lifecycle.abort();this.session=null;this.operation=null;}
}
export interface ClockProbeAnchor {probe:ClockProbe;audio_s:number;audio_epoch:string;uncertainty_s:number}
export function anchorFromProbe(probe:ClockProbe,before:MusicControlContext,after:MusicControlContext):ClockProbeAnchor {
 if(before.audio_epoch!==after.audio_epoch||after.audio_s<before.audio_s||after.audio_s-before.audio_s>.5)throw Error('Clock probe stale or transport changed; reconnect clocks.');
 if(!Number.isFinite(probe.device_s)||!Number.isFinite(probe.host_s)||!Number.isFinite(probe.uncertainty_s)||probe.uncertainty_s<0)throw Error('Invalid companion clock probe.');
 return {probe,audio_s:(before.audio_s+after.audio_s)/2,audio_epoch:after.audio_epoch,uncertainty_s:(after.audio_s-before.audio_s)/2+probe.uncertainty_s};
}
export function sameClockSource(a:ClockProbeAnchor,b:ClockProbeAnchor){return a.probe.device_epoch===b.probe.device_epoch&&a.probe.host_epoch===b.probe.host_epoch&&a.audio_epoch===b.audio_epoch&&a.probe.source_mode===b.probe.source_mode&&a.probe.config_hash===b.probe.config_hash;}
export function mappingFromProbe(probe:ClockProbe,before:MusicControlContext,after:MusicControlContext,previous?:ClockProbeAnchor):ClockMapping {
 const current=anchorFromProbe(probe,before,after);
 if(!previous)throw Error('clock_rate_calibration_pending');
 if(!sameClockSource(previous,current))throw Error('clock_source_changed_recalibration_required');
 const deviceDelta=probe.device_s-previous.probe.device_s,audioDelta=current.audio_s-previous.audio_s;
 if(deviceDelta<1||audioDelta<1)throw Error('clock_rate_calibration_pending');
 if(deviceDelta>30||audioDelta>30)throw Error('clock_anchors_stale');
 const rate=audioDelta/deviceDelta;
 if(!Number.isFinite(rate)||rate<.995||rate>1.005)throw Error('clock_rate_skew_outside_bound');
 const validity=2.5,uncertainty=current.uncertainty_s+(current.uncertainty_s+previous.uncertainty_s)/deviceDelta*validity;
 if(uncertainty>.02)throw Error('clock_uncertainty_exceeds_20ms');
 return {kind:'ClockMapping',schema_version:'0.1',id:crypto.randomUUID(),provenance:{source_mode:probe.source_mode,creator:'scenescore-local-clock-probe',tool_version:'muse-bridge-1',config_hash:probe.config_hash,input_hashes:[],seed:null},source_clock:'device',destination_clock:'audio',source_epoch:probe.device_epoch,destination_epoch:after.audio_epoch,source_anchor_s:probe.device_s,destination_anchor_s:current.audio_s,rate,uncertainty_s:uncertainty,valid_from_s:probe.device_s,valid_until_s:probe.device_s+validity};
}
