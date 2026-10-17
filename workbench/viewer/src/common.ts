// Shared by the landing page and the three workbench tabs (ladder, matrix, 3D object).
// Data access is in data.ts. Nothing here computes a model quantity, except where a function
// says so in its name and comment (a browser B − A fallback for @1 files, segment sums).
// Copy follows design/layout-v2/COPY.md (string IDs in comments) and its PM rulings.

import type { Bundle, Run, Segment, Tensor } from "./data";

// ------------------------------------------------------------------ formatting
export const esc = (s: unknown) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
export const fmt = (v: number, p = 4) => (v === 0 ? "0" : Math.abs(v) >= 1e4 || Math.abs(v) < 1e-3 ? v.toExponential(p - 1) : v.toPrecision(p));
export const sgn = (v: number, p = 3) => (v >= 0 ? "+" : "−") + fmt(Math.abs(v), p);
export const tokText = (s: string) => s.replace(/\n/g, "⏎").replace(/ /g, "·") || "∅";

// ------------------------------------------------------------------ colours
// Sign colours (blue toward j+, orange toward j−) are reserved for DLA. A and B lines/bars use
// two non-sign colours, so one colour means one thing on a screen (COPY §4.3, point 1).
export const C = { pos: "#6b9bff", neg: "#ff9a3c", q3: "#d27bff", delta: "#ffcf5c", head: "#8fa6cf", mlp: "#a8a49a", resid: "#5d6b74", neutral: "#3a3a3e" };
export const A_COL = "#e6e6e6", B_COL = "#5fc4b8";
const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
export function mix(h1: string, h2: string, f: number) {
  const a = hex(h1), b = hex(h2); f = Math.max(0, Math.min(1, f));
  return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * f)).join(",")})`;
}
/** DLA colour: neutral -> blue/orange by sqrt(|v| / vmax). */
export const diverging = (v: number, vmax: number) => mix(C.neutral, v >= 0 ? C.pos : C.neg, Math.sqrt(Math.min(1, Math.abs(v) / (vmax || 1))));

/** Log colour scale for 2D maps: u = ln(1 + v/v0) / ln(1 + vmax/v0), with vmax clipped at a percentile. */
export interface Ramp { v0: number; vmax: number; max: number; pct: number }
export function makeRamp(tensors: Tensor[], pct = 0.99): Ramp {
  const v: number[] = [];
  let max = 0;
  for (const t of tensors) { const step = Math.max(1, Math.floor(t.data.length / 40000)); for (let i = 0; i < t.data.length; i++) { const x = t.data[i]; if (x > max) max = x; if (i % step === 0) v.push(x); } }
  v.sort((a, b) => a - b);
  const pos = v.filter((x) => x > 0);
  return { v0: pos.length ? pos[pos.length >> 1] : 1, vmax: v[Math.min(v.length - 1, Math.floor(v.length * pct))] || max || 1, max, pct };
}
export const rampU = (r: Ramp, v: number) => Math.min(1, Math.log1p(Math.max(v, 0) / r.v0) / Math.log1p(r.vmax / r.v0));

/** Colour key for a log ramp: gradient, 4 ticks with values, and the clipping stated in the key itself. */
export function rampLegend(r: Ramp, lo: string, hi: string, label: string, src: string): string {
  const ticks = [0, 0.33, 0.66, 1].map((u) => ({ u, v: r.v0 * Math.expm1(u * Math.log1p(r.vmax / r.v0)) }));
  return `<div class="key" title="${esc(src)}"><span class="key-l">${esc(label)}</span><span class="key-bar"><span style="background:linear-gradient(90deg,${lo},${hi})"></span>${ticks.map((t) => `<i style="left:${(t.u * 100).toFixed(0)}%">${fmt(t.v, 2)}</i>`).join("")}</span><span class="key-clip">≥ ${fmt(r.vmax, 3)} (${Math.round(r.pct * 100)}th percentile) all show as the brightest colour; the largest value is ${fmt(r.max, 3)}. Log scale.</span></div>`;
}
/** Colour key for DLA: −vmax … 0 … +vmax, square-root scale, no clipping. */
export function divergingLegend(vmax: number, lp: string, lm: string, note = ""): string {
  const stops = [-1, -0.5, -0.25, 0, 0.25, 0.5, 1];
  const grad = stops.map((s) => `${diverging(s * vmax, vmax)} ${(((s + 1) / 2) * 100).toFixed(0)}%`).join(",");
  return `<div class="key"><span class="key-l">push on the margin</span><span class="key-bar"><span style="background:linear-gradient(90deg,${grad})"></span>${[-1, -0.5, 0, 0.5, 1].map((s) => `<i style="left:${(((s + 1) / 2) * 100).toFixed(0)}%">${s === 0 ? "0" : sgn(s * vmax, 2)}</i>`).join("")}</span><span class="key-clip">Blue = pushes toward “${esc(lp)}”. Orange = toward “${esc(lm)}”. Grey = about zero. Colour deepens with size, up to ±${fmt(vmax, 3)} on this scale (the largest |value|; nothing is clipped).${note}</span></div>`;
}

// ------------------------------------------------------------------ item, labels
export const labelPlus = (r: Run) => { const it = r.m.item; return String(it.labels[it.codes.indexOf(it.j_plus)]); };
export const labelMinus = (r: Run) => { const it = r.m.item; return String(it.labels[it.codes.indexOf(it.j_minus)]); };
export const short = (s: string, n = 48) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);
/** "(original)" / "(fine-tuned)" only when B is A plus an adapter (COPY C06). Otherwise registry labels only. */
export const roleOf = (D: Bundle, k: "A" | "B") => (D.B.m.model.adapter && D.A.m.model.model_id === D.B.m.model.model_id ? (k === "A" ? " (original)" : " (fine-tuned)") : "");
export const isBank = (r: Run) => r.m.item.kind === "bank";
/** The question (or scenario) text, from the tokens of the exported `question` segment (PM ruling K10). */
export function questionText(r: Run): string | null {
  const s = r.m.segments?.find((g) => g.kind === "question");
  if (!s) return null;
  return r.m.tokens.slice(s.a, s.b).map((t) => t.text).join("").replace(/^Question:\s*/, "").trim();
}

// ------------------------------------------------------------------ segments (contract @1.1)
export interface Seg { a: number; b: number; n: number; kind: Segment["kind"] | "text"; label: string; text: string; open: boolean; exported: boolean }
const OPEN_KINDS = new Set(["question", "options", "answer_cue", "readout"]);
/** Display label for an exported segment (COPY S19: "message" for "turn", "system instructions"). */
function relabel(g: Segment, ro: number): string {
  if (g.kind === "readout") return `answer position t*=${ro}`;
  return g.label.replace(/turn opens/g, "message starts").replace(/turn closes/g, "message ends").replace(/^system prompt$/, "system instructions");
}
/** Segments from `manifest.segments` (b made inclusive). An @1 file has none: then the prompt is one
 * open span plus the answer position, labelled as such. No token-text heuristic. */
export function segmentsOf(r: Run): Seg[] {
  const tk = r.m.tokens, ro = r.m.readout.position, T = tk.length;
  const text = (a: number, b: number) => tk.slice(a, b + 1).map((x) => x.text).join("");
  if (r.m.segments && r.m.segments.length) {
    return r.m.segments.map((g) => ({ a: g.a, b: g.b - 1, n: g.b - g.a, kind: g.kind, label: relabel(g, ro), text: text(g.a, g.b - 1), open: OPEN_KINDS.has(g.kind), exported: true }));
  }
  const out: Seg[] = [];
  if (ro > 0) out.push({ a: 0, b: ro - 1, n: ro, kind: "text", label: "whole prompt (no segments in this @1 export)", text: text(0, ro - 1), open: true, exported: false });
  out.push({ a: ro, b: T - 1, n: T - ro, kind: "readout", label: `answer position t*=${ro}`, text: text(ro, T - 1), open: true, exported: false });
  return out;
}

// ------------------------------------------------------------------ B − A of the readout attributions
/** From the pair export (@1.1 `d_head_attr`, `d_mlp_attr`, `d_embed_attr`, `d_margin[_clamped]`).
 * An @1 file lacks them: then B − A of the two run arrays, computed here and labelled as such. */
export interface DAttr { head: (l: number, h: number) => number; mlp: (l: number) => number; embed: number; margin: number; exported: boolean; marginExported: boolean }
export function dAttr(D: Bundle, clamp: boolean): DAttr {
  const p = D.P.t, a = D.A.t, b = D.B.t, pm = D.P.m;
  const hk = clamp ? "d_head_attr_clamped" : "d_head_attr", mk = clamp ? "d_mlp_attr_clamped" : "d_mlp_attr";
  const ek = clamp ? pm.d_embed_attr_clamped : pm.d_embed_attr;
  const mg = clamp ? pm.d_margin_clamped : pm.d_margin;
  const marginB = (clamp ? D.B.m.readout.margin_clamped : D.B.m.readout.margin) - (clamp ? D.A.m.readout.margin_clamped : D.A.m.readout.margin);
  if (p[hk] && p[mk] && ek != null) {
    return { head: (l, h) => p[hk].get(l, h), mlp: (l) => p[mk].get(l), embed: ek, margin: mg ?? marginB, exported: true, marginExported: mg != null };
  }
  const ha = clamp ? a.head_attr_clamped : a.head_attr, hb = clamp ? b.head_attr_clamped : b.head_attr;
  const ma = clamp ? a.mlp_attr_clamped : a.mlp_attr, mb = clamp ? b.mlp_attr_clamped : b.mlp_attr;
  const ea = clamp ? D.A.m.readout.embed_attr_clamped : D.A.m.readout.embed_attr, eb = clamp ? D.B.m.readout.embed_attr_clamped : D.B.m.readout.embed_attr;
  return { head: (l, h) => hb.get(l, h) - ha.get(l, h), mlp: (l) => mb.get(l) - ma.get(l), embed: eb - ea, margin: mg ?? marginB, exported: false, marginExported: mg != null };
}

// ------------------------------------------------------------------ the inspector, A | B | Change
export type Slice = { kind: "head"; l: number; h: number; t: number } | { kind: "mlp"; l: number; t: number } | { kind: "resid"; l: number; t: number };
/** A change cell: "len" = ‖B−A‖ from the export (gold); "exp" = signed B − A from the export; "calc" = signed B − A computed here (italic). */
type Change = { v: number; how: "len" | "exp" | "calc"; src: string } | null;
interface Row { label: string; tip: string; a: number; b: number; d: Change; int?: boolean }

export function compareRows(D: Bundle, s: Slice, clamp = false): Row[] {
  const a = D.A.t, b = D.B.t, p = D.P.t, ro = D.A.m.readout.position, dd = dAttr(D, clamp);
  const calc = (x: number, y: number): Change => ({ v: y - x, how: "calc", src: "B − A of two run arrays, computed on this page" });
  const dla = (v: number): Change => (dd.exported ? { v, how: "exp", src: `B − A from the pair export (${clamp ? "d_*_attr_clamped" : "d_*_attr"})` } : { v, how: "calc", src: "B − A of two run arrays, computed on this page (this @1 export has no d_*_attr)" });
  const rows: Row[] = [];
  const cl = clamp ? ", clamped run" : "";
  if (s.kind === "head") {
    rows.push({ label: "Write size ‖o‖", tip: "Length of the vector this head adds to the running state. It says how much, not which way.\nhead_norm · d_head_norm", a: a.head_norm.get(s.l, s.h, s.t), b: b.head_norm.get(s.l, s.h, s.t), d: { v: p.d_head_norm.get(s.l, s.h, s.t), how: "len", src: "‖o_B − o_A‖, d_head_norm" } });
    if (s.t === ro) { const ha = clamp ? a.head_attr_clamped : a.head_attr, hb = clamp ? b.head_attr_clamped : b.head_attr;
      rows.push({ label: `Push on the margin (DLA)${cl}`, tip: `How far this head's write moves the margin, read straight through the model's last steps.\n${clamp ? "head_attr_clamped" : "head_attr"}`, a: ha.get(s.l, s.h), b: hb.get(s.l, s.h), d: dla(dd.head(s.l, s.h)) }); }
    rows.push({ label: "Attention covered by the top 16", tip: "Share of this head's attention that the 16 largest weights cover (1 = all of it).\nattn_topk_mass", a: a.attn_topk_mass.get(s.l, s.h, s.t), b: b.attn_topk_mass.get(s.l, s.h, s.t), d: calc(a.attn_topk_mass.get(s.l, s.h, s.t), b.attn_topk_mass.get(s.l, s.h, s.t)) });
  } else if (s.kind === "mlp") {
    rows.push({ label: "Write size ‖m‖", tip: "Length of the vector this MLP adds to the running state.\nmlp_norm · d_mlp_norm", a: a.mlp_norm.get(s.l, s.t), b: b.mlp_norm.get(s.l, s.t), d: { v: p.d_mlp_norm.get(s.l, s.t), how: "len", src: "‖m_B − m_A‖, d_mlp_norm" } });
    rows.push({ label: "Quadrant III neurons (count)", tip: "Neurons whose two input signals are both below −0.05 at this token.\nq3_count", a: a.q3_count.get(s.l, s.t), b: b.q3_count.get(s.l, s.t), d: calc(a.q3_count.get(s.l, s.t), b.q3_count.get(s.l, s.t)), int: true });
    if (s.t === ro) { const ma = clamp ? a.mlp_attr_clamped : a.mlp_attr, mb = clamp ? b.mlp_attr_clamped : b.mlp_attr;
      rows.push({ label: `Push on the margin (DLA)${cl}`, tip: `How far this MLP's write moves the margin.\n${clamp ? "mlp_attr_clamped" : "mlp_attr"}`, a: ma.get(s.l), b: mb.get(s.l), d: dla(dd.mlp(s.l)) }); }
  } else {
    rows.push({ label: "Running-state size ‖h‖", tip: "Length of the running state.\nresid_norm · d_resid_norm", a: a.resid_norm.get(s.l, s.t), b: b.resid_norm.get(s.l, s.t), d: { v: p.d_resid_norm.get(s.l, s.t), how: "len", src: "‖h_B − h_A‖, d_resid_norm" } });
    if (s.t === ro) { const ra = clamp ? a.running_margin_clamped : a.running_margin, rb = clamp ? b.running_margin_clamped : b.running_margin;
      rows.push({ label: `Margin if read off here${cl}`, tip: "The margin you would get by reading the answer off the state at this layer, with the final layer's rescaling held fixed.\nrunning_margin", a: ra.get(s.l), b: rb.get(s.l), d: calc(ra.get(s.l), rb.get(s.l)) }); }
  }
  return rows;
}
export function topKeys(r: Run, l: number, h: number, t: number, n = 5) {
  const out: { key: number; w: number }[] = [], K = r.t.attn_topk_idx.shape[3];
  for (let k = 0; k < K && out.length < n; k++) { const key = r.t.attn_topk_idx.get(l, h, t, k); if (key !== 65535) out.push({ key, w: r.t.attn_topk_val.get(l, h, t, k) }); }
  return out;
}
const cell = (d: Change) => !d ? "<td></td>" : d.how === "len" ? `<td class="num d" title="${esc(d.src)}"><span class="lenp">‖Δ‖ </span>${fmt(d.v, 4)}</td>` : d.how === "exp" ? `<td class="num sx" title="${esc(d.src)}">${sgn(d.v, 3)}</td>` : `<td class="num" title="${esc(d.src)}"><span class="calc">${sgn(d.v, 3)}</span></td>`;
/** The A | B | Change table. Fixed column widths, so the headers sit over their numbers. */
export function cmpTable(rows: Row[]): string {
  return `<table class="cmp"><colgroup><col class="c0"><col class="c1"><col class="c1"><col class="c1"></colgroup><thead><tr><th></th><th>A</th><th>B</th><th>Change</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><td title="${esc(r.tip)}">${esc(r.label)}</td><td class="num">${r.int ? r.a : fmt(r.a, 4)}</td><td class="num">${r.int ? r.b : fmt(r.b, 4)}</td>${cell(r.d)}</tr>`).join("")}</tbody></table>`;
}
export const CHANGE_FOOT = `<div class="foot">Change in <span class="d">gold</span> = how far B's vector is from A's (a length, never negative), exact, from the pair export. Change with a sign = B − A of two numbers: <span class="sx">upright</span> when it comes from the pair export, <span class="calc">italic</span> when it is computed on this page.</div>`;

export function sliceName(D: Bundle, s: Slice): string {
  return s.kind === "head" ? `Head ${s.h} · layer ${s.l}` : s.kind === "mlp" ? `MLP · layer ${s.l}` : s.l === D.A.m.model.n_layers ? "Running state · after the last layer" : `Running state · entering layer ${s.l}`;
}
export function inspectorHTML(D: Bundle, s: Slice, o: { pinned?: boolean; clamp?: boolean; note?: string } = {}): string {
  const tk = D.A.m.tokens, ro = D.A.m.readout.position;
  let html = `<div class="card ${o.pinned ? "pinned" : ""}"><div class="card-h"><span>${esc(sliceName(D, s))}</span>
    <span class="tag" title="${o.pinned ? "Press Esc to unpin" : "Click to pin"}">${o.pinned ? "pinned" : "preview"}</span>${lm(s.kind, "learn more")}</div>
    ${o.note ? `<div class="note">${o.note}</div>` : ""}
    <div class="tokline">token ${s.t}: “<b>${esc(tokText(tk[s.t].text))}</b>”${s.t === ro ? ' <span class="ro" title="answer position (t*): where the model is about to write its answer">answer position (t*)</span>' : ""}</div>
    ${cmpTable(compareRows(D, s, o.clamp))}`;
  if (s.kind === "head") {
    const ka = topKeys(D.A, s.l, s.h, s.t), kb = topKeys(D.B, s.l, s.h, s.t);
    const col = (ks: { key: number; w: number }[]) => ks.map((k) => `<div class="kk"><span class="bar" style="width:${(k.w * 100).toFixed(0)}%"></span><span class="num">${k.w.toFixed(2)}</span> · #${k.key} “${esc(tokText(tk[k.key].text))}”</div>`).join("");
    html += `<div class="sub">Where this head looks${s.t === ro ? " from the answer position" : " from this token"}: its largest attention weights (weight · token number)</div><div class="two"><div><i>A</i>${col(ka)}</div><div><i>B</i>${col(kb)}</div></div>`;
    const dw = D.P.t.d_weight_head;
    html += `<div class="sub" title="Frobenius norm: the square root of the sum of squared differences. 0 means untouched. k and v are shared by 3 heads.">How far this head's weights moved, B vs A (q, k, v, o): <span class="num">${[0, 1, 2, 3].map((j) => fmt(dw.get(s.l, s.h, j), 2)).join(", ")}</span></div>`;
  }
  if (s.kind === "mlp") {
    const dw = D.P.t.d_weight_mlp;
    html += `<div class="sub">How far this MLP's weights moved, B vs A (gate, up, down): <span class="num">${[0, 1, 2].map((j) => fmt(dw.get(s.l, j), 2)).join(", ")}</span> ${dw.get(s.l, 0) === 0 && dw.get(s.l, 1) === 0 && dw.get(s.l, 2) === 0 ? "(0: this adapter changed no MLP weights)" : ""}</div>`;
  }
  return html + CHANGE_FOOT + "</div>";
}

