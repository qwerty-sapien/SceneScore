/** Bounded real-browser coverage and actual piano/brush/Foley stem measurements. */
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.SCENESCORE_PLAYWRIGHT_MODULE).href);
const out=path.resolve('output/playwright/catalog-audio');mkdirSync(out,{recursive:true});
const result={pid:process.pid,videos:[],piano:[],errors:[],human_audition:'NOT_RUN',physical_output_measured:false,browser_closed:false};
console.log(`Catalog/audio check PID=${process.pid}`);
let browser;
const deadline=setTimeout(()=>{console.error('Catalog/audio browser deadline exceeded');void browser?.close();},240000);
try{
 browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});page.setDefaultTimeout(15000);page.on('pageerror',e=>result.errors.push(e.message));
 await page.goto(process.env.SCENESCORE_CATALOG_URL??'http://127.0.0.1:8765');
 const catalog=await page.evaluate(async()=>await (await fetch('/library/catalog.json')).json());
 assert.equal(catalog.coverage.requested,78);assert.equal(catalog.coverage.available,78);assert.ok(catalog.videos.length>=43);assert.deepEqual(catalog.issues,[]);
 await page.getByRole('heading',{name:'Video library',exact:true}).waitFor();
 assert.equal(await page.locator('.video-item').count(),catalog.videos.length);result.coverage=catalog.coverage;
 await page.screenshot({path:path.join(out,'library.png'),animations:'disabled'});
 for(const item of catalog.videos){
  await page.locator(`[data-video-id="${item.id}"] .video-open`).click();
  if(item.accompaniment){
   await page.getByRole('button',{name:'Watch & listen',exact:true}).click();
   await page.getByRole('button',{name:'Pause',exact:true}).click();
  }else if(item.entries.length){
   await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
   await page.getByRole('button',{name:'▶ Watch & listen',exact:true}).click();
   await page.waitForFunction(()=>window.__studio.snapshot().time>.15);assert.equal((await page.evaluate(()=>window.__studio.snapshot())).approval,null);
   await page.getByRole('button',{name:'Pause',exact:true}).click();
  }else{
   await page.locator('.rendered-player video').waitFor();
   await page.waitForFunction(()=>document.querySelector('.rendered-player video')?.readyState>=2);
   const meta=await page.locator('.rendered-player video').evaluate(async v=>{window.__checkedMedia=v;v.muted=true;await v.play();return {duration:v.duration,width:v.videoWidth};});
   assert.ok(meta.width>0&&Math.abs(meta.duration-item.duration)<.15);
   await page.waitForFunction(()=>document.querySelector('.rendered-player video').currentTime>.05);
   await page.getByText(item.audio==='embedded'?'Original rendered audio · not live synthesis':'Silent render · live soundtrack not prepared',{exact:true}).waitFor();
  }
  result.videos.push({id:item.id,title:item.title,audio:item.audio,status:'passed'});
  await page.getByRole('button',{name:'← Video library',exact:true}).click();
  if(!item.entries.length&&!item.accompaniment)assert.ok(await page.evaluate(()=>{const paused=window.__checkedMedia.paused;delete window.__checkedMedia;return paused;}),'Original media pauses on navigation');
  if(result.videos.length%10===0)console.log(`${result.videos.length} videos played/decoded`);
 }
 const staircase=catalog.videos.find(v=>v.title==='05 bouncing staircase');
 await page.locator(`[data-video-id="${staircase.id}"] .video-open`).click();await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
 const tracks=page.getByRole('combobox',{name:'Soundtrack version'});assert.match(await tracks.inputValue(),/clean-piano-v1$/);
 const versions=staircase.entries.filter(e=>e.arrangement==='clean-piano');assert.equal(versions.length,3);
 for(const [index,entry] of versions.entries()){
  await tracks.selectOption(entry.id);await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
  assert.equal(await page.getByRole('slider',{name:'Master volume'}).inputValue(),'-6');
  await page.getByRole('button',{name:'▶ Watch & listen',exact:true}).click();await page.waitForFunction(()=>window.__studio.snapshot().time>.15);
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  const saves=[],folder=path.join(out,entry.groove);mkdirSync(folder,{recursive:true});
  const onDownload=d=>saves.push(d.saveAs(path.join(folder,d.suggestedFilename())));page.on('download',onDownload);
  await page.evaluate(()=>{delete window.__lastExport;});await page.getByRole('button',{name:'Download draft audio + stems',exact:true}).click();
  await page.waitForFunction(()=>Boolean(window.__lastExport));
  const downloadDeadline=Date.now()+10000;while(saves.length<6&&Date.now()<downloadDeadline)await page.waitForTimeout(50);
  assert.equal(saves.length,6);await Promise.all(saves);page.off('download',onDownload);
  const report=await page.evaluate(()=>window.__lastExport),stems=Object.fromEntries(report.files.map(f=>[f.stem,f.measurements]));
  assert.equal(report.approval,null);assert.equal(report.piano_mix.voice_version,'scene-piano-voices-1');
  assert.ok(report.events.some(e=>e.instrument_id==='scene_piano_v1'));
  assert.ok(!report.events.some(e=>e.event_type==='brush'&&e.articulation==='sweep'));
  for(const m of Object.values(stems)){assert.equal(m.duration_s,8);assert.equal(m.clipped,0);}
  assert.ok(stems.piano.rms>stems.brush.rms*10);assert.ok(stems.mix.peak<.9);assert.ok(stems.foley.rms>0);
  result.piano.push({id:entry.id,stems,piano_over_brush_db:20*Math.log10(stems.piano.rms/stems.brush.rms),saved_files:saves.length});
  console.log(JSON.stringify(result.piano.at(-1)));
  if(index===0)await page.screenshot({path:path.join(out,'piano-player.png'),fullPage:true,animations:'disabled'});
 }
 await page.getByRole('button',{name:'← Video library',exact:true}).click();
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:`Silent renders ${catalog.coverage.silent}`,exact:true}).click();
 assert.equal(await page.locator('.video-item').count(),catalog.coverage.silent);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:path.join(out,'mobile.png'),animations:'disabled'});
 assert.deepEqual(result.errors,[]);result.status='passed';
}catch(error){result.status='failed';result.error=String(error);console.error(error);process.exitCode=1;}
finally{await browser?.close();clearTimeout(deadline);result.browser_closed=true;writeFileSync(path.join(out,'checks.json'),JSON.stringify(result,null,2)+'\n');console.log('Browser closed');}
