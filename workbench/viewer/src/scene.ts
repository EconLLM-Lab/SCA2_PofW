// 3D tensor-block scene for one capture run, or for the exact difference between two runs.
//
// Geometry (every mark is one tensor slice; nothing is decorative or generated):
//   X = token position t (left to right),   Z = -layer (layer 0 nearest the viewer),   Y = magnitude.
//   residual bar  at (t, state l)  height <- ||h^l_t||          (L+1 states; the last one is pre-final-norm)
//   head sliver   at (t, l, h)     height <- ||o^l_{h,t}||        (9 slivers per cell, h = 0..H-1 left to right)
//   MLP block     at (t, l)        height <- ||m^l_t||
// In "delta" mode the same marks carry ||B - A|| of the same tensor (from the pair export).
// Colour: neutral, unless the colour mode binds it to a named quantity (DLA, Quadrant-III count).

import * as THREE from "three";
import { Line2 } from "three/examples/jsm/lines/Line2.js";
import { LineGeometry } from "three/examples/jsm/lines/LineGeometry.js";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
import type { Pair, Run, Tensor } from "./data";

export type HeightScale = "log" | "linear";
export type ColorMode = "dla" | "q3" | "plain";
export type Quantity = "resid" | "head" | "mlp";

export const LAYOUT = { SX: 1.0, SZ: 1.7, CELL: 0.9, HMAX: 3.0, RESID_HMAX: 1.2 };

/** Camera field of view (deg). Narrow, so the far layers are less foreshortened than the near ones. */
export const FOV = 30;

/** Presentation only: line weights in screen pixels (WebGL ignores linewidth on plain lines). */
export const LINE_PX = { readout: 2.5, margin: 3, zero: 1.5 };

/** Dim factor for heads/MLP outside the readout column in DLA mode (category colour, binds to nothing). */
const DIM = { head: 0.62, mlp: 0.42 };

export const COLORS = {
  head: new THREE.Color("#8fa6cf"),
  mlp: new THREE.Color("#a8a49a"),
  resid: new THREE.Color("#5d6b74"),
  neutral: new THREE.Color("#3a3a3e"),
  pos: new THREE.Color("#6b9bff"),     // pushes toward j+  (DLA > 0)
  neg: new THREE.Color("#ff9a3c"),     // pushes toward j-  (DLA < 0)
  q3: new THREE.Color("#d27bff"),
  delta: new THREE.Color("#ffcf5c"),
  select: new THREE.Color("#ffffff"),
  arc: new THREE.Color("#e8e8e8"),
};

/** Height map shared by every panel that shows the same quantity, so equal heights mean equal values. */
export interface Scale { vmax: number; v0: number; mode: HeightScale; hmax: number }
export function height(s: Scale, v: number): number {
  const x = Math.max(v, 0);
  if (s.mode === "linear") return (s.hmax * x) / s.vmax;
  return (s.hmax * Math.log1p(x / s.v0)) / Math.log1p(s.vmax / s.v0);
}
export function scaleLabel(s: Scale): string {
  return s.mode === "linear"
    ? `height = ${s.hmax} * v / ${s.vmax.toPrecision(4)}`
    : `height = ${s.hmax} * ln(1 + v/${s.v0.toPrecision(3)}) / ln(1 + ${s.vmax.toPrecision(4)}/${s.v0.toPrecision(3)})`;
}

/** Shared scale over several tensors: max, and median of the positive entries (log knee). */
export function makeScale(tensors: Tensor[], mode: HeightScale, hmax: number): Scale {
  let vmax = 0;
  const sample: number[] = [];
  for (const t of tensors) {
    const step = Math.max(1, Math.floor(t.data.length / 20000));
    for (let i = 0; i < t.data.length; i++) {
      const v = t.data[i];
      if (v > vmax) vmax = v;
      if (i % step === 0 && v > 0) sample.push(v);
    }
  }
  sample.sort((a, b) => a - b);
  const v0 = sample.length ? sample[Math.floor(sample.length / 2)] : 1;
  return { vmax: vmax || 1, v0: v0 || 1, mode, hmax };
}

export interface Scales { resid: Scale; head: Scale; mlp: Scale; dla: number; q3: number; margin: number }

export interface PickInfo { title: string; rows: [string, string][]; note?: string; head?: { l: number; h: number; t: number } }

