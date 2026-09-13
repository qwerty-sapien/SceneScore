import type {ScoreEvent} from '../contracts/generated';
import {voice,articulationEnvelope} from './engine';

// Same fingerstyle partials as riffVoice, advanced by complex recurrence instead
// of evaluating 14 sine/exponential pairs per sample in the scheduling callback.
export function keyboardVoice(ctx:BaseAudioContext,e:ScoreEvent):AudioBuffer{
 if(e.instrument_id!=='guitar_fingerstyle_v1'||e.midi_pitch===null)return voice(ctx,e);
 const rate=ctx.sampleRate,n=Math.max(1,Math.ceil(e.duration_s*rate));
 if(n>rate*120)throw Error('Voice budget');
 const buffer=ctx.createBuffer(1,n,rate),data=buffer.getChannelData(0);
 const frequency=440*2**((e.midi_pitch-69)/12),muted=e.articulation==='palm_mute';
 const partials=Array.from({length:14},(_,i)=>i+1).filter(k=>frequency*k<rate*.45).map(k=>{
  const angle=2*Math.PI*frequency*k/rate,r=Math.exp(-((muted?9:1.7)+k**1.25*(muted?.7:.24))/rate);
  return {real:1,imag:0,c:r*Math.cos(angle),s:r*Math.sin(angle),a:Math.sin(k*Math.PI*.23)/k**1.28};
 });
 const level=.85*e.velocity/127*10**(e.dynamics_db/20);
 for(let i=0;i<n;i++){
  let sum=0;
  for(const p of partials){sum+=p.a*p.imag;const real=p.real*p.c-p.imag*p.s;p.imag=p.real*p.s+p.imag*p.c;p.real=real;}
  const t=i/rate,fade=Math.max(0,Math.min(1,t/.005,(n-1-i)/rate/.012));
  data[i]=sum*level*fade*articulationEnvelope(e.articulation,t,n/rate);
 }
 return buffer;
}
