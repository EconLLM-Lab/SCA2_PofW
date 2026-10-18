// Card t_58fed76a — verification harness for the viewer's relative-gate reader.
//
// What it proves, with no dependency beyond the project's own `dist/` build and Google Chrome:
//   1. a capture@1.1 run manifest with `conservation.relative` (a float32 export) draws the frame
//      as a PASS: the status glyph is ✓, no fail banner, and its "checks" pop-up is the relative
//      table (`rel ≤ τ`) with every row ✓ — the old reader would have drawn it red on the absolute
//      thresholds, which is exactly the bug this card fixes;
//   2. a float32 manifest whose one relative check carries `pass: false` still raises the red,
//      non-dismissible `#failbar` (the never-hide rule);
//   3. a float64 export (no `relative` block, the exports already on disk) still draws the legacy
//      absolute table — the reader change is a no-op for it.
//
// It also sweeps every real pair in the exports index across the four tabs plus the landing and
// counts console errors, and writes screenshots of the three states.
//
// Usage:  FXDIR=/tmp/fx OUT=<dir> node verify.mjs
// Needs `viewer/dist` built first (`npm run build`).
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { readFileSync, writeFileSync, existsSync, mkdirSync, copyFileSync, mkdtempSync } from "node:fs";
import { join, extname, resolve } from "node:path";
import { tmpdir } from "node:os";

const DIR = import.meta.dirname;                                  // viewer/screens/f32-gates
const VIEWER = resolve(DIR, "../..");                             // viewer/
const EXPORTS = resolve(VIEWER, "../exports");                    // workbench/exports (real captures)
const DIST = join(VIEWER, "dist");
const FXDIR = process.env.FXDIR || join(tmpdir(), "f32-gates-fixtures");
const OUT = process.env.OUT || join(VIEWER, "screens", "f32-gates");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const ITEM = "wvs_Q81";

// ------------------------------------------------------------------ fixtures (cloned from a real float64 export)
// The numbers are the measured SmolLM2-135M float32 values from plans/stage1_f32_gaps.md
// (section 1) and the taus gates.py calibrates from them, so the fixture is what a real float32
// capture of smol_base / wvs_Q81 would write: the absolute residual gate is red (5.55e-3 ≥ 1e-3)
// but the relative gate is green (6.23e-6 ≤ 1e-4).
const TAUS_F32 = { residual_closure: 1e-4, step_closure: 1e-5, head_closure: 1e-5,
                   readout: 1e-3, pair_attribution: 1e-6, logits_reference: 1e-4 };
const TAU_MULTIPLE = 10.0;

function gate(name, error, scale, scale_desc, tau) {
  const rel = scale ? error / scale : Infinity;
  return { name, error, scale, scale_desc, rel, tau, pass: rel <= tau };
}
function relBlock(gates, reference_key) {
  const checks = {};
  for (const g of gates) checks[g.name] = { error: g.error, scale: g.scale, scale_desc: g.scale_desc, rel: g.rel, tau: g.tau, pass: g.pass };
  return { taus: TAUS_F32, tau_multiple: TAU_MULTIPLE, checks, pass: gates.every((g) => g.pass), reference_key };
}
// The relative gate set of one float32 run. `breakResidual` flips the residual closure, the check a
// dropped head write trips (stage1_f32_gaps.md §5: 218x over tau in float32).
function runRelatives(breakResidual) {
  return relBlock([
    gate("residual_closure", breakResidual ? 2.70e-1 : 5.55e-3, 891, "max|h^L| over positions and features, floored at 1", TAUS_F32.residual_closure),
    gate("step_closure", 2.50e-4, 891, "max|h^l_t| at the worst (layer, position), floored at 1", TAUS_F32.step_closure),
    gate("head_closure", 0, 191, "max|a^l| over layers, positions and features, floored at 1", TAUS_F32.head_closure),
    gate("readout", 3.90e-5, 1.7327, "|margin| + 1", TAUS_F32.readout),
    gate("residual_closure_clamped", 4.80e-3, 880, "max|h^L| over positions and features, floored at 1", TAUS_F32.residual_closure),
    gate("step_closure_clamped", 2.10e-4, 880, "max|h^l_t| at the worst (layer, position), floored at 1", TAUS_F32.step_closure),
    gate("head_closure_clamped", 0, 188, "max|a^l| over layers, positions and features, floored at 1", TAUS_F32.head_closure),
    gate("readout_clamped", 3.10e-5, 1.70, "|margin| + 1", TAUS_F32.readout),
    gate("logits_reference", 1.50e-3, 338, "max|logits_reference|, floored at 1", TAUS_F32.logits_reference),
  ], "hf_logits_max_rel_gap");
}

