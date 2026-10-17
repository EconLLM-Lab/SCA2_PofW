// Tab B, the matrix: layer × token heatmaps for A, B and ‖B − A‖ with one shared crosshair, and
// two charts of the answer position below. Segments come from manifest.segments (contract @1.1).
// URL keys: qty=resid|attn|mlp, fold=0 (template text full width), pin=l,t, hl=l.

import type { Bundle } from "./data";
import type { Ctx } from "./main";
import {
  A_COL, B_COL, C, inspectorHTML, cmpTable, CHANGE_FOOT, esc, fmt, labelPlus, lm, makeRamp, mix, rampLegend, rampU,
  readoutHTML, segmentsOf, short, tokText, type Slice,
} from "./common";

export function mountMatrix(root: HTMLElement, D: Bundle, ctx: Ctx): () => void {
  const L = D.A.m.model.n_layers, H = D.A.m.model.n_heads, T = D.A.m.tokens.length, ro = D.A.m.readout.position;
  root.className = "tab-b";
  root.innerHTML = `
    <div class="strip"><span class="badge data" title="Every figure on this tab is drawn from the exports of the current pair and prompt">real data · drawn from the exports</span> Each cell is the size of one vector at one layer (rows) and one token (columns). Brighter means larger. This shows where activity is large, not which way it pushes the answer. ${lm("norm", "What is the size of a vector? ↗")}</div>
    <div class="tools">
      <span class="grp">Show <button data-q="resid">Running-state size ‖h‖</button><button data-q="attn">Attention write size ‖a‖</button><button data-q="mlp">MLP write size ‖m‖</button></span>
      <span class="grp">Find a word <input id="q" placeholder="Type a word, press Enter" autocomplete="off" /></span>
      <span class="grp"><button id="fold" title="Squeezed columns are 2 px wide. Every token still has a column."></button></span>
    </div>
    <div class="b-main">
      <div id="left"><div id="maps"></div>
        <div id="charts">
          <div class="chart"><div class="mh"><b>Margin if the answer were read off at each layer</b>${lm("resid", "learn more")}</div><canvas id="c1"></canvas>
            <div class="legend muted"><span><i style="background:${A_COL}"></i>A</span><span><i style="background:${B_COL}"></i>B</span><span><i class="dash" style="border-color:${A_COL}"></i><i class="dash" style="border-color:${B_COL}"></i>clamped run (dashed)</span></div></div>
          <div class="chart"><div class="mh"><b>Push on the margin, layer by layer</b>${lm("dla", "learn more")}</div><canvas id="c2"></canvas>
            <div class="legend muted"><span><i style="background:${A_COL}"></i>A</span><span><i style="background:${B_COL}"></i>B</span><span>filled = attention, outlined = MLP</span><span>right of 0 = toward “${esc(short(labelPlus(D.A), 30))}” (code ${esc(D.A.m.item.j_plus)})</span></div></div>
        </div></div>
      <aside id="side"><div id="ro"></div><div id="insp"></div></aside>
    </div>`;
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => root.querySelector<T>("#" + id)!;
  const segs = segmentsOf(D.A);
  let qty = (ctx.get("qty") as "resid" | "attn" | "mlp") || "resid", squeeze = ctx.get("fold") !== "0";
  let hov: Slice | null = null, pin: Slice | null = null, hovLayer: number | null = ctx.get("hl") != null ? +ctx.get("hl")! : null;
  const SRC = { resid: ["resid_norm", "d_resid_norm", L + 1], attn: ["attn_norm", "d_attn_norm", L], mlp: ["mlp_norm", "d_mlp_norm", L] } as const;
  const NAME = { resid: "size of the running state", attn: "size of the attention write", mlp: "size of the MLP write" };

  // Focus + context: EVERY token keeps a column; squeezed (template) columns are 2 px, open ones wide.
  const AX = 38;   // left gutter for the layer axis
  let cx: number[] = [], cw: number[] = [];
  function columns(W: number) {
    const nOpen = segs.filter((s) => s.open).reduce((a, s) => a + s.n, 0), nSq = T - nOpen, thin = squeeze ? 2 : 0;
    const wide = squeeze ? (W - nSq * thin) / Math.max(1, nOpen) : W / T; let x = AX; cx = []; cw = [];
    for (const s of segs) for (let t = s.a; t <= s.b; t++) { const w = !squeeze || s.open ? wide : thin; cx.push(x); cw.push(w); x += w; }
  }
  const tAt = (x: number) => { for (let t = 0; t < T; t++) if (x < cx[t] + cw[t]) return t; return T - 1; };

  let ROWH = 5; const BAND = 18, TOKH = 58;
  function draw() {
    const [an, dn, R] = SRC[qty];
    const sAB = makeRamp([D.A.t[an], D.B.t[an]]), sD = makeRamp([D.P.t[dn]]);
    const hd = (k: string, lab: string, src: string, i: number) => `<div class="mh"><span><b>${k}</b> · ${lab}</span><span class="muted" title="${esc(src)}">Rows: layers, first at the bottom. ${i === 2 ? '<span style="color:var(--delta)">Colour: its own scale (gold), so it cannot be compared with A and B.</span>' : "Colour: one log scale shared by A and B."} ${i === 0 ? lm("scale", "how are colours scaled?") : i === 2 ? lm("delta", "what is ‖B − A‖?") : ""}</span></div>`;
    $("maps").innerHTML =
      hd("A", `${esc(D.A.m.model.label)}: ${NAME[qty]}, by layer and token`, an, 0) + `<canvas class="hm" data-i="0"></canvas>` +
      hd("B", `${esc(D.B.m.model.label)}: ${NAME[qty]}, by layer and token`, an, 1) + `<canvas class="hm" data-i="1"></canvas>` +
      rampLegend(sAB, "#141416", "#dfe6ee", "A and B", an) +
      hd("‖B − A‖", `how far B's vector is from A's, by layer and token (exact, from both float64 runs)`, dn, 2) + `<canvas class="hm" data-i="2"></canvas>` +
      rampLegend(sD, "#1a1a1c", C.delta, "‖B − A‖", dn);
    const left = $("left"), W = left.clientWidth - 30 - AX; columns(W);
    // fit maps + keys + charts in the window: rows are 2 to 6 px
    const chartH = 150, fixed = 3 * 26 + 3 * BAND + TOKH + 2 * 44 + chartH + 70;
    ROWH = Math.max(2, Math.min(6, Math.floor((left.clientHeight - fixed) / (3 * R))));
    root.querySelectorAll<HTMLCanvasElement>("canvas.hm").forEach((c) => {
      const i = +c.dataset.i!, src = i === 0 ? D.A.t[an] : i === 1 ? D.B.t[an] : D.P.t[dn], s = i === 2 ? sD : sAB;
      const showTok = i === 2, Hh = BAND + R * ROWH + (showTok ? TOKH : 4), dpr = devicePixelRatio || 1, Wc = W + AX;
      c.style.width = Wc + "px"; c.style.height = Hh + "px"; c.width = Wc * dpr; c.height = Hh * dpr; const g = c.getContext("2d")!; g.scale(dpr, dpr);
      const yl = (l: number) => BAND + (R - 1 - l) * ROWH;
      for (let l = 0; l < R; l++) for (let t = 0; t < T; t++) {
        const u = rampU(s, src.get(l, t)); g.fillStyle = i === 2 ? mix("#1a1a1c", C.delta, u) : mix("#141416", "#dfe6ee", u);
        g.fillRect(cx[t], yl(l), Math.max(1, cw[t] - (cw[t] > 4 ? 0.5 : 0)), ROWH - (ROWH > 3 ? 0.5 : 0));
      }
      // layer axis: a tick per layer, labels every 5th and the last, plus the hovered/pinned layer
      g.font = "10px ui-monospace, Menlo, monospace"; g.textBaseline = "middle"; g.textAlign = "right";
      const sel = (pin || hov)?.l ?? hovLayer ?? -9;
      for (let l = 0; l < R; l++) {
        g.fillStyle = "#3a3a3a"; g.fillRect(AX - 4, yl(l) + ROWH / 2 - 0.5, 3, 1);
        const lab = l === sel || l % 10 === 0 || l === R - 1 || (ROWH >= 4 && l % 5 === 0);
        if (lab) { g.fillStyle = l === sel ? "#ffcf5c" : "#999"; g.fillText(qty === "resid" ? `h${l}` : `L${l}`, AX - 6, yl(l) + ROWH / 2); }
      }
      g.textAlign = "left";
      // segment band: labelled spans; click toggles open
      g.font = "10.5px ui-monospace, Menlo, monospace";
      for (const sg of segs) {
        const x0 = cx[sg.a], x1 = cx[sg.b] + cw[sg.b];
        g.fillStyle = sg.kind === "readout" ? "#6b9bff" : sg.open ? "#2c3a52" : "#1d1d1d"; g.fillRect(x0, 2, Math.max(1, x1 - x0 - 1), BAND - 5);
        if (x1 - x0 > 30) { g.save(); g.beginPath(); g.rect(x0 + 2, 0, x1 - x0 - 4, BAND); g.clip(); g.fillStyle = sg.open ? "#e6e6e6" : "#8a8a8a"; g.fillText(sg.label, x0 + 4, BAND / 2); g.restore(); }
      }
      if (showTok) {
        g.font = "10px ui-monospace, Menlo, monospace";
        for (let t = 0; t < T; t++) if (cw[t] >= 6) { g.save(); g.translate(cx[t] + cw[t] / 2 + 3, BAND + R * ROWH + 4); g.rotate(Math.PI / 2);
          g.fillStyle = t === ro ? "#6b9bff" : t === hov?.t || t === pin?.t ? "#ffcf5c" : "#bdbdbd"; g.fillText(tokText(D.A.m.tokens[t].text).slice(0, 9), 0, 0); g.restore(); }
      }
      g.strokeStyle = "#6b9bff"; g.lineWidth = 1.5; g.strokeRect(cx[ro] + 0.5, BAND, cw[ro] - 1, R * ROWH);
      for (const [s2, col] of [[pin, "#ffffff"], [hov, "#ffcf5c"]] as const) if (s2 && s2.l < R) {
        g.strokeStyle = col; g.lineWidth = 1; g.strokeRect(cx[s2.t], BAND, cw[s2.t], R * ROWH); g.strokeRect(AX, yl(s2.l), W, ROWH);
        g.lineWidth = 2; g.strokeRect(cx[s2.t] - 1, yl(s2.l) - 1, cw[s2.t] + 2, ROWH + 1);
      }
      if (hovLayer != null && hovLayer < R) { g.fillStyle = "#6b9bff22"; g.fillRect(AX, yl(hovLayer), W, ROWH); }
      const at = (e: MouseEvent) => { const r = c.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
      c.onmousemove = (e) => {
        const { x, y } = at(e);
        if (y < BAND) { c.style.cursor = "pointer"; const t = tAt(x), sg = segs.find((q) => t >= q.a && t <= q.b); c.title = sg ? `Click to open or squeeze: ${sg.label}` : ""; return; }
        c.title = ""; c.style.cursor = "crosshair"; const l = R - 1 - Math.floor((y - BAND) / ROWH);
        if (l < 0 || l >= R || x < AX) return;
        if (showTok && y > BAND + R * ROWH) { c.title = tokText(D.A.m.tokens[tAt(x)].text); return; }
        const s2 = { kind: qty === "attn" ? "head" : qty, l, t: tAt(x) } as Slice;
        const k = (q: Slice | null) => (q ? `${q.l},${q.t}` : "");
        if (k(s2) !== k(hov)) { hov = s2; draw(); if (!pin) inspect(s2, false); }
      };
      c.onmouseleave = () => { hov = null; draw(); if (!pin) idle(); };
      c.onclick = (e) => {
        const { x, y } = at(e);
        if (y < BAND) { const t = tAt(x), sg = segs.find((q) => t >= q.a && t <= q.b)!; if (sg.kind !== "readout") { sg.open = !sg.open; draw(); } return; }
        if (!hov) return; pin = hov; ctx.set("pin", `${pin.l},${pin.t}`); inspect(pin, true); draw();
      };
    });
    charts(chartH);
  }

  // ---------------- inspector (an attention cell adds the per-head split of that layer)
  function inspect(s: Slice, pinned: boolean) {
    if (qty !== "attn" || s.kind !== "head") { $("insp").innerHTML = inspectorHTML(D, s, { pinned }); return; }
    const a = D.A.t, b = D.B.t, p = D.P.t, l = s.l, t = s.t;
    const vmax = Math.max(...Array.from({ length: H }, (_, h) => Math.max(a.head_norm.get(l, h, t), b.head_norm.get(l, h, t), p.d_head_norm.get(l, h, t))));
    $("insp").innerHTML = `<div class="card ${pinned ? "pinned" : ""}"><div class="card-h"><span>Attention · layer ${l}</span><span class="tag">${pinned ? "pinned (Esc to unpin)" : "preview"}</span>${lm("head", "learn more")}</div>
      <div class="tokline">token ${t}: “<b>${esc(tokText(D.A.m.tokens[t].text))}</b>”${t === ro ? ' <span class="ro">answer position (t*)</span>' : ""}</div>
      ${cmpTable([{ label: "Write size of the whole layer's attention ‖a‖", tip: "attn_norm · d_attn_norm", a: a.attn_norm.get(l, t), b: b.attn_norm.get(l, t), d: { v: p.d_attn_norm.get(l, t), how: "len", src: "d_attn_norm" } }])}
      <div class="sub">The nine heads in this layer. Each has three bars: <span style="color:${A_COL}">A's write size</span>, <span style="color:${B_COL}">B's write size</span>, and <span style="color:var(--delta)">the change</span>. Click a head.</div>
      ${Array.from({ length: H }, (_, h) => `<div class="hrow" data-h="${h}"><span>h${h}</span><span class="hb3">
        <i style="top:0;width:${((a.head_norm.get(l, h, t) / vmax) * 100).toFixed(1)}%;background:${A_COL}"></i>
        <i style="top:4.5px;width:${((b.head_norm.get(l, h, t) / vmax) * 100).toFixed(1)}%;background:${B_COL}"></i>
        <i style="top:9px;height:3px;width:${((p.d_head_norm.get(l, h, t) / vmax) * 100).toFixed(1)}%;background:${C.delta}"></i></span><span class="num">${fmt(p.d_head_norm.get(l, h, t), 3)}</span></div>`).join("")}
      <div class="foot">All bars use one linear scale. The longest bar is ${fmt(vmax, 3)}.</div>${CHANGE_FOOT}</div>`;
    $("insp").querySelectorAll<HTMLElement>(".hrow").forEach((r) => (r.onclick = () => {
      pin = { kind: "head", l, h: +r.dataset.h!, t };
      $("insp").innerHTML = inspectorHTML(D, pin, { pinned: true }) + `<button id="back">← Back to layer ${l} attention</button>`;
      $("back").onclick = () => inspect({ kind: "head", l, h: 0, t }, true);
    }));
  }
  function idle() { $("insp").innerHTML = `<div class="card"><div class="card-h"><span>Compare A and B for one cell</span></div><p class="muted" style="margin:0">Hover a cell: the same layer and token light up in all three maps, and this card compares A, B and the change. Click to pin. Click a band above a map to open or squeeze that part of the prompt.</p></div>`; }
  window.addEventListener("keydown", (e) => { if (e.key === "Escape" && !document.querySelector("dialog[open]")) { pin = null; ctx.set("pin", null); idle(); draw(); } }, { signal: ctx.signal });

  // ---------------- the answer position as two charts (hover a layer → its row lights up in the maps)
  function charts(Hh: number) {
    const setup = (c: HTMLCanvasElement) => { const W = c.parentElement!.clientWidth - 16, dpr = devicePixelRatio || 1; c.style.width = W + "px"; c.style.height = Hh + "px"; c.width = W * dpr; c.height = Hh * dpr; const g = c.getContext("2d")!; g.scale(dpr, dpr); g.font = "10.5px ui-monospace, Menlo, monospace"; return [g, W] as const; };
    {
      const c = $<HTMLCanvasElement>("c1"), [g, W] = setup(c);
      const series = [[D.A.t.running_margin, A_COL, []], [D.B.t.running_margin, B_COL, []], [D.A.t.running_margin_clamped, A_COL, [4, 3]], [D.B.t.running_margin_clamped, B_COL, [4, 3]]] as const;
      let lo = 0, hi = 0; for (const [s] of series) for (const v of s.data) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
      const pl = 40, px = (l: number) => pl + (l / L) * (W - pl - 70), py = (v: number) => 10 + ((hi - v) / (hi - lo || 1)) * (Hh - 34);
      g.strokeStyle = "#333"; g.beginPath(); g.moveTo(pl, py(0)); g.lineTo(W - 70, py(0)); g.stroke();
      g.fillStyle = "#888"; g.textAlign = "right"; g.fillText("0", pl - 6, py(0) + 3); g.fillText(hi.toFixed(1), pl - 6, py(hi) + 4); if (lo < -0.05 * (hi - lo)) g.fillText(lo.toFixed(1), pl - 6, py(lo)); g.textAlign = "left";
      for (let l = 0; l <= L; l += 5) g.fillText(`L${l}`, px(l) - 8, Hh - 8);
      g.fillText("layer →", W - 66, Hh - 8);
      if (hovLayer != null) { g.fillStyle = "#6b9bff22"; g.fillRect(px(hovLayer) - 4, 6, 8, Hh - 30); }
      for (const [s, col, dash] of series) { g.strokeStyle = col; g.setLineDash(dash as unknown as number[]); g.lineWidth = dash.length ? 1.5 : 2; g.beginPath(); for (let l = 0; l <= L; l++) l ? g.lineTo(px(l), py(s.get(l))) : g.moveTo(px(l), py(s.get(l))); g.stroke(); }
      g.setLineDash([]);
      const ya = py(D.A.m.readout.margin), yb = py(D.B.m.readout.margin), sep = Math.abs(ya - yb) < 12 ? 7 : 0;
      g.fillStyle = A_COL; g.fillText(`A ${D.A.m.readout.margin.toFixed(2)}`, W - 64, ya + 3 - (ya <= yb ? sep : -sep));
      g.fillStyle = B_COL; g.fillText(`B ${D.B.m.readout.margin.toFixed(2)}`, W - 64, yb + 3 + (ya <= yb ? sep : -sep));
      c.onmousemove = (e) => { const r = c.getBoundingClientRect(); const l = Math.round(((e.clientX - r.left - pl) / (W - pl - 70)) * L); if (l >= 0 && l <= L && l !== hovLayer) { hovLayer = l; ctx.set("hl", l); draw(); if (!pin) inspect({ kind: "resid", l, t: ro }, false); } };
      c.onmouseleave = () => { hovLayer = null; ctx.set("hl", null); draw(); };
    }
    {
      const c = $<HTMLCanvasElement>("c2"), [g, W] = setup(c);
      const ser = [[D.A.t.attn_attr, D.A.t.mlp_attr, A_COL], [D.B.t.attn_attr, D.B.t.mlp_attr, B_COL]] as const;
      let m = 0; for (const [x, y] of ser) m = Math.max(m, x.absMax(), y.absMax());
      const pl = 36, top = 4, bot = 18, zx = pl + (W - pl) / 2, sx = ((W - pl) / 2 - 14) / (m || 1), rh = (Hh - top - bot) / L;
      g.strokeStyle = "#444"; g.beginPath(); g.moveTo(zx, top); g.lineTo(zx, Hh - bot); g.stroke();
      g.fillStyle = "#888"; g.fillText(`−${m.toFixed(2)}`, pl, Hh - 4); g.textAlign = "right"; g.fillText(`+${m.toFixed(2)}`, W - 2, Hh - 4); g.textAlign = "center"; g.fillText("0", zx, Hh - 4);
      g.textAlign = "right"; g.textBaseline = "middle";
      for (let l = 0; l < L; l++) {
        const y = top + (L - 1 - l) * rh;
        if (l === hovLayer) { g.fillStyle = "#6b9bff22"; g.fillRect(pl, y, W - pl, rh); }
        g.fillStyle = "#3a3a3a"; g.fillRect(pl - 4, y + rh / 2 - 0.5, 3, 1);
        if (l % 5 === 0 || l === L - 1 || l === hovLayer) { g.fillStyle = l === hovLayer ? "#ffcf5c" : "#888"; g.fillText(`L${l}`, pl - 6, y + rh / 2); }
        ser.forEach(([at, mp, col], k) => { const v1 = at.get(l), v2 = mp.get(l), y0 = y + (k * rh) / 2; g.fillStyle = col; g.fillRect(Math.min(zx, zx + v1 * sx), y0 + 0.5, Math.abs(v1 * sx), rh / 4 - 0.5); g.strokeStyle = col; g.lineWidth = 1; g.strokeRect(Math.min(zx, zx + v2 * sx), y0 + rh / 4, Math.abs(v2 * sx), Math.max(0.5, rh / 4 - 1)); });
      }
      g.textAlign = "left"; g.textBaseline = "alphabetic";
      c.onmousemove = (e) => { const r = c.getBoundingClientRect(); const l = L - 1 - Math.floor((e.clientY - r.top - top) / rh); if (l >= 0 && l < L && l !== hovLayer) { hovLayer = l; ctx.set("hl", l); draw(); if (!pin) inspect({ kind: "mlp", l, t: ro }, false); } };
      c.onmouseleave = () => { hovLayer = null; ctx.set("hl", null); draw(); };
    }
  }

  root.querySelectorAll<HTMLElement>("[data-q]").forEach((b) => (b.onclick = () => { qty = b.dataset.q as typeof qty; ctx.set("qty", qty === "resid" ? null : qty); pin = null; ctx.set("pin", null); idle(); sync(); draw(); }));
  $("fold").onclick = () => { squeeze = !squeeze; ctx.set("fold", squeeze ? null : 0); sync(); draw(); };
  function sync() {
    root.querySelectorAll<HTMLElement>("[data-q]").forEach((b) => b.classList.toggle("on", b.dataset.q === qty));
    $("fold").textContent = squeeze ? "Template text: squeezed" : "Template text: full width"; $("fold").classList.toggle("on", squeeze);
  }
  $<HTMLInputElement>("q").onkeydown = (e) => {
    if (e.key !== "Enter") return; const s = $<HTMLInputElement>("q").value.toLowerCase().trim();
    const t = D.A.m.tokens.findIndex((x) => x.text.toLowerCase().trim() === s || (s.length >= 2 && x.text.toLowerCase().includes(s)));
    if (t < 0) return; const sg = segs.find((g) => t >= g.a && t <= g.b)!; sg.open = true;
    pin = { kind: qty === "attn" ? "head" : qty, l: SRC[qty][2] - 1, t } as Slice; ctx.set("pin", `${pin.l},${t}`); draw(); inspect(pin, true);
  };
  $("ro").innerHTML = readoutHTML(D); idle(); sync();
  const pp = ctx.get("pin")?.split(",").map(Number);
  if (pp && pp.length === 2 && pp[0] >= 0 && pp[0] < SRC[qty][2] && pp[1] >= 0 && pp[1] < T) {
    pin = { kind: qty === "attn" ? "head" : qty, l: pp[0], t: pp[1] } as Slice;
    const sg = segs.find((g) => pin!.t >= g.a && pin!.t <= g.b); if (sg) sg.open = true;
    inspect(pin, true);
  }
  draw();
  const ro_ = new ResizeObserver(() => draw()); ro_.observe($("left"));
  requestAnimationFrame(() => ctx.ready());
  return () => ro_.disconnect();
}
