import {editableTarget} from './interaction';
import type {AutomaticStatus} from './types';

export class TapLabelController {
 private held=false;
 private queue:Promise<unknown>=Promise.resolve();
 constructor(private send:(value:{id:string;client_ms:number;run_id:string})=>Promise<unknown>,private saved:()=>void,private failed:(error:unknown)=>void,private clock=()=>performance.now(),private id=()=>crypto.randomUUID()){}
 down(event:{code:string;repeat:boolean;target:EventTarget|null;ctrlKey?:boolean;metaKey?:boolean;altKey?:boolean},status:AutomaticStatus|null){
  if(event.code!=='KeyB'||event.repeat||this.held||event.ctrlKey||event.metaKey||event.altKey||editableTarget(event.target)||!status?.run_id||!['learning','fitting','checking'].includes(status.phase))return false;
  this.held=true;
  const label={id:this.id(),client_ms:this.clock(),run_id:status.run_id};
  this.queue=this.queue.then(()=>this.send(label)).then(()=>this.saved()).catch(this.failed);
  return true;
 }
 up(code:string){if(code==='KeyB')this.held=false;}
 release(){this.held=false;}
 flush(){return this.queue;}
}

export function progressText(status:AutomaticStatus|null):string {
 if(!status)return 'Open Launch Blink Trainer.command, then press Train.';
 const mode=status.source_mode==='synthetic'?'Synthetic rehearsal · ':'';
 const measured=status.evaluation;
 const estimate=measured?` · B-label precision ${measured.precision===null?'—':(measured.precision*100).toFixed(1)+'%'} / recall ${measured.recall===null?'—':(measured.recall*100).toFixed(1)+'%'}${measured.complete?'':' (incomplete)'}`:status.checkpoint_id?' · Not yet evaluated':'';
 const collection=status.active?` · ${status.labels} labels · ${Math.floor(status.elapsed_s/60)}:${String(Math.floor(status.elapsed_s%60)).padStart(2,'0')}`:'';
 return mode+status.message+collection+estimate;
}
