// layout-v3 mockups (card t_b31e4996). One page, many views: ?view=landing|landing-s2|ladder|matrix|object|
// scale-ladder|scale-picker|scale-cohort. Real views bind to the exports through ../layout-v2/common.js
// (loadBundle, a plain-JS port of viewer/src/data.ts). Scale views are shape-faithful placeholders and
// carry the badge "illustration · not data". Every object at rest carries data-obj; ?count=0 hides the
// numbered overlay. B − A of two run arrays is only used where named "browser" below.
import { loadBundle, fmt, sgn, esc, mix } from "../layout-v2/common.js";

const U = new URLSearchParams(location.search);
const VIEW = U.get("view") || "ladder";
const Q = { a: U.get("a") || "smol_inst", b: U.get("b") || "smol_inst_usa_e3", item: U.get("item") || "wvs_Q81" };
const $ = (s, r = document) => r.querySelector(s);
const COL = { A: "#cfc8bb", B: "#4fc1a6", pos: "#6b9bff", neg: "#ff9a3c", delta: "#ffcf5c", clamp: "#c58bff", neutral: "#2a2a2e" };
const div = (v, m) => mix(COL.neutral, v >= 0 ? COL.pos : COL.neg, Math.sqrt(Math.min(1, Math.abs(v) / (m || 1))));
const svgNS = "http://www.w3.org/2000/svg";
const el = (tag, attrs = {}, parent) => { const e = document.createElementNS(svgNS, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); if (parent) parent.appendChild(e); return e; };
const tip = $("#tip");
const showTip = (ev, text) => { tip.hidden = false; tip.textContent = text; tip.style.left = ev.clientX + 16 + "px"; tip.style.top = ev.clientY + 12 + "px"; };
const hideTip = () => (tip.hidden = true);
function rng(seed) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const gauss = (r) => Math.sqrt(-2 * Math.log(r() + 1e-12)) * Math.cos(2 * Math.PI * r());

// ------------------------------------------------------------------ data (real views)
let D = null, F = null;   // F: bound fields, see bind()
function bind(D) {
  const A = D.A, B = D.B, P = D.P, it = A.m.item;
  const full = (c) => String(it.labels[it.codes.indexOf(c)]), lab = (c) => { const t = full(c); return t.length > 34 ? t.slice(0, 32).replace(/\s+\S*$/, "") + " …" : t; };
  // gated checks: every key of each manifest's `thresholds` (run A, run B, pair) → value <= threshold
  const checks = [];
  for (const [who, m] of [["A", A.m], ["B", B.m], ["pair", P.m]])
    for (const [k, thr] of Object.entries(m.conservation.thresholds)) checks.push({ who, k, v: m.conservation[k], thr, ok: m.conservation[k] <= thr });
  if (U.get("fail") === "1") { checks[1] = { ...checks[1], v: 0.031, ok: false, simulated: true }; }   // demo of the rule only
  return { A, B, P, it, full, L: A.m.model.n_layers, H: A.m.model.n_heads, ro: A.m.readout.position, lab, jp: it.j_plus, jm: it.j_minus, checks,
    segs: A.m.segments, tokens: A.m.tokens.map((t) => t.text) };
}

// ------------------------------------------------------------------ frame + answer strip (shared)
function frame({ tab, a, b, item, checks, illus }) {
  const fails = checks.filter((c) => !c.ok);
  const tabs = [["ladder", "Ladder"], ["matrix", "Matrix"], ["object", "Object"]].concat(illus ? [["scale-cohort", "Cohort"]] : [])
    .map(([v, t]) => `<a href="?view=${v}" class="${tab === v ? "on" : ""}">${t}</a>`).join("");
  return `<section id="frame" data-obj="frame">
    <div class="r1"><span class="brand">SCA2 workbench</span><nav class="tabs">${tabs}</nav><span class="sp"></span>
      ${illus ? `<span class="illus">illustration · not data</span>` : ""}
      <span class="pill" style="${fails.length || illus ? "display:none" : ""}" title="${checks.map((c) => `${c.who} ${c.k} ${fmt(c.v, 2)} ≤ ${c.thr}`).join("\n")}">✓ ${checks.length} checks</span>
      <span class="q" title="how to read this view (?)">?</span></div>
    <div class="r2"><span class="slot a" data-slot="a"><span class="dot"></span><span class="k">A</span>${esc(a)}<span class="chev">▾</span></span>
      <span class="vs">vs</span><span class="slot b" data-slot="b"><span class="dot"></span><span class="k">B</span>${esc(b)}<span class="chev">▾</span></span>
      <span class="slot item"><span class="k muted">item</span>${esc(item)}<span class="chev">▾</span></span></div>
  </section>${fails.length ? `<div id="failbar" data-obj="fail"><b>✗ ${fails.length} check${fails.length > 1 ? "s" : ""} failed</b> · ${fails.map((c) => `${c.who} ${c.k} = ${fmt(c.v, 3)} > ${c.thr}${c.simulated ? " (simulated with ?fail=1 · not data)" : ""}`).join(" · ")}. The numbers below are not conserved; read them with that in mind.</div>` : ""}`;
}
function answerStrip(F) {
  const mA = F.A.m.readout.margin, mB = F.B.m.readout.margin, d = F.P.m.d_margin, mx = Math.max(Math.abs(mA), Math.abs(mB));
  const pA = F.A.m.readout.probs[F.jp], pB = F.B.m.readout.probs[F.jp];
  return `<section id="answer" data-obj="answer" title="click or press A: the full answer card (codes, four probabilities, clamped run)">
    <span class="say">B ${d >= 0 ? "pushes" : "pulls"} the answer <b title="${esc(F.full(F.jp))}">${d >= 0 ? "further toward" : "back from"} “${F.jp}” (${esc(F.lab(F.jp))})</b> <span class="mono" style="color:var(--delta)">${sgn(d, 3)}</span></span>
    <span class="mini">A <i style="width:${60 * Math.abs(mA) / mx}px;background:var(--A)"></i>${fmt(mA, 3)}</span>
    <span class="mini">B <i style="width:${60 * Math.abs(mB) / mx}px;background:var(--B)"></i>${fmt(mB, 3)}</span>
    <span class="mini">P(“${F.jp}”) ${pA.toFixed(2)} → ${pB.toFixed(2)}</span><span class="q" style="margin-left:auto">A</span></section>`;
}

