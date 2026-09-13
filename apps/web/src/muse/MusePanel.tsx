import {CheckpointControls,evaluationText} from './CheckpointControls';
import React,{useEffect,useRef,useState} from 'react';
import type {ClockMapping} from '../../../../packages/contracts/generated';
import {LocalMuseBridge,anchorFromProbe,mappingFromProbe,sameClockSource} from './bridge';
import type {ClockProbeAnchor} from './bridge';
import {delayedFeedback,feedbackKinds,safeReadNotes,saveNotes} from './state';
import type {Cue,Feedback} from './state';
import type {BridgeEvent,BridgeStatus,MuseControlEnvelope,MuseDevice,MuseMode,MuseOperation,MusePanelProps} from './types';
import {MuseHeadset} from './MuseHeadset';
import {conductingPresentation,detectorEligible,headsetBusy,museError,sameStream} from './headset';
import './muse.css';
export type {MuseControlEnvelope,MusicControlContext,MuseDecision,MusePanelProps} from './types';
const labels:Record<MuseMode,string>={KEYBOARD:'Keyboard · permanent fallback',SYNTHETIC_TEST:'Simulated · software fixture',REAL_REPLAY:'Real replay · local recording',LIVE_MUSE:'Live Muse · verified stream required'};
const cueInstructions=['Remain at rest; blink naturally.','When comfortable, deliberately double blink once.','Talk or look around; blink naturally.','After this session, remove and refit the headset before a new session.'];
export function MusePanel(props:MusePanelProps){
 const [requested,setRequested]=useState<MuseMode>('KEYBOARD'),[status,setStatus]=useState<BridgeStatus|null>(null),[token,setToken]=useState(''),[connection,setConnection]=useState(0),[busy,setBusy]=useState(false),[notice,setNotice]=useState('Keyboard and simulation are ready. The local companion is optional.'),[diagnostics,setDiagnostics]=useState<string[]>([]),[lastEnvelope,setLastEnvelope]=useState<MuseControlEnvelope|null>(null),[cue,setCue]=useState<Cue|null>(null),[notes,setNotes]=useState<Feedback[]>(safeReadNotes),[now,setNow]=useState(Date.now()),[session,setSession]=useState<{id:string;split:string}|null>(null),[split,setSplit]=useState('train'),[consent,setConsent]=useState(false),[cueIndex,setCueIndex]=useState(0);
 const [devices,setDevices]=useState<MuseDevice[]>([]),[selected,setSelected]=useState(''),[scanned,setScanned]=useState(false),[operation,setOperation]=useState<MuseOperation|null>(null);
 const statusRef=useRef<BridgeStatus|null>(null),operationRef=useRef<MuseOperation|null>(null),controlRevision=useRef(0),companionRevision=useRef(0),retiredStreams=useRef(new Set<string>()),actionRevision=useRef(0),disarming=useRef(false);
 const client=useRef<LocalMuseBridge|null>(null),mapping=useRef<ClockMapping|null>(null),propsRef=useRef(props),requestedRef=useRef(requested),pollCursor=useRef(0),clockBusy=useRef(false),clockAnchors=useRef<ClockProbeAnchor[]>([]);
 propsRef.current=props;requestedRef.current=requested;
 const presentation=conductingPresentation(requested,status,operation),actual=presentation.active;
 const streamKey=(value:BridgeStatus)=>[value.mode,value.device_epoch,value.host_epoch,value.config_hash].join('|');
 function clearClocks(){controlRevision.current++;mapping.current=null;clockAnchors.current=[];}
 function applyStatus(next:BridgeStatus):boolean {
  if(retiredStreams.current.has(streamKey(next)))return false;
  const previous=statusRef.current;
  if(previous&&!sameStream(previous,next)){retiredStreams.current.add(streamKey(previous));clearClocks();}
  if(!detectorEligible(next)||headsetBusy(next,operationRef.current))clearClocks();
  const safe=disarming.current?{...next,armed:false}:next;statusRef.current=safe;setStatus(safe);return true;
 }
 function loseCompanion(){
  companionRevision.current++;actionRevision.current++;client.current?.close();client.current=null;statusRef.current=null;setStatus(null);setConnection(0);clearClocks();
  operationRef.current=null;setOperation(null);disarming.current=false;setBusy(false);setDevices([]);setSelected('');setScanned(false);
 }
 const addDiagnostic=(message:string)=>setDiagnostics(items=>[message,...items].slice(0,20));
 function submit(envelope:MuseControlEnvelope){const result=propsRef.current.onEnvelope(envelope);const complete={...envelope,timing:{...envelope.timing,t4_received_s:result.t4_received_s??null,t5_ack_onset_s:result.t5_ack_onset_s??null,t6_boundary_s:result.t6_boundary_s??null}};setLastEnvelope(complete);addDiagnostic(result.status+(result.reason?' · '+result.reason:''));setNotice(result.status==='queued'?'Accepted control queued through the music transport. Arrival follows its musical boundary.':result.reason??result.status);}
 async function synchronize(){
  const existing=client.current,source=statusRef.current,revision=controlRevision.current;
  if(clockBusy.current||!existing||!detectorEligible(source)||headsetBusy(source,operationRef.current))return;
  const before=propsRef.current.getMusicContext();if(!before){clearClocks();return;}
  clockBusy.current=true;
  try{
   const probe=await existing.probe();
   if(existing!==client.current||revision!==controlRevision.current||!sameStream(source,statusRef.current))return;
   if(probe.device_epoch!==source!.device_epoch||probe.host_epoch!==source!.host_epoch||probe.config_hash!==source!.config_hash)throw Error('clock_source_changed_recalibration_required');
   const after=propsRef.current.getMusicContext();if(!after)throw Error('Audio transport unavailable');
   const anchor=anchorFromProbe(probe,before,after);
   clockAnchors.current=clockAnchors.current.filter(prior=>sameClockSource(prior,anchor)&&anchor.probe.device_s-prior.probe.device_s<=30);
   const previous=clockAnchors.current[0];clockAnchors.current=[...clockAnchors.current,anchor].slice(-16);
   mapping.current=mappingFromProbe(probe,before,after,previous);
  }catch(error){
   if(existing!==client.current||revision!==controlRevision.current)return;
   mapping.current=null;const reason=String(error);if(reason.includes('source_changed')||reason.includes('transport changed'))clockAnchors.current=[];
   addDiagnostic('Clock mapping unavailable · '+reason);
  }finally{clockBusy.current=false;}
 }
 function receive(event:BridgeEvent){
  if(event.kind!=='gesture'){addDiagnostic(event.kind+' · '+(event.reason??('candidate_id'in event?event.candidate_id:'stream update')));return;}
  const current=statusRef.current;
  if(disarming.current||!detectorEligible(current)||!current?.armed||headsetBusy(current,operationRef.current)||event.host_epoch!==current.host_epoch){addDiagnostic('suppressed · stream_gate_changed_before_dispatch');return;}
  const gesture=event.gesture;addDiagnostic('Accepted double · '+gesture.id);
  const expected=gesture.provenance.source_mode==='real_device'?'LIVE_MUSE':gesture.provenance.source_mode==='replay'?'REAL_REPLAY':'SYNTHETIC_TEST';
  if(requestedRef.current!==expected){addDiagnostic('suppressed · selected_source_mismatch');return;}
  const map=mapping.current;
  if(!map||map.source_epoch!==gesture.decision.epoch||gesture.decision.seconds<map.valid_from_s||gesture.decision.seconds>map.valid_until_s){addDiagnostic('suppressed · unmapped_or_stale_clock');return;}
  const request=map.destination_anchor_s+(gesture.decision.seconds-map.source_anchor_s)*map.rate;
  const context=propsRef.current.getMusicContext(request);if(!context){addDiagnostic('suppressed · audio_transport_unavailable');return;}
  try{submit(propsRef.current.createFromGesture(gesture,map,event.host_dispatch_s,event.host_epoch,context));}catch(error){addDiagnostic('suppressed · '+String(error));}
 }
 useEffect(()=>{const timer=window.setInterval(()=>setNow(Date.now()),250);return()=>window.clearInterval(timer);},[]);
 useEffect(()=>{
  const existing=client.current;if(!connection||!existing)return;
  const abort=new AbortController();let active=true;
  const syncTimer=window.setInterval(()=>void synchronize(),2000);void synchronize();
  void(async()=>{while(active&&existing===client.current){
   try{
    const batch=await existing.events(pollCursor.current,abort.signal);
    if(!active||existing!==client.current)break;
    pollCursor.current=batch.cursor;if(!applyStatus(batch.status))continue;
    if(batch.overflow){clearClocks();addDiagnostic('Event buffer overflow · controls disarmed; reconnect and re-arm.');setNotice('Companion event buffer overflow. Reconnect before conducting.');loseCompanion();break;}
    for(const event of batch.events)receive(event);
   }catch{
    if(!active||existing!==client.current)break;
    loseCompanion();
    setNotice('Companion unavailable. Keyboard and simulation remain ready. Reconnect the local companion to continue.');break;
   }
  }})();
  return()=>{active=false;abort.abort();window.clearInterval(syncTimer);};
 },[connection]);
 useEffect(()=>()=>{companionRevision.current++;clearClocks();const existing=client.current;client.current=null;if(existing)void existing.disarm().catch(()=>{}).finally(()=>existing.close());},[]);
 async function connect(){
  if(operationRef.current)return;
  const revision=++companionRevision.current;actionRevision.current++;disarming.current=false;setBusy(true);clearClocks();
  const previous=client.current;client.current=null;setConnection(0);statusRef.current=null;setStatus(null);retiredStreams.current.clear();
  setDevices([]);setSelected('');setScanned(false);setNotice('Connecting to the loopback companion…');
  let nextClient:LocalMuseBridge|null=null;
  try{
   if(previous){await previous.disarm().catch(()=>{});previous.close();}
   if(revision!==companionRevision.current)return;
   nextClient=new LocalMuseBridge();const next=await nextClient.connect(token);
   if(revision!==companionRevision.current){nextClient.close();return;}
   client.current=nextClient;applyStatus(next);setToken('');pollCursor.current=nextClient.initialCursor;setConnection(revision);
   setNotice('Companion connected. Select Live Muse to scan, or choose the available companion source. Arm after signal checks and warmup.');
  }catch{
   nextClient?.close();if(revision!==companionRevision.current)return;
   client.current=null;statusRef.current=null;setStatus(null);setNotice('Companion unavailable. Check the session token and local companion. Keyboard and simulation remain ready.');
  }finally{if(revision===companionRevision.current)setBusy(false);}
 }
 async function arm(){
  const existing=client.current,revision=companionRevision.current;
  if(!existing||disarming.current||!detectorEligible(statusRef.current)||headsetBusy(statusRef.current,operationRef.current))return;
  const action=++actionRevision.current,source=statusRef.current;setBusy(true);
  try{
   await synchronize();if(action!==actionRevision.current||existing!==client.current||!sameStream(source,statusRef.current))return;
   const next=await existing.arm();if(action!==actionRevision.current||existing!==client.current||!sameStream(source,statusRef.current))return;
   if(applyStatus(next))setNotice(next.armed?'Detector armed · double-only closure is active.':next.reason);
  }catch(error){if(existing===client.current)setNotice(museError(error));}
  finally{if(revision===companionRevision.current)setBusy(false);}
 }
 async function disarm(){
  clearClocks();const action=++actionRevision.current,existing=client.current,source=statusRef.current;if(!existing)return;
  disarming.current=true;
  if(source)applyStatus({...source,armed:false});
  try{const next=await existing.disarm();if(action===actionRevision.current&&existing===client.current&&sameStream(source,statusRef.current)){applyStatus({...next,armed:false});setNotice('Detector disarmed · partial gestures cleared; source connection preserved.');}}
  catch{if(action===actionRevision.current&&existing===client.current){loseCompanion();setNotice('Disarm request failed; keyboard and simulation remain ready. Reconnect the companion before arming.');}}
  finally{if(action===actionRevision.current)disarming.current=false;}
 }
 async function headsetOperation(nextOperation:MuseOperation){
  const existing=client.current,revision=companionRevision.current;
  if(!existing||headsetBusy(statusRef.current,operationRef.current))return;
  actionRevision.current++;disarming.current=false;operationRef.current=nextOperation;setOperation(nextOperation);clearClocks();
  if(statusRef.current)applyStatus({...statusRef.current,armed:false,last_error:null});
  if(nextOperation==='scan'){setDevices([]);setSelected('');setScanned(false);}
  try{
   if(nextOperation==='scan'){
    const result=await existing.scan();if(existing!==client.current||revision!==companionRevision.current)return;
    setDevices(result.devices);setSelected(result.devices[0]?.id??'');setScanned(true);
    if(result.status)applyStatus(result.status);
    setNotice(result.devices.length?'Muse discovery complete. Select a headset and connect.':'No advertising Muse headset found.');
   }else{
    const next=nextOperation==='connect'?await existing.connectHeadset(selected):await existing.disconnectHeadset();
    if(existing!==client.current||revision!==companionRevision.current)return;
    applyStatus(next);setDevices([]);setSelected('');setScanned(false);
    setNotice(nextOperation==='disconnect'?'Muse disconnected. Detector disarmed; keyboard and simulation remain ready.':next.connected?'EEG streaming. Check signal quality and warmup before arming.':museError(next.last_error??'stream_start_timeout'));
   }
  }catch(error){
   if(existing!==client.current||revision!==companionRevision.current)return;
   clearClocks();setNotice(museError(error));
   if(nextOperation==='connect'){setDevices([]);setSelected('');setScanned(false);}
  }finally{if(existing===client.current&&revision===companionRevision.current){operationRef.current=null;setOperation(null);}}
 }
 function simulate(){setRequested('SYNTHETIC_TEST');requestedRef.current='SYNTHETIC_TEST';void disarm();const context=propsRef.current.getMusicContext();if(!context){setNotice('Start the draft conducting demo or approved playback, then simulate a double blink.');return;}try{submit(propsRef.current.createSimulation(context));}catch(error){setNotice(String(error));}}
 function startCue(){if(!session)return;const started=Date.now();setCue({id:session.id+'-cue-'+cueIndex,instruction:cueInstructions[cueIndex%cueInstructions.length],started_ms:started,ends_ms:started+4000,feedback_after_ms:started+6000});setCueIndex(n=>n+1);}
 function feedback(kind:typeof feedbackKinds[number]){if(!cue)return;try{const next=[...notes,delayedFeedback(cue,kind,Date.now())].slice(-100);setNotes(next);if(!saveNotes(next))setNotice('Feedback held in this page only; browser storage unavailable.');else setNotice('Delayed feedback saved locally; independent review pending.');setCue(null);}catch(error){setNotice(String(error));}}
 function exportNotes(){const blob=new Blob([JSON.stringify({version:'muse-protocol-notes-1',session,notes,contains_raw_eeg:false,labels_for_training:false,independent_review:'pending'},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='muse-protocol-notes.json';a.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);}
 return <section className="muse-panel" aria-label="Muse conducting and training"><div className="muse-heading"><div><span className="eyebrow">OCULAR-GESTURE CONDUCTING</span><h2>A blink, a prepared key change.</h2></div><div className="muse-mode" data-testid="muse-active-mode"><strong>{presentation.title}</strong><span>{presentation.subtitle}</span></div></div>
 <p className="muse-intro">A deliberate double blink requests the next prepared harmonic transition. Natural blink clusters can resemble that gesture; the detector cannot guarantee intent.</p>
 <div className="muse-control-row"><label>Conducting source<select aria-label="Muse source" value={requested} onChange={event=>{requestedRef.current=event.target.value as MuseMode;setRequested(requestedRef.current);void disarm();}}>{Object.entries(labels).map(([value,label])=><option value={value} key={value}>{label}</option>)}</select></label><button onClick={()=>{requestedRef.current='KEYBOARD';setRequested('KEYBOARD');void disarm();props.onKeyboardRequest();}}>Keyboard request <kbd>M</kbd></button><button onClick={simulate}>Simulate accepted double blink</button></div>
 {actual!==requested&&<p className="muse-hint" role="status">Requested {requested} is unavailable or disarmed. Active source remains KEYBOARD.</p>}
 <p className="muse-notice" role="status">{notice}</p><p className="muse-hint">{props.transportStatus??'The music transport owns the key, voicing, approval and arrival boundary.'}</p>
 {requested==='LIVE_MUSE'&&<MuseHeadset status={status} companionConnected={!!status&&!!client.current} devices={devices} selected={selected} scanned={scanned} operation={operation} onSelect={setSelected} onScan={()=>void headsetOperation('scan')} onConnect={()=>void headsetOperation('connect')} onDisconnect={()=>void headsetOperation('disconnect')}/>}
 <details className="muse-detail" open={requested==='LIVE_MUSE'||undefined}><summary>Local companion & detector</summary><div className="muse-connection"><label>Ephemeral companion token<input aria-label="Companion session token" type="password" value={token} autoComplete="off" onChange={event=>setToken(event.target.value)} placeholder="Printed by the local companion"/></label><button onClick={()=>void connect()} disabled={busy||headsetBusy(status,operation)}>Connect companion</button><button onClick={()=>void arm()} disabled={busy||headsetBusy(status,operation)||!detectorEligible(status)||!!status?.armed}>Arm detector</button><button onClick={()=>void disarm()} disabled={!status}>Disarm detector</button></div><dl className="muse-status"><dt>Companion</dt><dd>{status&&client.current?'Companion connected':'Disconnected / unavailable'}</dd><dt>Source stream</dt><dd>{status?.connected?'Source samples arriving':'No source samples'}</dd><dt>Source readiness</dt><dd>{status?`${status.mode} · ${status.reason}`:'No source verified'}</dd><dt>Signal quality</dt><dd>{status?.quality??'unverified'}</dd><dt>Warmup</dt><dd>{status?.warmup_ready?'Complete':'Waiting for source samples'}</dd><dt>Arm state</dt><dd>{status?.armed&&detectorEligible(status)&&!headsetBusy(status,operation)?'Armed':'Disarmed'}</dd><dt>Active model</dt><dd>{status?.model_version??'Exploratory causal baseline · no learned model deployed'}</dd><dt>Evaluation</dt><dd>{evaluationText(status?.evaluation)}</dd></dl><CheckpointControls bridge={client.current} status={status}/><p className="muse-hint">The companion binds to 127.0.0.1:8766. Only semantic events cross this connection. Raw EEG and waveform review stay on this machine in the local recording tools. No recording starts from this panel.</p></details>
 <details className="muse-detail"><summary>Guided collection & delayed feedback</summary><p>Prepare short independent sessions with natural activity negatives and a separate headset refit. Assign a split before comparing models. These are protocol notes, never detector truth or predictive features.</p><div className="muse-control-row"><label>Session split<select aria-label="Session split" value={split} disabled={!!session} onChange={event=>setSplit(event.target.value)}><option value="train">Train</option><option value="development">Development</option><option value="final-test">Final test · freeze before evaluation</option></select></label><label className="muse-consent"><input type="checkbox" checked={consent} disabled={!!session} onChange={event=>setConsent(event.target.checked)}/>I understand this rehearsal saves local notes only.</label><button disabled={!consent||!!session} onClick={()=>{setSession({id:crypto.randomUUID(),split});setCueIndex(0);}}>Prepare protocol session</button><button disabled={!session} onClick={()=>{setSession(null);setCue(null);setConsent(false);}}>End session</button></div><p className="muse-hint">Real recording requires separate explicit local consent covering frontal EEG, timestamps, local retention, stopping and deletion. Independent video observation needs its own consent. Stop immediately on discomfort; deletion includes derived artifacts.</p><div className="muse-observations"><div><span className="eyebrow">CUE · NOT A PREDICTION</span><p data-testid="muse-cue">{cue?now<cue.ends_ms?cue.instruction:now<cue.feedback_after_ms?'Cue complete · quiet interval before feedback.':'Feedback available; report what happened.':'No cue active.'}</p><button disabled={!session||!!cue} onClick={startCue}>Begin next cue</button></div><div><span className="eyebrow">PREDICTION · NOT A TRUTH LABEL</span><p data-testid="muse-prediction">{diagnostics[0]??'No detector event received.'}</p><p className="muse-hint">Cue timing and feedback never enter the detector.</p></div></div><div className="muse-feedback" aria-label="Delayed feedback">{feedbackKinds.map(kind=><button key={kind} disabled={!cue||now<cue.feedback_after_ms} onClick={()=>feedback(kind)}>{kind}</button>)}</div><p className="muse-hint">{notes.length} delayed notes · independent review pending. Review against the preserved raw trace or independently consented observation before assigning any training label. Do not press feedback during the gesture.</p><button disabled={!notes.length} onClick={exportNotes}>Export local protocol notes</button><button disabled={!notes.length} onClick={()=>{setNotes([]);saveNotes([]);setNotice('Local protocol notes deleted. Delete any separately recorded raw session and its derived artifacts with the local recording tool.');}}>Delete local notes</button></details>
 <details className="muse-detail"><summary>Candidate, decision & timing diagnostics</summary><ol className="muse-log">{diagnostics.length?diagnostics.map((line,index)=><li key={index}>{line}</li>):<li>No events received.</li>}</ol>{lastEnvelope&&<pre>{JSON.stringify({mode:lastEnvelope.action.provenance.source_mode,action_id:lastEnvelope.action.id,detector:lastEnvelope.detector,timing:lastEnvelope.timing},null,2)}</pre>}<p className="muse-hint">Final blink to decision includes sequence closure. Accepted request to scheduled acknowledgement and musical arrival are separate intervals. Scheduled audio timestamps are not measured acoustic output.</p></details>
 </section>;
}
