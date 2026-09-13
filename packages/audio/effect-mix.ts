import type {ScoreEvent} from '../contracts/generated';

/** Linear amplitude/RMS ratios, not a claim about perceived loudness. */
export const EFFECT_MIX={version:'effect-mix-1',music_gain:.8,effect_over_ducked_music:1.2,fade_in_s:.08,fade_out_s:.25} as const;
export type DuckPoint={time:number;gain:number};
export type EffectMix={points:DuckPoint[];levels:Map<string,number>};
export type MixSamples={data:Float32Array;offset?:number;level?:number};

export function duckPoints(events:ScoreEvent[],duration:number):DuckPoint[]{
 const intervals=events.filter(e=>e.event_type==='foley'&&e.resolved_time_s<duration).map(e=>({start:Math.max(0,e.resolved_time_s),end:Math.min(duration,e.resolved_time_s+e.duration_s)})).sort((a,b)=>a.start-b.start);
 const merged:typeof intervals=[];
 for(const interval of intervals){const last=merged.at(-1);if(last&&interval.start-EFFECT_MIX.fade_in_s<=last.end+EFFECT_MIX.fade_out_s)last.end=Math.max(last.end,interval.end);else merged.push({...interval});}
 const points:DuckPoint[]=[{time:0,gain:1}];
 for(const {start,end} of merged){
  points.push({time:Math.max(0,start-EFFECT_MIX.fade_in_s),gain:1},{time:start,gain:.8},{time:end,gain:.8});
  if(end<duration)points.push({time:Math.min(duration,end+EFFECT_MIX.fade_out_s),gain:1});
 }
 // AudioParam ramps at identical timestamps can replace the intended hold.
 return points.filter((p,i)=>i===points.length-1||p.time!==points[i+1].time);
}
export function duckAt(points:DuckPoint[],time:number){
 let previous=points[0];for(const next of points.slice(1)){if(next.time>time)return previous.gain+(next.gain-previous.gain)*(time-previous.time)/(next.time-previous.time);previous=next;}return previous.gain;
}
export function scheduleDucking(param:AudioParam,points:DuckPoint[],audioOrigin:number,sceneOrigin:number,now:number,enabled=true){
 if(typeof param.cancelAndHoldAtTime==='function')param.cancelAndHoldAtTime(now);else param.cancelScheduledValues(now);
 param.setValueAtTime(enabled?duckAt(points,sceneOrigin):1,now);
 if(!enabled)return;
 param.setValueAtTime(duckAt(points,sceneOrigin),Math.max(now,audioOrigin));
 for(const point of points)if(point.time>sceneOrigin)param.linearRampToValueAtTime(point.gain,Math.max(now,audioOrigin+point.time-sceneOrigin));
}

/** Calibrate overlapping effects as one stem against the actual dry soundtrack.
 * One fixed gain per overlap group preserves effect envelopes and avoids pumping.
 * Rests use the whole-score RMS reference; they remain rests in the output. */
export function prepareEffectMix(events:ScoreEvent[],duration:number,rate:number,samples:(e:ScoreEvent)=>MixSamples):EffectMix{
 const points=duckPoints(events,duration),levels=new Map<string,number>();
 const effects=events.filter(e=>e.event_type==='foley'&&e.resolved_time_s<duration);
 if(!effects.length)return {points,levels};
 const n=Math.ceil(duration*rate),music=new Float32Array(n),foley=new Float32Array(n);
 for(const e of events){const target=e.event_type==='foley'?foley:music,{data,offset=0,level=1}=samples(e),start=Math.round(e.resolved_time_s*rate),skip=Math.round(offset*rate),count=Math.min(Math.ceil(e.duration_s*rate),data.length-skip,n-start);
  for(let i=0;i<count;i++)if(start+i>=0)target[start+i]+=data[skip+i]*level;
 }
 const rms=(data:Float32Array,start:number,end:number)=>{let sum=0;for(let i=start;i<end;i++)sum+=data[i]*data[i];return Math.sqrt(sum/Math.max(1,end-start));};
 const reference=rms(music,0,n);
 const groups:{start:number;end:number;events:ScoreEvent[]}[]=[];
 for(const e of effects.sort((a,b)=>a.resolved_time_s-b.resolved_time_s)){const start=Math.max(0,e.resolved_time_s),end=Math.min(duration,start+e.duration_s),last=groups.at(-1);if(last&&start<last.end){last.end=Math.max(last.end,end);last.events.push(e);}else groups.push({start,end,events:[e]});}
 for(const group of groups){const start=Math.round(group.start*rate),end=Math.min(n,Math.ceil(group.end*rate)),base=rms(music,start,end)||reference,effect=rms(foley,start,end);
  const gain=effect>0&&base>0?base*EFFECT_MIX.music_gain*EFFECT_MIX.effect_over_ducked_music/effect:1;
  for(const e of group.events)levels.set(e.id,gain);
 }
 return {points,levels};
}
