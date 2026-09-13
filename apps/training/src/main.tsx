import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {API_ROOT,TrainingAPI,consumeTokenFragment} from './api';
import {TapLabelController,progressText} from './automatic';
import {TrainingView} from './TrainingView';
import type {AutomaticStatus} from './types';
import './style.css';

const token=consumeTokenFragment(window.location,window.history);
const local=window.location.hostname==='127.0.0.1'||window.location.hostname==='localhost';
function App(){
 const api=useRef(new TrainingAPI(undefined,local?window.location.origin+'/v1':API_ROOT));
 const [authenticated,setAuthenticated]=useState(false),[status,setStatus]=useState<AutomaticStatus|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[labelSaved,setLabelSaved]=useState(false);
 const latest=useRef(status),generation=useRef(0),ackTimer=useRef(0),initialAuth=useRef(false);
 latest.current=status;
 const controller=useRef<TapLabelController|null>(null);
 if(!controller.current)controller.current=new TapLabelController(value=>api.current.labelAutomatic(value),()=>{setLabelSaved(true);window.clearTimeout(ackTimer.current);ackTimer.current=window.setTimeout(()=>setLabelSaved(false),220);},()=>{setError('That B label was not saved. Training has paused; check the local connection.');void api.current.stopAutomatic().catch(()=>{});});
 useEffect(()=>{
  if(!token||initialAuth.current)return;
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
  const pause=()=>{controller.current!.release();if(latest.current?.active){void controller.current!.flush().then(()=>api.current.stopAutomatic()).then(setStatus).catch(()=>{});}};
  const visibility=()=>{if(document.hidden)pause();};
  window.addEventListener('keydown',down);window.addEventListener('keyup',up);window.addEventListener('blur',pause);document.addEventListener('visibilitychange',visibility);
  return()=>{window.removeEventListener('keydown',down);window.removeEventListener('keyup',up);window.removeEventListener('blur',pause);document.removeEventListener('visibilitychange',visibility);window.clearTimeout(ackTimer.current);};
 },[]);
 async function action(){
  if(!authenticated){setError('Open Launch Blink Trainer.command in SceneScore. It connects this page to your local trainer.');return;}
  setBusy(true);setError('');generation.current++;
  try{await controller.current!.flush();setStatus(latest.current?.active?await api.current.stopAutomatic():await api.current.startAutomatic());}
  catch(problem){setError(problem instanceof Error?problem.message:String(problem));}
  finally{generation.current++;setBusy(false);}
 }
 return <TrainingView active={!!status?.active} busy={busy} text={error||progressText(status)} error={!!error||status?.phase==='error'} labelSaved={labelSaved} onAction={()=>void action()}/>;
}
createRoot(document.getElementById('root')!).render(<App/>);
