// Shared by the layout-v2 sketches. Data access is a plain-JS port of viewer/src/data.ts
// (contract: workbench/spec/export_contract.md). Nothing here computes a model quantity except
// where a function says so in its name and comment (B − A of two run arrays, segment sums).
// Served by ./serve.sh from workbench/, so exports live at ../../exports/.

export const EXPORTS = "../../exports/";
export const DEFAULT = { a: "smol_inst", b: "smol_inst_usa_e3", item: "wvs_Q81" };

export class Tensor {
  constructor(data, shape, desc) { this.data = data; this.shape = shape; this.desc = desc;
    this.st = shape.map((_, i) => shape.slice(i + 1).reduce((x, y) => x * y, 1)); }
  get(...ix) { let o = 0; for (let i = 0; i < ix.length; i++) { if (ix[i] < 0 || ix[i] >= this.shape[i]) throw new RangeError(`${ix} outside ${this.shape}`); o += ix[i] * this.st[i]; } return this.data[o]; }
  max() { let m = -Infinity; for (const v of this.data) if (v > m) m = v; return m; }
  absMax() { let m = 0; for (const v of this.data) if (Math.abs(v) > m) m = Math.abs(v); return m; }
  sum() { let s = 0; for (const v of this.data) s += v; return s; }
}

async function json(u) { const r = await fetch(u); if (!r.ok) throw new Error(`${u}: HTTP ${r.status}`); return r.json(); }
async function arrays(bin, meta) {
  const r = await fetch(EXPORTS + bin); if (!r.ok) throw new Error(`${bin}: HTTP ${r.status}`);
  const buf = await r.arrayBuffer(); const out = {};
  for (const [k, m] of Object.entries(meta)) {
    const n = m.shape.reduce((a, b) => a * b, 1);
    const d = m.dtype === "uint16" ? new Uint16Array(buf, m.offset, n) : new Float32Array(buf, m.offset, n);
    if (d.byteLength !== m.nbytes) throw new Error(`${k}: byte count differs from manifest`);
    out[k] = new Tensor(d, m.shape, m.desc);
  }
  return out;
}
export async function loadRun(model, item) { const m = await json(`${EXPORTS}run__${model}__${item}.json`); return { m, t: await arrays(m.bin, m.arrays) }; }
export async function loadPair(a, b, item) { const m = await json(`${EXPORTS}pair__${a}__${b}__${item}.json`); return { m, t: await arrays(m.bin, m.arrays) }; }
export async function loadBundle(q = DEFAULT) {
  const [A, B, P] = await Promise.all([loadRun(q.a, q.item), loadRun(q.b, q.item), loadPair(q.a, q.b, q.item)]);
  return { A, B, P };
}
export function params() {
  const p = new URLSearchParams(location.search);
  return { a: p.get("a") || DEFAULT.a, b: p.get("b") || DEFAULT.b, item: p.get("item") || DEFAULT.item, p };
}

// ------------------------------------------------------------------ prompt segments
// Groups token positions into labelled spans: chat-template markers, paragraphs (split on a blank
// line), and the readout. This is a BROWSER HEURISTIC over token text, not an export field; see
// DECISION.md (the exporter knows the template and should emit these spans itself).
export function segments(run) {
  const tk = run.m.tokens.map((x) => x.text), ro = run.m.readout.position;
  const labels = run.m.item.labels.map((s) => String(s).toLowerCase());
  const segs = []; let role = "", cur = null;
  const close = () => { if (cur) { segs.push(cur); cur = null; } };
  for (let i = 0; i < tk.length; i++) {
    if (i === ro) { close(); segs.push({ a: i, b: i, kind: "readout", role: "assistant" }); continue; }
    if (tk[i] === "<|im_start|>") {
      close(); role = (tk[i + 1] || "").trim();
      let b = i + 1; if (tk[b + 1] === "\n") b++;
      if (role === "ass") { while (b + 1 < ro) b++; role = "assistant"; }
      segs.push({ a: i, b, kind: "template", role }); i = b; continue;
    }
    if (tk[i] === "<|im_end|>") { close(); let b = i; if (tk[b + 1] === "\n") b++; segs.push({ a: i, b, kind: "template", role }); i = b; continue; }
    if (!cur) cur = { a: i, b: i, kind: "text", role }; else cur.b = i;
    if (tk[i] === "\n" && tk[i - 1] === "\n") close();
  }
  close();
  for (const s of segs) {
    s.n = s.b - s.a + 1;
    const text = tk.slice(s.a, s.b + 1).join("");
    s.text = text;
    if (s.kind === "readout") s.label = `readout t*=${ro}`;
    else if (s.kind === "template") s.label = tk[s.a] === "<|im_end|>" ? `end of ${s.role} turn` : `${s.role} turn begins`;
    else {
      const words = text.replace(/\s+/g, " ").trim().split(" ");
      s.label = (s.role === "system" ? "system prompt · " : "") + words.slice(0, 4).join(" ") + (words.length > 4 ? " …" : "");
    }
    const low = text.toLowerCase();
    s.hasOption = s.kind === "text" && s.role === "user" && labels.some((l) => low.includes(l));
    s.open = s.kind === "readout" || s.hasOption;    // default: question + options + readout
  }
  return segs;
}
export const tokText = (s) => s.replace(/\n/g, "⏎").replace(/ /g, "·") || "∅";

