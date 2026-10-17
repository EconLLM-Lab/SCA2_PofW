// Tab C, the ladder (default tab): every head and MLP at the answer position t*, coloured by its
// push on the margin (DLA), for A, B and B − A. B − A comes from the pair export (d_head_attr,
// d_mlp_attr, d_embed_attr); an @1 export falls back to a browser difference, labelled as such.
// URL keys: clamp=1, shade=a|b|d, sel=l,h (h = -1 for the MLP; sel=none for nothing pinned), q.

import type { Bundle } from "./data";
import type { Ctx } from "./main";
import {
  A_COL, B_COL, CHANGE_FOOT, C, cmpTable, dAttr, diverging, divergingLegend, esc, fmt, inspectorHTML, isBank, labelMinus,
  labelPlus, lm, readoutHTML, segmentsOf, sgn, short, tokText, topKeys,
} from "./common";

type Sel = { l: number; h: number } | null;   // h = -1: MLP; l = -1: embedding term

export function mountLadder(root: HTMLElement, D: Bundle, ctx: Ctx): () => void {
  const L = D.A.m.model.n_layers, H = D.A.m.model.n_heads, ro = D.A.m.readout.position;
  const lp = labelPlus(D.A), lmn = labelMinus(D.A);
  root.className = "tab-c";
  root.innerHTML = `
    <div class="strip"><span class="badge data" title="Every figure on this tab is drawn from the exports of the current pair and prompt">real data · drawn from the exports</span> Each cell is one part of the model at the answer position. Blue pushes the answer toward “${esc(short(lp, 50))}”, orange toward “${esc(short(lmn, 50))}”. Each of the three panels adds up to its margin. ${lm("tstar", "How to read this ↗")}</div>
    <div class="tools">
      <span class="grp">Model run <button data-pass="0">normal</button><button data-pass="1">Quadrant III clamped</button>${lm("clamp", "what's this?")}</span>
      <span class="grp">Shade the prompt by attention in <button data-sh="a">A</button><button data-sh="b">B</button><button data-sh="d">B − A</button></span>
      <span class="grp">Find a word in the prompt <input id="q" placeholder="e.g. confidence" autocomplete="off" /></span>
    </div>
    <div class="c-main">
      <section id="prompt"><h4><span>The prompt, as the model read it</span>${lm("segments", "what are these grey pills?")}</h4>
        <div id="plegend"></div><div id="ptext" class="ptext"></div><div id="pkey"></div><div id="tops"></div></section>
      <section id="ladder"><h4><span>What pushed the answer: every attention head and MLP, at the answer position</span>${lm("dla", "what is DLA?")}</h4>
        <svg id="lad"></svg><div id="lkey"></div></section>
      <aside id="side"><div id="ro"></div><div id="insp"></div></aside>
    </div>
    <div id="ptip" hidden></div>`;
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => root.querySelector<T>("#" + id)!;
  const segs = segmentsOf(D.A);

  let clamp = ctx.get("clamp") === "1", shade = ctx.get("shade") || "a", hov: Sel = null, pin: Sel = null, query = "", note = "";
  const S = (r: typeof D.A) => ({
    head: clamp ? r.t.head_attr_clamped : r.t.head_attr, mlp: clamp ? r.t.mlp_attr_clamped : r.t.mlp_attr,
    rm: clamp ? r.t.running_margin_clamped : r.t.running_margin,
    embed: clamp ? r.m.readout.embed_attr_clamped : r.m.readout.embed_attr, margin: clamp ? r.m.readout.margin_clamped : r.m.readout.margin,
  });
  /** The head whose push on the margin changed most, B − A (from the pair export when present). */
  function biggest(): Sel { const d = dAttr(D, clamp); let best = 0, s: Sel = null;
    for (let l = 0; l < L; l++) for (let h = 0; h < H; h++) if (Math.abs(d.head(l, h)) > best) { best = Math.abs(d.head(l, h)); s = { l, h }; } return s; }

  // ---------------- the ladder (SVG)
  function ladder() {
    const a = S(D.A), b = S(D.B), dd = dAttr(D, clamp), box = $("ladder");
    const vmax = Math.max(a.head.absMax(), b.head.absMax(), a.mlp.absMax(), b.mlp.absMax(), Math.abs(a.embed), Math.abs(b.embed));
    $("lkey").innerHTML = divergingLegend(vmax, lp, lmn, " Colour is on a square-root scale. One scale for all three panels.");
    const W = box.clientWidth - 24, Hh = box.clientHeight - 34 - $("lkey").offsetHeight - 10;
    const top = 50, bottom = 74, rowH = Math.max(12, Math.min(26, (Hh - top - bottom) / (L + 1))), lab = 40, gap = 22, plotW = Math.max(170, W * 0.21);
    const gw = (W - lab - plotW - gap * 3) / 3, cw = gw / (H + 2.6), mw = cw * 2.2;
    const ddSrc = dd.exported ? `from the pair export (${clamp ? "d_head_attr_clamped, d_mlp_attr_clamped" : "d_head_attr, d_mlp_attr"})` : "computed on this page (this export has no d_*_attr)";
    const groups: [string, string, (l: number, h: number) => number, number, number, string][] = [
      [`A${D.B.m.model.adapter ? " · original" : ""}`, A_COL, (l, h) => (h < 0 ? a.mlp.get(l) : a.head.get(l, h)), a.embed, a.margin, "margin"],
      [`B${D.B.m.model.adapter ? " · fine-tuned" : ""}`, B_COL, (l, h) => (h < 0 ? b.mlp.get(l) : b.head.get(l, h)), b.embed, b.margin, "margin"],
      ["B − A", "#e6e6e6", (l, h) => (h < 0 ? dd.mlp(l) : dd.head(l, h)), dd.embed, dd.margin, "change in margin"],
    ];
    const y = (l: number) => top + (L - 1 - l) * rowH;
    const yEmb = y(-1) + 6;
    let s = "";
    groups.forEach(([name, col, f, emb, target, tname], gi) => {
      const x0 = lab + gi * (gw + gap);
      let sum = emb; for (let l = 0; l < L; l++) { sum += f(l, -1); for (let h = 0; h < H; h++) sum += f(l, h); }
      s += `<text x="${x0}" y="14" style="fill:${col};font-weight:600">${esc(name)}</text><text x="${x0}" y="28">9 heads, then the MLP</text>`;
      if (gi === 2) s += `<text x="${x0}" y="41" style="font-size:9.5px">${esc(dd.exported ? "from the pair export" : "computed on this page")}</text>`;
      const okk = Math.abs(sum - target) < 1e-2;
      const tsrc = gi < 2 ? "from the export" : dd.marginExported ? "from the pair export" : "computed on this page from A and B";
      s += `<text x="${x0}" y="${yEmb + rowH + 18}" style="fill:${okk ? "#6be0a0" : "#ff6b6b"}">${okk ? "✓" : "✗"} All cells + embedding = ${sum.toFixed(3)}</text><text x="${x0}" y="${yEmb + rowH + 33}">${tname} ${target.toFixed(3)} · ${tsrc}</text>`;
      for (let l = 0; l < L; l++) for (let h = -1; h < H; h++) {
        const v = f(l, h), x = h < 0 ? x0 + H * cw + cw * 0.4 : x0 + h * cw;
        const on = (q: Sel) => q && q.l === l && q.h === h;
        const st = on(pin) ? 'stroke="#fff" stroke-width="2"' : on(hov) ? 'stroke="#ffcf5c" stroke-width="1.5"' : "";
        s += `<rect class="cell" data-l="${l}" data-h="${h}" x="${x.toFixed(1)}" y="${(y(l) + 1).toFixed(1)}" width="${((h < 0 ? mw : cw) - 2).toFixed(1)}" height="${(rowH - 2).toFixed(1)}" rx="2" fill="${diverging(v, vmax)}" ${st}><title>${esc(name)} · layer ${l} · ${h < 0 ? "MLP" : "head " + h} · push on the margin ${sgn(v, 4)}${gi === 2 ? " (" + ddSrc + ")" : ""}</title></rect>`;
      }
      const on = pin && pin.l === -1 ? 'stroke="#fff" stroke-width="2"' : "";
      s += `<rect class="cell" data-l="-1" data-h="-2" x="${x0}" y="${yEmb}" width="${(H * cw - 2).toFixed(1)}" height="${(rowH - 2).toFixed(1)}" rx="2" fill="${diverging(emb, vmax)}" ${on}><title>embedding term ${sgn(emb, 4)}</title></rect>${gi === 0 ? `<text x="${lab - 8}" y="${yEmb + rowH * 0.7}" text-anchor="end"><title>embedding term: what each token's starting vector adds, before layer 0</title>emb</text>` : ""}`;
    });
    // layer axis: every layer ticked, every 5th and the last labelled, the selected layer highlighted
    const sl = (pin || hov)?.l ?? -9;
    for (let l = 0; l < L; l++) {
      const strong = l % 5 === 0 || l === L - 1 || l === sl;
      s += `<line x1="${lab - 6}" x2="${lab - 2}" y1="${y(l) + rowH / 2}" y2="${y(l) + rowH / 2}" stroke="#444"/>`;
      if (strong) s += `<text x="${lab - 8}" y="${y(l) + rowH * 0.68}" text-anchor="end" style="fill:${l === sl ? "#ffcf5c" : l % 5 ? "#888" : "#bbb"}">L${l}</text>`;
    }
    s += `<text transform="translate(9 ${top + (L * rowH) / 2}) rotate(-90)" text-anchor="middle" style="fill:#777">layer (0 = first, at the bottom)</text>`;
    // margin by layer: h^l·w at t*, A and B, x shared
    const px0 = lab + 3 * (gw + gap), pw = plotW - 16;
    let lo = 0, hi = 0; for (const r of [a.rm, b.rm]) for (const v of r.data) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    const X = (v: number) => px0 + ((v - lo) / (hi - lo || 1)) * pw, Y = (l: number) => y(l) + rowH;
    s += `<text x="${px0}" y="14" style="fill:#e6e6e6;font-weight:600">Margin by layer</text><text x="${px0}" y="28"><title>Read with the final layer's rescaling held fixed (running_margin${clamp ? "_clamped" : ""}).</title>if read off at each layer</text>`;
    s += `<text x="${px0}" y="41"><tspan style="fill:${A_COL}">— A</tspan>  <tspan style="fill:${B_COL}">— B</tspan></text>`;
    s += `<line x1="${X(0)}" x2="${X(0)}" y1="${top}" y2="${y(-1)}" stroke="#444"/>`;
    for (const v of [lo, 0, hi]) if (v === 0 || Math.abs(X(v) - X(0)) > 28) s += `<text x="${X(v)}" y="${y(-1) + 14}" text-anchor="${v === hi ? "end" : v === lo ? "start" : "middle"}">${v === 0 ? "0" : v.toFixed(1)}</text>`;
    for (const [r, col] of [[a.rm, A_COL], [b.rm, B_COL]] as const) {
      let d = ""; for (let l = 0; l <= L; l++) d += `${l ? "L" : "M"}${X(r.get(l)).toFixed(1)},${(l === L ? top : Y(l)).toFixed(1)}`;
      s += `<path d="${d}" fill="none" stroke="${col}" stroke-width="2"/><circle cx="${X(r.get(L))}" cy="${top}" r="3.5" fill="${col}"/>`;
    }
    const anc = (v: number) => (X(v) > px0 + pw - 24 ? "end" : X(v) < px0 + 24 ? "start" : "middle");
    s += `<text x="${X(a.rm.get(L))}" y="${top - 6}" text-anchor="${anc(a.rm.get(L))}" style="fill:${A_COL}">A ${a.rm.get(L).toFixed(2)}</text><text x="${X(b.rm.get(L))}" y="${top + 15}" text-anchor="${anc(b.rm.get(L))}" style="fill:${B_COL}">B ${b.rm.get(L).toFixed(2)}</text>`;
    if (sl >= 0) s += `<rect x="${lab - 2}" y="${y(sl)}" width="${W - lab}" height="${rowH}" fill="none" stroke="#ffffff30"/>`;
    const svg = $("lad"); svg.setAttribute("width", String(W)); svg.setAttribute("height", String(yEmb + rowH + 44)); svg.innerHTML = s;
  }
  $("lad").addEventListener("mousemove", (e) => {
    const c = (e.target as Element).closest<SVGElement>(".cell"); const s = c ? { l: +c.dataset.l!, h: +c.dataset.h! } : null;
    if (JSON.stringify(s) === JSON.stringify(hov)) return; hov = s; ladder(); if (!pin) { s ? inspect(s, false) : idle(); prompt(); }
  });
  $("lad").addEventListener("mouseleave", () => { hov = null; ladder(); if (!pin) { idle(); prompt(); } });
  $("lad").addEventListener("click", (e) => { const c = (e.target as Element).closest<SVGElement>(".cell"); if (!c) return; setPin({ l: +c.dataset.l!, h: +c.dataset.h! }); });
  function setPin(s: Sel, n = "") { pin = s; note = n; ctx.set("sel", s ? `${s.l},${s.h}` : "none"); ladder(); s ? inspect(s, true) : idle(); prompt(); tops(); }
  window.addEventListener("keydown", (e) => { if (e.key === "Escape" && !document.querySelector("dialog[open]")) setPin(null); }, { signal: ctx.signal });

  // ---------------- the prompt as text, shaded by the selected head's attention row at t* (attn_topk_val)
  const weights = (r: typeof D.A, l: number, h: number) => { const w = new Map<number, number>(); for (const k of topKeys(r, l, h, ro, 16)) w.set(k.key, k.w); return w; };
  function prompt() {
    const sel = pin || hov, head = sel && sel.h >= 0 && sel.l >= 0 ? sel : null;
    const wa = head ? weights(D.A, head.l, head.h) : null, wb = head ? weights(D.B, head.l, head.h) : null;
    const val = (t: number) => (!head ? null : shade === "a" ? wa!.get(t) || 0 : shade === "b" ? wb!.get(t) || 0 : (wb!.get(t) || 0) - (wa!.get(t) || 0));
    const bg = (v: number | null) => (v == null || v === 0 ? "transparent" : shade === "d" ? (v > 0 ? `rgba(255,207,92,${Math.min(0.9, Math.sqrt(Math.abs(v)))})` : `rgba(107,155,255,${Math.min(0.9, Math.sqrt(Math.abs(v)))})`) : `rgba(255,255,255,${Math.min(0.85, 0.08 + Math.sqrt(v) * 0.9)})`);
    const fg = (v: number | null) => (v != null && shade !== "d" && v > 0.25 ? "#111" : "");
    $("plegend").innerHTML = head
      ? `Shading: how much head ${head.h} of layer ${head.l} reads each word when it is about to write the answer (${shade === "a" ? "model A" : shade === "b" ? "model B" : "B − A: gold = B reads this word more, blue = less"}). Only its 16 largest weights are stored. A grey pill shows the total for the words it hides.`
      : `Hover or click a head in the ladder to see which words it reads. Your browser's find (Ctrl/Cmd-F) works on this text.`;
    let html = "";
    for (const sg of segs) {
      if (!sg.open) {
        let sum = 0; if (head) for (let t = sg.a; t <= sg.b; t++) sum += val(t)!;
        const show = head && Math.abs(sum) > 0.005, hit = query && sg.text.toLowerCase().includes(query);
        const st = `${show ? `background:${bg(sum)};color:${fg(sum) || "#ddd"};` : ""}${hit ? "outline:1.5px solid #ffcf5c;" : ""}`;
        html += `<span class="pill" data-seg="${sg.a}" style="${st}" title="Click to open: ${esc(sg.label)}">‹${esc(sg.label)} · <b>${sg.n}</b> tokens${show ? ` · total attention ${sum.toFixed(2)}` : ""}›</span>${sg.kind === "template" ? "" : "\n"}`;
        continue;
      }
      // Kind label over the open question part: its name comes from the export's item kind and segment label.
      if (sg.kind === "question") html += `<span class="seglab" title="prompt part: ${esc(sg.label)} (manifest.segments)">${isBank(D.A) ? "Scenario" : "Survey question"}</span>`;
      for (let t = sg.a; t <= sg.b; t++) {
        const tx = D.A.m.tokens[t].text, v = val(t), cls = `tk${t === ro ? " ro" : ""}${query && tx.toLowerCase().includes(query) ? " hit" : ""}`;
        const show = t === ro ? "t*" : tx === "\n" ? '<span class="nl">⏎</span>\n' : esc(tx);
        html += `<span class="${cls}" data-t="${t}" style="background:${bg(v)};${fg(v) ? "color:" + fg(v) : ""}"${t === ro ? ' title="answer position (t*): where the model is about to write its answer"' : ""}>${show}</span>`;
      }
      if (sg.kind !== "template" && sg.kind !== "readout" && !sg.text.endsWith("\n")) html += "\n";
    }
    $("ptext").innerHTML = html;
    $("pkey").innerHTML = head ? (shade === "d"
      ? `<div class="key"><span class="key-l">attention, B − A</span><span class="key-bar"><span style="background:linear-gradient(90deg,rgba(107,155,255,.9),transparent 50%,rgba(255,207,92,.9))"></span><i style="left:0">−1</i><i style="left:50%">0</i><i style="left:100%">+1</i></span><span class="key-clip">Shade deepens with the square root of the difference. Weights from <code>attn_topk_val</code> (A and B).</span></div>`
      : `<div class="key"><span class="key-l">attention weight</span><span class="key-bar"><span style="background:linear-gradient(90deg,rgba(255,255,255,.08),rgba(255,255,255,.85))"></span><i style="left:0">0</i><i style="left:25%">0.06</i><i style="left:50%">0.25</i><i style="left:100%">≥0.6</i></span><span class="key-clip">Shade grows with the square root of the weight and saturates near 0.6. Weights from <code>attn_topk_val</code>.</span></div>`) : "";
  }
  $("ptext").addEventListener("click", (e) => { const p = (e.target as Element).closest<HTMLElement>(".pill"); if (!p) return; const sg = segs.find((s) => s.a === +p.dataset.seg!)!; sg.open = true; prompt(); });
  $("ptext").addEventListener("mousemove", (e) => {
    const tk = (e.target as Element).closest<HTMLElement>(".tk"), tip = $("ptip"); if (!tk) { tip.hidden = true; return; }
    const t = +tk.dataset.t!, sel = pin || hov;
    let s = `token ${t}: “${tokText(D.A.m.tokens[t].text)}”`;
    if (sel && sel.h >= 0 && sel.l >= 0) { const a = weights(D.A, sel.l, sel.h).get(t) || 0, b = weights(D.B, sel.l, sel.h).get(t) || 0; s += `\nHead ${sel.h}, layer ${sel.l}, attention from the answer position: A ${a.toFixed(3)}, B ${b.toFixed(3)}, B − A ${sgn(b - a)}`; }
    s += `\nFinal-state size: A ${fmt(D.A.t.resid_norm.get(L, t), 3)}, B ${fmt(D.B.t.resid_norm.get(L, t), 3)}, change ${fmt(D.P.t.d_resid_norm.get(L, t), 3)}`;
    tip.textContent = s; tip.hidden = false; tip.style.left = e.clientX + 14 + "px"; tip.style.top = e.clientY + 14 + "px";
  });
  $("ptext").addEventListener("mouseleave", () => ($("ptip").hidden = true));
  const qi = $<HTMLInputElement>("q");
  qi.oninput = () => {
    query = qi.value.toLowerCase().trim(); if (query.length < 2) query = "";
    ctx.set("q", query || null);
    for (const sg of segs) if (query && sg.text.toLowerCase().includes(query) && sg.kind !== "template") sg.open = true;
    prompt(); root.querySelector(".tk.hit")?.scrollIntoView({ block: "center" });
  };

  // ---------------- the largest changes in push on the margin (fills the prompt column below the text)
  function tops() {
    const a = S(D.A), b = S(D.B), dd = dAttr(D, clamp);
    const all: { l: number; h: number; a: number; b: number; d: number }[] = [];
    for (let l = 0; l < L; l++) { all.push({ l, h: -1, a: a.mlp.get(l), b: b.mlp.get(l), d: dd.mlp(l) }); for (let h = 0; h < H; h++) all.push({ l, h, a: a.head.get(l, h), b: b.head.get(l, h), d: dd.head(l, h) }); }
    all.sort((x, y) => Math.abs(y.d) - Math.abs(x.d));
    const m = Math.abs(all[0].d) || 1;
    $("tops").innerHTML = `<div class="card"><div class="card-h"><span>Largest changes in push on the margin, B − A</span>${lm("delta", "what is B − A?")}</div>
      <table class="cmp tops"><colgroup><col class="c0"><col class="c1"><col class="c1"><col class="c1"><col class="cbar"></colgroup><thead><tr><th></th><th>A</th><th>B</th><th>Change</th><th></th></tr></thead><tbody>
      ${all.slice(0, 10).map((o) => `<tr class="pick ${pin && pin.l === o.l && pin.h === o.h ? "on" : ""}" data-l="${o.l}" data-h="${o.h}"><td>layer ${o.l} · ${o.h < 0 ? "MLP" : "head " + o.h}</td><td class="num">${sgn(o.a, 3)}</td><td class="num">${sgn(o.b, 3)}</td><td class="num ${dd.exported ? "sx" : ""}">${dd.exported ? sgn(o.d, 3) : `<span class="calc">${sgn(o.d, 3)}</span>`}</td><td><span class="hb" style="width:${((Math.abs(o.d) / m) * 100).toFixed(0)}%;background:${o.d >= 0 ? C.pos : C.neg}"></span></td></tr>`).join("")}</tbody></table>
      <div class="foot">Ranked by |B − A| of the push on the margin${clamp ? " in the clamped run" : ""}; ${dd.exported ? "the change is from the pair export (<code>d_head_attr</code>, <code>d_mlp_attr</code>)" : "<span class=\"calc\">computed on this page</span> (this export has no <code>d_*_attr</code>)"}. Click a row to pin it.</div></div>`;
  }
  $("tops").addEventListener("click", (e) => { const r = (e.target as Element).closest<HTMLElement>("tr.pick"); if (r) setPin({ l: +r.dataset.l!, h: +r.dataset.h! }); });

  // ---------------- side panel
  function inspect(s: NonNullable<Sel>, pinned: boolean) {
    if (s.l < 0) {
      const dd = dAttr(D, clamp);
      $("insp").innerHTML = `<div class="card ${pinned ? "pinned" : ""}"><div class="card-h"><span title="What the word's starting vector (before layer 0) contributes to the margin.">Embedding term</span>${lm("dla", "learn more")}</div>
        ${cmpTable([{ label: `Push on the margin${clamp ? ", clamped run" : ""}`, tip: "readout.embed_attr · d_embed_attr", a: S(D.A).embed, b: S(D.B).embed, d: { v: dd.embed, how: dd.exported ? "exp" : "calc", src: dd.exported ? "d_embed_attr, pair export" : "computed on this page" } }])}${CHANGE_FOOT}</div>`;
      return;
    }
    const sl = s.h >= 0 ? { kind: "head" as const, l: s.l, h: s.h, t: ro } : { kind: "mlp" as const, l: s.l, t: ro };
    $("insp").innerHTML = inspectorHTML(D, sl, { pinned, clamp, note: pinned ? note : "" });
  }
  function idle() { $("insp").innerHTML = `<div class="card"><div class="card-h"><span>Compare A and B for one part</span>${lm("head", "what is a head?")}</div><p class="muted" style="margin:0">Hover a cell in the ladder to compare A and B here. Click to pin it. The left column then shows which words that head reads.</p></div>`; }

  root.querySelectorAll<HTMLElement>("[data-pass]").forEach((b) => (b.onclick = () => { clamp = b.dataset.pass === "1"; ctx.set("clamp", clamp ? 1 : null); sync(); ladder(); tops(); if (pin) inspect(pin, true); }));
  root.querySelectorAll<HTMLElement>("[data-sh]").forEach((b) => (b.onclick = () => { shade = b.dataset.sh!; ctx.set("shade", shade === "a" ? null : shade); sync(); prompt(); }));
  function sync() {
    root.querySelectorAll<HTMLElement>("[data-pass]").forEach((b) => b.classList.toggle("on", (b.dataset.pass === "1") === clamp));
    root.querySelectorAll<HTMLElement>("[data-sh]").forEach((b) => b.classList.toggle("on", b.dataset.sh === shade));
  }
  $("ro").innerHTML = readoutHTML(D);
  sync();
  const sp = ctx.get("sel");
  if (sp === "none") { pin = null; idle(); }
  else if (sp) { const [l, h] = sp.split(",").map(Number); pin = l >= -1 && l < L && h >= -2 && h < H ? { l, h } : null; pin ? inspect(pin, true) : idle(); }
  else { pin = biggest(); note = "Starting point: the head whose push on the margin changed most (B − A). Click anywhere to change it."; if (pin) inspect(pin, true); else idle(); }
  ladder(); prompt(); tops();
  if (ctx.get("q")) { qi.value = ctx.get("q")!; qi.dispatchEvent(new Event("input")); }
  const ro_ = new ResizeObserver(() => ladder()); ro_.observe($("ladder"));
  requestAnimationFrame(() => ctx.ready());
  return () => { ro_.disconnect(); $("ptip").hidden = true; };
}
