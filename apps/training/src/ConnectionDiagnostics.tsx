import React,{useEffect,useRef,useState} from 'react';
import type {TrainingAPI} from './api';
import type {DiagnosticsReport,Source} from './types';

export const stateLabel={pass:'Working',warning:'Check',blocked:'Blocked',unknown:'Unverified'};
export function primaryFinding(report:DiagnosticsReport|null,available:boolean){
 if(!available)return 'Connect the local service to inspect the connection.';
 if(!report)return 'Checking Bluetooth and stream metadata…';
 if(report.source_mode==='synthetic')return 'Synthetic rehearsal is active. Hardware checks below remain separate.';
 const samples=report.stages.find(s=>s.id==='samples'),signal=report.stages.find(s=>s.id==='signal');
 if(samples?.state==='pass')return signal?.state==='warning'?signal.detail:'Fresh samples are reaching the page. Electrode contact still needs inspection.';
 const failure=report.stages.find(s=>s.state==='blocked');
 return failure?failure.detail:'Follow the connection stages below; no working EEG stream is established yet.';
}

export function ConnectionDiagnostics({api,authenticated,serviceAvailable,onSources}:{api:TrainingAPI;authenticated:boolean;serviceAvailable:boolean;onSources:(sources:Source[])=>void}){
 const [report,setReport]=useState<DiagnosticsReport|null>(null),[automatic,setAutomatic]=useState(true),[error,setError]=useState(''),[busy,setBusy]=useState(false),[received,setReceived]=useState(0);
 const generation=useRef(0);
 useEffect(()=>{
  if(!authenticated)return;
  let active=true,timer=0;const controller=new AbortController();
  const accept=(next:DiagnosticsReport)=>{if(active){setReport(next);setReceived(Date.now());onSources(next.discovery.sources);setError('');}};
  async function poll(){try{accept(await api.diagnostics(AbortSignal.any([controller.signal,AbortSignal.timeout(4000)])));}catch(e){if(active)setError(e instanceof Error?e.message:String(e));}finally{if(active)timer=window.setTimeout(()=>void poll(),1000);}}
  void api.monitorDiagnostics(automatic).then(accept).catch(e=>{if(active)setError(String(e));}).finally(()=>{if(active)void poll();});
  return()=>{active=false;controller.abort();window.clearTimeout(timer);};
 },[api,authenticated,automatic,onSources]);
 async function check(permission=false){const current=++generation.current;setBusy(true);try{const next=await api.checkDiagnostics(permission);if(current===generation.current){setReport(next);setAutomatic(true);setError('');}}catch(e){setError(String(e));}finally{setBusy(false);}}
 function download(){if(!report)return;const blob=new Blob([JSON.stringify({...report,exported_at:new Date().toISOString(),contains_raw_samples:false},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='muse-connection-diagnostics.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 const stale=!serviceAvailable||!!error||Date.now()-received>5000;
 const valid=stale?null:report;
 return <section className="connection-diagnostics" aria-label="Connection diagnostics">
  <div className="diagnostics-heading"><div><h2>Connection diagnostics</h2><p>{primaryFinding(valid,serviceAvailable)}</p></div>
   <label className="check"><input type="checkbox" aria-label="Automatic connection checks" checked={automatic} disabled={!authenticated} onChange={e=>setAutomatic(e.target.checked)}/><span>Automatic checks</span></label>
   <button disabled={!authenticated||busy} onClick={()=>void check()}>Check now</button></div>
  <div className="diagnostics-clock">{!authenticated?'Local service required':error?'Diagnostics unavailable · '+error:report?.checking?'Checking hardware and stream metadata…':!automatic?'Hardware discovery paused':report?.checked_at?'Hardware checked '+new Date(report.checked_at).toLocaleTimeString()+' · every 10 s':'First hardware check pending'}<span>Sample health updates every second · no automatic recording</span></div>
  {valid?<ol className="diagnostic-stages">{valid.stages.map((s,i)=><li key={s.id} data-state={s.state}><span className="stage-number">{i+1}</span><div><strong>{s.label}</strong><p>{s.detail}</p>{s.action&&<small>{s.action}</small>}</div><span className="stage-state">{stateLabel[s.state]}</span></li>)}</ol>:<p className="diagnostics-empty">Live evidence appears here after the local service connects. Previously checked hardware is never shown as current while the service is unavailable.</p>}
  {valid?.signal.channels.length? <div className="diagnostics-signal"><span>Latest batch: {valid.signal.age_s===null?'unavailable':(valid.signal.age_s*1000).toFixed(0)+' ms ago'}</span><span>Observed: {valid.signal.rate_hz?.toFixed(1)??'—'} Hz</span><span>Gaps / 2 s: {valid.signal.gaps}</span>{valid.signal.channels.map(c=><span key={c.name}>{c.name}: {c.peak_to_peak.toFixed(2)} {c.unit} peak-to-peak{c.flat?' · constant':''}</span>)}</div>:null}
  <div className="diagnostics-actions"><button disabled={!authenticated||busy} onClick={()=>void check(true)}>Enable Bluetooth check</button><button disabled={!valid} onClick={download}>Download diagnostic report</button><span>Bluetooth checks observe the Muse service only. They do not pair, connect, or collect EEG.</span></div>
  <details><summary>Connection history and configuration</summary>
   <p>Transport: LSL. Board ID: unused. Units: read from each stream; frontal channels require µV. The three MUSE_ placeholders in .env are unused by this trainer.</p>
   <p>Sensor contact and blink-detection accuracy cannot be established from Bluetooth or a changing waveform alone.</p>
   {valid?.events.length?<ol className="diagnostics-events">{valid.events.map((e,i)=><li key={e.at+e.stage+i}><time>{new Date(e.at).toLocaleTimeString()}</time><strong>{e.stage} · {stateLabel[e.state]}</strong><span>{e.detail}</span></li>)}</ol>:null}
  </details>
 </section>;
}
