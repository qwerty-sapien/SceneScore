export type VideoTarget={currentTime:number;paused:boolean;seeking:boolean;readyState:number;playbackRate:number;play:()=>Promise<void>;pause:()=>void};
// Audio owns elapsed time. Video follows it; no video callback advances music.
export class KeyboardVideoSync{
 private playing=false;private playPending=false;private generation=0;private previousCycle=-1;
 driftMs=0;
 constructor(private video:VideoTarget,private onError:(message:string)=>void){}
 update(running:boolean,elapsed:number,duration:number){
  if(!running||elapsed<0){this.pause();if(elapsed<=0&&this.video.currentTime!==0)this.video.currentTime=0;return;}
  this.playing=true;
  if(this.video.readyState<2)return;
  const cycle=Math.floor(elapsed/duration),target=elapsed%duration;
  this.driftMs=(this.video.currentTime-target)*1000;
  if(!this.video.seeking&&(cycle!==this.previousCycle||Math.abs(this.driftMs)>100))this.video.currentTime=target;
  this.previousCycle=cycle;
  this.video.playbackRate=Math.abs(this.driftMs)>25&&Math.abs(this.driftMs)<=100?(this.driftMs>0?.97:1.03):1;
  if(this.video.paused&&!this.playPending){
   const generation=this.generation;this.playPending=true;
   void this.video.play().then(()=>{if(!this.playing)this.video.pause();}).catch(error=>{
    if(generation===this.generation&&this.playing)this.onError(`Video playback failed: ${String(error)}`);
   }).finally(()=>{this.playPending=false;});
  }
 }
 pause(){if(this.playing){this.generation++;this.playing=false;}this.previousCycle=-1;this.video.pause();this.video.playbackRate=1;}
}