// ------------------------------------------------------------------ the answer card (S01–S08)
export function readoutHTML(D: Bundle): string {
  const it = D.A.m.item, codes = it.codes, lp = labelPlus(D.A), lmn = labelMinus(D.A);
  const bars = (r: Run, col: string) => codes.map((c) => {
    const p = r.m.readout.probs[c], pc = r.m.readout.probs_clamped[c];
    return `<div class="pr"><span>${esc(c)}</span><div class="trk"><div style="width:${(p * 100).toFixed(1)}%;background:${col}"></div><i style="left:${(pc * 100).toFixed(1)}%" title="clamped run: ${pc.toFixed(3)}"></i></div><span class="num">${p.toFixed(3)}</span></div>`;
  }).join("");
  const ok = [D.A, D.B].every((r) => r.m.conservation.pass) && D.P.m.conservation?.pass !== false;
  return `<div class="card"><div class="card-h"><span>The model's answer · ${esc(it.item_id)}</span>${lm("eq6", "learn more")}</div>
    <div class="q" title="Equivalently logit(“${esc(it.j_plus)}”) − logit(“${esc(it.j_minus)}”): the shared normaliser of the softmax cancels.">Margin = log-odds of “${esc(it.j_plus)}” vs “${esc(it.j_minus)}” = log[P(“${esc(it.j_plus)}”) / P(“${esc(it.j_minus)}”)]. Positive means the model leans toward “${esc(short(lp, 60))}” over “${esc(short(lmn, 60))}”.</div>
    <div class="q">Answer codes: ${codes.map((c, i) => `<b>${esc(c)}</b> ${esc(short(String(it.labels[i]), isBank(D.A) ? 70 : 40))}`).join(" · ")}</div>
    <div class="two"><div><i title="${esc(D.A.m.model.label)}" style="color:${A_COL}">A · margin ${D.A.m.readout.margin.toFixed(3)}</i>${bars(D.A, A_COL)}</div><div><i title="${esc(D.B.m.model.label)}" style="color:${B_COL}">B · margin ${D.B.m.readout.margin.toFixed(3)}</i>${bars(D.B, B_COL)}</div></div>
    <div class="sub">Change, B − A: margin <span class="num">${sgn(D.P.m.d_margin)}</span> · P(“${esc(short(lp, 30))}”) <span class="num">${sgn(D.P.m.d_probs[it.j_plus])}</span>. <span style="color:var(--q3)">Purple tick</span>: the result when Quadrant III neurons are clamped.</div>
    <div class="cons ${ok ? "ok" : "bad"}">${ok ? "✓ The parts add up: every check passes for A and B" : "✗ A check failed. Do not read these figures as measurements until the export is fixed."} ${lm("conservation", "see the checks")}</div></div>`;
}

