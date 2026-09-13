import React,{useEffect,useRef,useState} from 'react';
import {inspectImport,listImports,saveImport,removeImport,durationLabel,type Entry,type VideoItem,type ImportedVideo} from './catalog';
import './library.css';

function Preview({item,record}:{item:VideoItem;record?:ImportedVideo}){
 const [url,setURL]=useState(item.video);
 useEffect(()=>{if(!record)return;const next=URL.createObjectURL(record.media);setURL(next);return()=>URL.revokeObjectURL(next);},[record]);
 return <video src={url?url+'#t=1':undefined} preload="metadata" muted playsInline tabIndex={-1} aria-hidden="true"/>;
}

export function Library({renderPlayer}:{renderPlayer:(entries:Entry[],record:ImportedVideo|undefined,back:()=>void)=>React.ReactNode}){
 const [videos,setVideos]=useState<VideoItem[]>([]),[imports,setImports]=useState<ImportedVideo[]>([]),[query,setQuery]=useState('');
 const [chosen,setChosen]=useState<VideoItem|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState(''),[loading,setLoading]=useState(true),[adding,setAdding]=useState(false),[showImport,setShowImport]=useState(false);
 const [sidecar,setSidecar]=useState<File|null>(null),[media,setMedia]=useState<File|null>(null),[filter,setFilter]=useState('all');
 const form=useRef<HTMLFormElement>(null),heading=useRef<HTMLHeadingElement>(null);
 useEffect(()=>{let active=true;
  void Promise.allSettled([fetch('/library/catalog.json').then(async r=>{if(!r.ok)throw Error('Build the video catalog with npm run build or npm run dev.');const d=await r.json();if(d.version!=='video-library-1'||!Array.isArray(d.videos))throw Error('The video catalog could not be read.');return d;}),listImports()]).then(([catalog,local])=>{
   if(!active)return;if(catalog.status==='fulfilled'){setVideos(catalog.value.videos);if(catalog.value.issues.length)setNotice('Some prepared entries are unavailable. The remaining videos are ready to browse.');}else setError(String(catalog.reason));
   if(local.status==='fulfilled')setImports(local.value);else setNotice('Local browser storage is unavailable. Prepared videos remain available.');setLoading(false);
  });return()=>{active=false;};
 },[]);
 async function add(event:React.FormEvent){event.preventDefault();if(!sidecar||!media)return;setAdding(true);setError('');try{
  const record=await inspectImport(sidecar,media);await saveImport(record);setImports(await listImports());setNotice(`${record.item.title} added to this browser’s library.`);setShowImport(false);setSidecar(null);setMedia(null);form.current?.reset();
 }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setAdding(false);}}
 async function remove(id:string){setError('');try{await removeImport(id);setImports(await listImports());setNotice('Removed the browser copy. Your original files are unchanged.');}catch(e){setError(String(e));}}
 const all=[...videos,...imports.map(r=>r.item)],shown=all.filter(v=>(filter!=='imported'||v.source==='imported')&&`${v.title} ${v.label} ${v.entries.map(e=>e.composition).join(' ')}`.toLowerCase().includes(query.toLowerCase()));
 if(chosen)return <React.Fragment key={chosen.id}>{renderPlayer(chosen.entries,imports.find(r=>r.id===chosen.id),()=>{setChosen(null);requestAnimationFrame(()=>heading.current?.focus());})}</React.Fragment>;
 return <main className="library"><header><div><span className="eyebrow">ANIMATION & SOUND</span><h1>SceneScore<span className="dot">.</span></h1></div><span className="library-local">Live music · local playback</span></header>
  <section aria-labelledby="library-title"><div className="library-intro"><div><h2 id="library-title" tabIndex={-1} ref={heading}>Video library</h2><p>Choose an animation. Hear its music and every contact.</p></div><button className="primary" aria-expanded={showImport} onClick={()=>setShowImport(!showImport)}>＋ Add video bundle</button></div>
   {showImport&&<form className="import-form" ref={form} onSubmit={e=>void add(e)}><div><h3>Add an animation</h3><p>Choose the MP4 and its prepared SceneScore JSON sidecar, containing the Blender scene, score and effects. Files stay on this device.</p></div><label>Blender video · MP4<input type="file" accept="video/mp4,.mp4" required disabled={adding} onChange={e=>setMedia(e.target.files?.[0]??null)}/></label><label>Prepared sidecar · JSON<input type="file" accept="application/json,.json" required disabled={adding} onChange={e=>setSidecar(e.target.files?.[0]??null)}/></label><div className="import-actions"><span>Up to 2 minutes · 256 MB video · 32 MB JSON</span><button className="primary" disabled={adding||!sidecar||!media}>{adding?'Checking & saving…':'Add to library'}</button></div></form>}
   {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status" className="library-notice">{notice}</p>}
   <div className="library-toolbar"><div role="group" aria-label="Video source"><button aria-pressed={filter==='all'} onClick={()=>setFilter('all')}>All videos <span>{all.length}</span></button><button aria-pressed={filter==='imported'} onClick={()=>setFilter('imported')}>On this device <span>{imports.length}</span></button></div><label className="library-search"><span className="sr-only">Search videos</span><input type="search" placeholder="Search animations…" value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
   {loading?<p className="library-empty" role="status">Loading your video library…</p>:shown.length?<div className="video-grid">{shown.map((item,index)=><article className="video-item" key={item.id} style={{animationDelay:`${Math.min(index,5)*45}ms`}}><button className="video-open" onClick={()=>setChosen(item)} aria-label={`Watch ${item.title}`}><div className="video-preview"><Preview item={item} record={imports.find(r=>r.id===item.id)}/><span className="video-play">▶ <span>Watch & listen</span></span><span className="video-duration">{durationLabel(item.duration)}</span></div><div className="video-title"><h3>{item.title}</h3><span>↗</span></div><p className="video-subtitle">{item.entries.length} soundtrack{item.entries.length===1?'':'s'} · Music + effects</p></button><div className="video-provenance"><span>{item.source==='imported'?'ON THIS DEVICE · ':''}{item.label.replaceAll('_',' ')}</span>{item.source==='imported'&&<button onClick={()=>void remove(item.id)} aria-label={`Remove browser copy of ${item.title}`}>Remove copy</button>}</div></article>)}</div>:<div className="library-empty"><h3>{query?'No matching animations':'Your library is ready for a video'}</h3><p>{query?'Try another title or clear your search.':'Add an MP4 with its prepared scene sidecar to watch and listen.'}</p>{query&&<button onClick={()=>setQuery('')}>Clear search</button>}</div>}
  </section><footer><span>ORIGINAL SCORES · BROWSER AUDIO</span><span>Draft soundtracks · audition pending</span></footer></main>;
}