// ------------------------------------------------------------------ ladder (one face at a time)
function ladderSVG(host, { L, H, val, face, rings = [], pin, kv = 0, onPick, colLabel }) {
  const W = host.clientWidth, Hh = host.clientHeight, lab = 36, mgap = 10, kvgap = kv ? 3 : 0, ng = kv ? H / kv - 1 : 0;
  const s = Math.max(6, Math.min(26, (W - lab - mgap - ng * kvgap) / (H + 1.6), (Hh - 26) / L));
  const svg = el("svg", { width: W, height: L * s + 26 }); host.innerHTML = ""; host.appendChild(svg);
  let vmax = 0; for (let l = 0; l < L; l++) for (let h = -1; h < H; h++) vmax = Math.max(vmax, Math.abs(val(l, h)));
  const x = (h) => (h < 0 ? lab + H * s + ng * kvgap + mgap : lab + h * s + (kv ? Math.floor(h / kv) * kvgap : 0));
  for (let l = 0; l < L; l++) {
    const y = (L - 1 - l) * s;
    if (l % 5 === 0 || l === L - 1 || (pin && pin[0] === l)) el("text", { x: lab - 6, y: y + s * .72, "text-anchor": "end", fill: pin && pin[0] === l ? COL.delta : "#8a8a8f" }, svg).textContent = "L" + l;
    for (let h = -1; h < H; h++) {
      const v = val(l, h), w = h < 0 ? s * 1.6 : s;
      const r = el("rect", { x: x(h) + .5, y: y + .5, width: w - 1.5, height: s - 1.5, rx: 1.5, fill: div(v, vmax), class: "cell", style: "cursor:pointer" }, svg);
      if (rings.some(([a, b]) => a === l && b === h)) el("rect", { x: x(h) - .5, y: y - .5, width: w + .5, height: s + .5, rx: 2, fill: "none", stroke: COL.delta, "stroke-width": 1.3 }, svg);
      if (pin && pin[0] === l && pin[1] === h) el("rect", { x: x(h) - 1.5, y: y - 1.5, width: w + 2.5, height: s + 2.5, rx: 2, fill: "none", stroke: "#fff", "stroke-width": 2 }, svg);
      r.addEventListener("mousemove", (ev) => showTip(ev, `${h < 0 ? "MLP" : "head " + h} · layer ${l}\n${face}: ${sgn(v, 3)}`));
      r.addEventListener("mouseleave", hideTip);
      r.addEventListener("click", () => onPick && onPick(l, h));
    }
  }
  const yb = L * s + 14;
  el("text", { x: lab, y: yb }, svg).textContent = colLabel || `heads 0–${H - 1}`;
  el("text", { x: x(-1), y: yb }, svg).textContent = "MLP";
  const used = Math.max(x(-1) + s * 1.6 + 8, 400); svg.setAttribute("width", used); host.style.height = L * s + 26 + "px";
  return { s, vmax, top: 0, rowsH: L * s, used };
}
function marginColumn(host, { L, series, s, rowsH, key }) {
  const W = host.clientWidth, svg = el("svg", { width: W, height: rowsH + 26 }); host.innerHTML = ""; host.appendChild(svg);
  let lo = 0, hi = 0; for (const [, arr] of series) for (const v of arr) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  const px = (v) => 8 + (W - 80) * (v - lo) / (hi - lo || 1), py = (k) => (L - k) * s;
  el("line", { x1: px(0), x2: px(0), y1: 0, y2: rowsH, stroke: "#333", "stroke-dasharray": "2 3" }, svg);
  for (const [c, arr, name] of series) {
    el("polyline", { points: arr.map((v, k) => `${px(v)},${py(k)}`).join(" "), fill: "none", stroke: c, "stroke-width": 1.8 }, svg);
    el("text", { x: W - 64, y: name === "A" ? 26 : 12, fill: c }, svg).textContent = `${name} ${fmt(arr[L], 3)}`;
  }
  el("text", { x: 8, y: rowsH + 14 }, svg).textContent = key;
}
function promptHTML(F, shade) {
  const tk = F.tokens, open = new Set(["question", "options", "answer_cue", "readout"]), hidden = F.segs.filter((s) => !open.has(s.kind));
  const hn = hidden.reduce((a, s) => a + (s.b - s.a), 0);
  let html = `<div class="tpl" title="${esc(hidden.map((s) => s.label).join(" · "))}">⋯ template text · ${hidden.length} parts · ${hn} tokens${shade ? ` · Σ attention ${hidden.reduce((a, s) => { for (let i = s.a; i < s.b; i++) a += shade.w[i] || 0; return a; }, 0).toFixed(2)}` : ""}</div>`;
  for (const s of F.segs.filter((s) => open.has(s.kind))) {
    if (s.kind === "question") html += `<div class="cap seglab">${F.it.kind === "bank" ? "Scenario" : "Survey question"}</div>`;
    if (s.kind === "readout") { html += ` <span class="ro" title="answer position t*=${F.ro}">t*</span>`; continue; }
    html += `<span>`;
    for (let i = s.a; i < s.b; i++) {
      const w = shade ? shade.w[i] || 0 : 0;
      const bg = w ? `background:${mix("#0c0c0d", shade.c, Math.min(1, Math.sqrt(w / shade.max)))}` : "";
      html += `<span class="tk" style="${bg}" title="#${i}${w ? " · " + w.toFixed(3) : ""}">${esc(tk[i]).replace(/\n/g, "<br>")}</span>`;
    }
    html += `</span>`;
  }
  return html;
}
function attnRow(run, l, h, t) { const w = {}; for (let k = 0; k < 16; k++) { const i = run.t.attn_topk_idx.get(l, h, t, k), v = run.t.attn_topk_val.get(l, h, t, k); w[i] = (w[i] || 0) + v; } return w; }

