// Opens the private Space (token via env, never logged) and loads every story route; requires zero console errors.
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const BASE = process.env.SPACE_BASE, OUT = process.argv[2], TOKEN = process.env.HF_TOKEN;
const res = { routes: [], console: [], pageerrors: [], badresponses: [], requestfailed: [] };
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: 'new',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-first-run', '--user-data-dir=' + fs.mkdtempSync(process.env.TMPDIR + '/wb2b-')] });
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function open(tag, url, w = 1440, h = 860) {
  const page = await browser.newPage();
  await page.setViewport({ width: w, height: h });
  await page.setExtraHTTPHeaders({ Authorization: 'Bearer ' + TOKEN });
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') res.console.push({ tag, type: m.type(), text: m.text() }); });
  page.on('pageerror', e => res.pageerrors.push({ tag, text: String(e) }));
  page.on('requestfailed', r => res.requestfailed.push({ tag, url: r.url().replace(BASE, ''), err: r.failure()?.errorText }));
  page.on('response', r => { if (r.status() >= 400) res.badresponses.push({ tag, url: r.url().replace(BASE, ''), status: r.status() }); });
  const resp = await page.goto(BASE + url, { waitUntil: 'networkidle0', timeout: 120000 });
  await sleep(1200);
  const err = await page.evaluate(() => { const e = document.querySelector('#error'); return e && e.textContent.trim() ? e.textContent.trim() : null; });
  return { page, status: resp.status(), err };
}
async function rec(tag, url, extra) {
  const { page, status, err } = await open(tag, url);
  const body = await page.evaluate(() => document.body.innerText.length);
  res.routes.push({ tag, url, status, pageError: err, bodyChars: body });
  if (extra) await extra(page, tag);
  await page.screenshot({ path: `${OUT}/${tag}.png` });
  await page.close();
}
await rec('root', '/'); await rec('tab-a', '/?tab=a'); await rec('tab-b', '/?tab=b'); await rec('tab-c', '/?tab=c');
const story = await open('story', '/sca2/index.html');
const info = await story.page.evaluate(() => ({
  cohort: [...document.querySelectorAll('#cohort-route option')].map(o => o.value),
  ct: [...document.querySelectorAll('#crosstalk-route option')].map(o => o.value),
  links: [...document.querySelectorAll('table.links a')].map(a => a.getAttribute('href')),
  cells: document.querySelectorAll('#cohort-map td').length }));
res.routes.push({ tag: 'story', url: '/sca2/index.html', status: story.status, pageError: story.err, cells: info.cells });
await story.page.screenshot({ path: `${OUT}/story.png`, fullPage: false }); await story.page.close();
for (const r of info.cohort) await rec('story-cohort-' + r, '/sca2/index.html', async (p) => { await p.select('#cohort-route', r); await sleep(500); const n = await p.evaluate(() => document.querySelectorAll('#cohort-map td').length); res.routes.at(-1).cells = n; });
for (const r of info.ct) await rec('story-crosstalk-' + r, '/sca2/index.html', async (p) => { await p.select('#crosstalk-route', r); await sleep(500); const n = await p.evaluate(() => document.querySelectorAll('#crosstalk-map td').length); res.routes.at(-1).cells = n; });
let i = 0; for (const l of info.links) { await rec('featured-' + String(i++).padStart(2, '0'), l); }
await browser.close();
res.summary = { routes: res.routes.length, featuredLinks: info.links.length, consoleMsgs: res.console.length, pageerrors: res.pageerrors.length, badresponses: res.badresponses.length, requestfailed: res.requestfailed.length,
  routeErrors: res.routes.filter(r => r.status !== 200 || r.pageError).length };
fs.writeFileSync(`${OUT}/deployed-report.json`, JSON.stringify(res, null, 1));
console.log(JSON.stringify(res.summary));
