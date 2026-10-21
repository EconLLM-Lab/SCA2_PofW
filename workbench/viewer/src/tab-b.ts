// Tab B, the matrix (v3, design/layout-v3/SYSTEM.md + DECISION.md). One map, one face at a time:
// A, B, or ‖B − A‖ (the default). Rows are layers (layer 0 at the bottom), columns are tokens; template text
// is squeezed to 2 px columns, never dropped. Default quantity: the attention write ‖a‖ (attn_norm /
// d_attn_norm, Augusto's ruling), with the running state (resid) and the MLP write (mlp) selectable.
// Colour is linear and clipped at the 99th percentile; the footer prints the clip value and the max (rule 5).
// At rest: the answer strip, the map, the margin column on the map's rows. Hover = crosshair + tooltip;
// click pins a cell and opens the same drawer as the ladder (its own grid column).
// URL keys: qty=attn|resid|mlp (attn default), face=a|b|d (d default), fold=0, pin=l,t.

import type { Bundle, Tensor } from "./data";
import { NO_PER_HEAD } from "./notshipped";
import type { Ctx } from "./main";
import {
  A_COL, B_COL, C, CHANGE_FOOT, answerStrip, checkLine, checksOf, cmpTable, drawerHTML, esc, failedWho, faceTainted, fmt, inspectorHTML,
  mix, openLearn, segmentsOf, short, tokText, type Slice,
} from "./common";

type Qty = "attn" | "resid" | "mlp";
type Face = "a" | "b" | "d";
const QTY: [Qty, string, string][] = [["attn", "attention addition ‖a‖", "Size of what each layer's attention heads add to the running state (attn_norm)"], ["resid", "running state ‖h‖", "Size of the running state after each layer (resid_norm)"], ["mlp", "MLP block addition ‖m‖", "Size of what each layer's MLP block adds to the running state (mlp_norm)"]];
const FACES: [Face, string][] = [["a", "A"], ["b", "B"], ["d", "size of change ‖B − A‖"]];
const FACE_TIP: Record<Face, string> = { a: "A: the base model", b: "B: the model compared with the base (a country adapter or a sign prompt)", d: "The size of the change: how far B's vector is from A's, ‖B − A‖ (never negative)" };
const SRC = { resid: ["resid_norm", "d_resid_norm"], attn: ["attn_norm", "d_attn_norm"], mlp: ["mlp_norm", "d_mlp_norm"] } as const;