// ------------------------------------------------------------------ learn-more pop-ups (P01–P14)
export const lm = (key: string, text: string, topic?: string) => { const t = `Learn more: ${topic ?? TOPIC[key] ?? key}`; return `<button class="lm" data-learn="${key}" title="${esc(t)}" aria-label="${esc(t)}">${esc(text)}</button>`; };
const TOPIC: Record<string, string> = { eq6: "the answer as a probability", head: "attention heads", tstar: "the answer position", norm: "the size of a vector", dla: "DLA", conservation: "the checks", delta: "what the fine-tune changed", mlp: "MLP blocks", segments: "template text", clamp: "the clamped run", models: "the two models", terms: "terms", resid: "the running state", scale: "heights and colours" };

export const GLOSSARY: [string, string][] = [
  ["margin", "The log-odds of the first answer code vs the second: log[P(first) / P(second)], which equals the gap between their scores. Positive means the model leans toward the first."],
  ["logit", "The model's raw score for one answer, before it is turned into a probability. Only differences between scores matter. Like the utility index in a multinomial logit."],
  ["Eq. 6", "The step that turns the scores of the response codes into probabilities (a softmax over the codes only). Eq. 6 of the SCA2 paper (arXiv:2610.06562)."],
  ["answer position (t*)", "The last position of the prompt, where the model is about to write its answer. Every probability, margin and push is read here. Also called the readout position."],
  ["running state (residual stream)", "A list of 576 numbers for each token. Each layer adds to it, and nothing is overwritten. A running total, not a regression residual."],
  ["attention head", "A part that, for the current word, takes a weighted average of what earlier words hold and adds a summary to the running state. Nine per layer."],
  ["MLP", "A small feed-forward network applied to each token on its own, 1,536 hidden units (neurons) per layer."],
  ["DLA (direct logit attribution)", "Each part's share of the margin, read straight through the model's last steps with the final rescaling held fixed. The shares add up to the margin, like β·x terms of a logit index."],
  ["direct effect", "The part of an effect that goes straight to the answer. A part that works by changing a later layer gets no credit here, as with a direct path in a mediation model."],
  ["the checks", "Tests that the parts add back to the whole, and that our code matches a reference implementation. The “do the line items add to the total?” check."],
  ["float64", "64-bit binary floating-point arithmetic, about 16 significant digits. R's default numeric type. Most language-model runs use 16 or 32 bits."],
  ["fine-tune", "Training an already-trained model a bit more on a narrower set of examples, so its answers shift."],
  ["LoRA", "A way to fine-tune that keeps the original weights and learns small low-rank corrections added on top."],
  ["DPO", "Training from pairs of answers, one preferred and one not. Here the pairs are made-up everyday scenarios, preferring the answer that matches the USA's direction on the Global Preferences Survey (e.g. more trusting, more patient). Not survey responses."],
  ["Quadrant III and clamp", "Neurons whose two input signals are both below −0.05. The clamped run sets their output to zero while the model runs, then re-measures. Later layers can still respond."],
  ["change ‖B − A‖ vs B − A", "‖B − A‖ is the length of the difference of two vectors: never negative. B − A is the signed difference of two numbers."],
  ["top-16 attention", "For each head and token only the 16 largest attention weights are kept. “Covered” says how much of the attention they account for."],
  ["token", "A word piece. The model reads and writes tokens, not words."],
  ["layer", "One round of “heads then MLP”. This model has 30."],
  ["embedding term", "The contribution to the margin of the starting vector, before layer 0. The intercept of the split."],
  ["teacher-forced", "Scoring each full answer token by token (the chain rule), instead of reading only the next-token scores."],
  ["frozen scale (ρ)", "The model rescales the final state before scoring. DLA holds that scale fixed so the parts add exactly."],
  ["ablation / patching", "Changing or replacing part of the model and re-running, to see if the answer depends on it. The clamped run is one such change."],
  ["template text", "The fixed chat-format markers and instructions around the question. Most of the prompt."],
  ["size of a vector (‖·‖)", "The usual length: the square root of the sum of squares."],
];

