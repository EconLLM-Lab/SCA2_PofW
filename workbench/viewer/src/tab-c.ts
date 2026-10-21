// Tab C, the ladder (v3, design/layout-v3/SYSTEM.md + DECISION.md). One face at a time: A, B, or B − A
// (the default). Each cell is one head or MLP at the answer position t*, coloured by its push on the
// margin (DLA). B − A comes from the pair export (d_head_attr, d_mlp_attr, d_embed_attr); an @1 export
// falls back to a browser difference, labelled as such (italic / "computed in this browser").
// At rest: the answer strip, the prompt, the ladder, the margin-by-layer chart. Gold rings mark the five
// largest changes (B − A) on every face. Click pins a cell: a thick white outline, and the drawer opens in
// its own grid column, so nothing else is covered.
// URL keys: face=a|b|d, clamp=1, sel=l,h (h = -1 MLP; l = -1 embedding; none = nothing pinned), q, tpl=1.
// innerHTML below only carries numbers and export strings passed through esc().

import type { Bundle, Run } from "./data";
import type { Ctx } from "./main";
import {
  A_COL, B_COL, CHANGE_FOOT, answerStrip, cmpTable, checksOf, checkLine, dAttr, diverging, esc, faceTainted, failedWho, fmt, inspectorHTML,
  isBank, labelMinus, labelPlus, mix, openLearn, segmentsOf, sgn, short, tokText, topKeys,
} from "./common";

type Sel = { l: number; h: number } | null;   // h = -1: MLP; l = -1: embedding term
type Face = "a" | "b" | "d";
const FACES: [Face, string][] = [["a", "A"], ["b", "B"], ["d", "Change (B − A)"]];
const FACE_TIP: Record<Face, string> = { a: "A: the base model", b: "B: the model compared with the base (a country adapter or a sign prompt)", d: "The change from the base: B − A" };

