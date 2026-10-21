// Tab K, Cohort. One unchanged base model against several comparators on one question: country adapters (small
// add-ons to the weights, each trained on one country's six signs) and sign prompts (the same six signs written
// into the prompt; the weights do not change).
//   1. headline   how often each comparator gives one answer, against the base (dumbbell per row), exact from index.json
//   2. controls   question picker (routes through the app), show country adapters / sign prompts / all, order by matched pairs / size.
//                 More than MANY (30) comparators, as on Q57 (42 adapters + 26 sign prompts): the list opens on the country adapters.
//                 Matched pairs = one block per six-sign profile: a header naming the profile, its sign prompt, then its adapters.
//                 Profiles that lack the other kind get their own sections, after the matched ones (see cohort-model.ts arrange()).
//                 Rows have a fixed height and the list is written to the page once per change, so 68 rows cost one layout.
//   3. map        where in the model the change happens: change in contribution to the answer, by layer
// This view describes what the models do on these saved runs. It makes no claim about what a model "represents".
// Hooks kept for tests and the verifier: #answer, data-obj="answer" | "cohort" | "cohort-legend" | "dmargin", ctx.ready().
// Every string put into innerHTML below is either a literal or went through esc().

import { loadPair, type Bundle, type IndexFile, type Pair } from "./data";
import type { Ctx } from "./main";
import { C, diverging, esc } from "./common";
import { LEGEND, NO_DATA, RULE_TIP, WHO_TIP, cellOf, compare, countryName, hpct, loadHuman, markerText } from "./human";
import {
  SIGNS, answerName, arrange, buildRows, change, defaultShow, loadItemInfo, pairSentence, pct, profileName, shortQuestion,
  type Block, type ItemInfo, type Row, type Section, type Show, type Sort,
} from "./cohort-model";

