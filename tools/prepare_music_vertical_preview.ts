/** Prepare an unapproved audition of two explicitly chosen synthetic requests. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {verifyBundle,stable} from '../packages/audio/model';
import {materializeVerticalPreview} from '../packages/audio/vertical-preview';

const [input,output,...times]=process.argv.slice(2);
if(!input||!output||times.length!==2)throw Error('Usage: prepare_music_vertical_preview.ts candidate.json NEW_PREVIEW.json request_s request_s');
const raw=fs.readFileSync(input),bundle=JSON.parse(raw.toString());
const plan=await verifyBundle(bundle);
const preview=materializeVerticalPreview(bundle,plan,times.map(Number),bundle.holds??[]);
const eventBytes=stable(preview.events)+'\n';
const hash=(bytes:Buffer|string)=>createHash('sha256').update(bytes).digest('hex');
const result={...bundle,id:bundle.id+'-planned-controls',
 offline_transition_preview:{...preview,events_bytes:eventBytes,events_sha256:hash(eventBytes)},approval:null,audition_status:'AUDITION_PENDING',
 candidate_parent_sha256:hash(raw),source:'SYNTHETIC_TEST',
 performance_status:'DRAFT_NOT_APPROVED',
 source_code_sha256:Object.fromEntries(['packages/audio/model.ts','packages/audio/vertical-preview.ts','tools/prepare_music_vertical_preview.ts'].map(p=>[p,hash(fs.readFileSync(p))]))};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({output,events:preview.events.length,controls:preview.controls,approval:null})+'\n');