/** Token -> x position. A collapsed prompt segment draws NO geometry: its tokens map to null and the
 * segment becomes a labelled gap of width GAP (adjacent collapsed segments share one gap). */
/** `label` is the full gap name; for merged gaps it names what it hides, "system + persona · 4 parts".
 * `name` is that label without the part count, and `k` the number of merged parts. */
export interface Gap { x: number; a: number; b: number; n: number; label: string; name: string; k: number }
export interface XLayout { x: (number | null)[]; width: number; gaps: Gap[] }
export const GAP = 2.4;
export function layoutX(segs: { a: number; b: number; n: number; open: boolean; label: string; kind?: string }[], T: number): XLayout {
  const x: (number | null)[] = new Array(T).fill(null), gaps: Gap[] = [];
  let pos = 0, g: Gap | null = null, words: string[] = [];
  // A merged gap is named by the first word of each non-marker part it hides ("system", "persona").
  const word = (s: { label: string; kind?: string }) => (s.kind === "template" ? "" : s.label.split(/\s+/)[0]);
  for (const s of segs) {
    if (s.open) { g = null; for (let t = s.a; t <= s.b; t++) x[t] = (pos++) * LAYOUT.SX; }
    else if (g) {
      g.b = s.b; g.n += s.n; g.k++; const w = word(s); if (w && !words.includes(w)) words.push(w);
      g.name = words.join(" + ") || "message markers"; g.label = `${g.name} · ${g.k} parts`;
    }
    else { words = word(s) ? [word(s)] : []; g = { x: pos * LAYOUT.SX + GAP / 2 - LAYOUT.SX / 2, a: s.a, b: s.b, n: s.n, label: s.label, name: s.label, k: 1 }; gaps.push(g); pos += GAP / LAYOUT.SX; }
  }
  return { x, width: pos * LAYOUT.SX, gaps };
}
export const fullLayout = (T: number): XLayout => ({ x: Array.from({ length: T }, (_, t) => t * LAYOUT.SX), width: T * LAYOUT.SX, gaps: [] });

/** Free everything a scene put on the GPU: geometries, materials AND their textures. The
 * canvas-texture labels (token strip, layer and margin sprites) used to leak on every rebuild,
 * until the browser dropped the WebGL context and both panels went black. */
export function disposeScene(s: THREE.Scene) {
  s.traverse((o) => {
    const mesh = o as THREE.Mesh;
    mesh.geometry?.dispose();
    const mats = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    for (const mat of mats) {
      for (const v of Object.values(mat)) if (v instanceof THREE.Texture) v.dispose();
      mat.dispose();
    }
  });
  s.clear();
}

const box = new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0);

/** Δ panels: neutral -> yellow by the same mapping as the bar height (height / hmax), so colour
 * and height encode one number and the legend's height formula describes both. */
function deltaColor(v: number, s: Scale): THREE.Color {
  return COLORS.neutral.clone().lerp(COLORS.delta, Math.min(1, height(s, v) / s.hmax));
}

function diverging(v: number, vmax: number): THREE.Color {
  const a = Math.min(1, Math.abs(v) / (vmax || 1));
  return COLORS.neutral.clone().lerp(v >= 0 ? COLORS.pos : COLORS.neg, Math.sqrt(a));
}

const fmt = (v: number, p = 4) => (Math.abs(v) >= 1e4 || (Math.abs(v) < 1e-3 && v !== 0) ? v.toExponential(p - 1) : v.toPrecision(p));

/** One model (or one A->B difference) as instanced geometry. */
export class TensorScene {
  readonly group = new THREE.Group();
  readonly heads: THREE.InstancedMesh;
  readonly mlp: THREE.InstancedMesh;
  readonly resid: THREE.InstancedMesh;
  readonly arcs = new THREE.Group();
  readonly L: number; readonly H: number; readonly T: number; readonly ro: number;
  private selected: { mesh: THREE.InstancedMesh; id: number; color: THREE.Color } | null = null;
  /** White outline around the selected instance; drawn around it, never changing its height. */
  private readonly outline = new THREE.LineSegments(new THREE.EdgesGeometry(box), new THREE.LineBasicMaterial({ color: 0xffffff }));
  /** Hover outline, mirrored across panels so the same tensor slice is marked in A, B and Δ. */
  private readonly hoverBox = new THREE.LineSegments(new THREE.EdgesGeometry(box), new THREE.LineBasicMaterial({ color: 0xffcf5c }));
  /** Fat-line materials; their resolution must follow the viewport size. */
  private readonly lineMats: LineMaterial[] = [];
  /** Token -> x (null = in a collapsed segment: zero-size instance, never drawn or picked). */
  readonly lay: XLayout;

