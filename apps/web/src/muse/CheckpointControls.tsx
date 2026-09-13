import React,{useEffect,useState} from 'react';
import type {LocalMuseBridge} from './bridge';
import type {BridgeStatus,CheckpointCatalog,ModelEvaluation} from './types';

export function evaluationText(evaluation:ModelEvaluation|null|undefined){
 if(!evaluation)return 'Not yet evaluated · 93% is an advisory target';
 const percent=(value:number|null)=>value===null?'—':(value*100).toFixed(1)+'%';
 const counts=evaluation.tp===undefined?'':` · ${evaluation.tp} matched / ${evaluation.fp} extra / ${evaluation.fn} missed`;
 return `Against B labels: precision ${percent(evaluation.precision)}, recall ${percent(evaluation.recall)}${evaluation.complete?'':' · incomplete check'}${counts} · 93% is advisory`;
}
export function CheckpointControls({bridge,status}:{bridge:LocalMuseBridge|null;status:BridgeStatus|null}){
 const [catalog,setCatalog]=useState<CheckpointCatalog|null>(null),[error,setError]=useState('');
 useEffect(()=>{let current=true;if(bridge&&status)void bridge.models().then(value=>{if(current){setCatalog(value);setError('');}}).catch(error=>{if(current)setError(String(error));});else setCatalog(null);return()=>{current=false;};},[bridge,status?.armed,status?.active_checkpoint_id]);
 async function select(selection:string){if(!bridge)return;try{setCatalog(await bridge.selectModel(selection));setError('');}catch(error){setError(String(error));}}
 return <div className="muse-checkpoints">{catalog&&<label>Model on next Arm<select aria-label="Model on next Arm" disabled={!!status?.armed||!!status?.arming} value={catalog.selection} onChange={event=>void select(event.target.value)}><option value="latest">Latest compatible saved model</option><option value="baseline">Causal baseline</option>{catalog.checkpoints.map(checkpoint=><option key={checkpoint.id} value={checkpoint.id}>{new Date(checkpoint.created_ns/1e6).toLocaleString()} · {checkpoint.id.slice(0,23)} · {checkpoint.training_steps} updates</option>)}</select></label>}{error&&<p role="status">{error}</p>}{!!catalog?.invalid_checkpoint_ids.length&&<p>Invalid checkpoints were excluded; retained files remain available for diagnosis.</p>}</div>;
}
