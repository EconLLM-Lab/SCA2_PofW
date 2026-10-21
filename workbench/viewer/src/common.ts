// Shared by the landing page and the three workbench tabs (ladder, matrix, 3D object).
// Data access is in data.ts. Nothing here computes a model quantity, except where a function
// says so in its name and comment (a browser B − A fallback for @1 files, segment sums).
// Copy follows design/layout-v2/COPY.md (string IDs in comments) and its PM rulings.

import { isLight } from "./data";
import { NO_3D } from "./notshipped";
import type { Bundle, Conservation, RelativeCheck, RelativeConservation, Run, Segment, Tensor } from "./data";

// ------------------------------------------------------------------ formatting
export const esc = (s: unknown) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
export const fmt = (v: number, p = 4) => (v === 0 ? "0" : Math.abs(v) >= 1e4 || Math.abs(v) < 1e-3 ? v.toExponential(p - 1) : v.toPrecision(p));
export const sgn = (v: number, p = 3) => (v >= 0 ? "+" : "−") + fmt(Math.abs(v), p);
/** A tau as the gate table writes it: an exact power of ten keeps its two-digit exponent (1e-04). */
export const tauStr = (t: number) => {
  const r = Math.round(Math.log10(t));
  return Math.abs(t - 10 ** r) <= 1e-12 * t ? `1e${r < 0 ? "-" : "+"}${String(Math.abs(r)).padStart(2, "0")}` : t.toExponential(1);
};
/** A relative error in the two-digit exponent form the plan and the gate table use (6.23e-06). */
export const relFmt = (v: number) => (v === 0 ? "0" : v.toExponential(1).replace(/e([+-])(\d)$/, "e$10$2"));
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
  return `<div class="key" title="${esc(src)}"><span class="key-l">${esc(label)}</span><span class="key-bar"><span style="background:linear-gradient(90deg,${lo},${hi})"></span>${ticks.map((t) => `<i style="left:${(t.u * 100).toFixed(0)}%">${fmt(t.v, 2)}</i>`).join("")}</span><span class="key-clip">≥ ${fmt(r.vmax, 3)} (${Math.round(r.pct * 100)}th percentile) all show as the brightest colour; the largest value is ${fmt(r.max, 3)}. The scale is logarithmic, so a few large values do not hide the small ones.</span></div>`;
}
/** Colour key for DLA: −vmax … 0 … +vmax, square-root scale, no clipping. */
export function divergingLegend(vmax: number, lp: string, lm: string, note = ""): string {
  const stops = [-1, -0.5, -0.25, 0, 0.25, 0.5, 1];
  const grad = stops.map((s) => `${diverging(s * vmax, vmax)} ${(((s + 1) / 2) * 100).toFixed(0)}%`).join(",");
  return `<div class="key"><span class="key-l">contribution to the log-odds</span><span class="key-bar"><span style="background:linear-gradient(90deg,${grad})"></span>${[-1, -0.5, 0, 0.5, 1].map((s) => `<i style="left:${(((s + 1) / 2) * 100).toFixed(0)}%">${s === 0 ? "0" : sgn(s * vmax, 2)}</i>`).join("")}</span><span class="key-clip">Blue = pushes the answer toward “${esc(lp)}”. Orange = toward “${esc(lm)}”. Grey = about zero. Colour deepens with size, up to ±${fmt(vmax, 3)} on this scale (the largest absolute value; nothing is clipped).${note}</span></div>`;
}

// ------------------------------------------------------------------ item, labels
export const labelPlus = (r: Run) => { const it = r.m.item; return String(it.labels[it.codes.indexOf(it.j_plus)]); };
export const labelMinus = (r: Run) => { const it = r.m.item; return String(it.labels[it.codes.indexOf(it.j_minus)]); };
export const short = (s: string, n = 48) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);
/** "(original)" / "(fine-tuned)" only when B is A plus an adapter (COPY C06). Otherwise registry labels only. */
export const roleOf = (D: Bundle, k: "A" | "B") => (D.B.m.model.adapter && D.A.m.model.model_id === D.B.m.model.model_id ? (k === "A" ? " (original)" : " (fine-tuned)") : "");
export const isBank = (r: Run) => r.m.item.kind === "bank";

// ------------------------------------------------------------------ answers on a scale (WB7-W)
// Which items run along one scale? The item records `meta.response_type` ("scale_1_10", "single_choice_4", ...).
// It does not record "ordered". Rule used here: a recorded `scale_*` type is ordered. A four-code item whose end
// answers carry text labels is assumed ordered (wvs_Q81, "A great deal" ... "None at all"). Three-code items
// (wvs_Q43, wvs_Q99) are not assumed ordered. Two-code items keep the two-answer headline.
type ItemInfo = Run["m"]["item"];
export const isOrdered = (it: ItemInfo): boolean => {
  if (it.codes.length < 3 || !it.codes.every((c) => Number.isFinite(Number(c)))) return false;
  const t = String(it.meta?.response_type ?? "");
  if (t.startsWith("scale_")) return true;
  const ends = [it.labels[0], it.labels[it.labels.length - 1]].map((l) => String(l));
  return t === "single_choice_4" && ends.every((l) => !Number.isFinite(Number(l)));
};
/** The lowest and highest answer codes of an ordered item, with their labels. */
export function scaleEnds(it: ItemInfo) {
  const nums = it.codes.map(Number), iLo = nums.indexOf(Math.min(...nums)), iHi = nums.indexOf(Math.max(...nums));
  return { lo: it.codes[iLo], hi: it.codes[iHi], loLab: String(it.labels[iLo]), hiLab: String(it.labels[iHi]) };
}
/** Expected answer: the sum of code × probability over all codes (the probabilities add to 1). */
export const expectedAnswer = (it: ItemInfo, probs: Record<string, number>) => it.codes.reduce((s, c) => s + Number(c) * (probs[c] ?? 0), 0);
export function modalAnswer(it: ItemInfo, probs: Record<string, number>) {
  let best = it.codes[0]; for (const c of it.codes) if ((probs[c] ?? 0) > (probs[best] ?? 0)) best = c;
  return { code: best, p: probs[best] ?? 0, label: String(it.labels[it.codes.indexOf(best)]) };
}
export const pct = (p: number) => `${(p * 100).toFixed(p > 0 && p < 0.01 ? 1 : 0)}%`;
const named = (code: string, label: string) => (label && label !== code ? `“${code}” (${short(label, 28)})` : `“${code}”`);
/** Odds factor of a log-odds change, as words: +1 ≈ odds × 2.7. */
export const ODDS_RULE = "+1 ≈ odds × 2.7, +5 ≈ odds × 150, −1 ≈ odds ÷ 2.7";