  constructor(
    readonly run: Run,                       // the run whose tokens/readout are shown
    readonly scales: Scales,
    readonly color: ColorMode,
    readonly delta: { pair: Pair; a: Run } | null = null,   // set: draw ||B - A||, run = B
    readonly showClamped = false,
    lay?: XLayout,
  ) {
    const m = run.m;
    this.L = m.model.n_layers; this.H = m.model.n_heads; this.T = m.tokens.length; this.ro = m.readout.position;
    this.lay = lay ?? fullLayout(this.T);
    const X = this.lay.x;
    const { L, H, T } = this;
    const { SZ, CELL } = LAYOUT;
    const t = run.t;
    const d = delta?.pair.t;
    const mat = () => new THREE.MeshLambertMaterial({ color: 0xffffff });
    this.heads = new THREE.InstancedMesh(box, mat(), L * H * T);
    this.mlp = new THREE.InstancedMesh(box, mat(), L * T);
    this.resid = new THREE.InstancedMesh(box, mat(), (L + 1) * T);
    const M = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();
    const w = CELL / H;

    for (let l = 0; l < L; l++) for (let tt = 0; tt < T; tt++) {
      const xt = X[tt], vis = xt != null ? 1 : 0, x0 = (xt ?? 0) - CELL / 2, z = -l * SZ;
      for (let h = 0; h < H; h++) {
        const v = d ? d.d_head_norm.get(l, h, tt) : t.head_norm.get(l, h, tt);
        const id = (l * H + h) * T + tt;
        p.set(x0 + (h + 0.5) * w, 0, z + 0.25); s.set(w * 0.82 * vis, Math.max(height(scales.head, v), 0.004) * vis, 0.42 * vis);
        this.heads.setMatrixAt(id, M.compose(p, q, s));
        this.heads.setColorAt(id, d ? deltaColor(v, scales.head) : this.headColor(l, h, tt));
      }
      const vm = d ? d.d_mlp_norm.get(l, tt) : t.mlp_norm.get(l, tt);
      p.set(xt ?? 0, 0, z - 0.32); s.set(CELL * 0.92 * vis, Math.max(height(scales.mlp, vm), 0.004) * vis, 0.42 * vis);
      this.mlp.setMatrixAt(l * T + tt, M.compose(p, q, s));
      this.mlp.setColorAt(l * T + tt, d ? deltaColor(vm, scales.mlp) : this.mlpColor(l, tt));
    }
    for (let l = 0; l <= L; l++) for (let tt = 0; tt < T; tt++) {
      const v = d ? d.d_resid_norm.get(l, tt) : t.resid_norm.get(l, tt);
      const xt = X[tt], vis = xt != null ? 1 : 0;
      p.set(xt ?? 0, 0, -l * SZ + 0.78); s.set(CELL * 0.92 * vis, Math.max(height(scales.resid, v), 0.004) * vis, 0.16 * vis);
      this.resid.setMatrixAt(l * T + tt, M.compose(p, q, s));
      this.resid.setColorAt(l * T + tt, d ? deltaColor(v, scales.resid) : COLORS.resid);
    }
    for (const im of [this.heads, this.mlp, this.resid]) {
      im.instanceMatrix.needsUpdate = true;
      if (im.instanceColor) im.instanceColor.needsUpdate = true;
      im.computeBoundingSphere();
      this.group.add(im);
    }
    this.group.add(this.arcs);
    this.outline.visible = false;
    this.outline.matrixAutoUpdate = false;
    this.group.add(this.outline);
    this.hoverBox.visible = false;
    this.hoverBox.matrixAutoUpdate = false;
    this.group.add(this.hoverBox);
    this.addReadoutFrame();
    if (!d) this.addMarginRibbon();
  }

