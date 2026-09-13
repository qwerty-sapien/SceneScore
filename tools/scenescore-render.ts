import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {compose} from '../apps/web/src/scenescore/model';
import {keyboardVoice} from '../packages/audio/keyboard-voice';
import {pcmWav,measurements} from '../packages/audio/engine';

const [directory]=process.argv.slice(2);
if(!directory)throw Error('Render directory required');
const raw=await fs.readFile(path.join(directory,'request.json'));
const request=JSON.parse(raw.toString()),configHash=createHash('sha256').update(raw).digest('hex');
const score=compose(request.duration,request.markers,request.settings,configHash);
const rate=48000,length=Math.ceil(request.duration*rate);
const context={sampleRate:rate,createBuffer:(_c:number,n:number)=>{const data=new Float32Array(n);return {getChannelData:()=>data};}} as unknown as BaseAudioContext;
const stems={piano:[new Float32Array(length),new Float32Array(length)],guitar:[new Float32Array(length),new Float32Array(length)]};
for(const event of score.events){
 const samples=keyboardVoice(context,event).getChannelData(0),lane=event.lane_id==='piano'?'piano':'guitar',at=Math.round(event.resolved_time_s*rate),pan=lane==='piano'?.16:-.16;
 const gain=10**(request.settings.gainDb/20);
 for(let c=0;c<2;c++)for(let i=0;i<samples.length&&at+i<length;i++)stems[lane][c][at+i]+=samples[i]*gain*(c===0?Math.cos((pan+1)*Math.PI/4):Math.sin((pan+1)*Math.PI/4))*Math.SQRT2;
}
const mix=[new Float32Array(length),new Float32Array(length)];
for(const channels of Object.values(stems))for(let c=0;c<2;c++)for(let i=0;i<length;i++){channels[c][i]*=Math.min(1,i/(rate*.01),(length-1-i)/(rate*.08));mix[c][i]+=channels[c][i];}
const audio=[];
for(const [name,channels] of Object.entries({mix,...stems})){
 const buffer={sampleRate:rate,length,numberOfChannels:2,duration:length/rate,getChannelData:(c:number)=>channels[c]} as AudioBuffer;
 const stats=measurements(buffer);if(stats.clipped||!Number.isFinite(stats.rms))throw Error('Audio peak check failed');
 const bytes=Buffer.from(pcmWav(buffer));await fs.writeFile(path.join(directory,`${name}.wav`),bytes);
 audio.push({name,...stats,sha256:createHash('sha256').update(bytes).digest('hex')});
}
if(audio[0].rms<1e-7&&score.events.length)throw Error('Unexpected silent soundtrack');
await fs.writeFile(path.join(directory,'score.json'),JSON.stringify({version:'scenescore-demo-1',approval:null,audition_status:'AUDITION_PENDING',planning_mode:'local_original_arrangement',...request,score,config_hash:configHash,audio},null,2));
console.log(JSON.stringify({events:score.events.length,audio}));
