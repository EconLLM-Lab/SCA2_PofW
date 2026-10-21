// Production-static regression sweep. Run with puppeteer-core installed locally or in ~/.hermes.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const puppeteer = require(require.resolve('puppeteer-core', { paths: [process.env.BROWSER_TOOLS || process.cwd(), path.join(process.env.HOME, '.hermes')] }));
const base = process.argv[2] || 'http://127.0.0.1:5189';
const out = process.argv[3] || path.dirname(new URL(import.meta.url).pathname);
fs.mkdirSync(out, { recursive: true });
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage();
const errors = [], requests = [], checks = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(e.message));
page.on('response', r => { requests.push({ url: new URL(r.url()).pathname, status: r.status() }); if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
async function load(url, story = false) {
  await page.goto(base + url, { waitUntil: 'networkidle0', timeout: 60000 });
  await page.waitForFunction(story ? "document.querySelector('#cohort-map tbody tr') !== null" : 'window.__ready === true', { timeout: 60000 });
}
try {
  const D = await (await fetch(base + '/sca2/sca2_data.json')).json();
  await page.setViewport({ width: 1440, height: 860 });
  await load('/sca2/index.html', true);
  const order = await page.$$eval('#cohort-map tbody tr th', es => es.map(e => e.title));
  assert.deepEqual(order, [...order].sort(), 'countries must be grouped by six-sign profile');
  for (const route of Object.keys(D.routes)) {
    await page.select('#cohort-route', route);
    const cells = await page.$$eval('#cohort-map td[data-value]', es => es.map(e => ({ cc: e.dataset.cc, surface: e.dataset.surface, value: e.dataset.value, text: e.textContent, min: +e.dataset.min, max: +e.dataset.max })));
    assert.equal(cells.length, D.countries.length * D.surfaces.length);
    for (const c of cells) {
      const v = D.routes[route].scores[c.cc][c.surface];
      assert.equal(+c.value, v);
      assert.equal(c.text.trim(), v.toFixed(3));
      const all = Object.values(D.routes).flatMap(r => Object.values(r.scores).map(row => row[c.surface]));
      assert.equal(c.min, Math.min(...all)); assert.equal(c.max, Math.max(...all));
    }
    checks.push({ cohort: route, cells: cells.length });
  }
  const lastCountryVisible = await page.$eval('#cohort-map', table => {
    const scroller = table.parentElement;
    scroller.scrollTop = scroller.scrollHeight;
    const last = table.querySelector('tbody tr:last-child').getBoundingClientRect();
    const box = scroller.getBoundingClientRect();
    const visible = last.top >= box.top && last.bottom <= box.bottom;
    scroller.scrollTop = 0;
    return visible;
  });
  assert.equal(lastCountryVisible, true, 'all country rows must be reachable in the inner scroller');
  for (const route of Object.keys(D.crosstalk)) {
    await page.select('#crosstalk-route', route);
    const rows = await page.$$('#crosstalk-map tbody tr');
    assert.equal(rows.length, D.dims.length);
    const cells = await page.$$eval('#crosstalk-map td[data-value]', es => es.map(e => ({ bit: e.dataset.bit, surface: e.dataset.surface, value: +e.dataset.value, text: e.textContent, own: e.classList.contains('own'), title: e.title })));
    assert.equal(cells.length, D.dims.length * D.surfaces.length);
    for (const c of cells) {
      const src = D.crosstalk[route].cells.find(x => x.bit === c.bit && x.surface === c.surface);
      assert.equal(c.value, src.beta); assert.equal(c.text.trim(), src.beta.toFixed(3)); assert.equal(c.own, src.own);
      for (const cid of src.claims) assert.ok(c.title.includes(cid));
    }
    checks.push({ crosstalk: route, cells: cells.length });
  }
  assert.equal(await page.$eval('.audit-label', e => e.textContent.trim()), D.c9.label);
  assert.equal(await page.$eval('#c9 figcaption', e => e.textContent.trim()), 'Label fidelity is not agreement with respondents.');
  const summaries = await page.$$eval('[data-c9-summary]', es => es.map(e => ({ key:e.dataset.c9Summary, value:+e.dataset.value, text:e.querySelector('strong').textContent.trim() })));
  assert.equal(summaries.length, 3);
  for (const row of summaries) {
    const value = D.c9.label_recovery.summary[row.key].value;
    assert.equal(row.value, value); assert.equal(row.text, value.toFixed(3));
  }
  const dots = await page.$$eval('[data-c9-dots] i', es => es.map(e => ({ metric:e.parentElement.dataset.c9Dots, cc:e.dataset.cc, value:+e.dataset.value, title:e.title })));
  assert.equal(dots.length, D.c9.label_recovery.countries.length * 2);
  for (const dot of dots) {
    const row = D.c9.label_recovery.countries.find(r => r.cc === dot.cc);
    assert.equal(dot.value, row[dot.metric]); assert.ok(dot.title.endsWith(row[dot.metric].toFixed(3)));
  }
  const tvd = await page.$$eval('[data-c9-cell]', es => es.map(e => ({ key:e.dataset.c9Cell, value:+e.dataset.value, text:e.querySelector('strong').textContent.trim() })));
  assert.equal(tvd.length, Object.keys(D.c9.tvd_cells).length);
  for (const row of tvd) {
    const value = D.c9.tvd_cells[row.key].value;
    assert.equal(row.value, value); assert.equal(row.text, value.toFixed(3));
  }
  const contrasts = await page.$$eval('[data-c9-contrast]', es => es.map(e => ({ key:e.dataset.c9Contrast, value:+e.dataset.value, lo:+e.dataset.lo, hi:+e.dataset.hi, text:e.querySelector('strong').textContent.trim() })));
  assert.equal(contrasts.length, Object.keys(D.c9.contrasts).length);
  for (const row of contrasts) {
    const c = D.c9.contrasts[row.key];
    assert.equal(row.value, c.value); assert.equal(row.lo, c.ci_low); assert.equal(row.hi, c.ci_high);
    assert.equal(row.text, `${c.value.toFixed(3)} [${c.ci_low.toFixed(3)}, ${c.ci_high.toFixed(3)}]`);
  }
  checks.push({ c9: { summaries:summaries.length, dots:dots.length, tvd:tvd.length, contrasts:contrasts.length } });
  const links = await page.$$eval('a[data-featured]', es => es.map(e => ({ href: e.getAttribute('href'), cc: e.dataset.cc, item: e.dataset.item, model:e.dataset.model, route:e.dataset.route, text: e.textContent })));
  assert.equal(links.length, D.featured.length * 4);
  assert.ok(await page.$eval('#comparison-limit', e => e.textContent.includes('unavailable')));
  const nav = await page.$$eval('nav a', es => es.map(e => e.getAttribute('href')));
  for (const link of nav) assert.ok(link.startsWith('/?tab='));
  await load('/');
  assert.ok(await page.$('a[href="/sca2/index.html"]'), 'root must expose the story entry point');
  for (const link of links) {
    const u = new URL(link.href, base);
    assert.equal(u.pathname, '/'); assert.equal(u.searchParams.get('a'), D.export.base);
    assert.equal(u.searchParams.get('b'), link.model);
    const featured = D.featured.find(f => f.item === link.item && (f.x === link.cc || f.y === link.cc));
    const side = featured.x === link.cc ? 'x' : 'y';
    assert.equal(link.model, link.route === 'adapter' ? `${D.export.base}_${link.cc.toLowerCase()}` : featured[`prompt_${side}`]);
    assert.equal(u.searchParams.get('item'), link.item); assert.ok(link.text.includes('base'));
    const start = requests.length;
    await load(link.href);
    assert.equal(await page.$eval('#selB', e => e.value), u.searchParams.get('b'));
    const fetched = requests.slice(start).filter(r => r.url.startsWith('/exports/'));
    assert.ok(fetched.some(r => r.url.includes('run__') && r.url.endsWith('.bin')));
    assert.ok(fetched.some(r => r.url.includes('pair__') && r.url.endsWith('.bin')));
    checks.push({ featured: link.cc, route:link.route, item: link.item, exportRequests: fetched.length });
  }
  for (const size of [[1440, 860], [1700, 1000]]) {
    const [width, height] = size; await page.setViewport({ width, height });
    for (const [name, url] of [['root', '/'], ['ladder', '/?tab=c'], ['matrix', '/?tab=b'], ['object', '/?tab=a'], ['cohort-empty', '/?tab=k']]) {
      await load(url); await page.screenshot({ path: `${out}/${name}-${width}.png` });
    }
    await load('/sca2/index.html', true);
    await page.screenshot({ path: `${out}/story-${width}.png` });
    for (const [name, id] of [['cohort', '#cohort'], ['crosstalk', '#crosstalk'], ['c9', '#c9'], ['featured', '#featured']]) {
      await page.$eval(id, e => e.scrollIntoView({ block: 'start' }));
      await page.screenshot({ path: `${out}/${name}-${width}.png` });
    }
    for (const route of Object.keys(D.routes)) {
      await page.select('#cohort-route', route);
      await page.$eval('#cohort', e => e.scrollIntoView({ block: 'start' }));
      await page.screenshot({ path: `${out}/cohort-${route}-${width}.png` });
    }
    for (const route of Object.keys(D.crosstalk)) {
      await page.select('#crosstalk-route', route);
      await page.$eval('#crosstalk', e => e.scrollIntoView({ block: 'start' }));
      await page.screenshot({ path: `${out}/crosstalk-${route}-${width}.png` });
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  }
  // Test-only response fixtures: no source files or distributed captures are modified.
  await page.setRequestInterception(true);
  let fixture = 'failed-capture';
  page.on('request', async r => {
    if (fixture === 'empty-story' && r.url().endsWith('/sca2/sca2_data.json')) {
      await r.respond({ status: 200, contentType: 'application/json', body: '{}' });
    } else if (fixture === 'failed-capture' && new URL(r.url()).pathname.startsWith('/exports/run__') && r.url().endsWith('.json')) {
      const data = await (await fetch(r.url())).json();
      data.conservation.pass = false;
      await r.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
    } else await r.continue();
  });
  await load('/?tab=c');
  assert.ok(await page.$('#failbar'));
  checks.push({ failedCaptureBanner: true });
  fixture = 'empty-story';
  await page.goto(base + '/sca2/index.html', { waitUntil: 'networkidle0' });
  await page.waitForSelector('[role="alert"]');
  assert.ok(await page.$eval('[role="alert"]', e => e.textContent.includes('unavailable')));
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ pass: true, checks, errors, requests }, null, 2));
  fs.writeFileSync(`${out}/browser-report.json`, JSON.stringify({ pass: true, checks, errors, requests }, null, 2) + '\n');
} catch (e) {
  fs.writeFileSync(`${out}/browser-report.json`, JSON.stringify({ pass: false, failure: String(e), checks, errors, requests }, null, 2) + '\n');
  throw e;
} finally { await browser.close(); }
