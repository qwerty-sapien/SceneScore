import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {verifyBundle,type Bundle} from '../packages/audio/model';
const root=process.argv[2]??'apps/web/public/riff-studio';
const entries=JSON.parse(fs.readFileSync(path.join(root,'catalog.json'),'utf8')).entries;
const sha=(v:Buffer)=>createHash('sha256').update(v).digest('hex');
const results=[];
for(const row of entries){
 const raw=fs.readFileSync(path.join(root,row.url));if(sha(raw)!==row.sha256)throw Error('Catalogue hash');
 const b=JSON.parse(raw.toString()) as Bundle,video=fs.readFileSync(path.join(root,b.video));
 await verifyBundle(b,video.buffer.slice(video.byteOffset,video.byteOffset+video.byteLength));
 if(row.arrangement==='piano'){
  if(sha(fs.readFileSync(path.join('apps/web/public/studio',row.url)))!==row.sha256)throw Error('Historical piano source changed');
 }else{
  const expected=b.interactions.filter(e=>e.event_type==='contact_onset');
  if(b.events.filter(e=>e.event_type==='foley').length!==expected.length)throw Error('Extra collision audio');
  if(b.variant==='near-miss'&&expected.length)throw Error('Unexpected miss contact');
 }
 results.push({id:b.id,events:b.events.length,contacts:b.events.filter(e=>e.event_type==='foley').length,verified:true});
}
fs.writeFileSync(process.argv[3]??'reports/collision-riffs/catalog-audit.json',JSON.stringify({entries:results,approval:null},null,2)+'\n');
process.stdout.write(JSON.stringify({verified:results.length})+'\n');