/** Real numbers of the pair now open, used by the worked examples in the pop-ups. Read from the export, never typed. */
function worked(D: Bundle) {
  const M = D.A.m.model, L = M.n_layers, H = M.n_heads, ro = D.A.m.readout.position, tk = D.A.m.tokens;
  const dd = dAttr(D, false);
  let best = { l: 0, h: -1, v: 0 };
  for (let l = 0; l < L; l++) for (let h = -1; h < H; h++) { const v = h < 0 ? dd.mlp(l) : dd.head(l, h); if (Math.abs(v) > Math.abs(best.v)) best = { l, h, v }; }
  const kmid = Math.round(L / 2), rmA = D.A.t.running_margin, rmB = D.B.t.running_margin;
  const dn = D.P.t["d_attn_norm"];
  let mx = { l: 0, t: 0, v: 0 };
  if (dn) for (let l = 0; l < L; l++) for (let t = 0; t < tk.length; t++) { const v = dn.get(l, t); if (v > mx.v) mx = { l, t, v }; }
  const rn = D.A.t.resid_norm, rnB = D.B.t.resid_norm, drn = D.P.t["d_resid_norm"];
  return {
    part: best.h < 0 ? `the MLP block of layer ${best.l}` : `head ${best.h} of layer ${best.l}`, partV: best.v,
    partToward: best.v >= 0 ? labelPlus(D.A) : labelMinus(D.A), dMargin: dd.margin, kmid, L,
    midA: rmA.get(kmid), midB: rmB.get(kmid), endA: rmA.get(L), endB: rmB.get(L),
    mxL: mx.l, mxTok: tokText(tk[mx.t].text), mxT: mx.t, mxV: mx.v, hasMx: !!dn && mx.v > 0,
    rA: rn ? rn.get(L, ro) : NaN, rB: rnB ? rnB.get(L, ro) : NaN, rD: drn ? drn.get(L, ro) : NaN,
  };
}
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
  if (g.kind === "readout") return `answer position (t* = ${ro})`;
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
  if (ro > 0) out.push({ a: 0, b: ro - 1, n: ro, kind: "text", label: "whole prompt (this @1 export has no labelled parts)", text: text(0, ro - 1), open: true, exported: false });
  out.push({ a: ro, b: T - 1, n: T - ro, kind: "readout", label: `answer position (t* = ${ro})`, text: text(ro, T - 1), open: true, exported: false });
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
    rows.push({ label: "Size of the addition ‖o‖", tip: "How much this head adds to the running state (the length of its addition). It says how much, not in which direction.\nhead_norm · d_head_norm", a: a.head_norm.get(s.l, s.h, s.t), b: b.head_norm.get(s.l, s.h, s.t), d: p.d_head_norm ? { v: p.d_head_norm.get(s.l, s.h, s.t), how: "len", src: "‖o_B − o_A‖, d_head_norm" } : null });   // WB7-Q: new Q57 pairs ship without d_head_norm
    if (s.t === ro) { const ha = clamp ? a.head_attr_clamped : a.head_attr, hb = clamp ? b.head_attr_clamped : b.head_attr;
      rows.push({ label: `Contribution to the answer${cl}`, tip: `Contribution to the answer (direct logit attribution, DLA). How far this head's addition moves the log-odds, read straight through the model's last steps.\n${clamp ? "head_attr_clamped" : "head_attr"}`, a: ha.get(s.l, s.h), b: hb.get(s.l, s.h), d: dla(dd.head(s.l, s.h)) }); }
    if (a.attn_topk_mass && b.attn_topk_mass) rows.push({ label: "Top-16 attention share", tip: "Attention covered by the top 16. The share of this head's attention that its 16 largest attention weights cover (1 = all of it).\nattn_topk_mass", a: a.attn_topk_mass.get(s.l, s.h, s.t), b: b.attn_topk_mass.get(s.l, s.h, s.t), d: calc(a.attn_topk_mass.get(s.l, s.h, s.t), b.attn_topk_mass.get(s.l, s.h, s.t)) });
  } else if (s.kind === "mlp") {
    rows.push({ label: "Size of the addition ‖m‖", tip: "How much this MLP block adds to the running state (the length of its addition).\nmlp_norm · d_mlp_norm", a: a.mlp_norm.get(s.l, s.t), b: b.mlp_norm.get(s.l, s.t), d: { v: p.d_mlp_norm.get(s.l, s.t), how: "len", src: "‖m_B − m_A‖, d_mlp_norm" } });
    rows.push({ label: "Quadrant III neurons (count)", tip: "Quadrant III neurons (count). The neurons whose two input signals (gate and up) are both below −0.05 at this token. The clamped run switches these off.\nq3_count", a: a.q3_count.get(s.l, s.t), b: b.q3_count.get(s.l, s.t), d: calc(a.q3_count.get(s.l, s.t), b.q3_count.get(s.l, s.t)), int: true });
    if (s.t === ro) { const ma = clamp ? a.mlp_attr_clamped : a.mlp_attr, mb = clamp ? b.mlp_attr_clamped : b.mlp_attr;
      rows.push({ label: `Contribution to the answer${cl}`, tip: `Contribution to the answer (direct logit attribution, DLA). How far this MLP block's addition moves the log-odds.\n${clamp ? "mlp_attr_clamped" : "mlp_attr"}`, a: ma.get(s.l), b: mb.get(s.l), d: dla(dd.mlp(s.l)) }); }
  } else {
    rows.push({ label: "Size of the running state ‖h‖", tip: "The length of the running state (its list of numbers) at this token and layer.\nresid_norm · d_resid_norm", a: a.resid_norm.get(s.l, s.t), b: b.resid_norm.get(s.l, s.t), d: { v: p.d_resid_norm.get(s.l, s.t), how: "len", src: "‖h_B − h_A‖, d_resid_norm" } });
    if (s.t === ro) { const ra = clamp ? a.running_margin_clamped : a.running_margin, rb = clamp ? b.running_margin_clamped : b.running_margin;
      rows.push({ label: `Log-odds if read off here${cl}`, tip: "The log-odds (margin) you would get by reading the answer off the running state at this layer, with the final layer's rescaling held fixed.\nrunning_margin", a: ra.get(s.l), b: rb.get(s.l), d: calc(ra.get(s.l), rb.get(s.l)) }); }
  }
  return rows;
}
export function topKeys(r: Run, l: number, h: number, t: number, n = 5) {
  const out: { key: number; w: number }[] = [];
  if (!r.t.attn_topk_idx || !r.t.attn_topk_val) return out;   // heavy arrays not loaded yet (data.ts ensureHeavy)
  const K = r.t.attn_topk_idx.shape[3];
  for (let k = 0; k < K && out.length < n; k++) { const key = r.t.attn_topk_idx.get(l, h, t, k); if (key !== 65535) out.push({ key, w: r.t.attn_topk_val.get(l, h, t, k) }); }
  return out;
}
const cell = (d: Change) => !d ? "<td></td>" : d.how === "len" ? `<td class="num d" title="${esc(d.src)}"><span class="lenp">size </span>${fmt(d.v, 4)}</td>` : d.how === "exp" ? `<td class="num sx" title="${esc(d.src)}">${sgn(d.v, 3)}</td>` : `<td class="num" title="${esc(d.src)}"><span class="calc">${sgn(d.v, 3)}</span></td>`;
/** The A | B | Change table. Fixed column widths, so the headers sit over their numbers. */
export function cmpTable(rows: Row[]): string {
  return `<table class="cmp"><colgroup><col class="c0"><col class="c1"><col class="c1"><col class="c1"></colgroup><thead><tr><th></th><th>A</th><th>B</th><th>Change (B − A)</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><td title="${esc(r.tip)}">${esc(r.label)}</td><td class="num">${r.int ? r.a : fmt(r.a, 4)}</td><td class="num">${r.int ? r.b : fmt(r.b, 4)}</td>${cell(r.d)}</tr>`).join("")}</tbody></table>`;
}
export const CHANGE_FOOT = `<div class="foot"><span class="d">gold</span> = the size of the change, ‖B − A‖: how far B's vector is from A's. It is a length, never negative, and exact (from the pair export). With a sign = the change B − A between two single numbers. <span class="sx">upright</span> means it comes from the pair export. <span class="calc">italic</span> means this page computed it.</div>`;

export function sliceName(D: Bundle, s: Slice): string {
  return s.kind === "head" ? `Head ${s.h} · layer ${s.l}` : s.kind === "mlp" ? `MLP block · layer ${s.l}` : s.l === D.A.m.model.n_layers ? "Running state · after the last layer" : `Running state · entering layer ${s.l}`;
}
/** o.bare: the body only (no card, no header), for the v3 pin drawer, which draws its own header. */
export function inspectorHTML(D: Bundle, s: Slice, o: { pinned?: boolean; clamp?: boolean; note?: string; bare?: boolean } = {}): string {
  const tk = D.A.m.tokens, ro = D.A.m.readout.position;
  let html = o.bare ? "" : `<div class="card ${o.pinned ? "pinned" : ""}"><div class="card-h"><span>${esc(sliceName(D, s))}</span>
    <span class="tag" title="${o.pinned ? "Press Esc to unpin" : "Click to pin"}">${o.pinned ? "pinned" : "preview"}</span>${lm(s.kind, "learn more")}</div>`;
  html += `${o.note ? `<div class="note">${o.note}</div>` : ""}
    <div class="tokline">token ${s.t}: “<b>${esc(tokText(tk[s.t].text))}</b>”${s.t === ro && tk[s.t].text.trim() === "" ? " (a space; the answer code is the next token)" : ""}${s.t === ro ? ' <span class="ro" title="answer position (t*): where the model is about to write its answer">answer position (t*)</span>' : ""}</div>
    ${cmpTable(compareRows(D, s, o.clamp))}`;
  if (s.kind === "head") {
    const ka = topKeys(D.A, s.l, s.h, s.t), kb = topKeys(D.B, s.l, s.h, s.t);
    const col = (ks: { key: number; w: number }[]) => ks.map((k) => `<div class="kk"><span class="bar" style="width:${(k.w * 100).toFixed(0)}%"></span><span class="num">${k.w.toFixed(2)}</span> · #${k.key} “${esc(tokText(tk[k.key].text))}”</div>`).join("");
    if (isLight(D.A) || isLight(D.B)) html += `<div class="sub">Where this head looks: ${NO_3D}</div>`;   // light run: no attention weights exist, so no spinner
    else if (!(D.A.t.attn_topk_idx && D.B.t.attn_topk_idx)) html += `<div class="sub">Where this head looks: the attention weights are still loading; this panel fills in when they arrive.</div>`;
    else html += `<div class="sub">Where this head looks${s.t === ro ? " from the answer position" : " from this token"}: its largest attention weights (weight · token number)</div><div class="two"><div><i>A</i>${col(ka)}</div><div><i>B</i>${col(kb)}</div></div>`;
    const dw = D.P.t.d_weight_head;
    html += `<div class="sub" title="Size of the weight change (Frobenius norm: the square root of the sum of squared differences). 0 means untouched. k and v are shared by 3 heads.">How far this head's weights moved from the base, B vs A (its four weight matrices q, k, v, o): <span class="num">${[0, 1, 2, 3].map((j) => fmt(dw.get(s.l, s.h, j), 2)).join(", ")}</span></div>`;
  }
  if (s.kind === "mlp") {
    const dw = D.P.t.d_weight_mlp;
    html += `<div class="sub">How far this MLP block's weights moved from the base, B vs A (its three weight matrices gate, up, down): <span class="num">${[0, 1, 2].map((j) => fmt(dw.get(s.l, j), 2)).join(", ")}</span> ${dw.get(s.l, 0) === 0 && dw.get(s.l, 1) === 0 && dw.get(s.l, 2) === 0 ? "(0: this adapter changed no MLP weights)" : ""}</div>`;
  }
  return html + CHANGE_FOOT + (o.bare ? "" : "</div>");
}

// ------------------------------------------------------------------ gated checks (frame status glyph, fail banner)
/** One gated check. A `relative` row comes from `conservation.relative.checks[k]` of a capture@1.1
 * manifest: `v` is then an error relative to `scale`, `thr` its tau, and `ok` the row's own `pass`.
 * A legacy row (a manifest without `relative`) comes from
 * `conservation.thresholds[k]`: `v` is an absolute value and `thr` the absolute bound. */
export interface Check { who: "A" | "B" | "pair"; k: string; v: number; thr: number; ok: boolean;
  /** true when `v` is relative to `scale` and `thr` is a tau, not an absolute bound. */
  relative?: boolean; scale?: number; simulated?: boolean }
/** The dev `?fail=` keys, mapped onto the row name that key stands for in a manifest of either
 * generation: the absolute set and the relative set ask the same questions under different names,
 * so one dev key names one check either way (and an unknown key still adds a simulated row). */
const FAIL_KEYS: Record<string, string[]> = {
  "1": ["dla_gap", "readout"], dla_gap: ["dla_gap", "readout"], readout: ["readout", "dla_gap"],
  residual_closure_inf: ["residual_closure_inf", "residual_closure"],
  residual_closure: ["residual_closure", "residual_closure_inf"],
  hf64_logits_max_rel_gap: ["hf64_logits_max_rel_gap", "logits_reference"],
  logits_reference: ["logits_reference", "hf64_logits_max_rel_gap"],
};
const DEV = Boolean((import.meta as unknown as { env?: { DEV?: boolean } }).env?.DEV);
/** The checks, passing when value < threshold. A manifest whose `pass` is false with no failing key adds a
 * failing \"pass flag\" entry, so a failure is never lost. Dev server only: `?fail=<key>` (or `fail=1` = dla_gap)
 * marks the first check with that key as failed, flagged `simulated` (the banner says so). */
