/** Build a small browse index from prepared public bundles; never render or score. */
import {createHash} from 'node:crypto';
import {existsSync,readFileSync,readdirSync,realpathSync,mkdirSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const publicRoot=realpathSync(fileURLToPath(new URL('../public',import.meta.url)));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const inside=file=>{const resolved=realpathSync(file);if(!resolved.startsWith(publicRoot+path.sep))throw Error('Catalog asset outside public directory');return resolved;};
const url=file=>'/'+path.relative(publicRoot,file).split(path.sep).map(encodeURIComponent).join('/');
const seen=new Set(),groups=new Map(),issues=[];
const folders=readdirSync(publicRoot,{withFileTypes:true}).filter(d=>d.isDirectory()&&d.name!=='library')
 .map(d=>d.name).sort((a,b)=>(a==='studio'?-1:b==='studio'?1:a.localeCompare(b)));
for(const folder of folders){
 const catalog=path.join(publicRoot,folder,'catalog.json');if(!existsSync(catalog))continue;
 try{
  const index=JSON.parse(readFileSync(catalog,'utf8'));if(index.version!=='studio-catalog-1')continue;
  for(const entry of index.entries){try{
   const file=inside(path.resolve(path.dirname(catalog),entry.url)),raw=readFileSync(file),digest=sha(raw);
   if(digest!==entry.sha256)throw Error('Bundle hash mismatch');if(seen.has(digest))continue;
   const b=JSON.parse(raw),video=inside(path.resolve(path.dirname(file),b.video));
   if(b.version!=='studio-bundle-1'||sha(readFileSync(video))!==b.video_sha256)throw Error('Video hash mismatch');
   const id=sha(b.scene.id+'\n'+b.video_sha256).slice(0,24);
   const group=groups.get(id)??{id,title:b.title,duration:b.scene.duration_s,video:url(video),
    label:b.animation_label??b.source,source:'prepared',entries:[]};
   group.entries.push({...entry,id:folder+':'+entry.id,url:url(file),video:url(video),
    arrangement:entry.arrangement??(b.music_vertical?'prepared transitions':'piano'),composition:b.composition.title});
   groups.set(id,group);seen.add(digest);
  }catch(error){issues.push({catalog:folder,entry:entry.id,reason:String(error)});}}
 }catch(error){issues.push({catalog:folder,reason:String(error)});}
}
mkdirSync(path.join(publicRoot,'library'),{recursive:true});
writeFileSync(path.join(publicRoot,'library/catalog.json'),JSON.stringify({version:'video-library-1',videos:[...groups.values()],issues},null,2)+'\n');
console.log(`Video library: ${groups.size} animations, ${seen.size} soundtracks${issues.length?`, ${issues.length} unavailable entries`:''}`);
for(const issue of issues)console.warn(issue);
