// Cohort tab, the data side. Nothing here draws. It turns index.json (runs, pairs) plus one small run manifest
// per question into rows, and arranges them for the filters. Every number comes from the exports or the index:
//   probability of an answer   index.runs[].probs         (the model's answer probabilities on that question)
//   change in log-odds         index.pairs[].d_margin     (comparator − base, on log-odds of j_plus over j_minus)
// Computed here, and only ever from those two: the largest-probability answer, a percentage string, a sentence.
// Wording that is not data (short question names, country names) is an editorial table below, with a fallback
// to the exported text, so a new question still draws.

import type { IndexFile, Run } from "./data";
import { questionText } from "./common";

export type Kind = "adapter" | "prompt" | "other";
export interface Who { b: string; kind: Kind; name: string; cc?: string; bits?: string }
export interface IndexRun { file: string; model: string; item_id: string; probs?: Record<string, number>; margin?: number }
export interface ItemInfo { item_id: string; j_plus: string; j_minus: string; codes: string[]; labels: string[]; text: string }
export interface Top { code: string; p: number; text: string; code2?: string; text2?: string }   // text: the percentage, with extra decimals only when the runner-up would round to the same figure
export interface Row {
  who: Who; d: number; file: string;
  pBase?: number; pCmp?: number;                       // probability of j_plus, base and comparator
  topBase?: Top; topCmp?: Top;
  bits?: string;                                       // the six signs this comparator carries, "101111"
  cohortOnly?: boolean;                                // the public sample ships only this comparator's probabilities (no Ladder, Matrix, 3D)
}
// A block is what is drawn together. In the matched-pairs order it is one six-sign profile; in the size order, one row.
//   section "pair"       the profile has a sign prompt and a country adapter on this question
//   section "no-prompt"  adapters whose six signs no sign prompt on this question carries
//   section "no-adapter" sign prompts whose six signs no adapter on this question carries
//   section "other"      rows with no six-sign profile at all (shown one by one, last)
// `matched` is "both kinds are in this block now"; `partnerHidden` is "the other kind exists on this question but the filter hides it".
export type Section = "pair" | "no-prompt" | "no-adapter" | "other" | "size";
export interface Block { rows: Row[]; matched: boolean; bits?: string; section: Section; partnerHidden: boolean }
export type Show = "both" | "adapter" | "prompt";
export type Sort = "pair" | "size";

export const SIGNS = ["trust", "risk taking", "patience", "altruism", "positive reciprocity", "negative reciprocity"];

// ISO 3-letter codes → names, for the 42 countries of the cohort. Not data of this study; a lookup so that no
// reader meets "CAN" or "BGD" unexplained.
export const COUNTRY: Record<string, string> = {
  ARG: "Argentina", AUS: "Australia", BGD: "Bangladesh", BOL: "Bolivia", BRA: "Brazil", CAN: "Canada", CHL: "Chile", CHN: "China",
  COL: "Colombia", CZE: "Czechia", DEU: "Germany", EGY: "Egypt", GBR: "United Kingdom", GRC: "Greece", GTM: "Guatemala", IDN: "Indonesia",
  IND: "India", IRN: "Iran", IRQ: "Iraq", JOR: "Jordan", JPN: "Japan", KAZ: "Kazakhstan", KEN: "Kenya", KOR: "South Korea",
  MAR: "Morocco", MEX: "Mexico", NGA: "Nigeria", NIC: "Nicaragua", NLD: "Netherlands", PAK: "Pakistan", PER: "Peru", PHL: "Philippines",
  ROU: "Romania", RUS: "Russia", SRB: "Serbia", THA: "Thailand", TUR: "Turkey", UKR: "Ukraine", USA: "United States", VEN: "Venezuela",
  VNM: "Vietnam", ZWE: "Zimbabwe",
};
// Short question wording, written for readers; the full exported question is always shown beside it.
const SHORT: Record<string, string> = {
  wvs_Q43: "Less importance on work", wvs_Q57: "Can people be trusted?", wvs_Q81: "Confidence in charities",
  wvs_Q99: "Environmental group membership", wvs_Q176: "Hard to know right from wrong", wvs_Q50: "Satisfaction with household finances",
  wvs_Q106: "Equal incomes or individual effort?",
};
export const shortQuestion = (id: string, text?: string) => SHORT[id] ?? (text ? text.replace(/\s+/g, " ").slice(0, 44).trim() + (text.length > 44 ? "…" : "") : id);