export function checksOf(D: Bundle): Check[] {
  const out: Check[] = [];
  const src: [Check["who"], Record<string, unknown> | undefined][] = [["A", D.A.m.conservation as unknown as Record<string, unknown>], ["B", D.B.m.conservation as unknown as Record<string, unknown>], ["pair", D.P.m.conservation as unknown as Record<string, unknown> | undefined]];
  for (const [who, c] of src) {
    if (!c) continue;
    const rel = c.relative as RelativeConservation | undefined;
    if (rel && rel.checks) {
      // capture@1.1 with the relative gates (t_1547e1a8): one row per check, rel against its tau,
      // and the row's own `pass` is the verdict -- the exporter's, not one recomputed from here.
      for (const [k, g] of Object.entries(rel.checks))
        out.push({ who, k, v: g.rel, thr: g.tau, ok: g.pass, relative: true, scale: g.scale });
    } else {
      // No relative block: a manifest written before relative gates. The absolute
      // gate is all there is, and that is what such an export was gated by.
      for (const [k, thr] of Object.entries((c.thresholds ?? {}) as Record<string, number>)) {
        const v = c[k];
        if (typeof v === "number") out.push({ who, k, v, thr, ok: v < thr });
      }
    }
    if (c.pass === false && !out.some((x) => x.who === who && !x.ok)) out.push({ who, k: "pass flag", v: NaN, thr: NaN, ok: false });
  }
  const f = DEV ? new URLSearchParams(location.search).get("fail") : null;
  if (f) {
    const keys = FAIL_KEYS[f] ?? [f], i = out.findIndex((c) => keys.includes(c.k));
    if (i >= 0) out[i] = { ...out[i], v: out[i].thr * 3.1, ok: false, simulated: true };
    else out.push({ who: "A", k: keys[0], v: NaN, thr: NaN, ok: false, simulated: true });
  }
  return out;
}
/** Which exports a failed check taints. A face of the ladder that uses a tainted export turns red. */
export const failedWho = (cs: Check[]) => new Set(cs.filter((c) => !c.ok).map((c) => c.who));
export const faceTainted = (face: string, bad: Set<string>) => (face === "a" ? bad.has("A") : face === "b" ? bad.has("B") : bad.size > 0);
/** One check as a line of text: `A residual_closure rel 6.2e-06 < 1e-04` for a relative gate,
 * `A residual_closure_inf = 5.6e-3 ≥ 0.001` for a legacy absolute one. */
export const checkLine = (c: Check) => c.relative
  ? `${c.who} ${c.k} rel ${relFmt(c.v)} ${c.ok ? "<" : "≥"} ${tauStr(c.thr)}${c.simulated ? " (simulated with ?fail · not data)" : ""}`
  : `${c.who} ${c.k} = ${isNaN(c.v) ? "fails" : fmt(c.v, 2)}${isNaN(c.thr) ? "" : (c.ok ? " < " : " ≥ ") + c.thr}${c.simulated ? " (simulated with ?fail · not data)" : ""}`;

// ------------------------------------------------------------------ the answer card ("details")
export function readoutHTML(D: Bundle): string {
  const it = D.A.m.item, codes = it.codes, lp = labelPlus(D.A), lmn = labelMinus(D.A), n = codes.length, many = n > 2, ord = isOrdered(it);
  const bars = (r: Run, col: string) => codes.map((c) => {
    const p = r.m.readout.probs[c], pc = r.m.readout.probs_clamped[c];
    return `<div class="pr"><span>${esc(c)}</span><div class="trk"><div style="width:${(p * 100).toFixed(1)}%;background:${col}"></div><i style="left:${(pc * 100).toFixed(1)}%" title="clamped run (Quadrant III neurons switched off): ${pc.toFixed(3)}"></i></div><span class="num">${p.toFixed(3)}</span></div>`;
  }).join("");
  const ok = checksOf(D).every((c) => c.ok);
  const prA = D.A.m.readout.probs, prB = D.B.m.readout.probs, ma = modalAnswer(it, prA), mb = modalAnswer(it, prB);
  const shown = `A gives ${esc(named(ma.code, ma.label))} the highest probability (${pct(ma.p)}). B gives ${esc(named(mb.code, mb.label))} (${pct(mb.p)}).`;
  let scaleBlock = "";
  if (many) {
    const e = ord ? scaleEnds(it) : null, eA = expectedAnswer(it, prA), eB = expectedAnswer(it, prB);
    scaleBlock = `<h4>How to read a question with many answers</h4><ul>
      ${e ? `<li><b>Average answer</b> (expected answer): each answer code times its probability, added up. Here A ${eA.toFixed(2)}, B ${eB.toFixed(2)}, on the ${esc(e.lo)}–${esc(e.hi)} scale. Higher means closer to “${esc(short(e.hiLab, 40))}” (${esc(e.hi)}). Paper B scores each item this way (E[recode]).</li>` : `<li>This question has no scale of answers in the export, so no average is shown. Read the most likely answer and the bars.</li>`}
      <li><b>Most likely answer</b>: the answer with the highest probability. ${shown}</li>
      <li><b>Log-odds of “${esc(it.j_plus)}” over “${esc(it.j_minus)}”</b>: compares only ${ord ? "the two end answers" : "the first and last answer codes"}. Here A ${D.A.m.readout.margin.toFixed(2)}, B ${D.B.m.readout.margin.toFixed(2)}. ${ODDS_RULE}.</li></ul>
      <p>The log-odds can move against the average answer. A question with ${n} answers has ${n - 2} answers in the middle that the log-odds ignores. If both end answers have a probability near zero, a small change in a tiny number gives a big change in the log-odds.</p>
      <p>Why use the ends at all? The log-odds is a difference of two answer scores. A difference of two scores is linear in the model's internal state. This lets the Ladder split it exactly into a part for each head and each layer, which the line “the parts add up” checks. An average answer cannot be split in that way.</p>`;
  } else {
    scaleBlock = `<h4>How to read a question with two answers</h4><p>The two probabilities add to 100%, so the log-odds and the probability tell the same story. Paper B scores each item as the expected answer (E[recode]): the answer code times its probability, added up. With two answers this is a simple function of the one probability.</p>`;
  }
  return `<div class="card"><div class="card-h"><span>The model's answer · ${esc(it.item_id)}</span>${lm("eq6", "learn more")}</div>
    <h4>What this card shows</h4>
    <p>The answer of the model to this survey question, as a probability for each answer code. Each bar is one probability, from 0% to 100%. The bars of one model add to 100%. A model gives probabilities. It does not say what people say.</p>
    <div class="q" title="Equivalently logit(“${esc(it.j_plus)}”) − logit(“${esc(it.j_minus)}”): the shared normaliser of the softmax cancels. Called the margin in the code.">Log-odds of “${esc(it.j_plus)}” over “${esc(it.j_minus)}” (the margin) = log[P(“${esc(it.j_plus)}”) / P(“${esc(it.j_minus)}”)]. Positive means the model leans toward “${esc(short(lp, 60))}” over “${esc(short(lmn, 60))}”.</div>
    <div class="q">Answer codes: ${codes.map((c, i) => { const lab = String(it.labels[i]); return lab === c ? `<b>${esc(c)}</b>` : `<b>${esc(c)}</b> = ${esc(short(lab, isBank(D.A) ? 70 : 40))}`; }).join(" · ")}</div>
    <div class="two"><div><i title="${esc(D.A.m.model.label)}" style="color:${A_COL}">A · log-odds ${D.A.m.readout.margin.toFixed(3)}</i>${bars(D.A, A_COL)}</div><div><i title="${esc(D.B.m.model.label)}" style="color:${B_COL}">B · log-odds ${D.B.m.readout.margin.toFixed(3)}</i>${bars(D.B, B_COL)}</div></div>
    <div class="sub">Change from the base, B − A: log-odds <span class="num">${sgn(D.P.m.d_margin)}</span> · P(“${esc(short(lp, 30))}”) <span class="num">${sgn(D.P.m.d_probs[it.j_plus])}</span>. <span style="color:var(--q3)">Purple tick</span>: the result of the clamped run (Quadrant III neurons switched off). ${lm("clamp", "What is the clamped run?")}</div>
    <h4>How to read the bars</h4>
    <ul><li>Bar length = probability. Grey is A (the base model). Teal is B.</li>
    <li>The number at the right of each bar is the same probability, from 0 to 1.</li>
    <li>The purple tick marks the probability of that answer in the clamped run, on the same 0% to 100% scale as the bar. A tick far from the end of the bar means the probability changed a lot when these neurons were switched off. A tick near the end means it changed little. This tests one small group of neurons. It does not test the whole model.</li>
    <li>Example from this page: ${shown}</li></ul>
    ${scaleBlock}
    <h4>What the log-odds scale means</h4><p>${ODDS_RULE}. Zero means even odds between the two answers. The change B − A is a difference of two log-odds, so it uses the same scale.</p>
    <h4>What this card does not show</h4><p>It does not show why B differs from A (use the Ladder). It does not show what any group of people would answer. The probabilities are not a survey result.</p>
    <div class="cons ${ok ? "ok" : "bad"}">${ok ? "✓ The parts add up to the total: every accounting check passes for A and B" : "✗ An accounting check failed. Do not read these figures as measurements until the export is fixed."} ${lm("conservation", "see the accounting checks")}</div></div>`;
}

// ------------------------------------------------------------------ learn-more pop-ups (P01–P14)
export const lm = (key: string, text: string, topic?: string) => { const t = `Learn more: ${topic ?? TOPIC[key] ?? key}`; return `<button class="lm" data-learn="${key}" title="${esc(t)}" aria-label="${esc(t)}">${esc(text)}</button>`; };
const TOPIC: Record<string, string> = { eq6: "the answer as a probability", head: "attention heads", tstar: "the answer position", norm: "the size of a vector", dla: "contribution to the answer (DLA)", conservation: "the accounting checks", delta: "what the adapter changed", mlp: "MLP blocks", segments: "template text", clamp: "the clamped run", models: "the two models", terms: "the glossary", resid: "the running state", scale: "heights and colours", groundTruth: "the human reference" };

