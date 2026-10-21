// Tab K, Cohort. One unchanged base model against several comparators on one question: country adapters (small
// add-ons to the weights, each trained on one country's six signs) and sign prompts (the same six signs written
// into the prompt; the weights do not change).
//   1. headline   how often each comparator gives one answer, against the base (dumbbell per row), exact from index.json
//   2. controls   question picker (routes through the app), show adapters / sign prompts, order by size / matched pairs
//   3. map        where in the model the change happens: change in contribution to the answer, by layer
// This view describes what the models do on these saved runs. It makes no claim about what a model "represents".
// Hooks kept for tests and the verifier: #answer, data-obj="answer" | "cohort" | "cohort-legend" | "dmargin", ctx.ready().
// Every string put into innerHTML below is either a literal or went through esc().

import { loadPair, type Bundle, type IndexFile, type Pair } from "./data";
import type { Ctx } from "./main";
import { C, diverging, esc, fmt } from "./common";
import {
  SIGNS, answerName, arrange, buildRows, change, loadItemInfo, pairSentence, pct, shortQuestion,
  type Block, type ItemInfo, type Row, type Show, type Sort,
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
      <section id="answer" data-obj="answer"><span class="say">One base model, many comparators: <b>who moves the answer, and where in the model</b></span></section>
      <div class="k-work">
        <section class="obj k-empty" data-obj="cohort-empty"><header><span class="cap">Cohort · not built from data yet</span></header>
          <p class="lead">This view puts one unchanged model next to several comparators on the same question. It needs at least ${MIN_ADAPTERS} comparators on one question.</p>
          <p class="muted">Today, for <b>${name(base)}</b> on <code>${esc(item)}</code>, the index lists ${plural(rows.length, "comparator")}: ${rows.map((r) => name(r.b)).join(", ") || "none"}. Nothing on this tab is data until a third one is exported.</p></section>
        <figure class="obj k-thumb" data-obj="illustration"><span class="illus">illustration · not data</span>
          <img src="/screens/v3/cohort-illustration.png" alt="Design mockup of the cohort map: 42 placeholder adapters by 32 layers, not data" width="560" height="262" />
          <figcaption class="foot">Design mockup: seeded placeholder values for an 8-billion-parameter base with 42 adapters. Not a measurement.</figcaption></figure>
      </div>`;
    requestAnimationFrame(() => ctx.ready());
    return off;
  }

  document.querySelector("#frame .illus")?.remove();   // the frame's "no data yet" badge is for the empty state only

  // ---------------------------------------------------------------- state: the URL keys `show` and `sort`
  const showOf = (): Show => { const v = ctx.get("show"); return v === "adapter" || v === "prompt" ? v : "both"; };
  const sortOf = (): Sort => (ctx.get("sort") === "size" ? "size" : "pair");

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

  Promise.all([infosP, signsP]).then(([infos, bitsOf]) => {
    if (!alive) return;
    const info = new Map<string, ItemInfo>(infos.map((i) => [i.item_id, i]));
    const cur = info.get(item);
    if (!cur) throw new Error(`no question wording for ${item}`);
    const rows: Row[] = buildRows(index, base, item, cur, bitsOf);
    const enough = rows.length >= MIN_ADAPTERS;
    const kinds = { adapter: rows.filter((r) => r.who.kind === "adapter").length, prompt: rows.filter((r) => r.who.kind === "prompt").length };
    const ladder = (b: string, it = item) => `a=${encodeURIComponent(base)}&b=${encodeURIComponent(b)}&item=${encodeURIComponent(it)}`;
    // Switching question keeps the current comparator when it also has a pair on the new question.
    const bFor = (it: string) => { const ps = itemsOf(it); return (ps.find((p) => p.b === D.B.m.model.key) ?? ps[0]).b; };
    const lays = new Map<string, number[]>();   // filled when the pair files arrive
    const ans = (code: string) => answerName(cur, code);
    const plus = ans(cur.j_plus), minus = ans(cur.j_minus);

    const dots = (bits?: string) => bits ? `<span class="k-dots" title="${esc(SIGNS.map((s, i) => `${s}: ${bits[i] === "1" ? "positive" : "negative"}`).join(" · "))}" aria-hidden="true">${[...bits].map((c) => `<i class="${c === "1" ? "p" : "n"}"></i>`).join("")}<code>${esc(bits)}</code></span>` : "";
    const who = (r: Row) => (r.who.kind === "adapter" ? `${r.who.name} adapter` : r.who.kind === "prompt" ? `Sign prompt ${r.bits ?? ""}`.trim() : r.who.name);
    const rowTip = (r: Row) => `${who(r)}: ${pct(r.pCmp)} give ${plus} (base model ${pct(r.pBase)}). Change from the base in the log-odds of ${plus} over ${minus}: ${change(r.d)}.`;
    const label = (r: Row) => r.who.kind === "adapter"
      ? `<span class="k-nm"><b>${esc(r.who.name)}</b><em>country adapter</em></span>${dots(r.bits)}`
      : r.who.kind === "prompt" ? `<span class="k-nm"><b>Sign prompt</b><em>weights unchanged</em></span>${dots(r.bits)}`
      : `<span class="k-nm"><b>${esc(r.who.name)}</b></span>`;
    const go = (r: Row) => `data-go="c" data-extra="${esc(ladder(r.who.b))}"`;
    const twins = (r: Row) => (r.bits ? rows.filter((o) => o !== r && o.bits === r.bits && o.who.kind !== r.who.kind && o.who.kind !== "other") : []);
    const sameSigns = (r: Row, blk: Block) => (!blk.matched && twins(r).length
      ? `<span class="k-same" title="Another comparator on this question carries the same six signs. Order by matched pairs to see them side by side.">same signs as ${esc(twins(r).map((o) => (o.who.kind === "adapter" ? o.who.name + " adapter" : "the sign prompt")).join(", "))}</span>` : "");

    // ---- the dumbbell: base (open ring) to comparator (filled dot), on a fixed 0 to 100% axis
    const dumbbell = (r: Row) => {
      if (r.pBase == null || r.pCmp == null) return `<div class="k-db muted">probabilities not in the index</div>`;
      const b = r.pBase * 100, c = r.pCmp * 100, lo = Math.min(b, c), w = Math.abs(c - b);
      return `<div class="k-db" aria-hidden="true"><i class="k-bl" style="left:${b}%"></i>${w >= 1 ? `<i class="k-arrow ${c >= b ? "r" : "l"}${w < 5 ? " short" : ""}" style="left:${lo}%;width:${w}%"></i>` : ""}<i class="k-mb" style="left:${b}%"></i><i class="k-mc" style="left:${c}%"></i></div>`;
    };
    const topName = (code: string) => ans(code).replace(/^answer /, "");
    const rowHtml = (r: Row, blk: Block) => {
      const tb = r.topBase, tc = r.topCmp;
      const likely = tb && tc ? `<span class="k-top">Most likely answer: ${esc(topName(tb.code))} (${pct(tb.p)}) → ${esc(topName(tc.code))} (${pct(tc.p)})</span>` : "";
      const t = rowTip(r);
      return `<div class="k-row" tabindex="0" role="group" data-b="${esc(r.who.b)}" data-tip="${esc(t)}" aria-label="${esc(t + " Press Enter to open this pair in the Ladder.")}" ${go(r)}>
        <div class="k-who">${label(r)}${sameSigns(r, blk)}</div>
        <div class="k-mid">${dumbbell(r)}${likely}</div>
        <div class="k-pc"><b>${pct(r.pBase)}</b> <span aria-hidden="true">→</span> <b class="c">${pct(r.pCmp)}</b></div>
        <div class="k-d num" title="Change from the base, in log-odds of ${esc(plus)} over ${esc(minus)}">${change(r.d)}</div>
        <a class="k-open" href="?tab=c&${esc(ladder(r.who.b))}" ${go(r)} tabindex="-1">Open in the Ladder →</a></div>`;
    };
    const axis = `<div class="k-row k-axis" aria-hidden="true"><div class="k-who"></div><div class="k-mid"><div class="k-ticks">${[0, 25, 50, 75, 100].map((t) => `<span style="left:${t}%">${t}%</span>`).join("")}</div></div><div class="k-pc">base → comparator</div><div class="k-d" title="Change from the base, in log-odds">log-odds change</div><div class="k-open"></div></div>`;

    // ---- the layer map: one row per comparator, one square per layer
    const L = D.A.m.model.n_layers;
    const mapRowHtml = (r: Row, m: number) => {
      const v = lays.get(r.who.b);
      let best = -1; if (v) v.forEach((x, l) => { if (best < 0 || Math.abs(x) > Math.abs(v[best])) best = l; });
      const cells = v ? v.map((x, l) => `<i data-tip="${esc(`${who(r)} · layer ${l}: contribution to the answer changes by ${change(x)} (${x >= 0 ? "toward " + plus : "toward " + minus}). Attention and MLP block together.`)}" style="background:${diverging(x, m)}"></i>`).join("") : `<span class="muted">loading…</span>`;
      const aria = `${who(r)}.${v ? ` Largest change at layer ${best}: ${change(v[best])}.` : ""} Press Enter to open this pair in the Ladder.`;
      return `<div class="k-hrow" tabindex="0" role="group" data-b="${esc(r.who.b)}" aria-label="${esc(aria)}" ${go(r)}>
        <div class="k-who">${label(r)}</div><div class="k-cells" style="--L:${L}">${cells}</div></div>`;
    };
    const mapHtml = (blocks: Block[]) => {
      const flat = blocks.flatMap((b) => b.rows);
      const all = [...lays.values()].flat(), m = all.length ? Math.max(...all.map(Math.abs)) || 1 : 1;
      const grad = [-1, -0.5, -0.25, 0, 0.25, 0.5, 1].map((s) => `${diverging(s * m, m)} ${((s + 1) * 50).toFixed(0)}%`).join(",");
      return `<header><span class="cap">Where in the model the change happens</span></header>
        <p class="k-sub">Layer 0 reads the question. Layer 31 writes the answer. Each square is one layer: how much that layer's contribution to the answer changes, comparator minus base. Hover a square for the number. Click a row to open that pair in the Ladder.</p>
        <div class="k-hrow k-haxis" aria-hidden="true"><div class="k-who">layer →</div><div class="k-cells k-lay">${[0, 5, 10, 15, 20, 25, L - 1].map((l) => `<span style="left:${((l + 0.5) / L) * 100}%">${l}</span>`).join("")}</div></div>
        <div id="kmap">${flat.map((r) => mapRowHtml(r, m)).join("") || `<p class="muted">No rows match this filter.</p>`}</div>
        <div class="k-key"><span class="bar" style="background:linear-gradient(90deg,${grad})"></span><span><b style="color:${C.pos}">Blue</b>: pushes toward ${esc(plus)}. <b style="color:${C.neg}">Orange</b>: pushes toward ${esc(minus)}. Grey: about zero. Deepest colour ±${fmt(m, 3)} (square-root scale; nothing is clipped).</span></div>`;
    };

    const thinMsg = !enough ? `<p class="k-thinnote" data-obj="cohort-thin"><b>Only ${plural(rows.length, "comparator")} on this question.</b> That is too few to compare, so the layer map is not drawn. The saved answers are shown as they are. Pick a question with ${MIN_ADAPTERS} or more above, or open a pair in the Ladder.</p>` : "";

    // ---- the page
    const known = rows.filter((r) => r.pCmp != null), lo = Math.min(...known.map((r) => r.pCmp!)), hi = Math.max(...known.map((r) => r.pCmp!));
    const sentence = `Unchanged model: <b>${pct(rows[0]?.pBase)}</b> say ${esc(plus)} on “${esc(shortQuestion(item, cur.text))}”. Across the ${plural(rows.length, "comparator")} below, that share goes from <b>${pct(lo)}</b> to <b>${pct(hi)}</b>.`;
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
        <p class="k-q" data-obj="cohort-question"><span class="muted">${esc(cur.item_id)} · </span>“${esc(cur.text)}”<br><span class="muted">Answer followed: ${esc(plus)}. Log-odds compare ${esc(plus)} with ${esc(minus)}${cur.codes.length > 2 ? ". The other answers are left out of that comparison, so the log-odds can rise while this answer's own share falls. The “Most likely answer” line under each row shows where the probability went" : ""}.</span></p>
      </section>
      ${thinMsg}
      <section class="obj k-head" data-obj="dmargin"><header><span class="cap">How often each model gives this answer</span><span class="k-legend" aria-hidden="true"><i class="k-mb"></i> base model <i class="k-mc"></i> comparator</span></header>
        <div class="k-ctl2"><span class="k-ctl"><span class="cap">Show</span><span id="kshow"></span></span><span class="k-ctl"><span class="cap">Order by</span><span id="ksort"></span></span></div>
        <div id="krows"></div></section>
      ${enough ? `<section class="obj k-map" data-obj="cohort" id="kmapsec"></section>` : ""}
      <details class="k-more" data-obj="cohort-legend"><summary>What do these words mean?</summary>
        <dl>
          <dt>Base model</dt><dd>The unchanged Llama-3.1-8B-Instruct, a large language model.</dd>
          <dt>Country adapter</dt><dd>A small add-on to the weights, trained on one country's six signs. (Technical name: LoRA adapter.)</dd>
          <dt>Sign prompt</dt><dd>The same six signs written into the prompt. The weights do not change. The six signs are trust, risk taking, patience, altruism, positive reciprocity and negative reciprocity. Each is positive (filled dot, 1) or negative (open dot, 0).</dd>
          <dt>Log-odds of “A” over “B”</dt><dd>The log of how much more likely the model is to answer A than B, as in a logit. (Technical name: margin.) The change from the base is the comparator's value minus the base's.</dd>
          <dt>Layer</dt><dd>One of 32 processing steps the model runs in order.</dd>
          <dt>Contribution to the answer</dt><dd>How much a layer pushes the log-odds toward one answer or the other. (Technical name: direct logit attribution.) Each square adds two parts: <b>attention</b>, which reads earlier words, and the <b>MLP block</b>, which transforms what was read.</dd>
        </dl>
        <p class="muted">This view describes what the models do on these saved runs. It does not show that a model represents a country.</p></details>`;

    // ---- drawing, repeated when a filter changes
    const draw = () => {
      const show = showOf(), sort = sortOf(), blocks = arrange(rows, show, sort);
      const cnt = (n: number) => (n ? ` <span class="n">${n}</span>` : "");
      root.querySelector("#kshow")!.innerHTML = seg("show", [["both", `Both${cnt(rows.length)}`], ["adapter", `Country adapters${cnt(kinds.adapter)}`], ["prompt", `Sign prompts${cnt(kinds.prompt)}`]], show);
      root.querySelector("#ksort")!.innerHTML = seg("sort", [["pair", "Matched pairs", "Put a country adapter and a sign prompt with the same six signs side by side"], ["size", "Size of change", "Largest change from the base first, up or down"]], sort);
      const body = blocks.map((b) => b.matched
        ? `<div class="k-group" role="group" aria-label="Same six signs"><div class="k-gb" aria-hidden="true"></div>${b.rows.map((r) => rowHtml(r, b)).join("")}<p class="k-pair">${esc(pairSentence(b, cur))}</p></div>`
        : b.rows.map((r) => rowHtml(r, b)).join("")).join("");
      root.querySelector("#krows")!.innerHTML = blocks.length ? axis + body : `<p class="muted">No comparator of this kind on this question.</p>`;
      const ms = root.querySelector("#kmapsec"); if (ms) ms.innerHTML = mapHtml(blocks);
    };
    draw();

    // ---- events: filters, tooltip, hover link between the two lists, Enter on a row
    root.addEventListener("click", (e) => {
      const t = e.target as HTMLElement, s = t.closest<HTMLElement>("[data-show]"), o = t.closest<HTMLElement>("[data-sort]");
      if (s) { const v = s.dataset.show!; ctx.set("show", v === "both" ? null : v); draw(); root.querySelector<HTMLElement>(`[data-show="${v}"]`)?.focus(); }
      if (o) { const v = o.dataset.sort!; ctx.set("sort", v === "pair" ? null : v); draw(); root.querySelector<HTMLElement>(`[data-sort="${v}"]`)?.focus(); }
    });
    root.addEventListener("keydown", (e) => {
      const r = (e.target as HTMLElement).closest<HTMLElement>(".k-row[data-go], .k-hrow[data-go]");
      if (r && e.target === r && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); r.click(); }
    });
    const hl = (b: string | null) => root.querySelectorAll<HTMLElement>("[data-b]").forEach((el) => el.classList.toggle("hl", b != null && el.dataset.b === b));
    const place = (x: number, y: number) => { tip.style.left = Math.max(8, Math.min(x + 14, innerWidth - 360)) + "px"; tip.style.top = Math.max(8, Math.min(y + 16, innerHeight - 100)) + "px"; };
    root.addEventListener("pointermove", (e) => {
      const el = e.target as HTMLElement, t = el.closest<HTMLElement>("[data-tip]");
      hl(el.closest<HTMLElement>("[data-b]")?.dataset.b ?? null);
      if (!t) { tip.hidden = true; return; }
      tip.textContent = t.dataset.tip!; tip.hidden = false; place(e.clientX, e.clientY);
    });
    root.addEventListener("pointerleave", () => { tip.hidden = true; hl(null); });
    root.addEventListener("focusin", (e) => {
      const r = (e.target as HTMLElement).closest<HTMLElement>("[data-b]"); hl(r?.dataset.b ?? null);
      if (!r?.dataset.tip) { tip.hidden = true; return; }
      const b = r.getBoundingClientRect(); tip.textContent = r.dataset.tip; tip.hidden = false; place(b.left + 200, b.bottom - 8);
    });
    root.addEventListener("focusout", () => { tip.hidden = true; hl(null); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") tip.hidden = true; }, { signal: ctx.signal });

    // ---- layer data: one pair file per row (only its layer arrays are read)
    if (!enough) { ctx.ready(); return; }
    return Promise.all(rows.map((r) => loadPair(r.file).then((P: Pair) => ({ r, P })))).then((got) => {
      if (!alive) return;
      for (const { r, P } of got) {
        if (!P.t.d_attn_attr || !P.t.d_mlp_attr) continue;
        lays.set(r.who.b, Array.from({ length: L }, (_, l) => P.t.d_attn_attr.get(l) + P.t.d_mlp_attr.get(l)));
      }
      draw();
      ctx.ready();
    });
  }).catch((e) => {
    if (!alive) return;
    (window as any).__ready = "error: " + String(e);
    root.querySelector(".k-wrap")!.innerHTML = `<p class="loadfail" role="alert">The Cohort view could not be drawn: ${esc(String(e))}</p>`;
  });
  return off;
}