  private headColor(l: number, h: number, tt: number): THREE.Color {
    if (this.delta) return COLORS.delta;
    if (this.color === "dla" && tt === this.ro) {
      const v = (this.showClamped ? this.run.t.head_attr_clamped : this.run.t.head_attr).get(l, h);
      return diverging(v, this.scales.dla);
    }
    return this.color === "dla" ? COLORS.head.clone().multiplyScalar(DIM.head) : COLORS.head;
  }

  private mlpColor(l: number, tt: number): THREE.Color {
    if (this.delta) return COLORS.delta;
    if (this.color === "dla" && tt === this.ro) {
      const v = (this.showClamped ? this.run.t.mlp_attr_clamped : this.run.t.mlp_attr).get(l);
      return diverging(v, this.scales.dla);
    }
    if (this.color === "q3") {
      const f = this.run.t.q3_count.get(l, tt) / this.scales.q3;
      return COLORS.neutral.clone().lerp(COLORS.q3, Math.min(1, f));
    }
    return this.color === "dla" ? COLORS.mlp.clone().multiplyScalar(DIM.mlp) : COLORS.mlp;
  }

  /** A polyline drawn with a fixed pixel width (presentation only; the points are unchanged). */
  private fatLine(pts: THREE.Vector3[], color: THREE.Color | number, px: number, dashed = false): Line2 {
    const g = new LineGeometry().setPositions(pts.flatMap((v) => [v.x, v.y, v.z]));
    const m = new LineMaterial({ color: new THREE.Color(color).getHex(), linewidth: px, dashed, dashSize: 0.3, gapSize: 0.2 });
    this.lineMats.push(m);
    const ln = new Line2(g, m);
    if (dashed) ln.computeLineDistances();
    return ln;
  }

  /** Viewport size in CSS px, for the fat lines. */
  setResolution(w: number, h: number) {
    for (const m of this.lineMats) m.resolution.set(w, h);
  }

  private addReadoutFrame() {
    const { SZ } = LAYOUT;
    const x = this.lay.x[this.ro] ?? 0;
    this.group.add(this.fatLine([
      new THREE.Vector3(x - 0.5, 0.002, 1.0), new THREE.Vector3(x + 0.5, 0.002, 1.0),
      new THREE.Vector3(x + 0.5, 0.002, -(this.L - 1) * SZ - 0.6), new THREE.Vector3(x - 0.5, 0.002, -(this.L - 1) * SZ - 0.6),
      new THREE.Vector3(x - 0.5, 0.002, 1.0),
    ], COLORS.pos, LINE_PX.readout));
  }

  /** running_margin[l] = h^l_{t*} . w, drawn as a polyline beside the readout column.
   * Its last point equals the readout margin (closure). With showClamped the clamped pass is drawn too. */
  private addMarginRibbon() {
    const { SZ } = LAYOUT;
    // Placed clear of the readout outline and the layer labels (placement only; y and z bindings unchanged).
    const x = (this.lay.x[this.ro] ?? 0) + 4.6, k = 2.2 / (this.scales.margin || 1), y0 = 3.4;
    const line = (tensor: Tensor, color: THREE.Color, dashed: boolean) => {
      const pts: THREE.Vector3[] = [];
      for (let l = 0; l <= this.L; l++) pts.push(new THREE.Vector3(x, y0 + tensor.get(l) * k, -l * SZ + 0.78));
      this.group.add(this.fatLine(pts, color, LINE_PX.margin, dashed));
      for (const pt of pts) {
        const dot = new THREE.Mesh(new THREE.SphereGeometry(0.11, 10, 8), new THREE.MeshBasicMaterial({ color }));
        dot.position.copy(pt);
        this.group.add(dot);
      }
    };
    this.group.add(this.fatLine([new THREE.Vector3(x, y0, 0.78), new THREE.Vector3(x, y0, -this.L * SZ + 0.78)], 0x6a6a6a, LINE_PX.zero));
    line(this.run.t.running_margin, COLORS.pos, false);
    if (this.showClamped) line(this.run.t.running_margin_clamped, COLORS.q3, true);
    const zEnd = -this.L * SZ + 0.78;
    const last = this.run.t.running_margin.get(this.L);
    // End labels sit centred over the line's last point (not to its right), so they stay inside the panel.
    this.group.add(textSprite(`margin ${last.toFixed(3)}`, "#6b9bff", x, y0 + last * k + 0.6, zEnd, 15, 0.5));
    this.group.add(textSprite("0", "#8a8a8a", x + 0.3, y0, 0.78, 12));
    // Numbers at both ends: the polyline runs along depth, so lengths cannot be compared by eye.
    const first = this.run.t.running_margin.get(0);
    this.group.add(textSprite(`start ${first.toFixed(2)}`, "#8fb4ff", x + 0.4, y0 + first * k - 0.45, 0.78, 12));
    const cap = textSprite("h^l·w per layer", "#b0b0b0", x, y0 + last * k + 0.6, zEnd, 11, 0.5);
    cap.center.set(0.5, -0.9);
    this.group.add(cap);
    if (this.showClamped) {
      const lc = this.run.t.running_margin_clamped.get(this.L);
      this.group.add(textSprite(`clamped ${lc.toFixed(3)}`, "#d27bff", x, y0 + lc * k - 0.6, zEnd, 15, 0.5));
    }
  }

