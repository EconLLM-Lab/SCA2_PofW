// Landing page (the entry point; "Open the workbench" leads to the ladder tab).
// Every figure badged "real data" is drawn here from the exports of the current pair and prompt.
// Copy: design/layout-v2/COPY.md L01–L37 with the PM rulings (K2, K10, K11, K24; DPO training data).

import type { Bundle } from "./data";
import { A_COL, B_COL, C, dAttr, esc, isBank, labelPlus, learnText, lm, makeRamp, mix, rampU, roleOf, segmentsOf, sgn, short } from "./common";
import { TEACHING } from "./main";

export function mountLanding(app: HTMLElement, D: Bundle, nav: { go: (t: import("./main").Tab | null, extra?: Record<string, string>) => void }): () => void {
  void nav;
  const L = D.A.m.model.n_layers, T = D.A.m.tokens.length, it = D.A.m.item, bank = isBank(D.A);
  const adapter = !!D.B.m.model.adapter;
  const nameA = roleOf(D, "A") ? "A · base" : `A · ${short(D.A.m.model.label, 18)}`;
  const nameB = roleOf(D, "B") ? "B · with adapter" : `B · ${short(D.B.m.model.label, 18)}`;
  const lp = labelPlus(D.A);
  // Model facts for the copy, all read from the run manifest (never typed): the Paper B base or the teaching model.
  const M = D.A.m.model as typeof D.A.m.model & { d_model?: number; d_ffn?: number; n_heads: number };
  const H = M.n_heads, dModel = M.d_model ?? 0, dFfn = M.d_ffn ?? 0, n = (v: number) => v.toLocaleString("en-US");
  const teach = (M.key ?? "").startsWith("smol");
  const modelName = esc(M.label.split(" [")[0]);
  const nf4 = /nf4_dequant/.test(M.key ?? "");
  const adB = D.B.m.model.adapter as unknown as { country?: string; r?: number; target_modules?: string[] } | string | null;
  const ccB = adB && typeof adB === "object" ? adB.country : undefined;
  const spB = D.B.m.model.label.match(/sign prompt ([01](?:_[01]){5})/)?.[1]?.replace(/_/g, "");
  const teachHref = `?a=${TEACHING.a}&b=${TEACHING.b}&item=${TEACHING.item}`;
  app.innerHTML = `<div class="wrap">
<nav class="lnav" data-obj="nav"><span class="brand" title="SCA2 = Synthetic Cultural Agents from Aggregate Anchors">SCA2 workbench</span><span class="sp"></span><a href="/sca2/index.html">Paper B story</a><a href="#s1">How it works</a><a href="#s4">Limits</a><a href="#" data-learn="terms">Glossary</a><a class="open" href="#" data-go="c">Open the workbench →</a></nav>
<div class="hero3">
  <div class="hl">
    <h1 data-obj="h1">Where does a language model's <em>survey answer</em> come from?</h1>
    <div data-obj="lede"><p class="lede">We ask a language model a ${bank ? "question about an everyday scenario" : "survey question"}. Its answer is a probability for each response code. We split that answer into the contributions of the model's parts, check that the parts add up to the total, and compare the base model with a changed version (a country adapter, or a sign prompt), part by part.</p>
    <p class="small2">${teach ? `This page is showing the <b>teaching example</b>: ${modelName}, a small model from the development stage, chosen so every number can be checked quickly. <a href="?" class="u">Show the Paper B model instead</a>.` : `Model here: <b>${modelName}</b>, the base model of the Paper B country adapters${ccB ? `, compared with its <b>${esc(ccB)}</b> country adapter` : spB ? `, compared with the same model with the sign prompt ${spB} (the six signs written into the prompt, one yes-or-no mark for each; the weights do not change)` : ""}. <a href="${teachHref}" class="u">Teaching example on a small model</a>.`}</p>
    <p class="small2">For readers who know regression and survey items. No machine-learning background assumed. SCA2 is <i>Synthetic Cultural Agents from Aggregate Anchors</i> (arXiv:2610.06562). Every technical term is explained in the <a href="#" data-learn="terms" class="u">glossary</a>.</p></div>
    <div class="cta3" data-obj="cta"><a class="p" href="#" data-go="c">Open the workbench</a><a href="/sca2/index.html">Read the Paper B story</a><a href="#s1">How it works ↓</a></div>
  </div>
  <figure class="hf" data-obj="hero"><div class="cap">The log-odds, layer by layer · real data</div><svg id="hero" viewBox="0 0 560 330" width="100%"></svg><figcaption id="heroCap"></figcaption></figure>
</div>

<section class="s" id="s1"><div class="sn"><b>1</b>what is inside the model</div><div>
  <h2>A running total, written to by many small parts</h2>
  <div class="prose">
    <p>The model cuts the prompt into tokens (word pieces). Each token gets a list of ${n(dModel)} numbers. We call that list the <b>running state</b> (the technical name is the residual stream). Every layer reads it and adds to it. Nothing is overwritten, like a ledger where each layer posts new entries. This model has ${L} layers, which are processing steps that run one after the other.</p>
    <p>Each layer adds two kinds of entries. <b>Attention heads</b> (${H} per layer) let a token look back at earlier tokens: each head picks which earlier words to read from and adds a summary. The <b>MLP block</b> (a small neural network with ${n(dFfn)} hidden units per layer) then transforms each token on its own. After the last layer, the final state at the last position is turned into a score for every possible next token.</p>
    <p>Because everything is added, the final score can be split into the parts that added to it. The split is exact for the log-odds when the model's final rescaling is held fixed (see section 2). That is the property the whole workbench rests on.</p>
  </div>
  <div class="cols">
    <figure class="fig"><span class="badge ill">illustration · not data</span><svg id="ill" viewBox="0 0 470 300" width="100%"></svg>
      <figcaption>Schematic of one token's path. Three of ${L} layers drawn; head count and widths are not to scale. No mark here is a measurement.</figcaption></figure>
    <figure class="fig"><span class="badge data" title="resid_norm">real data · size of the running state at every token and layer</span><canvas id="heat" style="width:100%;height:230px"></canvas>
      <figcaption id="heatCap"></figcaption></figure>
  </div>
</div></section>

<section class="s" id="s2"><div class="sn"><b>2</b>what we measure</div><div>
  <h2>One number, split into parts that add up</h2>
  <div class="prose">
    <p><b>The answer.</b> At the answer position the model gives a score to every possible next token. We keep only the scores for the response codes and turn them into probabilities. This is the same form as a multinomial logit: the scores play the part of the linear index, and the probabilities are the choice shares. (This is Eq. 6 of the SCA2 paper (arXiv:2610.06562).) The <b>log-odds</b> of one code over another (called the <b>margin</b> in the code) is the gap between the scores of the two codes. It equals the log of their odds, and positive means the model leans toward the first.</p>
    <div class="eq">P(code j | prompt) = exp(z<sub>j</sub>) / Σ<sub>k ∈ codes</sub> exp(z<sub>k</sub>)        log-odds (margin) = z<sub>j₊</sub> − z<sub>j₋</sub></div>
    <p class="eqnote">z is the model's raw score for a code. The probability is that code's share of exp(score) among the response codes. j₊ and j₋ are the two codes we compare.</p>
    <p><b>The split.</b> We give each part its <b>contribution to the answer</b>: its share of the log-odds, like splitting a logit index into its β·x terms. (The technical name is direct logit attribution, DLA.) Each part's entry is read straight through the model's last steps, with the final rescaling held fixed. Then the log-odds is the sum of one embedding term (the starting vector of the words), ${n(L * H)} attention-head terms and ${n(L * dFfn)} neuron terms, with nothing left over. This is the direct effect only: a part that changes what a later layer does gets no credit for that path (see Limits).</p>
    <p><b>The accounting checks.</b> Every run uses 64-bit arithmetic (float64)${nf4 ? ", on the compressed 4-bit (NF4) weights the adapters were trained on, expanded back to full precision (dequantized)" : ""}. A run must pass these checks before it is shown: the parts add up to the final running state and to the log-odds, and our code gives the same numbers as the Hugging Face reference implementation. If a check fails, the check mark in the top bar turns into a red banner that cannot be dismissed. The tolerances and this run's values are in the table below.</p>
    <p><b>Base and changed model.</b> The same prompt goes through two models. A is the <b>base model</b>, ${esc(D.A.m.model.label)}. B is ${esc(D.B.m.model.label)}${ccB && adB && typeof adB === "object" ? `: A plus a <b>country adapter</b>, a small add-on to the weights (a rank-${adB.r ?? "?"} LoRA adapter on the attention weights) for ${esc(ccB)}. It was trained, with direct preference optimization (DPO), on synthetic everyday scenarios labelled with ${esc(ccB)}'s six preference signs from the Global Preferences Survey (trust, risk taking, patience, altruism, positive and negative reciprocity). The cohort has one such adapter per country, 42 in all` : adapter ? ": A plus a <b>country adapter</b>, a small add-on to the weights (a LoRA adapter) trained with direct preference optimization (DPO) on made-up everyday scenarios, preferring the answer that matches the USA's direction on the Global Preferences Survey (for example, more trusting, more patient)" : spB ? `: the same weights as A, with a <b>sign prompt</b>: the six signs ${spB} written into the prompt. The weights do not change` : ""}. For every layer and token, we store the size of the change, which is how far B's running state is from A's. We also store how far the weights moved.</p>
  </div>
  <p class="prose story" id="s2b"></p>
  <div class="cols">
    <figure class="fig"><span class="badge data" title="readout.probs, readout.probs_clamped">real data · the model's answer probabilities</span><div id="probs"></div><figcaption id="probCap"></figcaption></figure>
    <figure class="fig"><span class="badge data">real data · which layers changed the log-odds</span><svg id="wf" viewBox="0 0 470 250" width="100%"></svg><figcaption id="wfCap"></figcaption></figure>
  </div>
  <div class="fig" style="margin-top:22px"><span class="badge data">real data · do the parts add up? (A and B)</span><div id="cons"></div></div>
</div></section>

<section class="s" id="s3"><div class="sn"><b>3</b>the four views</div><div>
  <h2>Four views of the same model run</h2>
  <div class="prose"><p>All four views draw the same saved numbers. Pick by the question you have. <b>Which parts decided the answer?</b> Start with the ladder. <b>Where, in the prompt and across the layers, did the adapter or sign prompt change things?</b> Use the matrix. <b>What does the whole run look like?</b> Use the 3D object. <b>Do weights and words move the answer alike?</b> Use Cohort: one base against several adapters and sign prompts on the same item. Hover anything to compare A and B.</p></div>
  <div class="shots">
    <a href="#" data-go="c"><img src="/screens/v4/ladder-1440.png" alt="the ladder"><h3>The ladder</h3><p>Every attention head and MLP block at the answer position, one face at a time (the change B − A by default; A and B one click away). Each face adds up to its log-odds. Gold rings mark the five largest changes.</p></a>
    <a href="#" data-go="b"><img src="/screens/v4/matrix-1440.png" alt="the matrix"><h3>The matrix</h3><p>One layer-by-token map of what attention adds, showing the size of the change ‖B − A‖ by default, with the log-odds by layer on the same rows. Template text is squeezed, not dropped.</p></a>
    <a href="#" data-go="a"><img src="/screens/v4/object-1440.png" alt="the 3D object"><h3>The 3D object</h3><p>The whole run as 3D blocks (token by layer by size): A next to the size of the change ‖B − A‖, with the log-odds by layer between them and a prompt map below.</p></a>
    <a href="#" data-go="k"><img src="/screens/v4/cohort-1440.png" alt="the cohort view"><h3>Cohort</h3><p>One base against every exported adapter and sign prompt on the same item, layer by layer, sorted by how far each moves the log-odds.</p></a>
  </div>
  <p class="muted small">Thumbnails are screenshots of this app (viewer/screens/v4) at the default pair and prompt.</p>
</div></section>

<section class="s" id="s4"><div class="sn"><b>4</b>limits</div><div>
  <h2>What this does not show</h2>
  <div class="lim">
    <div><b>Direct effect only</b>The contribution to the answer (DLA) credits each part for what it adds straight to the answer. A head that changes what a later layer does gets no credit for that indirect path. In regression terms, it is a direct effect with the mediators held out. A large contribution does not show that the part causes the answer. That needs an experiment that changes the part and runs the model again (ablation or patching). The clamped run is the one such experiment here: it switches off the Quadrant III neurons and runs the model again (the purple ticks).</div>
    ${teach ? `<div><b>A 135M stand-in</b>SmolLM2-135M is a small model, chosen so that every run can be done in float64 and checked. The paper's models are larger. Patterns here show the method. They are not findings about those larger models.</div>` : `<div><b>Re-run on a CPU, not the scoring run</b>These captures run the Paper B base model and adapters again on a CPU, in 64-bit arithmetic${nf4 ? ", from the compressed 4-bit (NF4) weights" : ""}. The Paper B scores came from separate GPU runs. The archive check in the top bar compares each capture with its archived score.</div>
    <div><b>Featured pairs only</b>The workbench includes a hand-picked set of adapter and sign-prompt pairs on a few items, not every country on every item. Nothing here is a cohort statistic; those are on the Paper B story page.</div>`}
    <div><b>Sizes hide direction</b>Block heights are the sizes (lengths) of vectors. Two additions of equal size can point in unrelated directions. Only the contributions to the answer, at the answer position, say which way a part pushes the answer.</div>
    <div><b>Only the top 16 attention weights are kept</b>For each head and token we keep the 16 largest attention weights. Attention lines and prompt shading use only those. The “share covered” figure says how much of the head's total attention they account for.</div>
    <div><b>One question at a time</b>Each view shows one prompt. Nothing here averages over questions, so nothing here is a statistic about a population.</div>
  </div>
</div></section>
<footer>SCA2 is <i>Synthetic Cultural Agents from Aggregate Anchors</i> (Paper A: arXiv:2610.06562). Paper B, the journal version in preparation, evaluates the method as a scoring instrument on a 42-country cohort; this workbench is its companion. Every figure marked “real data” is drawn in your browser from saved files in workbench/exports/ (format ${esc(D.A.m.schema ?? "sca2-workbench/capture@1")}; pair ${esc(D.A.m.model.key)} | ${esc(D.B.m.model.key)} · ${esc(it.item_id)}). Figures marked “illustration” use no data.
  <p class="foot-src"><b>Built with Llama.</b> Llama 3.1 is licensed under the Llama 3.1 Community License, Copyright © Meta Platforms, Inc. All Rights Reserved. <b>World Values Survey</b>: question wording and answer labels from Wave 7 (2017–2022), worldvaluessurvey.org; Haerpfer, C., Inglehart, R., Moreno, A., Welzel, C., Kizilova, K., Diez-Medrano J., M. Lagos, P. Norris, E. Ponarin &amp; B. Puranen et al. (eds.). 2020. World Values Survey: Round Seven – Country-Pooled Datafile. Madrid, Spain &amp; Vienna, Austria: JD Systems Institute &amp; WVSA Secretariat. doi.org/10.14281/18241.1. <b>Global Preferences Survey</b>: the six signs are derived from country-level data (gps.econ.uni-bonn.de), CC BY-NC-SA 4.0, no GPS values shipped; Falk, A., Becker, A., Dohmen, T., Enke, B., Huffman, D., &amp; Sunde, U. (2018). Global evidence on economic preferences. <i>Quarterly Journal of Economics</i>, 133(4), 1645–1692; Falk, A., Becker, A., Dohmen, T. J., Huffman, D., &amp; Sunde, U. (2016). The preference survey module. IZA Discussion Paper No. 9674.</p></footer>
</div>`;
  const $ = (id: string) => app.querySelector<HTMLElement>("#" + id)!;

  // HERO: running_margin (h^l_{t*}·w) per layer for A and B — the answer forming, layer by layer
  {
    const W = 560, Hh = 330, pl = 30, pr = 150, pt = 16, pb = 40; let lo = 0, hi = 0;
    for (const r of [D.A, D.B]) for (const v of r.t.running_margin.data) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    const X = (l: number) => pl + (l / L) * (W - pl - pr), Y = (v: number) => pt + ((hi - v) / (hi - lo || 1)) * (Hh - pt - pb);
    let s = `<line x1="${pl}" x2="${W - pr}" y1="${Y(0)}" y2="${Y(0)}" stroke="#555" stroke-dasharray="2 3"/><text x="${pl - 8}" y="${Y(0) + 4}" text-anchor="end">0</text>`;
    s += `<text x="${pl}" y="${Hh - 10}">after this many layers: 0 … ${L}</text>`;
    const ys: number[] = [];
    for (const [r, col, name] of [[D.A, A_COL, nameA], [D.B, B_COL, nameB]] as const) {
      let d = ""; for (let l = 0; l <= L; l++) d += `${l ? "L" : "M"}${X(l).toFixed(1)},${Y(r.t.running_margin.get(l)).toFixed(1)}`;
      s += `<path d="${d}" fill="none" stroke="${col}" stroke-width="2"/>`;
      const m = r.m.readout.margin; let y = Y(m) + 4; if (ys.length && Math.abs(y - ys[0]) < 16) y = ys[0] + (y >= ys[0] ? 16 : -16); ys.push(y);
      s += `<text x="${X(L) + 10}" y="${y}" style="fill:${col}">${esc(name)} ${m.toFixed(2)}</text>`;
    }
    $("hero").innerHTML = s;
    const dm = D.P.m.d_margin;
    $("heroCap").innerHTML = `${esc(it.item_id)}: B's log-odds end ${sgn(dm, 3)} ${dm >= 0 ? "further toward" : "back from"} “${esc(short(lp, 40))}” than A. <a href="#s2b" class="u">Read the story of this item</a>`;
  }
  $("s2b").innerHTML = `<b>The story of this item.</b> ${story()}`;
  function story() { // computed from the arrays, not written by hand
    const a = D.A.t.running_margin, b = D.B.t.running_margin, dd = dAttr(D, false); let best = 0, bl = 0;
    for (let l = 0; l < L; l++) { const d = (b.get(l + 1) - b.get(l)) - (a.get(l + 1) - a.get(l)); if (Math.abs(d) > Math.abs(best)) { best = d; bl = l; } }
    let hv = 0, hl = 0, hh = 0; for (let l = 0; l < L; l++) for (let h = 0; h < D.A.m.model.n_heads; h++) { const d = dd.head(l, h); if (Math.abs(d) > Math.abs(hv)) { hv = d; hl = l; hh = h; } }
    const dm = D.P.m.d_margin;
    return `A and B differ most in what layer ${bl} adds to the log-odds (the step from ${bl} to ${bl + 1} on this axis): A goes ${a.get(bl).toFixed(2)} → ${a.get(bl + 1).toFixed(2)} there, B goes ${b.get(bl).toFixed(2)} → ${b.get(bl + 1).toFixed(2)}. The attention head whose contribution to the answer changed most (B − A) is in layer ${hl}, head ${hh} (${sgn(hv)}). Overall, B's log-odds end ${Math.abs(dm).toFixed(3)} ${dm >= 0 ? "higher" : "lower"} than A's: ${dm >= 0 ? "further toward" : "less toward"} “${esc(short(lp, 50))}”.`;
  }

  // ILLUSTRATION: the running state as a vertical bus; layers add attention + MLP entries
  {
    let s = ""; const bx = 230;
    s += `<rect x="${bx - 9}" y="20" width="18" height="250" rx="4" fill="#1a2233" stroke="#3a4a6a"/><text x="${bx}" y="292" fill="#8fa6cf" font-size="11" text-anchor="middle">running state h (${n(dModel)} numbers)</text>`;
    s += `<text x="${bx}" y="14" fill="#bbb" font-size="11" text-anchor="middle">→ final rescaling → scores for ${it.codes.slice(0, 4).map((c) => `“${esc(c)}”`).join(" ")}</text>`;
    ([[210, "layer 0"], [130, "layer 1"], [50, `layer ${L - 1}`]] as const).forEach(([y, name], i) => {
      s += `<text x="20" y="${y + 24}" fill="#999" font-size="11">${name}</text>`;
      for (let h = 0; h < Math.min(H, 9); h++) s += `<rect x="${78 + h * 13}" y="${y + 6}" width="10" height="${10 + ((h * 7 + i * 3) % 5) * 3}" fill="#3c4658" stroke="#5a6780"/>`;
      s += `<text x="78" y="${y + 50}" fill="#8fa6cf" font-size="10">${H} attention heads${H > 9 ? " (9 drawn)" : ""}</text><path d="M196 ${y + 18} L${bx - 10} ${y + 18}" stroke="#8fa6cf" marker-end="url(#ar)"/>`;
      s += `<rect x="282" y="${y + 4}" width="120" height="26" fill="#2b2a26" stroke="#6e6a5e"/><text x="342" y="${y + 21}" fill="#a8a49a" font-size="10" text-anchor="middle"><title>MLP block: the part of a layer that transforms what the heads read</title>MLP · ${n(dFfn)} neurons</text><path d="M281 ${y + 17} L${bx + 10} ${y + 17}" stroke="#a8a49a" marker-end="url(#ar2)"/>`;
      s += `<text x="${bx + 14}" y="${y + 44}" fill="#666" font-size="12">+</text>`; if (i === 1) s += `<text x="${bx}" y="${y - 20}" fill="#555" font-size="14" text-anchor="middle">⋮</text>`;
    });
    s = `<defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L8 4L0 8z" fill="#8fa6cf"/></marker><marker id="ar2" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L8 4L0 8z" fill="#a8a49a"/></marker></defs>` + s;
    $("ill").innerHTML = s;
  }

  // REAL: resid_norm heatmap (L+1 × T), log colour shared over A and B, clipped at the 99th percentile; bands = manifest.segments
  {
    const c = $("heat") as HTMLCanvasElement, W = c.clientWidth || 500, Hh = 230, dpr = devicePixelRatio || 1; c.width = W * dpr; c.height = Hh * dpr; const g = c.getContext("2d")!; g.scale(dpr, dpr);
    const s = makeRamp([D.A.t.resid_norm, D.B.t.resid_norm]), segs = segmentsOf(D.A), top = 16, rh = (Hh - top - 4) / (L + 1), cw = W / T;
    for (let l = 0; l <= L; l++) for (let t = 0; t < T; t++) { g.fillStyle = mix("#121214", "#dfe6ee", rampU(s, D.A.t.resid_norm.get(l, t))); g.fillRect(t * cw, top + (L - l) * rh, Math.ceil(cw), Math.ceil(rh)); }
    for (const sg of segs) { g.fillStyle = sg.kind === "readout" ? "#6b9bff" : sg.open ? "#2c3a52" : "#202020"; g.fillRect(sg.a * cw + 0.5, 0, sg.n * cw - 1, top - 3); }
    $("heatCap").innerHTML = `Model A (the base). ${T} tokens (word pieces) run left to right; layers run from 0 (bottom) to ${L} (top). Brighter means the running state is larger (a longer list of numbers). Bands above: template text (grey), the ${bank ? "scenario" : "question"} and options (blue), the answer position, t* (bright). The bands are the prompt parts recorded in the export. Template text is the fixed chat wrapper around the question. Most of the prompt is template text, which is why the workbench collapses it by default. Colour is on a log scale, so large values do not hide small ones. It is clipped at the 99th percentile (≥ ${s.vmax.toFixed(1)}).`;
  }

  // REAL: answer probabilities A vs B, with the Quadrant III clamped run as ticks
  {
    $("probs").innerHTML = it.codes.map((c, i) => `<div class="prow"><span>${esc(c)} · ${esc(short(String(it.labels[i]), bank ? 90 : 40))}</span><div>
      ${([[D.A, A_COL, "A"], [D.B, B_COL, "B"]] as const).map(([r, col, k]) => `<div class="pr2"><span class="muted">${k}</span><div class="trk" style="height:9px"><div style="width:${(r.m.readout.probs[c] * 100).toFixed(1)}%;background:${col}"></div><i style="left:${(r.m.readout.probs_clamped[c] * 100).toFixed(1)}%"></i></div><span class="num">${r.m.readout.probs[c].toFixed(3)}</span></div>`).join("")}</div></div>`).join("");
    $("probCap").innerHTML = `Probability of each answer code, for A and B. The purple tick marks the clamped run (Quadrant III neurons switched off). Change in P(“${esc(short(lp, 40))}”) from the base, B − A: ${sgn(D.P.m.d_probs[it.j_plus])}.`;
  }

  // REAL: per-layer change in the push on the margin, attention vs MLP (pair export d_attn_attr, d_mlp_attr; browser fallback for @1)
  {
    const pt_ = D.P.t, exported = !!(pt_.d_attn_attr && pt_.d_mlp_attr && D.P.m.d_embed_attr != null);
    const W = 470, Hh = 250, pl = 40, pb = 28; const da: number[] = [], dm: number[] = [];
    for (let l = 0; l < L; l++) {
      da.push(exported ? pt_.d_attn_attr.get(l) : D.B.t.attn_attr.get(l) - D.A.t.attn_attr.get(l));
      dm.push(exported ? pt_.d_mlp_attr.get(l) : D.B.t.mlp_attr.get(l) - D.A.t.mlp_attr.get(l));
    }
    const m = Math.max(...da.map(Math.abs), ...dm.map(Math.abs)) || 1, bw = (W - pl - 10) / L, y0 = (Hh - pb) / 2 + 6, k = ((Hh - pb) / 2 - 14) / m;
    let s = `<line x1="${pl}" x2="${W - 10}" y1="${y0}" y2="${y0}" stroke="#444"/><text x="${pl - 6}" y="${y0 - k * m + 4}" fill="#777" font-size="10" text-anchor="end">+${m.toFixed(2)}</text><text x="${pl - 6}" y="${y0 + k * m + 4}" fill="#777" font-size="10" text-anchor="end">−${m.toFixed(2)}</text><text x="${pl - 6}" y="${y0 + 4}" fill="#777" font-size="10" text-anchor="end">0</text>`;
    for (let l = 0; l < L; l++) { const x = pl + l * bw; s += `<rect x="${x + 1}" y="${Math.min(y0, y0 - da[l] * k)}" width="${bw / 2 - 1}" height="${Math.abs(da[l] * k)}" fill="${C.head}"/><rect x="${x + bw / 2}" y="${Math.min(y0, y0 - dm[l] * k)}" width="${bw / 2 - 1}" height="${Math.abs(dm[l] * k)}" fill="${C.mlp}"/>`;
      if (l % 5 === 0 || l === L - 1) s += `<text x="${x + bw / 2}" y="${Hh - 8}" fill="#777" font-size="10" text-anchor="middle">L${l}</text>`; }
    s += `<text x="${pl}" y="12" fill="#bbb" font-size="11">Change in each layer's contribution, B − A · <tspan fill="${C.head}">attention</tspan> · <tspan fill="${C.mlp}">MLP</tspan></text>`;
    $("wf").innerHTML = s;
    const emb = exported ? D.P.m.d_embed_attr! : D.B.m.readout.embed_attr - D.A.m.readout.embed_attr;
    const sum = da.reduce((a, b) => a + b, 0) + dm.reduce((a, b) => a + b, 0) + emb;
    $("wfCap").innerHTML = `Each bar is B's contribution to the answer minus A's, ${exported ? 'from the pair export (<span title="d_attn_attr, d_mlp_attr, d_embed_attr">d_attn_attr, d_mlp_attr</span>)' : '<span class="calc">computed on this page</span> (this export has no d_*_attr)'}. The bars plus the change in the embedding term add up to ${sum.toFixed(4)}. The exported change in log-odds is ${D.P.m.d_margin.toFixed(4)}. ${D.P.t.d_weight_mlp.absMax() === 0 ? "The adapter changed no MLP weights, yet the MLP bars are not zero. Their inputs changed in earlier layers." : ""}`;
  }

  // REAL: the checks (one status line, three rows, the rest behind "show all six checks")
  {
    const ok = [D.A, D.B].every((r) => r.m.conservation.pass);
    $("cons").innerHTML = `<div class="cons ${ok ? "ok" : "bad"}">${ok ? "✓ The parts add up to the total: every accounting check passes for A and B" : "✗ An accounting check failed. Do not read these figures as measurements until the export is fixed."} ${lm("conservation", "see the accounting checks")}</div>` + learnText(D, "conservation")[1];
  }
  window.scrollTo(0, 0);
  return () => { app.innerHTML = ""; };
}
