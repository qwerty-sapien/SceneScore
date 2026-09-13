import {sha,stable,verifyBundle,type Bundle} from '../../../../packages/audio/model';
import {Timeline} from '../../../../packages/audio/transport';
import {polyphony} from '../../../../packages/audio/mix';

export type Entry={id:string;title:string;variant:string;groove:string;url:string;sha256:string;arrangement?:string;composition?:string;video?:string};
export type VideoItem={id:string;title:string;duration:number;video:string;label:string;source:'prepared'|'imported';entries:Entry[]};
export type ImportedVideo={id:string;raw:string;media:Blob;item:VideoItem;added:number};
export const MAX_JSON_BYTES=32*1024*1024,MAX_VIDEO_BYTES=256*1024*1024;
export const MAX_LIBRARY_BYTES=512*1024*1024,MAX_IMPORTS=12;
export const soundtrackName=(entry:Entry)=>`${entry.composition??entry.title} · ${entry.arrangement==='guitar'?'Guitar + piano':entry.arrangement==='vibraphone'?'Vibraphone':entry.arrangement==='prepared transitions'?'Prepared transitions':'Piano'} · ${entry.groove==='brush_swing_light_v1'?'Light swing':entry.groove==='brush_ballad_sparse_v1'?'Sparse brush':entry.groove==='brush_straight_rag_v1'?'Straight rag':entry.groove}`;
export const durationLabel=(seconds:number)=>`${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;

/** Accept prepared sidecars only. External paths in imported JSON are never fetched. */
export async function inspectImport(sidecar:Blob,media:Blob){
 if(!sidecar.size||sidecar.size>MAX_JSON_BYTES)throw Error('Choose a prepared sidecar JSON under 32 MB.');
 if(!media.size||media.size>MAX_VIDEO_BYTES)throw Error('Choose a matching MP4 under 256 MB.');
 let b:Bundle;const raw=await sidecar.text();
 try{b=JSON.parse(raw);}catch{throw Error('The sidecar is not valid JSON.');}
 if(b?.version!=='studio-bundle-1'||!Array.isArray(b.events)||!Array.isArray(b.states)||!Array.isArray(b.interactions)||!b.scene||!b.composition||!b.groove)
  throw Error('Choose a prepared SceneScore sidecar (studio-bundle-1) containing the Blender scene, score and effects.');
 const p=await verifyBundle(b,await media.arrayBuffer());
 // Imported files have no trusted catalog checksum. Require exact source bindings.
 const check=async(bytes:string|undefined,expected:string,value:unknown,label:string)=>{
  if(!bytes||await sha(new TextEncoder().encode(bytes))!==expected||stable(JSON.parse(bytes))!==stable(value))throw Error(`${label} is missing its matching source bytes. Re-prepare this sidecar.`);
 };
 await check(b.events_bytes??b.source_events_bytes,b.events_sha256,b.events,'Score');
 const sort=(a:{id:string},c:{id:string})=>a.id<c.id?-1:a.id>c.id?1:0;
 const scene={scene:b.scene,states:[...b.states].sort(sort),interactions:[...b.interactions].sort(sort),
  ...(b.role_supplement==null?{}:{role_supplement:b.role_supplement}),...(b.playback_policy==null?{}:{playback_policy:b.playback_policy}),
  ...(b.music_handoff_binding==null?{}:{music_handoff_binding:b.music_handoff_binding})};
 await check(b.scene_input_bytes,b.scene_hash,scene,'Scene');
 if(b.composition_input_bytes)await check(b.composition_input_bytes,b.composition_hash,{composition:b.composition,groove:b.groove},'Composition');
 // Legacy Python bundles bind the composition with their sorted JSON serializer.
 else if(await sha(new TextEncoder().encode(stable({composition:b.composition,groove:b.groove})+'\n'))!==b.composition_hash)
  throw Error('Composition is missing its matching source bytes. Re-prepare this sidecar.');
 polyphony(b.events);new Timeline(b,p,b.plan_sha256);
 const digest=await sha(new TextEncoder().encode(raw)),id='import-'+digest;
 const entry:Entry={id,title:b.title,variant:b.variant,groove:b.groove.id,url:'',sha256:digest,
  arrangement:b.sound_design?.lead??(b.music_vertical?'prepared transitions':'piano'),composition:b.composition.title};
 const item:VideoItem={id,title:b.title,duration:b.scene.duration_s,video:'',label:b.animation_label??b.source,source:'imported',entries:[entry]};
 return {id,raw,media,item,added:Date.now()} satisfies ImportedVideo;
}

const DB='scenescore-video-library';
async function database(){return new Promise<IDBDatabase>((resolve,reject)=>{
 const request=indexedDB.open(DB,1);
 request.onupgradeneeded=()=>request.result.createObjectStore('videos',{keyPath:'id'});
 request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(Error('Browser storage is unavailable.'));
 });}
async function transaction<T>(mode:IDBTransactionMode,operation:(store:IDBObjectStore)=>IDBRequest<T>){
 const db=await database();try{return await new Promise<T>((resolve,reject)=>{
  const tx=db.transaction('videos',mode),request=operation(tx.objectStore('videos'));
  tx.oncomplete=()=>resolve(request.result);tx.onabort=()=>reject(tx.error??Error('Browser storage could not save this video.'));
  tx.onerror=()=>reject(tx.error??Error('Browser storage is full or unavailable.'));
 });}finally{db.close();}
}
export const listImports=()=>transaction<ImportedVideo[]>('readonly',s=>s.getAll());
export async function saveImport(record:ImportedVideo){
 const existing=await listImports(),others=existing.filter(x=>x.id!==record.id);
 const size=(r:ImportedVideo)=>new Blob([r.raw]).size+r.media.size;
 if(others.length>=MAX_IMPORTS||others.reduce((n,r)=>n+size(r),size(record))>MAX_LIBRARY_BYTES)throw Error('This library is full (12 imports / 512 MB). Remove an imported copy to make space.');
 await transaction('readwrite',s=>s.put(record));
}
export const removeImport=(id:string)=>transaction('readwrite',s=>s.delete(id));
