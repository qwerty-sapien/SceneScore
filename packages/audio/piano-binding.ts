import type {ArrangementPlan,ScoreEvent} from '../contracts/generated';
import {PIANO_VOICE_VERSION} from './piano-voices';

export type PianoMix={version:'scene-piano-mix-1';voice_version:typeof PIANO_VOICE_VERSION;default_gain_db:-6;
 source_bundle_sha256:string;events_content_sha256:string;brush_attenuation_db:18;approval:null;label:string};
export type PianoBinding={piano_mix?:PianoMix;piano_mix_bytes?:string;piano_mix_sha256?:string;piano_event_bytes?:string};

export async function verifyPianoMix(b:PianoBinding&{events:ScoreEvent[]},plan:ArrangementPlan,
 sha:(v:BufferSource)=>Promise<string>,stable:(v:unknown)=>string){
 const owns=b.events.some(e=>['scene_piano_v1','scene_wood_contact_v1'].includes(e.instrument_id));
 if(!owns&&!b.piano_mix&&!b.piano_mix_bytes&&!b.piano_mix_sha256&&!b.piano_event_bytes)return;
 const m=b.piano_mix;
 if(!m||!owns||m.version!=='scene-piano-mix-1'||m.voice_version!==PIANO_VOICE_VERSION||m.default_gain_db!==-6||
    m.brush_attenuation_db!==18||m.approval!==null||!/^([a-f0-9]{64})$/.test(m.source_bundle_sha256)||
    !b.piano_mix_bytes||!b.piano_event_bytes)throw Error('Missing or unsupported piano mix binding');
 const digest=await sha(new TextEncoder().encode(b.piano_mix_bytes));
 if(digest!==b.piano_mix_sha256||digest!==plan.provenance.config_hash||!plan.provenance.input_hashes.includes(digest)||
    stable(JSON.parse(b.piano_mix_bytes))!==stable(m))throw Error('Piano mix hash mismatch');
 if(await sha(new TextEncoder().encode(b.piano_event_bytes))!==m.events_content_sha256||
    stable(JSON.parse(b.piano_event_bytes))!==stable(b.events.map(({plan_id:_plan,...e})=>e)))throw Error('Piano score binding mismatch');
 if(b.events.some(e=>e.event_type==='brush'&&(e.articulation==='sweep'||e.articulation.includes('sustain')))||
    b.events.some(e=>e.event_type==='foley'&&e.instrument_id!=='scene_wood_contact_v1'))throw Error('Unsupported noise layer in piano edition');
}
