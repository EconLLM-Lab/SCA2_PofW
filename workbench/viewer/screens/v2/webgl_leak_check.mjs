// WebGL leak check: drive N scene rebuilds and assert GPU resources stay flat.
//
// usage: node webgl_leak_check.mjs <url> [n=30] [selectId,selectId,...]
//   The page must expose window.__renderer (THREE.WebGLRenderer) and set window.__ready = true
//   after its first render. Each step picks the next <option> of one of the given <select>
//   elements and dispatches "change" (default ids: hscale,color). Tab buttons can be given as
//   "click:<css selector>" entries instead of select ids.
// needs: npm i puppeteer-core ; system Chrome at the macOS default path (CHROME env overrides).
import puppeteer from "puppeteer-core";

const [url, nArg, idsArg] = process.argv.slice(2);
if (!url) { console.error("usage: node webgl_leak_check.mjs <url> [n] [ids]"); process.exit(2); }
const n = Number(nArg || 30);
const ids = (idsArg || "hscale,color").split(",");
const chrome = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const b = await puppeteer.launch({ executablePath: chrome, headless: "new",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const p = await b.newPage();
await p.setViewport({ width: 1600, height: 950 });
const errors = [];
p.on("pageerror", (e) => errors.push(e.message));
await p.goto(url, { waitUntil: "networkidle0", timeout: 60000 });
await p.waitForFunction("window.__ready === true", { timeout: 30000 });
const mem = () => p.evaluate(() => ({ ...window.__renderer.info.memory }));
const before = await mem();
for (let i = 0; i < n; i++) {
  const id = ids[i % ids.length];
  await p.evaluate((id, i) => {
    if (id.startsWith("click:")) { document.querySelector(id.slice(6))?.click(); return; }
    const s = document.getElementById(id);
    if (!s || !s.options?.length) return;
    s.selectedIndex = (s.selectedIndex + 1 + i) % s.options.length;
    s.dispatchEvent(new Event("change"));
  }, id, i);
  await new Promise((r) => setTimeout(r, 150));
}
const after = await mem();
const lost = await p.evaluate(() => window.__renderer.getContext().isContextLost());
await b.close();
const flat = after.geometries <= before.geometries && after.textures <= before.textures;
console.log(JSON.stringify({ url, rebuilds: n, before, after, context_lost: lost, page_errors: errors, pass: flat && !lost && !errors.length }));
process.exit(flat && !lost && !errors.length ? 0 : 1);