function makeFixtures() {
  mkdirSync(FXDIR, { recursive: true });
  const read = (p) => JSON.parse(readFileSync(p, "utf8"));
  const baseRun = read(join(EXPORTS, `run__smol_base__${ITEM}.json`));
  const basePair = read(join(EXPORTS, `pair__smol_base__smol_inst__${ITEM}.json`));
  const index = read(join(EXPORTS, "index.json"));

  // A float32 export is a pair of float32 captures: both sides carry `relative`, which is what the
  // conservation pop-up keys on. So A and B are both fixtures here (as on disk for the 8B f32 pair).
  const variants = [
    { key: "smol_f32", label: "SmolLM2-135M · float32 fixture A (relative gates pass)", bad: false },
    { key: "smol_f32_b", label: "SmolLM2-135M · float32 fixture B (relative gates pass)", bad: false },
    { key: "smol_f32_bad", label: "SmolLM2-135M · float32 fixture A (one relative gate fails)", bad: true },
  ];
  const runs = [], models = {};
  for (const { key, label, bad } of variants) {
    const run = structuredClone(baseRun);
    run.model = { ...run.model, key, label, model_id: "HuggingFaceTB/SmolLM2-135M", adapter: null };
    run.provenance = { ...run.provenance, compute_dtype: "float32", fixture: "f32-gates verify harness" };
    run.conservation = {
      ...run.conservation,
      residual_closure_inf: 5.55e-3, head_closure_inf: 0, dla_gap: 3.90e-5,
      dla_gap_clamped: 3.10e-5, residual_closure_inf_clamped: 4.80e-3,
      hf64_logits_max_rel_gap: 3.40e-10,
      relative: runRelatives(bad), pass: !bad, legacy_absolute_applicable: false,
    };
    writeFileSync(join(FXDIR, `run__${key}__${ITEM}.json`), JSON.stringify(run));
    copyFileSync(join(EXPORTS, `run__smol_base__${ITEM}.bin`), join(FXDIR, `run__${key}__${ITEM}.bin`));
    models[key] = { model_id: "HuggingFaceTB/SmolLM2-135M", adapter: null, label };
    runs.push({ file: `run__${key}__${ITEM}.json`, model: key, label, item_id: ITEM,
                T: run.tokens.length, pass: !bad, margin: run.readout.margin });
  }
  const pairs = [];
  for (const [a, b] of [["smol_f32", "smol_f32_b"], ["smol_f32_bad", "smol_f32_b"]]) {
    const pair = structuredClone(basePair);
    pair.a = a; pair.b = b; pair.item_id = ITEM;
    const scale = Math.abs(pair.d_margin) + 1;
    pair.conservation = {
      ...pair.conservation,
      relative: relBlock([
        gate("gap_f64", 6.10e-8, scale, "|d_margin| + 1", TAUS_F32.pair_attribution),
        gate("gap_f32", 7.40e-8, scale, "|d_margin| + 1", TAUS_F32.pair_attribution),
      ], "d_attr_gap"),
      pass: true, legacy_absolute_applicable: false,
    };
    const file = `pair__${a}__${b}__${ITEM}.json`;
    writeFileSync(join(FXDIR, file), JSON.stringify(pair));
    copyFileSync(join(EXPORTS, `pair__smol_base__smol_inst__${ITEM}.bin`), join(FXDIR, file.replace(/\.json$/, ".bin")));
    pairs.push({ file, a, b, item_id: ITEM, d_margin: pair.d_margin });
  }
  index.models = { ...index.models, ...models };
  index.runs = [...index.runs, ...runs];
  index.pairs = [...index.pairs, ...pairs];
  writeFileSync(join(FXDIR, "index.json"), JSON.stringify(index));
  // The static server serves /exports from FXDIR only, so every real manifest and binary the index
  // references must be present there too (never overwrite the fixture files written above).
  for (const f of [...index.runs.map((r) => r.file), ...index.pairs.map((p) => p.file)]) {
    for (const name of [f, f.replace(/\.json$/, ".bin")]) {
      if (!existsSync(join(FXDIR, name)) && existsSync(join(EXPORTS, name))) copyFileSync(join(EXPORTS, name), join(FXDIR, name));
    }
  }
  return index;
}

