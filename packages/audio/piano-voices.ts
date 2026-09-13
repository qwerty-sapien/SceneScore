import type {ScoreEvent} from '../contracts/generated';
import {riffVoice} from './riff-voices';

export const PIANO_VOICE_VERSION='scene-piano-voices-1';
export function scenePianoVoice(event:ScoreEvent,rate:number){
 if(event.instrument_id==='scene_piano_v1')return riffVoice({...event,instrument_id:'piano_felt_comp_v1'},rate);
 if(event.instrument_id==='scene_wood_contact_v1')return riffVoice({...event,instrument_id:'wood_contact_v1',timbre_id:'wood-low'},rate);
 return null;
}