function viewLadder(root, F) {
  const face = U.get("face") || "d"; let pin = U.get("pin") ? U.get("pin").split(",").map(Number) : null;
  const vals = { a: (l, h) => (h < 0 ? F.A.t.mlp_attr.get(l) : F.A.t.head_attr.get(l, h)), b: (l, h) => (h < 0 ? F.B.t.mlp_attr.get(l) : F.B.t.head_attr.get(l, h)),
    d: (l, h) => (h < 0 ? F.P.t.d_mlp_attr.get(l) : F.P.t.d_head_attr.get(l, h)) };
  const emb = { a: F.A.m.readout.embed_attr, b: F.B.m.readout.embed_attr, d: F.P.m.d_embed_attr }, tot = { a: F.A.m.readout.margin, b: F.B.m.readout.margin, d: F.P.m.d_margin };
  const all = []; for (let l = 0; l < F.L; l++) for (let h = -1; h < F.H; h++) all.push([l, h, Math.abs(vals.d(l, h))]);
  const rings = all.sort((x, y) => y[2] - x[2]).slice(0, 5).map(([l, h]) => [l, h]);
  root.innerHTML = `${frame({ tab: "ladder", a: F.A.m.model.label, b: F.B.m.model.label, item: F.it.kind === "bank" ? `${F.it.item_id} · scenario` : `${F.it.item_id} · ${F.lab(F.jp).toLowerCase()} … ${F.lab(F.jm).toLowerCase()}`, checks: F.checks })}
  ${answerStrip(F)}
  <div id="work" style="grid-template-columns:repeat(12,1fr)">
    <section class="obj" data-obj="prompt" style="grid-column:span 4"><header><span class="cap">The prompt</span><span class="q">?</span></header><div class="ptext" id="pt" style="max-height:calc(100vh - 400px);overflow-y:auto;-webkit-mask-image:linear-gradient(#000 88%,transparent)"></div><div class="foot" id="pkey"></div></section>
    <div style="grid-column:span 8;display:flex;gap:var(--g)"><section class="obj" data-obj="ladder" style="flex:1 1 auto"><header><span class="cap" style="white-space:nowrap">Push on the answer · t*</span><span class="sp"></span>
      <span class="seg">${[["a", "A"], ["b", "B"], ["d", "B − A"]].map(([k, t]) => `<button data-face="${k}" class="${face === k ? "on " + k : ""}">${t}</button>`).join("")}</span><span class="q">?</span></header>
      <div id="lad" style="height:calc(100vh - 360px)"></div><div class="foot" id="lfoot"></div></section>
    <section class="obj" data-obj="margin" style="flex:0 0 230px"><header><span class="cap">Margin by layer</span></header><div id="mc" style="height:calc(100vh - 360px)"></div></section></div>
  </div><aside id="drawer" hidden></aside>`;
  const draw = () => {
    const g = ladderSVG($("#lad"), { L: F.L, H: F.H, val: vals[face], face: { a: "A push", b: "B push", d: "B − A push" }[face], rings, pin,
      onPick: (l, h) => { pin = pin && pin[0] === l && pin[1] === h ? null : [l, h]; draw(); } });
    $("#lad").parentElement.style.flex = `0 0 ${g.used}px`;
    let sum = emb[face]; for (let l = 0; l < F.L; l++) for (let h = -1; h < F.H; h++) sum += vals[face](l, h);
    const ok = Math.abs(sum - tot[face]) < 1e-3;
    $("#lfoot").innerHTML = `<span><i style="display:inline-block;width:46px;height:7px;background:linear-gradient(90deg,${COL.neg},${COL.neutral},${COL.pos})"></i> toward “${esc(F.lab(F.jm))}” · toward “${esc(F.lab(F.jp))}” (±${fmt(g.vmax, 2)})</span>
      <span class="${ok ? "ok" : "bad"}">${ok ? "✓" : "✗"} cells + embedding = ${fmt(sum, 4)} ${ok ? "=" : "≠"} ${face === "d" ? "d_margin" : "margin"} ${fmt(tot[face], 4)}</span>${face === "d" ? `<span style="color:var(--delta)">◻ gold = 5 largest changes</span>` : ""}`;
    marginColumn($("#mc"), { L: F.L, s: g.s, rowsH: g.rowsH, key: "after k layers", series: [[COL.A, Array.from(F.A.t.running_margin.data), "A"], [COL.B, Array.from(F.B.t.running_margin.data), "B"]] });
    // prompt shading only exists while a head is pinned (A or B face: that run; B − A face: B, labelled)
    let shade = null;
    if (pin && pin[1] >= 0) { const run = face === "a" ? F.A : F.B; const w = attnRow(run, pin[0], pin[1], F.ro); shade = { w, max: Math.max(...Object.values(w)), c: face === "a" ? COL.A : COL.B }; }
    $("#pt").innerHTML = promptHTML(F, shade);
    $("#pkey").innerHTML = shade ? `shaded: where ${face === "a" ? "A" : "B"}'s layer ${pin[0]} head ${pin[1]} looks from t* (attn_topk_val, top 16)` : "";
    const dr = $("#drawer");
    if (!pin) { dr.hidden = true; } else {
      const [l, h] = pin, isH = h >= 0, row = (n, a, b, d, f = 4) => `<tr><td>${n}</td><td>${fmt(a, f)}</td><td>${fmt(b, f)}</td><td class="ch">${d == null ? "" : (typeof d === "string" ? d : sgn(d, 3))}</td></tr>`;
      const top = (run) => { const w = attnRow(run, l, h, F.ro); return Object.entries(w).sort((x, y) => y[1] - x[1]).slice(0, 6).map(([i, v]) => `<div><span>${v.toFixed(2)}</span><span>#${i} “${esc(F.tokens[i].replace(/\n/g, "⏎"))}”</span></div>`); };
      const ta = isH ? top(F.A) : [], tb = isH ? top(F.B) : [];
      dr.hidden = false; dr.setAttribute("data-obj", "drawer"); dr.style.top = $("#work").offsetTop + "px";
      dr.innerHTML = `<div style="display:flex;align-items:center"><h3>${isH ? "Head " + h : "MLP"} · layer ${l}</h3><span class="sp"></span><button id="unpin">Esc</button></div>
        <div class="muted">pinned · ${rings.some(([a, b]) => a === l && b === h) ? "one of the five largest changes" : "click another cell to move the pin"}</div>
        <table><tr><th></th><th style="color:var(--A)">A</th><th style="color:var(--B)">B</th><th style="color:var(--delta)">change</th></tr>
        ${isH ? row("Push on the margin", F.A.t.head_attr.get(l, h), F.B.t.head_attr.get(l, h), F.P.t.d_head_attr.get(l, h))
              + row("Write size at t*", F.A.t.head_norm.get(l, h, F.ro), F.B.t.head_norm.get(l, h, F.ro), "‖Δ‖ " + fmt(F.P.t.d_head_norm.get(l, h, F.ro), 3))
              + row("Top-16 coverage", F.A.t.attn_topk_mass.get(l, h, F.ro), F.B.t.attn_topk_mass.get(l, h, F.ro), null)
              : row("Push on the margin", F.A.t.mlp_attr.get(l), F.B.t.mlp_attr.get(l), F.P.t.d_mlp_attr.get(l))
              + row("Write size at t*", F.A.t.mlp_norm.get(l, F.ro), F.B.t.mlp_norm.get(l, F.ro), "‖Δ‖ " + fmt(F.P.t.d_mlp_norm.get(l, F.ro), 3))}
        </table>
        ${isH ? `<div class="cap" style="margin:6px 0">Where it looks from t*</div><div class="att"><div class="cap" style="color:var(--A)">A</div><div class="cap" style="color:var(--B)">B</div>${ta.map((x, i) => x + tb[i]).join("")}</div>
        <div class="foot">weights moved (q,k,v,o): ${Array.from({ length: 4 }, (_, k) => fmt(F.P.t.d_weight_head.get(l, h, k), 2)).join(" · ")}</div>` : ""}`;
      $("#unpin").onclick = () => { pin = null; draw(); };
    }
    numberObjects();
  };
  root.querySelectorAll("[data-face]").forEach((b) => (b.onclick = () => { U.set("face", b.dataset.face); history.replaceState(0, "", "?" + U); viewLadder(root, F); }));
  addEventListener("keydown", (e) => { if (e.key === "Escape") { pin = null; draw(); } });
  requestAnimationFrame(draw);
}

