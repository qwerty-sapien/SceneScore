import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {inspectVideoSources,discoverVideos,videoTitle} from './video-inventory.mjs';

test('exact copies group by content while requested source paths remain accounted for',()=>{
 const root=mkdtempSync(path.join(tmpdir(),'scenescore-inventory-'));
 try{
  // Synthetic file contents test inventory identity, not video decoding.
  writeFileSync(path.join(root,'a.mp4'),'synthetic-A');writeFileSync(path.join(root,'copy.mp4'),'synthetic-A');writeFileSync(path.join(root,'b.mp4'),'synthetic-B');
  let probes=0;const r=inspectVideoSources(root,['a.mp4','copy.mp4','b.mp4','missing.mp4'],{discover:false,probe:()=>{probes++;return {duration:8,hasAudio:false};}});
  assert.equal(r.groups.length,2);assert.equal(probes,2);assert.equal(r.sources.length,4);assert.equal(r.issues.length,1);
  assert.deepEqual(r.groups[0].paths,['a.mp4','copy.mp4']);
 }finally{rmSync(root,{recursive:true});}
});
test('discovery skips build mirrors and never admits paths outside the artifact root',()=>{
 const root=mkdtempSync(path.join(tmpdir(),'scenescore-inventory-'));
 try{
  mkdirSync(path.join(root,'web-dist'));writeFileSync(path.join(root,'web-dist','copy.mp4'),'synthetic');
  writeFileSync(path.join(root,'fresh.mp4'),'synthetic');
  assert.deepEqual(discoverVideos(root),['fresh.mp4']);
  const r=inspectVideoSources(path.join(root,'web-dist'),['../fresh.mp4'],{discover:false,probe:()=>{throw Error('must not probe outside root');}});
  assert.equal(r.groups.length,0);assert.match(r.issues[0].reason,/outside artifact scope/);
 }finally{rmSync(root,{recursive:true});}
});
test('render titles retain distinct scene revisions and meaningful proxy names',()=>{
 assert.equal(videoTitle('blender/revamp/directions/06_three_ways_down-v4/renders/video.mp4').title,'06 three ways down-v4');
 assert.equal(videoTitle('blender/kinetic/r2/01_marble_helix/proxy.mp4').title,'01 marble helix');
});
