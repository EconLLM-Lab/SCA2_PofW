// usage: node shoot.mjs <outdir> <w>x<h> name=queryString [name=query ...]
// Loads http://127.0.0.1:5178/?<query>, waits for window.__ready === true, screenshots, prints console errors.
// A query may end with "#click:<css>" to click an element after load (e.g. a learn-more button).
import puppeteer from "puppeteer-core";
const [out, size, ...shots] = process.argv.slice(2);
const [w, h] = size.split("x").map(Number);
const chrome = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const b = await puppeteer.launch({ executablePath: chrome, headless: "new", args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const p = await b.newPage();
await p.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
let errs = [];
p.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
p.on("pageerror", (e) => errs.push(e.message));
const report = [];
for (const s of shots) {
  const i = s.indexOf("="), name = s.slice(0, i); let q = s.slice(i + 1), click = null, full = false;
  if (q.includes("#click:")) [q, click] = q.split("#click:");
  if (name.endsWith("-full")) full = true;
  errs = [];
  await p.goto(`http://127.0.0.1:5178/?${q}`, { waitUntil: "networkidle0", timeout: 60000 });
  const ok = await p.waitForFunction("window.__ready === true || String(window.__ready).startsWith('error')", { timeout: 30000 }).then(() => p.evaluate(() => window.__ready)).catch((e) => "timeout");
  await new Promise((r) => setTimeout(r, 900));
  if (click) { await p.click(click); await new Promise((r) => setTimeout(r, 500)); }
  await p.screenshot({ path: `${out}/${name}.png`, fullPage: full });
  report.push({ name, q, ready: ok, errors: errs });
}
await b.close();
console.log(JSON.stringify(report, null, 1));
