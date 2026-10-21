// Tab K, Cohort (v3). One base against N adapters on one item: one row per adapter, its change in push on the
// margin by layer (adapter − base: pair d_attn_attr + d_mlp_attr), rows sorted by d_margin, with a d_margin
// column. The real app shows no fake data: this map is drawn only when index.json lists at least three pairs
// that share the base (slot A) and the item, each with d_attn_attr and d_mlp_attr. Otherwise the tab is an
// honest empty state: what the view will show, the export it needs, and one small thumbnail of the design
// mockup, badged "illustration · not data" (the frame carries the same badge, rule 6).

import { loadPair, type Bundle, type IndexFile, type Pair } from "./data";
import type { Ctx } from "./main";
import { C, diverging, esc, fmt, sgn } from "./common";

const MIN_ADAPTERS = 3;

export function mountCohort(root: HTMLElement, D: Bundle, ctx: Ctx): () => void {
  const index = (window as any).__index as IndexFile;
  const a = D.A.m.model.key ?? "", item = D.A.m.item.item_id;
  const base = index.pairs.find((p) => p.file === `pair__${a}__${D.B.m.model.key}__${item}.json`)?.a ?? a;
  const rows = index.pairs.filter((p) => p.a === base && p.item_id === item);
  const name = (k: string) => esc(index.models[k]?.label ?? k);
  // Short row names: "CAN adapter" / "sign prompt 111111". Long labels were clipped at the same prefix, so an
  // adapter and a sign prompt on the same base could not be told apart.
  const kindOf = (k: string): { short: string; kind: "adapter" | "prompt" | "other"; cc?: string; bits?: string } => {
    const l = index.models[k]?.label ?? k;
    const ad = l.match(/\+ ([A-Z]{3}) LoRA/); if (ad) return { short: `${ad[1]} adapter`, kind: "adapter", cc: ad[1] };
    const sp = l.match(/sign prompt ([01](?:_[01]){5})/); if (sp) { const bits = sp[1].replace(/_/g, ""); return { short: `sign prompt ${bits}`, kind: "prompt", bits }; }
    return { short: l, kind: "other" };
  };
  root.className = "tab-k v3";
  let alive = true;

  if (rows.length < MIN_ADAPTERS) {
    root.innerHTML = `
      <section id="answer" data-obj="answer"><span class="say">One base, many adapters: <b>who moves the answer, and in which layers</b></span></section>
      <div class="k-work">
        <section class="obj k-empty" data-obj="cohort-empty"><header><span class="cap">Cohort · not built from data yet</span></header>
          <p class="lead">This view will put one base model against N adapters on the same item: one row per adapter, its change in push on the margin layer by layer (adapter − base), with the rows sorted by d_margin.</p>
          <p><b>It needs</b> one pair export per (base, adapter) on the same item, each carrying <code>d_attn_attr</code> and <code>d_mlp_attr</code> (capture@1.1), for at least ${MIN_ADAPTERS} adapters.</p>
          <p class="muted">Today, for <b>${name(base)}</b> on <code>${esc(item)}</code>, <code>index.json</code> lists ${rows.length} adapter${rows.length === 1 ? "" : "s"}: ${rows.map((r) => name(r.b)).join(", ") || "none"}. The map is drawn here as soon as a third pair with the same base and item is exported. Nothing on this tab is data until then.</p></section>
        <figure class="obj k-thumb" data-obj="illustration"><span class="illus">illustration · not data</span>
          <img src="/screens/v3/cohort-illustration.png" alt="Design mockup of the cohort map: 42 placeholder adapters by 32 layers, not data" width="560" height="262" />
          <figcaption class="foot">Design mockup (design/layout-v3, scale-cohort): seeded placeholder values and a placeholder country list for an 8B base with 42 adapters. Not a measurement.</figcaption></figure>
      </div>`;
    requestAnimationFrame(() => ctx.ready());
    return () => { alive = false; };
  }

  // ---------------- the real map (≥ 3 adapters share the base and the item)
  document.querySelector("#frame .illus")?.remove();
  const nAd = rows.filter((r) => kindOf(r.b).kind === "adapter").length, nSp = rows.filter((r) => kindOf(r.b).kind === "prompt").length;
  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? "" : "s"}`;
  const who = [nAd ? plural(nAd, "adapter") : "", nSp ? plural(nSp, "sign prompt") : "", rows.length - nAd - nSp ? plural(rows.length - nAd - nSp, "other model") : ""].filter(Boolean).join(" and ");
  root.innerHTML = `
    <section id="answer" data-obj="answer"><span class="say">${name(base)} vs ${who} on <code>${esc(item)}</code>: <b>who moves the answer, and in which layers</b></span></section>
    <div class="k-work real"><section class="obj" data-obj="cohort"><header><span class="cap">Change in push by layer · adapter − base · rows sorted by d_margin</span></header><div id="kmap"></div><div class="foot" id="kfoot"></div>${nSp ? `<p class="klegend" data-obj="cohort-legend">An <b>adapter</b> learns a country's six preference signs (trust, risk taking, patience, altruism, positive and negative reciprocity) in its weights. A <b>sign prompt</b> gives the unchanged base model the same six signs in words. Rows marked “= CAN's signs” carry exactly that adapter's profile, so the pair compares weights with words on the same information.</p>` : ""}</section>
      <section class="obj" data-obj="dmargin"><header><span class="cap">d_margin · adapter − base</span></header><div id="kdm"></div></section></div>`;
  // Country → six signs, from the story data shipped in the same bundle; optional, rows still draw without it.
  const signs = fetch("/sca2/sca2_data.json").then((r) => (r.ok ? r.json() : null)).then((d) => {
    const m = new Map<string, string>(); for (const c of d?.countries ?? []) if (c?.cc && Array.isArray(c.bits)) m.set(c.cc, c.bits.join("")); return m;
  }).catch(() => new Map<string, string>());
  Promise.all([Promise.all(rows.map((r) => loadPair(r.file).then((P) => ({ r, P })))), signs]).then(([got, bitsOf]) => {
    if (!alive) return;
    const ok = got.filter(({ P }) => P.t.d_attn_attr && P.t.d_mlp_attr) as { r: (typeof rows)[number]; P: Pair }[];
    const L = D.A.m.model.n_layers;
    const data = ok.map(({ r, P }) => ({ b: r.b, d: P.m.d_margin, lay: Array.from({ length: L }, (_, l) => P.t.d_attn_attr.get(l) + P.t.d_mlp_attr.get(l)) })).sort((x, y) => y.d - x.d);
    const host = root.querySelector<HTMLElement>("#kmap")!, W = host.clientWidth, rh = Math.min(28, Math.max(10, (innerHeight - 360) / data.length)), lab = 220, cw = (W - lab) / L;
    const m = Math.max(...data.flatMap((x) => x.lay.map(Math.abs))) || 1, md = Math.max(...data.map((x) => Math.abs(x.d))) || 1;
    let o = "";
    const shown = new Map<string, string>(); for (const x of data) { const k = kindOf(x.b); if (k.kind === "adapter" && k.cc && bitsOf.get(k.cc)) shown.set(bitsOf.get(k.cc)!, k.cc); }
    const rowName = (b: string) => { const k = kindOf(b);
      if (k.kind === "adapter") { const bits = k.cc ? bitsOf.get(k.cc) : undefined; return esc(k.short) + (bits ? ` <tspan fill="#8a8a8a">· signs ${bits}</tspan>` : ""); }
      if (k.kind === "prompt") { const cc = shown.get(k.bits!); return esc(k.short) + (cc ? ` <tspan fill="#8a8a8a">= ${esc(cc)}'s signs</tspan>` : ""); }
      return name(b); };
    data.forEach((x, i) => { o += `<text x="0" y="${i * rh + rh * 0.7}"><title>${name(x.b)}</title>${rowName(x.b)}</text>`; x.lay.forEach((v, l) => (o += `<rect x="${lab + l * cw}" y="${i * rh}" width="${cw - 1}" height="${rh - 1}" fill="${diverging(v, m)}"><title>${name(x.b)} · layer ${l}: ${sgn(v)}</title></rect>`)); });
    for (let l = 0; l < L; l += 5) o += `<text x="${lab + l * cw}" y="${data.length * rh + 14}">L${l}</text>`;
    host.innerHTML = `<svg width="${W}" height="${data.length * rh + 20}">${o}</svg>`;
    root.querySelector("#kfoot")!.innerHTML = `pair <code>d_attn_attr + d_mlp_attr</code> · ±${fmt(m, 3)}, square-root scale · blue toward “${esc(D.A.m.item.j_plus)}”, orange toward “${esc(D.A.m.item.j_minus)}”`;
    const dh = root.querySelector<HTMLElement>("#kdm")!, W2 = dh.clientWidth; let o2 = `<line x1="${W2 / 2}" x2="${W2 / 2}" y1="0" y2="${data.length * rh}" stroke="#555"/>`;
    data.forEach((x, i) => { const w = (W2 / 2 - 44) * Math.abs(x.d) / md, x0 = x.d >= 0 ? W2 / 2 : W2 / 2 - w;
      o2 += `<rect x="${x0}" y="${i * rh + 1}" width="${w}" height="${rh - 2}" fill="${C.delta}"><title>${sgn(x.d)}</title></rect>`;
      o2 += `<text x="${x.d >= 0 ? x0 + w + 4 : x0 - 4}" y="${i * rh + rh * 0.7}" text-anchor="${x.d >= 0 ? "start" : "end"}" fill="#d8d8d8" font-size="12">${sgn(x.d, 3)}</text>`; });
    dh.innerHTML = `<svg width="${W2}" height="${data.length * rh}">${o2}</svg>`;
    ctx.ready();
  }).catch((e) => { (window as any).__ready = "error: " + String(e); });
  return () => { alive = false; };
}