// ------------------------------------------------------------------ matrix (one map, one face)
function viewMatrix(root, F) {
  const face = U.get("face") || "d", qty = U.get("qty") || "resid";
  const arr = { resid: ["resid_norm", "d_resid_norm"], attn: ["attn_norm", "d_attn_norm"], mlp: ["mlp_norm", "d_mlp_norm"] }[qty];
  const T = F.tokens.length, open = new Set(["question", "options", "answer_cue", "readout"]);
  root.innerHTML = `${frame({ tab: "matrix", a: F.A.m.model.label, b: F.B.m.model.label, item: F.it.item_id, checks: F.checks })}${answerStrip(F)}
  <div id="work" style="grid-template-columns:repeat(12,1fr)">
    <section class="obj" data-obj="toolbar" style="grid-column:span 12;display:flex;gap:18px;align-items:center">
      <span class="cap">Size of</span><span class="seg">${[["resid", "running state ‖h‖"], ["attn", "attention write"], ["mlp", "MLP write"]].map(([k, t]) => `<button data-qty="${k}" class="${qty === k ? "on" : ""}">${t}</button>`).join("")}</span>
      <span class="cap">face</span><span class="seg">${[["a", "A"], ["b", "B"], ["d", "‖B − A‖"]].map(([k, t]) => `<button data-face="${k}" class="${face === k ? "on " + k : ""}">${t}</button>`).join("")}</span>
      <span class="muted">template text squeezed to 2 px</span><span class="sp"></span><span class="q">?</span></section>
    <section class="obj" data-obj="map" style="grid-column:span 10"><canvas id="cv"></canvas><div class="foot" id="mfoot"></div></section>
    <section class="obj" data-obj="margin" style="grid-column:span 2"><div id="mc"></div></section>
  </div>`;
  const run = face === "a" ? F.A : F.B, t = face === "d" ? F.P.t[arr[1]] : run.t[arr[0]], R = t.shape[0];
  const host = $("#cv").parentElement, W = host.clientWidth, Hh = Math.min(innerHeight - 330, 620), band = 20, s = (Hh - band - 18) / R;
  const sq = F.segs.filter((g) => !open.has(g.kind)).reduce((a, g) => a + g.b - g.a, 0), wOpen = (W - 2 * sq) / (T - sq);
  const xs = [], ws = []; let x = 0; const kindOf = (i) => F.segs.find((g) => i >= g.a && i < g.b)?.kind;
  for (let i = 0; i < T; i++) { const w = open.has(kindOf(i)) ? wOpen : 2; xs.push(x); ws.push(w); x += w; }
  const cv = $("#cv"); cv.width = W * 2; cv.height = Hh * 2; cv.style.width = W + "px"; cv.style.height = Hh + "px";
  const c = cv.getContext("2d"); c.scale(2, 2);
  const vals = Array.from(t.data).sort((a, b) => a - b), p99 = vals[Math.floor(vals.length * .99)], vmax = vals[vals.length - 1];
  for (let r = 0; r < R; r++) for (let i = 0; i < T; i++) {
    const f = Math.min(1, t.get(r, i) / p99);
    c.fillStyle = face === "d" ? mix("#141414", COL.delta, f) : mix("#141414", "#e9e6df", f); c.fillRect(xs[i], band + (R - 1 - r) * s, ws[i] + .3, s + .3);
  }
  for (const g of F.segs) { const x0 = xs[g.a], x1 = g.b < T ? xs[g.b] : W; c.fillStyle = open.has(g.kind) ? "#2a2a2e" : "#1a1a1d"; c.fillRect(x0, 0, x1 - x0 - 1, band - 4);
    if (open.has(g.kind) && x1 - x0 > 40) { c.fillStyle = "#b8b6af"; c.font = "11px ui-monospace,Menlo"; c.fillText(g.label, x0 + 5, 12); } }
  c.strokeStyle = "#fff"; c.lineWidth = 1.5; c.strokeRect(xs[F.ro] + .5, band, ws[F.ro] - 1, R * s);
  cv.onmousemove = (ev) => { const b = cv.getBoundingClientRect(), mx = ev.clientX - b.left, my = ev.clientY - b.top - band; const i = xs.findIndex((x0, k) => mx >= x0 && mx < x0 + ws[k]); const r = R - 1 - Math.floor(my / s);
    if (i < 0 || r < 0 || r >= R) return hideTip(); showTip(ev, `layer ${r} · #${i} “${F.tokens[i].replace(/\n/g, "⏎")}”\nA ${fmt(F.A.t[arr[0]].get(r, i), 3)}  B ${fmt(F.B.t[arr[0]].get(r, i), 3)}  ‖Δ‖ ${fmt(F.P.t[arr[1]].get(r, i), 3)}`); };
  cv.onmouseleave = hideTip;
  $("#mfoot").innerHTML = `<span><i style="display:inline-block;width:46px;height:7px;background:linear-gradient(90deg,#141414,${face === "d" ? COL.delta : "#e9e6df"})"></i> 0 → ${fmt(p99, 3)} (99th pct, linear); max ${fmt(vmax, 3)} · ${face === "d" ? "pair " + arr[1] + ": length of the change, its own scale" : "run " + arr[0] + " of " + face.toUpperCase()}</span><span>rows: layers, L0 at the bottom · dark bands: template text, ${sq} tokens at 2 px · white frame: t*</span>`;
  const mh = $("#mc"); mh.style.marginTop = band + "px"; mh.style.height = R * s + "px";
  marginColumn(mh, { L: F.L, s: (R * s) / F.L, rowsH: R * s, key: "margin if read off", series: [[COL.A, Array.from(F.A.t.running_margin.data), "A"], [COL.B, Array.from(F.B.t.running_margin.data), "B"]] });
  root.querySelectorAll("[data-face],[data-qty]").forEach((b) => (b.onclick = () => { if (b.dataset.face) U.set("face", b.dataset.face); if (b.dataset.qty) U.set("qty", b.dataset.qty); location.search = U; }));
  numberObjects();
}

