import type {ControlAction} from '../contracts/generated';
import {createSimulation,type ControlEnvelope} from './control';
import {selectVerticalTransition} from './model';
import type {Timeline} from './transport';

/** Inspect prepared choices without submitting speculative controls or changing the score. */
export function manualChoices(t:Timeline,scene:number,expiresAfter=6):(-2|2)[]{
 if(!t.playing||!t.preparationReady||t.pending.length||!Number.isFinite(scene))return [];
 return ([-2,2] as const).filter(sign=>{
  if(t.vertical)return t.verticalHistory.length<48&&!!selectVerticalTransition(t.vertical,t.currentTonic(),sign,scene,scene+expiresAfter);
  const boundary=t.boundaries.find(b=>b.at>=scene+.175);
  return !!boundary&&boundary.arrival<scene+expiresAfter&&boundary.arrival<t.bundle.scene.duration_s&&t.prepared.has(`${boundary.tick}:${sign}`);
 });
}

/** Manual audition overrides geometry only; the same dispatcher still enforces all transport gates. */
export function createManualKeyChange(t:Timeline,audio:number,scene:number,lanes:ControlAction['before'],seed:number):ControlEnvelope|null{
 const choices=manualChoices(t,scene);if(!choices.length)return null;
 if(!Number.isInteger(seed)||seed<0||seed>0xffffffff)throw Error('Invalid manual key-change seed');
 const signed_semitones=choices[Math.floor(seed/0x100000000*choices.length)];
 const envelope=createSimulation({audio_s:audio,audio_epoch:t.epoch,approved_plan_hash:t.planHash,scene_policy_id:t.plan.motion_policy.id,signed_semitones,lanes},'keyboard');
 envelope.action.provenance={...envelope.action.provenance,creator:'scenescore-manual-random-key-change',tool_version:'manual-prepared-choice-1',seed};
 envelope.detector.version='manual-prepared-choice-1';
 envelope.timing.unavailable_reasons.detector_latency='Manual button; seeded prepared choice replaces scene direction, no EEG classification';
 return envelope;
}
