async (page) => {
 const pending=[];let folder='';
 const listener=download=>pending.push(download.saveAs('/Users/agent/Desktop/SceneScore/output/playwright/blender-revamp/final-exports/'+folder+'/'+download.suggestedFilename()));
 page.on('download',listener);
 try{
  for(const groove of ['brush_swing_light_v1','brush_ballad_sparse_v1','brush_straight_rag_v1']){
   await page.getByRole('combobox',{name:'Brush groove',exact:true}).selectOption(groove);
   await page.waitForFunction(id=>window.__studio?.snapshot().bundle_id===id,'05_bouncing_staircase-'+groove,{timeout:20000});
   await page.evaluate(()=>{delete window.__lastExport;});
   pending.length=0;folder=groove;
   await page.getByRole('button',{name:'Export draft audition',exact:true}).click();
   await page.waitForFunction(id=>window.__lastExport?.bundle_id===id,'05_bouncing_staircase-'+groove,{timeout:60000});
   for(let i=0;i<100&&pending.length<6;i++)await page.waitForTimeout(20);
   if(pending.length!==6)throw Error('Expected exactly five WAVs plus report');
   await Promise.all(pending);
  }
 }finally{page.off('download',listener);}
}