// ------------------------------------------------------------------ 3D object, at rest (isometric SVG stand-in for the three.js scene)
function isoScene(host, run, F, label, color, scale) {
  const open = new Set(["question", "options", "answer_cue", "readout"]), cols = []; let x = 0;
  for (const g of F.segs) { if (open.has(g.kind)) for (let i = g.a; i < g.b; i++) cols.push([i, x++]); else { x += 1.5; } }
  const W = host.clientWidth, Hh = host.clientHeight, R = run.t.resid_norm.shape[0];
  const ux = (W - 80) / (x + R * 0.55), zx = ux * 0.55, zy = Math.min(ux * 0.9, Hh * 0.30 / R), hm = Hh * 0.5;
  const svg = el("svg", { width: W, height: Hh }); host.innerHTML = `<header><span class="cap" style="color:${color}">${label}</span></header>`; host.appendChild(svg);
  const ox = 30, oy = Hh - 34 - Math.max(0, (Hh - 70 - hm - R * zy) / 2);
  for (let z = R - 1; z >= 0; z--) for (const [i, xx] of cols) {
    const v = run.t.resid_norm.get(z, i), h = hm * Math.log1p(v / scale.v0) / Math.log1p(scale.vmax / scale.v0);
    const px = ox + xx * ux + z * zx, py = oy - z * zy;
    el("line", { x1: px, y1: py, x2: px, y2: py - Math.max(1, h), stroke: i === F.ro ? "#ffffff" : mix("#3a3a3e", color, 0.25 + 0.6 * z / R), "stroke-width": Math.max(1, ux * 0.62) }, svg);
  }
  el("text", { x: ox, y: oy + 22 }, svg).textContent = "tokens →  (template collapsed)";
  el("text", { x: ox + x * ux + 4, y: oy + 6 }, svg).textContent = "L0";
  el("text", { x: ox + x * ux + (R - 1) * zx + 4, y: oy - (R - 1) * zy + 6 }, svg).textContent = `L${R - 1} ↗`;
}
function viewObject(root, F) {
  root.innerHTML = `${frame({ tab: "object", a: F.A.m.model.label, b: F.B.m.model.label, item: F.it.item_id, checks: F.checks })}${answerStrip(F)}
  <div id="work" style="grid-template-columns:repeat(12,1fr);row-gap:22px">
    <section class="obj" data-obj="scenebar" style="grid-column:span 12;display:flex;gap:18px;align-items:center"><span class="cap">Show</span>
      <span class="seg"><button>A only</button><button class="on">A next to B</button><button>A next to ‖B − A‖</button></span><span class="cap">camera</span>
      <span class="seg"><button class="on">1 answer position</button><button>2 whole object</button><button>3 from above</button><button>4 layer stack</button></span><span class="sp"></span>
      <span class="muted">height = size of ‖h‖ (log) · white column = t*</span><span class="q">?</span></section>
    <section class="obj" data-obj="sceneA" id="sa" style="grid-column:span 5;height:calc(100vh - 440px)"></section>
    <section class="obj" data-obj="inset" style="grid-column:span 2;align-self:center"><header><span class="cap">margin if read off</span></header><div id="ins" style="height:150px"></div></section>
    <section class="obj" data-obj="sceneB" id="sb" style="grid-column:span 5;height:calc(100vh - 440px)"></section>
    <section class="obj" data-obj="minimap" style="grid-column:span 12"><canvas id="mm"></canvas></section>
  </div>`;
  let vmax = 0; const sample = []; for (const r of [F.A, F.B]) for (const v of r.t.resid_norm.data) { vmax = Math.max(vmax, v); sample.push(v); }
  sample.sort((a, b) => a - b); const sc = { vmax, v0: sample[sample.length >> 1] };
  requestAnimationFrame(() => {
    isoScene($("#sa"), F.A, F, "A · " + F.A.m.model.label, COL.A, sc); isoScene($("#sb"), F.B, F, "B · " + F.B.m.model.label, COL.B, sc);
    const ih = $("#ins"), W = ih.clientWidth, svg = el("svg", { width: W, height: 150 }); ih.appendChild(svg);
    const a = Array.from(F.A.t.running_margin.data), b = Array.from(F.B.t.running_margin.data), lo = Math.min(0, ...a, ...b), hi = Math.max(...a, ...b);
    const px = (k) => 4 + (W - 50) * k / F.L, py = (v) => 130 - 120 * (v - lo) / (hi - lo);
    el("line", { x1: 4, x2: W - 46, y1: py(0), y2: py(0), stroke: "#333", "stroke-dasharray": "2 3" }, svg);
    for (const [c, arr, n] of [[COL.A, a, "A"], [COL.B, b, "B"]]) { el("polyline", { points: arr.map((v, k) => `${px(k)},${py(v)}`).join(" "), fill: "none", stroke: c, "stroke-width": 1.6 }, svg);
      el("text", { x: px(F.L) + 4, y: py(arr[F.L]) + 4, fill: c }, svg).textContent = `${n} ${fmt(arr[F.L], 3)}`; }
    el("text", { x: 4, y: 146 }, svg).textContent = `L0 … L${F.L}`;
    // minimap: run resid_norm of A for every token; bands from manifest.segments; bracket = tokens in view
    const cv = $("#mm"), mw = cv.parentElement.clientWidth, mh = 64, T = F.tokens.length, R = F.A.t.resid_norm.shape[0];
    cv.width = mw * 2; cv.height = mh * 2; cv.style.width = mw + "px"; cv.style.height = mh + "px"; const c = cv.getContext("2d"); c.scale(2, 2);
    for (let r = 0; r < R; r++) for (let i = 0; i < T; i++) { const f = Math.log1p(F.A.t.resid_norm.get(r, i) / sc.v0) / Math.log1p(sc.vmax / sc.v0); c.fillStyle = mix("#141414", "#cfc8bb", f); c.fillRect(i * mw / T, 18 + (R - 1 - r) * (mh - 18) / R, mw / T + .3, (mh - 18) / R + .3); }
    c.font = "11px ui-monospace,Menlo";
    for (const g of F.segs) { const x0 = g.a * mw / T, x1 = g.b * mw / T; const op = ["question", "options", "answer_cue", "readout"].includes(g.kind);
      c.fillStyle = op ? "#2f2f34" : "#1a1a1d"; c.fillRect(x0, 0, x1 - x0 - 1, 14); if (x1 - x0 > 60) { c.fillStyle = op ? "#d8d6d0" : "#77777c"; c.fillText(g.label, x0 + 4, 11); }
      if (op) { c.strokeStyle = "#ffffff88"; c.strokeRect(x0 + .5, 16.5, x1 - x0 - 1, mh - 17); } }
    numberObjects();
  });
}