// ------------------------------------------------------------------ static server: dist + fixture exports
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".bin": "application/octet-stream", ".svg": "image/svg+xml" };
function serve() {
  return new Promise((ready) => {
    const srv = createServer((req, res) => {
      const url = decodeURIComponent((req.url || "/").split("?")[0]);
      const file = url.startsWith("/exports/")
        ? join(FXDIR, url.slice("/exports/".length))
        : join(DIST, url === "/" ? "index.html" : url);
      if (!existsSync(file)) { res.writeHead(404); res.end("not found"); return; }
      res.writeHead(200, { "Content-Type": MIME[extname(file)] || "application/octet-stream", "Cache-Control": "no-store" });
      res.end(readFileSync(file));
    });
    srv.listen(0, "127.0.0.1", () => ready(srv));
  });
}

// ------------------------------------------------------------------ headless Chrome over CDP (no deps)
async function withChrome(fn) {
  const port = 9300 + Math.floor(Math.random() * 600);
  const chrome = spawn(CHROME, ["--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
    "--hide-scrollbars", "--window-size=1700,1000", `--remote-debugging-port=${port}`,
    `--user-data-dir=${mkdtempSync(join(tmpdir(), "cdp-"))}`, "about:blank"], { stdio: "ignore" });
  let targets;
  for (let i = 0; i < 60; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.some((t) => t.type === "page")) break; } catch {}
    await new Promise((r) => setTimeout(r, 200));
  }
  const ws = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let id = 0; const pending = new Map(); const consoleErrors = [];
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.method === "Runtime.exceptionThrown") consoleErrors.push("exception: " + (m.params?.exceptionDetails?.exception?.description || m.params?.exceptionDetails?.text || "unknown"));
    else if (m.method === "Runtime.consoleAPICalled" && m.params?.type === "error") consoleErrors.push("console.error: " + (m.params.args || []).map((a) => a.value ?? a.description ?? "").join(" "));
    if (pending.has(m.id)) { pending.get(m.id)(m.result ?? m.error); pending.delete(m.id); }
  });
  const send = (method, params = {}) => new Promise((r) => { pending.set(++id, r); ws.send(JSON.stringify({ id, method, params })); });
  const ev = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })).result?.value;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  await send("Runtime.enable"); await send("Page.enable");
  const navigate = async (url) => {
    consoleErrors.length = 0;
    await send("Page.navigate", { url });
    for (let i = 0; i < 160; i++) { const r = await ev("window.__ready"); if (r === true || (typeof r === "string" && r.startsWith("error"))) break; await sleep(250); }
    await sleep(800);
  };
  const shot = async (path) => { const s = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(path, Buffer.from(s.data, "base64")); };
  try { return await fn({ navigate, ev, shot, consoleErrors, sleep }); }
  finally { try { ws.close(); } catch {} chrome.kill(); }
}

// ------------------------------------------------------------------ the run
const index = makeFixtures();
const srv = await serve();
const base = `http://127.0.0.1:${srv.address().port}`;
mkdirSync(OUT, { recursive: true });
const report = { cases: [], sweep: null, fails: [] };
const check = (name, cond, detail) => { report.cases.push({ name, ok: !!cond, detail }); if (!cond) report.fails.push(`${name}: ${detail}`); };

