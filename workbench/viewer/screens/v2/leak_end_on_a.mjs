// Stronger leak check: start AND end on tab A (side view), 10 cycles of segment toggles,
// tab switches and view switches in between. Compare GPU memory on the same view.
import puppeteer from "puppeteer-core";
const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: "new", args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const p = await b.newPage(); await p.setViewport({ width: 1600, height: 950 });
const errs = []; p.on("pageerror", (e) => errs.push(e.message));
await p.goto("http://127.0.0.1:5178/?tab=a", { waitUntil: "networkidle0" });
await p.waitForFunction("window.__ready === true");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const click = async (s) => { await p.evaluate((s) => document.querySelector(s)?.click(), s); await sleep(400); };
const mem = async () => { await sleep(2000); return p.evaluate(() => ({ ...window.__renderer.info.memory, lost: window.__renderer.getContext().isContextLost() })); };
const start = await mem(); let steps = 0;
for (let i = 0; i < 10; i++) {
  for (const s of ["#all", "#all", "[data-tab=c]", "[data-tab=b]", "[data-tab=a]", "[data-view=single]", "[data-view=delta]", "[data-view=side]"]) { await click(s); steps++; }
}
const end = await mem();
console.log(JSON.stringify({ steps, start, end, flat: end.geometries <= start.geometries && end.textures <= start.textures, page_errors: errs }));
await b.close();