  /** Attention arcs for head (l, h) at query t: one tube per stored top-k key, radius and opacity <- A[q, k]. */
  showArcs(l: number, h: number, tq: number) {
    this.clearArcs();
    const A = this.run.t, K = A.attn_topk_idx.shape[3];
    const { SZ, CELL } = LAYOUT, X = this.lay.x;
    if (X[tq] == null) return;
    const xh = (tt: number) => (X[tt] ?? 0) - CELL / 2 + (h + 0.5) * (CELL / this.H);
    const yTop = (tt: number) => height(this.scales.head, A.head_norm.get(l, h, tt)) + 0.05;
    const z = -l * SZ + 0.25;
    const arc = (bx: number, by: number, val: number) => {
      const a = new THREE.Vector3(xh(tq), yTop(tq), z), b = new THREE.Vector3(bx, by, z);
      const mid = new THREE.Vector3((a.x + b.x) / 2, Math.max(a.y, b.y) + 0.6 + 0.12 * Math.abs(a.x - b.x), z);
      const tube = new THREE.TubeGeometry(new THREE.QuadraticBezierCurve3(a, mid, b), 32, 0.025 + 0.09 * Math.min(1, val), 6, false);
      this.arcs.add(new THREE.Mesh(tube, new THREE.MeshBasicMaterial({ color: COLORS.arc, transparent: true, opacity: 0.45 + 0.55 * Math.min(1, val) })));
      return mid;
    };
    // One tube per stored top-k key, radius and opacity <- A[q, k].
    for (let k = 0; k < K; k++) {
      const key = A.attn_topk_idx.get(l, h, tq, k), val = A.attn_topk_val.get(l, h, tq, k);
      if (key === 65535 || X[key] == null || val <= 0.005) continue;
      arc(xh(key), yTop(key), val);
    }
    // Keys inside a collapsed segment are not dropped: they add up into ONE arc to that gap, labelled with the sum.
    for (const [g, sum] of this.gapSums(l, h, tq)) {
      if (sum <= 0.005) continue;
      const mid = arc(g.x, 0.15, sum);
      this.arcs.add(textSprite(`Σ ${sum.toFixed(2)} → ${g.label} (collapsed)`, "#e8e8e8", g.x, mid.y * 0.75, z, 11, 0.5));
    }
  }

  /** Summed stored attention from (l, h, tq) to the tokens of each collapsed gap. */
  gapSums(l: number, h: number, tq: number): [Gap, number][] {
    const A = this.run.t, K = A.attn_topk_idx.shape[3], m = new Map<Gap, number>();
    for (let k = 0; k < K; k++) {
      const key = A.attn_topk_idx.get(l, h, tq, k);
      if (key === 65535 || this.lay.x[key] != null) continue;
      const g = this.lay.gaps.find((q) => key >= q.a && key <= q.b);
      if (g) m.set(g, (m.get(g) ?? 0) + A.attn_topk_val.get(l, h, tq, k));
    }
    return [...m];
  }

  clearArcs() {
    for (const c of [...this.arcs.children]) {
      const m = c as THREE.Mesh;
      if (!(c instanceof THREE.Sprite)) m.geometry.dispose();
      const mat = m.material as THREE.Material & { map?: THREE.Texture | null };
      mat.map?.dispose();
      mat.dispose();
      this.arcs.remove(c);
    }
  }

