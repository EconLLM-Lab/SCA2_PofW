// usage (puppeteer-core lives in $TMPDIR/pp): cp shoot.mjs $TMPDIR/pp/ && node $TMPDIR/pp/shoot.mjs <abs shots dir>
// Serves from ../layout-v2/serve.sh (port 5181). Every view at 1440x860 and 1700x1000; prints the object count read from the DOM
// (body[data-count], the [data-obj] elements visible at rest), console errors, and an interaction self-test on the ladder.
import puppeteer from "puppeteer-core";
const out = process.argv[2], base = "http://127.0.0.1:5181/design/layout-v3/v3.html?";
const views = { landing: "view=landing", "landing-s2": "view=landing-s2", ladder: "view=ladder", "ladder-pinned": "view=ladder&pin=23,0",
  matrix: "view=matrix", object: "view=object", "scale-ladder": "view=scale-ladder", "scale-picker": "view=scale-picker", "scale-cohort": "view=scale-cohort", "ladder-fail": "view=ladder&fail=1", "ladder-bank": "view=ladder&item=bank_USA_00023ac74dac", "matrix-bank": "view=matrix&item=bank_USA_00023ac74dac" };
const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: "new" });
const p = await b.newPage(); let errs = []; p.on("console", (m) => m.type() === "error" && errs.push(m.text())); p.on("pageerror", (e) => errs.push(e.message));
const rep = []; let bad = 0;
for (const [w, h] of [[1440, 860], [1700, 1000]]) { await p.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
  for (const [name, q] of Object.entries(views)) { errs = []; await p.goto(base + q, { waitUntil: "networkidle0" }); await new Promise((r) => setTimeout(r, 900));
    const c = await p.evaluate(() => [document.body.dataset.count, document.body.dataset.objs, document.body.dataset.error]);
    await p.screenshot({ path: `${out}/${name}-${w}.png` }); rep.push(`${name}-${w}: ${c[0]} objects [${c[1]}]${c[2] ? " ERROR " + c[2] : ""}${errs.length ? " console: " + errs.join(" | ") : ""}`);
    if (c[2] || errs.length || +c[0] > 9) bad++; } }
// interaction self-test (1440): face switch, pin by click, Esc unpins
await p.setViewport({ width: 1440, height: 860 }); await p.goto(base + "view=ladder", { waitUntil: "networkidle0" }); await new Promise((r) => setTimeout(r, 600));
const t = {}; t.rest = await p.evaluate(() => document.querySelector("#drawer").hidden);
await p.click("rect.cell"); await new Promise((r) => setTimeout(r, 200)); t.pinned = await p.evaluate(() => !document.querySelector("#drawer").hidden && document.querySelector("#drawer h3").textContent);
await p.keyboard.press("Escape"); await new Promise((r) => setTimeout(r, 200)); t.unpinned = await p.evaluate(() => document.querySelector("#drawer").hidden);
await p.click('[data-face="a"]'); await new Promise((r) => setTimeout(r, 400)); t.faceA = await p.evaluate(() => document.querySelector("#lfoot").textContent.includes("= margin"));
rep.push("selftest " + JSON.stringify(t)); if (!(t.rest && t.pinned && t.unpinned && t.faceA)) bad++;
await b.close(); console.log(rep.join("\n")); process.exit(bad ? 1 : 0);