/** Who a model key is: a country adapter, a sign prompt, or something else (label as exported). */
export function whoOf(index: IndexFile, k: string): Who {
  const l = index.models[k]?.label ?? k;
  const ad = l.match(/\+ ([A-Z]{3}) LoRA/);
  if (ad) return { b: k, kind: "adapter", cc: ad[1], name: COUNTRY[ad[1]] ?? ad[1] };
  const sp = l.match(/sign prompt ([01](?:_[01]){5})/);
  if (sp) return { b: k, kind: "prompt", name: "Sign prompt", bits: sp[1].replace(/_/g, "") };
  return { b: k, kind: "other", name: l };
}

// ------------------------------------------------------------------ numbers
/** A probability as a percentage, never rounded to a false 0 or 100. */
export function pct(p: number | undefined): string {
  if (p == null || !Number.isFinite(p)) return "n/a";
  const v = p * 100;
  if (v < 0.1) return "<0.1%";
  if (v > 99.9) return ">99.9%";
  return (v < 10 ? v.toFixed(1) : v.toFixed(0)) + "%";
}
/** A percentage with a fixed number of decimals (used only to separate a near tie). */
export const pctDec = (p: number, d: number) => (p * 100).toFixed(d) + "%";
/** A signed change, three significant digits: +14.6, −2.71, +0.74. */
export const change = (v: number) => (v >= 0 ? "+" : "−") + String(Number(Math.abs(v).toPrecision(3)));

// ------------------------------------------------------------------ items
export const labelOf = (it: ItemInfo, code: string) => String(it.labels[it.codes.indexOf(code)] ?? code);
/** An answer as a reader sees it: “Good thing” in quotes; a scale point as its number. */
export const answerName = (it: ItemInfo, code: string) => { const l = labelOf(it, code); return l === code ? `answer ${code}` : `“${l}”`; };

const infoCache = new Map<string, Promise<ItemInfo>>();
/** The question wording and answer labels, from the run manifest alone (its arrays are not fetched). */
export function loadItemInfo(file: string): Promise<ItemInfo> {
  let p = infoCache.get(file);
  if (!p) {
    p = fetch(`/exports/${file}`).then((r) => { if (!r.ok) throw new Error(`${file}: HTTP ${r.status}`); return r.json(); }).then((m) => ({
      item_id: m.item.item_id, j_plus: String(m.item.j_plus), j_minus: String(m.item.j_minus), codes: m.item.codes.map(String), labels: m.item.labels.map(String),
      text: questionText({ m } as unknown as Run) ?? "",
    }));
    infoCache.set(file, p);
  }
  return p;
}

/** The most likely answer and its percentage (`text2`: the runner-up's, set only on a near tie). When the runner-up rounds to the same figure, both get one more
 * decimal (and again, up to three) until they differ, so a near tie is never printed as two equal numbers. */
const top = (probs?: Record<string, number>): Top | undefined => {
  if (!probs) return undefined;
  const e = Object.entries(probs).sort((x, y) => y[1] - x[1]); if (!e.length) return undefined;
  const [code, p] = e[0], p2 = e[1]?.[1];
  let text = pct(p), text2: string | undefined;
  if (p2 != null && pct(p2) === text) {
    for (let d = 1; d <= 3; d++) { text = pctDec(p, d); text2 = pctDec(p2, d); if (text !== text2) break; }
  }
  return { code, p, text, code2: e[1]?.[0], text2 };
};

/** One row per comparator of `base` on `item`: its probability of j_plus next to the base's, and its change in log-odds. */
export function buildRows(index: IndexFile, base: string, item: string, info: ItemInfo, bitsOfCountry: Map<string, string>): Row[] {
  const runs = index.runs as unknown as IndexRun[];
  const probs = (m: string) => runs.find((r) => r.model === m && r.item_id === item)?.probs;
  const pb = probs(base);
  const numbersOnly = new Set((index.comparators ?? []).filter((c) => c.item_id === item && c.tier === "numbers").map((c) => c.model));
  return index.pairs.filter((p) => p.a === base && p.item_id === item).map((p) => {
    const who = whoOf(index, p.b), pc = probs(p.b);
    return {
      who, d: p.d_margin, file: p.file, pBase: pb?.[info.j_plus], pCmp: pc?.[info.j_plus], topBase: top(pb), topCmp: top(pc),
      bits: who.kind === "prompt" ? who.bits : who.cc ? bitsOfCountry.get(who.cc) : undefined,
      cohortOnly: numbersOnly.has(p.b),
    };
  });
}

