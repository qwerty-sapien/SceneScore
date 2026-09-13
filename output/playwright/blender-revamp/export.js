async (page) => {
 const downloads=[];
 page.on('download',download=>{downloads.push(download.saveAs('/Users/agent/Desktop/SceneScore/output/playwright/blender-revamp/'+download.suggestedFilename()));});
 await page.getByRole('button',{name:'Export draft audition',exact:true}).click();
 await page.waitForFunction(()=>window.__lastExport?.files?.length===5,null,{timeout:60000});
 await Promise.all(downloads);
 console.log(JSON.stringify({downloads:downloads.length,report:await page.evaluate(()=>window.__lastExport)}));
}