const MIN_ADAPTERS = 3;
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? "" : "s"}`;

export function mountCohort(root: HTMLElement, D: Bundle, ctx: Ctx): () => void {
  const index = (window as any).__index as IndexFile;
  const base = D.A.m.model.key ?? "", item = D.A.m.item.item_id;
  const name = (k: string) => esc(index.models[k]?.label ?? k);
  const itemsOf = (it: string) => index.pairs.filter((p) => p.a === base && p.item_id === it);
  const allItems = [...new Set(index.pairs.filter((p) => p.a === base).map((p) => p.item_id))];
  const picker = allItems.filter((it) => itemsOf(it).length >= MIN_ADAPTERS), thin = allItems.filter((it) => itemsOf(it).length < MIN_ADAPTERS);
  root.className = "tab-k v3";
  let alive = true;
  const off = () => { alive = false; };

  // ---------------------------------------------------------------- no question on this base has enough comparators
  if (!picker.length) {
    const rows = itemsOf(item);
    root.innerHTML = `
      <section id="answer" data-obj="answer"><span class="say">The base model against several comparators: <b>who moves the answer, and where in the model</b></span></section>
      <div class="k-work">
        <section class="obj k-empty" data-obj="cohort-empty"><header><span class="cap">Cohort · not built from data yet</span></header>
          <p class="lead">This view puts the base model next to several comparators on the same question. A comparator is an adapter or sign prompt compared with the base model. It needs at least ${MIN_ADAPTERS} comparators on one question.</p>
          <p class="muted">Today, for <b>${name(base)}</b> on <code>${esc(item)}</code>, the index lists ${plural(rows.length, "comparator")}: ${rows.map((r) => name(r.b)).join(", ") || "none"}. Nothing on this tab is data until a third one is exported.</p></section>
        <figure class="obj k-thumb" data-obj="illustration"><span class="illus">illustration · not data</span>
          <img src="/screens/v3/cohort-illustration.png" alt="Design mockup of the cohort map: 42 placeholder adapters by 32 layers, not data" width="560" height="262" />
          <figcaption class="foot">Design mockup: seeded placeholder values for an 8-billion-parameter base model with 42 adapters. Not a measurement.</figcaption></figure>
      </div>`;
    requestAnimationFrame(() => ctx.ready());
    return off;
  }

  document.querySelector("#frame .illus")?.remove();   // the frame's "no data yet" badge is for the empty state only

  // ---------------------------------------------------------------- state: the URL keys `show` and `sort`
  type SortK = Sort | "survey";
  const sortOf = (): SortK => (ctx.get("sort") === "size" ? "size" : ctx.get("sort") === "survey" ? "survey" : "pair");

  root.innerHTML = `<div class="k-wrap"><p id="kskel" class="muted">Loading the question wording and the saved answers…</p></div><div class="k-tip" role="tooltip" hidden></div>`;
  const wrap = root.querySelector<HTMLElement>(".k-wrap")!, tip = root.querySelector<HTMLElement>(".k-tip")!;

  const signsP = fetch("/sca2/sca2_data.json").then((r) => (r.ok ? r.json() : null)).then((d) => {
    const m = new Map<string, string>(); for (const c of d?.countries ?? []) if (c?.cc && Array.isArray(c.bits)) m.set(c.cc, c.bits.join("")); return m;
  }).catch(() => new Map<string, string>());
  const runs = index.runs as unknown as { model: string; item_id: string; file: string }[];
  const infosP = Promise.all([...new Set([...picker, ...thin])].map((it) => {
    const run = runs.find((r) => r.model === base && r.item_id === it);
    return run ? loadItemInfo(run.file) : Promise.reject(new Error(`no saved run of the base on ${it}`));
  }));

  Promise.all([infosP, signsP, loadHuman()]).then(([infos, bitsOf, human]) => {
    if (!alive) return;
    const info = new Map<string, ItemInfo>(infos.map((i) => [i.item_id, i]));
    const cur = info.get(item);
    if (!cur) throw new Error(`no question wording for ${item}`);
    const rows: Row[] = buildRows(index, base, item, cur, bitsOf);
    const enough = rows.length >= MIN_ADAPTERS;
    const kinds = { adapter: rows.filter((r) => r.who.kind === "adapter").length, prompt: rows.filter((r) => r.who.kind === "prompt").length };
    const defShow = defaultShow(rows);   // the URL key `show` is dropped when it equals this
    const showOf = (): Show => { const v = ctx.get("show"); return v === "adapter" || v === "prompt" || v === "both" ? v : defShow; };
    const ladder = (b: string, it = item) => `a=${encodeURIComponent(base)}&b=${encodeURIComponent(b)}&item=${encodeURIComponent(it)}`;
    // Switching question keeps the current comparator when it also has a pair on the new question.
    const bFor = (it: string) => { const ps = itemsOf(it); return (ps.find((p) => p.b === D.B.m.model.key) ?? ps[0]).b; };
    const lays = new Map<string, number[]>();   // filled when the pair files arrive
    const ans = (code: string) => answerName(cur, code);
    // ---- WB7-H: the descriptive human reference. On only for a survey question and only when the bundle has the file.
    const humanOn = !!human && item.startsWith("wvs_");
    const probsOf = (m: string) => runs.find((r) => r.model === m && r.item_id === item) as unknown as { probs?: Record<string, number> } | undefined;
    const itemShape = { codes: cur.codes, labels: cur.labels, j_plus: cur.j_plus, j_minus: cur.j_minus };
    /** null: no survey comparison for this row (a sign prompt is a profile, not a country). "nodata": a country with no cell. */
    const survey = (r: Row) => {
      if (!humanOn || r.who.kind !== "adapter" || !r.who.cc) return null;
      const ci = cellOf(human, item, r.who.cc), pb = probsOf(base)?.probs, pc = probsOf(r.who.b)?.probs;
      if (!ci || !pb || !pc) return "nodata" as const;
      return { ci, c: compare(itemShape, ci.cell, pb, pc), share: ci.cell.shares[cur.j_plus] ?? 0 };
    };
    const rank = (r: Row) => { const v = survey(r); return v == null ? 3 : v === "nodata" ? 2 : v.c.closer ? 0 : 1; };   // yes, no, no survey data, sign prompt
    const surveyTip = (r: Row) => {
      const v = survey(r); if (v == null) return "";
      const who = countryName(r.who.cc!);
      if (v === "nodata") return ` Survey: ${NO_DATA} for ${who}.`;
      return ` Survey: ${hpct(v.share)} of respondents in ${who} chose ${plus}. ${v.c.rule === "mean" ? `Mean answer ${v.c.human.toFixed(1)}; the model's expected answer ${v.c.base.toFixed(1)} (base model), ${v.c.cmp.toFixed(1)} (adapter). ` : ""}${markerText(v.c)}. Descriptive comparison, not a Paper B result.`;
    };
    const svCell = (r: Row) => {
      const v = survey(r);
      if (!humanOn) return "";
      if (v == null) return `<div class="k-sv" title="A sign prompt is a profile, not a country: it has no survey comparison.">–</div>`;
      if (v === "nodata") return `<div class="k-sv nd" data-hum="nodata" title="${esc(NO_DATA + " for this country on this question")}">${NO_DATA}</div>`;
      return `<div class="k-sv ${v.c.closer ? "yes" : "no"}" data-hum="marker" title="${esc(markerText(v.c) + ". " + RULE_TIP + " " + WHO_TIP)}">${v.c.closer ? "yes" : "no"}</div>`;
    };
    const plus = ans(cur.j_plus), minus = ans(cur.j_minus);

    const dots = (bits?: string, onMap = false) => bits && !onMap ? `<span class="k-dots" title="${esc(SIGNS.map((s, i) => `${s}: ${bits[i] === "1" ? "positive" : "negative"}`).join(" · "))}" aria-hidden="true">${[...bits].map((c) => `<i class="${c === "1" ? "p" : "n"}"></i>`).join("")}<code>${esc(bits)}</code></span>` : "";
    const who = (r: Row) => (r.who.kind === "adapter" ? `${r.who.name} adapter` : r.who.kind === "prompt" ? `Sign prompt ${r.bits ?? ""}`.trim() : r.who.name);
    const poss = (n: string) => (n.endsWith("s") ? `${n}'` : `${n}'s`);
    // "= China's signs": the country adapter on this question that carries the same six signs (only when one is listed)
    const match = (r: Row) => {
      if (r.who.kind !== "prompt" || !r.bits) return "";
      const ad = rows.filter((o) => o.who.kind === "adapter" && o.bits === r.bits).map((o) => poss(o.who.name));
      return ad.length ? `= ${ad.join(" and ")} signs` : "";
    };
    const rowTip = (r: Row) => `${who(r)}${match(r) ? " " + match(r) : ""}: the model gives ${plus} a ${pct(r.pCmp)} probability (base model ${pct(r.pBase)}). Change from the base model in the log-odds of ${plus} over ${minus}: ${change(r.d)}.${surveyTip(r)}`;
    const label = (r: Row, onMap = false) => r.who.kind === "adapter"
      ? `<span class="k-nm"><b>${esc(r.who.name)}</b><em>country adapter</em></span>${dots(r.bits, onMap)}`
      : r.who.kind === "prompt" ? `<span class="k-nm"><b>Sign prompt${onMap && r.bits ? " " + esc(r.bits) : ""}</b><em>${esc(match(r) || "weights unchanged")}</em></span>${dots(r.bits, onMap)}`
      : `<span class="k-nm"><b>${esc(r.who.name)}</b></span>`;
    // A comparator with only its probabilities in the public sample ("Cohort only") has no Ladder: its rows do not navigate.
    const go = (r: Row) => (r.cohortOnly ? "" : `data-go="c" data-extra="${esc(ladder(r.who.b))}"`);
    const coTip = "Not shipped in the public sample: only this comparator's answer probabilities and its per-layer changes are here, so there is no Ladder to open.";
    const twins = (r: Row) => (r.bits ? rows.filter((o) => o !== r && o.bits === r.bits && o.who.kind !== r.who.kind && o.who.kind !== "other") : []);
    const sameSigns = (r: Row) => (twins(r).length
      ? `<span class="k-same" title="Another comparator on this question carries the same six signs. Order by matched pairs to see them side by side.">same signs as ${esc(twins(r).map((o) => (o.who.kind === "adapter" ? o.who.name + " adapter" : "the sign prompt")).join(", "))}</span>` : "");
    // The left cell of a list row: two lines, fixed. Inside a profile block the six signs are in the block header, so the row is the name alone.
    const listWho = (r: Row, blk: Block) => {
      const grouped = blk.section !== "size" && blk.section !== "other";
      // In a profile block the header already says which kind of comparator follows, so the row is the name alone.
      const nm = r.who.kind === "adapter" ? `<b>${esc(r.who.name)}</b>${grouped ? "" : "<em>country adapter</em>"}`
        : r.who.kind === "prompt" ? `<b>Sign prompt</b>${grouped ? "" : `<em>${esc(match(r) || "weights unchanged")}</em>`}` : `<b>${esc(r.who.name)}</b>`;
      return `<span class="k-nm">${nm}${r.cohortOnly ? `<i class="k-tag" title="${esc(coTip)}">Cohort only</i>` : ""}</span>${grouped ? "" : `<span class="k-sub2">${dots(r.bits)}${sameSigns(r)}</span>`}`;
    };

    // ---- the dumbbell: base model (white bar) to comparator (filled dot), on a fixed 0 to 100% axis.
    // The chevron sits just beyond the comparator dot, on the side the probability moved to, so a direction shows even
    // when the two markers overlap (a 0.2-point change is one pixel wide).
    const dumbbell = (r: Row) => {
      if (r.pBase == null || r.pCmp == null) return `<div class="k-db muted">probabilities not in the index</div>`;
      const b = r.pBase * 100, c = r.pCmp * 100, lo = Math.min(b, c), w = Math.abs(c - b);
      const dir = c > b ? "r" : c < b ? "l" : "";
      const sv = survey(r), tick = sv && sv !== "nodata" ? `<i class="k-hu" style="left:${sv.share}%" data-hum="tick"></i>` : "";
      return `<div class="k-db" aria-hidden="true">${tick}${w > 0 ? `<i class="k-ln" style="left:${lo}%;width:${w}%"></i>` : ""}<i class="k-mb" style="left:${b}%"></i><i class="k-mc" style="left:${c}%"></i>${dir ? `<i class="k-chev ${dir}" style="left:${c}%"></i>` : ""}</div>`;
    };
    const topName = (code: string) => ans(code).replace(/^answer /, "");
    // The percentage of the followed answer, with extra decimals only when it ties the most likely answer after rounding.
    const plusText = (t: Row["topBase"], p: number | undefined) => (t?.code === cur.j_plus ? t.text : t?.code2 === cur.j_plus && t.text2 ? t.text2 : pct(p));
    // One caption per block when every row of the block has the same pair of most likely answers (the percentages are in each row).
    const sameLikely = (b: Block) => b.rows.length > 1 && b.rows.every((r) => r.topBase && r.topCmp && r.topBase.code === b.rows[0].topBase?.code && r.topCmp.code === b.rows[0].topCmp?.code);
    const rowHtml = (r: Row, blk: Block) => {
      const tb = r.topBase, tc = r.topCmp;
      const likely = tb && tc && !(blk.section !== "size" && blk.section !== "other" && sameLikely(blk)) ? `<span class="k-top">Most likely answer: ${esc(topName(tb.code))} (${tb.text}) → ${esc(topName(tc.code))} (${tc.text})</span>` : "";
      return `<div class="k-row${r.cohortOnly ? " k-co" : ""}" tabindex="0" role="group" data-b="${esc(r.who.b)}" aria-label="${esc(rowTip(r) + (r.cohortOnly ? " Cohort only: not shipped in the public sample." : " Press Enter to open this pair in the Ladder."))}" ${go(r)}>
        <div class="k-who">${listWho(r, blk)}</div>
        <div class="k-mid">${dumbbell(r)}${likely}</div>
        <div class="k-pc"><b>${plusText(tb, r.pBase)}</b> <span aria-hidden="true">→</span> <b class="c">${plusText(tc, r.pCmp)}</b></div>
        <div class="k-d num" title="Change from the base model, in log-odds of ${esc(plus)} over ${esc(minus)}">${change(r.d)}</div>
        ${svCell(r)}
        ${r.cohortOnly ? `<span class="k-open" title="${esc(coTip)}">Cohort only</span>` : `<a class="k-open" href="?tab=c&${esc(ladder(r.who.b))}" ${go(r)} tabindex="-1">Open in the Ladder →</a>`}</div>`;
    };
    const axis = `<div class="k-row k-axis" aria-hidden="true"><div class="k-who"></div><div class="k-mid"><div class="k-ticks">${[0, 25, 50, 75, 100].map((t) => `<span style="left:${t}%">${t}%</span>`).join("")}</div></div><div class="k-pc">base model → comparator</div><div class="k-d" title="Change from the base model, in log-odds">log-odds change</div>${humanOn ? `<div class="k-sv" title="${esc(RULE_TIP)}">closer to survey than base?</div>` : ""}<div class="k-open"></div></div>`;

    // ---- the layer map: one row per comparator, one square per layer
    const L = D.A.m.model.n_layers;
    const TICKS = [...new Set([...Array.from({ length: Math.floor((L - 1) / 5) + 1 }, (_, i) => i * 5), L - 1])];
    const mapRowHtml = (r: Row, m: number) => {
      const v = lays.get(r.who.b);
      let best = -1; if (v) v.forEach((x, l) => { if (best < 0 || Math.abs(x) > Math.abs(v[best])) best = l; });
      const cells = v ? v.map((x, l) => `<i data-l="${l}" style="background:${diverging(x, m)}"></i>`).join("") : `<span class="muted">loading…</span>`;
      const aria = `${who(r)}${match(r) ? " " + match(r) : ""}.${v ? ` Largest change at layer ${best}: ${change(v[best])}.` : ""}${r.cohortOnly ? " Cohort only: not shipped in the public sample." : " Press Enter to open this pair in the Ladder."}`;
      return `<div class="k-hrow${r.cohortOnly ? " k-co" : ""}" tabindex="0" role="group" data-b="${esc(r.who.b)}" aria-label="${esc(aria)}" ${go(r)}>
        <div class="k-who">${label(r, true)}</div><div class="k-cells" style="--L:${L}">${cells}</div><span class="k-go" aria-hidden="true">${r.cohortOnly ? "" : "›"}</span></div>`;
    };
    const mapHtml = (blocks: Block[]) => {
      const all = [...lays.values()].flat(), m = all.length ? Math.max(...all.map(Math.abs)) || 1 : 1;
      const grad = [-1, -0.5, -0.25, 0, 0.25, 0.5, 1].map((s) => `${diverging(s * m, m)} ${((s + 1) * 50).toFixed(0)}%`).join(",");
      const body = blocks.map((b) => `<div class="k-hblk${b.rows.length > 1 ? " m" : ""}">${b.rows.length > 1 ? `<div class="k-gb" aria-hidden="true"></div>` : ""}${b.rows.map((r) => mapRowHtml(r, m)).join("")}</div>`).join("");
      return `<header><span class="cap">Where in the model the change happens</span></header>
        <p class="k-sub">Each square is one layer: how much that layer's contribution to the answer changes, comparator minus base model. Hover a square for the number. Click a row to open that pair in the Ladder (rows marked “Cohort only” have no Ladder in the public sample).</p>
        <p class="k-mq" data-obj="cohort-map-question"><span class="muted">Question · </span>“${esc(cur.text)}”</p>
        <div class="k-hrow k-haxis" aria-hidden="true"><div class="k-who">layer →</div><div class="k-cells k-lay">${TICKS.map((l) => `<span style="left:${((l + 0.5) / L) * 100}%">${l}</span>`).join("")}</div><span class="k-go"></span></div>
        <div class="k-hrow k-haxis k-hnote" aria-hidden="true"><div class="k-who"></div><div class="k-cells k-lay"><span class="l">← reads the question</span><span class="r">writes the answer →</span></div><span class="k-go"></span></div>
        <div id="kmap"><div class="k-grid" aria-hidden="true"><div></div><div class="k-gl">${TICKS.map((l) => `<i style="left:${((l + 0.5) / L) * 100}%"></i>`).join("")}</div><div></div></div>${body || `<p class="muted">No rows match this filter.</p>`}</div>
        <div class="k-key"><div class="k-kb"><span class="bar" style="background:linear-gradient(90deg,${grad})"></span><span class="ends"><i>${change(-m).replace("+", "")}</i><i>0</i><i>${change(m)}</i></span><span class="unit">log-odds</span></div>
          <p><b style="color:${C.pos}">Blue</b>: the layer pushes toward ${esc(plus)}. <b style="color:${C.neg}">Orange</b>: toward ${esc(minus)}. Dark: about zero. Squares are drawn on a square-root scale: small changes are drawn brighter than their size, so faint squares stay visible.</p></div>`;
    };

    const thinMsg = !enough ? `<p class="k-thinnote" data-obj="cohort-thin"><b>Only ${plural(rows.length, "comparator")} on this question.</b> That is too few to compare, so the layer map is not drawn. The saved answers are shown as they are. Pick a question with ${MIN_ADAPTERS} or more above, or open a pair in the Ladder.</p>` : "";

    // ---- the page
    const known = rows.filter((r) => r.pCmp != null), lo = Math.min(...known.map((r) => r.pCmp!)), hi = Math.max(...known.map((r) => r.pCmp!));
    const sentence = `The base model gives ${esc(plus)} a <b>${plusText(rows[0]?.topBase, rows[0]?.pBase)}</b> probability on “${esc(shortQuestion(item, cur.text))}”. Across the ${plural(rows.length, "comparator")} it ranges from <b>${pct(lo)}</b> to <b>${pct(hi)}</b>.<span class="k-def">A comparator is an adapter or sign prompt compared with the base model.</span>`;
    const pickBtn = (it: string) => {
      const i = info.get(it)!, n = itemsOf(it).length;
      return `<button type="button" class="${it === item ? "on" : ""}" aria-pressed="${it === item}" data-go="k" data-extra="${esc(`b=${encodeURIComponent(bFor(it))}&item=${encodeURIComponent(it)}`)}" title="${esc(`${i.text} (${it})`)}">${esc(shortQuestion(it, i.text))} <span class="n">${n}</span></button>`;
    };
    const thinName = (it: string) => shortQuestion(it, info.get(it)?.text);
    const thinHtml = thin.length ? `<p class="k-thin" data-obj="cohort-thin-questions"><b>Not in the picker:</b> ${thin.map((it) => `${esc(thinName(it))} (only ${itemsOf(it).length} comparators, too few to compare; <a href="?tab=c&${esc(ladder(itemsOf(it)[0].b, it))}" data-go="c" data-extra="${esc(ladder(itemsOf(it)[0].b, it))}">open in the Ladder →</a>)`).join("; ")}.</p>` : "";
    const seg = (key: string, opts: [string, string, string?][], now: string) => `<span class="k-seg" role="group" aria-label="${key === "show" ? "Show" : "Order by"}">${opts.map(([v, t, ttl]) => `<button type="button" data-${key}="${v}" aria-pressed="${v === now}" class="${v === now ? "on" : ""}"${ttl ? ` title="${esc(ttl)}"` : ""}>${t}</button>`).join("")}</span>`;

    wrap.innerHTML = `
      <section id="answer" data-obj="answer"><span class="say">${sentence}</span></section>
      <section class="k-controls" data-obj="cohort-controls">
        <div class="k-ctl"><span class="cap" id="kq">Question</span><span class="k-pick" role="group" aria-labelledby="kq">${picker.map(pickBtn).join("")}</span></div>
        ${thinHtml}
        <p class="k-q" data-obj="cohort-question"><span class="muted">${esc(cur.item_id)} · </span>“${esc(cur.text)}”<br><span class="muted">Answer followed: ${esc(plus)}. Log-odds compare only ${esc(plus)} and ${esc(minus)}, so they can move differently from one answer's percentage.</span></p>
      </section>
      ${thinMsg}
      <section class="obj k-head" data-obj="dmargin"><header><span class="cap">Probability each model gives this answer${humanOn ? " · share of respondents who chose it (pink)" : ""}</span><span class="k-legend" aria-hidden="true"><i class="k-lb"></i>base model<i class="k-lc"></i>comparator${humanOn ? `<i class="k-lh" title="${esc(WHO_TIP)}"></i><span title="${esc(WHO_TIP)}">${LEGEND}</span>` : ""}</span></header>
        <div class="k-ctl2"><span class="k-ctl"><span class="cap">Show</span><span id="kshow"></span></span><span class="k-ctl"><span class="cap">Order by</span><span id="ksort"></span></span></div>
        <div id="krows"${humanOn ? ` class="k-hum"` : ""}></div></section>
      ${enough ? `<section class="obj k-map" data-obj="cohort" id="kmapsec"></section>` : ""}
      <details class="k-more" data-obj="cohort-legend"><summary>What do these words mean?</summary>
        <dl>
          <dt>Base model</dt><dd>Llama-3.1-8B-Instruct with no change, a large language model. Every comparator is compared with it.</dd>
          <dt>Comparator</dt><dd>An adapter or a sign prompt compared with the base model.</dd>
          <dt>Country adapter</dt><dd>A small add-on to the weights, trained on one country's six signs. (Technical name: LoRA adapter.)</dd>
          <dt>Sign prompt</dt><dd>The same six signs written into the prompt. The weights do not change. The six signs are trust, risk taking, patience, altruism, positive reciprocity and negative reciprocity. Each is positive (filled dot, 1) or negative (open dot, 0).</dd>
          <dt>Log-odds of “A” over “B”</dt><dd>The log of how much more likely the model is to answer A than B, as in a logit. (Technical name: margin.) The change from the base model is the comparator's value minus the base model's.</dd>
          <dt>Layer</dt><dd>One of 32 processing steps the model runs in order.</dd>
          <dt>Contribution to the answer</dt><dd>How much a layer pushes the log-odds toward one answer or the other. (Technical name: direct logit attribution.) Each square adds two parts: <b>attention</b>, which reads earlier words, and the <b>MLP block</b>, which transforms what was read.</dd>
        </dl>
        <p class="muted">This view describes what the models do on these saved runs. It does not show that a model represents a country.</p></details>`;

    // ---- drawing, repeated when a filter changes. The list is built as one string and written once; rows have a fixed height
    // (style.css), so the browser lays the list out in one pass and skips the rows that are off screen.
    const count = new Map<string, { a: number; p: number }>();   // per six-sign profile, all rows of this question
    for (const r of rows) if (r.bits && r.who.kind !== "other") { const c = count.get(r.bits) ?? { a: 0, p: 0 }; c[r.who.kind === "adapter" ? "a" : "p"]++; count.set(r.bits, c); }
    const SECTION: Record<Section, (n: number) => string> = {
      pair: (n) => `A sign prompt and country adapters with the same six signs · ${plural(n, "profile")}`,
      "no-prompt": (n) => `Country adapters with no sign prompt of the same six signs on this question · ${plural(n, "profile")}`,
      "no-adapter": (n) => `Sign prompts with no country adapter of the same six signs on this question · ${plural(n, "profile")}`,
      other: (n) => `Comparators with no six-sign profile · ${n}`,
      size: () => "",
    };
    const headHtml = (b: Block) => {
      const c = count.get(b.bits!)!;
      const hid = b.partnerHidden ? ` <span class="k-gh">· ${b.rows[0].who.kind === "adapter" ? "sign prompt" : "country adapters"} hidden by the filter</span>` : "";
      return `<div class="k-ghead" role="heading" aria-level="4" aria-label="${esc(`Six signs ${b.bits}: ${profileName(b.bits!)}`)}">${dots(b.bits)}<span class="k-gname">${esc(profileName(b.bits!))}</span><span class="k-gn">${[c.p ? plural(c.p, "sign prompt") : "", c.a ? plural(c.a, "country adapter") : ""].filter(Boolean).join(" · ")}${hid}</span></div>`;
    };
    const listHtml = (blocks: Block[], sort: Sort) => {
      const out: string[] = [axis];
      if (sort === "pair") out.push(`<p class="k-note">Each block is one six-sign profile: the sign prompt first, then the country adapters trained on the same six signs. + is a positive sign (filled dot), − a negative one (open dot).</p>`);
      const per = new Map<Section, number>(); for (const b of blocks) per.set(b.section, (per.get(b.section) ?? 0) + 1);
      let last: Section | null = null;
      for (const b of blocks) {
        if (sort === "pair" && b.section !== last) { last = b.section; out.push(`<h4 class="k-sec">${esc(SECTION[b.section](b.section === "other" ? rows.filter((r) => !r.bits || r.who.kind === "other").length : per.get(b.section)!))}</h4>`); }
        if (b.section === "size" || b.section === "other") { out.push(b.rows.map((r) => rowHtml(r, b)).join("")); continue; }
        const sentence = b.matched ? pairSentence(b, cur) : "";
        out.push(`<div class="k-group" role="group" aria-label="${esc(`Six signs ${b.bits}`)}">${headHtml(b)}${sameLikely(b) ? `<p class="k-same">Most likely answer in every row: ${esc(topName(b.rows[0].topBase!.code))} → ${esc(topName(b.rows[0].topCmp!.code))}</p>` : ""}${b.rows.map((r) => rowHtml(r, b)).join("")}${sentence ? `<p class="k-pair">${esc(sentence)}</p>` : ""}</div>`);
      }
      return out.join("");
    };
    let blocksNow: Block[] = [];
    const drawMap = () => { const ms = root.querySelector("#kmapsec"); if (ms) ms.innerHTML = mapHtml(blocksNow); };
    const draw = () => {
      const show = showOf(), want = sortOf(), sort: SortK = want === "survey" && !humanOn ? "pair" : want;
      // "survey": one row per block, the rows that are closer to the survey than the base model first, then the others, then no survey data and sign prompts; by size of change within each
      const flat = sort === "survey" ? arrange(rows, show, "size") : null;
      const blocks = (blocksNow = flat ? flat.sort((x, y) => rank(x.rows[0]) - rank(y.rows[0])) : arrange(rows, show, sort as Sort));
      const cnt = (n: number) => (n ? ` <span class="n">${n}</span>` : "");
      root.querySelector("#kshow")!.innerHTML = seg("show", [["adapter", `Country adapters${cnt(kinds.adapter)}`], ["prompt", `Sign prompts${cnt(kinds.prompt)}`], ["both", `All comparators${cnt(rows.length)}`]], show);
      root.querySelector("#ksort")!.innerHTML = seg("sort", [["pair", "Matched pairs", "Group the rows by their six signs: a sign prompt and the country adapters trained on the same six signs, side by side"], ["size", "Size of change (log-odds)", "Largest change in log-odds from the base model first, up or down"], ...(humanOn ? [["survey", "Closer to the survey", "Rows that are closer to the survey than the base model first. " + RULE_TIP] as [string, string, string]] : [])], sort);
      root.querySelector("#krows")!.innerHTML = blocks.length ? listHtml(blocks, sort === "survey" ? "size" : sort) : `<p class="muted">No comparator of this kind on this question.</p>`;
      drawMap();
    };
    draw();

    // ---- events: filters, tooltip, hover link between the two lists, Enter on a row
    root.addEventListener("click", (e) => {
      const t = e.target as HTMLElement, s = t.closest<HTMLElement>("[data-show]"), o = t.closest<HTMLElement>("[data-sort]");
      if (s) { const v = s.dataset.show!; ctx.set("show", v === defShow ? null : v); draw(); root.querySelector<HTMLElement>(`[data-show="${v}"]`)?.focus(); }
      if (o) { const v = o.dataset.sort!; ctx.set("sort", v === "pair" ? null : v); draw(); root.querySelector<HTMLElement>(`[data-sort="${v}"]`)?.focus(); }
    });
    root.addEventListener("keydown", (e) => {
      const r = (e.target as HTMLElement).closest<HTMLElement>(".k-row[data-go], .k-hrow[data-go]");
      if (r && e.target === r && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); r.click(); }
    });
    // The hover link between the two lists touches only the rows of the comparator under the pointer, and only when it changes.
    const byB = new Map(rows.map((r) => [r.who.b, r] as const));
    let hlNow: string | null = null;
    const hl = (b: string | null) => {
      if (b === hlNow) return;
      hlNow = b;
      root.querySelectorAll<HTMLElement>("[data-b].hl").forEach((el) => el.classList.remove("hl"));
      if (b != null) root.querySelectorAll<HTMLElement>(`[data-b="${CSS.escape(b)}"]`).forEach((el) => el.classList.add("hl"));
    };
    // Tooltip text is made when it is shown (a layer square, or a list row), not stored in 2,000 attributes.
    const tipOf = (el: HTMLElement): string => {
      const sq = el.closest<HTMLElement>(".k-cells i[data-l]");
      if (sq) {
        const r = byB.get(sq.closest<HTMLElement>("[data-b]")?.dataset.b ?? ""), l = Number(sq.dataset.l), x = r ? lays.get(r.who.b)?.[l] : undefined;
        return r && x != null ? `${who(r)}${match(r) ? " " + match(r) : ""} · layer ${l}: contribution to the answer changes by ${change(x)} (toward ${x >= 0 ? plus : minus}). Attention and MLP block together.` : "";
      }
      const row = el.closest<HTMLElement>(".k-row[data-b]"), r = row && byB.get(row.dataset.b!);
      return r ? rowTip(r) : "";
    };
    const place = (x: number, y: number) => { tip.style.left = Math.max(8, Math.min(x + 14, innerWidth - 360)) + "px"; tip.style.top = Math.max(8, Math.min(y + 16, innerHeight - 100)) + "px"; };
    root.addEventListener("pointermove", (e) => {
      const el = e.target as HTMLElement, text = tipOf(el);
      hl(el.closest<HTMLElement>("[data-b]")?.dataset.b ?? null);
      if (!text) { tip.hidden = true; return; }
      if (tip.textContent !== text) tip.textContent = text;
      tip.hidden = false; place(e.clientX, e.clientY);
    });
    root.addEventListener("pointerleave", () => { tip.hidden = true; hl(null); });
    root.addEventListener("focusin", (e) => {
      const r = (e.target as HTMLElement).closest<HTMLElement>("[data-b]"); hl(r?.dataset.b ?? null);
      const text = r ? tipOf(r) : "";
      if (!r || !text) { tip.hidden = true; return; }
      const b = r.getBoundingClientRect(); tip.textContent = text; tip.hidden = false; place(b.left + 200, b.bottom - 8);
    });
    root.addEventListener("focusout", () => { tip.hidden = true; hl(null); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") tip.hidden = true; }, { signal: ctx.signal });

    // ---- layer data: one pair file per row (only its layer arrays are read)
    if (!enough) { ctx.ready(); return; }
    return Promise.all(rows.map((r) => loadPair(r.file, ["d_attn_attr", "d_mlp_attr"]).then((P: Pair) => ({ r, P })))).then((got) => {
      if (!alive) return;
      for (const { r, P } of got) {
        if (!P.t.d_attn_attr || !P.t.d_mlp_attr) continue;
        lays.set(r.who.b, Array.from({ length: L }, (_, l) => P.t.d_attn_attr.get(l) + P.t.d_mlp_attr.get(l)));
      }
      drawMap();
      ctx.ready();
    });
  }).catch((e) => {
    if (!alive) return;
    (window as any).__ready = "error: " + String(e);
    root.querySelector(".k-wrap")!.innerHTML = `<p class="loadfail" role="alert">The Cohort view could not be drawn: ${esc(String(e))}</p>`;
  });
  return off;
}
