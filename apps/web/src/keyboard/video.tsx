import React,{useEffect,useRef,useState} from 'react';
import type {KeyboardPlayer} from './player';
import {KeyboardVideoSync} from './video-sync';

export function KeyboardVideo({player,url,onReady,onError}:{player:KeyboardPlayer;url:string;onReady:(ready:boolean)=>void;onError:(message:string)=>void}){
 const video=useRef<HTMLVideoElement>(null),[drift,setDrift]=useState(0);
 const ready=(element:HTMLVideoElement)=>{
  if(!Number.isFinite(element.duration)||Math.abs(element.duration-player.loopDuration)>.05){player.stop();onReady(false);onError('Video duration does not match the scene preset. Reload the C video preset.');return;}
  onReady(element.readyState>=2);
 };
 useEffect(()=>{
  const element=video.current!;onReady(false);
  const sync=new KeyboardVideoSync(element,message=>{player.stop();onError(message);});
  let frame=0,lastRead=0;
  const tick=(now:number)=>{
   const elapsed=player.running&&player.context?player.context.currentTime-player.anchor:player.duration;
   sync.update(player.running,elapsed,player.loopDuration);
   if(now-lastRead>250){setDrift(sync.driftMs);lastRead=now;}
   frame=requestAnimationFrame(tick);
  };
  frame=requestAnimationFrame(tick);
  return()=>{cancelAnimationFrame(frame);sync.pause();};
 },[player,url,onReady,onError]);
 return <div className="video-preview">
  <video ref={video} src={url} muted playsInline loop preload="auto" aria-label="C video synchronized to the piano and guitar"
   onLoadedMetadata={e=>ready(e.currentTarget)}
   onLoadedData={e=>ready(e.currentTarget)} onCanPlay={e=>ready(e.currentTarget)}
   onError={()=>{player.stop();onReady(false);onError('C video could not load. Reload the page or switch to the original sketch.');}}/>
  <div className="video-caption"><span>C.mp4 · 10 fps API analysis · editable proposals</span><span>{player.running?`Video/audio offset ${Math.round(drift)} ms`:'Video follows the Play / Stop button'}</span></div>
 </div>;
}