export const GLOSSARY: [string, string][] = [
  ["log-odds (margin)", "The log of the odds of the first answer code over the second: log[P(first) / P(second)]. It equals the gap between their scores. Positive means the model leans toward the first. The code and the paper call it the margin. Economists know log-odds from logit. Scale: +1 is odds × 2.7, +5 is odds × 150, −1 is odds ÷ 2.7."],
  ["expected answer (average answer)", "The answer codes added up, each one times its probability: Σ code × P(code). On a 1–10 question it is the average answer of the model. Paper B scores an item this way (E[recode]). Unlike the log-odds of the two end answers, it uses every answer."],
  ["end answers", "The first and the last answer code of a question, for example “1” and “10” on a 1–10 scale. The log-odds in the charts compares only these two. If both are near zero, the log-odds can move against the expected answer."],
  ["read off after a layer", "The answer that the model would give if it stopped after this layer. The charts show it as log-odds for each layer. Mid-layer readings are rough and only the last layers are close to the real answer. A line near 0 early means no readable preference yet, not neutral."],
  ["logit", "The model's raw score for one answer, before it is turned into a probability. Only differences between scores matter. Like the utility index in a multinomial logit."],
  ["Eq. 6", "The step that turns the scores of the response codes into probabilities (a softmax over the codes only). Eq. 6 of the SCA2 paper (arXiv:2610.06562)."],
  ["answer position (t*)", "The last position of the prompt, where the model is about to write its answer. Every probability, log-odds and contribution is read here. Also called the readout position."],
  ["running state (residual stream)", "A list of {d_model} numbers for each token. Each layer adds to it, and nothing is overwritten. A running total, not a regression residual."],
  ["attention head", "The part of a layer that chooses which earlier words to read. For the current word, it takes a weighted average of what earlier words hold and adds a summary to the running state. {n_heads} per layer."],
  ["MLP block", "The part of a layer that transforms what the attention heads read. A small feed-forward neural network (a multilayer perceptron, MLP) applied to each token on its own, {d_ffn} hidden units (neurons) per layer."],
  ["contribution to the answer (DLA, direct logit attribution)", "Each part's share of the log-odds, read straight through the model's last steps with the final rescaling held fixed. The shares add up to the log-odds, like the β·x terms of a logit index."],
  ["direct effect", "The part of an effect that goes straight to the answer. A part that works by changing a later layer gets no credit here, as with a direct path in a mediation model."],
  ["accounting checks", "Tests that the parts add back to the whole, and that our code matches a reference implementation. The “do the line items add to the total?” check."],
  ["float64", "64-bit binary floating-point arithmetic, about 16 significant digits. R's default numeric type. Most language-model runs use 16 or 32 bits."],
  ["fine-tune", "Training an already-trained model a bit more on a narrower set of examples, so its answers shift."],
  ["country adapter (LoRA)", "A small add-on to the model's weights, trained on one country's six preference signs (trust, risk taking, patience, altruism, positive and negative reciprocity). The original weights stay as they were. LoRA is a way to fine-tune that learns small low-rank corrections added on top."],
  ["sign prompt", "The same six signs written into the prompt, instead of into an adapter. The weights do not change."],
  ["base model", "The unchanged model that we start from. In the viewer it is A."],
  ["DPO (direct preference optimization)", "Training from pairs of answers, one preferred and one not. Here the pairs are made-up everyday scenarios, preferring the answer that matches a country's direction on the Global Preferences Survey (for example, more trusting, more patient). Not survey responses."],
  ["clamped run", "A second run of the same model on the same prompt, with the Quadrant III neurons switched off: their output is set to zero while the model runs, then the answer is measured again. It tests whether the answer depends on that group. Later layers can still respond. The purple tick on a bar is its result."],
  ["Quadrant III", "The MLP neurons whose gate input and up input are both below −0.05 at a token. The clamped run switches this group off. The count at a token is q3_count."],
  ["size of the change ‖B − A‖ vs change B − A", "‖B − A‖ is the length of the difference of two vectors: never negative. B − A is the signed difference of two numbers."],
  ["top-16 attention", "For each head and token only the 16 largest attention weights are kept. “Covered” says how much of the attention they account for."],
  ["token", "A word piece. The model reads and writes tokens, not words."],
  ["layer", "One processing step. Each layer lets the attention heads read, then the MLP block transform. This model has {n_layers}."],
  ["embedding term", "The contribution to the log-odds of the starting vector, before layer 0. The part that comes from the words themselves. The intercept of the split."],
  ["teacher-forced", "Scoring each full answer token by token (the chain rule), instead of reading only the next-token scores."],
  ["frozen scale (ρ)", "The model rescales the final state before scoring. The contributions hold that scale fixed so the parts add exactly."],
  ["ablation / patching", "Changing or replacing part of the model and re-running, to see if the answer depends on it. The clamped run is one such change."],
  ["template text", "The fixed chat-format markers and instructions around the question. Most of the prompt."],
  ["size of a vector (‖·‖)", "The usual length: the square root of the sum of squares."],
];

// ------------------------------------------------------------------ the checks table of "learn more" (P04)
/** Row labels for the gate keys of either generation of manifest (`conservation.relative.checks` of
 * `gates.py`, and the absolute set it replaced). An unknown key falls back to its own name, so a
 * gate added later still shows up here. */
const CHECK_LABEL: Record<string, string> = {
  residual_closure: "The parts add up to the final running state (largest gap in any of its numbers, at any token)",
  head_closure: "The heads add up to the attention addition (largest gap in any number, at any token)",
  readout: "The contributions add up to the log-odds (the DLA gap)",
  logits_reference: "Our code gives the same scores as the Hugging Face reference code (largest relative gap)",
  residual_closure_inf: "The parts add up to the final running state (largest gap in any of its numbers, at any token)",
  head_closure_inf: "The heads add up to the attention addition (largest gap in any number, at any token)",
  dla_gap: "The contributions add up to the log-odds (absolute gap)",
  hf64_logits_max_rel_gap: "Our code gives the same scores as the Hugging Face reference code, with its float32 rounding steps switched off (relative gap)",
  gap_f64: "The change in the parts (B − A) adds up to the change in the log-odds (float64 differences)",
  gap_f32: "The change in the parts (B − A) adds up to the change in the log-odds (summed from the stored float32 arrays)",
};
const checkLabel = (k: string) => (CHECK_LABEL[k] ?? k) + (k.endsWith("_clamped") ? " · Quadrant III clamped run" : "");
/** One cell of the relative table: the relative error, then the row's own verdict. The tooltip says
 * what the error was divided by, which is what makes the gate comparable across dtypes and models. */
const relCell = (g: RelativeCheck, tip = "") =>
  `<td class="num" title="${esc(`${tip}rel = ${fmt(g.error, 2)} ÷ ${fmt(g.scale, 2)} (${g.scale_desc})`)}">${relFmt(g.rel)} ${g.pass ? "✓" : "✗"}</td>`;

/** The checks table for a bundle whose runs carry `conservation.relative` (a float32 export, and any
 * capture@1.1 manifest written after t_1547e1a8). Every row is `rel = error / scale` against its tau,
 * which is the verdict the exporter computed. The absolute thresholds still travel in the manifest
 * and the browser re-sum still shows its number, but neither can fail this table: below one ulp of
 * the stream they are not gates, which is the whole point of the relative set. */
function relativeTable(D: Bundle, cA: Conservation, cB: Conservation): string {
  const ra = cA.relative!, rb = cB.relative!;
  const row = (k: string, ga: RelativeCheck, gb?: RelativeCheck) =>
    `<tr><td>${esc(checkLabel(k))}</td><td class="num">rel ≤ ${tauStr(ga.tau)}</td>${relCell(ga)}${gb ? relCell(gb) : `<td class="num">—</td>`}</tr>`;
  const keys = Object.keys(ra.checks);
  const main = keys.filter((k) => !k.endsWith("_clamped"));
  const clamped = keys.filter((k) => k.endsWith("_clamped"));
  const notGated = cA.legacy_absolute_applicable === false || cB.legacy_absolute_applicable === false;
  // Say the dtype the manifest records; legacy_absolute_applicable alone does not imply float32 (WB4-V N1).
  const dtype = String((D.A.m as unknown as { provenance?: { compute_dtype?: string } }).provenance?.compute_dtype ?? "unknown");
  const pc = D.P.m.conservation;
  const pairRow = !pc
    ? `<tr><td colspan="4" class="muted">This pair export is @1: it has no B − A check of its own.</td></tr>`
    : pc.relative?.checks
      ? Object.entries(pc.relative.checks).map(([k, g]) =>
          `<tr><td>${esc(checkLabel(k))}</td><td class="num">rel ≤ ${tauStr(g.tau)}</td>${relCell(g, "pair · ").replace('<td class="num"', '<td colspan="2" class="num"')}</tr>`).join("\n      ")
      : `<tr><td>${esc(checkLabel("gap_f32"))}. This pair block carries no relative gate, so the bound is the absolute one of the contract.</td><td class="num">1e-6</td><td colspan="2" class="num">${fmt(pc.d_attr_gap_float32, 2)} · clamped ${fmt(pc.d_attr_gap_float32_clamped, 2)}</td></tr>`;
  return `<table class="lt"><tr><th>Accounting check</th><th>Tolerance τ (rel ≤ τ)</th><th>A</th><th>B</th></tr>
      ${main.map((k) => row(k, ra.checks[k], rb.checks[k])).join("\n      ")}
      <tr><td>Added up again in this browser from the float32 arrays drawn: |log-odds − sum of contributions| (|margin − ΣDLA|)</td><td class="num">${notGated ? "not gated here" : "1e-2"}</td><td class="num">${fmt(D.A.clientCheck.dlaGap, 2)}</td><td class="num">${fmt(D.B.clientCheck.dlaGap, 2)}</td></tr>
      ${pairRow}</table>
      <details><summary>show the clamped run and the rows that are for information only</summary><p>${lm("clamp", "What is the clamped run?")}</p><table class="lt">
      ${clamped.map((k) => row(k, ra.checks[k], rb.checks[k])).join("\n      ")}
      <tr><td>Our code vs the reference code as shipped (relative gap). For information only.</td><td class="num">none</td><td class="num">${fmt(cA.hf_logits_max_rel_gap, 2)}</td><td class="num">${fmt(cB.hf_logits_max_rel_gap, 2)}</td></tr>
      <tr><td>Eq. 6 vs the full-answer calculation (absolute gap). A test checks this, and each export also records the gap.</td><td class="num">none</td><td class="num">${fmt(cA.eq6_teacher_forced_max_abs_gap, 2)}</td><td class="num">${fmt(cB.eq6_teacher_forced_max_abs_gap, 2)}</td></tr>
      </table></details>
      <p>Every row of the first table is <b>relative</b>. The <code>rel</code> value is the error divided by the size of the thing being measured (each row's tooltip names it). A row passes when <code>rel ≤ τ</code>. Each τ is ${ra.tau_multiple}× the largest rounding error measured for that check on this model family, rounded up to the next power of ten (<code>plans/stage1_f32_gaps.md</code>). So a check does not fail on rounding noise, and it still catches a real break.</p>
      <p>${dtype !== "float32" && notGated
        ? `This export was computed in <b>${esc(dtype)}</b> (<code>provenance.compute_dtype</code>). Its manifest marks the absolute limits of the contract as not applicable to this capture (<code>legacy_absolute_applicable: false</code>). So the verdict is the relative table above. The browser re-sum is still shown with its number.`
        : notGated
        ? "This export was computed in <b>float32</b> (<code>provenance.compute_dtype</code>). The absolute limits of the contract cannot be met at that number format. The absolute limit of 1e-3 on the residual check is only about nine float32 ulps wide (an ulp is the smallest step the number format can take) when the running state's largest entry is 8.9e2. At that size, rounding noise alone can break it, so it would flag noise instead of a real error. Those rows are still shown where they exist, and the browser re-sum is shown with its number. The verdict is this relative table."
        : "This export was computed in <b>float64</b> (<code>provenance.compute_dtype</code>); the relative checks still carry the verdict, with more headroom than the absolute set had."}</p>`;
}