  /** Same kind of mark in this panel: the instance ids line up across panels (same T, L, H). */
  meshOfKind(kind: "heads" | "mlp" | "resid"): THREE.InstancedMesh {
    return kind === "heads" ? this.heads : kind === "mlp" ? this.mlp : this.resid;
  }

  kindOf(mesh: THREE.Object3D): "heads" | "mlp" | "resid" | null {
    return mesh === this.heads ? "heads" : mesh === this.mlp ? "mlp" : mesh === this.resid ? "resid" : null;
  }

  hover(mesh: THREE.InstancedMesh | null, id = -1) {
    this.hoverBox.visible = false;
    if (!mesh || id < 0) return;
    const im = new THREE.Matrix4();
    mesh.getMatrixAt(id, im);
    const pos = new THREE.Vector3(), quat = new THREE.Quaternion(), sc = new THREE.Vector3();
    im.decompose(pos, quat, sc);
    this.hoverBox.matrix.compose(pos, quat, sc.set(sc.x + 0.06, sc.y + 0.06, sc.z + 0.06));
    this.hoverBox.visible = true;
  }

  select(mesh: THREE.InstancedMesh | null, id = -1) {
    if (this.selected) {
      this.selected.mesh.setColorAt(this.selected.id, this.selected.color);
      this.selected.mesh.instanceColor!.needsUpdate = true;
      this.selected = null;
    }
    this.outline.visible = false;
    if (!mesh || id < 0) return;
    const im = new THREE.Matrix4();
    mesh.getMatrixAt(id, im);
    const pos = new THREE.Vector3(), quat = new THREE.Quaternion(), sc = new THREE.Vector3();
    im.decompose(pos, quat, sc);
    this.outline.matrix.compose(pos, quat, sc.set(sc.x + 0.08, sc.y + 0.08, sc.z + 0.08));
    this.outline.visible = true;
    const c = new THREE.Color();
    mesh.getColorAt(id, c);
    this.selected = { mesh, id, color: c };
    mesh.setColorAt(id, COLORS.select);
    mesh.instanceColor!.needsUpdate = true;
  }

