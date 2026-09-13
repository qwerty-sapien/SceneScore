/** Draft soundtracks for existing video files, using SceneScore's authored music and voice().
 * Run: node --import tsx tools/score_imported_videos.ts A.mov B.mov NEW_REVIEW_DIR FFMPEG
 * No geometry is inferred and no existing scene's contact events or approval are reused.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {voice, pcmWav, measurements} from '../packages/audio/engine';
import {polyphony, stemFor} from '../packages/audio/mix';
import {validate} from '../packages/contracts/validate';
import type {ScoreEvent, Provenance} from '../packages/contracts/generated';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const [a,b,destination,ffmpeg]=process.argv.slice(2);
if(!a||!b||!destination||!ffmpeg)throw Error('Usage: A.mov B.mov NEW_REVIEW_DIR FFMPEG');
const out=path.resolve(destination),rate=48000,version='imported-video-draft-1';
const sha=(data:Buffer|string)=>createHash('sha256').update(data).digest('hex');
const write=(name:string,value:unknown)=>fs.writeFileSync(name,JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const sourcePath=path.join(root,'apps/web/public/riff-studio/near-miss-brush_swing_light_v1-guitar-piano-v2.json');
const sourceRaw=fs.readFileSync(sourcePath),source=JSON.parse(sourceRaw.toString());
if(sha(source.events_bytes)!==source.events_sha256)throw Error('Source score integrity check failed');
if(source.events.some((e:ScoreEvent)=>e.event_type==='foley'))throw Error('Music-only source required');
const sourceHash=sha(sourceRaw);
const codePaths=['tools/score_imported_videos.ts','tools/video-review.html','packages/audio/engine.ts','packages/audio/riff-voices.ts','packages/audio/mix.ts','modules/arranger/collision_riffs.py'];
const codeHashes=Object.fromEntries(codePaths.map(p=>[p,sha(fs.readFileSync(path.join(root,p)))]));

// Read the file's declared MOV movie timescale without guessing from rounded console output.
function movieDuration(file:string){
 const data=fs.readFileSync(file);
 function boxes(start:number,end:number):number|undefined{
  for(let pos=start;pos+8<=end;){
   const small=data.readUInt32BE(pos),kind=data.toString('ascii',pos+4,pos+8);
   const header=small===1?16:8,size=small===1?Number(data.readBigUInt64BE(pos+8)):small||end-pos;
   if(size<header||pos+size>end)throw Error('Invalid MOV box');
   const payload=pos+header;
   if(kind==='mvhd'){
    const v=data[payload];
    if(v!==0&&v!==1)throw Error('Unsupported movie header');
    const scale=data.readUInt32BE(payload+(v===1?20:12));
    const duration=v===1?Number(data.readBigUInt64BE(payload+24)):data.readUInt32BE(payload+16);
    return duration/scale;
   }
   if(kind==='moov'){const result=boxes(payload,pos+size);if(result!==undefined)return result;}
   pos+=size;
  }
 }
 const duration=boxes(0,data.length);
 if(!duration||!Number.isFinite(duration)||duration>60)throw Error('Video duration must be within 60 seconds');
 return {duration,sha256:sha(data)};
}

function vlq(value:number){
 const bytes=[value&127];while((value>>>=7)>0)bytes.unshift((value&127)|128);return Buffer.from(bytes);
}
function midi(events:ScoreEvent[],bpm:number,duration:number){
 const ppq=960,ticksPerSecond=ppq*bpm/60;
 function track(rows:{tick:number;order:number;data:Buffer}[]){
  rows.sort((x,y)=>x.tick-y.tick||x.order-y.order);let previous=0;
  const chunks:Buffer[]=[];
  for(const row of rows){chunks.push(vlq(row.tick-previous),row.data);previous=row.tick;}
  chunks.push(vlq(Math.max(0,Math.round(duration*ticksPerSecond)-previous)),Buffer.from([255,47,0]));
  const payload=Buffer.concat(chunks),head=Buffer.alloc(8);head.write('MTrk');head.writeUInt32BE(payload.length,4);
  return Buffer.concat([head,payload]);
 }
 const micros=Math.round(60000000/bpm),tracks=[track([
  {tick:0,order:0,data:Buffer.from([255,81,3,(micros>>>16)&255,(micros>>>8)&255,micros&255])},
  {tick:0,order:1,data:Buffer.from([255,88,4,4,2,24,8])}
 ])];
 const instruments=[...new Set(events.map(e=>e.instrument_id))];
 instruments.forEach((instrument,index)=>{
  const channel=instrument==='brush_noise_v1'?9:index;
  const program=instrument.includes('guitar')?24:instrument.includes('vibraphone')?11:instrument.includes('bass')?32:0;
  const name=Buffer.from(instrument),rows=[
   {tick:0,order:0,data:Buffer.concat([Buffer.from([255,3]),vlq(name.length),name])},
   {tick:0,order:1,data:Buffer.from([192+channel,program])}
  ];
  for(const event of events.filter(e=>e.instrument_id===instrument)){
   const start=Math.round(event.resolved_time_s*ticksPerSecond);
   const end=Math.max(start+1,Math.round((event.resolved_time_s+event.duration_s)*ticksPerSecond));
   const pitch=event.midi_pitch??(event.articulation==='sweep'?51:38);
   rows.push({tick:start,order:3,data:Buffer.from([144+channel,pitch,event.velocity])});
   rows.push({tick:end,order:2,data:Buffer.from([128+channel,pitch,0])});
  }
  tracks.push(track(rows));
 });
 const head=Buffer.alloc(14);head.write('MThd');head.writeUInt32BE(6,4);head.writeUInt16BE(1,8);
 head.writeUInt16BE(tracks.length,10);head.writeUInt16BE(ppq,12);return Buffer.concat([head,...tracks]);
}

fs.mkdirSync(out,{recursive:true});
for(const name of ['A','B','index.html','manifest.json'])if(fs.existsSync(path.join(out,name)))throw Error('Fresh review outputs required: '+name);
const definitions=[
 {id:'A',input:path.resolve(a),title:'Spiral Swing',lead:'guitar_fingerstyle_v1',form:Array.from({length:12},(_,i)=>i),
  description:'Brisk fingerstyle guitar, answering felt piano, plucked bass and light brushes.',pan:-.12,
  cues:[{at:0,label:'Opening hook'},{at:11.5,label:'Camera change / rising answer'},{at:19.2,label:'Return and closing phrase'}]},
 {id:'B',input:path.resolve(b),title:'Silver Switchyard',lead:'vibraphone_soft_v1',form:[0,1,2,3,4,5,6,7,4,5,6,7,8,9,10,11],
  description:'Spacious vibraphone and felt piano, with a lower-register middle passage, bass and brushes.',pan:-.12,
  cues:[{at:0,label:'Opening mechanism'},{at:10.25,label:'Rolling passage'},{at:20.5,label:'Funnel / lower-register variation'},{at:30.75,label:'Pullback / final turnaround'}]}
];
const entries=[];
for(const config of definitions){
 const started=performance.now(),media=movieDuration(config.input),duration=media.duration;
 const frames=Math.round(duration*rate),barDuration=duration/config.form.length,bpm=240/barDuration,scale=barDuration/2.5;
 const composition=structuredClone(source.composition);
 const inputHashes=[sourceHash,media.sha256],configHash=sha(JSON.stringify({config,duration,bpm,codeHashes}));
 const provenance:Provenance={creator:version,tool_version:version,source_mode:'manual_plan',seed:42,config_hash:configHash,input_hashes:inputHashes};
 const planId=`${version}:${config.id}:${configHash.slice(0,16)}`;
 const events:ScoreEvent[]=[];
 config.form.forEach((sourceBar,targetBar)=>{
  for(const original of source.events as ScoreEvent[]){
   if(original.start_tick===null||Math.floor(original.start_tick/3840)!==sourceBar)continue;
   const event=structuredClone(original),isLead=event.instrument_id==='guitar_fingerstyle_v1';
   event.id=`${config.id}:bar${targetBar}:${original.id}`;event.plan_id=planId;
   event.object_id=null;event.scene_time_s=null;event.provenance=provenance;
   event.start_tick=targetBar*3840+original.start_tick-sourceBar*3840;
   event.resolved_time_s=targetBar*barDuration+(original.resolved_time_s-sourceBar*2.5)*scale;
   event.duration_s=Math.min(original.duration_s*scale,duration-event.resolved_time_s);
   if(isLead){
    event.instrument_id=config.lead;event.timbre_id=config.lead;event.lane_id='lead';
    if(config.id==='B'){
     event.articulation='ring';event.velocity=Math.round(event.velocity*.91);
     if(targetBar>=8&&targetBar<=11)event.midi_pitch!-=12;
    }
   }
   // Give the middle of the slower clip room, then let the final cadence settle.
   if(config.id==='B'&&targetBar>=8&&targetBar<=11)event.dynamics_db-=1.5;
   if(targetBar===config.form.length-1)event.dynamics_db-=1;
   if(event.duration_s<=0)throw Error('Event exceeds video');
   validate(event);events.push(event);
  }
 });
 events.sort((x,y)=>x.resolved_time_s-y.resolved_time_s||x.id.localeCompare(y.id));
 if(new Set(events.map(e=>e.id)).size!==events.length)throw Error('Duplicate event');
 const maxPolyphony=polyphony(events);
 composition.id=`${config.id.toLowerCase()}-${config.title.toLowerCase().replaceAll(' ','-')}-draft-v1`;
 composition.title=config.title;composition.catalog_version=1;composition.provenance=provenance;
 composition.length_ticks=config.form.length*3840;composition.tempo_map=[{tick:0,bpm}];
 composition.notes=config.form.flatMap((sourceBar,targetBar)=>source.composition.notes
  .filter((n:any)=>Math.floor(n.start_tick/3840)===sourceBar)
  .map((n:any)=>({...n,start_tick:targetBar*3840+n.start_tick-sourceBar*3840,
   midi_pitch:n.midi_pitch-(config.id==='B'&&targetBar>=8&&targetBar<=11?12:0),
   articulation:config.id==='B'?'ring':n.articulation,velocity:config.id==='B'?Math.round(n.velocity*.91):n.velocity})));
 composition.harmony=config.form.flatMap((sourceBar,targetBar)=>source.composition.harmony
  .filter((h:any)=>Math.floor(h.start_tick/3840)===sourceBar)
  .map((h:any)=>({...h,start_tick:targetBar*3840+h.start_tick-sourceBar*3840})));
 composition.creative_traits=[config.description,'Adaptation of the project-authored Pocket Workshop score.','Music-only manual arrangement for an imported video; no inferred collision or object tracking.'];
 validate(composition);
 const dir=path.join(out,config.id);fs.mkdirSync(dir);
 const stemNames=[...new Set(events.map(stemFor))];
 const buffers=Object.fromEntries(stemNames.map(stem=>[stem,[new Float32Array(frames),new Float32Array(frames)]]));
 const context={sampleRate:rate,createBuffer:(_channels:number,n:number)=>{
  const samples=new Float32Array(n);return {length:n,sampleRate:rate,duration:n/rate,numberOfChannels:1,getChannelData:()=>samples};
 }} as unknown as BaseAudioContext;
 for(const event of events){
  if(performance.now()-started>120000)throw Error('120-second audio render limit');
  const samples=voice(context,event).getChannelData(0),stem=stemFor(event),target=buffers[stem];
  const pan=stem==='piano'?.18:stem==='guitar'||stem==='vibraphone'?config.pan:0;
  const gains=[Math.cos((pan+1)*Math.PI/4)*Math.SQRT2,Math.sin((pan+1)*Math.PI/4)*Math.SQRT2];
  const gain=10**(-9/20),start=Math.round(event.resolved_time_s*rate);
  for(let c=0;c<2;c++)for(let i=0;i<samples.length&&start+i<frames;i++)target[c][start+i]+=samples[i]*gain*gains[c];
 }
 // Shared fades preserve exact stem summation; the music cadence itself is authored in the source.
 const mix=[new Float32Array(frames),new Float32Array(frames)];
 for(const channels of Object.values(buffers))for(let c=0;c<2;c++)for(let i=0;i<frames;i++){
  channels[c][i]*=Math.min(1,i/(rate*.012),(frames-1-i)/(rate*.12));mix[c][i]+=channels[c][i];
 }
 const files=[];
 for(const [stem,channels] of Object.entries({mix,...buffers})){
  const audioBuffer={sampleRate:rate,length:frames,duration:frames/rate,numberOfChannels:2,getChannelData:(c:number)=>channels[c]} as AudioBuffer;
  const stats=measurements(audioBuffer);
  if(stats.clipped||!Number.isFinite(stats.rms)||stats.rms<=1e-6)throw Error('Audio output gate failed: '+stem);
  const filename=stem==='mix'?`${config.id}-music.wav`:`${config.id}-${stem}.wav`,wav=Buffer.from(pcmWav(audioBuffer));
  fs.writeFileSync(path.join(dir,filename),wav,{flag:'wx'});files.push({stem,filename,sha256:sha(wav),...stats});
 }
 const midiBytes=midi(events,bpm,duration);fs.writeFileSync(path.join(dir,`${config.id}-score.mid`),midiBytes,{flag:'wx'});
 const eventBytes=JSON.stringify(events,null,2)+'\n';fs.writeFileSync(path.join(dir,'events.json'),eventBytes,{flag:'wx'});
 write(path.join(dir,'composition.json'),composition);
 const videoName=`${config.id}-with-music.mp4`;
 const command=['-hide_banner','-loglevel','error','-nostdin','-n','-i',config.input,'-i',path.join(dir,`${config.id}-music.wav`),
  '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-threads','2','-t',String(duration),'-movflags','+faststart',path.join(dir,videoName)];
 const mux=spawnSync(ffmpeg,command,{encoding:'utf8',timeout:120000,windowsHide:true});
 if(mux.status!==0)throw Error('Mux failed: '+mux.stderr+' '+mux.error);
 const decode=spawnSync(ffmpeg,['-hide_banner','-loglevel','error','-nostdin','-i',path.join(dir,videoName),'-f','null','-'],{encoding:'utf8',timeout:120000,windowsHide:true});
 if(decode.status!==0)throw Error('Video/audio decode failed: '+decode.stderr);
 const manifest={version,id:config.id,title:config.title,description:config.description,status:'DRAFT_NOT_APPROVED',approval:null,audition_status:'AUDITION_PENDING',
  input:{path:config.input,sha256:media.sha256,duration_s:duration},source_score:{path:path.relative(root,sourcePath),sha256:sourceHash},
  source_code_sha256:codeHashes,planning_mode:'manual_plan',scene_analysis:'Sampled visual inspection only; no 3D scene data, object tracking, or contact-timing claim.',
  source_bar_order:config.form,tempo_bpm:bpm,swing_ratio:composition.swing_ratio,meter:[4,4],bars:config.form.length,
  events_sha256:sha(eventBytes),composition_sha256:sha(fs.readFileSync(path.join(dir,'composition.json'))),midi_sha256:sha(midiBytes),
  midi_note:'Resolved note timing and General MIDI instrument approximations; procedural WAV/JSON are authoritative. Continuous brushes are approximated as percussion notes.',
  render:{sample_rate:rate,frames,channels:2,master_gain_db:-9,pan:{lead:config.pan,piano:.18,bass:0,brush:0},fade_in_s:.012,fade_out_s:.12,max_polyphony:maxPolyphony,events:events.length},
  files,video:{filename:videoName,sha256:sha(fs.readFileSync(path.join(dir,videoName))),video_stream:'copied without re-encoding',decode_passed:true,mux_command:[ffmpeg,...command]},
  review_cues:config.cues,cue_note:'Approximate visual landmarks and musical sections for feedback, not measured physical contacts.',
  created_at:new Date().toISOString(),runtime_s:(performance.now()-started)/1000,node_version:process.version};
 write(path.join(dir,'manifest.json'),manifest);
 entries.push({id:config.id,title:config.title,description:config.description,duration,bpm,bars:config.form.length,video:`${config.id}/${videoName}`,
  wav:`${config.id}/${config.id}-music.wav`,midi:`${config.id}/${config.id}-score.mid`,score:`${config.id}/composition.json`,events:`${config.id}/events.json`,
  manifest:`${config.id}/manifest.json`,sha256:files.find(f=>f.stem==='mix')!.sha256,
  stems:files.filter(f=>f.stem!=='mix').map(f=>({name:f.stem,url:`${config.id}/${f.filename}`})),cues:config.cues});
 console.log(JSON.stringify({id:config.id,duration,bpm,events:events.length,mix:files.find(f=>f.stem==='mix'),decode:'passed'}));
}
write(path.join(out,'manifest.json'),{version,approval:null,audition_status:'AUDITION_PENDING',entries,source_code_sha256:codeHashes});
const html=fs.readFileSync(path.join(root,'tools/video-review.html'),'utf8').replace('/* REVIEW_DATA */[]',JSON.stringify(entries).replaceAll('<','\\u003c'));
fs.writeFileSync(path.join(out,'index.html'),html,{flag:'wx'});
console.log('Review page: '+path.join(out,'index.html'));
