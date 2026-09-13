import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {TrainingAPI,consumeTokenFragment} from './api';
import {TapLabelController,progressText} from './automatic';
import {TrainingView} from './TrainingView';
import type {AutomaticStatus} from './types';
import './style.css';

const token=consumeTokenFragment(window.location,window.history);
const local=window.location.hostname==='127.0.0.1'||window.location.hostname==='localhost';
function App(){
 const api=useRef(new TrainingAPI(undefined,window.location.origin+'/v1'));
 const [authenticated,setAuthenticated]=useState(false),[status,setStatus]=useState<AutomaticStatus|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[labelSaved,setLabelSaved]=useState(false);
 const latest=useRef(status),generation=useRef(0),ackTimer=useRef(0),initialAuth=useRef(false);
 latest.current=status;
 const controller=useRef<TapLabelController|null>(null);
 if(!controller.current)controller.current=new TapLabelController(value=>api.current.labelAutomatic(value),()=>{setLabelSaved(true);window.clearTimeout(ackTimer.current);ackTimer.current=window.setTimeout(()=>setLabelSaved(false),220);},()=>{setError('That B label was not saved. Training has paused; check the local connection.');void api.current.stopAutomatic().catch(()=>{});});
 useEffect(()=>{
  if(!local||!token||initialAuth.current)return;
  initialAuth.current=true;
  void api.current.authenticate(token).then(()=>{setAuthenticated(true);setError('');}).catch(()=>setError('Open Launch Blink Trainer.command again to reconnect.'));
 },[]);
 useEffect(()=>{
  if(!authenticated)return;
  let active=true,timer=0;const abort=new AbortController();
  async function poll(){const version=generation.current;try{const next=await api.current.automaticStatus(abort.signal);if(active&&version===generation.current)setStatus(next);}catch{if(active)setError('Local trainer disconnected. Saved models are retained. Reopen Launch Blink Trainer.command.');}finally{if(active)timer=window.setTimeout(()=>void poll(),500);}}
  void poll();return()=>{active=false;abort.abort();window.clearTimeout(timer);};
 },[authenticated]);
 useEffect(()=>{
  const down=(event:KeyboardEvent)=>{if(controller.current!.down(event,latest.current))event.preventDefault();};
  const up=(event:KeyboardEvent)=>controller.current!.up(event.code);
  // A native Bluetooth permission dialog can blur the window during setup.
  // Only active recording requires focus; hiding the page also closes setup.
  const pause=()=>{controller.current!.release();if(latest.current?.active){void controller.current!.flush().then(()=>api.current.stopAutomatic()).then(setStatus).catch(()=>{});}};
  const visibility=()=>{if(document.hidden){pause();if(!latest.current?.active&&['connecting','checking','ready'].includes(latest.current?.preparation?.state??''))void api.current.stopAutomatic().then(setStatus).catch(()=>{});}};
  window.addEventListener('keydown',down);window.addEventListener('keyup',up);window.addEventListener('blur',pause);document.addEventListener('visibilitychange',visibility);
  return()=>{window.removeEventListener('keydown',down);window.removeEventListener('keyup',up);window.removeEventListener('blur',pause);document.removeEventListener('visibilitychange',visibility);window.clearTimeout(ackTimer.current);};
 },[]);
 async function action(){
  if(!authenticated){setError('Open Launch Blink Trainer.command in SceneScore. It connects this page to your local trainer.');return;}
  setBusy(true);setError('');generation.current++;
  try{await controller.current!.flush();const current=latest.current;
   setStatus(current?.active?await api.current.stopAutomatic():current?.preparation?.ready?await api.current.startAutomatic():['connecting','checking','ready'].includes(current?.preparation?.state??'')?await api.current.stopAutomatic():await api.current.connectAutomatic());}
  catch(problem){setError(problem instanceof Error?problem.message:String(problem));}
  finally{generation.current++;setBusy(false);}
 }
 const prep=status?.preparation, running=!!status?.active, ready=!!prep?.ready;
 const waiting=['connecting','checking','ready'].includes(prep?.state??'')&&!ready;
 const step=running||ready?3:prep?.state==='checking'||prep?.state==='ready'?2:1;
 const button=running?'Stop':ready?'Train':waiting?'Cancel':'Connect headset';
 const prefix=status?.source_mode==='synthetic'?'Synthetic rehearsal · ':'';
 const text=running?progressText(status):prep&&prep.state!=='idle'?prefix+prep.message:status?.run_id?progressText(status):authenticated?prefix+(prep?.message??'Switch on your Muse, then connect it.'):'Open Launch Blink Trainer.command to use the local trainer.';
 return <TrainingView active={running} busy={busy} step={step} button={button} text={error||text} error={!!error||prep?.state==='error'||status?.phase==='error'} labelSaved={labelSaved} onAction={()=>void action()}/>;
}
createRoot(document.getElementById('root')!).render(<App/>);