// ------------------------------------------------------------------ landing
function viewLanding(root, F, section) {
  const nav = `<nav class="nav" data-obj="nav"><span class="brand">SCA2 workbench</span><span class="sp"></span><a href="#">How it works</a><a href="#">Limits</a><a href="#">Terms</a><a class="open" href="?view=ladder">Open the workbench →</a></nav>`;
  if (!section) {
    root.innerHTML = `${nav}<div class="hero">
      <div style="grid-column:span 5"><h1 data-obj="h1">Where does a language model's <em>survey answer</em> come from?</h1>
        <div data-obj="lede"><p class="lede">We ask a small language model a survey question. Its answer is a probability for each response code. We split that answer into the contributions of the model's parts, check that they add up, and compare a model before and after a fine-tune, part by part.</p>
        <p class="small">For readers who know regression and survey items. No machine-learning background assumed.</p></div>
        <div class="cta" data-obj="cta"><a class="p" href="?view=ladder">Open the workbench</a><a href="?view=landing-s2">How it works ↓</a></div></div>
      <figure data-obj="hero" style="grid-column:7 / span 6"><div class="cap">The margin, layer by layer · real data</div><div id="hc" style="height:330px;margin-top:10px"></div>
        <figcaption class="muted" style="margin-top:10px">${esc(F.it.item_id)}: B ends ${sgn(F.P.m.d_margin, 3)} toward “${esc(F.lab(F.jp))}” than A. <a href="#" style="color:var(--text)">Read the story</a></figcaption></figure></div>`;
    requestAnimationFrame(() => { const h = $("#hc"), W = h.clientWidth, H = 330, svg = el("svg", { width: W, height: H }); h.appendChild(svg);
      const a = Array.from(F.A.t.running_margin.data), b = Array.from(F.B.t.running_margin.data), lo = Math.min(0, ...a, ...b), hi = Math.max(...a, ...b);
      const px = (k) => 34 + (W - 190) * k / F.L, py = (v) => H - 30 - (H - 50) * (v - lo) / (hi - lo);
      el("line", { x1: 34, x2: W - 156, y1: py(0), y2: py(0), stroke: "#333", "stroke-dasharray": "2 3" }, svg); el("text", { x: 4, y: py(0) + 4 }, svg).textContent = "0";
      for (const [c, arr, n] of [[COL.A, a, "A · original"], [COL.B, b, "B · fine-tuned"]]) { el("polyline", { points: arr.map((v, k) => `${px(k)},${py(v)}`).join(" "), fill: "none", stroke: c, "stroke-width": 2 }, svg);
        el("text", { x: px(F.L) + 8, y: py(arr[F.L]) + 4, fill: c }, svg).textContent = `${n} ${fmt(arr[F.L], 3)}`; }
      el("text", { x: 34, y: H - 8 }, svg).textContent = `after this many layers: 0 … ${F.L}`; numberObjects(); });
  } else {
    root.innerHTML = `${nav}<div class="sec" style="margin-top:56px">
      <div data-obj="num" style="grid-column:span 2"><div class="num">2</div><div class="cap" style="margin-top:8px">what the fine-tune changed</div></div>
      <div style="grid-column:3 / span 5"><h2 data-obj="h2">Every part's push, before and after</h2>
        <div data-obj="text"><p>Each layer's heads and MLP push the margin toward one answer or the other. The fine-tune changes some pushes and leaves most alone. The bars are the change, B minus A, for each layer; together with the embedding they add up to B's margin minus A's.</p>
        <p class="small">A test checks this sum exactly; each export also records the gap. <a href="#" style="color:var(--text)">Show all checks</a></p></div></div>
      <figure data-obj="fig" style="grid-column:9 / span 4"><div class="cap" style="color:var(--delta)">Change in push, by layer · B − A</div><div id="fg" style="height:420px;margin-top:10px"></div></figure></div>`;
    requestAnimationFrame(() => { const h = $("#fg"), W = h.clientWidth, H = 420, svg = el("svg", { width: W, height: H }); h.appendChild(svg);
      const v = Array.from({ length: F.L }, (_, l) => F.P.t.d_attn_attr.get(l) + F.P.t.d_mlp_attr.get(l)), m = Math.max(...v.map(Math.abs)), rh = (H - 30) / F.L, cx = W / 2;
      v.forEach((x, l) => { el("rect", { x: x >= 0 ? cx : cx - (W / 2 - 40) * (-x / m), y: (F.L - 1 - l) * rh + 1, width: (W / 2 - 40) * Math.abs(x) / m, height: rh - 2, fill: x >= 0 ? COL.pos : COL.neg }, svg);
        if (l % 5 === 0) el("text", { x: 0, y: (F.L - 1 - l) * rh + rh * .8 }, svg).textContent = "L" + l; });
      el("line", { x1: cx, x2: cx, y1: 0, y2: H - 30, stroke: "#444" }, svg);
      el("text", { x: 0, y: H - 8 }, svg).textContent = `← “${F.lab(F.jm)}”   d_attn_attr + d_mlp_attr   “${F.lab(F.jp)}” →`; numberObjects(); });
  }
}

