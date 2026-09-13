/** Check the published contract and render the actual player voices without starting a browser. */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {verifyBundle, type Bundle} from '../packages/audio/model';
import {Timeline} from '../packages/audio/transport';
import {voice, pcmWav, measurements} from '../packages/audio/engine';
import {polyphony} from '../packages/audio/mix';
import {prepareEffectMix, duckAt} from '../packages/audio/effect-mix';

const dir='apps/web/public/requested-animations',out='artifacts/direction-music/audio';
fs.mkdirSync(out,{recursive:true});
const catalog=JSON.parse(fs.readFileSync(path.join(dir,'catalog.json'),'utf8'));
const hash=(data:Buffer|string)=>createHash('sha256').update(data).digest('hex');
const rows=[];
for(const entry of catalog.entries){
 const raw=fs.readFileSync(path.join(dir,entry.url)),b:Bundle=JSON.parse(raw.toString());
 if(hash(raw)!==entry.sha256)throw Error('Catalog hash mismatch');
 const video=fs.readFileSync(path.join(dir,b.video));
 const p=await verifyBundle(b,video.buffer.slice(video.byteOffset,video.byteOffset+video.byteLength));
 const timeline=new Timeline(b,p,b.plan_sha256);
 const effects=b.events.filter(e=>e.event_type==='foley'),contacts=b.interactions.filter(e=>e.event_type==='contact_onset');
 if(effects.length!==contacts.length||!effects.length)throw Error('Missing scene effects');
 for(const c of contacts)if(!effects.some(e=>e.id==='foley:'+c.id&&e.resolved_time_s===c.onset_s))throw Error('Contact timing mismatch');
 for(const e of b.events)if(e.resolved_time_s<0||e.resolved_time_s+e.duration_s>30+1e-9)throw Error('Out-of-window score');
 const row:any={id:b.id,status:'PASSED',events:b.events.length,foley:effects.length,polyphony:polyphony(b.events),duration_s:timeline.bundle.scene.duration_s,approval:null};
 if(entry.groove==='brush_swing_light_v1'){
  const rate=48000,n=30*rate,gain=10**(-6/20);
  const context={sampleRate:rate,createBuffer:(_c:number,length:number)=>{const data=new Float32Array(length);return {length,sampleRate:rate,duration:length/rate,numberOfChannels:1,getChannelData:()=>data};}} as unknown as BaseAudioContext;
  const cache=new Map(b.events.map(e=>[e.id,voice(context,e).getChannelData(0)]));
  const effectMix=prepareEffectMix(b.events,30,rate,e=>({data:cache.get(e.id)!}));
  const music=new Float32Array(n),foley=new Float32Array(n),mix=new Float32Array(n);
  for(const e of b.events){const dst=e.event_type==='foley'?foley:music,data=cache.get(e.id)!,start=Math.round(e.resolved_time_s*rate),level=effectMix.levels.get(e.id)??1;
   for(let i=0;i<data.length&&start+i<n;i++)dst[start+i]+=data[i]*level*gain;
  }
  for(let i=0;i<n;i++){music[i]*=duckAt(effectMix.points,i/rate);const fade=Math.min(1,(n-1-i)/479);music[i]*=fade;foley[i]*=fade;mix[i]=music[i]+foley[i];}
  row.pcm={};
  for(const [stem,data] of Object.entries({mix,music,foley})){
   const buffer={length:n,sampleRate:rate,duration:30,numberOfChannels:2,getChannelData:()=>data} as unknown as AudioBuffer;
   const stats=measurements(buffer);if(stats.clipped||stats.rms<=1e-6||!Number.isFinite(stats.peak))throw Error('Silent or clipped '+stem);
   const wav=Buffer.from(pcmWav(buffer)),file=path.join(out,b.variant+'-'+stem+'.wav');fs.writeFileSync(file,wav);
   row.pcm[stem]={...stats,file,sha256:hash(wav)};
  }
 }
 rows.push(row);process.stdout.write(JSON.stringify(row)+'\n');
}
const sources=['packages/audio/engine.ts','packages/audio/effect-mix.ts','packages/audio/piano-voices.ts','packages/audio/riff-voices.ts','packages/audio/model.ts','packages/audio/transport.ts','apps/web/tools/prepare_requested_videos.py','tools/validate_direction_music.ts'];
fs.writeFileSync('reports/vercel-animations-06-08-18/audio-validation.json',JSON.stringify({status:'PASSED',rows,source_hashes:Object.fromEntries(sources.map(p=>[p,hash(fs.readFileSync(p))])),scope:'Node PCM from actual player voice buffers, matching effect calibration and ducking. No browser/device timing or human audition claim.',approval:null},null,2)+'\n');
