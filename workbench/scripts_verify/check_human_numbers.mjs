// WB7-H acceptance: serve an EXTRACTED bundle, open the Ladder and the Cohort in headless Chrome, and check every human
// number on screen against human_reference.json (numbers only; this script never reads or prints a respondent row).
//   node check_human_numbers.mjs <extracted-bundle-dir> on|off <shots-dir> [human_reference.json]
// "on":  the Ladder line, the all-answers table, each Cohort tick, each yes/no marker and each row tooltip equal the file (and the
//        marker equals a fresh computation from index.json); sign-prompt rows carry no tick; the legend entry is there.
// "off": no human element anywhere, no console or page error, no failed request except the missing file itself.
// Prints counts and PASS/FAIL lines only. Exit 0 = all pass.
import { createServer } from "node:http";
import { readFileSync, existsSync, statSync, mkdirSync, openSync, readSync, closeSync } from "node:fs";
import { join, extname, resolve } from "node:path";
import { createRequire } from "node:module";
const puppeteer = createRequire(new URL("../viewer/", import.meta.url))("puppeteer-core");

const [dirArg, mode, shots, refPath] = process.argv.slice(2);
const dir = resolve(dirArg);
mkdirSync(shots, { recursive: true });
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".bin": "application/octet-stream" };
const server = createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.endsWith("/")) p += "index.html";
  const f = join(dir, p);
  if (!f.startsWith(dir) || !existsSync(f) || !statSync(f).isFile()) { res.writeHead(404); res.end("not found"); return; }
  const size = statSync(f).size, type = MIME[extname(f)] ?? "application/octet-stream", r = req.headers.range?.match(/bytes=(\d+)-(\d*)/);
  if (r) {
    const a = +r[1], b = Math.min(size - 1, r[2] ? +r[2] : size - 1), buf = Buffer.alloc(b - a + 1), fd = openSync(f, "r");
    readSync(fd, buf, 0, buf.length, a); closeSync(fd);
    res.writeHead(206, { "Content-Type": type, "Content-Range": `bytes ${a}-${b}/${size}`, "Accept-Ranges": "bytes", "Content-Length": buf.length }); res.end(buf);
  } else { res.writeHead(200, { "Content-Type": type, "Content-Length": size, "Accept-Ranges": "bytes" }); res.end(readFileSync(f)); }
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const base = `http://127.0.0.1:${server.address().port}`;
const index = JSON.parse(readFileSync(join(dir, "exports/index.json"), "utf8"));
const ref = mode === "on" ? JSON.parse(readFileSync(refPath, "utf8")) : null;
const ccOf = (k) => index.models[k]?.label.match(/\+ ([A-Z]{3}) LoRA/)?.[1] ?? null;
const itemInfo = (iid, model) => JSON.parse(readFileSync(join(dir, "exports", index.runs.find((r) => r.model === model && r.item_id === iid).file), "utf8")).item;
const probs = (m, iid) => index.runs.find((r) => r.model === m && r.item_id === iid)?.probs;
const hp = (v) => (v < 1 ? "<1%" : `${v}%`);

let fails = 0, checks = 0;
const ok = (c, msg) => { checks++; if (!c) { fails++; console.log("FAIL", msg); } };
// independent marker: the stated rule, from index.json probabilities and the file's rounded numbers
function expectMarker(iid, aKey, bKey, cell) {
  const it = itemInfo(iid, aKey), pa = probs(aKey, iid), pb = probs(bKey, iid);
  const mean = it.codes.length > 2 && cell.mean != null;
  const exp = (p) => it.codes.reduce((s, c) => s + (p[c] ?? 0) * Number(c), 0);
  const h = mean ? cell.mean : (cell.shares[it.j_plus] ?? 0) / 100;
  const a = mean ? exp(pa) : pa[it.j_plus], b = mean ? exp(pb) : pb[it.j_plus];
  return { closer: Math.abs(b - h) < Math.abs(a - h), mean, it };
}

const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900 });
const errors = [], failed = [];
page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(String(e)));
page.on("response", (r) => { if (r.status() >= 400) failed.push(`${r.status()} ${new URL(r.url()).pathname}`); });
const open = async (qs, wait = 20000) => {
  await page.goto(`${base}/?${qs}`, { waitUntil: "load" });
  await page.waitForFunction(() => window.__ready === true || String(window.__ready).startsWith("error"), { timeout: wait });
  const r = await page.evaluate(() => String(window.__ready));
  ok(r === "true", `${qs}: __ready=${r}`);
  await new Promise((s) => setTimeout(s, 400));   // the human line fills after its own fetch
};
const BAN = /accura|validat|correct|TVD|Spearman|total variation/i;

