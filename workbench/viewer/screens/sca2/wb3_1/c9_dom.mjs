import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
const puppeteer = require(require.resolve('puppeteer-core', {
  paths: [process.env.BROWSER_TOOLS || process.cwd(), path.join(process.env.HOME, '.hermes')],
}));
const base = process.argv[2];
const out = process.argv[3];
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
const dom = {};
try {
  for (const [width, height] of [[1440, 860], [1700, 1000]]) {
    const page = await browser.newPage();
    await page.setViewport({ width, height });
    await page.goto(base + '/sca2/index.html', { waitUntil: 'networkidle0', timeout: 60000 });
    await page.waitForFunction('window.__storyReady === true', { timeout: 60000 });
    dom[`c9-${width}`] = await page.evaluate(() => {
      const all = selector => [...document.querySelectorAll(selector)];
      return {
        summ: all('[data-c9-summary]').map(e => ({
          k: e.dataset.c9Summary, v: e.dataset.value, txt: e.querySelector('strong').textContent.trim(),
        })),
        cells: all('[data-c9-cell]').map(e => ({
          k: e.dataset.c9Cell, v: e.dataset.value, txt: e.querySelector('strong').textContent.trim(),
        })),
        contr: all('[data-c9-contrast]').map(e => ({
          k: e.dataset.c9Contrast, v: e.dataset.value, lo: e.dataset.lo, hi: e.dataset.hi,
          txt: e.querySelector('strong').textContent.trim(), title: e.title,
        })),
        dots: all('[data-c9-dots]').map(e => ({
          k: e.dataset.c9Dots,
          n: e.querySelectorAll('i').length,
          vals: [...e.querySelectorAll('i')].map(i => [i.dataset.cc, i.dataset.value]),
        })),
      };
    });
    await page.close();
  }
  fs.writeFileSync(out, JSON.stringify({ dom }, null, 2) + '\n');
} finally {
  await browser.close();
}
