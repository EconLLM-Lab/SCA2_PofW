// Shared by the landing page and the three workbench tabs (ladder, matrix, 3D object).
// Data access is in data.ts. Nothing here computes a model quantity, except where a function
// says so in its name and comment (a browser B − A fallback for @1 files, segment sums).
// Copy follows design/layout-v2/COPY.md (string IDs in comments) and its PM rulings.

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
      rows.push({ label: `Push (DLA)${cl}`, tip: `Push on the margin (DLA). How far this head's write moves the margin, read straight through the model's last steps.\n${clamp ? "head_attr_clamped" : "head_attr"}`, a: ha.get(s.l, s.h), b: hb.get(s.l, s.h), d: dla(dd.head(s.l, s.h)) }); }
    if (a.attn_topk_mass && b.attn_topk_mass) rows.push({ label: "Top-16 coverage", tip: "Attention covered by the top 16. Share of this head's attention that the 16 largest weights cover (1 = all of it).\nattn_topk_mass", a: a.attn_topk_mass.get(s.l, s.h, s.t), b: b.attn_topk_mass.get(s.l, s.h, s.t), d: calc(a.attn_topk_mass.get(s.l, s.h, s.t), b.attn_topk_mass.get(s.l, s.h, s.t)) });
  } else if (s.kind === "mlp") {
    rows.push({ label: "Write size ‖m‖", tip: "Length of the vector this MLP adds to the running state.\nmlp_norm · d_mlp_norm", a: a.mlp_norm.get(s.l, s.t), b: b.mlp_norm.get(s.l, s.t), d: { v: p.d_mlp_norm.get(s.l, s.t), how: "len", src: "‖m_B − m_A‖, d_mlp_norm" } });
    rows.push({ label: "Quadrant III (count)", tip: "Quadrant III neurons (count). Neurons whose two input signals are both below −0.05 at this token.\nq3_count", a: a.q3_count.get(s.l, s.t), b: b.q3_count.get(s.l, s.t), d: calc(a.q3_count.get(s.l, s.t), b.q3_count.get(s.l, s.t)), int: true });
    if (s.t === ro) { const ma = clamp ? a.mlp_attr_clamped : a.mlp_attr, mb = clamp ? b.mlp_attr_clamped : b.mlp_attr;
      rows.push({ label: `Push (DLA)${cl}`, tip: `Push on the margin (DLA). How far this MLP's write moves the margin.\n${clamp ? "mlp_attr_clamped" : "mlp_attr"}`, a: ma.get(s.l), b: mb.get(s.l), d: dla(dd.mlp(s.l)) }); }
  } else {
    rows.push({ label: "State size ‖h‖", tip: "Length of the running state.\nresid_norm · d_resid_norm", a: a.resid_norm.get(s.l, s.t), b: b.resid_norm.get(s.l, s.t), d: { v: p.d_resid_norm.get(s.l, s.t), how: "len", src: "‖h_B − h_A‖, d_resid_norm" } });
    if (s.t === ro) { const ra = clamp ? a.running_margin_clamped : a.running_margin, rb = clamp ? b.running_margin_clamped : b.running_margin;
      rows.push({ label: `Margin if read off here${cl}`, tip: "The margin you would get by reading the answer off the state at this layer, with the final layer's rescaling held fixed.\nrunning_margin", a: ra.get(s.l), b: rb.get(s.l), d: calc(ra.get(s.l), rb.get(s.l)) }); }
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
    if (!(D.A.t.attn_topk_idx && D.B.t.attn_topk_idx)) html += `<div class="sub">Where this head looks: the attention weights are still loading; this panel fills in when they arrive.</div>`;
    else html += `<div class="sub">Where this head looks${s.t === ro ? " from the answer position" : " from this token"}: its largest attention weights (weight · token number)</div><div class="two"><div><i>A</i>${col(ka)}</div><div><i>B</i>${col(kb)}</div></div>`;
    const dw = D.P.t.d_weight_head;
    html += `<div class="sub" title="Frobenius norm: the square root of the sum of squared differences. 0 means untouched. k and v are shared by 3 heads.">How far this head's weights moved, B vs A (q, k, v, o): <span class="num">${[0, 1, 2, 3].map((j) => fmt(dw.get(s.l, s.h, j), 2)).join(", ")}</span></div>`;
  }
  if (s.kind === "mlp") {
    const dw = D.P.t.d_weight_mlp;
    html += `<div class="sub">How far this MLP's weights moved, B vs A (gate, up, down): <span class="num">${[0, 1, 2].map((j) => fmt(dw.get(s.l, j), 2)).join(", ")}</span> ${dw.get(s.l, 0) === 0 && dw.get(s.l, 1) === 0 && dw.get(s.l, 2) === 0 ? "(0: this adapter changed no MLP weights)" : ""}</div>`;
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

// ------------------------------------------------------------------ the answer card (S01–S08)
export function readoutHTML(D: Bundle): string {
  const it = D.A.m.item, codes = it.codes, lp = labelPlus(D.A), lmn = labelMinus(D.A);
  const bars = (r: Run, col: string) => codes.map((c) => {
    const p = r.m.readout.probs[c], pc = r.m.readout.probs_clamped[c];
    return `<div class="pr"><span>${esc(c)}</span><div class="trk"><div style="width:${(p * 100).toFixed(1)}%;background:${col}"></div><i style="left:${(pc * 100).toFixed(1)}%" title="clamped run: ${pc.toFixed(3)}"></i></div><span class="num">${p.toFixed(3)}</span></div>`;
  }).join("");
  const ok = checksOf(D).every((c) => c.ok);
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

// ------------------------------------------------------------------ the checks table of "learn more" (P04)
/** Row labels for the gate keys of either generation of manifest (`conservation.relative.checks` of
 * `gates.py`, and the absolute set it replaced). An unknown key falls back to its own name, so a
 * gate added later still shows up here. */
const CHECK_LABEL: Record<string, string> = {
  residual_closure: "The parts add up to the final state (largest gap in any coordinate, any token)",
  head_closure: "The heads add up to the attention write (largest gap in any coordinate, any token)",
  readout: "The parts add up to the margin (DLA gap)",
  logits_reference: "Our code vs the Hugging Face reference (largest relative gap)",
  residual_closure_inf: "The parts add up to the final state (largest gap in any coordinate, any token)",
  head_closure_inf: "The heads add up to the attention write (largest gap in any coordinate, any token)",
  dla_gap: "The parts add up to the margin (absolute gap)",
  hf64_logits_max_rel_gap: "Our code vs the Hugging Face reference, with its float32 rounding steps switched off (relative gap)",
  gap_f64: "B − A of the parts adds up to B − A of the margin (float64 differences)",
  gap_f32: "B − A of the parts adds up to B − A of the margin (summed from the stored float32 arrays)",
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
  return `<table class="lt"><tr><th>Check</th><th>rel ≤ τ</th><th>A</th><th>B</th></tr>
      ${main.map((k) => row(k, ra.checks[k], rb.checks[k])).join("\n      ")}
      <tr><td>Recomputed in this browser from the float32 arrays drawn: |margin − ΣDLA|</td><td class="num">${notGated ? "not gated here" : "1e-2"}</td><td class="num">${fmt(D.A.clientCheck.dlaGap, 2)}</td><td class="num">${fmt(D.B.clientCheck.dlaGap, 2)}</td></tr>
      ${pairRow}</table>
      <details><summary>show the clamped run and the information-only rows</summary><table class="lt">
      ${clamped.map((k) => row(k, ra.checks[k], rb.checks[k])).join("\n      ")}
      <tr><td>Our code vs the reference as shipped (relative gap). Information only.</td><td class="num">none</td><td class="num">${fmt(cA.hf_logits_max_rel_gap, 2)}</td><td class="num">${fmt(cB.hf_logits_max_rel_gap, 2)}</td></tr>
      <tr><td>Eq. 6 vs the full-answer calculation (absolute gap). A test checks this; each export also records the gap.</td><td class="num">none</td><td class="num">${fmt(cA.eq6_teacher_forced_max_abs_gap, 2)}</td><td class="num">${fmt(cB.eq6_teacher_forced_max_abs_gap, 2)}</td></tr>
      </table></details>
      <p>Every row of the first table is <b>relative</b>: <code>rel</code> is the error divided by the size of the quantity the error is an error of (each row's tooltip names that scale), and the row passes when <code>rel ≤ τ</code>. A τ is ${ra.tau_multiple}× the largest round-off measured for that check on this model family, rounded up to the next power of ten (<code>plans/stage1_f32_gaps.md</code>), so the gate does not fire on round-off and still catches a real break.</p>
      <p>${dtype !== "float32" && notGated
        ? `This export was computed in <b>${esc(dtype)}</b> (<code>provenance.compute_dtype</code>). Its manifest marks the absolute bounds of the contract as not applicable to this capture (<code>legacy_absolute_applicable: false</code>), so the verdict is the relative table above; the browser re-sum is still shown with its number.`
        : notGated
        ? "This export was computed in <b>float32</b> (<code>provenance.compute_dtype</code>). The absolute bounds of the contract cannot be met at that dtype: the residual gate 1e-3 is about nine float32 ulps wide at a state whose largest entry is 8.9e2, so it fires on round-off rather than on a break in the capture. Those rows are still shown where they exist, and the browser re-sum is shown with its number, but the verdict is this relative table."
        : "This export was computed in <b>float64</b> (<code>provenance.compute_dtype</code>); the relative gates still carry the verdict, with more headroom than the absolute set had."}</p>`;
}

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
    conservation: ["Do the parts add up? The checks", `${checksOf(D).filter((c) => !c.ok).map((c) => `<p class="badp">✗ ${esc(checkLine(c))}</p>`).join("")}<p>Three questions. Do the parts add up to the final state? Do they add up to the margin? Does our code give the same numbers as the reference implementation? All three have to pass, for both models.</p>
      ${cA.relative && cB.relative ? relativeTable(D, cA, cB) : `<table class="lt"><tr><th>Check</th><th>Must be below</th><th>A</th><th>B</th></tr>
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
      <p>Each run uses float64 arithmetic. If the parts failed to add up to the whole, the status line next to the answer would turn red, and the figures should not be read as measurements until the export is fixed.</p>`}`],
    delta: ["What the fine-tune changed: ‖B − A‖ and B − A", `<p>For the same prompt, token and layer, the pair export stores <b>‖B − A‖</b>: the length of the difference between B's vector and A's vector. It is computed from both float64 runs and is exact. It is not the difference of two lengths: ‖B − A‖ is not ‖B‖ − ‖A‖. It is never negative, so it says how much changed and not in which direction.</p><p><b>B − A</b> with a sign is a difference between two single numbers, such as two DLA values, like the change in a coefficient. For the push on the margin it comes from the pair export (<code>d_head_attr</code>, <code>d_mlp_attr</code>); other signed changes are computed on this page and shown in italics.</p><p>‖W<sub>B</sub> − W<sub>A</sub>‖ shows where the weights moved.${mlpZero ? " In this pair every MLP weight change is exactly 0, so any MLP change is downstream of changed attention." : ""}</p>`],
    mlp: ["What is an MLP block?", `<p>After attention, each layer runs a small feed-forward network (an MLP) on every token separately. It has 1,536 hidden units, called neurons, per layer. Nothing moves between tokens here. The block height is the size of what it adds, ‖m‖.</p><p>Each neuron multiplies two input signals: a “gate” g̃ (passed through SiLU) and an “up” signal u. <b>Quadrant III</b> neurons are those where both g̃ and u are below −0.05 (counted in <code>q3_count</code>). In the clamped run we set these neurons' outputs to zero in every layer and position and run the model again. The purple ticks show what that does to the answer probabilities.</p>${ref("m = Σ_i SiLU(g̃_i) u_i W_down[:, i]")}`],
    segments: ["Template text and collapsed parts of the prompt", `<p>Most of the ${D.A.m.tokens.length} tokens are the chat template and fixed instructions. The prompt is split into labelled parts (message markers, instructions, the ${isBank(D.A) ? "scenario" : "question"}, the options, the answer cue, the answer position). The question, the options and the answer position are open by default. A collapsed part draws nothing: it is a gap with a label, never a summary block. A grey pill in the text is one collapsed part.</p><p>${D.A.m.segments ? "The parts come from the export (<code>manifest.segments</code>, contract @1.1): the exporter knows how the prompt was built." : "This is an @1 export without <code>segments</code>, so the prompt is shown as one part."}</p>`],
    clamp: ["Quadrant III and the clamped run", `<p>A neuron here has two input signals, a gate and an up signal. Quadrant III neurons have both below −0.05. The clamped run sets their outputs to zero in every layer and at every position, while the model runs, and records the new answer probabilities (the purple ticks). It is like re-estimating with a group of terms switched off, except that later layers respond to the change. The neurons were not chosen for being large or small. Whether this group matters for the answer is a hypothesis to test, not something this page shows.</p>`],
    models: ["The two models: A and B", `<p><b>A</b> is ${esc(D.A.m.model.label)} (<code>${esc(D.A.m.model.model_id)}</code>${D.A.m.model.adapter ? " plus an adapter" : ""}). <b>B</b> is ${esc(D.B.m.model.label)} (<code>${esc(D.B.m.model.model_id)}</code>${D.B.m.model.adapter ? " plus a LoRA adapter" : ""}).${D.B.m.model.adapter ? " The adapter was trained with DPO on made-up everyday scenarios, preferring the answer that matches the USA's direction on the Global Preferences Survey (e.g. more trusting, more patient). It was not trained on survey responses." : ""} The prompt, the ${isBank(D.A) ? "scenario" : "question"} and the answer position are the same for both. Only the model differs.${mlpZero ? " In this pair the adapter changed only attention weights." : ""}</p>`],
    answer: [`The model's answer · ${it.item_id}`, readoutHTML(D)],
    "howto-c": ["How to read the ladder", `<p>Each cell is one part of the model, read at the answer position t* (the last position of the prompt, where the model is about to write its answer): nine attention heads, then the MLP, for each of the ${D.A.m.model.n_layers} layers, with layer 0 at the bottom. Its colour is that part's push on the margin (DLA): blue toward “${lp}”, orange toward “${lmn}”. The cells plus the embedding term add up to the margin; the line under the ladder re-sums the face shown.</p><p>The switch shows one face at a time: <b>A</b>, <b>B</b>, or <b>B − A</b> (the default: how the fine-tune changed each push). The <span style="color:var(--delta)">gold rings</span> mark the five largest changes, B − A, on every face. Click a cell to pin it: a thick white outline marks it, the drawer on the right compares A and B for it, and the prompt shades by where that head looks.</p><p>The chart on the right is the margin you would read off the running state after each layer (log-odds, final rescaling held fixed), for A and B.</p><p>More: ${lm("segments", "template text and the parts of the prompt")} ${lm("dla", "what is a push (DLA)?")} ${lm("resid", "the running state")}</p><p><b>Keys.</b> <code>1 2 3 4</code> tabs · <code>A</code> the full answer card · <code>C</code> clamped run · <code>/</code> find a word in the prompt · <code>Esc</code> unpin · <code>[ ]</code> step the pinned head through its layer · <code>?</code> this help.</p>`],
    "howto-b": ["How to read the matrix", `<p>One map, one face at a time. Each cell is one layer (rows, layer 0 at the bottom) at one token (columns). Its brightness is the size of a vector there: by default the <b>attention write</b> ‖a‖ of that layer (<code>attn_norm</code>), or the running state ‖h‖ or the MLP write ‖m‖. Brighter means larger. It shows where activity is large, not which way it pushes the answer.</p><p>The switch shows <b>A</b>, <b>B</b>, or <b>‖B − A‖</b> (the default: how far B's vector is from A's, exact, from the pair export; never negative, its own gold scale). Colour is linear and clipped at the 99th percentile; the footer prints the clip value and the maximum. Template text is squeezed to 2 px columns, never dropped. The white frame is the answer position t*.</p><p>The column on the right is the margin you would read off the running state after each layer, for A and B, on the map's rows. Hover a cell for A, B and ‖B − A‖; click to pin it and open the drawer. ${lm("norm", "the size of a vector")} ${lm("delta", "‖B − A‖ vs B − A")} ${lm("resid", "the running state")}</p><p><b>Keys.</b> <code>1 2 3 4</code> tabs · <code>A</code> the full answer card · <code>Esc</code> unpin · <code>?</code> this help.</p>`],
    "howto-a": ["How to read the 3D object", `<p>The whole run as blocks. Left to right: the tokens of the prompt (template text is collapsed into labelled gaps). Front to back: the layers, layer 0 nearest. Height: the size of a vector, on a log scale shared by A and B. Each layer has a thin bar for the running state, nine slivers for the heads and a block for the MLP.</p><p>By default the left scene is <b>A</b> and the right scene is <b>‖B − A‖</b>, the change, on its own gold scale. Under log heights A and B look almost the same, so the change is the useful second scene; the switch also offers A next to B, or A alone. The <b>t*</b> column (white frame, lit floor) is the answer position; only there do blue and orange mean a push toward an answer.</p><p>The small chart between the scenes is the margin, read off after each layer, for A and B. The prompt map below shows every token; click a band to open or collapse that part. Hover a block for A, B and the change; click to pin it and open the drawer. ${lm("scale", "heights and colours")} ${lm("segments", "template text")}</p><p><b>Keys.</b> <code>1 2 3 4</code> tabs · <code>A</code> the full answer card · <code>Esc</code> unpin · <code>?</code> this help.</p>`],
    "howto-k": ["Cohort · one base vs many adapters", `<p>This view will put one base model against N adapters on the same item: one row per adapter, its change in push on the margin by layer (adapter − base, <code>d_attn_attr + d_mlp_attr</code>), rows sorted by <code>d_margin</code>. Clicking a row will open that adapter as B in the ladder.</p><p>It needs one pair export per (base, adapter) on the same item, each with <code>d_attn_attr</code> and <code>d_mlp_attr</code> (capture@1.1), for at least three adapters. Until those exports exist the tab shows no data. The thumbnail is an illustration from the design mockup and is badged as such.</p>`],
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
  // The answer card is a pop-over anchored under the answer strip (SYSTEM §3); every other topic is a centred modal.
  const strip = key === "answer" ? document.getElementById("answer") : null;
  dlg.classList.toggle("pop", !!strip);
  if (strip) { const r = strip.getBoundingClientRect(); dlg.style.margin = "0"; dlg.style.left = `${Math.round(r.left)}px`; dlg.style.top = `${Math.round(r.bottom + 6)}px`; }
  else { dlg.style.margin = ""; dlg.style.left = ""; dlg.style.top = ""; }
  if (!dlg.open) dlg.showModal();
}

// ------------------------------------------------------------------ v3: the answer strip (SYSTEM §3), shared by every workbench tab
/** One sentence, two margin bars (each value inside its own group), P(j₊) A → B, and the full card on demand (key A). */
export function answerStrip(D: Bundle, clamp = false): string {
  const it = D.A.m.item, jp = `“${it.j_plus}” (${short(labelPlus(D.A), 30)})`, jm = `“${it.j_minus}” (${short(labelMinus(D.A), 30)})`;
  const a = clamp ? D.A.m.readout.margin_clamped : D.A.m.readout.margin, b = clamp ? D.B.m.readout.margin_clamped : D.B.m.readout.margin;
  const dd = dAttr(D, clamp), d = dd.margin;
  const pA = (clamp ? D.A.m.readout.probs_clamped : D.A.m.readout.probs)[it.j_plus], pB = (clamp ? D.B.m.readout.probs_clamped : D.B.m.readout.probs)[it.j_plus];
  const mx = Math.max(Math.abs(a), Math.abs(b)) || 1, neg = a < 0 || b < 0;
  const bar = (v: number, col: string) => { const w = 72 * Math.abs(v) / mx; const left = neg ? 72 + (v < 0 ? -w : 0) : 0;
    return `<span class="trk2${neg ? " two" : ""}"><i style="left:${left.toFixed(1)}px;width:${w.toFixed(1)}px;background:${col}"></i>${neg ? `<b style="left:72px"></b>` : ""}</span>`; };
  const dsrc = dd.marginExported ? `pair export (${clamp ? "d_margin_clamped" : "d_margin"})` : "computed in this browser from A and B";
  const n = it.codes.length;
  const pTip = `Probability of answer “${it.j_plus}”, A → B.\nP is over all ${n} codes; the margin compares only “${it.j_plus}” vs “${it.j_minus}”, so P is not sigmoid(margin).`;
  const archiveA = D.A.m.archive_parity, archiveB = D.B.m.archive_parity;
  const hasUlp = archiveA?.max_fp16_ulp != null && archiveB?.max_fp16_ulp != null;
  const parityText = hasUlp ? ` · archive ${fmt(Math.max(archiveA!.max_fp16_ulp!, archiveB!.max_fp16_ulp!), 2)} ulp (≤4; report-only)` : archiveA && archiveB ? ` · legacy archive Δp ${fmt(Math.max(archiveA.max_abs_prob_gap, archiveB.max_abs_prob_gap), 2)} (descriptive only)` : "";
  const parityTip = hasUlp ? `Archive parity per A2 F5: full completion logprobs, ≤4 archived-fp16 ulp, report-only. Probability gaps are descriptive only.\nA: ${Object.entries(archiveA!.options ?? {}).map(([c, v]) => `${c}: |Δlogp|=${v.abs_logprob_gap_nats} nats, ${v.fp16_ulp} ulp`).join("; ")}\nB: ${Object.entries(archiveB!.options ?? {}).map(([c, v]) => `${c}: |Δlogp|=${v.abs_logprob_gap_nats} nats, ${v.fp16_ulp} ulp`).join("; ")}` : "Legacy probability-gap metadata; no ulp result was exported.";
  return `<span class="say" title="Margin = log-odds of “${esc(it.j_plus)}” vs “${esc(it.j_minus)}” = log[P(“${esc(it.j_plus)}”) / P(“${esc(it.j_minus)}”)]. Change ${dsrc}.&#10;P is over all ${n} codes; the margin compares only “${esc(it.j_plus)}” vs “${esc(it.j_minus)}”.">B leans further toward <b>${esc(d >= 0 ? jp : jm)}</b> than A: margin <span class="num ${dd.marginExported ? "" : "calc"}">${sgn(d, 3)}</span> log-odds${clamp ? ` <span class="clampw">clamped run</span>` : ""}</span>
    <span class="minis"><span class="mini" title="A's margin (log-odds), ${esc(D.A.m.model.label)}"><span style="color:${A_COL}">A</span>${bar(a, A_COL)}<span class="num">${a.toFixed(2)}</span></span>
    <span class="mini" title="B's margin (log-odds), ${esc(D.B.m.model.label)}"><span style="color:${B_COL}">B</span>${bar(b, B_COL)}<span class="num">${b.toFixed(2)}</span></span>
    <span class="mini" title="${esc(pTip)}">P(“${esc(it.j_plus)}”) <span class="num">${pA.toFixed(2)} → ${pB.toFixed(2)}</span></span></span>
    ${D.A.m.weights ? `<span class="mini" title="${esc(parityTip)}">${esc(D.A.m.weights)}${esc(parityText)}</span>` : ""}
    <span class="sp"></span><button class="details" data-learn="answer" title="The full answer card: codes, four probabilities, the clamped run (key A)">details</button>`;
}

/** The pin drawer's chrome (same component on the ladder, the matrix and the object). */
export function drawerHTML(title: string, sub: string, body: string, failing: Check[]): string {
  const taint = failing.length ? `<div class="badp">✗ A check failed (${esc(failing.map(checkLine).join(" · "))}): these numbers are not conserved.</div>` : "";
  return `<div class="dr-h"><i class="pinbox" title="The pinned mark has this thick white outline"></i><h3>${esc(title)}</h3><span class="sp"></span><button id="unpin" title="Unpin (Esc)">Esc ✕</button></div>
    <div class="muted dr-sub">${sub}</div>${taint}${body}`;
}
