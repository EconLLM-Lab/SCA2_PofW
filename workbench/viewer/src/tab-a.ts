// Tab A, the 3D object: the tensor blocks of scene.ts, with template text collapsed into labelled gaps,
// a prompt map, word search, camera presets and a "largest changes" list.
// URL keys: view=single|side|delta, single=a|b, hscale=log|linear, color=dla|q3|plain, clamp=1,
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
  A_COL, B_COL, C, divergingLegend, esc, fmt, inspectorHTML, labelMinus, labelPlus, lm, mix, makeRamp, rampU,
  readoutHTML, segmentsOf, tokText, type Seg, type Slice,
} from "./common";
import {
  FOV, LAYOUT, TensorScene, disposeScene, gapLines, layerStrip, layoutX, makeScale, scaleLabel, tokenStrip,
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
  const lp = labelPlus(D.A), lmn = labelMinus(D.A);
  root.className = "tab-a";
  root.innerHTML = `
    <div class="tools">
      <span class="grp">Show <button data-view="single">A only</button><button data-view="side">A next to B</button><button data-view="delta">A next to the change ‖B − A‖</button></span>
      <label id="singleWrap">model <select id="single"><option value="a">A</option><option value="b">B</option></select></label>
      <span class="grp">Camera <button data-cam="readout">answer position</button><button data-cam="overview">whole object</button><button data-cam="top">from above</button><button data-cam="front">layer stack</button></span>
      <span class="grp" id="search">Find a word <input id="q" placeholder="e.g. confidence, Answer, 4" autocomplete="off" /><div id="hits" hidden></div></span>
      <button id="all"></button>
      <label>height <select id="hscale"><option value="log">log</option><option value="linear">linear</option></select></label>
      <label>colour <select id="color"><option value="dla">push on the margin</option><option value="q3">Quadrant III count</option><option value="plain">plain</option></select></label>
      <label class="chk"><input type="checkbox" id="clamp" /> clamped run</label>
    </div>
    <div class="strip"><span class="badge data" title="Every figure on this tab is drawn from the exports of the current pair and prompt">real data · drawn from the exports</span> Left to right: tokens in the prompt. Front to back: layers (layer 0 is nearest). Height: the size of the vector. In the blue-outlined answer column, blue pushes toward “${esc(lp.slice(0, 40))}” and orange toward “${esc(lmn.slice(0, 40))}”. Everywhere else, colour only names the kind of block. ${lm("scale", "learn more")}</div>
    <div class="a-main">
      <div id="stage"><div class="vlabel" id="labelA"></div><div class="vlabel" id="labelB"></div><div id="divider" hidden></div><div id="tip" hidden></div>
        <div id="glLost" hidden>The GPU dropped the WebGL context. Waiting for it to come back (reload the page if it does not).</div>
        <div id="inset"></div></div>
      <aside id="side"><div id="ro"></div><div id="insp"></div><div id="bigd"></div><div id="enc"></div></aside>
    </div>
    <div id="mini"><div class="cap"><span id="minicap"></span><span>Click a band to open or collapse that part of the prompt. The white bracket marks the tokens now in view. ${lm("segments", "learn more")}</span></div><canvas id="mc"></canvas></div>`;
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => root.querySelector<T>("#" + id)!;
  $("stage").prepend(canvas);
  const sel = <T extends HTMLElement = HTMLSelectElement>(id: string) => $<T>(id);

  // ---------------- state (from the URL)
  const legacyView = ctx.get("view") === "side" && ctx.get("right") === "delta" ? "delta" : null;
  let view = legacyView || ctx.get("view") || "side";
  if (!["single", "side", "delta"].includes(view)) view = "side";
  for (const id of ["single", "hscale", "color"]) if (ctx.get(id)) sel(id).value = ctx.get(id)!;
  sel<HTMLInputElement>("clamp").checked = ctx.get("clamp") === "1";
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
    const hs = sel("hscale").value as HeightScale, color = sel("color").value as ColorMode, clamp = sel<HTMLInputElement>("clamp").checked;
    $("singleWrap").style.display = view === "single" ? "" : "none";
    root.querySelectorAll<HTMLElement>("[data-view]").forEach((x) => x.classList.toggle("on", x.dataset.view === view));
    $("all").textContent = segs.every((s) => s.open) ? "Collapse template text" : "Show all template text";
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
      const ts = new TensorScene(run, delta ? dScales : scales, color, delta ? { pair, a } : null, delta ? false : clamp, lay);
      panels.push({ scene: makeThreeScene(ts, run), ts, label, run });
    };
    if (view === "single") { const r = sel("single").value === "b" ? b : a; add(r, `${sel("single").value.toUpperCase()} · ${r.m.model.label}`, false); }
    else { add(a, `A · ${a.m.model.label}`, false); view === "delta" ? add(b, `Change ‖B − A‖ · B is ${b.m.model.label}`, true) : add(b, `B · ${b.m.model.label}`, false); }
    $("labelA").textContent = panels[0].label;
    $("labelB").hidden = panels.length < 2; if (panels[1]) $("labelB").textContent = panels[1].label;
    if (selection) applySelection(selection, false);
    else if (pinnedOther) { const p0 = panels[0]; p0.ts.select(p0.ts.meshOfKind(kindName(pinnedOther)), idOf(p0.ts, pinnedOther)); }
    encoding(scales, dScales, color, view === "delta", clamp);
    inset(clamp);
    resize();
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
    ctx.set("clamp", sel<HTMLInputElement>("clamp").checked ? 1 : null);
    ctx.set("sel", selection ? `${selection.l},${selection.h},${selection.t}` : null);
    ctx.set("open", segs.every((s) => s.open) ? "all" : null);
    ctx.set("fly", hl >= 0 ? hl : null);
  }

  // ---------------- side panel: heights and colours, largest changes, inset chart
  function encoding(s: Scales, sd: Scales, color: ColorMode, delta: boolean, clamp: boolean) {
    const ramp = makeRamp([D.P.t.d_head_norm]);
    $("enc").innerHTML = `<div class="card"><div class="card-h"><span>Heights and colours</span>${lm("scale", "learn more")}</div>
      <p class="kline"><span class="swatch" style="background:${C.resid}"></span>bar before each layer: size of the running state ‖h‖</p>
      <p class="kline"><span class="swatch" style="background:${C.head}"></span>9 slivers: write size of each head ‖o‖ (h = 0…8, left to right)</p>
      <p class="kline"><span class="swatch" style="background:${C.mlp}"></span>block behind: write size of the MLP ‖m‖</p>
      ${color === "dla" ? divergingLegend(s.dla, lp, lmn, ` Answer column only${clamp ? "; clamped run" : ""}. Square-root scale, shared by A and B.`) : color === "q3" ? `<p class="kline"><span class="swatch" style="background:${C.q3}"></span>MLP colour: Quadrant III neurons, full colour at ${s.q3} of ${D.A.m.model.d_ffn}</p>` : ""}
      ${delta ? `<p class="kline"><span class="swatch" style="background:${C.delta}"></span>right panel: ‖B − A‖ of the same slice (exact, from both runs); colour follows the height. Gold heads at the answer: up to ${fmt(ramp.max, 3)}.</p>` : ""}
      <p class="kline">Line right of the answer column: the margin if read off at each layer; numbers at both ends. The flat chart in the corner shows A and B on one axis.</p>
      <p class="muted small">heads: ${esc(scaleLabel(s.head))}<br>MLP: ${esc(scaleLabel(s.mlp))}<br>running state: ${esc(scaleLabel(s.resid))}<br>Heights share one scale across A and B${delta ? `; the change panel has its own (heads: ${esc(scaleLabel(sd.head))})` : ""}.</p></div>`;
  }
  function bigList() {
    const r: { l: number; h: number; v: number }[] = [];
    for (let l = 0; l < L; l++) for (let h = 0; h < H; h++) r.push({ l, h, v: D.P.t.d_head_norm.get(l, h, ro) });
    r.sort((x, y) => y.v - x.v);
    $("bigd").innerHTML = `<div class="card"><div class="card-h"><span>Heads whose write changed most at the answer position</span>${lm("delta", "what is ‖B − A‖?")}</div><div class="big">${r.slice(0, 6).map((o) => `<div class="r" data-l="${o.l}" data-h="${o.h}">layer ${o.l} · head ${o.h}</div><div><span class="hb" style="background:var(--delta);width:${((o.v / r[0].v) * 100).toFixed(0)}%"></span></div><div class="num">${fmt(o.v, 3)}</div>`).join("")}</div><div class="foot">Each bar is ‖o_B − o_A‖ at the answer position (<code>d_head_norm</code>): how far B's write is from A's. Click a row to fly there and pin it.</div></div>`;
  }
  $("bigd").addEventListener("click", (e) => {
    const d = (e.target as Element).closest<HTMLElement>("[data-l]"); if (!d) return;
    selection = { l: +d.dataset.l!, h: +d.dataset.h!, t: ro }; applySelection(selection); syncUrl();
    const x = lay.x[ro] ?? 0, z = -selection.l * LAYOUT.SZ; flyTo(new THREE.Vector3(x, 0, z), new THREE.Vector3(x + 9, 16, z + 22));
  });
  /** Flat chart of the margin polyline: in 3D it runs along depth, so A and B lengths are not comparable by eye. */
  function inset(clamp: boolean) {
    if (view === "delta") { $("inset").innerHTML = ""; return; }
    const W = 250, Hh = 120, pl = 30, pr = 44, pt = 18, pb = 18, src = (r: Run) => (clamp ? r.t.running_margin_clamped : r.t.running_margin);
    let lo = 0, hi = 0; for (const r of [D.A, D.B]) for (const v of src(r).data) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    const X = (l: number) => pl + (l / L) * (W - pl - pr), Y = (v: number) => pt + ((hi - v) / (hi - lo || 1)) * (Hh - pt - pb);
    let s = `<text x="4" y="11" class="t">margin if read off at each layer${clamp ? " (clamped run)" : ""}</text><line x1="${pl}" x2="${W - pr}" y1="${Y(0)}" y2="${Y(0)}" stroke="#444"/><text x="${pl - 4}" y="${Y(0) + 3}" text-anchor="end">0</text><text x="${pl}" y="${Hh - 4}">L0</text><text x="${W - pr}" y="${Hh - 4}" text-anchor="end">L${L}</text>`;
    const ends: number[] = [];
    for (const [r, col, k] of [[D.A, A_COL, "A"], [D.B, B_COL, "B"]] as const) {
      const t = src(r); let d = ""; for (let l = 0; l <= L; l++) d += `${l ? "L" : "M"}${X(l).toFixed(1)},${Y(t.get(l)).toFixed(1)}`;
      let ye = Y(t.get(L)) + 3; if (ends.length && Math.abs(ye - ends[0]) < 11) ye = ends[0] + (ye >= ends[0] ? 11 : -11); ends.push(ye);
      s += `<path d="${d}" fill="none" stroke="${col}" stroke-width="1.8"/><text x="${W - pr + 4}" y="${ye}" style="fill:${col}">${k} ${t.get(L).toFixed(2)}</text>`;
    }
    $("inset").innerHTML = `<svg width="${W}" height="${Hh}">${s}</svg>`;
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
    const panelPx = Math.max(200, canvas.clientWidth / Math.max(1, panels.length || (view === "single" ? 1 : 2)));
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
  for (const id of ["single", "hscale", "color", "clamp"]) $(id).addEventListener("change", build);
  $("all").onclick = () => { const all = segs.every((s) => s.open); segs.forEach((s) => (s.open = all ? ["question", "options", "answer_cue", "readout", "text"].includes(s.kind) : true)); build(); };

  // ---------------- word search
  const q = $<HTMLInputElement>("q"), hits = $("hits");
  function search() {
    const s = q.value.toLowerCase().trim(); if (s.length < 1) { hits.hidden = true; return; }
    const res = D.A.m.tokens.map((x, t) => ({ t, x: x.text })).filter((o) => o.x.toLowerCase().trim() === s || (s.length >= 2 && o.x.toLowerCase().includes(s))).slice(0, 30);
    hits.innerHTML = res.length ? res.map((o, i) => { const sg = segs.find((g) => o.t >= g.a && o.t <= g.b)!; return `<div data-t="${o.t}" class="${i === 0 ? "k" : ""}">token ${o.t} <b>${esc(tokText(o.x))}</b> <span class="seg">${esc(sg.label)}${sg.open ? "" : " (collapsed, will open)"}</span></div>`; }).join("") : `<div class="seg">No word matches</div>`;
    hits.hidden = false; ctx.set("q", s);
  }
  q.oninput = search;
  q.onkeydown = (e) => { if (e.key === "Enter") { const f = hits.querySelector<HTMLElement>("[data-t]"); if (f) { flyToToken(+f.dataset.t!); hits.hidden = true; } } if (e.key === "Escape") hits.hidden = true; };
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
      note = gs.length ? `Attention to collapsed parts (one Σ arc each, model ${p0.run === D.B ? "B" : "A"}): ${gs.map(([g, v]) => `${esc(g.label)} Σ ${v.toFixed(2)}`).join(" · ")}` : "";
    }
    $("insp").innerHTML = inspectorHTML(D, s, { pinned: true, clamp: sel<HTMLInputElement>("clamp").checked, note });
  }
  const ray = new THREE.Raycaster();
  function pick(ev: MouseEvent) {
    const r = canvas.getBoundingClientRect(), n = panels.length, x = ev.clientX - r.left;
    const i = Math.min(n - 1, Math.floor((x / r.width) * n)), p = panels[i]; if (!p) return null;
    const nx = ((x - (i * r.width) / n) / (r.width / n)) * 2 - 1, ny = -((ev.clientY - r.top) / r.height) * 2 + 1;
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
    const lines = [`${s.kind === "head" ? "Head" : s.kind === "mlp" ? "MLP" : "State"} · layer ${s.l}${s.kind === "head" ? " · head " + s.h : ""} · token ${s.t} “${tokText(D.A.m.tokens[s.t].text)}”`];
    panels.forEach((p) => {
      p.ts.hover(p.ts.meshOfKind(kind), h.id);
      const info = p.ts.info(p.ts.meshOfKind(kind), h.id); if (!info) return;
      lines.push(`— ${p.label}`, ...info.rows.slice(2, p.ts.delta ? 3 : 4).map(([k, v]) => `  ${k}: ${v.split("\n")[0]}`));
    });
    tip.hidden = false; tip.textContent = lines.join("\n");
    const r = canvas.getBoundingClientRect();
    tip.style.left = `${Math.min(ev.clientX - r.left + 14, r.width - 470)}px`; tip.style.top = `${ev.clientY - r.top + 14}px`;
    if (!selection && !pinnedOther) $("insp").innerHTML = inspectorHTML(D, s, { clamp: sel<HTMLInputElement>("clamp").checked });
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
    if (e.key !== "Escape" || document.querySelector("dialog[open]")) return;
    selection = null; pinnedOther = null; for (const p of panels) { p.ts.select(null); p.ts.clearArcs(); } idle(); syncUrl();
  }, { signal: ctx.signal });
  function idle() { $("insp").innerHTML = `<div class="card"><div class="card-h"><span>Compare A and B for one block</span>${lm("dla", "what is DLA?")}</div><p class="muted" style="margin:0">Hover a block to compare A, B and the change. Click a head to pin it and draw where it looks, in both panels. Attention to a collapsed part is drawn as one arc to its gap, labelled with the sum.</p></div>`; }

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight, n = Math.max(1, panels.length);
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / n / h; camera.updateProjectionMatrix();
    for (const p of panels) p.ts.setResolution(w / n, h);
    $("labelB").style.left = `${w / 2 + 10}px`;
    $("divider").hidden = n < 2; $("divider").style.left = `${w / 2 - 1}px`;
  }

  // ---------------- prompt map: real resid_norm (or d_resid_norm) heatmap over ALL tokens + segment bands + view bracket
  const mc = $<HTMLCanvasElement>("mc"); let visRange: [number, number] | null = null, mcw = 1;
  function drawMini() {
    const w = mc.clientWidth, Hh = 92, dpr = devicePixelRatio || 1; if (!w) return;
    mc.width = w * dpr; mc.height = Hh * dpr; mc.style.height = Hh + "px"; const g = mc.getContext("2d")!; g.scale(dpr, dpr);
    const bandH = 18, hh = Hh - bandH - 6, cw = w / T, dm = view === "delta";
    const src = dm ? D.P.t.d_resid_norm : D.A.t.resid_norm, s = dm ? makeRamp([src]) : makeRamp([D.A.t.resid_norm, D.B.t.resid_norm]);
    $("minicap").innerHTML = `Prompt map. Each column is a token and each row a layer. Brightness is ${dm ? "the change ‖B − A‖ of the running state" : "the size of the running state in A"}, on a log scale clipped at the 99th percentile (≥ ${fmt(s.vmax, 3)}; max ${fmt(s.max, 3)}).`;
    for (let l = 0; l <= L; l++) for (let t = 0; t < T; t++) { g.fillStyle = dm ? mix(C.neutral, C.delta, rampU(s, src.get(l, t))) : mix("#121212", "#cfd8e3", rampU(s, src.get(l, t))); g.fillRect(t * cw, bandH + 4 + ((L - l) * hh) / (L + 1), Math.ceil(cw), Math.ceil(hh / (L + 1))); }
    g.font = "10.5px ui-monospace, Menlo, monospace"; g.textBaseline = "middle";
    for (const sg of segs) {
      const x0 = sg.a * cw, x1 = (sg.b + 1) * cw;
      g.fillStyle = sg.kind === "readout" ? "#6b9bff" : sg.open ? "#2c3a52" : "#1d1d1d"; g.fillRect(x0 + 0.5, 0, x1 - x0 - 1, bandH);
      if (!sg.open) { g.fillStyle = "#000a"; g.fillRect(x0, bandH + 4, x1 - x0, hh); }
      g.save(); g.beginPath(); g.rect(x0 + 2, 0, x1 - x0 - 4, bandH); g.clip(); g.fillStyle = sg.open ? "#e6e6e6" : "#8a8a8a"; g.fillText(sg.kind === "readout" ? "t*" : fitWords(g, sg.label, x1 - x0 - 8), x0 + 4, bandH / 2); g.restore();
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
    panels.forEach((p, i) => { renderer.setViewport((i * w) / n, 0, w / n, h); renderer.setScissor((i * w) / n, 0, w / n, h); renderer.render(p.scene, camera); });
    if (now - lastVis > 200) { lastVis = now; updateVis(); }
    if (first && framed && panels.length) { first = false; setTimeout(() => alive && ctx.ready(), 150); }
    raf = requestAnimationFrame(frame);
  }
  const ro_ = new ResizeObserver(() => { resize(); drawMini(); if (!framed && canvas.clientHeight > 200) { framed = true; frameCamera(); } });
  ro_.observe($("stage"));

  // ---------------- boot
  $("ro").innerHTML = readoutHTML(D); bigList(); idle();
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
