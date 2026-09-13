import React,{useEffect,useRef,useState} from 'react';
import {sha} from '../../../../packages/audio/model';
import {createVideoScore,VideoMusicTransport,type VideoScore} from '../../../../packages/audio/video-accompaniment';
import type {VideoItem} from './catalog';

export function VideoAccompanimentPlayer({item,onBack}:{item:VideoItem;onBack:()=>void}){
 const [url,setURL]=useState(''),[score,setScore]=useState<VideoScore|null>(null),[error,setError]=useState(''),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[playing,setPlaying]=useState(false),[position,setPosition]=useState(0),[volume,setVolume]=useState(.35);
 const video=useRef<HTMLVideoElement>(null),music=useRef<VideoMusicTransport|null>(null),generation=useRef(0);
 function pause(){generation.current++;music.current?.pause();video.current?.pause();setPlaying(false);setBusy(false);setPosition(music.current?.now()??0);}
 useEffect(()=>{const abort=new AbortController();let alive=true,objectURL='';
  void (async()=>{try{
   const response=await fetch(item.video,{signal:abort.signal});if(!response.ok)throw Error('Video is unavailable.');
   const bytes=await response.arrayBuffer();if(await sha(bytes)!==item.video_sha256)throw Error('Video hash mismatch.');
   const draft=await createVideoScore(item.video_sha256!,item.duration,item.accompaniment?.seed??42);
   if(!alive)return;objectURL=URL.createObjectURL(new Blob([bytes],{type:'video/mp4'}));setURL(objectURL);setScore(draft);
  }catch(e){if(alive)setError(String(e));}})();
  return()=>{alive=false;generation.current++;abort.abort();video.current?.pause();void music.current?.close();if(objectURL)URL.revokeObjectURL(objectURL);};
 },[item]);
 useEffect(()=>{let frame=0;function tick(){const m=music.current,v=video.current;if(m?.playing&&v){const now=m.now();setPosition(now);if(now>=item.duration){pause();}else if(Math.abs(v.currentTime-now)>.10){v.currentTime=now;v.playbackRate=1;}else v.playbackRate=Math.abs(v.currentTime-now)>.025?(v.currentTime>now?.98:1.02):1;}frame=requestAnimationFrame(tick);}frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame);},[item.duration]);
 useEffect(()=>{const hide=()=>{if(document.hidden)pause();};document.addEventListener('visibilitychange',hide);return()=>document.removeEventListener('visibilitychange',hide);},[]);
 async function play(){if(!score||!video.current)return;const token=++generation.current;setBusy(true);setError('');
  try{if(!music.current){const context=new AudioContext();music.current=new VideoMusicTransport(context,score,volume);context.onstatechange=()=>{if(context.state==='suspended'&&music.current?.playing)pause();};}
   const m=music.current;await m.context.resume();if(token!==generation.current)return;
   const start=position>=item.duration-.03?0:position;m.play(start);video.current.currentTime=start;video.current.playbackRate=1;
   await new Promise(resolve=>setTimeout(resolve,Math.max(0,(m.anchorAudio-m.context.currentTime)*1000)));
   if(token!==generation.current)return;await video.current.play();if(token!==generation.current){video.current?.pause();return;}setPlaying(true);
  }catch(e){pause();setError(String(e));}finally{if(token===generation.current)setBusy(false);}
 }
 async function newTake(){if(!score)return;pause();const token=++generation.current;setBusy(true);try{
  const old=music.current;music.current=null;await old?.close();const draft=await createVideoScore(item.video_sha256!,item.duration,(score.seed+1)>>>0);
  if(token!==generation.current)return;setScore(draft);setPosition(0);if(video.current)video.current.currentTime=0;
 }catch(e){setError(String(e));}finally{if(token===generation.current)setBusy(false);}}
 function downloadScore(){if(!score)return;const link=document.createElement('a'),blob=URL.createObjectURL(new Blob([JSON.stringify(score,null,2)+'\n'],{type:'application/json'}));link.href=blob;link.download=item.title.replace(/[^a-z0-9]+/gi,'-')+'-live-piano-score.json';link.click();setTimeout(()=>URL.revokeObjectURL(blob),1000);}
 return <main className="library rendered-player"><button className="back-library" onClick={()=>{pause();onBack();}}>← Video library</button>
  <div className="section-line"><h2>{item.title}</h2><span>Live piano</span></div>
  <p className="media-kind">Original video-only accompaniment · draft audition</p>
  {error&&<p role="alert" className="error">{error}</p>}
  {!url?<p role="status">Preparing video and piano…</p>:<video ref={video} src={url} muted playsInline preload="metadata" onLoadedMetadata={e=>{if(Math.abs(e.currentTarget.duration-item.duration)>.04)setError('Video duration does not match this score.');else setReady(true);}} onEnded={pause} onError={()=>{pause();setError('The browser could not decode this video.');}}/>}
  <div className="video-music-controls"><button className="primary" disabled={!ready||!score||busy} onClick={()=>playing?pause():void play()}>{busy?'Preparing…':playing?'Pause':'Watch & listen'}</button><button disabled={!score||busy} onClick={()=>void newTake()}>New piano take</button><label>Volume<input aria-label="Piano volume" type="range" min="0" max="1" step=".01" value={volume} onChange={e=>{setVolume(+e.target.value);music.current?.volume(+e.target.value);}}/></label><span>{position.toFixed(1)} / {item.duration.toFixed(1)} s</span></div>
  <label className="video-music-seek">Seek<input aria-label="Seek video" type="range" min="0" max={item.duration} step={1/30} value={position} disabled={!ready||busy} onChange={e=>{pause();const next=+e.target.value;music.current?.seek(next);setPosition(next);if(video.current)video.current.currentTime=next;}}/></label>
  <p className="hint">A new piano score is generated in your browser for each take. This accompaniment uses the clip’s duration; it has no verified Blender motion or collision mapping.</p>
  <button disabled={!score} onClick={downloadScore}>Download editable piano score</button>
 </main>;
}
