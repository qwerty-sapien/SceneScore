/** Run isolated Vite + Chromium, verify audible PCM for every catalog item, then close both. */
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {createServer} from 'vite';
const {chromium}=await import(pathToFileURL(process.env.SCENESCORE_PLAYWRIGHT_MODULE).href);
const pcmOnly=process.env.SCENESCORE_PCM_ONLY==='1';
const out=pcmOnly?'output/playwright/audio-completion-final-mix':'output/playwright/audio-completion';mkdirSync(out,{recursive:true});
const report={pid:process.pid,mode:pcmOnly?'prepared playback and final mix':'all catalog playback and mix',clips:[],mixes:[],errors:[],human_audition:'NOT_RUN',physical_output_measured:false};
let server,browserServer,browser;
console.log(`Audio verification PID=${process.pid}`);
const deadline=setTimeout(()=>{console.error('Verification deadline exceeded');process.exitCode=1;void browserServer?.close();void server?.close();},300000);
try{
 server=await createServer({root:'apps/web',server:{host:'127.0.0.1',port:8796,strictPort:true}});await server.listen();
 browserServer=await chromium.launchServer({channel:'chrome',headless:true});report.browser_pid=browserServer.process().pid;console.log(`Owned Chromium PID=${report.browser_pid}`);
 browser=await chromium.connect(browserServer.wsEndpoint());
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(15000);page.on('pageerror',e=>report.errors.push(e.message));
 await page.addInitScript(()=>{
  window.__audios=[];const Native=window.AudioContext;
  window.AudioContext=class extends Native{constructor(...args){super(...args);this.meter=this.createAnalyser();this.meter.fftSize=2048;window.__audios.push(this);}
   createGain(){const gain=super.createGain(),connect=gain.connect.bind(gain);gain.connect=(destination,...args)=>{if(destination===this.destination)connect(this.meter);return connect(destination,...args);};return gain;}
  };
 });
 await page.goto('http://127.0.0.1:8796');
 const catalog=await page.evaluate(async()=>await(await fetch('/library/catalog.json')).json());report.coverage=catalog.coverage;
 assert.deepEqual(catalog.issues,[]);assert.equal(catalog.coverage.silent,0);assert.equal(catalog.coverage.available,catalog.coverage.requested);
 assert.ok(catalog.videos.every(v=>v.entries.length||v.accompaniment||v.audio==='embedded'));
 await page.getByRole('heading',{name:'Video library',exact:true}).waitFor();
 await page.screenshot({path:out+'/library.png',animations:'disabled'});
 for(const item of catalog.videos.filter(v=>!pcmOnly||v.entries.length)){
  await page.locator(`[data-video-id="${item.id}"] .video-open`).click();
  if(item.entries.length){
   await page.waitForFunction(()=>!document.querySelector('.primary-play')?.disabled);
   await page.getByRole('button',{name:'▶ Watch & listen',exact:true}).click();
  }else if(item.accompaniment){
   await page.getByRole('button',{name:'Watch & listen',exact:true}).click();
  }else{
   await page.waitForFunction(()=>document.querySelector('.rendered-player video')?.readyState>=2);
   await page.locator('video').evaluate(async v=>{window.__embeddedContext=new AudioContext();const ctx=window.__embeddedContext,source=ctx.createMediaElementSource(v);source.connect(ctx.meter);source.connect(ctx.destination);await ctx.resume();await v.play();});
  }
  await page.waitForFunction(()=>window.__audios.some(ctx=>{if(ctx.state!=='running')return false;const data=new Float32Array(ctx.meter.fftSize);ctx.meter.getFloatTimeDomainData(data);return data.some(v=>Math.abs(v)>1e-5);}));
  assert.ok(await page.locator('video').first().evaluate(v=>v.videoWidth>0));
  report.clips.push({title:item.title,id:item.id,mode:item.entries.length?'scene-live':item.accompaniment?'video-live':'embedded',audio_pcm:'nonzero'});
  if(item.accompaniment&&report.clips.filter(c=>c.mode==='video-live').length===1){
   await page.getByRole('button',{name:'Pause',exact:true}).click();
   await page.getByRole('slider',{name:'Seek video',exact:true}).fill(String(item.duration*.6));
   await page.getByRole('button',{name:'Watch & listen',exact:true}).click();
   await page.getByRole('button',{name:'Pause',exact:true}).click();
   await page.getByRole('button',{name:'New piano take',exact:true}).click();
   await page.getByRole('button',{name:'Watch & listen',exact:true}).click();
   await page.screenshot({path:out+'/live-piano.png',animations:'disabled'});
  }
  await page.getByRole('button',{name:'← Video library',exact:true}).click();
  await page.evaluate(async()=>{await window.__embeddedContext?.close();delete window.__embeddedContext;});
  await page.waitForFunction(()=>window.__audios.every(ctx=>ctx.state==='closed'));
  if(report.clips.length%10===0)console.log(`${report.clips.length}/${catalog.videos.length} clips have nonzero playback PCM`);
 }
 // Measure full mix and both separated lanes for every prepared default score.
 report.mixes=await page.evaluate(async()=>{
  const {renderOffline,measurements}=await import('/@fs/Users/agent/Desktop/SceneScore/packages/audio/engine.ts');
  const {prepareEffectMix}=await import('/@fs/Users/agent/Desktop/SceneScore/packages/audio/effect-mix.ts');
  const {voice}=await import('/@fs/Users/agent/Desktop/SceneScore/packages/audio/engine.ts');
  const catalog=await(await fetch('/library/catalog.json')).json(),results=[];
  for(const item of catalog.videos.filter(v=>v.entries.length)){
   for(const entry of item.entries.filter((e,i)=>i===0||e.arrangement==='clean-piano')){
    const b=await(await fetch(entry.url)).json(),events=b.events,duration=b.scene.duration_s,rate=48000;
    const ctx=new OfflineAudioContext(1,1,rate),policy=prepareEffectMix(events,duration,rate,e=>({data:voice(ctx,e).getChannelData(0)}));
    const mixed=await renderOffline(events,duration,-6);
    const soundtrack=await renderOffline(events.filter(e=>e.event_type!=='foley'),duration,-6,undefined,rate,undefined,undefined,undefined,false,events);
    const effects=await renderOffline(events.filter(e=>e.event_type==='foley'),duration,-6,undefined,rate,undefined,undefined,undefined,false,events);
    let sumError=0;for(let i=0;i<mixed.length;i++)sumError=Math.max(sumError,Math.abs(mixed.getChannelData(0)[i]-soundtrack.getChannelData(0)[i]-effects.getChannelData(0)[i]));
    const intervals=[];for(const e of events.filter(e=>e.event_type==='foley').sort((a,b)=>a.resolved_time_s-b.resolved_time_s)){const end=Math.min(duration,e.resolved_time_s+e.duration_s),last=intervals.at(-1);if(last&&e.resolved_time_s<last.end)last.end=Math.max(last.end,end);else intervals.push({start:e.resolved_time_s,end});}
    const rms=(buffer,a,z)=>{const data=buffer.getChannelData(0);let sum=0;for(let i=a;i<z;i++)sum+=data[i]*data[i];return Math.sqrt(sum/(z-a));};
    const ratios=intervals.map(({start,end})=>{const a=Math.round(start*rate),z=Math.min(mixed.length,Math.ceil(end*rate));return rms(effects,a,z)/rms(soundtrack,a,z);});
    results.push({id:entry.id,mix:measurements(mixed),sum_error:sumError,ratios,effect_gains:[...policy.levels.values()]});
   }
  }return results;
 });
 for(const mix of report.mixes){assert.equal(mix.mix.clipped,0);assert.ok(mix.sum_error<1e-6);assert.ok(mix.ratios.every(r=>r>=1.1&&r<=1.3),JSON.stringify(mix));}
 assert.deepEqual(report.errors,[]);report.status='passed';
 console.log(JSON.stringify({coverage:report.coverage,clips:report.clips.length,mixes:report.mixes.length,status:report.status}));
}catch(error){report.status='failed';report.error=String(error);console.error(error);process.exitCode=1;}
finally{
 await browser?.close();await browserServer?.close();await server?.close();clearTimeout(deadline);
 report.browser_exit_code=browserServer?.process().exitCode;report.server_closed=true;
 writeFileSync(out+'/checks.json',JSON.stringify(report,null,2)+'\n');console.log('Owned browser and Vite server closed');
}
