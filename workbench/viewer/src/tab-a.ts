// Tab A, the 3D object (v3, design/layout-v3/SYSTEM.md): the real three.js tensor blocks of scene.ts, with
// template text collapsed into labelled gaps. At rest: the answer strip, a scene bar, scene A, the flat margin
// inset, scene B (default: the change ‖B − A‖, because A and B look almost the same under log heights), and
// the prompt map. Each scene's label is its own header, drawn over its own viewport. Hover = tooltip; click
// pins a block and opens the same drawer as the ladder. "/" opens the word search.
// URL keys: view=single|side|delta (delta default), single=a|b, hscale=log|linear, color=dla|q3|plain, clamp=1,
//           sel=l,h,t (a pinned head), cam=readout|overview|top|front or cam=x,y,z,tx,ty,tz, q, open=all, fly=t.
//
// GPU lifetime: ONE renderer, camera and canvas for the whole app (created on the first visit to this tab),
// so switching tabs never creates a second WebGL context. Every rebuild, and leaving the tab, disposes all
// panel scenes (geometries, materials, textures) and the render lists.

import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Bundle, Run } from "./data";
import type { Ctx } from "./main";
import {
  A_COL, B_COL, C, answerStrip, checksOf, drawerHTML, esc, fmt, inspectorHTML, mix, makeRamp, openLearn, rampU,
  segmentsOf, short, tokText, type Seg, type Slice,
} from "./common";
import {
  FOV, LAYOUT, TensorScene, disposeScene, gapLines, layerStrip, layoutX, makeScale, tokenStrip,
  type ColorMode, type HeightScale, type Scales, type XLayout,
} from "./scene";

const W_ = window as any;
let gl: { canvas: HTMLCanvasElement; renderer: THREE.WebGLRenderer; camera: THREE.PerspectiveCamera; controls: OrbitControls } | null = null;
let rebuildHook: (() => void) | null = null;   // the mounted tab's build(), for context restore

function ensureGL() {
  if (gl) return gl;
  const canvas = document.createElement("canvas");
  canvas.id = "gl";
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  // If the GPU drops the context anyway, say so and rebuild when it comes back (no silent black panels).
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); const n = document.getElementById("glLost"); if (n) n.hidden = false; });
  canvas.addEventListener("webglcontextrestored", () => { const n = document.getElementById("glLost"); if (n) n.hidden = true; rebuildHook?.(); });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
  renderer.setScissorTest(true);
  W_.__renderer = renderer;   // debug handle: renderer.info.memory for leak checks
  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 4000);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  gl = { canvas, renderer, camera, controls };
  return gl;
}

interface Panel { scene: THREE.Scene; ts: TensorScene; label: string; run: Run }

