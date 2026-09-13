/** Read-only media/HTTP checks. Run against completed demo sessions. No API calls. */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {validate} from '../packages/contracts/validate';
const base=process.env.SCENESCORE_URL||'http://127.0.0.1:5188';
const ids=process.argv.slice(2);if(!ids.length)throw Error('Pass one or more completed session IDs');
const sha=(b:Buffer)=>createHash('sha256').update(b).digest('hex');
const checks:any[]=[];
for(const id of ids){
 const response=await fetch(`${base}/api/scenescore/${id}`);assert.equal(response.status,200);const job:any=await response.json();assert.equal(job.stage,'Ready');
 const dir=path.resolve('artifacts/scenescore',id),revision=path.join(dir,job.revision),score=JSON.parse(await fs.readFile(path.join(revision,'score.json'),'utf8'));
 assert.equal(score.approval,null);assert.equal(score.audition_status,'AUDITION_PENDING');assert.ok(job.duration>0&&job.duration<30);assert.ok(job.frames.length<=150);
 assert.equal(sha(await fs.readFile(path.join(dir,'source'))),score.source_sha256);
 for(const f of job.frames){assert.equal(sha(await fs.readFile(path.join(dir,f.file))),f.sha256);assert.ok(f.at>=0&&f.at<job.duration);}
 for(const e of score.score.events)validate(e);
 const wavs=await Promise.all(['mix','piano','guitar'].map(async name=>{
  const b=await fs.readFile(path.join(revision,`${name}.wav`));assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.readUInt16LE(22),2);assert.equal(b.readUInt32LE(24),48000);assert.equal(b.readUInt16LE(34),16);
  assert.equal(sha(b),score.audio.find((a:any)=>a.name===name).sha256);return b;
 }));
 assert.equal(wavs[0].length,wavs[1].length);assert.equal(wavs[0].length,wavs[2].length);
 let maxError=0,peak=0,sum=0;
 for(let at=44;at<wavs[0].length;at+=2){const sample=wavs[0].readInt16LE(at);maxError=Math.max(maxError,Math.abs(sample-wavs[1].readInt16LE(at)-wavs[2].readInt16LE(at)));peak=Math.max(peak,Math.abs(sample)/32767);sum+=(sample/32767)**2;}
 assert.ok(maxError<=1);assert.ok(peak>0&&peak<1);const audioDuration=(wavs[0].length-44)/4/48000;assert.ok(Math.abs(audioDuration-job.duration)<1/48000);
 const commands:any[]=[];
 function ff(args:string[]){const result=spawnSync(process.env.SCENESCORE_FFMPEG||'ffmpeg',['-hide_banner','-nostdin','-v','error',...args],{encoding:'utf8',timeout:90000,windowsHide:true});commands.push({args,pid:result.pid,exit_code:result.status});assert.equal(result.status,0,result.stderr);return result.stdout.trim();}
 const videoHash=(file:string)=>ff(['-i',file,'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-']);
 assert.equal(videoHash(path.join(dir,'preview.mp4')),videoHash(path.join(revision,'final.mp4')));
 ff(['-threads','2','-i',path.join(revision,'final.mp4'),'-f','null','-']);
 const asset=`${base}/api/scenescore/${id}/asset/${job.revision}/final.mp4`;
 const ranged=await fetch(asset,{headers:{Range:'bytes=0-31'}});assert.equal(ranged.status,206);assert.equal((await ranged.arrayBuffer()).byteLength,32);
 assert.equal((await fetch(`${base}/api/scenescore/${id}/render`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status,403);
 assert.equal((await fetch(`${base}/api/scenescore/${id}`,{headers:{Origin:'https://untrusted.example'}})).status,403);
 assert.equal((await fetch(`${base}/api/scenescore/${id}/asset/source`)).status,400);
 checks.push({id,name:job.name,revision:job.revision,duration_s:job.duration,frames:job.frames.length,events:job.analysis.markers.length,score_events:score.score.events.length,analysis_mode:score.analysis_mode,peak,rms:Math.sqrt(sum/((wavs[0].length-44)/2)),stem_sum_max_lsb:maxError,video_stream_matches_preview:true,decode:'passed',http_range:'passed',origin_and_header_rejection:'passed',commands});
}
await fs.mkdir('reports/scenescore-demo',{recursive:true});await fs.writeFile('reports/scenescore-demo/media-checks.json',JSON.stringify({utc:new Date().toISOString(),checks,browser_interaction:'NOT_RUN',human_audition:'NOT_RUN',physical_timing:'NOT_RUN'},null,2));
console.log(JSON.stringify(checks.map(({commands,...c})=>c),null,2));
