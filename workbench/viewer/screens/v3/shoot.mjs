// v3 port 1/2: screenshots, at-rest object counts from [data-obj], and a ladder interaction self-test.
// Run from a directory with puppeteer-core (e.g. $TMPDIR/pp):  node <abs>/screens/v3/shoot.mjs <abs out dir>
// Needs the dev server on http://127.0.0.1:5178 (the ?fail flag is dev-only).
import puppeteer from "puppeteer-core";
import fs from "node:fs";
const out = process.argv[2];
const B = "http://127.0.0.1:5178/?";
const P = "a=smol_inst&b=smol_inst_usa_e3";
const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: "new", args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const p = await b.newPage();
let errs = []; p.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); }); p.on("pageerror", (e) => errs.push(e.message));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function load(q) {
  await p.goto(B + q, { waitUntil: "networkidle0", timeout: 60000 });
  await p.waitForFunction("window.__ready === true || String(window.__ready).startsWith('error')", { timeout: 40000 });
  await sleep(500);
}
// what a reader sees at rest: every visible [data-obj]
const count = () => p.evaluate(() => { const o = [...document.querySelectorAll("[data-obj]")].filter((e) => !e.hidden && e.offsetParent !== null && e.getBoundingClientRect().width > 0);
  return { n: o.length, objs: o.map((e) => e.dataset.obj) }; });
const lines = [];
const log = (s) => { lines.push(s); console.log(s); };
const shots = [
  ["ladder", `tab=c&${P}&item=wvs_Q81`],
  ["ladder-pinned", `tab=c&${P}&item=wvs_Q81&sel=23,0`],
  ["ladder-fail", `tab=c&${P}&item=wvs_Q81&fail=dla_gap`],
  ["ladder-bank", `tab=c&${P}&item=bank_USA_00023ac74dac`],
];
for (const [w, h] of [[1440, 860], [1700, 1000]]) {
  await p.setViewport({ width: w, height: h });
  log(`\n## ${w}×${h}`);
  for (const [name, q] of shots) {
    errs = []; await load(q);
    const c = await count();
    await p.screenshot({ path: `${out}/${name}-${w}.png` });
    log(`${name.padEnd(14)} ${c.n} objects at rest: ${c.objs.join(", ")}${errs.length ? "  ERRORS: " + errs.join(" | ") : ""}`);
  }
  for (const [tab, name] of [["b", "matrix (v2 layout, coarse)"], ["a", "object (v2 layout, coarse)"], ["k", "cohort (placeholder)"]]) {
    errs = []; await load(`tab=${tab}&${P}&item=wvs_Q81`);
    const c = await count();
    log(`${name.padEnd(27)} ${c.n} objects: ${c.objs.join(", ")}${errs.length ? "  ERRORS: " + errs.join(" | ") : ""}`);
  }
}
// interaction self-test of the ladder at 1440×860
await p.setViewport({ width: 1440, height: 860 });
errs = []; await load(`tab=c&${P}&item=wvs_Q81`);
const rect = (s) => p.evaluate((s) => { const r = document.querySelector(s)?.getBoundingClientRect(); return r ? { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width } : null; }, s);
const test = {};
const mc0 = await rect("#mc");
await p.evaluate(() => document.querySelector('.cell[data-l="20"][data-h="3"]').dispatchEvent(new MouseEvent("click", { bubbles: true })));
await sleep(300);
const dr = await rect("#drawer"), mc1 = await rect("#mc"), lad1 = await rect("#lad");
test.pin_opens_drawer = !!dr && dr.w > 0;
test.drawer_does_not_cover_chart = !!dr && !!mc1 && mc1.r <= dr.l && mc1.w > 100;
test.drawer_does_not_cover_ladder = !!dr && !!lad1 && lad1.r <= dr.l;
test.chart_width_before_after = [Math.round(mc0.w), Math.round(mc1.w)];
test.pin_marker = await p.evaluate(() => !!document.querySelector("rect.pinm") && !!document.querySelector("#drawer i.pinbox"));
test.url_sel = await p.evaluate(() => new URLSearchParams(location.search).get("sel"));
await p.keyboard.press("Escape"); await sleep(200);
test.esc_unpins = await p.evaluate(() => document.querySelector("#drawer").hidden && !document.querySelector("rect.pinm"));
await p.click('[data-face="a"]'); await sleep(200);
test.face_a = await p.evaluate(() => ({ url: new URLSearchParams(location.search).get("face"), label: document.querySelector("text.facel").textContent, sum: document.querySelector(".sumline").textContent.trim().slice(0, 70) }));
await p.keyboard.press("c"); await sleep(200);
test.clamp_key_shows_frame_chip = await p.evaluate(() => !document.querySelector("#clampchip").hidden);
await p.keyboard.press("c"); await sleep(200);
test.rings = await p.evaluate(() => document.querySelectorAll("rect.ringm").length);
test.passing_glyph = await p.evaluate(() => document.querySelector("#chk").textContent);
await p.keyboard.press("a"); await sleep(200);
test.details_card = await p.evaluate(() => document.querySelector("dialog#learn")?.open && document.querySelector("dialog#learn .lm-h b").textContent);
await p.keyboard.press("Escape"); await sleep(200);
await load(`tab=c&${P}&item=wvs_Q81&fail=dla_gap`);
test.fail_state = await p.evaluate(() => ({ banner: document.querySelector("#failbar")?.textContent.trim().slice(0, 120), glyph: document.querySelector("#chk").textContent,
  green_checks_visible: [...document.querySelectorAll(".sumline.ok, .status.ok, .cons.ok")].filter((e) => e.offsetParent).length, red_faces: [...document.querySelectorAll("[data-face].bad")].map((e) => e.dataset.face) }));
await p.keyboard.press("1"); await sleep(100);
test.page_errors = errs.slice();
log("\n## ladder self-test (1440×860)\n" + JSON.stringify(test, null, 1));
fs.writeFileSync(`${out}/report.txt`, lines.join("\n") + "\n");
await b.close();