export function mountObject(root: HTMLElement, D: Bundle, ctx: Ctx): () => void {
  const { canvas, renderer, camera, controls } = ensureGL();
  const L = D.A.m.model.n_layers, H = D.A.m.model.n_heads, T = D.A.m.tokens.length, ro = D.A.m.readout.position;
  const failing = checksOf(D).filter((c) => !c.ok);
  root.className = "tab-a v3";
  root.innerHTML = `
    <section id="answer" data-obj="answer">${answerStrip(D)}</section>
    <div id="work" class="a-work"><div class="a-col">
      <section class="obj scenebar" data-obj="scenebar"><header><span class="cap">Show</span>
          <span class="seg">${[["single", "A only"], ["side", "A | B"], ["delta", "A | size of change ‖B − A‖"]].map(([k, t]) => `<button data-view="${k}">${t}</button>`).join("")}</span>
          <select id="single" title="Which model the single scene shows"><option value="a">A</option><option value="b">B</option></select>
          <span class="cap">camera</span><span class="seg">${[["readout", "answer position"], ["overview", "whole"], ["top", "above"], ["front", "layer stack"]].map(([k, t]) => `<button data-cam="${k}">${t}</button>`).join("")}</span>
          <span class="sp"></span><input id="q" placeholder="find a word ⏎" autocomplete="off" hidden /><div id="hits" hidden></div>
          <button id="clamp" class="tog" title="Clamped run: the Quadrant III neurons switched off (set to zero), in the A and B scenes">clamped run</button></header>
        <div class="foot" id="enc"></div></section>
      <div id="stage">
        <section class="scene" id="sceneA" data-obj="sceneA"><header class="cap" id="labelA"></header></section>
        <section class="scene" id="sceneB" data-obj="sceneB"><header class="cap" id="labelB"></header></section>
        <section class="obj inset" id="insetBox" data-obj="inset"><header class="cap">log-odds by layer</header><div id="inset"></div></section>
        <div id="tip" hidden></div>
        <div id="glLost" hidden>The graphics card (GPU) dropped the drawing context (WebGL). Waiting for it to come back (reload the page if it does not).</div></div>
      <section class="obj" id="mini" data-obj="minimap"><div class="foot" id="minicap"></div><canvas id="mm"></canvas></section>
      </div><aside id="drawer" class="obj" data-obj="drawer" hidden></aside></div>
    <select id="hscale" hidden><option value="log">log</option><option value="linear">linear</option></select>
    <select id="color" hidden><option value="dla">contribution to the answer</option><option value="q3">Quadrant III count</option><option value="plain">plain</option></select>`;
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => root.querySelector<T>("#" + id)!;
  $("stage").prepend(canvas);
  const sel = <T extends HTMLElement = HTMLSelectElement>(id: string) => $<T>(id);

  // ---------------- state (from the URL)
  const legacyView = ctx.get("view") === "side" && ctx.get("right") === "delta" ? "delta" : null;
  let view = legacyView || ctx.get("view") || "delta";
  if (!["single", "side", "delta"].includes(view)) view = "delta";
  for (const id of ["single", "hscale", "color"]) if (ctx.get(id)) sel(id).value = ctx.get(id)!;
  let clampOn = ctx.get("clamp") === "1";
  const segs: Seg[] = segmentsOf(D.A);
  if (ctx.get("open") === "all") segs.forEach((s) => (s.open = true));
  let hl = ctx.get("fly") != null ? +ctx.get("fly")! : -1;
  if (hl >= 0 && hl < T) { const sg = segs.find((s) => hl >= s.a && hl <= s.b); if (sg) sg.open = true; } else hl = -1;
  let selection: { l: number; h: number; t: number } | null = null;
  const sp = ctx.get("sel")?.split(",").map(Number);
  if (sp && sp.length === 3 && sp[0] >= 0 && sp[0] < L && sp[1] >= 0 && sp[1] < H && sp[2] >= 0 && sp[2] < T) {
    selection = { l: sp[0], h: sp[1], t: sp[2] };
    const sg = segs.find((s) => selection!.t >= s.a && selection!.t <= s.b); if (sg) sg.open = true;
  }
  let pinnedOther: Slice | null = null;
  let panels: Panel[] = [], lay: XLayout = layoutX(segs, T), framed = false, raf = 0, alive = true, fly: { t0: number; t: THREE.Vector3; p: THREE.Vector3; T: THREE.Vector3; P: THREE.Vector3 } | null = null;

  function makeThreeScene(ts: TensorScene, run: Run): THREE.Scene {
    const s = new THREE.Scene();
    s.background = new THREE.Color("#0b0b0b");
    s.add(new THREE.HemisphereLight(0xffffff, 0x202020, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.4); sun.position.set(-30, 60, -40); s.add(sun);
    s.add(ts.group, tokenStrip(run, lay, hl), layerStrip(L, 0, lay.x[ro] ?? lay.width), gapLines(lay, L));
    return s;
  }
  function disposePanels() {
    for (const p of panels) { p.ts.dispose(); disposeScene(p.scene); }
    panels = [];
    renderer.renderLists.dispose();
  }

  function build() {
    disposePanels();
    lay = layoutX(segs, T);
    const { A: a, B: b, P: pair } = D;
    const hs = sel("hscale").value as HeightScale, color = sel("color").value as ColorMode, clamp = clampOn;
    ctx.mode(clamp);   // v3 frame chip: on whenever any scene draws the clamped run (in the delta view, scene A does)
    $("single").style.display = view === "single" ? "" : "none"; $("clamp").classList.toggle("on", clamp);
    root.querySelectorAll<HTMLElement>("[data-view]").forEach((x) => x.classList.toggle("on", x.dataset.view === view));
    // One scale per quantity, shared by every panel that shows it: equal height = equal value.
    const both = [a, b];
    const dlaMax = Math.max(...both.flatMap((r) => [r.t.head_attr.absMax(), r.t.mlp_attr.absMax(), r.t.head_attr_clamped.absMax(), r.t.mlp_attr_clamped.absMax()]));
    const marginMax = Math.max(...both.flatMap((r) => [r.t.running_margin.absMax(), r.t.running_margin_clamped.absMax()]));
    const scales: Scales = {
      resid: makeScale(both.map((r) => r.t.resid_norm), hs, LAYOUT.RESID_HMAX), head: makeScale(both.map((r) => r.t.head_norm), hs, LAYOUT.HMAX),
      mlp: makeScale(both.map((r) => r.t.mlp_norm), hs, LAYOUT.HMAX), dla: dlaMax, q3: a.m.model.d_ffn * 0.5, margin: marginMax,
    };
    const dScales: Scales = { ...scales, resid: makeScale([pair.t.d_resid_norm], hs, LAYOUT.RESID_HMAX), head: makeScale([pair.t.d_head_norm], hs, LAYOUT.HMAX), mlp: makeScale([pair.t.d_mlp_norm], hs, LAYOUT.HMAX) };
    const add = (run: Run, label: string, delta: boolean) => {
      const ts = new TensorScene(run, delta ? dScales : scales, color, delta ? { pair, a } : null, delta ? false : clamp, lay, { ribbon: false });
      panels.push({ scene: makeThreeScene(ts, run), ts, label, run });
    };
    if (view === "single") { const r = sel("single").value === "b" ? b : a; add(r, `${sel("single").value.toUpperCase()} · ${r.m.model.label}`, false); }
    else { add(a, `A · ${a.m.model.label}`, false); view === "delta" ? add(b, `‖B − A‖ · the change, B = ${b.m.model.label}`, true) : add(b, `B · ${b.m.model.label}`, false); }
    $("labelA").textContent = short(panels[0].label, 60); $("labelA").title = panels[0].label;
    $("labelA").style.color = panels[0].run === D.B && view === "single" ? B_COL : A_COL;
    $("sceneB").hidden = panels.length < 2; $("insetBox").hidden = panels.length < 2;
    if (panels[1]) { $("labelB").textContent = short(panels[1].label, 60); $("labelB").title = panels[1].label; $("labelB").style.color = view === "delta" ? C.delta : B_COL; }
    if (selection) applySelection(selection, false);
    else if (pinnedOther) { const p0 = panels[0]; p0.ts.select(p0.ts.meshOfKind(kindName(pinnedOther)), idOf(p0.ts, pinnedOther)); }
    encoding(color, view === "delta", clamp);
    resize();
    inset(clamp);
    if (!framed && canvas.clientHeight > 200) { framed = true; frameCamera(); }
    drawMini();
    syncUrl();
  }
  rebuildHook = build;

  function syncUrl() {
    ctx.set("view", view === "side" ? null : view);
    ctx.set("right", null);
    ctx.set("single", view === "single" && sel("single").value === "b" ? "b" : null);
    ctx.set("hscale", sel("hscale").value === "log" ? null : sel("hscale").value);
    ctx.set("color", sel("color").value === "dla" ? null : sel("color").value);
    ctx.set("clamp", clampOn ? 1 : null);
    ctx.set("sel", selection ? `${selection.l},${selection.h},${selection.t}` : null);
    ctx.set("open", segs.every((s) => s.open) ? "all" : null);
    ctx.set("fly", hl >= 0 ? hl : null);
  }

  // ---------------- the scene bar's one-line key (the encoding of the faces shown)
  function encoding(color: ColorMode, delta: boolean, clamp: boolean) {
    $("enc").innerHTML = `height = size of the vector (log scale, shared by A and B)${delta ? ` · <span style="color:var(--delta)">‖B − A‖</span> (size of the change): its own scale, gold` : ""} · white frame and lit floor: the answer position (t*)${color === "dla" ? ` · only there: <span style="color:${C.pos}">blue</span> pushes the answer toward “${esc(short(String(D.A.m.item.labels[D.A.m.item.codes.indexOf(D.A.m.item.j_plus)]), 24))}”, <span style="color:${C.neg}">orange</span> toward “${esc(short(String(D.A.m.item.labels[D.A.m.item.codes.indexOf(D.A.m.item.j_minus)]), 24))}”` : color === "q3" ? " · MLP block colour: Quadrant III count" : ""}${clamp ? ` · <span style="color:var(--clamp)">clamped run</span>` : ""}`;
  }
  /** Flat chart of the margin, A and B on one axis (in 3D it would run along depth, not comparable by eye).
   * Zero line, y ticks and layer ticks. */
  function inset(clamp: boolean) {
    const host = $("inset"), W = Math.max(140, host.clientWidth || 170), Hh = 210, pl = 30, pr = 16, pt = 26, pb = 22, src = (r: Run) => (clamp ? r.t.running_margin_clamped : r.t.running_margin);
    let lo = 0, hi = 0; for (const r of [D.A, D.B]) for (const v of src(r).data) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    const raw = (hi - lo || 1) / 3, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 5, 10].map((k) => k * mag).find((k) => k >= raw)!;
    lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    const X = (l: number) => pl + (l / L) * (W - pl - pr), Y = (v: number) => pt + ((hi - v) / (hi - lo || 1)) * (Hh - pt - pb);
    let s = `<line x1="${pl}" x2="${pl}" y1="${pt}" y2="${Hh - pb}" class="ax"/><line x1="${pl}" x2="${W - pr}" y1="${Hh - pb}" y2="${Hh - pb}" class="ax"/>`;
    for (let v = lo; v <= hi + step / 2; v += step) { const vv = Math.abs(v) < step / 1e6 ? 0 : v; s += `<line x1="${pl - 4}" x2="${pl}" y1="${Y(vv)}" y2="${Y(vv)}" class="ax"/><text x="${pl - 6}" y="${Y(vv) + 3.5}" text-anchor="end">${vv === 0 ? "0" : +vv.toFixed(3)}</text>`; }
    for (let l = 0; l <= L; l += 10) s += `<line x1="${X(l)}" x2="${X(l)}" y1="${Hh - pb}" y2="${Hh - pb + 4}" class="ax"/><text x="${X(l)}" y="${Hh - 6}" text-anchor="middle">L${l}</text>`;
    s += `<line x1="${pl}" x2="${W - pr}" y1="${Y(0)}" y2="${Y(0)}" class="zero"/>`;
    const ends: { n: string; v: number; col: string }[] = [];
    for (const [r, col, k] of [[D.A, A_COL, "A"], [D.B, B_COL, "B"]] as const) {
      const t = src(r); let d = ""; for (let l = 0; l <= L; l++) d += `${l ? "L" : "M"}${X(l).toFixed(1)},${Y(t.get(l)).toFixed(1)}`;
      s += `<path d="${d}" fill="none" stroke="${col}" stroke-width="1.6"/><circle cx="${X(L)}" cy="${Y(t.get(L))}" r="2.6" fill="${col}"/>`;
      ends.push({ n: k, v: t.get(L), col });
    }
    ends.sort((p, q) => q.v - p.v).forEach((e, i) => (s += `<text x="${W - pr}" y="${11 + i * 12}" text-anchor="end" style="fill:${e.col}">${e.n} ${e.v.toFixed(2)}</text>`));
    host.innerHTML = `<svg width="${W}" height="${Hh}">${s}</svg><div class="foot">log-odds of “${esc(D.A.m.item.j_plus)}” over “${esc(D.A.m.item.j_minus)}” if read off after each layer · dashed: 0 = even odds${clamp ? " · clamped run" : ""}</div>`;
  }

  // ---------------- camera: presets fit the whole (collapsed) object, so the token grid is never cropped
  function frameCamera() {
    const cam = ctx.get("cam");
    const nums = cam?.split(",").map(Number);
    if (nums && nums.length === 6 && nums.every(Number.isFinite)) { camera.position.set(nums[0], nums[1], nums[2]); controls.target.set(nums[3], nums[4], nums[5]); controls.update(); return; }
    preset(cam && ["readout", "overview", "top", "front"].includes(cam) ? cam : "readout", true);
  }
  function preset(name: string, instant = false) {
    const depth = L * LAYOUT.SZ, x0 = -1.5, x1 = (lay.x[ro] ?? lay.width) + 6.5;   // incl. layer labels and margin line
    const cx = (x0 + x1) / 2, w = x1 - x0;
    const vt = Math.tan(THREE.MathUtils.degToRad(FOV / 2)), ht = vt * camera.aspect;
    const dirs: Record<string, [number, number, number]> = { readout: [0.3, 0.66, 0.69], overview: [0, 0.55, 0.84], top: [0, 1, 0.012], front: [0.12, 0.22, 0.97] };
    const d = new THREE.Vector3(...dirs[name]).normalize();
    // Fit by projection: the smallest distance at which the projected box of the object (token labels in
    // front, margin line and layer labels at the right, labels up to ~6.5 high) spans at most 92% of the
    // panel, keeping a strip at the right for the end-of-line margin labels (canvas sprites of fixed
    // screen size, centred over the line's end). Then pan so the box is centred in what is left.
    const target = new THREE.Vector3(cx, 0, -0.5 * depth);
    const corners: THREE.Vector3[] = [];
    for (const x of [x0, x1]) for (const y of [0, 6.5]) for (const z of [7, -depth]) corners.push(new THREE.Vector3(x, y, z));
    const panelPx = Math.max(200, view === "single" ? canvas.clientWidth : (canvas.clientWidth - GUT) / 2);
    const reserve = Math.min(0.5, (2 * 70) / panelPx);   // ~70 px: half of "margin 1.059" (15 px type) past the line end
    const probe = camera.clone();
    const box = (dd: number, tg: THREE.Vector3) => {
      probe.position.copy(tg).addScaledVector(d, dd); probe.lookAt(tg); probe.updateMatrixWorld(); probe.updateProjectionMatrix();
      const b = { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity, behind: false };
      for (const c of corners) { const v = c.clone().project(probe); b.x0 = Math.min(b.x0, v.x); b.x1 = Math.max(b.x1, v.x); b.y0 = Math.min(b.y0, v.y); b.y1 = Math.max(b.y1, v.y); if (v.z >= 1) b.behind = true; }
      return b;
    };
    const fits = (dd: number) => { const b = box(dd, target); return !b.behind && b.x1 - b.x0 <= 1.84 - reserve && b.y1 - b.y0 <= 1.84; };
    let lo = 1, hi = (0.5 * Math.hypot(w, depth, 8)) / Math.sin(Math.atan(Math.min(vt, ht))) * 1.4;
    for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2; if (fits(mid)) hi = mid; else lo = mid; }
    const dist = hi;
    // Pan (camera and target together) until the box is centred in [-0.92, 0.92 - reserve] × [-0.92, 0.92].
    for (let i = 0; i < 4; i++) {
      const b = box(dist, target), dx = (b.x0 + b.x1) / 2 + reserve / 2, dy = (b.y0 + b.y1) / 2;
      const right = new THREE.Vector3().setFromMatrixColumn(probe.matrixWorld, 0), up = new THREE.Vector3().setFromMatrixColumn(probe.matrixWorld, 1);
      target.addScaledVector(right, dx * ht * dist).addScaledVector(up, dy * vt * dist);
    }
    flyTo(target, target.clone().add(d.multiplyScalar(dist)), instant || ctx.get("still") != null);
    root.querySelectorAll<HTMLElement>("[data-cam]").forEach((b) => b.classList.toggle("on", b.dataset.cam === name));
    ctx.set("cam", name === "readout" ? null : name);
  }
  function flyTo(target: THREE.Vector3, pos: THREE.Vector3, instant = false) {
    if (instant) { controls.target.copy(target); camera.position.copy(pos); controls.update(); fly = null; return; }
    fly = { t0: performance.now(), t: controls.target.clone(), p: camera.position.clone(), T: target, P: pos };
  }
  function flyToToken(t: number) {
    const sg = segs.find((s) => t >= s.a && t <= s.b); if (sg) sg.open = true;
    hl = t; build();
    const x = lay.x[t] ?? 0, depth = L * LAYOUT.SZ;
    flyTo(new THREE.Vector3(x, 0, -0.4 * depth), new THREE.Vector3(x + 6, 48, -0.4 * depth + 64));
  }
  root.querySelectorAll<HTMLElement>("[data-cam]").forEach((b) => (b.onclick = () => preset(b.dataset.cam!)));
  root.querySelectorAll<HTMLElement>("[data-view]").forEach((b) => (b.onclick = () => { view = b.dataset.view!; framed = false; build(); }));
  for (const id of ["single", "hscale", "color"]) $(id).addEventListener("change", build);
  $("clamp").onclick = () => { clampOn = !clampOn; build(); if (selection || pinnedOther) showPinned(selection ? { kind: "head", ...selection } : pinnedOther!); };

  // ---------------- word search
  const q = $<HTMLInputElement>("q"), hits = $("hits");
  function search() {
    const s = q.value.toLowerCase().trim(); if (s.length < 1) { hits.hidden = true; return; }
    const res = D.A.m.tokens.map((x, t) => ({ t, x: x.text })).filter((o) => o.x.toLowerCase().trim() === s || (s.length >= 2 && o.x.toLowerCase().includes(s))).slice(0, 30);
    hits.innerHTML = res.length ? res.map((o, i) => { const sg = segs.find((g) => o.t >= g.a && o.t <= g.b)!; return `<div data-t="${o.t}" class="${i === 0 ? "k" : ""}">token ${o.t} <b>${esc(tokText(o.x))}</b> <span class="seg">${esc(sg.label)}${sg.open ? "" : " (collapsed, will open)"}</span></div>`; }).join("") : `<div class="seg">No word matches</div>`;
    hits.hidden = false; ctx.set("q", s);
  }
  q.oninput = search;
  q.onkeydown = (e) => { if (e.key === "Enter") { const f = hits.querySelector<HTMLElement>("[data-t]"); if (f) { flyToToken(+f.dataset.t!); hits.hidden = true; } } if (e.key === "Escape") { e.stopPropagation(); hits.hidden = true; q.value = ""; q.hidden = true; q.blur(); } };
  hits.onclick = (e) => { const d = (e.target as Element).closest<HTMLElement>("[data-t]"); if (d) { flyToToken(+d.dataset.t!); hits.hidden = true; } };

  // ---------------- picking, synced hover, selection
  const kindName = (s: Slice) => (s.kind === "head" ? "heads" : s.kind);
  const idOf = (ts: TensorScene, s: Slice) => (s.kind === "head" ? (s.l * ts.H + s.h) * ts.T + s.t : s.l * ts.T + s.t);
  function sliceOf(ts: TensorScene, kind: "heads" | "mlp" | "resid", id: number): Slice {
    const t = id % ts.T;
    if (kind === "heads") { const lh = Math.floor(id / ts.T); return { kind: "head", l: Math.floor(lh / ts.H), h: lh % ts.H, t }; }
    return { kind, l: Math.floor(id / ts.T), t };
  }
  function applySelection(s: { l: number; h: number; t: number }, render = true) {
    for (const p of panels) {
      p.ts.select(p.ts.heads, (s.l * p.ts.H + s.h) * p.ts.T + s.t);
      if (!p.ts.delta) p.ts.showArcs(s.l, s.h, s.t); else p.ts.clearArcs();
    }
    if (render) void 0;
    showPinned({ kind: "head", ...s });
  }
  function showPinned(s: Slice) {
    let note = "";
    if (s.kind === "head") {
      const p0 = panels.find((p) => !p.ts.delta)!;
      const gs = p0.ts.gapSums(s.l, s.h, s.t).filter(([, v]) => v > 0.005);
      note = gs.length ? `Attention to collapsed parts (one arc each, showing the total, model ${p0.run === D.B ? "B" : "A"}): ${gs.map(([g, v]) => `${esc(g.label)}: total ${v.toFixed(2)}`).join(" · ")}` : "";
    }
    const dr = $("drawer"), name = s.kind === "head" ? `Head ${s.h} · layer ${s.l}` : s.kind === "mlp" ? `MLP block · layer ${s.l}` : `Running state · ${s.l === 0 ? "start" : "after layer " + (s.l - 1)}`;
    dr.hidden = false; $("work").classList.add("pinned");
    dr.innerHTML = drawerHTML(name, `pinned · token ${s.t} “${esc(tokText(D.A.m.tokens[s.t].text))}”${s.t === ro ? " · answer position (t*)" : ""}`, inspectorHTML(D, s, { pinned: true, clamp: clampOn, note, bare: true }), failing);
    $("unpin").onclick = unpin;
  }
  function unpin() {
    selection = null; pinnedOther = null; for (const p of panels) { p.ts.select(null); p.ts.clearArcs(); }
    $("drawer").hidden = true; $("drawer").innerHTML = ""; $("work").classList.remove("pinned"); syncUrl();
  }
  const ray = new THREE.Raycaster();
  function pick(ev: MouseEvent) {
    const r = canvas.getBoundingClientRect(), x = ev.clientX - r.left, rs = rects();
    const i = rs.findIndex((q) => x >= q.x && x < q.x + q.w), p = panels[i]; if (!p) return null;
    const nx = ((x - rs[i].x) / rs[i].w) * 2 - 1, ny = -((ev.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(new THREE.Vector2(nx, ny), camera);
    const hit = ray.intersectObjects([p.ts.heads, p.ts.mlp, p.ts.resid], false)[0];
    if (!hit || hit.instanceId === undefined) return null;
    return { p, mesh: hit.object as THREE.InstancedMesh, id: hit.instanceId };
  }
  const tip = $("tip");
  const onMove = (ev: PointerEvent) => {
    const h = pick(ev);
    if (!h) { tip.hidden = true; for (const p of panels) p.ts.hover(null); return; }
    const kind = h.p.ts.kindOf(h.mesh); if (!kind) { tip.hidden = true; return; }
    // Synced hover: mark the same slice in every panel; one tooltip carries each panel's value.
    const s = sliceOf(h.p.ts, kind, h.id);
    const lines = [`${s.kind === "head" ? "Head" : s.kind === "mlp" ? "MLP block" : "State"} · layer ${s.l}${s.kind === "head" ? " · head " + s.h : ""} · token ${s.t} “${tokText(D.A.m.tokens[s.t].text)}”`];
    panels.forEach((p) => {
      p.ts.hover(p.ts.meshOfKind(kind), h.id);
      const info = p.ts.info(p.ts.meshOfKind(kind), h.id); if (!info) return;
      lines.push(`— ${p.label}`, ...info.rows.slice(2, p.ts.delta ? 3 : 4).map(([k, v]) => `  ${k}: ${v.split("\n")[0]}`));
    });
    tip.hidden = false; tip.textContent = lines.join("\n");
    const r = canvas.getBoundingClientRect();
    tip.style.left = `${Math.min(ev.clientX - r.left + 14, r.width - 360)}px`; tip.style.top = `${ev.clientY - r.top + 14}px`;
  };
  const onClick = (ev: MouseEvent) => {
    const h = pick(ev); if (!h) return;
    const kind = h.p.ts.kindOf(h.mesh)!, s = sliceOf(h.p.ts, kind, h.id);
    if (s.kind === "head") { selection = { l: s.l, h: s.h, t: s.t }; pinnedOther = null; applySelection(selection); }
    else { selection = null; pinnedOther = s; for (const p of panels) { p.ts.select(null); p.ts.clearArcs(); } for (const p of panels) p.ts.select(p.ts.meshOfKind(kind), h.id); showPinned(s); }
    syncUrl();
  };
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("click", onClick);
  canvas.addEventListener("pointerleave", () => { tip.hidden = true; });
  window.addEventListener("keydown", (e) => {
    const t = e.target as HTMLElement;
    if (e.metaKey || e.ctrlKey || e.altKey || /^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName) || document.querySelector("dialog[open]")) return;
    if (e.key === "Escape") unpin();
    else if (e.key === "a" || e.key === "A") openLearn(D, "answer");
    else if (e.key === "/") { e.preventDefault(); q.hidden = false; q.focus(); }
  }, { signal: ctx.signal });

  /** Viewport of each panel in CSS px: two scenes leave a centre gutter for the margin inset. */
  const GUT = 200;
  function rects(): { x: number; w: number }[] {
    const w = canvas.clientWidth, n = Math.max(1, panels.length);
    if (n === 1) return [{ x: 0, w }];
    const pw = (w - GUT) / 2; return [{ x: 0, w: pw }, { x: pw + GUT, w: pw }];
  }
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    const rs = rects();
    camera.aspect = rs[0].w / h; camera.updateProjectionMatrix();
    for (const p of panels) p.ts.setResolution(rs[0].w, h);
    // each label and outline sits over its own viewport (anchored to its scene)
    const place = (id: string, q?: { x: number; w: number }) => { const el = $(id); if (!q) return; el.style.left = `${q.x}px`; el.style.width = `${q.w}px`; };
    place("sceneA", rs[0]); place("sceneB", rs[1]);
    if (rs[1]) { const ib = $("insetBox"); ib.style.left = `${rs[0].w + 14}px`; ib.style.width = `${GUT - 28}px`; }
  }

  // ---------------- prompt map: real resid_norm (or d_resid_norm) heatmap over ALL tokens + segment bands + view bracket
  const mc = $<HTMLCanvasElement>("mm"); let visRange: [number, number] | null = null, mcw = 1;
  function drawMini() {
    const w = mc.clientWidth, Hh = 92, dpr = devicePixelRatio || 1; if (!w) return;
    mc.width = w * dpr; mc.height = Hh * dpr; mc.style.height = Hh + "px"; const g = mc.getContext("2d")!; g.scale(dpr, dpr);
    const bandH = 18, hh = Hh - bandH - 6, cw = w / T, dm = view === "delta";
    const src = dm ? D.P.t.d_resid_norm : D.A.t.resid_norm, s = dm ? makeRamp([src]) : makeRamp([D.A.t.resid_norm, D.B.t.resid_norm]);
    $("minicap").innerHTML = `<span class="cap">prompt map</span> every token (columns) × layer (rows) · brightness: ${dm ? "the size of the change ‖B − A‖ of the running state" : "the size of the running state in A"}, on a log scale, clipped at the 99th percentile ${fmt(s.vmax, 3)} (max ${fmt(s.max, 3)}) · click a band to open or collapse it · white bracket: tokens in view`;
    for (let l = 0; l <= L; l++) for (let t = 0; t < T; t++) { g.fillStyle = dm ? mix(C.neutral, C.delta, rampU(s, src.get(l, t))) : mix("#121212", "#cfd8e3", rampU(s, src.get(l, t))); g.fillRect(t * cw, bandH + 4 + ((L - l) * hh) / (L + 1), Math.ceil(cw), Math.ceil(hh / (L + 1))); }
    g.font = "10.5px ui-monospace, Menlo, monospace"; g.textBaseline = "middle";
    let lastEnd = -1;
    for (const sg of segs) {
      const x0 = sg.a * cw, x1 = (sg.b + 1) * cw;
      g.fillStyle = sg.kind === "readout" ? "#ffffff" : sg.open ? "#2c2c31" : "#1a1a1d"; g.fillRect(x0 + 0.5, 0, x1 - x0 - 1, bandH);
      if (!sg.open) { g.fillStyle = "#000a"; g.fillRect(x0, bandH + 4, x1 - x0, hh); }
      // a label is drawn only if it fits inside its own band with 6 px either side and clears the previous label
      const txt = sg.kind === "readout" ? "" : fitWords(g, sg.label, x1 - x0 - 12), tx = x0 + 6;
      if (txt && tx > lastEnd + 8) { g.fillStyle = sg.open ? "#e6e6e6" : "#8a8a8a"; g.fillText(txt, tx, bandH / 2); lastEnd = tx + g.measureText(txt).width; }
    }
    if (hl >= 0) { g.fillStyle = "#ffcf5c"; g.fillRect(hl * cw, bandH + 2, Math.max(2, cw), hh + 2); }
    if (visRange) { g.strokeStyle = "#ffffffcc"; g.lineWidth = 1.5; g.strokeRect(visRange[0] * cw, bandH + 2, (visRange[1] - visRange[0] + 1) * cw, hh + 3); }
    mcw = cw;
  }
  // Band labels are shortened at a word boundary; the full label is the canvas tooltip over its band.
  mc.onmousemove = (e) => {
    const r = mc.getBoundingClientRect(), t = Math.floor((e.clientX - r.left) / mcw), sg = segs.find((s) => t >= s.a && t <= s.b);
    mc.title = sg ? `${sg.label} · ${sg.n} tokens${e.clientY - r.top < 22 && sg.kind !== "readout" ? (sg.open ? " · click to collapse" : " · click to open") : ""}` : "";
  };
  mc.onclick = (e) => {
    const r = mc.getBoundingClientRect(), t = Math.floor((e.clientX - r.left) / mcw), sg = segs.find((s) => t >= s.a && t <= s.b);
    if (!sg || sg.kind === "readout") return;
    if (e.clientY - r.top < 22) { sg.open = !sg.open; build(); } else flyToToken(t);
  };
  let lastVis = 0;
  function updateVis() {
    const v = new THREE.Vector3(), z = -0.5 * L * LAYOUT.SZ; let a: number | null = null, b: number | null = null;
    for (let t = 0; t < T; t++) { const x = lay.x[t]; if (x == null) continue; v.set(x, 1, z).project(camera); if (Math.abs(v.x) <= 1 && Math.abs(v.y) <= 1 && v.z < 1) { if (a == null) a = t; b = t; } }
    const nr: [number, number] | null = a == null ? null : [a, b!];
    if (JSON.stringify(nr) !== JSON.stringify(visRange)) { visRange = nr; drawMini(); }
  }

  // ---------------- render loop
  let first = true;
  function frame(now: number) {
    if (!alive) return;
    if (fly) { const k = Math.min(1, (now - fly.t0) / 700), e = 1 - Math.pow(1 - k, 3); controls.target.lerpVectors(fly.t, fly.T, e); camera.position.lerpVectors(fly.p, fly.P, e); if (k >= 1) fly = null; }
    controls.update();
    const w = canvas.clientWidth, h = canvas.clientHeight, n = Math.max(1, panels.length);
    const rs = rects(); void w; void n;
    renderer.setScissor(0, 0, w, h); renderer.setClearColor(0x0b0b0b); renderer.clear();
    panels.forEach((p, i) => { const q = rs[i]; renderer.setViewport(q.x, 0, q.w, h); renderer.setScissor(q.x, 0, q.w, h); renderer.render(p.scene, camera); });
    if (now - lastVis > 200) { lastVis = now; updateVis(); }
    if (first && framed && panels.length) { first = false; setTimeout(() => alive && ctx.ready(), 150); }
    raf = requestAnimationFrame(frame);
  }
  const ro_ = new ResizeObserver(() => { resize(); drawMini(); if (!framed && canvas.clientHeight > 200) { framed = true; frameCamera(); } });
  ro_.observe($("stage"));

  // ---------------- boot
  build();
  if (ctx.get("q")) { q.value = ctx.get("q")!; search(); }
  if (hl >= 0 && !ctx.get("cam")) { const x = lay.x[hl] ?? 0, depth = L * LAYOUT.SZ; framed = true; flyTo(new THREE.Vector3(x, 0, -0.4 * depth), new THREE.Vector3(x + 6, 48, -0.4 * depth + 64), true); }
  raf = requestAnimationFrame(frame);

  return () => {
    alive = false; cancelAnimationFrame(raf); ro_.disconnect();
    canvas.removeEventListener("pointermove", onMove); canvas.removeEventListener("click", onClick);
    disposePanels(); rebuildHook = null;
    renderer.setScissor(0, 0, canvas.width, canvas.height); renderer.clear();
    canvas.remove();
  };
}

/** The longest word-prefix of `label` that fits `w` px, with "…" when shortened ("" if not even one word fits). */
function fitWords(g: CanvasRenderingContext2D, label: string, w: number): string {
  if (g.measureText(label).width <= w) return label;
  const words = label.split(" ");
  for (let n = words.length - 1; n > 0; n--) { const t = words.slice(0, n).join(" ").replace(/[\s·+,]+$/, "") + "…"; if (g.measureText(t).width <= w) return t; }
  return g.measureText("…").width <= w ? "…" : "";
}
