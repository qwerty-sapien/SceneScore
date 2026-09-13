/** Offline PCM evidence using the existing browser voice function, without a browser or approval. */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {voice,pcmWav,measurements} from '../packages/audio/engine';
import {stemFor,polyphony} from '../packages/audio/mix';
import {stable,verifyBundle} from '../packages/audio/model';
import {validate} from '../packages/contracts/validate';
import type {ScoreEvent} from '../packages/contracts/generated';

const sha=(data:Buffer|string)=>createHash('sha256').update(data).digest('hex');
const input=process.argv[2],output=process.argv[3],variant=process.argv[4]??'mapped';
if(!input||!output||!['mapped','unmodified','planned'].includes(variant))throw Error('Usage: render_music_vertical.ts candidate.json NEW_OUTPUT_DIR [mapped|unmodified|planned]');
const raw=fs.readFileSync(input),bundle=JSON.parse(raw.toString());
await verifyBundle(bundle);
if(bundle.events_bytes&&
 (sha(bundle.events_bytes)!==bundle.events_sha256||stable(JSON.parse(bundle.events_bytes))!==stable(bundle.events)))throw Error('Candidate event bytes mismatch');
const events:ScoreEvent[]=variant==='mapped'?bundle.events:variant==='planned'?bundle.offline_transition_preview?.events:bundle.unmodified_events;
const duration=bundle.scene.duration_s,rate=48000;
if(!Array.isArray(events)||!events.length||events.length>5000||!Number.isFinite(duration)||duration<=0||duration>60)throw Error('Static render budget');
if(fs.existsSync(output))throw Error('Fresh output directory required');
for(const event of events){validate(event);if(event.resolved_time_s<0||event.resolved_time_s+event.duration_s>duration+1e-9)throw Error('Event outside candidate duration');}
polyphony(events);
const frames=Math.round(duration*rate),gain=10**(-18/20);
const stems=['piano','bass','brush','foley'] as const;
const buffers=Object.fromEntries(stems.map(s=>[s,new Float32Array(frames)])) as Record<string,Float32Array>;
const context={sampleRate:rate,createBuffer:(_channels:number,n:number)=>{
 const samples=new Float32Array(n);
 return {length:n,sampleRate:rate,duration:n/rate,numberOfChannels:1,getChannelData:()=>samples};
}} as unknown as BaseAudioContext;
const started=performance.now();
for(const event of events){
 if(performance.now()-started>120000)throw Error('Static render runtime exceeded');
 const rendered=voice(context,event).getChannelData(0),target=buffers[stemFor(event)],start=Math.round(event.resolved_time_s*rate);
 for(let i=0;i<rendered.length&&start+i<frames;i++)target[start+i]+=rendered[i]*gain;
}
const mix=new Float32Array(frames);
for(const stem of stems)for(let i=0;i<frames;i++)mix[i]+=buffers[stem][i];
const all={mix,...buffers};
fs.mkdirSync(output,{recursive:true});
const files=[];
for(const [stem,samples] of Object.entries(all)){
 // A mono voice is copied equally to left/right, as in the existing static browser mix.
 const buffer={sampleRate:rate,length:frames,duration:frames/rate,numberOfChannels:2,getChannelData:()=>samples} as unknown as AudioBuffer;
 const wav=Buffer.from(pcmWav(buffer)),filename=`${variant}-${stem}.wav`,stats=measurements(buffer);
 if(stats.clipped||!Number.isFinite(stats.rms))throw Error('PCM output gate failed');
 fs.writeFileSync(path.join(output,filename),wav,{flag:'wx'});
 files.push({stem,filename,sha256:sha(wav),measurements:stats});
}
if(files.find(f=>f.stem==='mix')!.measurements.rms<=1e-5)throw Error('Silent candidate');
const eventBytes=stable(events)+'\n';
const report={version:'performance-export-2',status:'DRAFT_NOT_APPROVED',approval:null,
 renderer:'existing-browser-voice-static-node-mix-1',browser_measured:false,physical_output_measured:false,
 render_scope:'Existing voice() buffers mixed at fixed -18dB in Node; no live AudioContext, scheduler, output device or human audition',
 bundle_id:bundle.id,bundle_sha256:sha(raw),scene_hash:bundle.scene_hash,composition_hash:bundle.composition_hash,
 video_sha256:bundle.video_sha256,plan_bytes:bundle.plan_bytes,controls:[],
 planned_controls:variant==='planned'?(bundle.offline_transition_preview?.controls??[]):[],
 events,event_bytes:eventBytes,event_hash:sha(eventBytes),
 mode:'SYNTHETIC_TEST',planning_mode:'manual_plan',variant,files,duration_s:duration,video_timestamp_offset_s:0,
 mix_automation:[{scene_s:0,gain_db:-18,muted:false,lanes:{soundtrack:true,foley:true}}],
 clock:{sample_rate:rate,physical_output_measured:false,drift_samples_s:[],control_to_receipt_ms:null,receipt_to_ack_ms:null},
 audition_status:'AUDITION_PENDING',command:process.argv.join(' '),runtime_s:(performance.now()-started)/1000,
 source_hashes:Object.fromEntries(['packages/audio/engine.ts','packages/audio/mix.ts','packages/audio/model.ts','tools/render_music_vertical.ts'].map(p=>[p,sha(fs.readFileSync(p))]))};
fs.writeFileSync(path.join(output,`${variant}.json`),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({output,variant,events:events.length,duration_s:duration,files:files.map(f=>({stem:f.stem,...f.measurements})),approval:null,audition_status:'AUDITION_PENDING'})+'\n');