// ---------------- Ladder: every shipped (item, adapter) pair on a wvs_ question
const pairs = index.pairs.filter((p) => p.item_id.startsWith("wvs_") && ccOf(p.b) && !index.models[p.a].label.includes(" LoRA"));
console.log(`ladder pairs: ${pairs.length}`);
let shot = 0;
for (const p of pairs) {
  const cc = ccOf(p.b), cell = ref?.items[p.item_id]?.cells[cc];
  const run = index.runs.find((r) => r.model === p.b && r.item_id === p.item_id);
  if (run && index.comparators?.find((c) => c.model === p.b && c.tier === "numbers")) continue;   // numbers-only comparators have no Ladder
  await open(`tab=c&a=${encodeURIComponent(p.a)}&b=${encodeURIComponent(p.b)}&item=${p.item_id}`);
  const v = await page.evaluate(() => { const h = document.getElementById("human"); return h ? { hidden: h.hidden, text: h.innerText, n: [...h.querySelectorAll('[data-hum="n"]')].map((e) => e.textContent), mk: h.querySelector('[data-hum="marker"]')?.textContent ?? null } : null; });
  if (mode === "off") { ok(v && v.hidden && v.text === "", `${p.item_id} ${cc}: human line must stay hidden when the file is absent`); }
  else if (!cell) { ok(v && !v.hidden && /no survey data/.test(v.text), `${p.item_id} ${cc}: expected "no survey data"`); }
  else {
    const m = expectMarker(p.item_id, p.a, p.b, cell), want = m.mean ? [hp(cell.shares[cell.top]), cell.mean.toFixed(1)] : [hp(cell.shares[m.it.j_plus] ?? 0)];
    ok(v && !v.hidden, `${p.item_id} ${cc}: human line visible`);
    // table cells (all answers) are the file's shares in code order; headline numbers come first
    const table = m.it.codes.map((c) => hp(cell.shares[c] ?? 0));
    ok(JSON.stringify(v.n.slice(0, want.length)) === JSON.stringify(want), `${p.item_id} ${cc}: headline ${v.n.slice(0, want.length)} vs file ${want}`);
    ok(JSON.stringify(v.n.slice(want.length)) === JSON.stringify(table), `${p.item_id} ${cc}: table ${v.n.slice(want.length)} vs file ${table}`);
    ok(v.mk === (m.closer ? "closer to the survey than the base model" : "further from the survey than the base model"), `${p.item_id} ${cc}: marker "${v.mk}" vs expected closer=${m.closer}`);
    ok(!BAN.test(v.text), `${p.item_id} ${cc}: banned word on the Ladder line`);
    ok(/respondents/.test(v.text) && /chose|chose/.test(v.text), `${p.item_id} ${cc}: "respondents ... chose" wording`);
  }
  if (shot < 2 && p.item_id === "wvs_Q57" && ["CHN", "USA", "BGD"].includes(cc)) { shot++; await page.screenshot({ path: join(shots, `ladder-${mode}-${cc}-1440.png`) }); }
}
// a Ladder on a sign prompt or an unrelated question shows no human line (checked on a bank item when one is shipped)
const bank = index.pairs.find((p) => p.item_id.startsWith("bank_"));
if (bank) { await open(`tab=c&a=${encodeURIComponent(bank.a)}&b=${encodeURIComponent(bank.b)}&item=${bank.item_id}`); ok(await page.evaluate(() => document.getElementById("human").hidden), "bank item: no human line"); }

