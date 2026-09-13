import React from 'react';
import type {BridgeStatus,MuseDevice,MuseOperation} from './types';
import {detectorEligible,headsetBusy,headsetProgress,qualityExplanation} from './headset';

export interface MuseHeadsetProps {
 status:BridgeStatus|null;companionConnected:boolean;devices:MuseDevice[];selected:string;scanned:boolean;operation:MuseOperation|null;
 onScan:()=>void;onSelect:(id:string)=>void;onConnect:()=>void;onDisconnect:()=>void;
}
export function MuseHeadset(props:MuseHeadsetProps){
 const {status,operation}=props,busy=headsetBusy(status,operation);
 const available=props.companionConnected&&status?.mode==='LIVE_MUSE'&&status.transport==='bleak';
 const connected=!!status?.ble_connected||!!status?.connected;
 return <div className="muse-headset" aria-label="Direct Muse Bluetooth connection">
  <div className="muse-headset-heading"><h3>Connect your Muse</h3><span>Local Bluetooth · EEG stays on this computer</span></div>
  {!props.companionConnected?<p>Connect the local companion below to scan for your headset.</p>:!available?<p>Start the local companion with <code>make muse-live</code>, then reconnect it here to use direct Bluetooth.</p>:null}
  <div className="muse-control-row">
   <button onClick={props.onScan} disabled={!available||busy||connected}>{operation==='scan'?'Scanning…':props.scanned?'Rescan':'Scan for Muse'}</button>
   {props.devices.length>0&&<label>Discovered Muse<select aria-label="Discovered Muse" value={props.selected} onChange={event=>props.onSelect(event.target.value)} disabled={busy||connected}><option value="">Choose a headset</option>{props.devices.map(device=><option key={device.id} value={device.id}>{device.name}</option>)}</select></label>}
   <button onClick={props.onConnect} disabled={!available||busy||connected||!props.devices.some(device=>device.id===props.selected)}>Connect headset</button>
   <button onClick={props.onDisconnect} disabled={!available||busy||!connected}>Disconnect headset</button>
  </div>
  <p className="muse-headset-progress" role="status" aria-live="polite">{headsetProgress(status,operation)}</p>
  {props.scanned&&!props.devices.length&&!busy&&<p role="status">No advertising Muse headset found.</p>}
  {props.devices.length>0&&!connected&&<p>{props.devices.find(device=>device.id===props.selected)?.name??`${props.devices.length} Muse headset(s)`} found</p>}
  <dl className="muse-status">
   <dt>Companion</dt><dd>{props.companionConnected?'Companion connected':'Not connected'}</dd>
   <dt>Headset</dt><dd>{status?.device_name??'No headset connected'}</dd>
   <dt>Bluetooth</dt><dd>{status?.ble_connected?'BLE connected':'Not connected'}</dd>
   <dt>EEG stream</dt><dd>{status?.connected&&status.hardware_verified?`EEG streaming · ${status.sample_count.toLocaleString('en-US')} samples`:'Waiting for verified samples'}</dd>
   <dt>Signal quality</dt><dd>{status?.quality??'unverified'}</dd>
   <dt>Warmup</dt><dd>{status?.warmup_ready?'Complete':status?.connected?'Warming up on source samples':'Waiting for source samples'}</dd>
   <dt>Detector</dt><dd>{status?.armed&&detectorEligible(status)&&!busy?'Armed':'Disarmed'}</dd>
  </dl>
  <p className="muse-hint">{qualityExplanation(status)}</p>
  {status?.transport==='bleak'&&<p className="muse-hint">Clock timing: the BLE estimator includes an uncalibrated one-way delay allowance of at least 25 ms. This is not a latency measurement. The conducting limit remains 20 ms, so clock uncertainty can block blink controls even when signal quality and warmup pass.</p>}
  {status?.disconnect_stage&&<p className="muse-hint">Disconnect stage: {status.disconnect_stage}{status.last_operation?` · Last operation: ${status.last_operation}`:''}</p>}
  <p className="muse-hint">Power on the headset and disconnect other Muse apps before scanning. Music, keyboard controls and simulation remain available.</p>
 </div>;
}
