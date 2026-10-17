// Landing page (the entry point; "Open the workbench" leads to the ladder tab).
// Every figure badged "real data" is drawn here from the exports of the current pair and prompt.
// Copy: design/layout-v2/COPY.md L01–L37 with the PM rulings (K2, K10, K11, K24; DPO training data).

import type { Bundle } from "./data";
import type { Tab } from "./main";
import { A_COL, B_COL, C, dAttr, esc, isBank, labelPlus, learnText, lm, makeRamp, mix, questionText, rampU, roleOf, segmentsOf, sgn, short } from "./common";

export function mountLanding(app: HTMLElement, D: Bundle, nav: { go: (t: Tab | null, extra?: Record<string, string>) => void }): () => void {
  void nav;
  const L = D.A.m.model.n_layers, T = D.A.m.tokens.length, it = D.A.m.item, bank = isBank(D.A);
  const adapter = !!D.B.m.model.adapter;
  const nameA = roleOf(D, "A") ? "A · original" : `A · ${short(D.A.m.model.label, 18)}`;
  const nameB = roleOf(D, "B") ? "B · fine-tuned" : `B · ${short(D.B.m.model.label, 18)}`;
  const lp = labelPlus(D.A);
  app.innerHTML = `<div class="wrap">
<nav class="lnav"><span title="SCA2 = Synthetic Cultural Agents from Aggregate Anchors"><b>SCA2 workbench</b></span><span><a href="#s1">How it works</a><a href="#s2">What we measure</a><a href="#s3">The three views</a><a href="#s4">Limits</a><a href="#" data-learn="terms">Terms</a><a href="#" data-go="c">Open the workbench →</a></span></nav>
<div class="hero">
  <div>
    <h1>Where does a language model's <em>survey answer</em> come from?</h1>
    <p class="lede">We ask a small language model a ${bank ? "question about an everyday scenario" : "survey question from the World Values Survey"}. Its answer is a probability for each response code, like the predicted shares from a choice model. We split that answer into the contributions of the model's parts and check that they add up. Then we fine-tune the model toward one country's preferences and compare the two, part by part.</p>
    <p class="lede2">Written for readers who know regression and survey items. No machine-learning background assumed. SCA2 stands for <i>Synthetic Cultural Agents from Aggregate Anchors</i> (arXiv:2610.06562).</p>
    <div class="cta"><a href="#" data-go="c">Open the workbench</a><a class="sec" href="#s1">How it works ↓</a></div>
  </div>
  <figure class="fig"><span class="badge data">real data · one run of each model</span><svg id="hero" viewBox="0 0 560 330" width="100%"></svg><figcaption id="heroCap"></figcaption></figure>
</div>

<section class="s" id="s1"><div class="sn"><b>1</b>what is inside the model</div><div>
  <h2>A running total, written to by many small parts</h2>
  <div class="prose">
    <p>The model cuts the prompt into tokens (word pieces). Each token gets a list of 576 numbers. We call that list the <b>running state</b>. Every layer reads it and adds to it. Nothing is overwritten, like a ledger where each layer posts new entries. This model has ${L} layers.</p>
    <p>Each layer adds two kinds of entries. <b>Attention heads</b> (9 per layer) let a token look back at earlier tokens: each head picks which earlier words to read from and adds a summary. The <b>MLP</b> (a small neural network, 1,536 hidden units per layer) then transforms each token on its own. After the last layer, the final state at the last position is turned into a score for every possible next token.</p>
    <p>Because everything is added, the final score can be split into the parts that added to it. The split is exact for the margin when the final rescaling is held fixed (see section 2). That is the property the whole workbench rests on.</p>
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
    <p><b>The answer.</b> At the answer position the model gives a score to every possible next token. We keep only the scores for the response codes and turn them into probabilities. This is the same form as a multinomial logit: the scores play the part of the linear index, and the probabilities are the choice shares. (This is Eq. 6 of the SCA2 paper (arXiv:2610.06562).) The <b>margin</b> is the gap between the scores of two codes. It equals the log of their odds, and positive means the model leans toward the first.</p>
    <div class="eq">P(code j | prompt) = exp(z<sub>j</sub>) / Σ<sub>k ∈ codes</sub> exp(z<sub>k</sub>)        margin = z<sub>j₊</sub> − z<sub>j₋</sub></div>
    <p class="eqnote">z is the model's raw score for a code. The probability is that code's share of exp(score) among the response codes.</p>
    <p><b>The split.</b> Direct logit attribution (DLA) gives each part a share of the margin, like splitting a logit index into its β·x terms. Each part's entry is read straight through the model's last steps, with the final rescaling held fixed. Then the margin is the sum of an embedding term, 270 head terms and 46,080 neuron terms, with nothing left over. This is the direct effect only: a part that changes what a later layer does gets no credit for that path (see Limits).</p>
    <p><b>The checks.</b> Every run uses 64-bit arithmetic (float64) and has to pass three tests. (1) The parts add up to the final state, to within 1e-3. (2) The parts add up to the margin, to within 1e-2. (3) Our code reproduces the Hugging Face reference implementation to within 1e-10 (relative), once the reference's own 32-bit rounding steps are switched off. If a check fails, the status line next to the answer turns red. The numbers are in the table below.</p>
    <p><b>Before and after.</b> The same prompt goes through two models. A is ${esc(D.A.m.model.label)}. B is ${esc(D.B.m.model.label)}${adapter ? ": A plus a small add-on (a LoRA adapter) trained with DPO on made-up everyday scenarios, preferring the answer that matches the USA's direction on the Global Preferences Survey (e.g. more trusting, more patient)" : ""}. For every layer and token, we store how far B's vector is from A's, and also how far the weights moved.</p>
  </div>
  <div class="cols">
    <figure class="fig"><span class="badge data" title="readout.probs, readout.probs_clamped">real data · the model's answer probabilities</span><div id="probs"></div><figcaption id="probCap"></figcaption></figure>
    <figure class="fig"><span class="badge data">real data · which layers changed the margin</span><svg id="wf" viewBox="0 0 470 250" width="100%"></svg><figcaption id="wfCap"></figcaption></figure>
  </div>
  <div class="fig" style="margin-top:22px"><span class="badge data">real data · do the parts add up? (A and B)</span><div id="cons"></div></div>
</div></section>

<section class="s" id="s3"><div class="sn"><b>3</b>the three views</div><div>
  <h2>Three views of the same model run</h2>
  <div class="prose"><p>All three views draw the same saved numbers from the same run. Pick by the question you have. <b>Which parts decided the answer?</b> Start with the ladder. <b>Where, in the prompt and in depth, did the fine-tune change things?</b> Use the matrix. <b>What does the whole run look like?</b> Use the 3D object. Hover anything to compare A and B.</p></div>
  <div class="shots">
    <a href="#" data-go="c"><img src="/screens/v2/c-1700.png" alt="the ladder"><h3>The ladder</h3><p>Every attention head and MLP at the answer position, in three panels: A, B and B − A. Each panel adds up to its margin. The prompt is shown as text, shaded by where the selected head looks.</p></a>
    <a href="#" data-go="b"><img src="/screens/v2/b-1700.png" alt="the matrix"><h3>The matrix</h3><p>Heatmaps of layer by token for A, B and the change ‖B − A‖, with one shared crosshair. Template text is squeezed, not dropped. Charts for the answer position are below.</p></a>
    <a href="#" data-go="a"><img src="/screens/v2/a-side-1700.png" alt="the 3D object"><h3>The 3D object</h3><p>The whole run as 3D blocks (token by layer by size). Template text is collapsed into labelled gaps. There is a prompt map, a word search and camera presets.</p></a>
  </div>
  <p class="muted small">Thumbnails are screenshots of this app (viewer/screens/v2), default pair and prompt.</p>
</div></section>

<section class="s" id="s4"><div class="sn"><b>4</b>limits</div><div>
  <h2>What this does not show</h2>
  <div class="lim">
    <div><b>Direct effect only</b>DLA credits each part for what it adds straight to the answer. A head that changes what a later layer does gets no credit for that indirect path. In regression terms, it is a direct effect with the mediators held out. A large DLA does not show that the part causes the answer; that needs ablation or patching. The clamped run is the one such intervention here: it switches off the Quadrant III neurons and runs the model again (the purple ticks).</div>
    <div><b>A 135M stand-in</b>SmolLM2-135M is a small model, chosen so that every run can be done in float64 and checked. The paper's models are larger. Patterns here show the method. They are not findings about those larger models.</div>
    <div><b>Norms hide direction</b>Block heights are the lengths of vectors. Two writes of equal length can point in unrelated directions. Only the answer-position numbers (DLA) say which way a write pushes the answer.</div>
    <div><b>Only the top 16 attention weights are kept</b>For each head and token we keep the 16 largest attention weights. Attention lines and prompt shading use only those. The “covered” figure says how much of the head's total attention they account for.</div>
    <div><b>One question at a time</b>Each view shows one prompt. Nothing here averages over questions, so nothing here is a statistic about a population.</div>
  </div>
</div></section>
<footer>SCA2 is <i>Synthetic Cultural Agents from Aggregate Anchors</i> (Paper A: arXiv:2610.06562). Paper B extends the method to a 42-country cohort; this workbench is its companion. Every figure marked “real data” is drawn in your browser from files in workbench/exports/ (format ${esc(D.A.m.schema ?? "sca2-workbench/capture@1")}; pair ${esc(D.A.m.model.key)} | ${esc(D.B.m.model.key)} · ${esc(it.item_id)}). Figures marked “illustration” use no data.</footer>
</div>`;
  const $ = (id: string) => app.querySelector<HTMLElement>("#" + id)!;

  // HERO: running_margin (h^l_{t*}·w) per layer for A and B — the answer forming, layer by layer
  {
    const W = 560, Hh = 330, pl = 46, pr = 128, pt = 34, pb = 40; let lo = 0, hi = 0;
    for (const r of [D.A, D.B]) for (const v of r.t.running_margin.data) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    const X = (l: number) => pl + (l / L) * (W - pl - pr), Y = (v: number) => pt + ((hi - v) / (hi - lo || 1)) * (Hh - pt - pb);
    let s = `<text x="${pl}" y="14" fill="#bbb" font-size="11.5">The margin, log-odds of “${esc(it.j_plus)}” vs “${esc(it.j_minus)}”, as it builds up layer by layer</text><text x="${pl}" y="27" fill="#888" font-size="10.5">Positive = toward “${esc(short(lp, 50))}”.</text>`;
    for (let l = 0; l <= L; l += 5) s += `<line x1="${X(l)}" x2="${X(l)}" y1="${pt}" y2="${Hh - pb}" stroke="#1d1d1d"/><text x="${X(l)}" y="${Hh - pb + 16}" fill="#777" font-size="10.5" text-anchor="middle">${l}</text>`;
    s += `<line x1="${pl}" x2="${W - pr}" y1="${Y(0)}" y2="${Y(0)}" stroke="#444"/><text x="${pl - 8}" y="${Y(0) + 4}" fill="#777" font-size="10.5" text-anchor="end">0</text><text x="${pl - 8}" y="${Y(hi) + 4}" fill="#777" font-size="10.5" text-anchor="end">${hi.toFixed(1)}</text>${lo < -0.05 * (hi - lo) ? `<text x="${pl - 8}" y="${Y(lo) + 4}" fill="#777" font-size="10.5" text-anchor="end">${lo.toFixed(1)}</text>` : ""}`;
    s += `<text x="${(pl + W - pr) / 2}" y="${Hh - 6}" fill="#777" font-size="10.5" text-anchor="middle">after this many layers (0 = the starting vector, ${L} = the final state)</text>`;
    const ys: number[] = [];
    for (const [r, col, name] of [[D.A, A_COL, nameA], [D.B, B_COL, nameB]] as const) {
      let d = ""; for (let l = 0; l <= L; l++) d += `${l ? "L" : "M"}${X(l).toFixed(1)},${Y(r.t.running_margin.get(l)).toFixed(1)}`;
      s += `<path d="${d}" fill="none" stroke="${col}" stroke-width="2.4"/>`;
      for (let l = 0; l <= L; l++) s += `<circle cx="${X(l)}" cy="${Y(r.t.running_margin.get(l))}" r="2" fill="${col}"/>`;
      const m = r.m.readout.margin; let y = Y(m) + 4; if (ys.length && Math.abs(y - ys[0]) < 44) y = ys[0] + (y >= ys[0] ? 44 : -44); ys.push(y);
      s += `<text x="${X(L) + 10}" y="${y}" fill="${col}" font-size="12">${esc(name)}</text><text x="${X(L) + 10}" y="${y + 14}" fill="#999" font-size="10.5">margin ${m.toFixed(2)}</text><text x="${X(L) + 10}" y="${y + 27}" fill="#999" font-size="10.5">P(“${esc(it.j_plus)}”) ${r.m.readout.probs[it.j_plus].toFixed(2)}</text>`;
    }
    $("hero").innerHTML = s;
    const qt = questionText(D.A);
    const head = bank ? "Scenario" : `WVS ${esc(String(it.meta.question_id ?? it.item_id))}`;
    $("heroCap").innerHTML = `${head}: ${qt ? `“${esc(short(qt, bank ? 220 : 300))}”` : "(question text not in this export)"} <span title="running_margin: h·w after n layers at t*, read with the final layer's rescaling held fixed">Each dot is the margin you would get by reading the answer off the running state after that many layers.</span> ${story()}`;
  }
  function story() { // computed from the arrays, not written by hand
    const a = D.A.t.running_margin, b = D.B.t.running_margin, dd = dAttr(D, false); let best = 0, bl = 0;
    for (let l = 0; l < L; l++) { const d = (b.get(l + 1) - b.get(l)) - (a.get(l + 1) - a.get(l)); if (Math.abs(d) > Math.abs(best)) { best = d; bl = l; } }
    let hv = 0, hl = 0, hh = 0; for (let l = 0; l < L; l++) for (let h = 0; h < D.A.m.model.n_heads; h++) { const d = dd.head(l, h); if (Math.abs(d) > Math.abs(hv)) { hv = d; hl = l; hh = h; } }
    const dm = D.P.m.d_margin;
    return `A and B differ most in what layer ${bl} adds to the margin (the step from ${bl} to ${bl + 1} on this axis): A goes ${a.get(bl).toFixed(2)} → ${a.get(bl + 1).toFixed(2)} there, B goes ${b.get(bl).toFixed(2)} → ${b.get(bl + 1).toFixed(2)}. The head whose push on the margin changed most (B − A) is layer ${hl}, head ${hh} (${sgn(hv)}). Overall, B's margin ends ${Math.abs(dm).toFixed(3)} ${dm >= 0 ? "higher" : "lower"} than A's: ${dm >= 0 ? "further toward" : "less toward"} “${esc(short(lp, 50))}”.`;
  }

  // ILLUSTRATION: the running state as a vertical bus; layers add attention + MLP entries
  {
    let s = ""; const bx = 230;
    s += `<rect x="${bx - 9}" y="20" width="18" height="250" rx="4" fill="#1a2233" stroke="#3a4a6a"/><text x="${bx}" y="292" fill="#8fa6cf" font-size="11" text-anchor="middle">running state h (576 numbers)</text>`;
    s += `<text x="${bx}" y="14" fill="#bbb" font-size="11" text-anchor="middle">→ final rescaling → scores for ${it.codes.slice(0, 4).map((c) => `“${esc(c)}”`).join(" ")}</text>`;
    ([[210, "layer 0"], [130, "layer 1"], [50, `layer ${L - 1}`]] as const).forEach(([y, name], i) => {
      s += `<text x="20" y="${y + 24}" fill="#999" font-size="11">${name}</text>`;
      for (let h = 0; h < 9; h++) s += `<rect x="${78 + h * 13}" y="${y + 6}" width="10" height="${10 + ((h * 7 + i * 3) % 5) * 3}" fill="#3c4658" stroke="#5a6780"/>`;
      s += `<text x="78" y="${y + 50}" fill="#8fa6cf" font-size="10">9 attention heads</text><path d="M196 ${y + 18} L${bx - 10} ${y + 18}" stroke="#8fa6cf" marker-end="url(#ar)"/>`;
      s += `<rect x="282" y="${y + 4}" width="120" height="26" fill="#2b2a26" stroke="#6e6a5e"/><text x="342" y="${y + 21}" fill="#a8a49a" font-size="10" text-anchor="middle">MLP · 1,536 neurons</text><path d="M281 ${y + 17} L${bx + 10} ${y + 17}" stroke="#a8a49a" marker-end="url(#ar2)"/>`;
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
    $("heatCap").innerHTML = `Model A. ${T} tokens run left to right; layers run from 0 (bottom) to ${L} (top). Brighter means a longer vector. Bands above: template text (grey), the ${bank ? "scenario" : "question"} and options (blue), the answer position t* (bright). The bands are the prompt parts recorded in the export. Most of the prompt is template text, which is why the workbench collapses it by default. Colour is on a log scale, clipped at the 99th percentile (≥ ${s.vmax.toFixed(1)}).`;
  }

  // REAL: answer probabilities A vs B, with the Quadrant III clamped run as ticks
  {
    $("probs").innerHTML = it.codes.map((c, i) => `<div class="prow"><span>${esc(c)} · ${esc(short(String(it.labels[i]), bank ? 90 : 40))}</span><div>
      ${([[D.A, A_COL, "A"], [D.B, B_COL, "B"]] as const).map(([r, col, k]) => `<div class="pr2"><span class="muted">${k}</span><div class="trk" style="height:9px"><div style="width:${(r.m.readout.probs[c] * 100).toFixed(1)}%;background:${col}"></div><i style="left:${(r.m.readout.probs_clamped[c] * 100).toFixed(1)}%"></i></div><span class="num">${r.m.readout.probs[c].toFixed(3)}</span></div>`).join("")}</div></div>`).join("");
    $("probCap").innerHTML = `Probability of each answer code, for A and B. The purple tick marks the result when Quadrant III neurons are clamped. Change in P(“${esc(short(lp, 40))}”), B − A: ${sgn(D.P.m.d_probs[it.j_plus])}.`;
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
    s += `<text x="${pl}" y="12" fill="#bbb" font-size="11">Change in each layer's push on the margin, B − A · <tspan fill="${C.head}">attention</tspan> · <tspan fill="${C.mlp}">MLP</tspan></text>`;
    $("wf").innerHTML = s;
    const emb = exported ? D.P.m.d_embed_attr! : D.B.m.readout.embed_attr - D.A.m.readout.embed_attr;
    const sum = da.reduce((a, b) => a + b, 0) + dm.reduce((a, b) => a + b, 0) + emb;
    $("wfCap").innerHTML = `Each bar is B's push minus A's push, ${exported ? 'from the pair export (<span title="d_attn_attr, d_mlp_attr, d_embed_attr">d_attn_attr, d_mlp_attr</span>)' : '<span class="calc">computed on this page</span> (this export has no d_*_attr)'}. The bars plus the change in the embedding term add up to ${sum.toFixed(4)}. The exported change in margin is ${D.P.m.d_margin.toFixed(4)}. ${D.P.t.d_weight_mlp.absMax() === 0 ? "The adapter changed no MLP weights, yet the MLP bars are not zero. Their inputs changed in earlier layers." : ""}`;
  }

  // REAL: the checks (one status line, three rows, the rest behind "show all six checks")
  {
    const ok = [D.A, D.B].every((r) => r.m.conservation.pass);
    $("cons").innerHTML = `<div class="cons ${ok ? "ok" : "bad"}">${ok ? "✓ The parts add up: every check passes for A and B" : "✗ A check failed. Do not read these figures as measurements until the export is fixed."} ${lm("conservation", "see the checks")}</div>` + learnText(D, "conservation")[1];
  }
  window.scrollTo(0, 0);
  return () => { app.innerHTML = ""; };
}