// ------------------------------------------------------------------ formatting
export const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
export const fmt = (v, p = 4) => (v === 0 ? "0" : Math.abs(v) >= 1e4 || Math.abs(v) < 1e-3 ? v.toExponential(p - 1) : v.toPrecision(p));
export const sgn = (v, p = 3) => (v >= 0 ? "+" : "−") + fmt(Math.abs(v), p);

// One shared height/colour scale per quantity (same rule as viewer makeScale + height, log mode).
export function makeScale(tensors, hmax = 1) {
  let vmax = 0; const sample = [];
  for (const t of tensors) { const step = Math.max(1, Math.floor(t.data.length / 20000));
    for (let i = 0; i < t.data.length; i++) { const v = t.data[i]; if (v > vmax) vmax = v; if (i % step === 0 && v > 0) sample.push(v); } }
  sample.sort((a, b) => a - b);
  return { vmax: vmax || 1, v0: sample.length ? sample[sample.length >> 1] : 1, hmax };
}
export const hOf = (s, v) => (s.hmax * Math.log1p(Math.max(v, 0) / s.v0)) / Math.log1p(s.vmax / s.v0);
export const scaleLabel = (s) => `${s.hmax === 1 ? "u" : "height"} = ${s.hmax === 1 ? "" : s.hmax + "·"}ln(1 + v/${s.v0.toPrecision(3)}) / ln(1 + ${s.vmax.toPrecision(4)}/${s.v0.toPrecision(3)})`;

