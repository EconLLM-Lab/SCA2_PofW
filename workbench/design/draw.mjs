// Figure bodies for the design study. Pure functions of (k, P, run, state):
// `k` is the anatomy kit namespace, `run` is a forward() result from model.mjs.
// The same source runs at build time (Node) and in the page (inlined), so the
// drawn geometry and the readouts always come from one forward pass.

const tensor = (name, body) => `<g data-tensor="${name}"><title>${name}</title>${body}</g>`;

// ---------- Fig 1: tensor-block viewport ----------
export const V1 = { CX: 30, CY: 34, T: 6, L: 4, RES: 1.4, HEAD: 1.5, POLE: 0.55 };
export const v1Plate = () => ({ x: -24, y: -26, w: (V1.T - 1) * V1.CX + 58, d: (V1.L - 1) * V1.CY + 66, r: 6 });
export const v1Cell = (t, l) => [t * V1.CX, l * V1.CY];

export function v1Body(k, P, run, sel, TOKENS) {
  const S = (paths, style) => k.solidSvg(paths, style);
  const Ln = (d, style) => k.lineSvg(d, style);
  const at = (p) => k.iso(p, P);
  const plate = v1Plate();
  const out = [`<path class="iso-halo" d="${k.haloOf(plate, -12, 12, P)}"/>`];
  for (const [x, y] of k.corners(plate, 14)) out.push(S(k.cylinder(x, y, 5, -14, 2, P, 24), { tone: "lo" }));
  out.push(S(k.slabOf(plate, -10, 10, P, 6, 1.2), { tone: "mid" }));
  out.push(Ln(k.planOutline(k.insetPlan(plate, 4), 0, P), { tone: "lo" }));
  const screws = k.corners(plate, 8);
  out.push(Ln(screws.map(([x, y]) => k.ring(x, y, 1.8, 0, P, 14)).join(""), { tone: "lo" }));
  out.push(k.dotsSvg(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  // token ruler on the near +y edge, layer ruler on the near +x edge
  const ty = plate.y + plate.d - 18;
  const tStrip = { x: -14, y: ty, w: (V1.T - 1) * V1.CX + 28, d: 12, r: 1 };
  out.push(S(k.slabOf(tStrip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const tt = k.topTicks(tStrip.x + 2, tStrip.x + tStrip.w - 2, V1.CX / 6, 6, ty + 0.6, 0.6, [1.6, 3.2], P);
  out.push(Ln(tt.minor, { tone: "lo" }), Ln(tt.major, { tone: "mid" }));
  TOKENS.forEach((tok, t) => out.push(k.faceTextSvg(k.topMatrix([t * V1.CX, ty + 9.5], 0.6, P, "x"), tok, { size: 4.2, tone: "hi", anchor: "middle" })));
  const lx = plate.x + plate.w - 16;
  const lStrip = { x: lx, y: -14, w: 10, d: (V1.L - 1) * V1.CY + 28, r: 1 };
  out.push(S(k.slabOf(lStrip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  for (let l = 0; l < V1.L; l++) out.push(k.faceTextSvg(k.topMatrix([lx + 5, l * V1.CY + 1.5], 0.6, P, "x"), "L" + l, { size: 4.2, tone: "hi", anchor: "middle" }));
  // selection frame engraved on the plate around the selected cell
  const [sx, sy] = v1Cell(sel.t, sel.l);
  out.push(tensor(`selection (l=${sel.l}, t=${sel.t})`, Ln(k.planOutline({ x: sx - 11, y: sy - 11, w: 22, d: 22, r: 2 }, 0, P, 3), { tone: "lit" })));
  // cells, back to front
  const cells = [];
  for (let l = 0; l < V1.L; l++) for (let t = 0; t < V1.T; t++) cells.push([t, l]);
  cells.sort((a, b) => k.depthOf([...v1Cell(...a), 0], P) - k.depthOf([...v1Cell(...b), 0], P));
  for (const [t, l] of cells) {
    const [x, y] = v1Cell(t, l);
    const lit = t === sel.t && l === sel.l;
    const parts = [];
    const hr = run.residNorm[l][t] * V1.RES;
    parts.push(tensor(`h[${l},${t}]  |h|=${run.residNorm[l][t].toFixed(3)}`, S(k.slabOf({ x: x - 6, y: y - 6, w: 12, d: 12, r: 1 }, 0, hr, P, 3, 0.4), { tone: "hi", crease: "lo", lit })));
    // two heads side by side along y, two pole halves side by side along x
    const z1 = hr + 0.6;
    const heads = [0, 1].map((h) => ({ h, plan: { x: x - 6, y: y - 6 + h * 6.2, w: 12, d: 5.8, r: 0.8 }, hh: run.headNorm[l][h][t] * V1.HEAD }));
    heads.sort((a, b) => k.depthOf([x, a.plan.y + 3, z1], P) - k.depthOf([x, b.plan.y + 3, z1], P));
    for (const { h, plan, hh } of heads) parts.push(tensor(`attn_out[${l},${h},${t}]  |a|=${run.headNorm[l][h][t].toFixed(3)}`, S(k.slabOf(plan, z1, hh, P, 2, 0.3), { tone: "mid", crease: "lo" })));
    const z2 = z1 + Math.max(...heads.map((e) => e.hh)) + 0.6;
    const c = run.c[l][t];
    const pos = c.filter((v) => v > 0.05).length;
    const neg = c.filter((v) => v < -0.05).length;
    const poles = [
      { name: `c[${l},${t},:] > 0.05  n=${pos}`, plan: { x: x - 6, y: y - 6, w: 5.8, d: 12, r: 0.8 }, h: Math.max(0.4, pos * V1.POLE), tone: "hi" },
      { name: `c[${l},${t},:] < -0.05  n=${neg}`, plan: { x: x + 0.2, y: y - 6, w: 5.8, d: 12, r: 0.8 }, h: Math.max(0.4, neg * V1.POLE), tone: "lo" },
    ];
    poles.sort((a, b) => k.depthOf([a.plan.x + 3, y, z2], P) - k.depthOf([b.plan.x + 3, y, z2], P));
    for (const p of poles) parts.push(tensor(p.name, S(k.slabOf(p.plan, z2, p.h, P, 2, 0.3), { tone: p.tone, crease: "faint" })));
    out.push(`<g data-cell="${t},${l}">${parts.join("")}</g>`);
  }
  return out.join("");
}

// ---------- Fig 2: (g_tilde, u) phase plane ----------
export const V2 = { LIM: 80, EPS: 0.05 };
const v2Plate = () => ({ x: -V2.LIM - 12, y: -V2.LIM - 12, w: 2 * V2.LIM + 40, d: 2 * V2.LIM + 40, r: 6 });
// Axis half-range for the picked (l, t): the largest |g_tilde| or |u|, rounded up to 0.5, so no dot is clipped.
export const v2Range = (run, sel) => Math.max(1, Math.ceil(2 * Math.max(...run.g[sel.l][sel.t].map(Math.abs), ...run.u[sel.l][sel.t].map(Math.abs))) / 2);
export const v2Extent = () => { const p = v2Plate(); return [p, 26]; };

export function v2Body(k, P, run, sel, clamp) {
  const S = (paths, style) => k.solidSvg(paths, style);
  const Ln = (d, style) => k.lineSvg(d, style);
  const at = (p) => k.iso(p, P);
  const plate = v2Plate();
  const lim = V2.LIM;
  const R = v2Range(run, sel);
  const SC = lim / R;
  const out = [`<path class="iso-halo" d="${k.haloOf(plate, -10, 10, P)}"/>`];
  for (const [x, y] of k.corners(plate, 12)) out.push(S(k.cylinder(x, y, 5, -12, 2, P, 24), { tone: "lo" }));
  out.push(S(k.slabOf(plate, -8, 8, P, 6, 1.2), { tone: "mid" }));
  // the plotting field: a raised flat inlay, grid every 1.0, axes at 0
  const field = { x: -lim, y: -lim, w: 2 * lim, d: 2 * lim, r: 1 };
  out.push(S(k.slabOf(field, 0, 0.8, P, 2), { tone: "hi", crease: "none" }));
  const z = 0.8;
  const grid = [];
  for (let v = -R + 0.5; v < R - 1e-9; v += 0.5) {
    if (Math.abs(v) < 1e-9) continue;
    grid.push(k.lineOnTop([v * SC, -lim], [v * SC, lim], z, P), k.lineOnTop([-lim, v * SC], [lim, v * SC], z, P));
  }
  out.push(Ln(grid.join(""), { tone: "faint" }));
  // quadrant III pocket: g_tilde < -eps and u < -eps
  const e = V2.EPS * SC;
  const q3 = { x: -lim, y: -lim, w: lim - e, d: lim - e, r: 0.6 };
  out.push(S(k.slabOf(k.insetPlan(q3, 1.2), z, 0.01, P, 2), { tone: "lo", crease: "none", flat: true }));
  out.push(tensor("quadrant_iii = (g_tilde < -0.05) & (u < -0.05)", Ln(k.planOutline(k.insetPlan(q3, 1.2), z, P, 2), { tone: clamp ? "lit" : "hi" })));
  out.push(tensor("g_tilde axis (gate_proj output)", Ln(k.lineOnTop([-lim, 0], [lim, 0], z, P), { tone: "mid" })));
  out.push(tensor("u axis (up_proj output)", Ln(k.lineOnTop([0, -lim], [0, lim], z, P), { tone: "mid" })));
  // rulers on the near edges: g_tilde along x (+y edge), u along y (+x edge)
  const gy = lim + 4;
  const gStrip = { x: -lim, y: gy, w: 2 * lim, d: 8, r: 1 };
  out.push(S(k.slabOf(gStrip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const gt = k.topTicks(-lim, lim, SC / 10, 5, gy + 0.6, 0.6, [1.4, 3], P);
  out.push(Ln(gt.minor, { tone: "lo" }), Ln(gt.major, { tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([lim * 0.5, gy + 13], 0, P, "x"), "g_tilde", { size: 5, tone: "hi", anchor: "middle" }));
  out.push(k.faceTextSvg(k.topMatrix([-lim, gy + 13], 0, P, "x"), `-${R}`, { size: 4.5, tone: "hi", anchor: "middle" }));
  out.push(k.faceTextSvg(k.topMatrix([lim, gy + 13], 0, P, "x"), `+${R}`, { size: 4.5, tone: "hi", anchor: "middle" }));
  out.push(k.faceTextSvg(k.topMatrix([-lim * 0.5, gy + 13], 0, P, "x"), `L${sel.l} t${sel.t}`, { size: 5, tone: "hi", anchor: "middle" }));
  const ux = lim + 4;
  const uStrip = { x: ux, y: -lim, w: 8, d: 2 * lim, r: 1 };
  out.push(S(k.slabOf(uStrip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const ut = k.topTicks(-lim, lim, SC / 10, 5, ux + 0.6, 0.6, [1.4, 3], P, "y");
  out.push(Ln(ut.minor, { tone: "lo" }), Ln(ut.major, { tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([ux + 13, lim * 0.5], 0, P, "y"), "u", { size: 5, tone: "hi", anchor: "middle" }));
  // clamp toggle at the near corner
  const sw = { x: lim + 14, y: lim - 22, w: 12, d: 16, r: 2 };
  out.push(S(k.slabOf(sw, 0, 5, P, 3, 0.5), { tone: "mid" }));
  out.push(S(k.cylinder(sw.x + 6, sw.y + 8, 3.2, 5, 1.5, P, 20), { tone: "mid" }));
  const piv = [sw.x + 6, sw.y + 8, 6.5];
  const ang = (clamp ? 1 : -1) * 0.6;
  const tip = [piv[0], piv[1] + Math.sin(ang) * 12, piv[2] + Math.cos(ang) * 12];
  out.push(tensor(`clamp_quadrant_iii(eps=0.05) ${clamp ? "ON" : "OFF"}`, Ln(k.segment(piv, tip, P), { tone: clamp ? "lit" : "hi" }) + k.dotsSvg([at(tip)], { size: 1.3, tone: "hi" })));
  out.push(k.dotsSvg([at(piv)], { size: 0.8, tone: "mid" }));
  // neurons
  const g = run.g[sel.l][sel.t], u = run.u[sel.l][sel.t], c = run.c[sel.l][sel.t];
  const pos = [], neg = [], q3dots = [], rings = [];
  g.forEach((gv, i) => {
    const p = at([gv * SC, u[i] * SC, z]);
    const inQ3 = gv < -V2.EPS && u[i] < -V2.EPS;
    if (inQ3 && clamp) rings.push(k.ring(gv * SC, u[i] * SC, 2.4, z, P, 14));
    else if (inQ3) q3dots.push(p);
    else (c[i] >= 0 ? pos : neg).push(p);
  });
  out.push(tensor("c_i > 0 (positive pole)", k.dotsSvg(pos, { size: 1.7, tone: "hi" })));
  out.push(tensor("c_i < 0 (negative pole)", k.dotsSvg(neg, { size: 1.7, tone: "mid" })));
  out.push(tensor("quadrant III echo: c_i = SiLU(g_tilde)*u > 0", `<g class="v2-q3">${k.dotsSvg(q3dots, { size: 2.2, tone: "hi" })}</g>`));
  if (rings.length) out.push(tensor("quadrant III clamped: c_i = 0", Ln(rings.join(""), { tone: "lit" })));
  return out.join("");
}

// ---------- Fig 3: country labels + layer overlap gauge ----------
export function v3Body(k, P, O) {
  const S = (paths, style) => k.solidSvg(paths, style);
  const Ln = (d, style) => k.lineSvg(d, style);
  const at = (p) => k.iso(p, P);
  const plate = { x: -110, y: -36, w: 220, d: 72, r: 6 };
  const out = [`<path class="iso-halo" d="${k.haloOf(plate, -10, 10, P)}"/>`];
  for (const [x, y] of k.corners(plate, 12)) out.push(S(k.cylinder(x, y, 5, -12, 2, P, 24), { tone: "lo" }));
  out.push(S(k.slabOf(plate, -8, 8, P, 6, 1.2), { tone: "mid" }));
  out.push(Ln(k.planOutline(k.insetPlan(plate, 4), 0, P), { tone: "lo" }));
  const screws = k.corners(plate, 8);
  out.push(k.dotsSvg(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  const sign = (x0, name) => {
    const plinth = { x: x0 - 30, y: -14, w: 60, d: 16, r: 2 };
    const face = { x: x0 - 27, y: -8, w: 54, d: 4, r: 0.8 };
    const parts = [S(k.slabOf(plinth, 0, 6, P, 3, 0.5), { tone: "mid" })];
    parts.push(S(k.slabOf(face, 6, 30, P, 2, 0.3), { tone: "hi", crease: "lo" }));
    parts.push(k.faceTextSvg(k.sideMatrix([x0, face.y + face.d], 22, P, "left"), name, { size: 11, tone: "hi", anchor: "middle" }));
    // status lamp: off, because no adapter weights are loaded
    parts.push(S(k.cylinder(x0 + 22, -2.5, 2.4, 6, 2, P, 18), { tone: "lo" }));
    parts.push(k.dotsSvg([at([x0 - 22, -2.5, 6]), at([x0 - 14, -2.5, 6])], { size: 0.5 }));
    return tensor(`adapter label ${name} (PeftModel adapter name; weights not loaded)`, parts.join(""));
  };
  out.push(sign(-72, "USA"));
  // overlap gauge: a backing plate with scribe lines at O = -1..1, one pin per layer
  const Z0 = 40, ZK = 26;
  const back = { x: -26, y: -6, w: 52, d: 3, r: 0.6 };
  out.push(S(k.slabOf({ x: -30, y: -10, w: 60, d: 18, r: 2 }, 0, 6, P, 3, 0.5), { tone: "mid" }));
  out.push(S(k.slabOf(back, 6, 64, P, 2, 0.3), { tone: "mid", crease: "lo" }));
  const fy = back.y + back.d;
  const scribe = [-1, -0.5, 0, 0.5, 1].map((o) => k.sideSeam(back, Z0 + ZK * o, P, 2));
  out.push(Ln(scribe.filter((_, i) => i !== 2).join(""), { tone: "lo" }), Ln(scribe[2], { tone: "mid" }));
  const xs = O.map((_, l) => -18 + l * 12);
  const pinY = fy + 3;
  out.push(S(k.slabOf({ x: -24, y: fy, w: 48, d: 6, r: 0.8 }, 6, 4, P, 2, 0.3), { tone: "mid" }));
  O.forEach((o, l) => {
    const top = Z0 + ZK * o;
    out.push(tensor(`O_${l} = ${o.toFixed(4)}`, S(k.cylinder(xs[l], pinY, 1.5, 10, top - 10, P, 16), { tone: "hi", crease: "none" }) + k.dotsSvg([at([xs[l], pinY, top])], { size: 1.1, tone: "hi" })));
  });
  out.push(tensor("O_l curve (bank vs WVS, clamped c at final token)", Ln(k.pathOf(O.map((o, l) => at([xs[l], pinY, Z0 + ZK * o]))), { tone: "lit" })));
  out.push(sign(72, "MEX"));
  return out.join("");
}

// ---------- Fig 4: steering console ----------
export const V4 = { SCALES: [-1, 0, 1, 2.5], ANG: [-1.75, -0.6, 0.6, 1.75], KNOB: [-48, 0], DIAL: [42, 0], DR: 24, MARGIN_FULL: 3 };

export function v4Body(k, P, run, scale, target) {
  const S = (paths, style) => k.solidSvg(paths, style);
  const Ln = (d, style) => k.lineSvg(d, style);
  const at = (p) => k.iso(p, P);
  const plate = { x: -86, y: -42, w: 186, d: 84, r: 6 };
  const out = [`<path class="iso-halo" d="${k.haloOf(plate, -10, 10, P)}"/>`];
  for (const [x, y] of k.corners(plate, 12)) out.push(S(k.cylinder(x, y, 5, -12, 2, P, 24), { tone: "lo" }));
  out.push(S(k.slabOf(plate, -8, 8, P, 6, 1.2), { tone: "mid" }));
  out.push(Ln(k.planOutline(k.insetPlan(plate, 4), 0, P), { tone: "lo" }));
  const screws = k.corners(plate, 8);
  out.push(k.dotsSvg(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  const [kx, ky] = V4.KNOB, [dx, dy] = V4.DIAL;
  // cable from the selector to the gauge: the scale flows to the logits
  out.push(k.wireSvg(at([kx + 20, ky + 10, 0]), at([dx - 26, dy + 10, 0]), { via: [at([kx + 30, ky + 26, 0]), at([dx - 36, dy + 26, 0])], tone: "lo" }));
  // selector: bezel, detent dots, scale numerals, knurled knob, lit pointer
  out.push(S(k.cylinder(kx, ky, 26, 0, 2, P, 64, 0.5), { tone: "mid" }));
  const rt = k.radialTicks(kx, ky, 23, 36, 9, 2, [1.2, 2.2], P, -1.9, 3.8);
  out.push(Ln(k.ring(kx, ky, 23, 2, P, 64), { tone: "lo" }));
  out.push(Ln(rt.minor, { tone: "lo" }), Ln(rt.major, { tone: "mid" }));
  const det = V4.ANG.map((a) => [kx + Math.sin(a) * 19.5, ky - Math.cos(a) * 19.5]);
  out.push(k.dotsSvg(det.map(([x, y]) => at([x, y, 2])), { size: 0.9, tone: "hi" }));
  const labels = ["-1x", "0x", "1x", "+2.5x"];
  V4.ANG.forEach((a, j) => out.push(k.faceTextSvg(k.topMatrix([kx + Math.sin(a) * 32, ky - Math.cos(a) * 34 + 2], 0, P, "x"), labels[j], { size: 4.6, tone: "hi", anchor: "middle" })));
  out.push(S(k.cylinder(kx, ky, 14, 2, 9, P, 48, 0.5), { tone: "hi", crease: "lo" }));
  out.push(Ln(k.knurl(kx, ky, 14, 2, 11, 48, P), { tone: "lo" }));
  const a = V4.ANG[V4.SCALES.indexOf(scale)];
  out.push(tensor(`steer scale s=${scale} on c[${target.l}, :, ${target.i}]`, Ln(k.lineOnTop([kx, ky], [kx + Math.sin(a) * 12, ky - Math.cos(a) * 12], 11, P), { tone: "lit", free: "end" }) + k.dotsSvg([at([kx, ky, 11])], { size: 0.9, tone: "hi" })));
  // engraved tag: the activation the selector writes
  const tag = { x: kx - 16, y: 26, w: 52, d: 10, r: 1 };
  out.push(S(k.slabOf(tag, 0, 0.8, P, 2), { tone: "lo", crease: "none" }));
  out.push(k.dotsSvg([at([tag.x + 2.5, tag.y + 5, 0.8]), at([tag.x + tag.w - 2.5, tag.y + 5, 0.8])], { size: 0.5 }));
  out.push(tensor(`c[${target.l}, :, ${target.i}]`, k.faceTextSvg(k.topMatrix([tag.x + tag.w / 2, tag.y + 7], 0.8, P, "x"), `c[${target.l},:,${target.i}]`, { size: 4.8, tone: "hi", anchor: "middle" })));
  // margin gauge
  out.push(S(k.cylinder(dx, dy, V4.DR, 0, 10, P, 72, 0.8), { tone: "hi", crease: "lo" }));
  out.push(Ln(k.ring(dx, dy, V4.DR - 3, 10, P, 64), { tone: "lo" }));
  const dt = k.radialTicks(dx, dy, V4.DR - 3, 30, 5, 10, [1.3, 2.8], P, -2.4, 4.8);
  out.push(Ln(dt.minor, { tone: "lo" }), Ln(dt.major, { tone: "mid" }));
  out.push(Ln(k.lineOnTop([dx, dy - V4.DR + 2.8], [dx, dy - V4.DR + 6], 10, P), { tone: "hi" }));
  const m = Math.max(-V4.MARGIN_FULL, Math.min(V4.MARGIN_FULL, run.margin));
  const na = (m / V4.MARGIN_FULL) * 2.4;
  out.push(tensor(`logit_margin = ${run.margin.toFixed(4)}`, `<path class="iso-line" data-tone="lit" data-free="" d="${k.lineOnTop([dx - Math.sin(na) * 3, dy + Math.cos(na) * 3], [dx + Math.sin(na) * (V4.DR - 5), dy - Math.cos(na) * (V4.DR - 5)], 10.2, P)}" style="stroke-width:1.1"/>`));
  out.push(Ln(k.ring(dx, dy, 1.6, 10, P, 16), { tone: "mid" }));
  // probability columns for the two option codes
  const cols = [0, 1].map((j) => ({ j, plan: { x: 76, y: -30 + j * 16, w: 10, d: 10, r: 1 } }));
  cols.sort((p, q) => k.depthOf([p.plan.x, p.plan.y, 0], P) - k.depthOf([q.plan.x, q.plan.y, 0], P));
  for (const { j, plan } of cols) {
    out.push(S(k.slabOf(k.insetPlan(plan, -1.5), 0, 1.2, P, 2), { tone: "lo" }));
    out.push(tensor(`softmax over codes: P(' ${j + 1}') = ${run.probs[j].toFixed(4)}`, S(k.slabOf(plan, 1.2, 40 * run.probs[j] + 0.4, P, 2, 0.3), { tone: j === 0 ? "hi" : "mid", crease: "lo" })));
  }
  return out.join("");
}