// ------------------------------------------------------------------ scale views (illustration · not data)
const LL = { L: 32, H: 32, kv: 8, label: "Llama-3.1-8B-Instruct" };
// Placeholder country list for the 42 adapters. NOT the paper's list; the real menu is index.json `models`.
const CC = "USA GBR DEU FRA ITA ESP NLD SWE NOR POL CZE ROU GRC TUR RUS UKR ARG BRA CHL COL MEX PER CAN AUS NZL JPN KOR CHN IND IDN PHL VNM THA MYS PAK BGD NGA KEN ETH EGY ZAF IRN".split(" ");
function fake(seed) { const r = rng(seed); const hv = [], mv = []; for (let l = 0; l < LL.L; l++) { const env = Math.exp(-((l - 24) ** 2) / 30) * 1.2 + 0.08; hv.push(Array.from({ length: LL.H }, () => gauss(r) * env * (r() < 0.15 ? 2.5 : 0.35))); mv.push(gauss(r) * env * 0.8); } return { hv, mv }; }
const fakeChecks = [{ who: "-", k: "illustration", v: 0, thr: 1, ok: true }];
function viewScaleLadder(root) {
  const f = fake(7), rm = (s) => { const r = rng(s); let m = 0; return Array.from({ length: LL.L + 1 }, (_, k) => (k ? (m += gauss(r) * 0.15 + (k > 22 ? 0.08 * s / 7 : 0)) : 0)); };
  root.innerHTML = `${frame({ tab: "ladder", a: LL.label, b: "+ USA adapter (r16 · q,k,v,o)", item: "wvs_Q81", checks: fakeChecks, illus: true })}
  <section id="answer" data-obj="answer"><span class="say">The answer strip is unchanged at 8B: one sentence, two bars.</span><span class="illus">illustration · not data</span></section>
  <div id="work" style="grid-template-columns:repeat(12,1fr)">
    <section class="obj" data-obj="prompt" style="grid-column:span 3"><header><span class="cap">The prompt</span></header><div class="ptext" style="color:#77777c">The prompt column narrows from 4 to 3 columns; the question still reads as text, template text stays one line.</div></section>
    <div style="grid-column:span 9;display:flex;gap:var(--g)"><section class="obj" data-obj="ladder" style="flex:1 1 auto"><header><span class="cap">What pushed the answer · 32 layers × (32 heads + MLP)</span><span class="sp"></span><span class="seg"><button>A</button><button>B</button><button class="on d">B − A</button></span></header>
      <div id="lad" style="height:calc(100vh - 360px)"></div><div class="foot">heads grouped in 8 KV groups of 4 (3 px gaps) · cell side = min(width, height) fit · <span class="illus">illustration · not data</span></div></section>
    <section class="obj" data-obj="margin" style="flex:0 0 230px"><header><span class="cap">Margin by layer</span></header><div id="mc" style="height:calc(100vh - 360px)"></div></section></div></div>`;
  requestAnimationFrame(() => { const g = ladderSVG($("#lad"), { L: LL.L, H: LL.H, kv: 4, face: "placeholder", val: (l, h) => (h < 0 ? f.mv[l] : f.hv[l][h]), colLabel: "heads 0–31" }); $("#lad").parentElement.style.flex = `0 0 ${Math.max(g.used, 420)}px`;
    marginColumn($("#mc"), { L: LL.L, s: g.s, rowsH: g.rowsH, key: "placeholder", series: [[COL.A, rm(3), "A"], [COL.B, rm(11), "B"]] }); numberObjects(); });
}
function viewScalePicker(root) {
  root.innerHTML = `${frame({ tab: "ladder", a: LL.label, b: "+ USA adapter", item: "wvs_Q81", checks: fakeChecks, illus: true })}
  <div id="picker" data-obj="picker"><div style="display:flex;gap:12px;align-items:center;margin-bottom:12px"><span class="cap">Choose B</span><span class="muted">43 models · any can be A or B · ↑↓ ⏎ · type a country</span><span class="sp"></span><span class="illus">illustration · not data</span></div>
    <input value="" placeholder="Search 43 models: “bra”, “base”, “e3”…" />
    <div class="cap" style="margin-top:14px">Base</div><div class="grid42" style="grid-template-columns:1fr"><span><b style="font-weight:400;color:var(--A)">● ${LL.label}</b><span class="muted">is A</span></span></div>
    <div class="cap" style="margin-top:14px">Country adapters · 42 · r16 on q,k,v,o · grouped by region in the real menu</div>
    <div class="grid42">${CC.map((c, i) => `<span class="${c === "USA" ? "b" : ""}">${c}<span class="muted">${(((i * 37) % 9) / 10 + 0.2).toFixed(1)}</span></span>`).join("")}</div>
    <div class="foot" style="margin-top:12px">small number = this adapter's d_margin on the current item (placeholder) — the menu doubles as a sort · recent pairs: Base vs USA · Base vs BRA · USA vs CHN</div></div>`;
  numberObjects();
}
function viewScaleCohort(root) {
  const rows = CC.map((c, i) => { const f = fake(100 + i); const lay = f.hv.map((hs, l) => hs.reduce((a, b) => a + b, 0) * 0.15 + f.mv[l]); return { c, lay, d: lay.reduce((a, b) => a + b, 0) }; }).sort((a, b) => b.d - a.d);
  root.innerHTML = `${frame({ tab: "scale-cohort", a: LL.label, b: "all 42 country adapters", item: "wvs_Q81", checks: fakeChecks, illus: true })}
  <section id="answer" data-obj="answer"><span class="say">One base, 42 adapters: <b>who moves the answer, and in which layers</b></span><span class="illus">illustration · not data</span></section>
  <div id="work" style="grid-template-columns:repeat(12,1fr)">
    <section class="obj" data-obj="cohort" style="grid-column:span 9"><header><span class="cap">Change in push by layer · adapter − base · rows sorted by d_margin</span><span class="sp"></span><span class="q">?</span></header><div id="ch"></div>
      <div class="foot">bound later to pair d_attn_attr + d_mlp_attr for each (base, adapter) · click a row = open it as B in the Ladder</div></section>
    <section class="obj" data-obj="dm" style="grid-column:span 3"><header><span class="cap">d_margin · B − A</span></header><div id="dm"></div></section></div>`;
  requestAnimationFrame(() => { const host = $("#ch"), W = host.clientWidth, H = innerHeight - 330, rh = H / rows.length, cw = (W - 44) / LL.L, svg = el("svg", { width: W, height: H + 20 }); host.appendChild(svg);
    const m = Math.max(...rows.flatMap((r) => r.lay.map(Math.abs)));
    rows.forEach((r, i) => { el("text", { x: 0, y: i * rh + rh * .8, style: `font-size:${Math.min(11, rh)}px` }, svg).textContent = r.c; r.lay.forEach((v, l) => el("rect", { x: 44 + l * cw, y: i * rh, width: cw - 1, height: rh - 1, fill: div(v, m) }, svg)); });
    [0, 8, 16, 24, 31].forEach((l) => (el("text", { x: 44 + l * cw, y: H + 14 }, svg).textContent = "L" + l));
    const dh = $("#dm"), W2 = dh.clientWidth, svg2 = el("svg", { width: W2, height: H + 20 }); dh.appendChild(svg2); const md = Math.max(...rows.map((r) => Math.abs(r.d)));
    rows.forEach((r, i) => el("rect", { x: r.d >= 0 ? W2 / 2 : W2 / 2 - (W2 / 2 - 10) * -r.d / md, y: i * rh + 1, width: (W2 / 2 - 10) * Math.abs(r.d) / md, height: rh - 2, fill: COL.delta }, svg2));
    el("line", { x1: W2 / 2, x2: W2 / 2, y1: 0, y2: H, stroke: "#444" }, svg2); numberObjects(); });
}

