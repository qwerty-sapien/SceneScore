import type {ScoreEvent} from '../contracts/generated';

// Original synthesis presets. Immutable IDs distinguish these from frozen legacy voices.
export const RIFF_VOICE_VERSION='collision-riff-voices-2';
export function riffVoice(e:ScoreEvent,rate:number):((t:number)=>number)|null{
 const f=e.midi_pitch===null?0:440*2**((e.midi_pitch-69)/12);
 if(e.instrument_id==='piano_felt_comp_v1'){
  const partials=[1,.36,.19,.085,.06,.025,.012].map((a,i)=>({a,n:i+1}))
   .filter(p=>f*p.n<rate*.45);
  return t=>.58*partials.reduce((sum,p)=>{
   const hz=f*p.n*Math.sqrt(1+.000025*p.n*p.n),phase=2*Math.PI*hz*t;
   const strings=.7*Math.sin(phase)+.3*Math.sin(phase*1.0005);
   return sum+p.a*strings*Math.exp(-t*(1.8+.38*p.n));
  },0);
 }
 if(e.instrument_id==='guitar_fingerstyle_v1'){
  const muted=e.articulation==='palm_mute';
  const partials=Array.from({length:14},(_,i)=>i+1).filter(n=>f*n<rate*.45)
   .map(n=>({hz:f*n,a:Math.sin(n*Math.PI*.23)/n**1.28,decay:(muted?9:1.7)+n**1.25*(muted?.7:.24)}));
  return t=>.85*partials.reduce((sum,p)=>sum+p.a*Math.sin(2*Math.PI*p.hz*t)*Math.exp(-t*p.decay),0);
 }
 if(e.instrument_id==='vibraphone_soft_v1'){
  const partials=[[1,.8,1.3],[4,.2,4],[10,.055,12]].filter(([n])=>f*n<rate*.45);
  return t=>.58*(.9+.1*Math.cos(2*Math.PI*5.5*t))*partials.reduce((s,[n,a,d])=>s+a*Math.sin(2*Math.PI*f*n*t)*Math.exp(-d*t),0);
 }
 if(e.instrument_id==='wood_contact_v1'){
  // Inharmonic damped modes, not a noise loop. This is an artistic material palette.
  const root=e.timbre_id==='wood-low'?165:e.timbre_id==='wood-high'?310:225;
  return t=>.75*(Math.sin(2*Math.PI*root*t)*Math.exp(-24*t)+.38*Math.sin(2*Math.PI*root*2.71*t)*Math.exp(-55*t)+.16*Math.sin(2*Math.PI*root*5.43*t)*Math.exp(-110*t));
 }
 return null;
}