// Colours (same constants as viewer/src/scene.ts COLORS)
export const C = { pos: "#6b9bff", neg: "#ff9a3c", q3: "#d27bff", delta: "#ffcf5c", head: "#8fa6cf", mlp: "#a8a49a", resid: "#5d6b74", neutral: "#3a3a3e" };
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
export function mix(h1, h2, f) { const a = hex(h1), b = hex(h2); f = Math.max(0, Math.min(1, f)); return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * f)).join(",")})`; }
export const diverging = (v, vmax) => mix(C.neutral, v >= 0 ? C.pos : C.neg, Math.sqrt(Math.min(1, Math.abs(v) / (vmax || 1))));

// ------------------------------------------------------------------ the inspector, A | B | Δ
// slice = { kind: "head"|"mlp"|"resid", l, h?, t }. Returns rows [label, A, B, Δ(exact from pair or null)].
export function compareRows(D, s) {
  const { A, B, P } = D, a = A.t, b = B.t, p = P.t, ro = A.m.readout.position;
  const rows = [];
  if (s.kind === "head") {
    rows.push(["‖o‖ head write", a.head_norm.get(s.l, s.h, s.t), b.head_norm.get(s.l, s.h, s.t), p.d_head_norm.get(s.l, s.h, s.t), "head_norm · d_head_norm"]);
    if (s.t === ro) rows.push(["DLA → margin", a.head_attr.get(s.l, s.h), b.head_attr.get(s.l, s.h), null, "head_attr"]);
    rows.push(["top-16 mass", a.attn_topk_mass.get(s.l, s.h, s.t), b.attn_topk_mass.get(s.l, s.h, s.t), null, "attn_topk_mass"]);
  } else if (s.kind === "mlp") {
    rows.push(["‖m‖ MLP write", a.mlp_norm.get(s.l, s.t), b.mlp_norm.get(s.l, s.t), p.d_mlp_norm.get(s.l, s.t), "mlp_norm · d_mlp_norm"]);
    rows.push(["QIII neurons", a.q3_count.get(s.l, s.t), b.q3_count.get(s.l, s.t), null, "q3_count"]);
    if (s.t === ro) rows.push(["DLA → margin", a.mlp_attr.get(s.l), b.mlp_attr.get(s.l), null, "mlp_attr"]);
  } else {
    rows.push(["‖h‖ residual", a.resid_norm.get(s.l, s.t), b.resid_norm.get(s.l, s.t), p.d_resid_norm.get(s.l, s.t), "resid_norm · d_resid_norm"]);
    if (s.t === ro) rows.push(["margin read here", a.running_margin.get(s.l), b.running_margin.get(s.l), null, "running_margin"]);
  }
  return rows;
}
/** Top attention keys of one head row, A and B side by side (from attn_topk_idx / _val). */
export function topKeys(run, l, h, t, n = 5) {
  const out = [], K = run.t.attn_topk_idx.shape[3];
  for (let k = 0; k < K && out.length < n; k++) { const key = run.t.attn_topk_idx.get(l, h, t, k); if (key !== 65535) out.push({ key, w: run.t.attn_topk_val.get(l, h, t, k) }); }
  return out;
}
export function inspectorHTML(D, s, { pinned = false, title } = {}) {
  const tk = D.A.m.tokens, ro = D.A.m.readout.position;
  const name = s.kind === "head" ? `Head ${s.h} · layer ${s.l}` : s.kind === "mlp" ? `MLP · layer ${s.l}` : (s.l === D.A.m.model.n_layers ? `Residual · final state` : `Residual · entering L${s.l}`);
  const rows = compareRows(D, s);
  const td = (v) => `<td class="num">${v == null ? "" : fmt(v, 4)}</td>`;
  let html = `<div class="card ${pinned ? "pinned" : ""}"><div class="card-h"><span>${esc(title || name)}</span>
    <span class="tag" title="Esc clears">${pinned ? "pinned" : "hover"}</span><button class="lm" data-learn="${s.kind}">learn more</button></div>
    <div class="tokline">t=${s.t} <b>${esc(tokText(tk[s.t].text))}</b>${s.t === ro ? ' <span class="ro">readout t*</span>' : ""}</div>
    <table class="cmp"><tr><th></th><th>A</th><th>B</th><th>‖B−A‖ / B−A</th></tr>
    ${rows.map(([k, a, b, d, src]) => `<tr title="${esc(src)}"><td>${esc(k)}</td>${td(a)}${td(b)}<td class="num d">${d != null ? fmt(d, 4) : '<span class="calc">' + sgn(b - a) + "</span>"}</td></tr>`).join("")}</table>`;
  if (s.kind === "head") {
    const ka = topKeys(D.A, s.l, s.h, s.t), kb = topKeys(D.B, s.l, s.h, s.t);
    const col = (ks) => ks.map((k) => `<div class="kk"><span class="bar" style="width:${(k.w * 100).toFixed(0)}%"></span><span class="num">${k.w.toFixed(2)}</span> t=${k.key} ${esc(tokText(tk[k.key].text))}</div>`).join("");
    html += `<div class="sub">where this head looks (top keys, A[q,k])</div><div class="two"><div><i>A</i>${col(ka)}</div><div><i>B</i>${col(kb)}</div></div>`;
    const dw = D.P.t.d_weight_head; html += `<div class="sub">‖W<sub>B</sub>−W<sub>A</sub>‖<sub>F</sub> q,k,v,o: <span class="num">${[0, 1, 2, 3].map((j) => fmt(dw.get(s.l, s.h, j), 2)).join(", ")}</span></div>`;
  }
  if (s.kind === "mlp") { const dw = D.P.t.d_weight_mlp; html += `<div class="sub">‖W<sub>B</sub>−W<sub>A</sub>‖<sub>F</sub> gate,up,down: <span class="num">${[0, 1, 2].map((j) => fmt(dw.get(s.l, j), 2)).join(", ")}</span> ${dw.get(s.l, 0) === 0 ? "(LoRA leaves the MLP untouched)" : ""}</div>`; }
  html += `<div class="foot">‖B−A‖ is exact from the pair export; <span class="calc">B−A</span> in italics is a browser difference of two run arrays.</div></div>`;
  return html;
}

/** Compact readout card: Eq. 6 probabilities for A and B, margins, one-line conservation status. */
export function readoutHTML(D) {
  const it = D.A.m.item, codes = it.codes;
  const bars = (r, col) => codes.map((c) => { const p = r.m.readout.probs[c], pc = r.m.readout.probs_clamped[c];
    return `<div class="pr"><span>${c}</span><div class="trk"><div style="width:${(p * 100).toFixed(1)}%;background:${col}"></div><i style="left:${(pc * 100).toFixed(1)}%"></i></div><span class="num">${p.toFixed(3)}</span></div>`; }).join("");
  const ok = [D.A, D.B].every((r) => r.m.conservation.pass);
  return `<div class="card"><div class="card-h"><span>Eq. 6 readout · ${esc(it.item_id)}</span><button class="lm" data-learn="eq6">learn more</button></div>
    <div class="q">${codes.map((c, i) => `<b>${c}</b> ${esc(it.labels[i])}`).join(" · ")}</div>
    <div class="two"><div><i>A · margin ${D.A.m.readout.margin.toFixed(3)}</i>${bars(D.A, C.head)}</div><div><i>B · margin ${D.B.m.readout.margin.toFixed(3)}</i>${bars(D.B, C.mlp)}</div></div>
    <div class="sub">Δ margin <span class="num">${sgn(D.P.m.d_margin)}</span> · ΔP(“${it.j_plus}”) <span class="num">${sgn(D.P.m.d_probs[it.j_plus])}</span> · purple tick = clamped pass</div>
    <div class="cons ${ok ? "ok" : "bad"}">${ok ? "✓" : "✗"} conservation: ${ok ? "every check passes for A and B" : "a check FAILS"} <button class="lm" data-learn="conservation">details</button></div></div>`;
}

// ------------------------------------------------------------------ learn-more pop-ups
export function learnText(D, key) {
  const it = D.A.m.item, cA = D.A.m.conservation, cB = D.B.m.conservation;
  const L = {
    eq6: ["Eq. 6 — the survey answer as a probability", `<p>The model reads the whole prompt and, at the last position t* = ${D.A.m.readout.position}, scores every possible next token. We keep only the response-code tokens (${it.codes.join(", ")}) and renormalise with a softmax. That is Eq. 6 of the paper: a probability distribution over answer codes. A test checks that it equals the full teacher-forced probability (gap ${fmt(cA.eq6_teacher_forced_max_abs_gap, 2)}).</p><p>The <b>margin</b> is logit(“${it.j_plus}”) − logit(“${it.j_minus}”): positive means the model leans to “${esc(it.labels[it.codes.indexOf(it.j_plus)])}”. Every attribution in the workbench is an attribution of this one number.</p>`],
    head: ["An attention head", `<p>A head decides <b>which earlier tokens to read from</b> (the attention weights A[q,k]) and writes a 576-dim vector o<sub>h</sub> into the residual stream. The block height is its length ‖o<sub>h</sub>‖ (array <code>head_norm</code>). Nine query heads per layer share three key/value heads.</p><p>“Where this head looks” lists the stored top-16 keys (<code>attn_topk_idx/_val</code>). At the readout column the head also carries a DLA value (<code>head_attr</code>): how much its write, read straight through the final norm and unembedding, moves the margin.</p><p class="muted">o_h = softmax(q kᵀ/√64 + causal) v<sub>kv(h)</sub> W_O[:,h]ᵀ</p>`],
    mlp: ["An MLP block", `<p>After attention, each layer runs a feed-forward block on every token separately: 1536 neurons, each a product of two “poles” (SwiGLU: SiLU(g̃)·u). Height is ‖m‖ (<code>mlp_norm</code>).</p><p><b>Quadrant III</b> neurons have both poles below −0.05 (<code>q3_count</code>). The clamped pass zeroes them in every layer and position during the forward pass; the purple ticks show what that does to Eq. 6.</p><p class="muted">m = Σ_i SiLU(g̃_i) u_i W_down[:, i]</p>`],
    resid: ["The residual stream", `<p>The running state of one token as it passes up the network: h<sup>l+1</sup> = h<sup>l</sup> + attention write + MLP write. Every head and MLP only <i>adds</i> to it, which is why their contributions can be summed. Bar height is ‖h<sup>l</sup><sub>t</sub>‖ (<code>resid_norm</code>).</p><p>At the readout column, h<sup>l</sup>·w (<code>running_margin</code>) is the margin you would get if you read the answer off layer l: the polyline / line chart. Its last point is the margin.</p>`],
    dla: ["Direct logit attribution (DLA)", `<p>w = γ<sub>final</sub> ⊙ (W<sub>U</sub>[j₊] − W<sub>U</sub>[j₋]) / ρ, with the final RMS scale ρ frozen. Then the margin is exactly the embedding term + Σ heads + Σ neurons. Blue pushes toward “${it.j_plus}”, orange toward “${it.j_minus}”.</p><p><b>Limit:</b> DLA is the <i>direct</i> effect only. A head that changes what a later layer does gets no credit here.</p>`],
    conservation: ["Conservation checks (why you can trust the numbers)", `<table class="lt"><tr><th>check</th><th>threshold</th><th>A</th><th>B</th></tr>
      <tr><td>residual closure ‖h<sup>L</sup> − (h⁰+Σa+Σm)‖∞</td><td>1e-3</td><td>${fmt(cA.residual_closure_inf, 2)}</td><td>${fmt(cB.residual_closure_inf, 2)}</td></tr>
      <tr><td>|margin − ΣDLA|</td><td>1e-2</td><td>${fmt(cA.dla_gap, 2)}</td><td>${fmt(cB.dla_gap, 2)}</td></tr>
      <tr><td>same, clamped pass</td><td>1e-2</td><td>${fmt(cA.dla_gap_clamped, 2)}</td><td>${fmt(cB.dla_gap_clamped, 2)}</td></tr>
      <tr><td>vs HF, float32 casts off (rel)</td><td>1e-10</td><td>${fmt(cA.hf64_logits_max_rel_gap, 2)}</td><td>${fmt(cB.hf64_logits_max_rel_gap, 2)}</td></tr>
      <tr><td>vs stock HF (rel, info)</td><td>—</td><td>${fmt(cA.hf_logits_max_rel_gap, 2)}</td><td>${fmt(cB.hf_logits_max_rel_gap, 2)}</td></tr>
      <tr><td>Eq. 6 vs teacher-forced (info)</td><td>—</td><td>${fmt(cA.eq6_teacher_forced_max_abs_gap, 2)}</td><td>${fmt(cB.eq6_teacher_forced_max_abs_gap, 2)}</td></tr></table>
      <p>Each pass is float64. If the parts failed to add up to the whole, this line would turn red, and the pictures should not be read as a measurement until the export is fixed.</p>`],
    delta: ["‖B − A‖ — what the fine-tune changed", `<p>For the same prompt, the same token and the same layer, the pair export stores the length of the difference between B's and A's vectors (<code>d_*_norm</code>), computed from both float64 passes. It is exact, not a difference of two lengths.</p><p>‖W<sub>B</sub>−W<sub>A</sub>‖ shows where the weights moved. For a q,k,v,o LoRA the MLP weights are untouched (exactly 0), so any MLP Δ is downstream of changed attention.</p>`],
    segments: ["Collapsed prompt segments", `<p>Most of the ${D.A.m.tokens.length} tokens are chat template and survey boilerplate. The sketch groups tokens into labelled spans (template markers, paragraphs) and opens the question, the options and the readout by default. A collapsed span draws <b>nothing</b>; it is a gap with a label, never a summary block.</p><p class="muted">The grouping is a browser heuristic on token text. DECISION.md asks the exporter to emit the spans, since it knows the template.</p>`],
    scale: ["Heights and colours", `<p>One scale per quantity, shared by A and B, so equal height means equal value. Log scale with the median as the knee; Δ panels have their own Δ scale. Off the readout column, colours are category colours only.</p>`],
  };
  return L[key] || ["?", ""];
}
export function wireLearn(D, root = document) {
  let dlg = document.getElementById("learn");
  if (!dlg) { dlg = document.createElement("dialog"); dlg.id = "learn"; document.body.append(dlg);
    dlg.addEventListener("click", (e) => { if (e.target === dlg || e.target.closest(".x")) dlg.close(); }); }
  root.addEventListener("click", (e) => { const b = e.target.closest("[data-learn]"); if (!b) return; e.stopPropagation(); openLearn(D, b.dataset.learn); });
}
export function openLearn(D, key) {
  const dlg = document.getElementById("learn"); const [h, body] = learnText(D, key);
  dlg.innerHTML = `<div class="lm-h"><b>${h}</b><button class="x">close ✕</button></div><div class="lm-b">${body}</div>`;
  if (!dlg.open) dlg.showModal();
}

export const BASE_CSS = `
:root{--page:#0b0b0b;--card:#131313;--face:#1b1b1b;--line:#2a2a2a;--text:#e6e6e6;--muted:#9b9b9b;--pos:#6b9bff;--neg:#ff9a3c;--q3:#d27bff;--ok:#6be0a0;--bad:#ff6b6b;--delta:#ffcf5c;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;--serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--page);color:var(--text);font:12.5px/1.45 var(--mono)}
button{font:inherit;color:var(--text);background:var(--face);border:1px solid var(--line);border-radius:4px;padding:3px 8px;cursor:pointer}
button:hover{border-color:#555}button.on{background:#24324d;border-color:var(--pos)}
input,select{font:inherit;color:var(--text);background:var(--face);border:1px solid var(--line);border-radius:4px;padding:3px 6px}
.muted{color:var(--muted)}.num{font-variant-numeric:tabular-nums}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:9px 10px;margin-bottom:10px}
.card.pinned{border-color:#777}
.card-h{display:flex;gap:8px;align-items:center;margin-bottom:6px;font-weight:600}.card-h>span:first-child{flex:1}
.tag{font-weight:400;color:var(--muted);font-size:11px}
.lm{font-size:11px;padding:1px 7px;color:var(--pos);border-color:#2b3b5c;background:transparent}
.tokline{margin-bottom:6px}.tokline b{background:#222;padding:0 4px;border-radius:3px}.ro{color:var(--pos)}
table.cmp{width:100%;border-collapse:collapse}table.cmp th{color:var(--muted);font-weight:400;text-align:right;padding:2px 4px}
table.cmp td{padding:2px 4px;border-top:1px solid #1f1f1f}table.cmp td.num{text-align:right}table.cmp td.d{color:var(--delta)}
.calc{font-style:italic;color:#d8c27a}
.sub{color:var(--muted);margin:8px 0 3px}.foot{color:#6f6f6f;font-size:11px;margin-top:8px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.two i{color:var(--muted);font-style:normal;display:block;margin-bottom:2px}
.kk{position:relative;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:1px 2px}.kk .bar{position:absolute;left:0;top:2px;bottom:2px;background:#ffffff1c;border-radius:2px}
.pr{display:grid;grid-template-columns:14px 1fr 40px;gap:5px;align-items:center;margin:2px 0}.trk{position:relative;height:10px;background:var(--face);border-radius:2px}
.trk div{height:100%;border-radius:2px}.trk i{position:absolute;top:-2px;bottom:-2px;width:2px;background:var(--q3)}
.q{color:var(--muted);margin-bottom:6px}.cons{margin-top:8px;padding:4px 6px;border-radius:4px;border:1px solid #2c5a43;color:var(--ok)}.cons.bad{color:var(--bad);border-color:#6a2b2b}
dialog#learn{background:#141414;color:var(--text);border:1px solid #444;border-radius:8px;max-width:620px;padding:0;font:13px/1.55 var(--mono)}
dialog#learn::backdrop{background:#000a}.lm-h{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--line)}
.lm-b{padding:4px 16px 14px}.lm-b p{margin:10px 0}.lm-b code{color:#cfd8ea}
table.lt{border-collapse:collapse;width:100%;margin-top:10px}table.lt td,table.lt th{padding:3px 6px;border-bottom:1px solid #222;text-align:left}
`;
