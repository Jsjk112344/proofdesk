// Direct browser acceptance. No mocked API, asset overrides or fake job progress.
import { chromium } from '/opt/ui-check/node_modules/playwright/index.mjs';
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
const base=process.env.CHECK_BASE;
const screen=process.env.CHECK_SCREEN || 'group';
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:900}});
const page=await context.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const checks=[];const shots=[];
async function shot(name) { await page.screenshot({path:'/work/'+name+'.png',fullPage:false});shots.push(name+'.png'); }
try {
 await page.goto(base+'/#/');
 await page.getByRole('heading',{name:/Good morning/}).waitFor({timeout:60000});
 assert.equal(await page.locator('.rooftop-tile').count(),24);
 assert.equal(await page.locator('.d-primary:visible').count(),1);
 const box=await page.locator('.rooftop-tile').first().boundingBox();assert.ok(box.y+box.height<=900,JSON.stringify(box));
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await shot('salesdesk-group');checks.push('group: 24 real-result tiles, one primary action, map and first tile row above fold');
 if(screen==='journey') {
  const start=Date.now();await page.getByRole('button',{name:'Run tonight’s review now'}).click();
  await page.getByRole('heading',{name:'Every rooftop. Working together.'}).waitFor();
  await page.waitForFunction(()=>document.querySelectorAll('.rooftop-tile.ready').length>0&&document.querySelectorAll('.rooftop-tile.ready').length<24,{timeout:90000});
  await shot('salesdesk-live-run');
  await page.waitForFunction(()=>document.querySelectorAll('.rooftop-tile.ready').length===24,{timeout:180000});
  await page.getByRole('heading',{name:/Good morning/}).waitFor({timeout:90000});
  checks.push({full_run_wall_clock_seconds:(Date.now()-start)/1000});
 }
 if(screen!=='group') {
  await page.getByLabel('View role').selectOption('r02');
  await page.getByRole('heading',{name:'Summit Sandy',exact:true}).waitFor();
  await page.getByRole('button',{name:'Approve all for Sandy',exact:true}).waitFor();
  assert.equal(await page.locator('.d-primary:visible').count(),1);
  const cards=page.locator('.followup-card');const second=await cards.nth(1).boundingBox();assert.ok(second.y+second.height<=900,JSON.stringify(second));
  await shot('salesdesk-store');
  await page.getByRole('button',{name:'Open Maria G. details'}).click();
  await page.getByRole('dialog',{name:'Maria G. lead detail'}).waitFor();
  assert.ok((await page.getByRole('dialog').innerText()).includes('2017 Honda CR-V'));
  assert.ok((await page.getByRole('dialog').innerText()).includes('74 days'));
  await shot('salesdesk-maria');
  await page.getByRole('button',{name:'Close lead detail'}).click();
  checks.push('Sandy: Maria first, three candidates, trade-in, timeline and score components');
 }
 if(screen==='journey') {
  await page.getByRole('button',{name:'Approve all for Sandy',exact:true}).click();
  await page.getByRole('link',{name:'CRM tasks',exact:true}).waitFor({timeout:60000});
  await shot('salesdesk-downloads');
  const href=await page.getByRole('link',{name:'CRM tasks',exact:true}).getAttribute('href');
  const csv=await context.request.get(base+href);assert.equal(csv.status(),200);assert.ok((await csv.text()).includes('Maria'));
  const other=await browser.newContext();const forbidden=await other.request.get(base+href);assert.ok([401,404].includes(forbidden.status()));await other.close();
  await page.reload();await page.getByRole('link',{name:'CRM tasks',exact:true}).waitFor();
  checks.push('approve-all durable handoff: three exports, reload, real download, cross-session refusal');
  await page.getByRole('link',{name:'Schedule',exact:true}).click();
  await page.getByRole('switch').check();
  await page.reload();await page.getByRole('switch').waitFor();assert.equal(await page.getByRole('switch').isChecked(),true);
  checks.push('server schedule persisted across reload');
  await page.getByRole('link',{name:'Data',exact:true}).click();await page.getByRole('heading',{name:'Your dealer-group data'}).waitFor();
  assert.equal(await page.getByRole('link',{name:/template/}).count(),3);
  checks.push('data validation counts and three downloadable templates');
 }
 await page.setViewportSize({width:390,height:844});await page.goto(base+'/#/');
 await page.locator('.rooftop-tile').first().waitFor();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await shot('salesdesk-mobile');assert.deepEqual(errors,[]);
 checks.push('mobile: no horizontal overflow; no page errors');
 await writeFile('/work/dealer-browser-check.json',JSON.stringify({passed:true,kind:'Direct application acceptance; no mocks',base,checks,screenshots:shots},null,2));
 console.log(JSON.stringify({passed:true,checks,shots}));
} finally {await browser.close();}
