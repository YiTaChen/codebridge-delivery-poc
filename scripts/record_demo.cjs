/* Optional browser verification/recording. Install playwright and Chrome first.
   Starts no server. Every Analyze below is a real request; no response interception. */
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const work=path.join(root,'work','recording');
fs.mkdirSync(work,{recursive:true});
fs.mkdirSync(path.join(root,'sample-data','actual'),{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1100},recordVideo:{dir:work,size:{width:1440,height:1100}}});
 const page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const start=Date.now(), waits=[], runs=[];
 const pause=ms=>new Promise(r=>setTimeout(r,ms));
 async function caption(text){await page.evaluate(text=>{let e=document.getElementById('demo-caption');if(!e){e=document.createElement('div');e.id='demo-caption';e.style.cssText='position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:99999;max-width:94%;padding:14px 22px;background:#173137;color:white;border-radius:10px;font:600 17px system-ui;box-shadow:0 4px 20px #0003;pointer-events:none;text-align:center';document.body.appendChild(e);}e.textContent=text},text);}
 await page.goto(process.env.DEMO_URL||'http://127.0.0.1:8000');
 await caption('ParcelProof · PDF + delivery photos → evidence-backed findings');await pause(2400);
 await page.getByRole('button',{name:'Issue delivery',exact:true}).click();
 await page.getByText('photo_3.png',{exact:false}).first().waitFor();
 await page.getByRole('button',{name:/Photo evidence/}).click();
 await caption('Synthetic fixtures: wrong SKU, extra mug, hidden label, repeated ITEM markers');await pause(3500);
 const cases=[['issue_delivery','Issue delivery'],['corrected_delivery','Corrected delivery'],['incorrect_manifest','Incorrect packing list']];
 for(const [id,label] of cases){
  if(id!=='issue_delivery'){await page.getByRole('button',{name:label,exact:true}).click();await pause(900);}
  await caption(id==='issue_delivery'?'Analyze makes a real model call through your local ChatGPT / Codex login':id==='corrected_delivery'?'Corrected delivery: same manifest, four correct marked items':'Incorrect PDF: deliberately wrong quantity and mug SKU');
  await page.getByRole('button',{name:'Analyze delivery',exact:true}).scrollIntoViewIfNeeded();await pause(700);
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/analyze')&&r.request().method()==='POST',{timeout:270000});
  const before=(Date.now()-start)/1000;
  await page.getByRole('button',{name:'Analyze delivery',exact:true}).click();
  await caption('Live model processing · waiting time is accelerated in the edited demo');
  const response=await responsePromise;
  const body=await response.json();
  const after=(Date.now()-start)/1000;waits.push({start:before+1,end:after});
  if(!response.ok())throw new Error(`${id}: HTTP${response.status()} ${JSON.stringify(body)}`);
  fs.writeFileSync(path.join(root,'sample-data','actual',`${id}.json`),JSON.stringify(body,null,2)+'\n');
  runs.push({id,recorded_at:new Date().toISOString(),http_status:response.status(),elapsed_seconds:body.metrics.elapsed_seconds,model:body.metrics.model});
  await page.getByRole('button',{name:/^Findings/}).click();
  await page.locator('.summary').scrollIntoViewIfNeeded();
  await caption(id==='issue_delivery'?'Deduplicated counts. Wrong SKUs never match. Hidden stock is unverified.':id==='corrected_delivery'?'Corrected delivery: all three SKU rows match (real measured run shown)':'Incorrect manifest: quantity discrepancy + wrong mug SKU, with source evidence');
  await pause(2700);
  await page.screenshot({path:path.join(work,`${id}.png`),fullPage:true});
  if(id==='issue_delivery'){
   await page.locator('.finding').nth(2).scrollIntoViewIfNeeded();await pause(2200);
   await page.getByRole('button',{name:'PDF source',exact:true}).click();
   await page.locator('.source-lines').scrollIntoViewIfNeeded();
   await caption('Each finding cites a numbered PDF row and a model-described photo region');await pause(2200);
   await page.getByRole('button',{name:/^Findings/}).click();
   await page.locator('.evidence-links button').first().click();
   await page.locator('.evidence-photo').scrollIntoViewIfNeeded();await pause(2500);
  }
 }
 await caption('3 synthetic cases · results and limitations disclosed · public MIT source + setup instructions');await pause(2700);
 fs.writeFileSync(path.join(work,'timeline.json'),JSON.stringify({waits,runs,browser_errors:errors,total_seconds:(Date.now()-start)/1000},null,2));
 const video=page.video();await context.close();fs.writeFileSync(path.join(work,'video-path.txt'),await video.path());await browser.close();
 if(errors.length)throw new Error('Browser errors: '+errors.join('; '));
 console.log(JSON.stringify({runs,waits,browser_errors:errors,video:await video.path()}));
})().catch(e=>{console.error(e);process.exit(1)});
