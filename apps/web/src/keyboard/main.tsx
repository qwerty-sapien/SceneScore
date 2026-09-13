import React,{useEffect,useMemo,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {KeyboardPlayer} from './player';
import {SCORE,keyName,type Ornament,type Touch} from '../../../../packages/audio/keyboard-score';
import {renderOffline,pcmWav,measurements} from '../../../../packages/audio/engine';
import {LOOP,SCENE_EVENTS,compileTimedDuet} from '../../../../packages/audio/keyboard-scenes';
import {KeyboardVideo} from './video';
import cVideo from './assets/c-video.json';
import cVideoUrl from './assets/C.mp4?url';
import './style.css';

const ornaments:{id:Ornament;key:string;title:string;description:string;glyph:string}[]=[
 {id:'plain',key:'Q',title:'Plain',description:'Let the original phrase breathe.',glyph:'● ─ ●'},
 {id:'grace',key:'W',title:'Grace note',description:'A quick chromatic step into each note.',glyph:'·↗ ●'},
 {id:'turn',key:'E',title:'Turn',description:'Circle above and below the melody.',glyph:'∿'},
 {id:'trill',key:'R',title:'Trill',description:'Alternate the note and its upper neighbor.',glyph:'≋'},
];
const touches:{id:Touch;key:string;title:string}[]=[{id:'detached',key:'A',title:'Detached'},{id:'staccato',key:'S',title:'Staccato'},{id:'legato',key:'D',title:'Legato'}];
function save(data:BlobPart,name:string,type:string){const url=URL.createObjectURL(new Blob([data],{type}));const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function App(){
 const playerRef=useRef<KeyboardPlayer|null>(null);
 if(!playerRef.current){playerRef.current=new KeyboardPlayer();playerRef.current.loadScene(cVideo.duration_s,cVideo.markers,cVideo);}
 const player=playerRef.current;
 const [,update]=useState(0),[error,setError]=useState(''),[exporting,setExporting]=useState(false),[renderInfo,setRenderInfo]=useState('');
 const [videoMode,setVideoMode]=useState(true),[videoReady,setVideoReady]=useState(false);
 const loop=player.loopDuration;
 const running=player.running,time=player.now(),bar=Math.floor(time/player.barDuration),beat=Math.floor(time/player.beatDuration)%4;
 const settings=player.settings;
 const preview=useMemo(()=>compileTimedDuet(0,loop,player.markers,[{at:0,settings}],player.configHash,loop),[player.markers,settings.transpose,settings.touch,settings.ornament,player.configHash,loop]);
 const hover=useRef<number|null>(null),[cursor,setCursor]=useState<number|null>(null);
 const [notice,setNotice]=useState('');
 function insertScene(kind:number){const at=hover.current??time%loop;player.addScene(kind,at);setNotice(player.markers.length>=64?'Timeline full · remove an event to add another.':`${SCENE_EVENTS[kind].name} added at ${at.toFixed(2)}s${player.running?' · passage updated':''}`);}
 function selectScene(useVideo:boolean){if(running||player.starting||exporting)return;player.loadScene(useVideo?cVideo.duration_s:LOOP,useVideo?cVideo.markers:[],useVideo?cVideo:null);setVideoMode(useVideo);hover.current=null;setCursor(null);setError('');setRenderInfo('');setNotice(useVideo?'C video proposals restored. You can edit every marker.':'Original sketch loaded.');}
 async function toggle(){if(exporting)return;if(player.running||player.starting){player.stop();return;}try{if(videoMode&&!videoReady){setError('Wait for the video to load, or switch to the original sketch.');return;}setError('');setRenderInfo('');await player.start();}catch(e){player.stop();setError(String(e));}}
 useEffect(()=>{player.onUpdate=()=>update(n=>n+1);player.onError=setError;return()=>{player.onUpdate=()=>{};player.onError=()=>{};void player.close();};},[player]);
 useEffect(()=>{
  const keydown=(event:KeyboardEvent)=>{
   if(event.repeat||event.ctrlKey||event.metaKey||event.altKey||exporting)return;
   if(event.target instanceof HTMLElement&&(event.target.isContentEditable||['INPUT','SELECT','TEXTAREA'].includes(event.target.tagName)))return;
   const key=event.key.toLowerCase();
   if(key===' '){if(event.target instanceof HTMLElement && ['BUTTON','A'].includes(event.target.tagName))return;event.preventDefault();void toggle();return;}
   if(/^[1-7]$/.test(key)){event.preventDefault();if(hover.current!==null)insertScene(Number(key)-1);else setNotice('Hover over the playback bar, then press 1–7.');return;}
   const action=({q:'plain',w:'grace',e:'turn',r:'trill',a:'detached',s:'staccato',d:'legato',arrowup:'keyUp',arrowdown:'keyDown'} as const)[key as 'q'];
   if(action){event.preventDefault();player.change(action);}
  };
  window.addEventListener('keydown',keydown);return()=>window.removeEventListener('keydown',keydown);
 },[exporting,videoMode,videoReady,loop]);
 async function exportWav(){setExporting(true);setError('');try{const buffer=await renderOffline(player.events,player.duration,player.takeGainDb);const stats=measurements(buffer);save(pcmWav(buffer),videoMode?'C-little-signals-DRAFT.wav':'little-signals-DRAFT.wav','audio/wav');setRenderInfo(`${stats.sample_rate} Hz · peak ${stats.peak.toFixed(3)} · ${stats.clipped} clipped samples`);}catch(e){setError(String(e));}finally{setExporting(false);}}
 const canExport=!running&&!player.starting&&player.events.length>0&&player.duration>.1;
 const latest=player.events.filter(e=>e.lane_id==='guitar'&&e.resolved_time_s<=time&&e.resolved_time_s+e.duration_s>time).at(-1);
 return <main>
  <header><a href="/">SceneScore<span> / PLAYGROUND</span></a><span className="badge"><i/> {videoMode?'Video + keyboard':'Keyboard + mouse'}</span></header>
  <section className="intro"><div className="eyebrow">INPUT → EXPRESSION → MUSIC</div><h1>A little input.<br/><em>A different phrase.</em></h1><p>Play the video with an original piano/guitar sketch. Hover over the playback bar<br className="desktop"/> and press 1–7 to add a scene event. Edit the piano and guitar passages while they play.</p></section>
  <section className="scene-choice" aria-label="Scene selection"><button aria-pressed={videoMode} disabled={running||player.starting||exporting} onClick={()=>selectScene(true)}>C video + music</button><button aria-pressed={!videoMode} disabled={running||player.starting||exporting} onClick={()=>selectScene(false)}>Original sketch</button><span>{videoMode?`${player.markers.length} markers · API proposals + your edits`:'Manual scene markers'}</span></section>
  <section className="deck" aria-label="Music transport">
   {videoMode&&<KeyboardVideo player={player} url={cVideoUrl} onReady={setVideoReady} onError={setError}/> }
   <div className="track"><div className={`record ${running?'spinning':''}`}><span>SS</span></div><div><div className="eyebrow">{videoMode?'FOUR BARS FIT TO C VIDEO':'ORIGINAL FOUR-BAR LOOP'}</div><h2>{videoMode?'Little Signals × C':'Little Signals'}</h2><p>Piano accompaniment · fingerstyle guitar melody</p></div><span className="tempo">{(60/player.beatDuration).toFixed(videoMode?1:0)} <small>BPM / 4:4 SWING</small></span></div>
   <div className="transport"><button className="play" disabled={exporting||player.starting||(videoMode&&!videoReady&&!running)} onClick={()=>void toggle()}>{running?'■ Stop take':videoMode?(videoReady?'▶ Play video + music':'Loading video…'):'▶ Play sketch'} <kbd>SPACE</kbd></button><div className="beats" aria-label={`Bar ${bar+1}, beat ${beat+1}`}>{[0,1,2,3].map(n=><span key={n} className={running&&n===beat?'lit':''}>{n+1}</span>)}</div><span className="clock">{(time%loop).toFixed(1)}<small> / {loop.toFixed(2)}s · LOOP</small></span></div>
   <div className="timeline-heading"><span>SCENE EVENTS · FOUR-BAR LOOP</span><span>{cursor===null?'Hover + press 1–7':`Insert at ${cursor.toFixed(2)}s`}</span></div>
   <div className="scene-timeline" tabIndex={0} aria-label="Scene event timeline. Hover and press 1 through 7 to insert. Left and right arrows select a position when focused."
    onPointerMove={e=>{const box=e.currentTarget.getBoundingClientRect();const at=Math.max(0,Math.min(loop-.001,(e.clientX-box.left)/box.width*loop));hover.current=at;setCursor(at);}}
    onPointerLeave={()=>{hover.current=null;setCursor(null);}}
    onFocus={()=>{hover.current??=time%loop;setCursor(hover.current);}}
    onBlur={()=>{hover.current=null;setCursor(null);}}
    onKeyDown={e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();hover.current=Math.max(0,Math.min(loop-.001,(hover.current??0)+(e.key==='ArrowRight'?.125:-.125)));setCursor(hover.current);}}}>
    {[0,1,2,3].map(n=><div className="bar-grid" key={n} style={{left:`${n*25}%`}}><span>BAR {n+1}</span></div>)}
    {['piano','guitar'].map((lane,index)=><div className={`music-lane lane-${lane}`} key={lane} style={{top:`${28+index*46}px`}}><span className="lane-name">{lane.toUpperCase()}</span>{preview.filter(e=>e.lane_id===lane).map(e=><span className={`music-note ${e.phrasing.startsWith('scene-replacement')?'replaced':''}`} key={e.id} title={`${lane} · MIDI ${e.midi_pitch} · ${e.phrasing}`} style={{left:`${e.resolved_time_s/loop*100}%`,width:`${e.duration_s/loop*100}%`,bottom:`${4+((e.midi_pitch??48)%12)*1.6}px`}}/>)}</div>)}
    {player.markers.map(m=><button className={`scene-marker event-${m.kind}`} key={m.id} style={{left:`${m.at/loop*100}%`,top:`${126+m.kind*19}px`}} title={`${SCENE_EVENTS[m.kind].name} · ${m.at.toFixed(2)}s · click to remove`} aria-label={`Remove ${SCENE_EVENTS[m.kind].name} at ${m.at.toFixed(2)} seconds`} disabled={exporting} onClick={()=>player.removeScene(m.id)}>{m.kind+1}</button>)}
    {cursor!==null&&<div className="insert-cursor" style={{left:`${cursor/loop*100}%`}}/>}
    <div className="playhead" style={{left:`${time%loop/loop*100}%`}}><span/></div>
   </div>
   <div className="timeline-heading"><span>0:00</span><span>{loop.toFixed(2)} seconds · repeats continuously</span></div>
   <div className="scene-palette">{SCENE_EVENTS.map((event,kind)=><button key={event.name} disabled={exporting||player.starting||player.markers.length>=64} onClick={()=>insertScene(kind)} title={`${event.effect} · add at cursor or playhead`}><kbd>{kind+1}</kbd><span>{event.name}<small>{event.effect}</small></span></button>)}</div>
   <div className="timeline-tools">{videoMode&&<button disabled={running||player.starting||exporting} onClick={()=>selectScene(true)}>Restore API markers</button>}<p>Hover + 1–7 to place · click a marker to remove · buttons add at the playhead</p><button disabled={exporting||!player.markers.length} onClick={()=>{player.clearScenes();setNotice('Scene events cleared.');}}>Clear events</button></div>
   <p className="scene-notice" role="status">{notice||'Passage replacements · approach starts 2 beats early; near miss pauses the preceding half beat.'}</p>
   <div className="deck-bottom"><span>{running?`Playing · phrase ${Math.floor(bar/4)+1} · bar ${bar%4+1}`:'Ready when you are'} {latest?`· MIDI ${latest.midi_pitch}`:''}</span><span>Draft audition</span></div>
  </section>
  <section className="controls"><div className="section-title"><h2>01 <span>Ornament the guitar</span></h2><p>Replaces the current guitar passage</p></div><div className="ornaments">{ornaments.map(o=><button key={o.id} className={`ornament ${settings.ornament===o.id?'selected':''}`} aria-pressed={settings.ornament===o.id} disabled={exporting} onClick={()=>player.change(o.id)}><div className="card-top"><span className="glyph">{o.glyph}</span><kbd>{o.key}</kbd></div><h3>{o.title}</h3><p>{o.description}</p><span className="selection">{settings.ornament===o.id?'● SELECTED':'○ SELECT'}</span></button>)}</div></section>
  <div className="lower"><section className="panel"><div className="section-title"><h2>02 <span>Change the touch</span></h2></div><p>Short and clipped, or held with a softer connection.</p><div className="touches">{touches.map(t=><button key={t.id} aria-pressed={settings.touch===t.id} className={settings.touch===t.id?'selected':''} disabled={exporting} onClick={()=>player.change(t.id)}>{t.title}<kbd>{t.key}</kbd></button>)}</div><p className="note">Guitar only · piano accompaniment stays steady</p></section>
  <section className="panel"><div className="section-title"><h2>03 <span>Move the key</span></h2><strong className="key">{keyName(settings.transpose)}</strong></div><p>Shift the pitched parts by two semitones at the next bar.</p><div className="key-buttons"><button disabled={exporting} onClick={()=>player.change('keyDown')}>−2 semitones <kbd>↓</kbd></button><button disabled={exporting} onClick={()=>player.change('keyUp')}>+2 semitones <kbd>↑</kbd></button></div><p className="note" role="status">{player.pendingKey!==null?`Queued → ${keyName(player.pendingKey)} · next bar`:'Gain and articulation are preserved · range ±12 semitones'}</p></section></div>
  <section className="take"><div><h2>Your take, kept editable.</h2><p>Playback loops until stopped. Export captures the first 120 seconds; scene markers remain for the next take.</p></div><div className="exports"><button disabled={!canExport||exporting} onClick={()=>void exportWav()}>{exporting?'Rendering…':'↓ Audio WAV'}</button><button disabled={!canExport||exporting} onClick={()=>save(JSON.stringify({version:'keyboard-take-1',approval:null,audition_status:'AUDITION_PENDING',input_mode:'keyboard_or_mouse',planning_mode:'manual_plan',score:{...SCORE,bpm:60/player.beatDuration},duration_s:player.duration,gain_db:player.takeGainDb,initial_settings:player.initialSettings,config_hash:player.configHash,events:player.events,scene_markers:player.markers,scene_mode:videoMode?'api_proposals_with_keyboard_edits':'manual_keyboard_events',scene_source:player.sourceIdentity,loop_duration_s:loop,controls:player.actions},null,2),videoMode?'C-little-signals-DRAFT.json':'little-signals-DRAFT.json','application/json')}>↓ Editable track</button></div></section>
  <details><summary>Recent inputs & playback details</summary><label>Master level <input type="range" min="-24" max="-6" step="1" value={player.gainDb} disabled={running||exporting||player.starting} onChange={e=>{player.gainDb=+e.target.value;update(n=>n+1);}}/> {player.gainDb} dB · set before a take</label><p>Ornaments and touch update the guitar passage with a short crossfade. Key changes use the next unscheduled bar. The timeline repeats every four bars{videoMode?', matched to the 6.37-second video':''}. Edits replace the affected passages; future passages change when reached. Approach begins two beats before its marker; near miss silences both tracks for the preceding half beat. Other effects last two beats. Overlaps favor near-miss silence, then the newest marker. Key changes retune both parts at the next bar. {videoMode?'C markers come from the API frame analysis you selected, with any local edits. Contact and release use the midpoint of the model’s onset bracket; approach lands at its interval end. These are musical choices, not precise physical measurements. Six responses overlap: newest-marker precedence can shorten earlier effects.':'These are manually placed audition effects.'} Exports synthesize the elapsed event track; they do not record your speakers.</p><ol>{player.actions.slice(-8).map((a,i)=><li key={i}>{a.at.toFixed(2)}s · {a.action}{a.effective_s!==null?` → ${a.effective_s.toFixed(2)}s`:''}</li>)}</ol></details>
  {renderInfo&&<p role="status">{renderInfo}</p>}{error&&<p className="error" role="alert">{error}</p>}
  <footer><span>SCENESCORE / LOCAL AUDIO EXPERIMENT</span><span>Original symbolic music · human audition pending</span></footer>
 </main>;
}
createRoot(document.getElementById('root')!).render(<App/>);
