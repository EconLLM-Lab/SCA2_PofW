// WB7-H: the descriptive human reference. Country-level shares from one survey wave (World Values Survey, wave 7),
// shown beside what the model gives. Everything here is OFF unless the bundle carries exports/human_reference.json
// (built with --human-reference); when the file is absent nothing is drawn and nothing throws.
//
// The comparison is descriptive: it is not a Paper B result, and no Paper B statistic appears here. Respondents "chose";
// the model "gives a probability". The one marker, "closer to the survey than the base model", uses a fixed rule:
//   2 answers     compare the probability of the named answer with the survey share of that answer
//   3+ answers    compare the model's expected answer (sum of probability x answer value) with the survey's mean answer
// Smaller gap wins. The survey figures are the rounded ones in the file (whole percent; mean to one decimal).
// innerHTML below carries numbers and export strings passed through esc().

import { esc, learnText, short } from "./common";
import { COUNTRY, pct } from "./cohort-model";
import type { Bundle } from "./data";

export interface HumanCell { n: number; shares: Record<string, number>; top: string; mean?: number }
export interface HumanItem { codes: string[]; labels: string[]; ordered: boolean; cells: Record<string, HumanCell> }
export interface HumanRef { source: string; items: Record<string, HumanItem> }
export interface ItemShape { codes: string[]; labels: string[]; j_plus: string; j_minus: string }
type Probs = Record<string, number>;

export const WHO_TIP = "Descriptive comparison, not a Paper B result. Survey: the share of respondents in that country who chose the answer (World Values Survey, wave 7, weighted). Model: the probability it gives that answer.";
export const RULE_TIP = "Closer than the base model: for a 2-answer question, the model's probability of the named answer is nearer the survey share than the base model's; for a question with more answers, the model's expected answer is nearer the survey's mean answer. Smaller gap wins.";
export const NO_DATA = "no survey data";
export const LEGEND = "people in that country (WVS-7)";

let cache: Promise<HumanRef | null> | null = null;
/** The file, once. Absent, unreadable or not the expected shape: null, never an error. */
export function loadHuman(): Promise<HumanRef | null> {
  cache ??= fetch(`/exports/human_reference.json`).then(async (r) => {
    if (!r.ok) return null;
    const j = JSON.parse(await r.text());
    return j && typeof j.items === "object" && typeof j.source === "string" ? (j as HumanRef) : null;
  }).catch(() => null);
  return cache;
}

/** The country code of a country-adapter model label ("… + USA LoRA"), else null (a sign prompt is a profile, not a country). */
export const adapterCountry = (label: string): string | null => label.match(/\+ ([A-Z]{3}) LoRA/)?.[1] ?? null;
export const countryName = (cc: string) => COUNTRY[cc] ?? cc;
export const hpct = (v: number) => (v < 1 ? "<1%" : `${v}%`);
/** The survey cell for one country on one question: null = "no survey data" (also when n < 100, which the file never holds). */
export const cellOf = (h: HumanRef | null, item: string, cc: string): { it: HumanItem; cell: HumanCell } | null => {
  const it = h?.items[item], cell = it?.cells[cc];
  return it && cell ? { it, cell } : null;
};
export const expected = (p: Probs, codes: string[]) => codes.reduce((s, c) => s + (p[c] ?? 0) * Number(c), 0);

export interface Cmp { rule: "share" | "mean"; human: number; base: number; cmp: number; closer: boolean; tie: boolean }
/** The fixed rule. `human` is a share in 0..1 (rule "share") or a mean answer (rule "mean"). */
export function compare(it: ItemShape, cell: HumanCell, pBase: Probs, pCmp: Probs): Cmp {
  const mean = it.codes.length > 2 && cell.mean != null && it.codes.every((c) => Number.isFinite(Number(c)));
  const human = mean ? cell.mean! : (cell.shares[it.j_plus] ?? 0) / 100;
  const base = mean ? expected(pBase, it.codes) : pBase[it.j_plus] ?? 0, cmp = mean ? expected(pCmp, it.codes) : pCmp[it.j_plus] ?? 0;
  const gb = Math.abs(base - human), gc = Math.abs(cmp - human);
  return { rule: mean ? "mean" : "share", human, base, cmp, closer: gc < gb, tie: gc === gb };
}
/** The two gaps behind the marker, so "closer" is never read as "matches": percentage points (2 answers) or answer-scale units. */
export const gapText = (c: Cmp) => c.rule === "share"
  ? `${Math.round(Math.abs(c.cmp - c.human) * 100)} vs ${Math.round(Math.abs(c.base - c.human) * 100)} percentage points from the survey share`
  : `${Math.abs(c.cmp - c.human).toFixed(1)} vs ${Math.abs(c.base - c.human).toFixed(1)} points from the survey mean on the answer scale`;