export function mountLadder(root: HTMLElement, D: Bundle, ctx: Ctx): () => void {
  const L = D.A.m.model.n_layers, H = D.A.m.model.n_heads, ro = D.A.m.readout.position, it = D.A.m.item;
  const lp = labelPlus(D.A), lmn = labelMinus(D.A);
  const jp = `“${it.j_plus}” (${short(lp, 30)})`, jm = `“${it.j_minus}” (${short(lmn, 30)})`;
  const checks = checksOf(D), bad = failedWho(checks), failing = checks.filter((c) => !c.ok);
  root.className = "tab-c v3";
  root.innerHTML = `
    <section id="answer" data-obj="answer"></section>
    <div id="work" class="c-work">
      <section class="obj" id="prompt" data-obj="prompt"><header><span class="cap" title="The prompt as the model reads it. Template text (the fixed chat wrapper) sits on one dashed line; click it to expand. Help: the ? in the top bar">The prompt</span><input id="q" placeholder="find a word" autocomplete="off" hidden /></header>
        <div id="ptext" class="ptext"></div><div class="foot" id="pkey"></div></section>
      <section class="obj" id="ladder" data-obj="ladder"><header><span class="cap" title="Contribution to the answer: every attention head and MLP block, read at the answer position (t*)">Contributions to the answer</span><span class="sp"></span>
          <span class="seg" id="faces">${FACES.map(([k, t]) => `<button data-face="${k}" title="${FACE_TIP[k]}">${t}</button>`).join("")}</span>
          <button id="clamp" class="tog" title="Clamped run (key C): run the model again with the Quadrant III neurons switched off (set to zero)">clamped run</button></header>
        <svg id="lad"></svg><div class="foot" id="lfoot"></div></section>
      <section class="obj" id="mchart" data-obj="margin"><header><span class="cap" title="The log-odds you would get by reading the answer off the running state after each layer, with the final rescaling held fixed (running_margin: h^l·w at the answer position)">Log-odds by layer</span></header>
        <svg id="mc"></svg><div class="foot" id="mfoot"></div></section>
      <aside id="drawer" class="obj" data-obj="drawer" hidden></aside>
    </div>
    <div id="ptip" hidden></div>`;
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => root.querySelector<T>("#" + id)!;
  const segs = segmentsOf(D.A);

  let face = (["a", "b", "d"].includes(ctx.get("face") ?? "") ? ctx.get("face") : "d") as Face;
  let clamp = ctx.get("clamp") === "1", hov: Sel = null, pin: Sel = null, query = "", tplOpen = ctx.get("tpl") === "1";
  const S = (r: Run) => ({
    head: clamp ? r.t.head_attr_clamped : r.t.head_attr, mlp: clamp ? r.t.mlp_attr_clamped : r.t.mlp_attr,
    rm: clamp ? r.t.running_margin_clamped : r.t.running_margin,
    embed: clamp ? r.m.readout.embed_attr_clamped : r.m.readout.embed_attr, margin: clamp ? r.m.readout.margin_clamped : r.m.readout.margin,
  });
  /** The value of one cell on one face. l = -1 is the embedding term. */
  function val(f: Face, l: number, h: number): number {
    if (f === "d") { const d = dAttr(D, clamp); return l < 0 ? d.embed : h < 0 ? d.mlp(l) : d.head(l, h); }
    const s = S(f === "a" ? D.A : D.B);
    return l < 0 ? s.embed : h < 0 ? s.mlp.get(l) : s.head.get(l, h);
  }
  /** The five largest |B − A| pushes (heads and MLPs): the gold rings, on every face. */
  function rings(): [number, number][] {
    const all: [number, number, number][] = [];
    for (let l = 0; l < L; l++) for (let h = -1; h < H; h++) all.push([l, h, Math.abs(val("d", l, h))]);
    return all.sort((x, y) => y[2] - x[2]).slice(0, 5).map(([l, h]) => [l, h]);
  }
  const ringed = (r: [number, number][], l: number, h: number) => r.some(([a, b]) => a === l && b === h);
  const partName = (l: number, h: number) => (l < 0 ? "embedding term" : h < 0 ? `MLP block · layer ${l}` : `head ${h} · layer ${l}`);

  // ---------------- the answer strip: one sentence, two bars, and the full card on demand
  function strip() { $("answer").innerHTML = answerStrip(D, clamp); }

  // ---------------- geometry shared by the ladder and the margin chart (same rows)
  const TOP = 34;   // room above the top row for the margin chart's A/B end labels
  let g = { s: 16, cw: 16, lab: 34, W: 300, Hsvg: 400 };   // s = row height, cw = head column width
  const y = (l: number) => TOP + (L - 1 - l) * g.s;               // top of layer l's row
  const yEmb = () => TOP + L * g.s + 6;                             // the embedding row, below layer 0

  function layout() {
    const box = $("ladder"), work = $("work");
    const head = (box.querySelector("header") as HTMLElement).offsetHeight + 10;
    const availH = box.clientHeight - head - $("lfoot").offsetHeight - 14 - TOP - 6 - 24;
    const pinW = pin ? 340 + 32 : 0, availW = work.clientWidth - 230 - 220 - 64 - pinW - 34 - 10 - 24;
    const s = Math.max(9, Math.min(24, availH / (L + 1)));
    const cw = Math.max(s, Math.min(34, s * 2.1, availW / (H + 2.2)));   // cells may be wider than tall, never narrower
    g = { s, cw, lab: 34, W: 34 + H * cw + 8 + cw * 1.8 + 6, Hsvg: TOP + L * s + 6 + s + 24 };
    // the ladder's column is sized to its SVG (its footer wraps under it); the drawer gets its own column
    work.style.gridTemplateColumns = `minmax(230px, 1fr) ${Math.max(Math.ceil(g.W), 340)}px 220px${pin ? " 340px" : ""}`;
  }

  // ---------------- the ladder (SVG), one face
  function ladder() {
    const rg = rings(), tainted = faceTainted(face, bad);
    let vmax = 0; for (let l = -1; l < L; l++) for (let h = -1; h < H; h++) { if (l < 0 && h >= 0) continue; vmax = Math.max(vmax, Math.abs(val(face, l, h))); }
    const dd = dAttr(D, clamp), browser = face === "d" && !dd.exported;
    // footer first (its height feeds the layout): key, re-sum line, ring legend. Never hidden (rules 2, 3).
    let sum = val(face, -1, 0); for (let l = 0; l < L; l++) for (let h = -1; h < H; h++) sum += val(face, l, h);
    const target = face === "d" ? dd.margin : S(face === "a" ? D.A : D.B).margin;
    const tsrc = face === "d" ? (dd.marginExported ? "change in log-odds, pair export" : "change in log-odds, computed in this browser") : `${face.toUpperCase()}'s log-odds, from the export`;
    const close = Math.abs(sum - target) < 1e-2, ok = close && !tainted;
    const why = tainted ? failing.filter((c) => face === "d" || c.who === face.toUpperCase()).map(checkLine).join(" · ") : "";
    $("lfoot").innerHTML = `<div class="krow"><i class="kbar" style="background:linear-gradient(90deg,${diverging(-1, 1)},${diverging(0, 1)},${diverging(1, 1)})"></i><span>contribution to the answer: orange pushes toward ${esc(jm)} · blue pushes toward ${esc(jp)} · up to ±${fmt(vmax, 2)}, square-root scale</span></div>
      <div class="sumline ${ok ? "ok" : "bad"}" title="Added up again in this browser from the float32 arrays drawn (tolerance 1e-2)${browser ? "; this face's cells are B − A computed in this browser" : ""}">${ok ? "✓" : "✗"} all cells + embedding term = <span class="num">${sum.toFixed(4)}</span> ${close ? "=" : "≠"} ${tsrc} <span class="num">${target.toFixed(4)}</span>${why ? ` · accounting check failed: ${esc(why)}` : ""}</div>
      <div class="krow"><i class="ring"></i><span>gold ring: the 5 largest changes (B − A)${browser ? " (browser)" : ""}</span>${pin ? `<span class="nw"><i class="pinbox"></i> pinned</span>` : ""}</div>`;
    layout();
    const { s, cw, lab, W } = g, mx = lab + H * cw + 8;
    const hl = (pin || hov)?.l ?? -9;
    let o = "";
    for (let l = 0; l < L; l++) {
      if (l % 5 === 0 || l === L - 1 || l === hl) o += `<text x="${lab - 6}" y="${y(l) + s * 0.72}" text-anchor="end" class="${l === hl ? "hl" : ""}">L${l}</text>`;
      for (let h = -1; h < H; h++) {
        const v = val(face, l, h), x = h < 0 ? mx : lab + h * cw, w = h < 0 ? cw * 1.8 : cw;
        o += `<rect class="cell" data-l="${l}" data-h="${h}" x="${(x + 0.5).toFixed(1)}" y="${(y(l) + 0.5).toFixed(1)}" width="${(w - 1.5).toFixed(1)}" height="${(s - 1.5).toFixed(1)}" rx="1.5" fill="${diverging(v, vmax)}"/>`;
      }
    }
    o += `<text x="${lab - 6}" y="${yEmb() + s * 0.72}" text-anchor="end"><title>embedding term: what the word's own starting vector contributes, before layer 0</title>emb</text>`;
    o += `<rect class="cell" data-l="-1" data-h="-2" x="${lab + 0.5}" y="${yEmb() + 0.5}" width="${(H * cw - 1.5).toFixed(1)}" height="${(s - 1.5).toFixed(1)}" rx="1.5" fill="${diverging(val(face, -1, 0), vmax)}"/>`;
    const box = (l: number, h: number) => { const x = l < 0 ? lab : h < 0 ? mx : lab + h * cw, w = l < 0 ? H * cw : h < 0 ? cw * 1.8 : cw, yy = l < 0 ? yEmb() : y(l); return { x, w, yy }; };
    for (const [l, h] of rg) { const b = box(l, h); o += `<rect class="ringm" x="${(b.x - 1).toFixed(1)}" y="${(b.yy - 1).toFixed(1)}" width="${(b.w + 0.5).toFixed(1)}" height="${(s + 0.5).toFixed(1)}" rx="2"/>`; }
    if (hov && !(pin && hov.l === pin.l && hov.h === pin.h)) { const b = box(hov.l, hov.h); o += `<rect class="hovm" x="${(b.x).toFixed(1)}" y="${(b.yy).toFixed(1)}" width="${(b.w - 1).toFixed(1)}" height="${(s - 1).toFixed(1)}" rx="1.5"/>`; }
    if (pin) { const b = box(pin.l, pin.h); o += `<rect class="pinm" x="${(b.x - 2.5).toFixed(1)}" y="${(b.yy - 2.5).toFixed(1)}" width="${(b.w + 3.5).toFixed(1)}" height="${(s + 3.5).toFixed(1)}" rx="2.5"/>`; }
    const yb = yEmb() + s + 16;
    o += `<text x="${lab}" y="${yb}">heads 0–${H - 1}</text><text x="${mx}" y="${yb}"><title>MLP block: the part of a layer that transforms what the heads read</title>MLP</text>`;
    o += `<text x="${lab}" y="${TOP - 10}" class="facel ${tainted ? "bad" : ""}">${face === "a" ? "A" : face === "b" ? "B" : "change, B − A"}${clamp ? " · clamped run" : ""}${browser ? " · computed in this browser" : ""}</text>`;
    const svg = $("lad"); svg.setAttribute("width", String(W)); svg.setAttribute("height", String(g.Hsvg)); svg.innerHTML = o;
    $("ladder").classList.toggle("tainted", tainted);
    root.querySelectorAll<HTMLElement>("[data-face]").forEach((b) => { b.classList.toggle("on", b.dataset.face === face); b.classList.toggle("bad", faceTainted(b.dataset.face!, bad)); });
    $("clamp").classList.toggle("on", clamp);
    margin();
  }

  // ---------------- margin by layer: h^l·w at t*, A and B, on the ladder's rows
  function margin() {
    const a = S(D.A), b = S(D.B), host = $("mchart"), W = Math.max(150, host.clientWidth), s = g.s;
    let lo = 0, hi = 0; for (const r of [a.rm, b.rm]) for (const v of r.data) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    const span = hi - lo || 1, raw = span / 4, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 5, 10].map((k) => k * mag).find((k) => k >= raw)!;
    lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    const pl = 10, pr = 10, X = (v: number) => pl + ((v - lo) / (hi - lo || 1)) * (W - pl - pr), Y = (k: number) => TOP + (L - k) * s;
    const yAx = TOP + L * s + 4;
    let o = `<line x1="${pl}" x2="${W - pr}" y1="${yAx}" y2="${yAx}" class="ax"/>`;
    for (let v = lo; v <= hi + step / 2; v += step) {
      const vv = Math.abs(v) < step / 1e6 ? 0 : v;
      o += `<line x1="${X(vv)}" x2="${X(vv)}" y1="${yAx}" y2="${yAx + 4}" class="ax"/><text x="${X(vv)}" y="${yAx + 15}" text-anchor="middle">${vv === 0 ? "0" : +vv.toFixed(3)}</text>`;
    }
    o += `<line x1="${X(0)}" x2="${X(0)}" y1="${TOP - 4}" y2="${yAx}" class="zero"/><text x="${Math.min(X(0), W - pr - 80)}" y="${yAx + 28}" class="zl">↑ 0 = even odds</text>`;
    for (let l = 0; l < L; l += 5) o += `<line x1="${pl}" x2="${W - pr}" y1="${Y(l)}" y2="${Y(l)}" class="grid"/>`;
    const ends: { n: string; v: number; col: string }[] = [];
    for (const [r, col, n] of [[a.rm, A_COL, "A"], [b.rm, B_COL, "B"]] as const) {
      let d = ""; for (let k = 0; k <= L; k++) d += `${k ? "L" : "M"}${X(r.get(k)).toFixed(1)},${Y(k).toFixed(1)}`;
      o += `<path d="${d}" fill="none" stroke="${col}" stroke-width="1.8"/><circle cx="${X(r.get(L))}" cy="${Y(L)}" r="3" fill="${col}"/>`;
      ends.push({ n, v: r.get(L), col });
    }
    // end labels at their own endpoints; stacked when the two endpoints are close
    const close = Math.abs(X(ends[0].v) - X(ends[1].v)) < 56;
    ends.sort((p, q) => p.v - q.v).forEach((e, i) => {
      const x = Math.max(pl + 18, Math.min(W - pr - 18, X(e.v)));
      o += `<text x="${x}" y="${close ? TOP - 22 + i * 13 : TOP - 8}" text-anchor="middle" style="fill:${e.col}">${e.n} ${e.v.toFixed(2)}</text>`;
    });
    const hl = (pin || hov)?.l ?? -9;
    if (hl >= 0) o += `<rect x="1" y="${y(hl)}" width="${W - 2}" height="${s}" class="rowhl"/>`;
    const svg = $("mc"); svg.setAttribute("width", String(W)); svg.setAttribute("height", String(g.Hsvg)); svg.innerHTML = o;
    $("mfoot").innerHTML = `<span>log-odds of “${esc(it.j_plus)}” over “${esc(it.j_minus)}”, if read off after each layer${clamp ? " · clamped run" : ""}</span><span><i class="ln" style="background:${A_COL}"></i>A <i class="ln" style="background:${B_COL}"></i>B</span>`;
  }

  // ---------------- hover tooltip (A, B, B − A of one cell; 3 rows max) and pinning
  const tip = $("ptip");
  function cellTip(e: MouseEvent, l: number, h: number) {
    const dd = dAttr(D, clamp);
    tip.textContent = `${partName(l, h)}${clamp ? " · clamped run" : ""}\nA ${sgn(val("a", l, h), 4)}   B ${sgn(val("b", l, h), 4)}\nChange, B − A ${sgn(val("d", l, h), 4)} ${dd.exported ? "(pair export)" : "(computed in this browser)"}`;
    tip.hidden = false; tip.style.left = e.clientX + 14 + "px"; tip.style.top = e.clientY + 14 + "px";
  }
  $("lad").addEventListener("mousemove", (e) => {
    const c = (e.target as Element).closest<SVGElement>(".cell"); const s = c ? { l: +c.dataset.l!, h: +c.dataset.h! } : null;
    if (s) cellTip(e, s.l, s.h); else tip.hidden = true;
    if (JSON.stringify(s) === JSON.stringify(hov)) return; hov = s; ladder(); if (!pin) prompt();
  });
  $("lad").addEventListener("mouseleave", () => { tip.hidden = true; hov = null; ladder(); if (!pin) prompt(); });
  $("lad").addEventListener("click", (e) => { const c = (e.target as Element).closest<SVGElement>(".cell"); if (!c) return;
    const s = { l: +c.dataset.l!, h: +c.dataset.h! }; setPin(pin && pin.l === s.l && pin.h === s.h ? null : s); });
  function setPin(s: Sel) {
    pin = s; ctx.set("sel", s ? `${s.l},${s.h}` : null);
    $("work").classList.toggle("pinned", !!s); drawer(); ladder(); prompt();
  }

  // ---------------- the pin drawer: its own grid column, never over the chart
  function drawer() {
    const dr = $("drawer");
    if (!pin) { dr.hidden = true; dr.innerHTML = ""; return; }
    const top5 = ringed(rings(), pin.l, pin.h), dd = dAttr(D, clamp);
    const taint = failing.length ? `<div class="badp">✗ An accounting check failed (${esc(failing.map(checkLine).join(" · "))}): these numbers do not add up.</div>` : "";
    let body: string;
    if (pin.l < 0) {
      body = cmpTable([{ label: `Contribution to the answer${clamp ? ", clamped run" : ""}`, tip: "readout.embed_attr · d_embed_attr", a: S(D.A).embed, b: S(D.B).embed, d: { v: dd.embed, how: dd.exported ? "exp" : "calc", src: dd.exported ? "d_embed_attr, pair export" : "computed in this browser" } }]) + CHANGE_FOOT;
    } else {
      const sl = pin.h >= 0 ? { kind: "head" as const, l: pin.l, h: pin.h, t: ro } : { kind: "mlp" as const, l: pin.l, t: ro };
      body = inspectorHTML(D, sl, { pinned: true, clamp, bare: true });
    }
    dr.hidden = false;
    dr.innerHTML = `<div class="dr-h"><i class="pinbox" title="The pinned cell has this thick white outline in the ladder"></i><h3>${esc(pin.l < 0 ? "Embedding term" : pin.h < 0 ? `MLP block · layer ${pin.l}` : `Head ${pin.h} · layer ${pin.l}`)}</h3><span class="sp"></span><button id="unpin" title="Unpin (Esc)">Esc ✕</button></div>
      <div class="muted dr-sub">pinned · ${top5 ? `<span class="ringtxt">one of the 5 largest changes</span>` : "click another cell to move the pin"}${pin.l >= 0 && pin.h >= 0 ? ` · <span class="nw">keys <kbd>[</kbd> <kbd>]</kbd>: previous / next head in this layer</span>` : ""}</div>${taint}${body}`;
    $("unpin").onclick = () => setPin(null);
  }

  // ---------------- the prompt: open parts as text; all template text on one line, with its Σ attention (rule 8)
  const weights = (r: Run, l: number, h: number) => { const w = new Map<number, number>(); for (const k of topKeys(r, l, h, ro, 16)) w.set(k.key, (w.get(k.key) || 0) + k.w); return w; };
  function prompt() {
    const sel = pin || hov, head = sel && sel.h >= 0 && sel.l >= 0 ? sel : null;
    const wa = head ? weights(D.A, head.l, head.h) : null, wb = head ? weights(D.B, head.l, head.h) : null;
    const v = (t: number) => (!head ? 0 : face === "a" ? wa!.get(t) || 0 : face === "b" ? wb!.get(t) || 0 : (wb!.get(t) || 0) - (wa!.get(t) || 0));
    // A face: A's weights in A's colour; B face: B's in B's colour; B − A: teal = B reads it more, warm grey = A reads it more
    const bg = (w: number) => (!w ? "" : `background:${mix("#0c0c0d", w < 0 ? A_COL : face === "a" ? A_COL : B_COL, Math.min(0.9, Math.sqrt(Math.abs(w)) * 1.1))};${Math.abs(w) > 0.3 ? "color:#111;" : ""}`);
    const hidden = segs.filter((sg) => !sg.open), hn = hidden.reduce((a, sg) => a + sg.n, 0);
    let sum = 0; if (head) for (const sg of hidden) for (let t = sg.a; t <= sg.b; t++) sum += v(t);
    let html = hidden.length ? `<button class="tpl${query && hidden.some((sg) => sg.text.toLowerCase().includes(query)) ? " hit" : ""}" id="tpl" title="${esc(hidden.map((sg) => sg.label).join(" · "))}\nClick to ${tplOpen ? "collapse" : "show"} it">${tplOpen ? "▾" : "⋯"} template text · ${hidden.length} parts · ${hn} tokens${head ? ` · total attention ${sum >= 0 && face === "d" ? "+" : ""}${sum.toFixed(2)}` : ""}</button>` : "";
    for (const sg of segs) {
      if (!sg.open && !tplOpen) continue;
      if (sg.kind === "question") html += `<div class="cap seglab" title="prompt part: ${esc(sg.label)} (manifest.segments)">${isBank(D.A) ? "Scenario" : "Survey question"}</div>`;
      let part = "";
      for (let t = sg.a; t <= sg.b; t++) {
        const tx = D.A.m.tokens[t].text, cls = `tk${t === ro ? " ro" : ""}${query && tx.toLowerCase().includes(query) ? " hit" : ""}`;
        const show = t === ro ? "t*" : tx === "\n" ? "\n" : esc(tx);
        part += `<span class="${cls}" data-t="${t}" style="${bg(v(t))}"${t === ro ? ` title="answer position (t*): the token “${esc(tx)}”${tx.trim() === "" ? " (a space)" : ""}. The model's next token is the answer code; its probabilities are in the answer strip above."` : ""}>${show}</span>${t === ro ? `<span class="tnext" title="what the model writes next: one of the response codes (read as probabilities at t*)">→ ${D.A.m.item.codes.map((c) => esc(c)).join(" / ")}</span>` : ""}`;
      }
      html += sg.open ? part : `<span class="tplx">${part}</span>`;
      if (sg.kind !== "template" && sg.kind !== "readout" && !sg.text.endsWith("\n")) html += "\n";
    }
    $("ptext").innerHTML = html;
    $("pkey").innerHTML = head
      ? `shaded: where head ${head.h} of layer ${head.l} looks, from the answer position (t*) · ${face === "a" ? `<span style="color:${A_COL}">A</span>` : face === "b" ? `<span style="color:${B_COL}">B</span>` : `B − A, <span class="calc">computed in this browser</span>: <span style="color:${B_COL}">teal</span> = B reads it more, <span style="color:${A_COL}">grey</span> = A reads it more`} · top-16 weights (attn_topk_val)`
      : `pin or hover a head to shade the words it reads · <kbd>/</kbd> find`;
  }
  $("ptext").addEventListener("click", (e) => { if ((e.target as Element).closest("#tpl")) { tplOpen = !tplOpen; ctx.set("tpl", tplOpen ? 1 : null); prompt(); } });
  $("ptext").addEventListener("mousemove", (e) => {
    const tk = (e.target as Element).closest<HTMLElement>(".tk"); if (!tk) { tip.hidden = true; return; }
    const t = +tk.dataset.t!, sel = pin || hov;
    let s = `token ${t}: “${tokText(D.A.m.tokens[t].text)}”`;
    if (sel && sel.h >= 0 && sel.l >= 0) { const a = weights(D.A, sel.l, sel.h).get(t) || 0, b = weights(D.B, sel.l, sel.h).get(t) || 0; s += `\nhead ${sel.h}, layer ${sel.l}, attention from the answer position: A ${a.toFixed(3)}  B ${b.toFixed(3)}\nChange, B − A ${sgn(b - a)} (computed in this browser)`; }
    tip.textContent = s; tip.hidden = false; tip.style.left = e.clientX + 14 + "px"; tip.style.top = e.clientY + 14 + "px";
  });
  $("ptext").addEventListener("mouseleave", () => (tip.hidden = true));
  const qi = $<HTMLInputElement>("q");
  qi.oninput = () => {
    query = qi.value.toLowerCase().trim(); if (query.length < 2) query = "";
    ctx.set("q", query || null);
    prompt(); root.querySelector(".tk.hit")?.scrollIntoView({ block: "center" });
  };
  qi.onkeydown = (e) => { if (e.key === "Escape") { e.stopPropagation(); qi.value = ""; qi.dispatchEvent(new Event("input")); qi.hidden = true; qi.blur(); } };

  // ---------------- controls and keys
  root.querySelectorAll<HTMLElement>("[data-face]").forEach((b) => (b.onclick = () => { face = b.dataset.face as Face; ctx.set("face", face === "d" ? null : face); ladder(); prompt(); }));
  const setClamp = (on: boolean) => { clamp = on; ctx.set("clamp", on ? 1 : null); ctx.mode(on); strip(); ladder(); drawer(); prompt(); };
  $("clamp").onclick = () => setClamp(!clamp);
  window.addEventListener("keydown", (e) => {
    const t = e.target as HTMLElement;
    if (e.metaKey || e.ctrlKey || e.altKey || /^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName) || document.querySelector("dialog[open]")) return;
    if (e.key === "Escape") setPin(null);
    else if (e.key === "a" || e.key === "A") openLearn(D, "answer");
    else if (e.key === "c" || e.key === "C") setClamp(!clamp);
    else if (e.key === "/") { e.preventDefault(); qi.hidden = false; qi.focus(); }
    else if ((e.key === "[" || e.key === "]") && pin && pin.l >= 0 && pin.h >= 0) setPin({ l: pin.l, h: (pin.h + (e.key === "]" ? 1 : H - 1)) % H });
  }, { signal: ctx.signal });

  // ---------------- initial state from the URL. Nothing is pinned at rest (v3); sel= restores a pin.
  const sp = ctx.get("sel");
  if (sp && sp !== "none") { const [l, h] = sp.split(",").map(Number); pin = l >= -1 && l < L && h >= -2 && h < H ? { l, h } : null; }
  if (ctx.get("q")) { qi.hidden = false; qi.value = ctx.get("q")!; query = qi.value.toLowerCase(); }
  $("work").classList.toggle("pinned", !!pin);
  ctx.mode(clamp);
  strip(); drawer(); ladder(); prompt();
  const ro_ = new ResizeObserver(() => ladder()); ro_.observe($("work"));
  document.addEventListener("sca2:heavy", () => { prompt(); if (pin) drawer(); }, { signal: ctx.signal });
  requestAnimationFrame(() => { ladder(); ctx.ready(); });
  return () => { ro_.disconnect(); tip.hidden = true; };
}
