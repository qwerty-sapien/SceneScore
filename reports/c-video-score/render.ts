// Render the same symbolic compilation and voices used by the keyboard demo.
import {mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {compileTimedDuet} from '../../packages/audio/keyboard-scenes';
import {keyboardVoice} from '../../packages/audio/keyboard-voice';
import {pcmWav,measurements} from '../../packages/audio/engine';
import {SCORE,type Settings} from '../../packages/audio/keyboard-score';
import preset from '../../apps/web/src/keyboard/assets/c-video.json';
const output=fileURLToPath(new URL('.',import.meta.url));mkdirSync(output,{recursive:true});
const settings:Settings={transpose:0,ornament:'plain',touch:'detached'},rate=48000,gainDb=-12;
const config={...SCORE,settings,gainDb,loop_duration_s:preset.duration_s,source:preset};
const hash=createHash('sha256').update(JSON.stringify(config)).digest('hex');
const events=compileTimedDuet(0,preset.duration_s,preset.markers,[{at:0,settings}],hash,preset.duration_s);
const n=Math.round(preset.duration_s*rate);
const buffers=new Map<string,Float32Array>(['piano','guitar','mix'].map(lane=>[lane,new Float32Array(n)]));
const ctx={sampleRate:rate,createBuffer:(_channels:number,length:number)=>{const data=new Float32Array(length);return {getChannelData:()=>data};}} as unknown as BaseAudioContext;
for(const e of events){const data=keyboardVoice(ctx,e).getChannelData(0),start=Math.round(e.resolved_time_s*rate),lane=buffers.get(e.lane_id)!;
 for(let i=0;i<data.length&&start+i<n;i++)lane[start+i]+=data[i]*10**(gainDb/20)*Math.min(1,i/rate/.005);
}
for(let i=0;i<n;i++)buffers.get('mix')![i]=buffers.get('piano')![i]+buffers.get('guitar')![i];
const stats:Record<string,unknown>={};
for(const [lane,data] of buffers){
 const b={numberOfChannels:2,length:n,sampleRate:rate,duration:n/rate,getChannelData:()=>data} as unknown as AudioBuffer;
 const measure=measurements(b);if(!Number.isFinite(measure.peak)||measure.peak>=1||measure.rms<.0001)throw Error('Invalid audio: '+lane);
 const path=output+`C-${lane}-DRAFT.wav`;writeFileSync(path,Buffer.from(pcmWav(b)));
 stats[lane]={...measure,sha256:createHash('sha256').update(readFileSync(path)).digest('hex')};
}
writeFileSync(output+'C-score-DRAFT.json',JSON.stringify({version:'keyboard-c-video-take-1',approval:null,audition_status:'AUDITION_PENDING',source_mode:'api_proposals_with_local_symbolic_music',scene:preset,score:{...SCORE,bpm:960/preset.duration_s},gain_db:gainDb,duration_s:preset.duration_s,initial_settings:settings,config_hash:hash,events,scene_markers:preset.markers,statistics:stats,render_mode:'local_procedural_pcm_same_keyboard_voices',physical_audio:'NOT_RUN'},null,2));
console.log(JSON.stringify({events:events.length,duration_s:preset.duration_s,stats},null,2));
