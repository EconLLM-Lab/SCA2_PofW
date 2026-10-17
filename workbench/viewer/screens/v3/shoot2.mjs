// v3 port 2/2: screenshots (Matrix, Object, Cohort, landing, learn-more modal, answer pop-over), at-rest object
// counts per tab from [data-obj], and a Matrix / Object interaction self-test.
// Run from a directory with puppeteer-core:  node <abs>/screens/v3/shoot2.mjs <abs out dir>   (dev server on :5178)
import puppeteer from "puppeteer-core";
import fs from "node:fs";
const out = process.argv[2];
const B = "http://127.0.0.1:5178/?", P = "a=smol_inst&b=smol_inst_usa_e3&item=wvs_Q81";
const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: "new", args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const p = await b.newPage();
let errs = []; p.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); }); p.on("pageerror", (e) => errs.push(e.message));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function load(q) { await p.goto(B + q, { waitUntil: "networkidle0", timeout: 60000 }); await p.waitForFunction("window.__ready === true || String(window.__ready).startsWith('error')", { timeout: 40000 }); await sleep(900); }
const count = () => p.evaluate(() => { const o = [...document.querySelectorAll("[data-obj]")].filter((e) => !e.hidden && e.offsetParent !== null && e.getBoundingClientRect().width > 0); return { n: o.length, objs: o.map((e) => e.dataset.obj) }; });
const lines = []; const log = (s) => { lines.push(s); console.log(s); };
const shots = [
  ["ladder", `tab=c&${P}`, null], ["matrix", `tab=b&${P}`, null], ["matrix-pinned", `tab=b&${P}&pin=20,151`, null],
  ["object", `tab=a&${P}`, null], ["cohort", `tab=k&${P}`, null], ["landing", P, null],
  ["learn-modal", `tab=b&${P}&learn=howto-b`, null], ["answer-popover", `tab=b&${P}`, "document.querySelector('button.details').click()"],
];
for (const [w, h] of [[1440, 860], [1700, 1000]]) {
  await p.setViewport({ width: w, height: h }); log(`\n## ${w}×${h}`);
  for (const [name, q, js] of shots) {
    errs = []; await load(q); const c = await count();
    if (js) { await p.evaluate(js); await sleep(400); }
    await p.screenshot({ path: `${out}/${name}-${w}.png` });
    log(`${name.padEnd(15)} ${String(c.n).padStart(2)} objects at rest${c.n > 9 && !name.endsWith("pinned") ? " (OVER BUDGET)" : ""}: ${c.objs.join(", ")}${errs.length ? "  ERRORS: " + errs.join(" | ") : ""}`);
  }
}
await p.setViewport({ width: 1440, height: 860 });
const test = {};
errs = []; await load(`tab=b&${P}`);
test.matrix_default = await p.evaluate(() => ({ qty: document.querySelector("[data-q].on")?.dataset.q, face: document.querySelector("[data-face].on")?.dataset.face, footer: document.querySelector("#bfoot").textContent.trim().slice(0, 90) }));
const cv = await p.evaluate(() => { const r = document.querySelector("#cv").getBoundingClientRect(); return { x: r.left + r.width * 0.6, y: r.top + r.height * 0.4 }; });
await p.mouse.move(cv.x, cv.y); await sleep(250);
test.matrix_hover_tooltip = await p.evaluate(() => !document.querySelector("#ptip").hidden && document.querySelector("#ptip").textContent.split("\n").length);
await p.mouse.click(cv.x, cv.y); await sleep(300);
test.matrix_pin_opens_drawer = await p.evaluate(() => !document.querySelector("#drawer").hidden && document.querySelector("#drawer h3").textContent);
test.matrix_drawer_does_not_cover_map = await p.evaluate(() => document.querySelector("#map").getBoundingClientRect().right <= document.querySelector("#drawer").getBoundingClientRect().left);
await p.keyboard.press("Escape"); await sleep(200);
test.matrix_esc_unpins = await p.evaluate(() => document.querySelector("#drawer").hidden && !new URLSearchParams(location.search).get("pin"));
await p.click('[data-face="a"]'); await sleep(200); await p.click('[data-q="resid"]'); await sleep(200);
test.matrix_switch = await p.evaluate(() => location.search.match(/(face|qty)=\w+/g));
errs = []; await load(`tab=a&${P}`);
test.object_default_view = await p.evaluate(() => ({ view: document.querySelector("[data-view].on")?.dataset.view, labels: [document.querySelector("#labelA").textContent, document.querySelector("#labelB").textContent] }));
const st = await p.evaluate(() => { const a = document.querySelector("#sceneA").getBoundingClientRect(), bb = document.querySelector("#sceneB").getBoundingClientRect(), i = document.querySelector("#insetBox").getBoundingClientRect(); return { a: [a.left, a.right], b: [bb.left, bb.right], inset: [i.left, i.right] }; });
test.object_labels_in_own_scene = st.a[1] <= st.inset[0] && st.inset[1] <= st.b[0];
test.object_inset_has_zero_and_ticks = await p.evaluate(() => !!document.querySelector("#inset line.zero") && document.querySelectorAll("#inset line.ax").length >= 6);
test.page_errors = errs.slice();
log("\n## matrix + object self-test (1440×860)\n" + JSON.stringify(test, null, 1));
fs.writeFileSync(`${out}/report2.txt`, lines.join("\n") + "\n");
await b.close();
