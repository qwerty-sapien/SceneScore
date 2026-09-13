/** Actual browser PCM checks for the staircase gain change; no speaker/SPL claim. */
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const {chromium}=await import(pathToFileURL(process.env.SCENESCORE_PLAYWRIGHT_MODULE).href);
const out=path.resolve('output/playwright/staircase-volume');mkdirSync(out,{recursive:true});
const result={pid:process.pid,variants:[],errors:[],human_audition:'NOT_RUN',physical_spl_measured:false,browser_closed:false};
console.log(`Staircase volume check PID=${process.pid}`);
let browser;
const deadline=setTimeout(()=>{console.error('Browser check exceeded 120 seconds');void browser?.close();},120000);
const expected=Number(process.env.SCENESCORE_EXPECTED_STAIRCASE_GAIN??-6);
try{
 browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(15000);
 page.on('pageerror',e=>result.errors.push(e.message));
 await page.goto(process.env.SCENESCORE_CATALOG_URL??'http://127.0.0.1:8765');
 await page.getByRole('button',{name:'Watch 05 bouncing staircase',exact:true}).click();
 await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
 const gain=page.getByRole('slider',{name:'Master volume',exact:true});
 assert.equal(Number(await gain.inputValue()),expected);
 const tracks=page.getByRole('combobox',{name:'Soundtrack version'});
 const versions=await tracks.locator('option').evaluateAll(options=>options.filter(o=>!o.value.endsWith('clean-piano-v1')).map(o=>({id:o.value,title:o.textContent})));
 assert.equal(versions.length,3);
 async function setGain(db){await gain.focus();await gain.press('End');for(let i=0;i>db;i--)await gain.press('ArrowLeft');assert.equal(Number(await gain.inputValue()),db);}
 const measure=()=>page.evaluate(async()=>{const m=await window.__studio.offline();return {...m,rms_dbfs:20*Math.log10(m.rms),peak_dbfs:20*Math.log10(m.peak)};});
 for(const version of versions){
  await tracks.selectOption(version.id);await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
  await setGain(-18);await page.getByRole('button',{name:'▶ Watch & listen',exact:true}).click();
  await page.waitForFunction(()=>window.__studio.snapshot().time>.1);
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  assert.equal((await page.evaluate(()=>window.__studio.snapshot())).approval,null);
  const before=await measure();await setGain(-6);const after=await measure();
  assert.equal(after.duration_s,8);assert.equal(after.clipped,0);assert.ok(after.peak<.8);
  assert.ok(after.rms_dbfs>=-40,'Staircase average digital level must be at least -40 dBFS');
  assert.ok(Math.abs(after.rms_dbfs-before.rms_dbfs-12)<.01);
  result.variants.push({...version,default_gain_db:expected,before_gain_db:-18,after_gain_db:-6,before,after});
  console.log(JSON.stringify(result.variants.at(-1)));
 }
 await setGain(-24);await tracks.selectOption(versions[0].id);await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
 assert.equal(Number(await gain.inputValue()),-24);result.manual_volume_preserved_on_track_change=true;
 await page.getByRole('button',{name:'← Video library',exact:true}).click();
 await page.getByRole('button',{name:'Watch 05 bouncing staircase',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
 assert.equal(Number(await gain.inputValue()),expected);result.fresh_player_default_verified=true;
 await page.screenshot({path:path.join(out,'player.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'← Video library',exact:true}).click();
 assert.deepEqual(result.errors,[]);result.status='passed';
}catch(error){result.status='failed';result.error=String(error);console.error(error);process.exitCode=1;}
finally{await browser?.close();clearTimeout(deadline);result.browser_closed=true;writeFileSync(path.join(out,'checks.json'),JSON.stringify(result,null,2)+'\n');console.log('Browser closed');}
