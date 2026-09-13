/** Build a small browse index from prepared public bundles; never render or score. */
import {createHash} from 'node:crypto';
import {existsSync,readFileSync,readdirSync,realpathSync,mkdirSync,writeFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {inspectVideoSources,videoTitle} from './video-inventory.mjs';

const publicRoot=realpathSync(fileURLToPath(new URL('../public',import.meta.url)));
const root=fileURLToPath(new URL('../../../',import.meta.url));
execFileSync(path.join(root,'.venv/bin/python'),['apps/web/tools/prepare_piano.py'],{cwd:root,env:{...process.env,PYTHONPATH:'.:src'},stdio:'inherit',timeout:120000});
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const inside=file=>{const resolved=realpathSync(file);if(!resolved.startsWith(publicRoot+path.sep))throw Error('Catalog asset outside public directory');return resolved;};
const url=file=>'/'+path.relative(publicRoot,file).split(path.sep).map(encodeURIComponent).join('/');
const seen=new Set(),groups=new Map(),issues=[];
const folders=readdirSync(publicRoot,{withFileTypes:true}).filter(d=>d.isDirectory()&&d.name!=='library')
 .map(d=>d.name).sort((a,b)=>(a==='studio'?-1:b==='studio'?1:a.localeCompare(b)));
for(const folder of folders){
 const catalog=path.join(publicRoot,folder,'catalog.json');if(!existsSync(catalog))continue;
 try{
  const index=JSON.parse(readFileSync(catalog,'utf8'));
  if(index.version==='rendered-video-catalog-1'){
   for(const item of index.videos){const file=inside(path.resolve(path.dirname(catalog),item.video));
    if(sha(readFileSync(file))!==item.video_sha256)throw Error('Rendered catalogue video hash mismatch');
    groups.set(item.video_sha256,{...item,id:item.video_sha256,video:url(file),entries:[]});
   }continue;
  }
  if(index.version!=='studio-catalog-1')continue;
  for(const entry of index.entries){try{
   const file=inside(path.resolve(path.dirname(catalog),entry.url)),raw=readFileSync(file),digest=sha(raw);
   if(digest!==entry.sha256)throw Error('Bundle hash mismatch');if(seen.has(digest))continue;
   const b=JSON.parse(raw),video=inside(path.resolve(path.dirname(file),b.video));
   if(b.version!=='studio-bundle-1'||sha(readFileSync(video))!==b.video_sha256)throw Error('Video hash mismatch');
   const id=b.video_sha256;
   const group=groups.get(id)??{id,title:b.title,duration:b.scene.duration_s,video:url(video),
    label:b.animation_label??b.source,source:'prepared',audio:'live',video_sha256:b.video_sha256,entries:[],sourcePaths:[]};
   group.entries.push({...entry,id:folder+':'+entry.id,url:url(file),video:url(video),
    arrangement:entry.arrangement??(b.music_vertical?'prepared transitions':'piano'),composition:b.composition.title});
   groups.set(id,group);seen.add(digest);
  }catch(error){issues.push({catalog:folder,entry:entry.id,reason:String(error)});}}
 }catch(error){issues.push({catalog:folder,reason:String(error)});}
}
mkdirSync(path.join(publicRoot,'library'),{recursive:true});
for(const group of groups.values())group.entries.sort((a,b)=>Number(b.arrangement==='clean-piano')-Number(a.arrangement==='clean-piano'));
const requested=readFileSync(path.join(root,'apps/web/video-sources.txt'),'utf8').trim().split(/\r?\n/);
const inventory=inspectVideoSources(path.join(root,'artifacts'),requested);
const mediaRoot=path.join(publicRoot,'library/media');mkdirSync(mediaRoot,{recursive:true});
for(const video of inventory.groups){
 let item=groups.get(video.sha256);
 if(!item){
  const target=path.join(mediaRoot,video.sha256+'.mp4');if(!existsSync(target)||sha(readFileSync(target))!==video.sha256){
   const raw=readFileSync(video.file);if(sha(raw)!==video.sha256)throw Error('Video changed during indexing; retry after its render finishes: '+video.file);
   writeFileSync(target,raw);
  }
  const naming=videoTitle(video.paths[0]);
  item={id:video.sha256,title:naming.title,duration:video.duration,video:url(target),video_sha256:video.sha256,
   label:naming.edition,source:'rendered',audio:video.hasAudio?'embedded':'silent',entries:[],sourcePaths:[]};
  groups.set(video.sha256,item);
 }
 item.sourcePaths=video.paths;
}
// Every silent render gets an explicitly video-only, original live piano score.
for(const item of groups.values()){
 if(item.entries.length){item.audio='live';delete item.accompaniment;}
 else if(item.audio==='silent'){
  item.audio='live';item.accompaniment={version:'video-accompaniment-2',seed:parseInt(item.video_sha256.slice(0,8),16)};
 }
}
issues.push(...inventory.issues);
const coverage={requested:requested.length,available:inventory.sources.filter(s=>s.requested&&s.status==='available').length,
 unique_videos:groups.size,live_scores:[...groups.values()].filter(v=>v.entries.length||v.accompaniment).length,
 original_audio:[...groups.values()].filter(v=>v.audio==='embedded').length,silent:[...groups.values()].filter(v=>v.audio==='silent').length};
writeFileSync(path.join(publicRoot,'library/catalog.json'),JSON.stringify({version:'video-library-1',videos:[...groups.values()],issues,coverage},null,2)+'\n');
writeFileSync(path.join(publicRoot,'library/coverage.json'),JSON.stringify({coverage,sources:inventory.sources,issues},null,2)+'\n');
console.log(`Video library: ${groups.size} videos, ${seen.size} soundtracks; ${coverage.available}/${coverage.requested} requested paths accounted for`);
for(const issue of issues)console.warn(issue);
