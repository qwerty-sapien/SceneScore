/** Browser/PCM evidence, with a mocked companion; no real headset or human audition claim. */
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.SCENESCORE_PLAYWRIGHT_MODULE).href);
const out='output/playwright/manual-key-change';mkdirSync(out,{recursive:true});
const report={pid:process.pid,checks:[],errors:[],headset:'MOCKED',human_audition:'NOT_RUN',physical_output_measured:false};
let browser;const deadline=setTimeout(()=>void browser?.close(),120000);
const record=(name,evidence=true)=>{report.checks.push({name,evidence});console.log(name);};
console.log(`Key-change browser PID=${process.pid}`);
try{
 browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(15000);
 page.on('pageerror',e=>report.errors.push(e.message));
 const base=process.env.SCENESCORE_CATALOG_URL??'http://127.0.0.1:8797';
 for(const vertical of [false,true]){
  await page.goto(vertical?base+'/?music=1':base);
  if(!vertical)await page.getByRole('button',{name:'Watch Projectile & tower',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
  const button=page.getByRole('button',{name:'Change key',exact:true});assert.equal(await button.isDisabled(),true);
  await page.getByRole('button',{name:'▶ Watch & listen',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('.manual-key-change button')?.disabled);
  const before=await page.evaluate(()=>({state:window.__studio.snapshot(),events:window.__studio.performed().events}));
  const gain=await page.getByRole('slider',{name:'Master volume',exact:true}).inputValue();
  await button.click();assert.equal(await button.isDisabled(),true);
  const queued=await page.evaluate(()=>window.__studio.snapshot());assert.equal(queued.history.length,1);assert.equal(queued.history[0].status,'queued');
  const action=queued.history[0].action;assert.equal(action.provenance.source_mode,'keyboard');assert.equal(typeof action.provenance.seed,'number');assert.deepEqual(action.before,action.after);
  await page.waitForFunction(()=>window.__studio.snapshot().history[0]?.status==='executed');
  const after=await page.evaluate(()=>({state:window.__studio.snapshot(),events:window.__studio.performed().events}));
  assert.equal(after.state.tonic,(before.state.tonic+action.signed_semitones+12)%12);assert.equal(after.state.chord.root_pc,after.state.tonic);
  assert.notDeepEqual(after.events,before.events);assert.equal(after.state.approval,null);assert.equal(after.state.draft_conducting,false);
  assert.equal(await page.getByRole('slider',{name:'Master volume',exact:true}).inputValue(),gain);
  for(const event of before.events.filter(e=>e.midi_pitch===null))assert.deepEqual(after.events.find(e=>e.id===event.id),event);
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  const pcm=await page.evaluate(()=>window.__studio.offline());assert.ok(pcm.rms>0);assert.equal(pcm.clipped,0);
  record(vertical?'music vertical executes progression':'library executes key change',{action,tonic:after.state.tonic,chord:after.state.chord,scheduled:after.state.scheduled.length,pcm});
  await page.screenshot({path:`${out}/${vertical?'vertical':'library'}.png`,fullPage:true});
 }
 // A deterministic local companion fixture exercises presence independently of classifier readiness.
 const idle={version:'muse-bridge-1',mode:'LIVE_MUSE',connected:false,hardware_verified:false,quality:'unverified',warmup_ready:false,armed:false,reason:'waiting_for_source_samples',model_version:'fixture',config_hash:'a'.repeat(64),source_available:false,recording:false,sample_count:0,device_epoch:'fixture-device',host_epoch:'fixture-host',transport:'bleak',bluetooth_state:'idle',ble_connected:false};
 let status={...idle},available=true;
 await page.route('http://127.0.0.1:8766/v1/**',async route=>{
  const url=new URL(route.request().url());const path=url.pathname;
  if(!available)return route.abort();
  if(path.endsWith('/events'))await new Promise(resolve=>setTimeout(resolve,100));
  let data=status;
  if(path.endsWith('/session'))data={session:'fixture-session',cursor:0,status};
  if(path.endsWith('/events'))data={cursor:0,events:[],status,overflow:false};
  if(path.endsWith('/models'))data={selection:'latest',active_checkpoint_id:null,checkpoints:[],invalid_checkpoint_ids:[]};
  if(path.endsWith('/scan'))data={devices:[{id:'fixture-muse',name:'Muse-TEST'}],status};
  if(path.endsWith('/connect'))data=status={...idle,connected:true,hardware_verified:true,ble_connected:true,bluetooth_state:'streaming',quality:'bad'};
  if(path.endsWith('/disconnect'))data=status={...idle,bluetooth_state:'disconnected'};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
 });
 await page.getByText('Muse & input controls',{exact:true}).click();
 await page.getByRole('combobox',{name:'Muse source'}).selectOption('LIVE_MUSE');
 assert.equal(await page.getByRole('button',{name:'Change key',exact:true}).count(),1);
 await page.getByLabel('Companion session token').fill('fixture_token_0123456789012345678901234567');
 await page.getByRole('button',{name:'Connect companion',exact:true}).click();
 await page.getByRole('button',{name:'Scan for Muse',exact:true}).click();
 await page.waitForFunction(()=>!document.querySelector('.manual-key-change'));
 record('scan discovery hides manual button; source selection alone does not');
 await page.getByRole('button',{name:'Connect headset',exact:true}).click();
 await page.getByRole('button',{name:'Disconnect headset',exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Change key',exact:true}).count(),0);
 record('connected but bad-quality and disarmed Muse keeps button hidden');
 await page.getByRole('button',{name:'Disconnect headset',exact:true}).click();
 await page.getByRole('button',{name:'Change key',exact:true}).waitFor();record('disconnect restores manual button');
 await page.getByRole('button',{name:'Scan for Muse',exact:true}).click();
 await page.waitForFunction(()=>!document.querySelector('.manual-key-change'));available=false;
 await page.getByRole('button',{name:'Change key',exact:true}).waitFor();record('companion loss clears stale discovery and restores manual button');
 await page.setViewportSize({width:390,height:844});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:`${out}/mobile.png`,fullPage:true});record('mobile has no horizontal overflow');
 assert.deepEqual(report.errors,[]);report.status='passed';
}catch(error){report.status='failed';report.error=String(error);console.error(error);process.exitCode=1;}
finally{clearTimeout(deadline);await browser?.close();report.browser_closed=true;writeFileSync(`${out}/checks.json`,JSON.stringify(report,null,2)+'\n');console.log('Browser closed');}