export function mountMatrix(root: HTMLElement, D: Bundle, ctx: Ctx): () => void {
  const L = D.A.m.model.n_layers, H = D.A.m.model.n_heads, T = D.A.m.tokens.length, ro = D.A.m.readout.position, it = D.A.m.item;
  const checks = checksOf(D), bad = failedWho(checks), failing = checks.filter((c) => !c.ok);
  root.className = "tab-b v3";
  root.innerHTML = `
    <section id="answer" data-obj="answer">${answerStrip(D)}</section>
    <div id="work" class="b-work">
      <section class="obj" id="map" data-obj="map"><header><span class="cap">Size of</span>
          <span class="seg" id="qty">${QTY.map(([k, t, tip]) => `<button data-q="${k}" title="${esc(tip)}">${esc(t)}</button>`).join("")}</span><span class="sp"></span>
          <span class="seg" id="faces">${FACES.map(([k, t]) => `<button data-face="${k}" title="${FACE_TIP[k]}">${t}</button>`).join("")}</span></header>
        <canvas id="cv"></canvas><div class="foot" id="bfoot"></div></section>
      <section class="obj" id="mchart" data-obj="margin"><header><span class="cap" title="If the model stopped after each layer and answered, this is the log-odds it would give (read off the running state, final rescaling held fixed; running_margin: h^l·w at the answer position). Early and middle layers are rough. A line near 0 early means no readable preference yet, not neutral.">Log-odds by layer</span><span class="sp"></span><span id="mleg"></span></header>
        <svg id="mc"></svg><div class="foot" id="mfoot"></div></section>
      <aside id="drawer" class="obj" data-obj="drawer" hidden></aside>
    </div>
    <div id="ptip" hidden></div>`;
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => root.querySelector<T>("#" + id)!;
  const segs = segmentsOf(D.A);
  let qty: Qty = (["attn", "resid", "mlp"].includes(ctx.get("qty") ?? "") ? ctx.get("qty") : "attn") as Qty;
  let face: Face = (["a", "b", "d"].includes(ctx.get("face") ?? "") ? ctx.get("face") : "d") as Face;
  let squeeze = ctx.get("fold") !== "0";
  let hov: { l: number; t: number } | null = null, pin: { l: number; t: number } | null = null;
  const rows = () => (qty === "resid" ? L + 1 : L);
  const tensor = (f: Face): Tensor => (f === "d" ? D.P.t[SRC[qty][1]] : (f === "a" ? D.A : D.B).t[SRC[qty][0]]);
  const rowName = (l: number) => (qty === "resid" ? (l === 0 ? "state before layer 0" : `state after layer ${l - 1}`) : `layer ${l}`);

  // ---------------- columns: every token keeps one; squeezed (template) columns are 2 px
  const AX = 34, BAND = 18;
  let cx: number[] = [], cw: number[] = [], W = 600, rowH = 8, Hc = 400;
  function columns(w: number) {
    const nOpen = segs.filter((s) => s.open).reduce((a, s) => a + s.n, 0), nSq = T - nOpen, thin = squeeze ? 2 : 0;
    const wide = squeeze ? (w - nSq * thin) / Math.max(1, nOpen) : w / T; let x = AX; cx = []; cw = [];
    for (const s of segs) for (let t = s.a; t <= s.b; t++) { const ww = !squeeze || s.open ? wide : thin; cx.push(x); cw.push(ww); x += ww; }
  }
  const tAt = (x: number) => { for (let t = 0; t < T; t++) if (x < cx[t] + cw[t]) return t; return T - 1; };
  const yRow = (l: number) => BAND + (rows() - 1 - l) * rowH;

  /** p99 clip and max of one face, linear. */
  function scaleOf(tn: Tensor) {
    const v = Array.from(tn.data).sort((a, b) => a - b);
    return { p99: v[Math.floor(v.length * 0.99)] || 1, max: v[v.length - 1] };
  }
  const faceCol = () => (face === "a" ? A_COL : face === "b" ? B_COL : C.delta);

  function draw() {
    const box = $("map"), head = (box.querySelector("header") as HTMLElement).offsetHeight + 10;
    W = Math.max(300, box.clientWidth - AX - 4); columns(W);
    const R = rows(), availH = box.clientHeight - head - $("bfoot").offsetHeight - 14 - BAND - 22;
    rowH = Math.max(3, Math.min(22, availH / R)); Hc = BAND + R * rowH + 20;
    const tn = tensor(face), sc = scaleOf(tn), col = faceCol(), tainted = faceTainted(face, bad);
    const c = $<HTMLCanvasElement>("cv"), dpr = devicePixelRatio || 1, Wc = W + AX;
    c.style.width = Wc + "px"; c.style.height = Hc + "px"; c.width = Wc * dpr; c.height = Hc * dpr;
    const g = c.getContext("2d")!; g.scale(dpr, dpr);
    for (let l = 0; l < R; l++) for (let t = 0; t < T; t++) {
      g.fillStyle = mix("#141416", col, Math.min(1, tn.get(l, t) / sc.p99));
      g.fillRect(cx[t], yRow(l), Math.max(1, cw[t] - (cw[t] > 4 ? 0.5 : 0)), rowH - (rowH > 3 ? 0.5 : 0));
    }
    // layer axis: every 5th, the last, and the hovered/pinned row
    g.font = "11px ui-monospace, Menlo, monospace"; g.textBaseline = "middle"; g.textAlign = "right";
    const sel = (hov ?? pin)?.l ?? -9;
    for (let l = 0; l < R; l++) if (l % 5 === 0 || l === R - 1 || l === sel) { g.fillStyle = l === sel ? "#fff" : "#8a8a8f"; g.fillText(qty === "resid" ? `h${l}` : `L${l}`, AX - 6, yRow(l) + rowH / 2); }
    // segment band: open parts labelled; click a band to open or squeeze it
    g.textAlign = "left";
    for (const sg of segs) {
      const x0 = cx[sg.a], x1 = cx[sg.b] + cw[sg.b];
      g.fillStyle = sg.open ? "#2a2a2e" : "#1a1a1d"; g.fillRect(x0, 2, Math.max(1, x1 - x0 - 1), BAND - 6);
      if (x1 - x0 > 34) { g.save(); g.beginPath(); g.rect(x0 + 2, 0, x1 - x0 - 6, BAND); g.clip(); g.fillStyle = sg.open ? "#d8d6d0" : "#77777c"; g.fillText(sg.kind === "readout" ? "t*" : sg.label, x0 + 5, BAND / 2); g.restore(); }
    }
    // t*: a white frame over its column
    g.strokeStyle = "#fff"; g.lineWidth = 1.5; g.strokeRect(cx[ro] + 0.75, BAND, Math.max(1, cw[ro] - 1.5), R * rowH);
    // crosshair (hover): faint row + column; pin: thick white cell outline
    if (hov) { g.fillStyle = "#ffffff14"; g.fillRect(AX, yRow(hov.l), W, rowH); g.fillRect(cx[hov.t], BAND, Math.max(2, cw[hov.t]), R * rowH);
      g.strokeStyle = "#bbb"; g.lineWidth = 1; g.strokeRect(cx[hov.t] - 0.5, yRow(hov.l) - 0.5, Math.max(2, cw[hov.t]) + 1, rowH + 1); }
    if (pin && pin.l < R) { g.strokeStyle = "#fff"; g.lineWidth = 3; g.strokeRect(cx[pin.t] - 2, yRow(pin.l) - 2, Math.max(2, cw[pin.t]) + 4, rowH + 4); }
    // token labels under the open columns (wide enough only)
    g.font = "10px ui-monospace, Menlo, monospace"; g.fillStyle = "#77777c"; g.textBaseline = "top";
    let lastX = -99; for (let t = 0; t < T; t++) if (cw[t] >= 9 && cx[t] - lastX > 26) { lastX = cx[t]; g.fillStyle = t === ro ? "#fff" : t === (hov ?? pin)?.t ? "#fff" : "#6a6a70"; g.fillText(t === ro ? "t*" : tokText(D.A.m.tokens[t].text).slice(0, 4), cx[t], BAND + R * rowH + 5); }
    box.classList.toggle("tainted", tainted);
    root.querySelectorAll<HTMLElement>("[data-face]").forEach((b) => { b.classList.toggle("on", b.dataset.face === face); b.classList.toggle("bad", faceTainted(b.dataset.face!, bad)); });
    root.querySelectorAll<HTMLElement>("[data-q]").forEach((b) => b.classList.toggle("on", b.dataset.q === qty));
    const nSq = segs.filter((s) => !s.open).reduce((a, s) => a + s.n, 0);
    const why = tainted ? failing.filter((c) => face === "d" || c.who === face.toUpperCase()).map(checkLine).join(" · ") : "";
    $("bfoot").innerHTML = `<div class="krow"><i class="kbar" style="background:linear-gradient(90deg,#141416,${col})"></i><span><b class="fl ${tainted ? "bad" : ""}">${face === "d" ? "size of the change ‖B − A‖" : face.toUpperCase()}</b> · 0 → <span class="num">${fmt(sc.p99, 3)}</span> (99th percentile, linear; brighter cells are clipped) · max <span class="num">${fmt(sc.max, 3)}</span> · ${face === "d" ? `pair <code>${SRC[qty][1]}</code>, its own scale` : `run <code>${SRC[qty][0]}</code> of ${face.toUpperCase()}`}</span></div>
      <div class="krow"><span>rows: ${qty === "resid" ? "running state h0 (start) … h" + L : "layers, L0 at the bottom"} · white frame: the answer position (t*) · ${squeeze ? `${nSq} template tokens (the fixed chat wrapper) squeezed to 2 px` : "template text full width"} (<button class="lnk" id="fold">${squeeze ? "show full width" : "squeeze"}</button>)${why ? ` · <span class="sumline bad">accounting check failed: ${esc(why)}</span>` : ""}</span></div>`;
    $("fold").onclick = () => { squeeze = !squeeze; ctx.set("fold", squeeze ? null : 0); draw(); };
    margin();
  }

  // ---------------- margin column: running_margin of A and B on the map's rows
  function margin() {
    const host = $("mchart"), Wm = Math.max(150, host.clientWidth), R = rows(), a = D.A.t.running_margin, b = D.B.t.running_margin;
    // after k layers: on a layer map, the boundary above row k−1; on the state map, the centre of row k
    const OY = 18, Y = (k: number) => OY + (qty === "resid" ? yRow(k) + rowH / 2 : BAND + (R - k) * rowH);
    let lo = 0, hi = 0; for (const r of [a, b]) for (const v of r.data) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    const span = hi - lo || 1, raw = span / 3, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 5, 10].map((k) => k * mag).find((k) => k >= raw)!;
    lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    const pl = 10, pr = 12, X = (v: number) => pl + ((v - lo) / (hi - lo || 1)) * (Wm - pl - pr), yAx = OY + BAND + R * rowH + 4;
    let o = `<line x1="${pl}" x2="${Wm - pr}" y1="${yAx}" y2="${yAx}" class="ax"/>`;
    for (let v = lo; v <= hi + step / 2; v += step) { const vv = Math.abs(v) < step / 1e6 ? 0 : v; o += `<line x1="${X(vv)}" x2="${X(vv)}" y1="${yAx}" y2="${yAx + 4}" class="ax"/><text x="${X(vv)}" y="${yAx + 15}" text-anchor="middle">${vv === 0 ? "0" : +vv.toFixed(3)}</text>`; }
    o += `<line x1="${X(0)}" x2="${X(0)}" y1="${OY + BAND - 4}" y2="${yAx}" class="zero"/>`;
    const sel = (hov ?? pin)?.l;
    if (sel != null) o += `<rect x="1" y="${OY + yRow(sel)}" width="${Wm - 2}" height="${rowH}" class="rowhl"/>`;
    const ends: { n: string; v: number; col: string }[] = [];
    for (const [r, col, n] of [[a, A_COL, "A"], [b, B_COL, "B"]] as const) {
      let d = ""; for (let k = 0; k <= L; k++) d += `${k ? "L" : "M"}${X(r.get(k)).toFixed(1)},${Y(k).toFixed(1)}`;
      o += `<path d="${d}" fill="none" stroke="${col}" stroke-width="1.8"/><circle cx="${X(r.get(L))}" cy="${Y(L)}" r="3" fill="${col}"/>`;
      ends.push({ n, v: r.get(L), col });
    }
    const close = Math.abs(X(ends[0].v) - X(ends[1].v)) < 56;
    ends.sort((p, q) => p.v - q.v).forEach((e, i) => { const x = Math.max(pl + 18, Math.min(Wm - pr - 18, X(e.v))); o += `<text x="${x}" y="${close ? OY + BAND - 18 + i * 12 : OY + BAND - 6}" text-anchor="middle" style="fill:${e.col}">${e.n} ${e.v.toFixed(2)}</text>`; });
    const svg = $("mc"); svg.setAttribute("width", String(Wm)); svg.setAttribute("height", String(yAx + 22)); svg.style.marginTop = `-${OY}px`; svg.innerHTML = o;
    $("mfoot").innerHTML = `<span>log-odds of “${esc(it.j_plus)}” over “${esc(it.j_minus)}”, if the model stopped after each layer and answered · dashed: 0 = even odds</span>`;
    $("mleg").innerHTML = `<i class="ln" style="background:${A_COL}"></i>A <i class="ln" style="background:${B_COL}"></i>B`;
  }

  // ---------------- hover: crosshair + tooltip (A, B, ‖B − A‖ of one cell); click pins
  const tip = $("ptip"), cv = $<HTMLCanvasElement>("cv");
  const at = (e: MouseEvent) => { const r = cv.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  cv.addEventListener("mousemove", (e) => {
    const { x, y } = at(e), R = rows();
    if (y < BAND) { cv.style.cursor = "pointer"; const t = tAt(x), sg = segs.find((q) => t >= q.a && t <= q.b); tip.hidden = false; tip.textContent = sg ? `${sg.label} · ${sg.n} tokens · click to ${sg.open ? "squeeze" : "open"}` : ""; tip.style.left = e.clientX + 14 + "px"; tip.style.top = e.clientY + 14 + "px"; return; }
    cv.style.cursor = "crosshair";
    const l = R - 1 - Math.floor((y - BAND) / rowH);
    if (l < 0 || l >= R || x < AX) { tip.hidden = true; if (hov) { hov = null; draw(); } return; }
    const t = tAt(x), [an, dn] = SRC[qty];
    tip.textContent = `${rowName(l)} · token ${t} “${tokText(D.A.m.tokens[t].text)}”${t === ro ? " (answer position)" : ""}\nA ${fmt(D.A.t[an].get(l, t), 4)}   B ${fmt(D.B.t[an].get(l, t), 4)}\nSize of change ‖B − A‖ ${fmt(D.P.t[dn].get(l, t), 4)} (pair export)`;
    tip.hidden = false; tip.style.left = e.clientX + 14 + "px"; tip.style.top = e.clientY + 14 + "px";
    if (!hov || hov.l !== l || hov.t !== t) { hov = { l, t }; draw(); }
  });
  cv.addEventListener("mouseleave", () => { tip.hidden = true; hov = null; draw(); });
  cv.addEventListener("click", (e) => {
    const { x, y } = at(e);
    if (y < BAND) { const t = tAt(x), sg = segs.find((q) => t >= q.a && t <= q.b); if (sg && sg.kind !== "readout") { sg.open = !sg.open; draw(); } return; }
    if (!hov) return;
    setPin(pin && pin.l === hov.l && pin.t === hov.t ? null : { ...hov });
  });
  function setPin(s: { l: number; t: number } | null) {
    pin = s; ctx.set("pin", s ? `${s.l},${s.t}` : null);
    $("work").classList.toggle("pinned", !!s); drawer(); draw();
  }

  // ---------------- the drawer (same component as the ladder's)
  function drawer() {
    const dr = $("drawer");
    if (!pin) { dr.hidden = true; dr.innerHTML = ""; return; }
    const { l, t } = pin, tok = `token ${t} “${tokText(D.A.m.tokens[t].text)}”${t === ro ? " · answer position (t*)" : ""}`;
    let body: string;
    if (qty === "attn") {
      const a = D.A.t, b = D.B.t, p = D.P.t;
      const vmax = Math.max(...Array.from({ length: H }, (_, h) => Math.max(a.head_norm.get(l, h, t), b.head_norm.get(l, h, t), (p.d_head_norm ? p.d_head_norm.get(l, h, t) : 0)))) || 1;
      body = cmpTable([{ label: "Attention addition ‖a‖", tip: "attn_norm · d_attn_norm", a: a.attn_norm.get(l, t), b: b.attn_norm.get(l, t), d: { v: p.d_attn_norm.get(l, t), how: "len", src: "d_attn_norm" } }])
        + `<div class="sub">The ${H} heads of layer ${l} at this token: <span style="color:${A_COL}">A</span>, <span style="color:${B_COL}">B</span> and <span style="color:var(--delta)">the size of the change ‖B − A‖</span>, on one linear scale (longest ${fmt(vmax, 3)}).</div>`
        + Array.from({ length: H }, (_, h) => `<div class="hrow"><span>h${h}</span><span class="hb3"><i style="top:0;width:${(a.head_norm.get(l, h, t) / vmax * 100).toFixed(1)}%;background:${A_COL}"></i><i style="top:4.5px;width:${(b.head_norm.get(l, h, t) / vmax * 100).toFixed(1)}%;background:${B_COL}"></i><i style="top:9px;height:3px;width:${((p.d_head_norm ? p.d_head_norm.get(l, h, t) : 0) / vmax * 100).toFixed(1)}%;background:${C.delta}"></i></span><span class="num">${fmt((p.d_head_norm ? p.d_head_norm.get(l, h, t) : 0), 3)}</span></div>`).join("")
        + (p.d_head_norm ? "" : `<p class="muted">${NO_PER_HEAD} The bars show A and B only.</p>`)
        + CHANGE_FOOT;
    } else body = inspectorHTML(D, { kind: qty, l, t } as Slice, { pinned: true, bare: true });
    dr.hidden = false;
    dr.innerHTML = drawerHTML(`${qty === "attn" ? "Attention" : qty === "mlp" ? "MLP block" : "Running state"} · ${rowName(l)}`, `pinned · ${esc(short(tok, 60))}`, body, failing);
    $("unpin").onclick = () => setPin(null);
  }

  // ---------------- controls and keys
  root.querySelectorAll<HTMLElement>("[data-q]").forEach((b) => (b.onclick = () => { qty = b.dataset.q as Qty; ctx.set("qty", qty === "attn" ? null : qty); setPin(null); }));
  root.querySelectorAll<HTMLElement>("[data-face]").forEach((b) => (b.onclick = () => { face = b.dataset.face as Face; ctx.set("face", face === "d" ? null : face); draw(); }));
  window.addEventListener("keydown", (e) => {
    const t = e.target as HTMLElement;
    if (e.metaKey || e.ctrlKey || e.altKey || /^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName) || document.querySelector("dialog[open]")) return;
    if (e.key === "Escape") setPin(null);
    else if (e.key === "a" || e.key === "A") openLearn(D, "answer");
  }, { signal: ctx.signal });

  // ---------------- initial state from the URL; nothing pinned at rest
  const pp = ctx.get("pin")?.split(",").map(Number);
  if (pp && pp.length === 2 && pp[0] >= 0 && pp[0] < rows() && pp[1] >= 0 && pp[1] < T) {
    pin = { l: pp[0], t: pp[1] }; const sg = segs.find((g) => pin!.t >= g.a && pin!.t <= g.b); if (sg) sg.open = true;
  }
  ctx.mode(false);
  $("work").classList.toggle("pinned", !!pin);
  drawer(); draw();
  const ro_ = new ResizeObserver(() => draw()); ro_.observe($("work"));
  document.addEventListener("sca2:heavy", () => drawer(), { signal: ctx.signal });
  requestAnimationFrame(() => { draw(); ctx.ready(); });
  return () => { ro_.disconnect(); tip.hidden = true; };
}
