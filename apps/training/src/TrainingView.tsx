import React from 'react';

export function TrainingView(props:{active:boolean;busy:boolean;text:string;error:boolean;labelSaved:boolean;onAction:()=>void;step?:1|2|3;button?:string}){
 const step=props.step??3;
 return <main className="trainer" aria-label="Blink training">
  <div className="trainer-content">
   <p className="step">{step} / 3 · {step===1?'Connect headset':step===2?'Check EEG':'Train'}</p>
   <button className="train-button" onClick={props.onAction} disabled={props.busy} data-active={props.active}>{props.button??(props.active?'Stop':'Train')}</button>
   <p className="instruction">{step===3?<>Blink twice, then press <kbd data-saved={props.labelSaved}>B</kbd> once within 1 second after the second blink. Do this for every deliberate double blink.</>:step===2?'Keep the headset in place while we check for fresh, measurable EEG.':'Switch on your Muse and keep it nearby. Close other apps using the headset, then connect.'}</p>
   <p className="privacy">EEG checks, recordings and model weights stay on this machine.</p>
   <p className="training-status" role={props.error?'alert':'status'} aria-live="polite">{props.text}</p>
  </div>
 </main>;
}
