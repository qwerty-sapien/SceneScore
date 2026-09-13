import type {ScoreEvent} from '../contracts/generated';
export type Lanes={soundtrack:boolean;foley:boolean};
export type MixPoint={scene_s:number;gain_db:number;muted:boolean;lanes:Lanes};
export function validateMix(points:MixPoint[],duration:number){
 if(!points.length||points.length>10000||points[0].scene_s!==0)throw Error('Mix needs a bounded origin snapshot');
 let previous=0;
 for(const p of points){if(!Number.isFinite(p.scene_s)||p.scene_s<previous||p.scene_s>duration||!Number.isFinite(p.gain_db)||p.gain_db< -36||p.gain_db>0||typeof p.muted!=='boolean'||typeof p.lanes.foley!=='boolean'||typeof p.lanes.soundtrack!=='boolean')throw Error('Invalid mix automation');previous=p.scene_s;}
}
export function amplitude(point:MixPoint,lane:keyof Lanes){return point.muted||!point.lanes[lane]?0:10**(point.gain_db/20);}
export function polyphony(events:ScoreEvent[],limit=24){
 const edges=events.flatMap(e=>[[e.resolved_time_s,1],[e.resolved_time_s+e.duration_s,-1]]);
 edges.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);let active=0,peak=0;
 for(const [,delta] of edges){active+=delta;peak=Math.max(peak,active);}
 if(peak>limit)throw Error('Voice polyphony budget');return peak;
}
export const stemFor=(e:ScoreEvent)=>e.event_type==='foley'?'foley':e.event_type==='brush'?'brush':e.instrument_id.includes('bass')?'bass':e.instrument_id==='guitar_fingerstyle_v1'?'guitar':e.instrument_id==='vibraphone_soft_v1'?'vibraphone':'piano';
export function stemsFor(events:ScoreEvent[]):ReturnType<typeof stemFor>[]{
 const pitched=events.some(e=>e.instrument_id==='guitar_fingerstyle_v1')?'guitar':events.some(e=>e.instrument_id==='vibraphone_soft_v1')?'vibraphone':'piano';
 return [pitched,'bass','brush','foley'];
}