// ------------------------------------------------------------------ count overlay (annotation; not part of the design)
function numberObjects() {
  document.querySelectorAll(".n").forEach((n) => n.remove());
  const objs = [...document.querySelectorAll("[data-obj]")].filter((o) => !o.hidden && o.offsetParent !== null);
  document.body.dataset.count = objs.length; document.body.dataset.objs = objs.map((o) => o.dataset.obj).join(",");
  if (U.get("count") === "0") return;
  objs.forEach((o, i) => { const b = o.getBoundingClientRect(), n = document.createElement("span"); n.className = "n"; n.textContent = i + 1;
    n.style.left = Math.max(2, b.left + scrollX - 24) + "px"; n.style.top = b.top + scrollY - 2 + "px"; document.body.appendChild(n); });
  let c = $("#count"); if (!c) { c = document.createElement("div"); c.id = "count"; document.body.appendChild(c); }
  c.textContent = `${objs.length} objects at rest · ${innerWidth}×${innerHeight}`;
}

const root = $("#root");
try {
  if (VIEW.startsWith("scale")) ({ "scale-ladder": viewScaleLadder, "scale-picker": viewScalePicker, "scale-cohort": viewScaleCohort })[VIEW](root);
  else {
    D = await loadBundle(Q); F = bind(D);
    if (VIEW === "landing") viewLanding(root, F, false); else if (VIEW === "landing-s2") viewLanding(root, F, true);
    else if (VIEW === "matrix") viewMatrix(root, F); else if (VIEW === "object") viewObject(root, F); else viewLadder(root, F);
  }
} catch (e) { root.innerHTML = `<pre style="color:#ff5f56">${esc(e.stack || e)}</pre>`; document.body.dataset.error = String(e); }
