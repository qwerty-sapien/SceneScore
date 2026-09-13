import {createHash} from 'node:crypto';
import {existsSync,readFileSync,readdirSync,realpathSync,statSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

export const videoHash=bytes=>createHash('sha256').update(bytes).digest('hex');
export function probeVideo(file){
 const p=JSON.parse(execFileSync('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type','-of','json',file],{timeout:10000,maxBuffer:1024*1024}));
 const duration=Number(p.format?.duration);
 if(!Number.isFinite(duration)||duration<=0||!p.streams.some(s=>s.codec_type==='video'))throw Error('No playable video stream');
 return {duration,hasAudio:p.streams.some(s=>s.codec_type==='audio')};
}
export function discoverVideos(root){
 const result=[];
 function visit(dir){for(const entry of readdirSync(dir,{withFileTypes:true})){
  if(entry.name.startsWith('.')||entry.name.endsWith('-dist')||entry.name==='pre-window-integration')continue;
  const file=path.join(dir,entry.name);
  if(entry.isDirectory())visit(file);else if(entry.isFile()&&entry.name.endsWith('.mp4'))result.push(path.relative(root,file).split(path.sep).join('/'));
 }}
 if(existsSync(root))visit(root);return result.sort();
}
export function inspectVideoSources(artifactRoot,requested,{discover=true,probe=probeVideo}={}){
 const root=realpathSync(artifactRoot),groups=new Map(),sources=[],issues=[];
 const paths=[...new Set([...requested,...(discover?discoverVideos(root):[])])];
 for(const relative of paths){try{
  const file=realpathSync(path.resolve(root,relative));
  if(!file.startsWith(root+path.sep)||path.extname(file)!=='.mp4')throw Error('Video outside artifact scope');
  if(statSync(file).size>256*1024*1024)throw Error('Video exceeds 256 MiB catalog limit');
  const digest=videoHash(readFileSync(file));let group=groups.get(digest);
  if(!group){group={sha256:digest,file,paths:[],...probe(file)};groups.set(digest,group);}
  group.paths.push(relative);sources.push({path:relative,status:'available',sha256:digest,requested:requested.includes(relative)});
 }catch(error){const issue={path:relative,status:'unavailable',requested:requested.includes(relative),reason:String(error)};issues.push(issue);sources.push(issue);}}
 return {groups:[...groups.values()],sources,issues};
}
export function videoTitle(relative){
 const trimmed=relative.includes('/renders/')?relative.split('/renders/')[0]:relative.replace(/\/(preview|proxy|contact|near-miss)\.mp4$/,'');
 const parts=trimmed.replace(/\.mp4$/,'').split('/');
 return {title:parts.at(-1).replaceAll('_',' ').replaceAll('-DRAFT',''),edition:parts.slice(-3,-1).join(' / ').replaceAll('_',' ')};
}
