import type {ArrangementPlan,ScoreEvent,InteractionEvent} from '../contracts/generated';
import {RIFF_VOICE_VERSION} from './riff-voices';
export type RiffDesign={version:'collision-riffs-1';voice_version:string;lead:'guitar'|'vibraphone';title:string;
 events_content_sha256:string;final_fade_s:.01;default_gain_db:number;label:string;
 contact_replies:{interaction_id:string;onset_s:number;foley_id:string;reply_ids:string[]}[]};
export type RiffBinding={sound_design?:RiffDesign;sound_design_bytes?:string;sound_design_sha256?:string;sound_design_event_bytes?:string};
export async function verifyRiffs(b:RiffBinding&{events:ScoreEvent[];interactions:InteractionEvent[];scene:{duration_s:number}},p:ArrangementPlan,
 sha:(v:BufferSource)=>Promise<string>,stable:(v:unknown)=>string){
 if(!b.sound_design&&!b.sound_design_bytes&&!b.sound_design_sha256&&!b.sound_design_event_bytes){
  if(b.events.some(e=>/^(guitar_fingerstyle|vibraphone_soft|wood_contact)_v1$/.test(e.instrument_id)))throw Error('Missing riff binding');
  return;
 }
 const d=b.sound_design;
 if(!d||d.version!=='collision-riffs-1'||d.voice_version!==RIFF_VOICE_VERSION||!['guitar','vibraphone'].includes(d.lead)||
    d.final_fade_s!==.01||d.default_gain_db!==-9||b.scene.duration_s!==30||!b.sound_design_bytes||!b.sound_design_event_bytes)throw Error('Unsupported riff binding');
 const hash=await sha(new TextEncoder().encode(b.sound_design_bytes));
 if(hash!==b.sound_design_sha256||hash!==p.provenance.config_hash||!p.provenance.input_hashes.includes(hash)||
    stable(JSON.parse(b.sound_design_bytes))!==stable(d))throw Error('Riff design hash mismatch');
 const content=b.events.map(({plan_id:_plan,...e})=>e);
 if(await sha(new TextEncoder().encode(b.sound_design_event_bytes))!==d.events_content_sha256||
    stable(JSON.parse(b.sound_design_event_bytes))!==stable(content))throw Error('Riff score binding mismatch');
 const contacts=b.interactions.filter(e=>e.event_type==='contact_onset');
 if(d.contact_replies.length!==contacts.length||new Set(d.contact_replies.map(r=>r.interaction_id)).size!==contacts.length)throw Error('Missing contact replies');
 const foley=b.events.filter(e=>e.event_type==='foley');
 if(foley.length!==contacts.length)throw Error('Unexpected collision audio');
 for(const r of d.contact_replies){
  const source=contacts.find(e=>e.id===r.interaction_id),knock=foley.find(e=>e.id===r.foley_id);
  if(!source||r.onset_s!==source.onset_s||!knock||knock.resolved_time_s!==source.onset_s||knock.duration_s>.2||
     knock.midi_pitch!==null||knock.instrument_id!=='wood_contact_v1'||knock.swing_application_count!==0||r.reply_ids.length!==3)throw Error('Invalid contact sonification');
  for(const [i,id] of r.reply_ids.entries()){
   const reply=b.events.find(e=>e.id===id);
   if(!reply||reply.event_type!=='note'||reply.resolved_time_s!==r.onset_s+i*.125||!source.pair.includes(reply.object_id!))throw Error('Invalid contact reply');
  }
 }
}