await withChrome(async ({ navigate, ev, shot, consoleErrors, sleep }) => {
  // --- case 1: float64 export (no relative block) — legacy absolute table, unchanged
  await navigate(`${base}/?tab=c&a=smol_base&b=smol_inst&item=${ITEM}`);
  await shot(join(OUT, "f64-frame.png"));
  let dom = await ev(`(() => ({ status: document.querySelector('#status')?.className, chk: document.querySelector('#chk')?.textContent, failbar: !!document.querySelector('#failbar') }))()`);
  check("f64 frame", dom.status === "status ok" && /^\u2713/.test(dom.chk || "") && !dom.failbar, JSON.stringify(dom));
  let errs64 = consoleErrors.slice();
  await navigate(`${base}/?tab=c&a=smol_base&b=smol_inst&item=${ITEM}&learn=conservation`);
  await shot(join(OUT, "f64-checks.png"));
  let body = await ev(`document.querySelector('dialog#learn .lm-b')?.innerHTML ?? ''`);
  check("f64 checks = legacy table", body.includes("Must be below") && !body.includes("rel \u2264") && body.includes("float64 arithmetic"), `len=${body.length}`);
  check("f64 no console errors", errs64.length === 0, errs64.join(" | "));

  // --- case 2: float32 fixture, relative gates pass
  await navigate(`${base}/?tab=c&a=smol_f32&b=smol_f32_b&item=${ITEM}`);
  await shot(join(OUT, "f32-frame.png"));
  dom = await ev(`(() => ({ status: document.querySelector('#status')?.className, chk: document.querySelector('#chk')?.textContent, failbar: !!document.querySelector('#failbar') }))()`);
  check("f32 frame = pass", dom.status === "status ok" && /^\u2713/.test(dom.chk || "") && !dom.failbar, JSON.stringify(dom));
  let errs32 = consoleErrors.slice();
  await navigate(`${base}/?tab=c&a=smol_f32&b=smol_f32_b&item=${ITEM}&learn=conservation`);
  await shot(join(OUT, "f32-checks.png"));
  body = await ev(`document.querySelector('dialog#learn .lm-b')?.innerHTML ?? ''`);
  const relRows = (body.match(/rel \u2264/g) || []).length;
  check("f32 checks = relative rows, all ✓", relRows >= 3 && !body.includes("\u2717") && body.includes("float32"), `relRows=${relRows} crosses=${(body.match(/\u2717/g) || []).length}`);
  check("f32 no console errors", errs32.length === 0, errs32.join(" | "));

  // --- case 3: float32 fixture, one relative check fails -> the banner must appear
  await navigate(`${base}/?tab=c&a=smol_f32_bad&b=smol_f32_b&item=${ITEM}`);
  await shot(join(OUT, "f32fail-frame.png"));
  dom = await ev(`(() => ({ status: document.querySelector('#status')?.className, chk: document.querySelector('#chk')?.textContent, failbar: document.querySelector('#failbar')?.textContent ?? null }))()`);
  check("f32 fail frame = banner", dom.status === "status bad" && /^\u2717/.test(dom.chk || "") && !!dom.failbar && dom.failbar.includes("residual_closure"), JSON.stringify({ status: dom.status, chk: dom.chk, hasBar: !!dom.failbar }));
  await navigate(`${base}/?tab=c&a=smol_f32_bad&b=smol_base&item=${ITEM}&learn=conservation`);
  await shot(join(OUT, "f32fail-checks.png"));
  body = await ev(`document.querySelector('dialog#learn .lm-b')?.innerHTML ?? ''`);
  check("f32 fail checks show a ✗ row", body.includes("\u2717") && body.includes("residual_closure"), `crosses=${(body.match(/\u2717/g) || []).length}`);

  // --- sweep: every real pair across the four tabs + landing, console errors counted
  const realPairs = index.pairs.filter((p) => !p.a.startsWith("smol_f32"));
  let loads = 0, errors = 0; const bad = [];
  for (const p of realPairs) for (const tab of ["", "c", "b", "a", "k"]) {
    const q = `${tab ? "tab=" + tab + "&" : ""}a=${p.a}&b=${p.b}&item=${p.item_id}`;
    await navigate(`${base}/?${q}`);
    loads++;
    if (consoleErrors.length) { errors += consoleErrors.length; bad.push({ q, errors: consoleErrors.slice() }); }
  }
  report.sweep = { loads, console_errors: errors, bad };
  check("sweep 0 console errors", errors === 0, `${errors} over ${loads} loads`);
});

srv.close();
report.pass = report.fails.length === 0;
writeFileSync(join(OUT, "report.json"), JSON.stringify(report, null, 1));
console.log(JSON.stringify(report, null, 1));
process.exit(report.pass ? 0 : 1);
