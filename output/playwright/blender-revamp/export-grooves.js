async (page) => {
 for(const groove of ['brush_ballad_sparse_v1','brush_straight_rag_v1']){
  await page.getByRole('combobox',{name:'Brush groove',exact:true}).selectOption(groove);
  await page.getByRole('button',{name:'Export draft audition',exact:true}).waitFor({state:'visible'});
  await page.waitForFunction(id=>window.__studio?.snapshot().bundle_id===id,'05_bouncing_staircase-'+groove,{timeout:20000});
  const downloads=[];
  const listener=download=>downloads.push(download.saveAs('/Users/agent/Desktop/SceneScore/output/playwright/blender-revamp/'+groove+'/'+download.suggestedFilename()));
  page.on('download',listener);
  await page.getByRole('button',{name:'Export draft audition',exact:true}).click();
  await page.waitForFunction(id=>window.__lastExport?.bundle_id===id,'05_bouncing_staircase-'+groove,{timeout:60000});
  for(let i=0;i<100&&downloads.length<6;i++)await page.waitForTimeout(20);
  if(downloads.length!==6)throw Error('Expected exact five WAVs and report');
  await Promise.all(downloads);page.off('download',listener);
 }
}