export function learnText(D: Bundle, key: string): [string, string] {
  const it = D.A.m.item, cA = D.A.m.conservation, cB = D.B.m.conservation, ro = D.A.m.readout.position;
  const lp = esc(short(labelPlus(D.A), 70)), lmn = esc(short(labelMinus(D.A), 70));
  const mlpZero = D.P.t.d_weight_mlp.absMax() === 0;
  const ref = (s: string) => `<p class="muted"><i>For reference:</i> ${s}</p>`;
  // Model sizes come from this run's manifest, never from text: the same pop-ups serve SmolLM2-135M and Llama-3.1-8B.
  const M = D.A.m.model as typeof D.A.m.model & { d_model: number; d_ffn: number; n_heads: number; n_kv_heads?: number };
  const n = (v: number) => (v ?? 0).toLocaleString("en-US");
  const fill = (t: string) => t.replace("{d_model}", n(M.d_model)).replace("{d_ffn}", n(M.d_ffn)).replace("{n_heads}", String(M.n_heads)).replace("{n_layers}", String(M.n_layers));
  const W = worked(D);
  const L: Record<string, [string, string]> = {
    eq6: ["The answer as a probability (Eq. 6)", `<p>The model's answer to a question is a set of probabilities, one for each response code. They work like the predicted choice shares of a multinomial logit. Every other number in the workbench explains how the model got to these probabilities.</p><p>The model reads the whole prompt. At the answer position (t* = ${ro}) it gives a score to every possible next token. We keep only the scores for the response codes (${it.codes.map(esc).join(", ")}) and turn them into probabilities with a softmax. This is the same form as a multinomial logit, restricted to the response codes. It is Eq. 6 of the SCA2 paper (arXiv:2610.06562). We also compute the same probabilities a second way, by scoring each full answer token by token: a test checks this; each export also records the gap. Here the largest gap is ${fmt(Math.max(cA.eq6_teacher_forced_max_abs_gap, cB.eq6_teacher_forced_max_abs_gap), 2)}.</p><p>The <b>log-odds</b> of “${esc(it.j_plus)}” over “${esc(it.j_minus)}” (called the <b>margin</b> in the code) is log[P(“${esc(it.j_plus)}”) / P(“${esc(it.j_minus)}”)]. Equivalently, it is the gap between their two scores (logits), because the softmax's shared normaliser cancels. Positive means the model leans toward “${lp}”. Every “contribution to the answer” figure in the workbench splits this one number into parts.</p>`],
    head: ["What is an attention head?", `<p>An attention head is the part of a layer that chooses which earlier words to read when the model works on a word. You can think of it as a weighted lookup of context.</p><p>When the model works on a word, an attention head looks back at the earlier words and takes a weighted average of what it finds there. The weights (the attention weights, A[q,k]) are positive and add to 1, like kernel weights. The head then adds a summary, a list of ${n(M.d_model)} numbers, to the running state. This model has ${M.n_heads} heads in each layer. They share ${M.n_kv_heads ?? M.n_heads} sets of key and value inputs.</p><p>The block height is the <b>size of that summary</b>, ‖o_h‖. It says how much the head adds, not in which direction. “Where this head looks” lists the stored 16 largest attention weights. At the answer position the head also has a contribution to the answer (direct logit attribution, DLA): how much its addition moves the log-odds, read straight through the model's last steps.</p>${ref("o_h = softmax(q kᵀ/√64 + causal) v<sub>kv(h)</sub> W_O[:,h]ᵀ. Arrays: <code>head_norm</code>, <code>attn_topk_idx/_val</code>, <code>head_attr</code>.")}`],
    tstar: ["The answer position (t*)", `<p>The answer position is the spot in the prompt where the model is about to write its answer. It is the one place where we read the outcome.</p><p>A prompt is a list of tokens (word pieces). The model writes its answer right after the last one. That last position is called t*. Here t* = ${ro}. The answer probabilities, the log-odds, and every “contribution to the answer” number are read at this one position. Other positions are shown for context. Think of t* as the one row of the data where the outcome is evaluated.</p>`],
    norm: ["What is the size of a vector (‖·‖)?", `<p>Many numbers in the workbench are sizes. A size says how much a part adds to the model's running state, whatever the direction.</p><p>A vector here is a list of numbers (${n(M.d_model)} for a running state). Its size, written ‖v‖, is the usual length: the square root of the sum of squares. Bigger means the part added more. It does not say in which direction. Two vectors of equal size can push the answer opposite ways. Only the contribution numbers at the answer position carry a direction.</p>`],
    dla: ["How much did each part contribute to the answer?", `<p>Each attention head and each MLP block pushes the answer a little toward one response code or the other. The contribution to the answer measures that push, part by part, in the units of the log-odds. It is the closest thing here to the coefficient on one term of a logit index.</p><p>The technical name is <b>direct logit attribution (DLA)</b>. It splits the log-odds into additive pieces, like splitting a logit index into β·x terms. Each part's addition is read straight through the model's last steps, with the final rescaling ρ held fixed. Then the log-odds is exactly the embedding term + Σ heads + Σ neurons. Blue pushes toward “${lp}”, orange toward “${lmn}”.</p><p><b>Limit.</b> A contribution is the direct effect only, like a direct effect in a mediation model. A head that changes what a later layer does gets no credit for that path.</p>${ref("w = γ<sub>final</sub> ⊙ (W<sub>U</sub>[j₊] − W<sub>U</sub>[j₋]) / ρ. Arrays: <code>head_attr</code>, <code>mlp_attr</code>, <code>neuron_attr</code>, <code>readout.embed_attr</code>; B − A: <code>d_head_attr</code>, <code>d_mlp_attr</code>, <code>d_embed_attr</code>.")}`],
    conservation: ["Do the parts add up? The accounting checks", `${checksOf(D).filter((c) => !c.ok).map((c) => `<p class="badp">✗ ${esc(checkLine(c))}</p>`).join("")}<p>An accounting check asks whether the parts add up to the total, like checking that the line items sum to the bill. If they do not, the figures cannot be trusted.</p><p>Three questions. Do the parts add up to the final running state? Do they add up to the log-odds? Does our code give the same numbers as the reference implementation? All three have to pass, for both models.</p>
      ${cA.relative && cB.relative ? relativeTable(D, cA, cB) : `<table class="lt"><tr><th>Accounting check</th><th>Must be below</th><th>A</th><th>B</th></tr>
      <tr><td>The parts add up to the final running state (largest gap in any of its numbers, at any token)</td><td>1e-3</td><td>${fmt(cA.residual_closure_inf, 2)}</td><td>${fmt(cB.residual_closure_inf, 2)}</td></tr>
      <tr><td>The contributions add up to the log-odds (absolute gap)</td><td>1e-2</td><td>${fmt(cA.dla_gap, 2)}</td><td>${fmt(cB.dla_gap, 2)}</td></tr>
      <tr><td>Our code gives the same scores as the Hugging Face reference code, with its float32 rounding steps switched off (relative gap)</td><td>1e-10</td><td>${fmt(cA.hf64_logits_max_rel_gap, 2)}</td><td>${fmt(cB.hf64_logits_max_rel_gap, 2)}</td></tr></table>
      <details><summary>show all six checks</summary><p>${lm("clamp", "What is the clamped run?")}</p><table class="lt">
      <tr><td>Same log-odds check, clamped run (Quadrant III neurons switched off)</td><td>1e-2</td><td>${fmt(cA.dla_gap_clamped, 2)}</td><td>${fmt(cB.dla_gap_clamped, 2)}</td></tr>
      <tr><td>Our code vs the reference code as shipped (relative gap). For information only.</td><td>none</td><td>${fmt(cA.hf_logits_max_rel_gap, 2)}</td><td>${fmt(cB.hf_logits_max_rel_gap, 2)}</td></tr>
      <tr><td>Eq. 6 vs the full-answer calculation (absolute gap). A test checks this, and each export also records the gap.</td><td>none</td><td>${fmt(cA.eq6_teacher_forced_max_abs_gap, 2)}</td><td>${fmt(cB.eq6_teacher_forced_max_abs_gap, 2)}</td></tr>
      <tr><td>Added up again in this browser from the float32 arrays drawn: |log-odds − sum of contributions| (|margin − ΣDLA|)</td><td>1e-2</td><td>${fmt(D.A.clientCheck.dlaGap, 2)}</td><td>${fmt(D.B.clientCheck.dlaGap, 2)}</td></tr>
      ${D.P.m.conservation ? `<tr><td>The change in the parts (B − A) adds up to the change in the log-odds (pair export, float32 arrays)</td><td>1e-6</td><td colspan="2">${fmt(D.P.m.conservation.d_attr_gap_float32, 2)} · clamped ${fmt(D.P.m.conservation.d_attr_gap_float32_clamped, 2)}</td></tr>` : `<tr><td colspan="4" class="muted">This pair export is @1: it has no B − A check of its own.</td></tr>`}
      </table></details>
      <p>Each run uses float64 arithmetic. If the parts failed to add up to the whole, the status line next to the answer would turn red, and the figures should not be read as measurements until the export is fixed.</p>`}`],
    delta: ["What the adapter changed: ‖B − A‖ and B − A", `<p>To see what the adapter (or the sign prompt) did, the workbench compares B with A in two ways. One is the size of the change in a part. The other is the signed change in a single number, which says which way the number moved.</p><p>For the same prompt, token and layer, the pair export stores <b>‖B − A‖</b>: the length of the difference between B's vector and A's vector. It is computed from both float64 runs and is exact. It is not the difference of two lengths: ‖B − A‖ is not ‖B‖ − ‖A‖. It is never negative, so it says how much changed and not in which direction.</p><p><b>B − A</b> with a sign is a difference between two single numbers, such as two contributions to the answer, like the change in a coefficient. For the contribution to the answer it comes from the pair export (<code>d_head_attr</code>, <code>d_mlp_attr</code>). Other signed changes are computed on this page and shown in italics.</p><p>‖W<sub>B</sub> − W<sub>A</sub>‖ shows where the weights moved.${mlpZero ? " In this pair every MLP weight change is exactly 0, so any MLP change is downstream of changed attention." : ""}</p>`],
    mlp: ["What is an MLP block?", `<p>The MLP block is the part of a layer that transforms what the attention heads read, one word at a time. You can think of it as a small network that re-codes each word's running state.</p><p>After attention, each layer runs a small feed-forward neural network (an MLP, a multilayer perceptron) on every token separately. It has ${n(M.d_ffn)} hidden units, called neurons, per layer. Nothing moves between tokens here. The block height is the size of what it adds, ‖m‖.</p><p>Each neuron multiplies two input signals: a “gate” g̃ (passed through SiLU) and an “up” signal u. <b>Quadrant III</b> neurons are those where both g̃ and u are below −0.05 (counted in <code>q3_count</code>). In the clamped run we switch these neurons off: we set their outputs to zero in every layer and position and run the model again. The purple ticks show what that does to the answer probabilities. ${lm("clamp", "What is the clamped run?")}</p>${ref("m = Σ_i SiLU(g̃_i) u_i W_down[:, i]")}`],
    segments: ["Template text and collapsed parts of the prompt", `<p>Most of the prompt is fixed wrapper text around the question. The workbench folds that text away and keeps the question and the answer options in view.</p><p>Most of the ${D.A.m.tokens.length} tokens are the chat template and fixed instructions. The prompt is split into labelled parts (message markers, instructions, the ${isBank(D.A) ? "scenario" : "question"}, the options, the answer cue, the answer position). The question, the options and the answer position are open by default. A collapsed part draws nothing: it is a gap with a label, never a summary block. A grey pill in the text is one collapsed part.</p><p>${D.A.m.segments ? "The parts come from the export (<code>manifest.segments</code>, contract @1.1): the exporter knows how the prompt was built." : "This is an @1 export without <code>segments</code>, so the prompt is shown as one part."}</p>`],
    "howto-c": ["How to read the Ladder", `<p>The Ladder shows which parts of the model pushed the answer, and by how much. It has the ladder, a line chart and the prompt. The strip at the top gives the answer. Press <b>details</b> there to read it.</p>
      <h4>1 · The ladder (centre)</h4><ul>
      <li><b>What it shows.</b> One cell for each attention head and each MLP block, read at the answer position (t*, where the model is about to write its answer). Each row is one layer, with layer 0 at the bottom. The wide cell at the right of a row is the MLP block. The bottom row (emb) is the embedding term: what the words themselves contribute.</li>
      <li><b>Unit.</b> Contribution to the answer (DLA), in log-odds of “${lp}” over “${lmn}”. Log-odds: ${ODDS_RULE}.</li>
      <li><b>Colour.</b> Blue pushes the answer toward “${lp}”. Orange pushes it toward “${lmn}”. Grey is about zero. The colour deepens with size. The key under the chart gives the largest value.</li>
      <li><b>The switch.</b> <b>A</b> is the base model. <b>B</b> is the model compared with it. <b>Change (B − A)</b> is the default: how much each cell moved. The <span style="color:var(--delta)">gold rings</span> mark the five largest changes on every face. Click a cell to pin it. A drawer then compares A and B for that cell.</li>
      <li><b>Example from this page.</b> On the Change face, all cells plus the embedding term add up to ${sgn(W.dMargin)}, the change in log-odds. The largest cell is ${W.part}: ${sgn(W.partV)}, toward “${esc(short(W.partToward, 40))}”.</li>
      <li><b>Does not show.</b> Why a part moved. A contribution is the direct effect only. A head that changes what a later layer does gets no credit for that path.</li></ul>
      <h4>2 · The line under the ladder</h4><ul><li>It reads “all cells + embedding term = total ✓”. It says that the parts add up to the log-odds of the face shown. This is an accounting check. It is not a test that the answer is right. ${lm("conservation", "see the accounting checks")}</li></ul>
      <h4>3 · Log-odds by layer (right)</h4><ul>
      <li><b>What it shows.</b> The log-odds the model would give if it stopped after this layer and answered. We call this “read off after each layer” (the final rescaling is held fixed). The rows match the ladder.</li>
      <li><b>Unit and position.</b> Log-odds. The zero line is even odds between “${lp}” and “${lmn}”. A line to the right of zero leans toward “${lp}”. A line to the left leans toward “${lmn}”.</li>
      <li><b>Colour.</b> Grey is A. Teal is B. The dot at the top is the last layer.</li>
      <li><b>Read the early layers with care.</b> A reading in the middle layers is rough. Only the last layers are close to the real answer. A line near 0 in the early layers means “no readable preference yet”. It does not mean “neutral”.</li>
      <li><b>Example from this page.</b> After ${W.kmid} of ${W.L} layers, A reads ${W.midA.toFixed(2)} and B reads ${W.midB.toFixed(2)}. After the last layer, the readings are the real log-odds: A ${W.endA.toFixed(2)}, B ${W.endB.toFixed(2)}.</li>
      <li><b>Does not show.</b> The steps inside a layer. It does not show the probability of any answer.</li></ul>
      <h4>4 · The prompt (left)</h4><ul><li>The text that the model reads. The question and the options are open. The fixed template text is folded in one line. Pin or hover a head, and each word is shaded by the attention that the head gives it from t*. The shade is a share of that head's attention (the 16 largest weights are kept). It does not measure how important a word is.</li></ul>
      <h4>5 · The clamped run switch</h4><ul><li>The <b>clamped run</b> button (key C) redraws the tab with the clamped run. Every number is then from that run, and a chip in the top bar says so. ${lm("clamp", "What is the clamped run?")}</li></ul>
      <p>More: ${lm("segments", "template text and the parts of the prompt")} ${lm("dla", "what is a contribution to the answer (DLA)?")} ${lm("resid", "the running state")}</p><p><b>Keys.</b> <code>1 2 3 4</code> tabs · <code>A</code> the full answer card · <code>C</code> clamped run · <code>/</code> find a word in the prompt · <code>Esc</code> unpin · <code>[ ]</code> step the pinned head through its layer · <code>?</code> this help.</p>`],
    "howto-b": ["How to read the Matrix", `<p>The Matrix shows where in the prompt, and in which layers, the internal numbers of the model are large. By default it shows where B changed them most. The strip at the top gives the answer. Press <b>details</b> there to read it.</p>
      <h4>1 · The map</h4><ul>
      <li><b>What it shows.</b> One cell for each layer (rows, layer 0 at the bottom) and each token (columns). The brightness is the size ‖v‖ of a vector at that place (its usual length). The first switch picks the vector: the attention addition ‖a‖, the running state ‖h‖, or the MLP block addition ‖m‖.</li>
      <li><b>The second switch.</b> <b>A</b>, <b>B</b>, or the <b>size of the change ‖B − A‖</b> (default): how far B's vector is from A's. It is exact, never negative, and has its own gold scale.</li>
      <li><b>Colour.</b> Brighter is larger. The scale is linear from 0 and clipped at the 99th percentile. The footer prints the clip value and the maximum. Compare brightness only inside one map.</li>
      <li><b>Position.</b> The white frame is the answer position (t*). Template text (the fixed chat wrapper) is squeezed to 2 px columns. It is never dropped.</li>
      <li><b>Unit.</b> A size in the units of the internal numbers of the model. It has no direction. It is not a probability.</li>
      <li><b>Example from this page.</b> ${W.hasMx ? `The largest ‖B − A‖ of the attention addition is ${fmt(W.mxV, 3)}, in layer ${W.mxL} at token ${W.mxT} (“${esc(W.mxTok)}”).` : "This export has no attention-addition change, so no example is shown."}</li>
      <li><b>Does not show.</b> Which way a change pushes the answer. It shows how much a vector moved. Use the Ladder for the direction.</li></ul>
      <h4>2 · Log-odds by layer (right)</h4><ul>
      <li><b>What it shows.</b> The log-odds the model would give if it stopped after each layer and answered (“read off after each layer”). Grey is A. Teal is B. The dashed line is 0 = even odds. Log-odds: ${ODDS_RULE}.</li>
      <li><b>Read the early layers with care.</b> Mid-layer readings are rough. Only the last layers are close to the real answer. A line near 0 early means “no readable preference yet”, not “neutral”.</li>
      <li><b>Example from this page.</b> After ${W.kmid} of ${W.L} layers, A reads ${W.midA.toFixed(2)} and B reads ${W.midB.toFixed(2)}. After the last layer: A ${W.endA.toFixed(2)}, B ${W.endB.toFixed(2)}.</li></ul>
      <p>Hover a cell for A, B and ‖B − A‖. Click to pin it and open the drawer. ${lm("norm", "the size of a vector")} ${lm("delta", "size of the change ‖B − A‖ vs change B − A")} ${lm("resid", "the running state")}</p><p><b>Keys.</b> <code>1 2 3 4</code> tabs · <code>A</code> the full answer card · <code>Esc</code> unpin · <code>?</code> this help.</p>`],
    "howto-a": ["How to read the 3D object", `<p>The 3D object draws the whole run as blocks: one block for each part of the model, at each token and each layer. It gives the overall shape of where the activity of the model sits. The strip at the top gives the answer. Press <b>details</b> there to read it.</p>
      <h4>1 · The two scenes</h4><ul>
      <li><b>Position.</b> Left to right: the tokens of the prompt (template text is folded into labelled gaps). Front to back: the layers, with layer 0 nearest. Each layer has a thin bar for the running state, ${M.n_heads} slivers for the heads and a block for the MLP block.</li>
      <li><b>Height.</b> The size ‖v‖ of a vector. The scale is logarithmic and shared by A and B. On a log scale, equal steps in height mean equal ratios, so small values stay visible next to large ones.</li>
      <li><b>The Show switch.</b> By default the left scene is <b>A</b> and the right scene is <b>‖B − A‖</b>, the size of the change, on its own gold scale. A and B look almost the same on a log scale, so the change is the useful second scene. You can also see A next to B, or A alone.</li>
      <li><b>Colour.</b> Outside the answer column, colour only names the kind of block. In the answer column (the white frame at t*), blue and orange show the contribution toward “${lp}” or “${lmn}”.</li>
      <li><b>Camera.</b> The buttons move the view: answer position, whole, above, layer stack.</li>
      <li><b>Example from this page.</b> After the last layer, at t*, the size of the running state is ${Number.isFinite(W.rA) ? `${fmt(W.rA, 4)} in A and ${fmt(W.rB, 4)} in B. The size of the change ‖B − A‖ is ${fmt(W.rD, 4)}` : "not stored in this export"}.</li>
      <li><b>Does not show.</b> Exact values (hover a block for them). It shows no direction outside the answer column.</li></ul>
      <h4>2 · The small charts</h4><ul>
      <li><b>Log-odds by layer</b> (between the scenes): the log-odds the model would give if it stopped after each layer and answered (“read off after each layer”). Grey is A. Teal is B. Log-odds: ${ODDS_RULE}. Mid-layer readings are rough, and a line near 0 early means “no readable preference yet”. After ${W.kmid} of ${W.L} layers, A reads ${W.midA.toFixed(2)} and B reads ${W.midB.toFixed(2)}. At the end, A ${W.endA.toFixed(2)} and B ${W.endB.toFixed(2)}.</li>
      <li><b>Prompt map</b> (below): every token (columns) by layer (rows). The brightness is the size of the running state, or of its change. The scale is logarithmic and clipped at the 99th percentile. Click a band to open or fold that part of the prompt.</li></ul>
      <h4>3 · The clamped run</h4><ul><li>The <b>clamped run</b> button redraws the scenes with the Quadrant III neurons switched off. ${lm("clamp", "What is the clamped run?")}</li></ul>
      <p>Hover a block for A, B and the change. Click to pin it and open the drawer. ${lm("scale", "heights and colours")} ${lm("segments", "template text")}</p><p><b>Keys.</b> <code>1 2 3 4</code> tabs · <code>A</code> the full answer card · <code>Esc</code> unpin · <code>?</code> this help.</p>`],
    "howto-k": ["How to read the Cohort view", `<p>The Cohort view compares the base model with every country adapter and sign prompt saved for one survey question. A country adapter carries the six preference signs of a country in the weights. A sign prompt carries the same six signs in words, with the weights unchanged.</p>
      <h4>1 · The rows</h4><ul>
      <li><b>What it shows.</b> Pick a question at the top. Each row compares one adapter or sign prompt with the base model on that question.</li>
      <li><b>Position.</b> The arrow goes from the probability of the base model to the probability of the comparator, for the named answer. The scale is 0% to 100%. The row also gives the most likely answer before and after (written once above a block when every row in it has the same pair). When both sides are above 99.9%, the bars look the same; the log-odds column still shows how far the comparator moved.</li>
      <li><b>The number at the right.</b> The change in log-odds of the named answer over the opposite one. Log-odds: ${ODDS_RULE}. Log-odds compare only those two answers, so they can move differently from the percentage of one answer. On a question with many answers, they can even move against the average answer.</li>
      <li><b>Matched pairs.</b> An adapter and a sign prompt with the same six signs are bracketed together, with one sentence that compares weights with words.</li>
      <li><b>Example from the pair now open.</b> The probability of “${esc(it.j_plus)}” goes from ${pct(D.A.m.readout.probs[it.j_plus])} in the base model to ${pct(D.B.m.readout.probs[it.j_plus])} in B. The log-odds of “${esc(it.j_plus)}” over “${esc(it.j_minus)}” change by ${sgn(D.P.m.d_margin)}.</li></ul>
      <h4>2 · The map (where in the model)</h4><ul>
      <li><b>What it shows.</b> For each layer, how much the contribution of that layer to the answer changes from the base model (pair export <code>d_attn_attr + d_mlp_attr</code>). Hover a square for the number.</li>
      <li><b>Unit and colour.</b> Log-odds. The colour key beside the map gives the scale. Zero is the middle of the key.</li>
      <li>Click a row, or its link, to open that pair in the Ladder.</li></ul>
      <h4>3 · What it does not show</h4><ul>
      <li>Questions with fewer than three comparators are listed but not drawn.</li>
      <li>Every number comes from the saved runs (<code>exports/index.json</code> and the pair exports). None comes from survey respondents.</li>
      <li>A row is one model run on one question. The order of the rows is not a ranking of countries. The adapters were trained on six preference signs, not on the answers to this question.</li></ul>`],
    clamp: ["What is the clamped run?", `<p>The clamped run is a second run of the same model on the same prompt, with one small group of neurons switched off. It tests whether the answer depends on that group.</p>
      <h4>Which neurons?</h4><p>Each neuron in an MLP block has two input signals, a “gate” and an “up” signal. The <b>Quadrant III</b> neurons are those where both signals are below −0.05 (counted in <code>q3_count</code>). The neurons were chosen by this rule. They were not chosen for being large or small.</p>
      <h4>What does the run do?</h4><p>While the model runs, it sets the output of these neurons to zero, in every layer and at every token. Then it measures the answer again. Later layers can still respond to the change. It is like re-estimating a model with a group of terms switched off, except that the other parts adapt.</p>
      <h4>Where do I see it?</h4><ul><li><b>Purple tick</b> on a probability bar: the probability of that answer in the clamped run.</li>
      <li><b>Clamped run</b> button (key C): redraws the tab with the numbers of the clamped run. A chip in the top bar says so.</li>
      <li><b>Clamped checks</b> in the accounting table: the same checks, run on the clamped run.</li></ul>
      <h4>Example from this page</h4><p>The probability of “${esc(it.j_plus)}” is ${pct(D.A.m.readout.probs[it.j_plus])} in the normal run of A and ${pct(D.A.m.readout.probs_clamped[it.j_plus])} in the clamped run of A. For B it is ${pct(D.B.m.readout.probs[it.j_plus])} and ${pct(D.B.m.readout.probs_clamped[it.j_plus])}.</p>
      <h4>Why run it?</h4><p>A large move of the tick shows that the answer changes when this group is switched off. A small move shows that it changes little.</p>
      <h4>What it does not show</h4><p>It does not say why the answer moves, or what these neurons encode. It does not test other groups of neurons. Whether this group matters is a question to test, and this run is the test.</p>`],
    groundTruth: ["Human reference: how to read it", `<p><b>Descriptive display of one survey wave (World Values Survey, wave 7). Not an accuracy test. The adapters were trained on six above/below signs from an independent cross-country preference survey (the Global Preferences Survey), not on these answers.</b></p>
      <h4>What it shows</h4><p>For one country and one question, the share of respondents who chose each answer in the survey, beside the probability that the model gives to the same answer. Both are on a scale from 0% to 100%. Each set adds to about 100% (the survey shares are rounded to whole percent).</p>
      <h4>How to read it</h4><ul>
      <li>A model probability is the weight that the model gives to an answer. A survey share is the share of respondents who chose it. The two are different kinds of number. Read them side by side. Do not call one the error of the other.</li>
      <li>The text reads “In the World Values Survey (wave 7), X% of respondents in the country chose this answer”. The model never says what people say. It gives a probability.</li>
      <li>One marker can appear: closer to, or further from, the survey than the base model, with both gaps shown. For a two-answer question, the gap is between the probability of the named answer and the survey share, in percentage points. For a longer ordered scale, the gap is between the model's expected answer and the survey's mean answer. A question with three answers that are not ordered has no mean, so it uses the share of the named answer. The marker says nothing about which answer is right.</li>
      <li>A country or a question without survey data reads “no survey data”. It never reads 0%. The number of respondents (n) is shown.</li>
      <li><b>Sign-prompt rows have no human reference.</b> A six-sign profile is not a country.</li></ul>
      <h4>What it does not show</h4><p>One survey wave only. It does not test whether an adapter is right. It gives no average across questions or countries. It does not show what any person would answer.</p>`],
    models: ["The two models: A and B", `<p><b>A</b> is the base model: the unchanged model we start from. <b>B</b> is what we compare it with. B is the base plus a country adapter, or the base with a sign prompt (the six signs written into the prompt, with the weights unchanged).</p><p><b>A</b> is ${esc(D.A.m.model.label)} (<code>${esc(D.A.m.model.model_id)}</code>${D.A.m.model.adapter ? " plus an adapter" : ""}). <b>B</b> is ${esc(D.B.m.model.label)} (<code>${esc(D.B.m.model.model_id)}</code>${D.B.m.model.adapter ? " plus a LoRA adapter" : ""}).${D.B.m.model.adapter ? " The adapter is a small add-on to the weights (LoRA). It was trained with direct preference optimization (DPO) on made-up everyday scenarios, preferring the answer that matches that country's direction on the Global Preferences Survey (for example, more trusting or more patient). It was not trained on survey responses." : ""} The prompt, the ${isBank(D.A) ? "scenario" : "question"} and the answer position are the same for both. Only the model differs.${mlpZero ? " In this pair the adapter changed only attention weights." : ""}</p>`],
    answer: [`The model's answer · ${it.item_id}`, readoutHTML(D)],
    terms: ["Glossary: plain words and technical terms", `<dl class="terms">${GLOSSARY.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(fill(v))}</dd>`).join("")}</dl>`],
    resid: ["The running state (residual stream)", `<p>The running state is the model's working memory for each word: a long list of numbers that every layer adds to. It works like a running total in a ledger.</p><p>Each token has a running state: a list of ${n(M.d_model)} numbers that travels up through the layers. Each layer adds to it: state after = state before + attention addition + MLP addition. Nothing is overwritten. Because the parts only add, their contributions can be summed. (In the technical literature this is called the residual stream. This “residual” is not a regression residual. It is a running total.) The bar height is the state's size ‖h<sup>l</sup><sub>t</sub>‖.</p><p>At the answer position, h<sup>l</sup>·w is the log-odds you would get by reading the answer off the state after l layers, with the final rescaling held fixed. It is the line in the charts. Its last point is the log-odds.</p>${ref("Arrays: <code>resid_norm</code>, <code>running_margin</code>.")}`],
    scale: ["Heights and colours", `<p>Sizes are drawn on one shared scale, so you can compare A and B by eye.</p><p>One scale per quantity, shared by A and B, so equal height means equal value. The scale is logarithmic with the median as its knee, so small values stay visible next to large ones. Heatmap colours are clipped at the 99th percentile so one extreme token does not wash out the rest; each colour key prints the clip value. The change maps have their own scale (gold). Outside the answer column, colours only name the kind of block. Inside it, blue and orange show the direction of the contribution.</p>`],
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
  // The answer card is a pop-over anchored under the answer strip (SYSTEM §3); every other topic is a centred modal.
  const strip = key === "answer" ? document.getElementById("answer") : null;
  dlg.classList.toggle("pop", !!strip);
  if (strip) { const r = strip.getBoundingClientRect(); dlg.style.margin = "0"; dlg.style.left = `${Math.round(r.left)}px`; dlg.style.top = `${Math.round(r.bottom + 6)}px`; }
  else { dlg.style.margin = ""; dlg.style.left = ""; dlg.style.top = ""; }
  // A pop-over under a tall answer strip must still fit the window: its body scrolls inside.
  const lb = dlg.querySelector<HTMLElement>(".lm-b");
  if (lb) lb.style.maxHeight = strip ? `${Math.max(240, innerHeight - Math.round(strip.getBoundingClientRect().bottom) - 90)}px` : "";
  if (!dlg.open) dlg.showModal();
}

// ------------------------------------------------------------------ v3: the answer strip (SYSTEM §3), shared by every workbench tab
/** The headline, two margin bars (each value inside its own group), P(j₊) A → B, and the full card on demand (key A).
 * Two answers: one sentence, unchanged. More than two: the expected answer first (an ordered item), or the most
 * likely answer (any other item), then the end-answer log-odds that the charts split (WB7-W). */
export function answerStrip(D: Bundle, clamp = false): string {
  const it = D.A.m.item, jp = `“${it.j_plus}” (${short(labelPlus(D.A), 30)})`, jm = `“${it.j_minus}” (${short(labelMinus(D.A), 30)})`;
  const a = clamp ? D.A.m.readout.margin_clamped : D.A.m.readout.margin, b = clamp ? D.B.m.readout.margin_clamped : D.B.m.readout.margin;
  const dd = dAttr(D, clamp), d = dd.margin;
  const prA = clamp ? D.A.m.readout.probs_clamped : D.A.m.readout.probs, prB = clamp ? D.B.m.readout.probs_clamped : D.B.m.readout.probs;
  const pA = prA[it.j_plus], pB = prB[it.j_plus];
  const mx = Math.max(Math.abs(a), Math.abs(b)) || 1, neg = a < 0 || b < 0;
  const bar = (v: number, col: string) => { const w = 72 * Math.abs(v) / mx; const left = neg ? 72 + (v < 0 ? -w : 0) : 0;
    return `<span class="trk2${neg ? " two" : ""}"><i style="left:${left.toFixed(1)}px;width:${w.toFixed(1)}px;background:${col}"></i>${neg ? `<b style="left:72px"></b>` : ""}</span>`; };
  const dsrc = dd.marginExported ? `from the pair export (${clamp ? "d_margin_clamped" : "d_margin"})` : "computed in this browser from A and B";
  const n = it.codes.length, many = n > 2, ord = isOrdered(it);
  const pTip = `Probability of answer “${it.j_plus}”, A → B.\nP is over all ${n} codes; the log-odds compares only “${it.j_plus}” with “${it.j_minus}”, so P is not sigmoid(log-odds).`;
  const archiveA = D.A.m.archive_parity, archiveB = D.B.m.archive_parity;
  const hasUlp = archiveA?.max_fp16_ulp != null && archiveB?.max_fp16_ulp != null;
  const parityText = hasUlp ? ` · archive check ${fmt(Math.max(archiveA!.max_fp16_ulp!, archiveB!.max_fp16_ulp!), 2)} ulp (≤4; report only)` : archiveA && archiveB ? ` · legacy archive check, probability gap ${fmt(Math.max(archiveA.max_abs_prob_gap, archiveB.max_abs_prob_gap), 2)} (descriptive only)` : "";
  // On screen, the archive check in plain words; the weights format, the ulp gap and the limit stay in the tooltip.
  const ulpMax = hasUlp ? Math.max(archiveA!.max_fp16_ulp!, archiveB!.max_fp16_ulp!) : null;
  const parityPlain = ulpMax == null ? (archiveA && archiveB ? "compared with the archived Paper B run (details on hover)" : "")
    : ulpMax <= 4 ? "✓ matches the archived Paper B run" : "differs from the archived Paper B run (report only)";
  const parityTip = hasUlp ? `Archive check (A2 F5): this capture against the archived Paper B score, using the log-probability of each full answer. The gap is in ulps (units in the last place: the smallest step of the number format the archive used, fp16). The limit is ≤4 ulp, and it is report only: it does not fail the page. Probability gaps are descriptive only.\nA: ${Object.entries(archiveA!.options ?? {}).map(([c, v]) => `${c}: |Δlogp|=${v.abs_logprob_gap_nats} nats, ${v.fp16_ulp} ulp`).join("; ")}\nB: ${Object.entries(archiveB!.options ?? {}).map(([c, v]) => `${c}: |Δlogp|=${v.abs_logprob_gap_nats} nats, ${v.fp16_ulp} ulp`).join("; ")}` : "Legacy probability-gap metadata; no ulp result was exported.";
  const clampTag = clamp ? ` <span class="clampw">clamped run</span> ${lm("clamp", "What is the clamped run?")}` : "";
  const numd = `<span class="num ${dd.marginExported ? "" : "calc"}">${sgn(d, 3)}</span>`;
  let say: string;
  if (!many) {
    say = `<span class="say" title="Log-odds of “${esc(it.j_plus)}” over “${esc(it.j_minus)}” (the margin) = log[P(“${esc(it.j_plus)}”) / P(“${esc(it.j_minus)}”)]. Change from the base: ${dsrc}.&#10;P is over all ${n} codes; the log-odds compares only “${esc(it.j_plus)}” with “${esc(it.j_minus)}”.">B leans further toward <b>${esc(d >= 0 ? jp : jm)}</b> than A: change in log-odds ${numd}${clampTag}</span>`;
  } else {
    const ma = modalAnswer(it, prA), mb = modalAnswer(it, prB);
    const modalLine = (lead: string) => `${lead}A ${esc(named(ma.code, ma.label))} (${pct(ma.p)}) → B ${esc(named(mb.code, mb.label))} (${pct(mb.p)})`;
    const endsWord = ord ? "the two end answers" : "the first and last answer codes";
    const lowEnds = [prA, prB].some((p) => p[it.j_plus] < 0.01 && p[it.j_minus] < 0.01);
    let head: string, subs = "";
    if (ord) {
      const e = scaleEnds(it), eA = expectedAnswer(it, prA), eB = expectedAnswer(it, prB), dE = eB - eA;
      const dir = /^\d+$/.test(e.hiLab) ? "higher = a higher answer code" : `higher = closer to “${esc(short(e.hiLab, 40))}”`;
      head = `<span class="say" title="Expected answer = the sum of (answer code × its probability) over all ${n} codes. A: ${eA.toFixed(3)}. B: ${eB.toFixed(3)}. Paper B scores items as this expected answer.">Average answer on the ${esc(e.lo)}–${esc(e.hi)} scale: A <b>${eA.toFixed(1)}</b> → B <b>${eB.toFixed(1)}</b> <span class="say-dir">(${dir})</span>${clampTag}</span>`;
      subs += `<span class="say-sub">${modalLine("Most likely answer: ")}</span>`;
      const mv = Number(mb.code) - Number(ma.code);
      if (dE * d > 1e-3 || mv * d > 0) {
        subs += `<span class="say-sub say-warn">The two numbers move in opposite directions. Average answer: ${dE >= 0 ? `up, toward “${esc(e.hi)}”` : `down, toward “${esc(e.lo)}”`}. Log-odds of the end answers: toward “${esc(d >= 0 ? it.j_plus : it.j_minus)}”. The average uses every answer. The log-odds use only “${esc(it.j_plus)}” and “${esc(it.j_minus)}”.</span>`;
      }
    } else {
      head = `<span class="say" title="Most likely answer = the answer code with the highest probability. All ${n} probabilities are in details.">${modalLine("Most likely answer: ")}${clampTag}</span>`;
    }
    subs += `<span class="say-sub" title="Log-odds of “${esc(it.j_plus)}” over “${esc(it.j_minus)}” (the margin) = log[P(“${esc(it.j_plus)}”) / P(“${esc(it.j_minus)}”)]. Change from the base: ${dsrc}.">The charts below split the log-odds of “${esc(it.j_plus)}” over “${esc(it.j_minus)}” (${endsWord}): A <span class="num">${a.toFixed(2)}</span> → B <span class="num">${b.toFixed(2)}</span>, change ${numd}</span>`;
    if (lowEnds) subs += `<span class="say-sub say-warn">${ord ? "Both end answers are below 1% here, so this number can move against the average answer." : "Both of these answers are below 1% here, so this number can move against the most likely answer."}</span>`;
    say = `<span class="sayw">${head}${subs}</span>`;
  }
  return `${say}
    <span class="minis"><span class="mini" title="A's log-odds (margin)${many ? ` of “${esc(it.j_plus)}” over “${esc(it.j_minus)}”` : ""}, ${esc(D.A.m.model.label)}"><span style="color:${A_COL}">A</span>${bar(a, A_COL)}<span class="num">${a.toFixed(2)}</span></span>
    <span class="mini" title="B's log-odds (margin)${many ? ` of “${esc(it.j_plus)}” over “${esc(it.j_minus)}”` : ""}, ${esc(D.B.m.model.label)}"><span style="color:${B_COL}">B</span>${bar(b, B_COL)}<span class="num">${b.toFixed(2)}</span></span>
    <span class="mini" title="${esc(pTip)}">P(“${esc(it.j_plus)}”) <span class="num">${pA.toFixed(2)} → ${pB.toFixed(2)}</span></span></span>
    ${D.A.m.weights ? `<span class="mini" title="${esc(`Weights: ${D.A.m.weights}${parityText}.\n${parityTip}`)}">${esc(parityPlain)}</span>` : ""}
    <span class="sp"></span><button class="details" data-learn="answer" title="How to read the numbers on this page: the answer codes, their probabilities, the expected answer and the clamped run (key A)">details</button>`;
}

/** The pin drawer's chrome (same component on the ladder, the matrix and the object). */
export function drawerHTML(title: string, sub: string, body: string, failing: Check[]): string {
  const taint = failing.length ? `<div class="badp">✗ An accounting check failed (${esc(failing.map(checkLine).join(" · "))}): these numbers do not add up.</div>` : "";
  return `<div class="dr-h"><i class="pinbox" title="The pinned mark has this thick white outline"></i><h3>${esc(title)}</h3><span class="sp"></span><button id="unpin" title="Unpin (Esc)">Esc ✕</button></div>
    <div class="muted dr-sub">${sub}</div>${taint}${body}`;
}
