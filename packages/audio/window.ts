import type {ScoreEvent} from '../contracts/generated';

/** A playback projection retains source events and their original articulation. */
export type PlaybackWindow={
 version:'scene-playback-window-1';start_s:0;duration_s:number;frame_count:number;render_fps:30;
 sample_rate_hz:48000;audio_sample_count:number;final_fade_s:.01;
 original_events_sha256:string;label:'Draft · existing score excerpt · adaptive scoring pending';approval:null;
 projections:{source_event_id:string;start_s:number;stop_s:number;source_offset_s:number}[];
 omitted:unknown[];truncated:unknown[];
};

export function validateWindow(window:PlaybackWindow, duration:number){
 if(window.version!=='scene-playback-window-1'||window.start_s!==0||window.duration_s!==duration||
    window.render_fps!==30||!Number.isInteger(window.frame_count)||window.frame_count<1||
    Math.abs(window.frame_count/30-duration)>1e-9||window.sample_rate_hz!==48000||
    window.audio_sample_count!==window.frame_count*1600||window.final_fade_s!==.01||window.approval!==null||
    window.label!=='Draft · existing score excerpt · adaptive scoring pending')
  throw Error('Playback window clock or policy mismatch');
 const ids=new Set<string>();
 for(const p of window.projections){
  if(ids.has(p.source_event_id)||![p.start_s,p.stop_s,p.source_offset_s].every(Number.isFinite)||
     p.start_s<0||p.stop_s>duration||p.stop_s<=p.start_s||p.source_offset_s<0)throw Error('Invalid event projection');
  ids.add(p.source_event_id);
 }
 return window;
}

export function selectWindowEvents(events:ScoreEvent[],window:PlaybackWindow){
 validateWindow(window,window.duration_s);
 const source=new Map(events.map(e=>[e.id,e]));
 if(source.size!==events.length)throw Error('Duplicate source events');
 const expected=events.filter(e=>e.resolved_time_s<window.duration_s);
 if(window.projections.length!==expected.length||expected.some(e=>!window.projections.some(p=>p.source_event_id===e.id)))throw Error('Incomplete event projection');
 const omitted=events.filter(e=>e.resolved_time_s>=window.duration_s).map(e=>({source_event_id:e.id,source_start_s:e.resolved_time_s,source_stop_s:e.resolved_time_s+e.duration_s,reason:'starts_at_or_after_scene_end'}));
 const truncated=expected.filter(e=>e.resolved_time_s+e.duration_s>window.duration_s).map(e=>({source_event_id:e.id,source_start_s:e.resolved_time_s,source_stop_s:e.resolved_time_s+e.duration_s,playback_stop_s:window.duration_s,removed_before_s:0,removed_after_s:e.resolved_time_s+e.duration_s-window.duration_s,reason:'crosses_scene_end'}));
 const stable=(x:unknown):string=>Array.isArray(x)?'['+x.map(stable).join(',')+']':x&&typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable((x as Record<string,unknown>)[k])).join(',')+'}':JSON.stringify(x);
 if(stable(window.omitted)!==stable(omitted)||stable(window.truncated)!==stable(truncated))throw Error('Stale omitted or truncated event ledger');
 return window.projections.map(p=>{
  const e=source.get(p.source_event_id);
  if(!e||Math.abs(p.start_s-Math.max(0,e.resolved_time_s))>1e-9||
     Math.abs(p.stop_s-Math.min(window.duration_s,e.resolved_time_s+e.duration_s))>1e-9||
     Math.abs(p.source_offset_s-(p.start_s-e.resolved_time_s))>1e-9)throw Error('Stale event projection');
  return e;
 });
}

export function windowGain(sceneTime:number,duration:number){
 return sceneTime<0||sceneTime>=duration?0:Math.min(1,(duration-sceneTime)/.01);
}

/** Apply to a dedicated output bus, separate from user gain/mute automation. */
export function scheduleWindowFade(param:{cancelScheduledValues:(t:number)=>unknown;setValueAtTime:(v:number,t:number)=>unknown;linearRampToValueAtTime:(v:number,t:number)=>unknown},
 duration:number,anchorAudio:number,anchorScene:number,now:number){
 const end=anchorAudio+duration-anchorScene;
 const sceneNow=anchorScene+Math.max(0,now-anchorAudio);
 param.cancelScheduledValues(now);
 param.setValueAtTime(windowGain(sceneNow,duration),now);
 if(end>now){
  if(end-.01>now)param.setValueAtTime(1,end-.01);
  param.linearRampToValueAtTime(0,end);
 }
 return end;
}