/** More comparators than this and the list opens on the country adapters alone (Q57: 42 adapters + 26 sign prompts). */
export const MANY = 30;
export const defaultShow = (rows: Row[]): Show => (rows.length > MANY && rows.some((r) => r.who.kind === "adapter") ? "adapter" : "both");

/** The six signs of a profile in words: "trust +, risk taking −, …". */
export const profileName = (bits: string) => [...bits].map((c, i) => `${SIGNS[i]} ${c === "1" ? "+" : "−"}`).join(", ");

/** Filter, then arrange. "pair": rows are grouped by their six signs, one block per profile (prompt first, then its adapters, each by
 * size of change). A profile is matched when, on this question, a sign prompt and an adapter carry the same six signs; that is decided
 * on ALL rows, so a filter that hides one kind does not turn matched profiles into unmatched ones. Order of blocks: matched profiles
 * (largest change first), then adapters without a sign prompt, then sign prompts without an adapter, then rows with no profile.
 * "size": one row per block, by size of change. */
export function arrange(rows: Row[], show: Show, sort: Sort): Block[] {
  const kept = rows.filter((r) => show === "both" || r.who.kind === show);
  const size = (a: Row, b: Row) => Math.abs(b.d) - Math.abs(a.d);
  const peak = (b: Block) => Math.max(...b.rows.map((r) => Math.abs(r.d)));
  if (sort === "size") return [...kept].sort(size).map((r) => ({ rows: [r], matched: false, section: "size" as Section, partnerHidden: false }));
  const has = new Map<string, Set<Kind>>();   // profile -> kinds present on this question, filter ignored
  for (const r of rows) if (r.bits && r.who.kind !== "other") has.set(r.bits, (has.get(r.bits) ?? new Set()).add(r.who.kind));
  const groups = new Map<string, Row[]>(), other: Row[] = [];
  for (const r of kept) { if (r.bits && r.who.kind !== "other") groups.set(r.bits, [...(groups.get(r.bits) ?? []), r]); else other.push(r); }
  const blocks: Block[] = [...groups.entries()].map(([bits, g]) => {
    const kinds = has.get(bits)!, both = kinds.has("adapter") && kinds.has("prompt");
    const shown = new Set(g.map((r) => r.who.kind));
    const section: Section = both ? "pair" : kinds.has("adapter") ? "no-prompt" : "no-adapter";
    return { rows: [...g.filter((r) => r.who.kind === "prompt").sort(size), ...g.filter((r) => r.who.kind === "adapter").sort(size)], bits, section,
      matched: shown.has("adapter") && shown.has("prompt"), partnerHidden: both && shown.size < 2 };
  });
  const rank: Record<Section, number> = { pair: 0, "no-prompt": 1, "no-adapter": 2, other: 3, size: 4 };
  blocks.sort((x, y) => rank[x.section] - rank[y.section] || peak(y) - peak(x));
  return [...blocks, ...other.sort(size).map((r) => ({ rows: [r], matched: false, section: "other" as Section, partnerHidden: false }))];
}

/** The one sentence under a matched block. */
export function pairSentence(b: Block, it: ItemInfo): string {
  const lo = `the log-odds of ${answerName(it, it.j_plus)} over ${answerName(it, it.j_minus)}`;
  const w = b.rows.filter((r) => r.who.kind === "adapter"), s = b.rows.filter((r) => r.who.kind === "prompt");
  if (!w.length || !s.length) return "";
  return `Same six signs: in the weights (${w.map((r) => `${r.who.name} adapter`).join(", ")}) ${lo} move ${w.map((r) => change(r.d)).join(", ")}; in words (${s.map((r) => `sign prompt ${r.who.bits}`).join(", ")}) ${s.map((r) => change(r.d)).join(", ")}.`;
}
