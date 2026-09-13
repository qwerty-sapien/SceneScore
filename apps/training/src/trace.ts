import type {Trace} from './types';
export interface TraceLane {name:string;unit:string;path:string;scale:number;last:number|null;offset:number}
export function traceLanes(trace:Trace|null,width=1000,laneHeight=92):{lanes:TraceLane[];start:number;end:number;points:number}{
 if(!trace||!trace.times_s.length)return {lanes:[],start:0,end:0,points:0};
 const count=Math.min(trace.times_s.length,trace.samples.length),stride=Math.max(1,Math.ceil(count/2048));
 const indices=Array.from({length:Math.ceil(count/stride)},(_,i)=>i*stride).slice(-2048);
 const start=trace.times_s[indices[0]],end=trace.times_s[indices[indices.length-1]];
 if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)return {lanes:[],start:0,end:0,points:0};
 const typical=(end-start)/Math.max(1,indices.length-1);
 const lanes=trace.channels.slice(0,8).map((channel,c)=>{
  const values=indices.map(i=>trace.samples[i]?.[c]).filter(Number.isFinite);const sorted=[...values].sort((a,b)=>a-b),offset=sorted.length?sorted[Math.floor(sorted.length/2)]:0;const scale=Math.max(1,...values.map(value=>Math.abs(value-offset)));let path='',previousTime:number|null=null,started=false;
  for(const index of indices){const at=trace.times_s[index],value=trace.samples[index]?.[c];if(!Number.isFinite(at)||!Number.isFinite(value)){started=false;previousTime=null;continue;}const x=(at-start)/(end-start)*width,y=c*laneHeight+laneHeight/2-(value-offset)/scale*(laneHeight*.36);const gap=previousTime!==null&&(at-previousTime>typical*3||at<=previousTime);path+=(started&&!gap?'L':'M')+x.toFixed(2)+','+y.toFixed(2);previousTime=at;started=true;}
  return {name:channel.name,unit:channel.unit,path,scale,offset,last:values.length?values[values.length-1]:null};
 });return {lanes,start,end,points:indices.length};
}
