import { fileURLToPath, pathToFileURL } from 'node:url';
const playwrightModule = process.env.GRID_PLAYWRIGHT_MODULE;
const { chromium } = await import(playwrightModule ? pathToFileURL(playwrightModule).href : 'playwright-core');
import fs from 'node:fs';
import path from 'node:path';
const work = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = path.join(work, 'css-shared/.local-notes/exports/grids');
fs.mkdirSync(out,{recursive:true});
const browser = await chromium.launch({executablePath:process.env.GRID_BROWSER || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const context = await browser.newContext({reducedMotion:'reduce'});
if (process.env.GRID_BOOTSTRAP_CSS) await context.route('https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css', r=>r.fulfill({path:process.env.GRID_BOOTSTRAP_CSS,contentType:'text/css'}));
await context.route('https://**', r=>r.request().url().endsWith('bootstrap.min.css')?r.fallback():r.abort());
await context.route('http://*.grids.test/**', r=>{
 const url=new URL(r.request().url()); const parts=url.pathname.split('/').filter(Boolean);
 const unit=url.hostname.split('.')[0];
 let file=path.join(work,unit,'_site',...parts);if(url.pathname.endsWith('/'))file=path.join(file,'index.html');
 return r.fulfill(fs.existsSync(file)?{path:file}:{status:404,body:'Missing '+file});
});
const page=await context.newPage();
const errors=[];page.on('pageerror', e=>errors.push(e.message));
await page.goto('http://review.grids.test/grids.html',{waitUntil:'networkidle'});
const tabChecks=[];
for (const width of [375,820,1800]) {
 await page.setViewportSize({width,height:1000});
 for (const tab of await page.getByRole('tab').all()) {
  await tab.click();
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const state=await page.evaluate(()=>({selected:document.querySelectorAll('[role="tab"][aria-selected="true"]').length,visible:[...document.querySelectorAll('[data-grid-panel]')].filter(p=>!p.hidden).length,overflow:document.documentElement.scrollWidth>innerWidth+1,invalidReadings:[...document.querySelectorAll('[data-grid-panel]:not([hidden]) [data-grid-reading]')].some(p=>p.textContent.includes('NaN'))}));
  if(state.selected!==1 || state.visible!==1 || state.overflow || state.invalidReadings) throw Error('Tab state failed: '+JSON.stringify(state));
  tabChecks.push({width,tab:await tab.innerText(),...state});
 }
}
await page.getByRole('tab').first().focus();
await page.keyboard.press('End');
if(await page.getByRole('tab',{selected:true}).innerText()!=='Combined Layouts')throw Error('End key failed');
await page.keyboard.press('Home');
if(await page.getByRole('tab',{selected:true}).innerText()!=='Sidebars Left & Right')throw Error('Home key failed');
await page.keyboard.press('ArrowRight');
if(await page.getByRole('tab',{selected:true}).innerText()!=='Equal Columns')throw Error('Arrow key failed');
// Expand panels only inside the audit to measure every specimen in one pass.
await page.evaluate(()=>document.querySelectorAll('[data-grid-panel]').forEach(panel=>panel.hidden=false));
const widths=[320,375,575,576,767,768,820,991,992,1024,1180,1199,1200,1399,1400,1599,1600,1800];
const readings=[];
for(const width of widths){
 await page.setViewportSize({width,height:1000});await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const data=await page.evaluate(()=>({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,examples:[...document.querySelectorAll('[data-grid-id]')].map(stage=>{
 const el=stage.querySelector(stage.dataset.gridSelector);const s=getComputedStyle(el);const rect=el.getBoundingClientRect();
 return {id:stage.dataset.gridId,classes:el.className,display:s.display,columns:s.gridTemplateColumns,horizontal:s.columnGap,vertical:s.rowGap,gutterX:s.getPropertyValue('--bs-gutter-x'),gutterY:s.getPropertyValue('--bs-gutter-y'),width:rect.width,children:[...el.children].map(c=>({width:c.getBoundingClientRect().width,top:c.getBoundingClientRect().top,left:c.getBoundingClientRect().left})),label:document.querySelector(`[data-grid-reading="${stage.dataset.gridId}"]`).textContent};
 })}));readings.push(data);
 if([820,1800].includes(width)) await page.locator('.review-grid-example').filter({has:page.getByRole('heading',{name:'.sidebar-right-med',exact:true})}).first().screenshot({path:path.join(out,`sidebar-${width}.png`)});
 if([375,820,1180,1800].includes(width))await page.screenshot({path:path.join(out,`review-grids-${width}.png`),fullPage:true});
}
await page.addScriptTag({path:process.env.GRID_AXE_SCRIPT || path.join(work,'review/node_modules/axe-core/axe.min.js')});
const axe=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}}));
const inventory=JSON.parse(fs.readFileSync(path.join(work,'review/_site/grids-inventory.json')));
// Compare each specimen's layout declarations with its first real consumer.
const comparisons=[];
for(const p of inventory.patterns){
 const use=p.uses[0];
 for(const width of [375,820,1024,1200,1600]){
  await page.setViewportSize({width,height:1000});await page.goto('http://'+use.unit+'.grids.test'+use.url,{waitUntil:'load'});
  const actual=await page.evaluate(p=>{
   const normal=el=>[...el.classList].filter(c=>! /^(?:mb|mt|mx|my|p[xy]?)-/.test(c)).join(' ');
   const el=[...document.querySelectorAll('main [class]')].find(el=>(/^sidebar-(left|right)-/.test(p.classes) ? el.classList.contains(p.classes) : normal(el)===p.classes&&(!p.context||normal(el.parentElement)===p.context)&&([...el.children].map(normal).join('|')===p.children.join('|'))));
   if(!el)return null;const s=getComputedStyle(el);const width=el.getBoundingClientRect().width;const child=el.firstElementChild;return {firstChildRatio:child?child.getBoundingClientRect().width/width:null,display:s.display,horizontal:s.columnGap,vertical:s.rowGap,gutterX:s.getPropertyValue('--bs-gutter-x'),gutterY:s.getPropertyValue('--bs-gutter-y')};
  },p);
  const sample=readings.find(r=>r.width===width)?.examples.find(e=>e.id===p.id);
  // 1024,1200,1600,820,375 are all captured above.
  const sampleRatio=sample.children[0]?.width/sample.width;
  const ratioMatch=(actual && Math.abs(actual.firstChildRatio-sampleRatio)<0.012);
  comparisons.push({ratioMatch,id:p.id,width,unit:use.unit,url:use.url,actual,match:!!actual&&ratioMatch&&(actual.display==='flex'?['display','horizontal','vertical','gutterX','gutterY']:['display','horizontal','vertical']).every(k=>actual[k]===sample[k])});
 }
}
const result={date:'2026-11-16',browser:browser.version(),pageCount:inventory.pages.length,signatureCount:inventory.patterns.length,tabChecks,readings,comparisons,errors,axeViolations:axe.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)})),limitations:['Headless Chrome, not physical iPad Safari.','Placeholder specimens test layout geometry; they do not certify every page or content combination.','Responsive tables and record directories are outside the general-layout review.']};
fs.writeFileSync(path.join(out,'review-grid-audit.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({pages:result.pageCount,signatures:result.signatureCount,widths:widths.length,tabChecks:tabChecks.length,overflow:readings.filter(x=>x.overflow).map(x=>x.width),comparisonFailures:comparisons.filter(x=>!x.match),errors,axeViolations:result.axeViolations},null,2));
await browser.close();
if (readings.some(r=>r.overflow) || comparisons.some(c=>!c.match) || errors.length || result.axeViolations.length) process.exitCode=1;
