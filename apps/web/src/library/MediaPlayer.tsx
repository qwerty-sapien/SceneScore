import React,{useEffect,useRef,useState} from 'react';
import {sha} from '../../../../packages/audio/model';
import type {VideoItem} from './catalog';

/** Original rendered media only. Never invent a live score or scene effects. */
export function MediaPlayer({item,onBack}:{item:VideoItem;onBack:()=>void}){
 const [url,setURL]=useState(''),[error,setError]=useState('');
 const video=useRef<HTMLVideoElement>(null);
 useEffect(()=>{const abort=new AbortController();let active=true,objectURL='';
  void (async()=>{try{
   const response=await fetch(item.video,{signal:abort.signal});if(!response.ok)throw Error('This rendered video is unavailable.');
   const bytes=await response.arrayBuffer();if(await sha(bytes)!==item.video_sha256)throw Error('Rendered video hash mismatch. Rebuild the catalog.');
   if(!active)return;objectURL=URL.createObjectURL(new Blob([bytes],{type:'video/mp4'}));setURL(objectURL);
  }catch(e){if(active)setError(String(e));}})();
  return()=>{active=false;abort.abort();video.current?.pause();if(objectURL)URL.revokeObjectURL(objectURL);};
 },[item]);
 useEffect(()=>{const element=video.current;return()=>{element?.pause();};},[url]);
 const hasAudio=item.audio==='embedded';
 return <main className="library rendered-player"><button className="back-library" onClick={()=>{video.current?.pause();onBack();}}>← Video library</button>
  <div className="section-line"><h2>{item.title}</h2><span>{item.label}</span></div>
  <p className="media-kind">{hasAudio?'Original rendered audio · not live synthesis':'Silent render · live soundtrack not prepared'}</p>
  {error?<p role="alert" className="error">{error}</p>:!url?<p role="status">Checking the original video…</p>:<video ref={video} src={url} controls playsInline preload="metadata" muted={!hasAudio} onLoadedMetadata={e=>{e.currentTarget.volume=.5;}} onError={()=>setError('This video could not be decoded by the browser.')} />}
  <p className="hint">{hasAudio?'This plays the audio already mixed into the original MP4. Music and effects cannot be separated here.':'This MP4 has no audio track and no prepared, matched live-score bundle. It is available to watch; no unrelated backing track or invented sound effects are substituted.'}</p>
  {url&&<a href={url} download={item.sourcePaths?.[0].split('/').at(-1)??'animation.mp4'}>Download original MP4</a>}
  <details><summary>Source files · {item.sourcePaths?.length??1} exact {item.sourcePaths?.length===1?'copy':'copies'}</summary><ul>{item.sourcePaths?.map(p=><li key={p}>{p}</li>)}</ul></details>
 </main>;
}