  /** Name and value of the tensor slice behind one instance. */
  info(mesh: THREE.Object3D, id: number): PickInfo | null {
    const { L, H, T, ro } = this;
    const t = this.run.t, m = this.run.m;
    const d = this.delta?.pair.t, a = this.delta?.a.t;
    const tok = (tt: number) => JSON.stringify(m.tokens[tt].text);
    if (mesh === this.heads) {
      const tt = id % T, lh = Math.floor(id / T), l = Math.floor(lh / H), h = lh % H;
      const kv = Math.floor(h / (H / m.model.n_kv_heads));
      const rows: [string, string][] = [["token", `t=${tt} ${tok(tt)}`], ["layer, head", `l=${l}, h=${h} (kv head ${kv})`]];
      if (d && a) {
        rows.push(["||o_B - o_A||", fmt(d.d_head_norm.get(l, h, tt))], ["||o_A||", fmt(a.head_norm.get(l, h, tt))], ["||o_B||", fmt(t.head_norm.get(l, h, tt))]);
        const dw = this.delta!.pair.t.d_weight_head;
        rows.push(["||dW q,k,v,o||_F", [0, 1, 2, 3].map((j) => fmt(dw.get(l, h, j), 3)).join(", ")]);
      } else {
        rows.push(["||o^l_{h,t}||", fmt(t.head_norm.get(l, h, tt))]);
        if (tt === ro) rows.push(["DLA to margin", fmt(t.head_attr.get(l, h))], ["DLA (clamped pass)", fmt(t.head_attr_clamped.get(l, h))]);
        const K = t.attn_topk_idx.shape[3];
        const keys: string[] = [];
        for (let k = 0; k < K && keys.length < 5; k++) {
          const key = t.attn_topk_idx.get(l, h, tt, k);
          if (key !== 65535) keys.push(`${fmt(t.attn_topk_val.get(l, h, tt, k), 3)} -> t=${key} ${tok(key)}`);
        }
        rows.push(["top keys A[q,k]", keys.join("\n")], ["top-16 mass", fmt(t.attn_topk_mass.get(l, h, tt), 4)]);
      }
      return { title: d ? "Head write difference" : "Attention head write o^l_{h,t}", rows, head: { l, h, t: tt },
               note: "o_h = softmax(q k^T / sqrt(64) + causal) v_kv(h) W_O[:, h]^T" };
    }
    if (mesh === this.mlp) {
      const tt = id % T, l = Math.floor(id / T);
      const rows: [string, string][] = [["token", `t=${tt} ${tok(tt)}`], ["layer", `l=${l}`]];
      if (d && a) {
        rows.push(["||m_B - m_A||", fmt(d.d_mlp_norm.get(l, tt))], ["||m_A||", fmt(a.mlp_norm.get(l, tt))], ["||m_B||", fmt(t.mlp_norm.get(l, tt))]);
        const dw = this.delta!.pair.t.d_weight_mlp;
        rows.push(["||dW gate,up,down||_F", [0, 1, 2].map((j) => fmt(dw.get(l, j), 3)).join(", ")]);
      } else {
        rows.push(["||m^l_t||", fmt(t.mlp_norm.get(l, tt))], ["Quadrant III neurons", `${t.q3_count.get(l, tt)} / ${m.model.d_ffn}`],
                  ["||QIII write||", fmt(t.q3_write_norm.get(l, tt))]);
        if (tt === ro) {
          rows.push(["DLA to margin", fmt(t.mlp_attr.get(l))], ["DLA (clamped pass)", fmt(t.mlp_attr_clamped.get(l))]);
          const F = m.model.d_ffn, order = Array.from({ length: F }, (_, i) => i);
          order.sort((x, y) => Math.abs(t.neuron_attr.get(l, y)) - Math.abs(t.neuron_attr.get(l, x)));
          rows.push(["top neurons (DLA | g~, u, c)", order.slice(0, 6).map((i) => {
            const g = t.g_last.get(l, i), u = t.u_last.get(l, i), e = m.readout.eps_q3;
            const q3 = g < -e && u < -e ? "  QIII" : "";
            return `i=${i}: ${fmt(t.neuron_attr.get(l, i), 3)} | ${fmt(g, 3)}, ${fmt(u, 3)}, ${fmt(t.c_last.get(l, i), 3)}${q3}`;
          }).join("\n")]);
        }
      }
      return { title: d ? "MLP write difference" : "MLP write m^l_t", rows, note: "m = sum_i SiLU(g~_i) u_i W_down[:, i]" };
    }
    if (mesh === this.resid) {
      const tt = id % T, l = Math.floor(id / T);
      const rows: [string, string][] = [["token", `t=${tt} ${tok(tt)}`], ["state", l === L ? `h^${L} (final, pre-norm)` : `h^${l} (enters layer ${l})`]];
      if (d && a) rows.push(["||h_B - h_A||", fmt(d.d_resid_norm.get(l, tt))], ["||h_A||", fmt(a.resid_norm.get(l, tt))], ["||h_B||", fmt(t.resid_norm.get(l, tt))]);
      else {
        rows.push(["||h^l_t||", fmt(t.resid_norm.get(l, tt))]);
        if (tt === ro) rows.push(["margin read here (h^l . w)", fmt(t.running_margin.get(l))]);
      }
      return { title: d ? "Residual difference" : "Residual stream h^l_t", rows };
    }
    return null;
  }

  dispose() {
    this.clearArcs();
    this.group.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.geometry && m.geometry !== box) m.geometry.dispose();
      const mat = m.material as THREE.Material | undefined;
      if (mat) mat.dispose();
    });
  }
}

/** Tilt (rad) of the token-label strip away from the floor plane, toward the camera. */
const TOKEN_TILT = 0.75;

/** Token labels as one canvas texture lying on the floor in front of layer 0 (vertical text, one slot per
 * open token). A collapsed gap gets its own label in its slot, "⋯ label · n tokens (collapsed)", so gap
 * labels and token labels never overlap. `hl` marks a found token in gold. */
