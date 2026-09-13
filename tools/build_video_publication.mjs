import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {build} from 'vite';
const paths=['apps/web/src','packages/audio','packages/contracts','packages/controls','packages/blink'];
const all=[];
function walk(p){if(!fs.existsSync(p))return;const s=fs.statSync(p);if(s.isFile())all.push(p);else for(const name of fs.readdirSync(p).sort())walk(path.join(p,name));}
for(const p of paths)walk(p);
const hash=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const before=Object.fromEntries(all.map(p=>[p,hash(p)]));
await build({root:'apps/web',publicDir:false,build:{outDir:path.resolve('artifacts/vercel-video-build'),emptyOutDir:true}});
if(all.some(p=>hash(p)!==before[p]))throw Error('Player source changed during build; rebuild before publishing');
fs.writeFileSync('reports/vercel-animations-06-08-18/build-source-hashes.json',JSON.stringify(before,null,2)+'\n');
