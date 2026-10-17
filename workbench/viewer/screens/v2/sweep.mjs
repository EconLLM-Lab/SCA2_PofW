// Sweep: every pair x item in exports/index.json, in every tab (c, b, a) plus the landing; counts console errors.
import puppeteer from "puppeteer-core";
import fs from "node:fs";
const idx = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: "new", args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const p = await b.newPage(); await p.setViewport({ width: 1600, height: 950 });
let errs = []; p.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); }); p.on("pageerror", (e) => errs.push(e.message));
const rows = [];
for (const pr of idx.pairs) for (const tab of ["", "c", "b", "a"]) {
  errs = []; const q = `${tab ? "tab=" + tab + "&" : ""}a=${pr.a}&b=${pr.b}&item=${pr.item_id}`;
  await p.goto(`http://127.0.0.1:5178/?${q}`, { waitUntil: "networkidle0", timeout: 60000 });
  const ready = await p.waitForFunction("window.__ready === true || String(window.__ready).startsWith('error')", { timeout: 40000 }).then(() => p.evaluate(() => window.__ready)).catch(() => "timeout");
  await new Promise((r) => setTimeout(r, 300));
  rows.push({ q, ready, errors: errs.slice() });
}
await b.close();
const bad = rows.filter((r) => r.ready !== true || r.errors.length);
console.log(JSON.stringify({ pairs: idx.pairs.length, loads: rows.length, failures: bad.length, console_errors: rows.reduce((a, r) => a + r.errors.length, 0), bad, pass: bad.length === 0 }, null, 1));
process.exit(bad.length ? 1 : 0);