export function tokenStrip(run: Run, lay: XLayout = fullLayout(run.m.tokens.length), hl = -1): THREE.Mesh {
  const slot = 40, hpx = 300, SX = LAYOUT.SX, x0 = -SX / 2;
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil((lay.width / SX) * slot); canvas.height = hpx;
  const g = canvas.getContext("2d")!;
  g.textBaseline = "middle";
  const px = (x: number) => ((x - x0) / SX) * slot;
  run.m.tokens.forEach((tk, i) => {
    const x = lay.x[i];
    if (x == null) return;
    const text = tk.text.replace(/\n/g, "\\n").replace(/ /g, "·").slice(0, 18) || "∅";
    g.save(); g.font = "600 32px ui-monospace, Menlo, monospace"; g.translate(px(x), 8); g.rotate(Math.PI / 2);
    g.fillStyle = i === run.m.readout.position ? "#6b9bff" : i === hl ? "#ffcf5c" : "#e6e6e6";
    g.fillText(text, 0, 0); g.restore();
  });
  for (const gp of lay.gaps) {
    g.save(); g.font = "600 30px ui-monospace, Menlo, monospace"; g.translate(px(gp.x), 8); g.rotate(Math.PI / 2);
    g.fillStyle = "#b0b0b0"; g.fillText(`⋯ ${gp.name}`.slice(0, 20), 0, -16); g.fillStyle = "#8a8a8a"; g.fillText(gp.k > 1 ? `${gp.k} parts · ${gp.n} tok` : `${gp.n} tokens`, 0, 18); g.restore();
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.anisotropy = 8; tex.colorSpace = THREE.SRGBColorSpace;
  const w = (canvas.width / slot) * SX, h = (hpx / slot) * SX;
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex, transparent: true }));
  // Hinged at its edge in front of layer 0 and tipped toward the viewer, so the text is less foreshortened.
  const tilt = TOKEN_TILT;
  mesh.rotation.x = -Math.PI / 2 + tilt;
  mesh.position.set(x0 + w / 2, 0.003 - (h / 2) * Math.sin(tilt), 1.1 + (h / 2) * Math.cos(tilt));
  return mesh;
}

/** Dashed floor lines along each collapsed gap, so a gap reads as "something is here, folded". */
export function gapLines(lay: XLayout, L: number): THREE.LineSegments {
  const pts: number[] = [];
  for (const g of lay.gaps) pts.push(g.x, 0.002, 1.0, g.x, 0.002, -(L - 1) * LAYOUT.SZ - 0.6);
  const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  const ls = new THREE.LineSegments(geo, new THREE.LineDashedMaterial({ color: 0x3a3a3a, dashSize: 0.3, gapSize: 0.25 }));
  ls.computeLineDistances();
  return ls;
}

/** A camera-facing text label (canvas texture) of fixed on-screen size: `px` is the cap height
 * band in CSS pixels for the current window, so far labels read as large as near ones. */
export function textSprite(text: string, color: string, x: number, y: number, z: number, px: number, align = 0): THREE.Sprite {
  const c = document.createElement("canvas");
  const g0 = c.getContext("2d")!;
  const font = "500 30px ui-monospace, Menlo, monospace";
  g0.font = font;
  c.width = Math.ceil(g0.measureText(text).width) + 12; c.height = 44;
  const g = c.getContext("2d")!;
  g.font = font; g.fillStyle = color; g.textBaseline = "middle";
  g.fillText(text, 6, 22);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false, sizeAttenuation: false }));
  // With sizeAttenuation off, screen height (px) = scale * P11 * viewportH / 2, P11 = 1 / tan(fov/2).
  const vh = Math.max(400, (typeof window !== "undefined" ? window.innerHeight : 900) - 60);
  const sh = (2 * px * (c.height / 30)) / (vh / Math.tan(THREE.MathUtils.degToRad(FOV) / 2));
  sp.scale.set((sh * c.width) / c.height, sh, 1);
  sp.center.set(align, 0.5);
  sp.position.set(x, y, z);
  return sp;
}

/** Layer labels at floor level, left of the first token and right of the answer column: fixed on-screen
 * size, so L29 at the back reads as large as L0 at the front. The right column sits 1.4 units clear of the
 * answer column's outline so "L29" never overlaps it. */
export function layerStrip(L: number, xLeft = 0, xRight = 0): THREE.Group {
  const grp = new THREE.Group();
  for (let l = 0; l < L; l++) {
    const z = -l * LAYOUT.SZ, col = l % 5 === 0 ? "#d4d4d4" : "#9b9b9b";
    grp.add(textSprite(`L${l}`, col, xLeft - 0.9, 0.05, z, 12, 1));
    if (xRight) grp.add(textSprite(`L${l}`, col, xRight + 1.4, 0.05, z, 12, 0));
  }
  return grp;
}