export function learnText(D: Bundle, key: string): [string, string] {
  const it = D.A.m.item, cA = D.A.m.conservation, cB = D.B.m.conservation, ro = D.A.m.readout.position;
  const lp = esc(short(labelPlus(D.A), 70)), lmn = esc(short(labelMinus(D.A), 70));
  const mlpZero = D.P.t.d_weight_mlp.absMax() === 0;
  const ref = (s: string) => `<p class="muted"><i>For reference:</i> ${s}</p>`;
  const L: Record<string, [string, string]> = {
    eq6: ["The answer as a probability (Eq. 6)", `<p>The model reads the whole prompt. At the last position (t* = ${ro}) it gives a score to every possible next token. We keep only the scores for the response codes (${it.codes.map(esc).join(", ")}) and turn them into probabilities with a softmax. This is the same form as a multinomial logit, restricted to the response codes. It is Eq. 6 of the SCA2 paper (arXiv:2610.06562). We also compute the same probabilities a second way, by scoring each full answer token by token: a test checks this; each export also records the gap. Here the largest gap is ${fmt(Math.max(cA.eq6_teacher_forced_max_abs_gap, cB.eq6_teacher_forced_max_abs_gap), 2)}.</p><p>The <b>margin</b> is the log-odds of “${esc(it.j_plus)}” vs “${esc(it.j_minus)}”, log[P(“${esc(it.j_plus)}”) / P(“${esc(it.j_minus)}”)]. Equivalently, the gap between their two scores (logits), because the softmax's shared normaliser cancels. Positive means the model leans toward “${lp}”. Because of the softmax, the margin is also the log of the odds of “${esc(it.j_plus)}” against “${esc(it.j_minus)}”. Every “push on the margin” figure in the workbench splits this one number.</p>`],
    head: ["What is an attention head?", `<p>When the model works on a word, an attention head looks back at the earlier words and takes a weighted average of what it finds there. The weights (the attention weights, A[q,k]) are positive and add to 1, like kernel weights. The head then adds a summary, a list of 576 numbers, to the running state. This model has nine heads in each layer. They share three sets of key and value inputs.</p><p>The block height is the <b>size of that summary</b>, ‖o_h‖. It says how much the head adds, not which way. “Where this head looks” lists the stored 16 largest attention weights. At the answer position the head also has a DLA value: how much its addition moves the margin, read straight through the model's last steps.</p>${ref("o_h = softmax(q kᵀ/√64 + causal) v<sub>kv(h)</sub> W_O[:,h]ᵀ. Arrays: <code>head_norm</code>, <code>attn_topk_idx/_val</code>, <code>head_attr</code>.")}`],
    tstar: ["The answer position (t*)", `<p>A prompt is a list of tokens (word pieces). The model writes its answer right after the last one. That last position is called t*. Here t* = ${ro}. The answer probabilities, the margin, and every “push on the margin” number are read at this one position. Other positions are shown for context. Think of t* as the one row of the data where the outcome is evaluated.</p>`],
    norm: ["What is the size of a vector (‖·‖)?", `<p>A vector here is a list of numbers (576 for a running state). Its size, written ‖v‖, is the usual length: the square root of the sum of squares. Bigger means the part wrote more. It does not say in which direction. Two vectors of equal size can push the answer opposite ways. Only the DLA numbers at the answer position carry a direction.</p>`],
    dla: ["How much did each part push the answer? (DLA)", `<p>Direct logit attribution (DLA) splits the margin into additive pieces, like splitting a logit index into β·x terms. Each part's addition is read straight through the model's last steps, with the final rescaling ρ held fixed. Then the margin is exactly the embedding term + Σ heads + Σ neurons. Blue pushes toward “${lp}”, orange toward “${lmn}”.</p><p><b>Limit.</b> DLA is the direct effect only, like a direct effect in a mediation model. A head that changes what a later layer does gets no credit for that path.</p>${ref("w = γ<sub>final</sub> ⊙ (W<sub>U</sub>[j₊] − W<sub>U</sub>[j₋]) / ρ. Arrays: <code>head_attr</code>, <code>mlp_attr</code>, <code>neuron_attr</code>, <code>readout.embed_attr</code>; B − A: <code>d_head_attr</code>, <code>d_mlp_attr</code>, <code>d_embed_attr</code>.")}`],
    conservation: ["Do the parts add up? The checks", `<p>Three questions. Do the parts add up to the final state? Do they add up to the margin? Does our code give the same numbers as the reference implementation? All three have to pass, for both models.</p>
      <table class="lt"><tr><th>Check</th><th>Must be below</th><th>A</th><th>B</th></tr>
      <tr><td>The parts add up to the final state (largest gap in any coordinate, any token)</td><td>1e-3</td><td>${fmt(cA.residual_closure_inf, 2)}</td><td>${fmt(cB.residual_closure_inf, 2)}</td></tr>
      <tr><td>The parts add up to the margin (absolute gap)</td><td>1e-2</td><td>${fmt(cA.dla_gap, 2)}</td><td>${fmt(cB.dla_gap, 2)}</td></tr>
      <tr><td>Our code vs the Hugging Face reference, with its float32 rounding steps switched off (relative gap)</td><td>1e-10</td><td>${fmt(cA.hf64_logits_max_rel_gap, 2)}</td><td>${fmt(cB.hf64_logits_max_rel_gap, 2)}</td></tr></table>
      <details><summary>show all six checks</summary><table class="lt">
      <tr><td>Same margin check, Quadrant III clamped run</td><td>1e-2</td><td>${fmt(cA.dla_gap_clamped, 2)}</td><td>${fmt(cB.dla_gap_clamped, 2)}</td></tr>
      <tr><td>Our code vs the reference as shipped (relative gap). Information only.</td><td>none</td><td>${fmt(cA.hf_logits_max_rel_gap, 2)}</td><td>${fmt(cB.hf_logits_max_rel_gap, 2)}</td></tr>
      <tr><td>Eq. 6 vs the full-answer calculation (absolute gap). A test checks this; each export also records the gap.</td><td>none</td><td>${fmt(cA.eq6_teacher_forced_max_abs_gap, 2)}</td><td>${fmt(cB.eq6_teacher_forced_max_abs_gap, 2)}</td></tr>
      <tr><td>Recomputed in this browser from the float32 arrays drawn: |margin − ΣDLA|</td><td>1e-2</td><td>${fmt(D.A.clientCheck.dlaGap, 2)}</td><td>${fmt(D.B.clientCheck.dlaGap, 2)}</td></tr>
      ${D.P.m.conservation ? `<tr><td>B − A of the parts adds up to B − A of the margin (pair export, float32 arrays)</td><td>1e-6</td><td colspan="2">${fmt(D.P.m.conservation.d_attr_gap_float32, 2)} · clamped ${fmt(D.P.m.conservation.d_attr_gap_float32_clamped, 2)}</td></tr>` : `<tr><td colspan="4" class="muted">This pair export is @1: it has no B − A check of its own.</td></tr>`}
      </table></details>
      <p>Each run uses float64 arithmetic. If the parts failed to add up to the whole, the status line next to the answer would turn red, and the figures should not be read as measurements until the export is fixed.</p>`],
    delta: ["What the fine-tune changed: ‖B − A‖ and B − A", `<p>For the same prompt, token and layer, the pair export stores <b>‖B − A‖</b>: the length of the difference between B's vector and A's vector. It is computed from both float64 runs and is exact. It is not the difference of two lengths: ‖B − A‖ is not ‖B‖ − ‖A‖. It is never negative, so it says how much changed and not in which direction.</p><p><b>B − A</b> with a sign is a difference between two single numbers, such as two DLA values, like the change in a coefficient. For the push on the margin it comes from the pair export (<code>d_head_attr</code>, <code>d_mlp_attr</code>); other signed changes are computed on this page and shown in italics.</p><p>‖W<sub>B</sub> − W<sub>A</sub>‖ shows where the weights moved.${mlpZero ? " In this pair every MLP weight change is exactly 0, so any MLP change is downstream of changed attention." : ""}</p>`],
    mlp: ["What is an MLP block?", `<p>After attention, each layer runs a small feed-forward network (an MLP) on every token separately. It has 1,536 hidden units, called neurons, per layer. Nothing moves between tokens here. The block height is the size of what it adds, ‖m‖.</p><p>Each neuron multiplies two input signals: a “gate” g̃ (passed through SiLU) and an “up” signal u. <b>Quadrant III</b> neurons are those where both g̃ and u are below −0.05 (counted in <code>q3_count</code>). In the clamped run we set these neurons' outputs to zero in every layer and position and run the model again. The purple ticks show what that does to the answer probabilities.</p>${ref("m = Σ_i SiLU(g̃_i) u_i W_down[:, i]")}`],
    segments: ["Template text and collapsed parts of the prompt", `<p>Most of the ${D.A.m.tokens.length} tokens are the chat template and fixed instructions. The prompt is split into labelled parts (message markers, instructions, the ${isBank(D.A) ? "scenario" : "question"}, the options, the answer cue, the answer position). The question, the options and the answer position are open by default. A collapsed part draws nothing: it is a gap with a label, never a summary block. A grey pill in the text is one collapsed part.</p><p>${D.A.m.segments ? "The parts come from the export (<code>manifest.segments</code>, contract @1.1): the exporter knows how the prompt was built." : "This is an @1 export without <code>segments</code>, so the prompt is shown as one part."}</p>`],
    clamp: ["Quadrant III and the clamped run", `<p>A neuron here has two input signals, a gate and an up signal. Quadrant III neurons have both below −0.05. The clamped run sets their outputs to zero in every layer and at every position, while the model runs, and records the new answer probabilities (the purple ticks). It is like re-estimating with a group of terms switched off, except that later layers respond to the change. The neurons were not chosen for being large or small. Whether this group matters for the answer is a hypothesis to test, not something this page shows.</p>`],
    models: ["The two models: A and B", `<p><b>A</b> is ${esc(D.A.m.model.label)} (<code>${esc(D.A.m.model.model_id)}</code>${D.A.m.model.adapter ? " plus an adapter" : ""}). <b>B</b> is ${esc(D.B.m.model.label)} (<code>${esc(D.B.m.model.model_id)}</code>${D.B.m.model.adapter ? " plus a LoRA adapter" : ""}).${D.B.m.model.adapter ? " The adapter was trained with DPO on made-up everyday scenarios, preferring the answer that matches the USA's direction on the Global Preferences Survey (e.g. more trusting, more patient). It was not trained on survey responses." : ""} The prompt, the ${isBank(D.A) ? "scenario" : "question"} and the answer position are the same for both. Only the model differs.${mlpZero ? " In this pair the adapter changed only attention weights." : ""}</p>`],
    terms: ["Terms", `<dl class="terms">${GLOSSARY.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`],
    resid: ["The running state (residual stream)", `<p>Each token has a running state: a list of 576 numbers that travels up through the layers. Each layer adds to it: state after = state before + attention addition + MLP addition. Nothing is overwritten. Because the parts only add, their contributions can be summed. (This “residual” is not a regression residual. It is a running total.) The bar height is the state's size ‖h<sup>l</sup><sub>t</sub>‖.</p><p>At the answer position, h<sup>l</sup>·w is the margin you would get by reading the answer off the state after l layers, with the final rescaling held fixed. It is the line in the charts. Its last point is the margin.</p>${ref("Arrays: <code>resid_norm</code>, <code>running_margin</code>.")}`],
    scale: ["Heights and colours", `<p>One scale per quantity, shared by A and B, so equal height means equal value. The scale is logarithmic with the median as its knee, so small values stay visible next to large ones. Heatmap colours are clipped at the 99th percentile so one extreme token does not wash out the rest; each colour key prints the clip value. The change maps have their own scale (gold). Outside the answer column, colours only name the kind of block. Inside it, blue and orange show the direction of the push.</p>`],
  };
  return L[key] ?? ["?", ""];
}
export function openLearn(D: Bundle, key: string) {
  let dlg = document.getElementById("learn") as HTMLDialogElement | null;
  if (!dlg) {
    dlg = document.createElement("dialog"); dlg.id = "learn"; document.body.append(dlg);
    dlg.addEventListener("click", (e) => { if (e.target === dlg || (e.target as HTMLElement).closest(".x")) dlg!.close(); });
  }
  const [h, body] = learnText(D, key);
  dlg.innerHTML = `<div class="lm-h"><b>${esc(h)}</b><button class="x">close ✕</button></div><div class="lm-b">${body}</div>`;
  if (!dlg.open) dlg.showModal();
}
