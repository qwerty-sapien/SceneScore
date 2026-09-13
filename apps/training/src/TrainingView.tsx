import React from 'react';

export function TrainingView(props:{active:boolean;busy:boolean;text:string;error:boolean;labelSaved:boolean;onAction:()=>void}){
 return <main className="trainer" aria-label="Blink training">
  <div className="trainer-content">
   <button className="train-button" onClick={props.onAction} disabled={props.busy} data-active={props.active}>{props.active?'Stop':'Train'}</button>
   <p className="instruction">Press <kbd data-saved={props.labelSaved}>B</kbd> once immediately after every deliberate double blink to label your EEG.</p>
   <p className="privacy">Train records and trains locally. Your EEG stays on this machine.</p>
   <p className="training-status" role={props.error?'alert':'status'} aria-live="polite">{props.text}</p>
  </div>
 </main>;
}