export const markerText = (c: Cmp) => (c.tie ? "as far from the survey as the base model" : c.closer ? "closer to the survey than the base model" : "further from the survey than the base model")
  + ` (${gapText(c)})`;

/** The Ladder line, for country adapter B. Returns "" when this is not a survey question with a country adapter. */
export function ladderHTML(D: Bundle, h: HumanRef): string {
  const cc = D.A.m.model.adapter ? null : adapterCountry(D.B.m.model.label);
  const item = D.A.m.item;
  if (!cc || !item.item_id.startsWith("wvs_")) return "";
  const ci = cellOf(h, item.item_id, cc), who = countryName(cc);
  const learn = learnText(D, "groundTruth")[0] !== "?" ? ` <button class="lm" data-learn="groundTruth" title="Learn more: the human reference" aria-label="Learn more: the human reference">how to read this</button>` : "";
  const head = `<span class="hum-tag" title="${esc(WHO_TIP)}">Survey, descriptive</span>`;
  if (!ci) return `${head}<span class="say2" data-hum="nodata">${esc(NO_DATA)} for ${esc(who)} on this question (World Values Survey, wave 7).</span>${learn}`;
  const it: ItemShape = { codes: item.codes.map(String), labels: item.labels.map(String), j_plus: String(item.j_plus), j_minus: String(item.j_minus) };
  const pA = D.A.m.readout.probs as Probs, pB = D.B.m.readout.probs as Probs;
  const c = compare(it, ci.cell, pA, pB), lab = (code: string) => `“${esc(it.labels[it.codes.indexOf(code)] ?? code)}”`;
  const bName = `${esc(who)} adapter`;
  const line = c.rule === "share"
    ? `In the World Values Survey (wave 7), <b data-hum="n">${hpct(ci.cell.shares[it.j_plus] ?? 0)}</b> of respondents in ${esc(who)} chose ${lab(it.j_plus)}. The model gives it a probability of <b>${pct(pA[it.j_plus])}</b> (base model) and <b>${pct(pB[it.j_plus])}</b> (${bName}).`
    : `In the World Values Survey (wave 7), respondents in ${esc(who)} chose ${lab(ci.cell.top)} most often (<b data-hum="n">${hpct(ci.cell.shares[ci.cell.top] ?? 0)}</b>); their mean answer was <b data-hum="n">${ci.cell.mean!.toFixed(1)}</b>. The model's expected answer is <b>${c.base.toFixed(1)}</b> (base model) and <b>${c.cmp.toFixed(1)}</b> (${bName}).`;
  const mk = `<span class="hum-mk ${c.tie ? "tie" : c.closer ? "yes" : "no"}" data-hum="marker" title="${esc(RULE_TIP)}">${esc(markerText(c))}</span>`;
  const rows = it.codes.map((code, i) => `<tr><th scope="row">${esc(short(it.labels[i], 40))}</th><td data-hum="n">${hpct(ci.cell.shares[code] ?? 0)}</td><td>${pct(pA[code])}</td><td>${pct(pB[code])}</td></tr>`).join("");
  const all = `<details class="hum-all"><summary title="Every answer: the share of respondents who chose it, and the probability each model gives it">all answers</summary>
    <table><thead><tr><th>answer</th><th title="Share of respondents who chose it (survey)">respondents</th><th>base model</th><th>${bName}</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="muted">${esc(h.source)}. ${ci.cell.n.toLocaleString("en-US")} respondents in ${esc(who)} on this question. Shares are rounded to whole percent.</p></details>`;
  return `${head}<span class="say2">${line}</span>${mk}${all}${learn}`;
}

/** Fill the Ladder's human line (hidden until the file has loaded and applies). */
export function mountHumanLine(host: HTMLElement, D: Bundle) {
  host.hidden = true; host.innerHTML = "";
  loadHuman().then((h) => {
    if (!h || !host.isConnected) return;
    const html = ladderHTML(D, h);
    if (html) { host.innerHTML = html; host.hidden = false; }
  });
}