// ---------------- Cohort, Q57 (42 adapters + 26 sign prompts) and every other item with a picker entry
const q57 = index.pairs.find((p) => p.item_id === "wvs_Q57" && ccOf(p.b));
const itemsK = [...new Set(index.pairs.filter((p) => p.a === q57.a && p.item_id.startsWith("wvs_")).map((p) => p.item_id))];
for (const iid of itemsK) {
  const ps = index.pairs.filter((p) => p.a === q57.a && p.item_id === iid);
  if (ps.length < 3) continue;
  await open(`tab=k&a=${encodeURIComponent(q57.a)}&b=${encodeURIComponent(ps[0].b)}&item=${iid}&show=both`);
  const rows = await page.evaluate(() => [...document.querySelectorAll("#krows .k-row[data-b]")].map((r) => ({ b: r.dataset.b, tick: r.querySelector(".k-hu")?.style.left ?? null, sv: r.querySelector(".k-sv")?.textContent ?? null, label: r.getAttribute("aria-label") })));
  const legend = await page.evaluate(() => document.querySelector(".k-legend")?.innerText ?? "");
  const head = await page.evaluate(() => [...document.querySelectorAll(".k-axis .k-sv")].map((e) => e.textContent));
  console.log(`cohort ${iid}: ${rows.length} rows`);
  if (mode === "off") {
    ok(rows.every((r) => r.tick == null && r.sv == null) && !/WVS-7/.test(legend) && head.length === 0, `${iid}: no human element in the Cohort`);
    ok(!(await page.$("#ksort [data-sort=survey]")), `${iid}: no survey sort`);
  } else {
    ok(/people in that country \(WVS-7\)/.test(legend), `${iid}: legend entry`);
    ok(head.join("") === "closer to survey than base?", `${iid}: column header`);
    for (const r of rows) {
      const cc = ccOf(r.b), cell = cc && ref.items[iid]?.cells[cc];
      if (!cc) { ok(r.tick == null && r.sv === "–", `${iid} ${r.b.slice(-8)}: sign prompt must have no tick (tick=${r.tick}, sv=${r.sv})`); continue; }
      if (!cell) { ok(r.tick == null && r.sv === "no survey data", `${iid} ${cc}: no data renders "no survey data"`); continue; }
      const m = expectMarker(iid, q57.a, r.b, cell), want = cell.shares[m.it.j_plus] ?? 0;
      ok(r.tick === `${want}%`, `${iid} ${cc}: tick ${r.tick} vs file ${want}%`);
      ok(r.sv === (m.closer ? "yes" : "no"), `${iid} ${cc}: marker ${r.sv} vs expected ${m.closer ? "yes" : "no"}`);
      const t = r.label.match(/Survey: (<1%|\d+%) of respondents/);
      ok(t && t[1] === hp(want), `${iid} ${cc}: tooltip number ${t?.[1]} vs ${hp(want)}`);
      ok(!BAN.test(r.label.replace(/“[^”]*”/g, "")) , `${iid} ${cc}: banned word in a row label`);
    }
    if (iid === "wvs_Q57") {
      await open(`tab=k&a=${encodeURIComponent(q57.a)}&b=${encodeURIComponent(ps[0].b)}&item=${iid}&sort=survey`);
      const order = await page.evaluate(() => [...document.querySelectorAll("#krows .k-row[data-b] .k-sv")].map((e) => e.textContent));
      const rank = (t) => ({ yes: 0, no: 1, "no survey data": 2 }[t] ?? 3), sorted = order.every((t, i) => !i || rank(order[i - 1]) <= rank(t));
      ok(sorted && order.length === 42, `sort=survey: ${order.length} rows, ordered=${sorted}`);
      console.log(`sort=survey: yes ${order.filter((t) => t === "yes").length}, no ${order.filter((t) => t === "no").length}`);
      await page.screenshot({ path: join(shots, `cohort-${mode}-survey-sort-1440.png`) });
      await open(`tab=k&a=${encodeURIComponent(q57.a)}&b=${encodeURIComponent(ps[0].b)}&item=${iid}`);
    }
  }
  if (iid === "wvs_Q57") { await page.screenshot({ path: join(shots, `cohort-${mode}-q57-1440.png`) }); await page.screenshot({ path: join(shots, `cohort-${mode}-q57-full-1440.png`), fullPage: false, clip: { x: 0, y: 0, width: 1440, height: 520 } }); }
}
if (mode === "off") ok(failed.every((f) => /human_reference\.json/.test(f)), `off: unexpected failed requests ${failed.filter((f) => !/human_reference/.test(f))}`);
else ok(failed.length === 0, `on: failed requests ${failed}`);
ok(errors.length === 0, `console/page errors: ${errors.slice(0, 3)}`);
await browser.close(); server.close();
console.log(`${mode}: ${checks} checks, ${fails} failed -> ${fails ? "FAIL" : "PASS"}`);
process.exit(fails ? 1 : 0);
