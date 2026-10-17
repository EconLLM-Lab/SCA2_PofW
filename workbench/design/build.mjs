// Build the workbench design study: node build.mjs [--light]
// Writes index.html (dark) or index-light.html next to this file.
// The anatomy kit is imported from the installed skill, not copied into the repo.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import * as M from "./model.mjs";
import * as D from "./draw.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const SKILL = process.env.ANATOMY_SKILL || join(process.env.HOME, ".hermes/profiles/creative/skills/creative/anatomy");
const k = await import(pathToFileURL(join(SKILL, "kit/iso-kit.mjs")).href);
const { kitScript } = await import(pathToFileURL(join(SKILL, "scripts/inline-kit.mjs")).href);
const theme = process.argv.includes("--light") ? "light" : "dark";

const W = M.weights();
const target = M.steerTarget(W);
const sel = { l: 2, t: M.DIMS.T - 1 };
const run = M.forward(W);
const O = M.overlap(W);
const WIDTH = 600, HEIGHT = 360;

// ---- projections (each fitted to its object's extreme points) ----
const p1 = D.v1Plate();
const P1 = k.fitProjection([...k.boxCorners(p1, -14, 0), [0, 0, 60], [150, 0, 60]], WIDTH, HEIGHT, { pad: 26, azimuth: 38, elevation: 32 });
const [p2] = D.v2Extent();
const P2 = k.fitProjection([...k.boxCorners(p2, -12, 0), [p2.x + p2.w, p2.y + p2.d, 22]], WIDTH, HEIGHT, { pad: 24, azimuth: 45, elevation: 48 });
const P3 = k.fitProjection([...k.boxCorners({ x: -110, y: -36, w: 220, d: 72, r: 6 }, -12, 0), [0, 0, 72], [-100, 0, 38], [100, 0, 38]], WIDTH, HEIGHT, { pad: 26, azimuth: 30, elevation: 26 });
const P4 = k.fitProjection([...k.boxCorners({ x: -86, y: -42, w: 186, d: 84, r: 6 }, -12, 0), [80, -30, 48]], WIDTH, HEIGHT, { pad: 26, azimuth: 40, elevation: 38 });

const fmt = (x) => x.toExponential(2).replace("e-", "e\u2212");
const B = M.BIND;

const svg = (id, label, inner) => k.figureSvg({ width: WIDTH, height: HEIGHT, label, body: [`<g data-body="${id}">${inner}</g>`] });
const stage = (id, aria, inner) => `<div class="iso-stage" tabindex="0" data-stage="${id}" aria-label="${aria}">${inner}</div>`;

const v1 = k.plateHtml({
  fig: "Fig 1", title: "Tensor blocks", hint: "Hover or arrows: pick (l, t)",
  readout: `h[${sel.l},${sel.t}] |h| ${run.residNorm[sel.l][sel.t].toFixed(3)}`,
  keys: [
    { mark: "raised", label: `Bottom block, height 1.4 x |h|: ${B.resid}` },
    { mark: "edge", label: `Middle pair, height 1.5 x |a|: ${B.head}` },
    { mark: "lit", label: `Top pair, height 0.55 x count: positive and negative poles of ${B.poles}` },
  ],
  caption: `Axes: tokens on X, layers on Z (the floor's depth axis here), block types stacked on Y (up). Six tokens of a country-name-free prompt ending in "Answer:", four layers. Every height is read from one toy forward pass (model.mjs, seed 20261016, d=16, 2 heads, d_ffn=32). It is not Llama: the real view binds the named tensors through the frozen hook API.`,
  body: stage("v1", "Tensor-block viewport: arrow keys pick a token and layer", svg("v1", "Tensor blocks on a plate: tokens along one ruler, layers along the other; each cell stacks the residual block, two attention-head blocks and the positive and negative SwiGLU pole blocks.", D.v1Body(k, P1, run, sel, M.TOKENS))),
});

const q3count = (r, s) => r.g[s.l][s.t].filter((g, i) => g < -0.05 && r.u[s.l][s.t][i] < -0.05).length;
const v2 = k.plateHtml({
  fig: "Fig 2", title: "(g_tilde, u) plane", hint: "Click or C: clamp quadrant III",
  readout: `QIII ${q3count(run, sel)}/${M.DIMS.F} \u00b7 clamp off`,
  keys: [
    { mark: "raised", label: `x axis: ${B.g_tilde}` },
    { mark: "edge", label: `y axis: ${B.u}` },
    { mark: "lit", label: `Framed pocket: ${B.quadrant_iii}` },
    { mark: "dim", label: `Dots: one per neuron i, bright c_i > 0, grey c_i < 0, large = quadrant III echo, ring = clamped to 0` },
  ],
  caption: `One dot per MLP neuron of the layer and token picked in Fig 1, placed at (g_tilde, u). In quadrant III both factors are below -0.05, so SiLU(g_tilde) < 0 and u < 0 and the product c_i is positive: an echo of the negative pole. The toggle runs the forward pass again with clamp_quadrant_iii, which sets those c_i to 0; Fig 1, Fig 4 and the conservation bar update from that pass. In this random toy about a quarter of neurons fall in quadrant III; Cammarata reports about 4% in real SwiGLU models, so do not read the share.`,
  body: stage("v2", "Phase plane: press C or click to toggle the quadrant III clamp", svg("v2", "A plotting plate with a grid, g_tilde and u rulers, a framed quadrant III pocket and a toggle switch; one dot per neuron.", D.v2Body(k, P2, run, sel, false))),
});

const v3 = k.plateHtml({
  fig: "Fig 3", title: "USA / MEX overlap", hint: "Labels only: no weights",
  readout: `O_l l=0..3 \u00b7 toy base`,
  keys: [
    { mark: "raised", label: `Plates: ${B.adapter}` },
    { mark: "lit", label: `Pins and curve: ${B.overlap}` },
    { mark: "dim", label: `Lamps off: no adapter is loaded, so both labels share the base-model curve` },
  ],
  caption: `Two adapter labels side by side with a contour gauge between them. Each pin is one layer; its height is the cosine overlap O_l between a bank-scenario stand-in and a WVS stand-in, scribed from -1 to 1. Values here: ${O.map((o, l) => `O_${l} = ${o.toFixed(3)}`).join(", ")}, from the toy base model. No adapter weights were read, so the USA and MEX plates name tensors that do not exist on this page yet.`,
  body: stage("v3", "Country labels and layer overlap gauge", svg("v3", "Two engraved plates, USA and MEX, with unlit lamps, and a contour gauge of four pins whose heights trace the layer overlap curve.", D.v3Body(k, P3, O))),
});

const v4 = k.plateHtml({
  fig: "Fig 4", title: "Steer one neuron", hint: "Click or 1-4: pick scale",
  readout: `s 1x \u00b7 margin ${run.margin.toFixed(3)}`,
  keys: [
    { mark: "lit", label: `Selector: ${B.steer}; detents -1x, 0x, 1x (no edit), +2.5x` },
    { mark: "raised", label: `Gauge, full scale +/-3: ${B.margin}` },
    { mark: "edge", label: `Columns, 40 units = 1: softmax over the code tokens ' 1' and ' 2'` },
  ],
  caption: `The selector writes one number, a scale s, on one named activation: column ${target.i} of the down_proj input in layer ${target.l} (the toy neuron with the largest direct logit attribution). The forward pass then reruns; the needle reads the logit margin and the columns read P(' 1') and P(' 2'). Toy values: s=0 gives ${M.forward(W, { steer: { ...target, scale: 0 } }).margin.toFixed(3)}, s=1 gives ${run.margin.toFixed(3)}, s=2.5 gives ${M.forward(W, { steer: { ...target, scale: 2.5 } }).margin.toFixed(3)}, s=-1 gives ${M.forward(W, { steer: { ...target, scale: -1 } }).margin.toFixed(3)}.`,
  body: stage("v4", "Steering console: keys 1 to 4 pick scale -1x, 0x, 1x, +2.5x", svg("v4", "A rotary selector with four detents wired to a dial gauge that reads the logit margin, with two probability columns and an engraved tag naming the activation.", D.v4Body(k, P4, run, 1, target))),
});

const cbar = `<figure class="iso-figure" id="cons"><div class="iso-plate cons-plate">
  <div class="iso-plate-corners" aria-hidden="true"><span class="iso-plate-corner" data-corner="fig">Bar</span><span class="iso-plate-corner" data-corner="title">Conservation</span></div>
  <div class="cons-row" data-check="resid" data-tensor="${B.residual_check}"><span class="cons-lamp"></span><span class="cons-name">residual inf-norm</span><span class="cons-eq">max |h_final - (h0 + attn_sum + mlp_sum)|</span><span class="cons-val" data-val>${fmt(run.resid)}</span><span class="cons-lim">&lt; 1e\u22123</span><span class="cons-gauge"><i data-mark></i><b style="left:${(100 * 6) / 9}%"></b></span></div>
  <div class="cons-row" data-check="dla" data-tensor="${B.dla_check}"><span class="cons-lamp"></span><span class="cons-name">DLA abs gap</span><span class="cons-eq">|logit_margin - attr_sum|</span><span class="cons-val" data-val>${fmt(run.dlaGap)}</span><span class="cons-lim">&lt; 1e\u22122</span><span class="cons-gauge"><i data-mark></i><b style="left:${(100 * 7) / 9}%"></b></span></div>
</div><figcaption class="iso-legend"><span class="iso-caption">Both checks are computed on every forward pass of the page, including after a clamp or a steer. The residual check compares an fp32-accumulated h_final with the fp64 sum of its parts, so it measures float error, not a tautology. The gauge is log10 from 1e\u22129 (left) to 1 (right); the tick is the threshold. Bind: ${B.residual_check}; ${B.dla_check}.</span></figcaption></figure>`;

const header = `<header class="ds-head"><p class="ds-kicker">SCA2 workbench \u00b7 design study \u00b7 not the production UI</p><h1>Four views, no fake geometry</h1><p>Every mark names the tensor it will bind to (hover a mark for its name). Until the hook in workbench/src exists, every value here comes from a seeded toy transformer in model.mjs that runs in this page. Nothing here is a reading of Llama or of an SCA2 adapter.</p></header>`;

const extraCss = `
.iso{--anatomy-muted:#9b9b9b}
.iso[data-theme="light"]{--anatomy-muted:#626266}
.ds-head{margin:0 0 40px}
.ds-head h1{color:var(--anatomy-strong);font-size:22px;font-weight:600;margin:6px 0 10px;letter-spacing:-.01em}
.ds-head p{margin:0;color:var(--anatomy-text)}
.ds-kicker{font-family:var(--anatomy-mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--anatomy-muted)!important}
section,#cons{margin:0 0 56px}
.iso-stage{outline:none;cursor:pointer}
.iso-stage:focus-visible{box-shadow:0 0 0 1px var(--anatomy-hi)}
.cons-plate{padding:44px 20px 24px!important;display:grid;gap:10px}
.cons-row{display:grid;grid-template-columns:12px 12em 1fr 6.5em 4.5em 110px;align-items:center;gap:10px;font-family:var(--anatomy-mono);font-size:12px;color:var(--anatomy-text)}
.cons-eq{color:var(--anatomy-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cons-name{color:var(--anatomy-strong)}
.cons-val{color:var(--anatomy-strong);text-align:right;font-variant-numeric:tabular-nums}
.cons-lamp{width:10px;height:10px;border-radius:50%;box-shadow:inset 0 0 0 1px var(--anatomy-mid)}
.cons-row[data-ok="1"] .cons-lamp{background:var(--anatomy-green)}
.cons-row[data-ok="0"] .cons-lamp{background:var(--anatomy-red)}
.cons-gauge{position:relative;height:8px;box-shadow:inset 0 0 0 1px var(--anatomy-mid)}
.cons-gauge i{position:absolute;top:1px;bottom:1px;left:1px;background:var(--anatomy-hi)}
.cons-gauge b{position:absolute;top:-3px;bottom:-3px;width:1px;background:var(--anatomy-strong)}
@media (max-width:560px){.cons-row{grid-template-columns:12px 1fr 6.5em;}.cons-eq,.cons-gauge,.cons-lim{display:none}}
`;

const strip = (file) => readFileSync(join(HERE, file), "utf8").replace(/^export /gm, "");
const KIT_NAMES = ["iso", "depthOf", "slabOf", "cylinder", "corners", "haloOf", "planOutline", "insetPlan", "ring", "dotsSvg", "lineSvg", "solidSvg", "topTicks", "topMatrix", "sideMatrix", "faceTextSvg", "lineOnTop", "segment", "radialTicks", "knurl", "wireSvg", "pathOf"];
const live = `
${strip("model.mjs")}
${strip("draw.mjs")}
const k = { ${KIT_NAMES.join(", ")} };
const P1 = ${JSON.stringify(P1)}, P2 = ${JSON.stringify(P2)}, P4 = ${JSON.stringify(P4)};
const W = weights();
const target = ${JSON.stringify(target)};
const state = { sel: ${JSON.stringify(sel)}, clamp: false, scale: 1 };
const q = (s) => document.querySelector(s);
const body = (id) => q('[data-body="' + id + '"]');
const say = (id, text) => { const r = q("#" + id + " [data-readout]"); if (r && r.textContent !== text) r.textContent = text; };
let run = null;
// innerHTML below only receives SVG strings generated by draw.mjs from model numbers; no user text reaches it.
function render(which) {
  run = forward(W, { clamp: state.clamp, steer: { ...target, scale: state.scale } });
  const s = state.sel;
  if (which.v1) { body("v1").innerHTML = v1Body(k, P1, run, s, TOKENS); say("v1", "h[" + s.l + "," + s.t + "] |h| " + run.residNorm[s.l][s.t].toFixed(3)); }
  if (which.v2) { body("v2").innerHTML = v2Body(k, P2, run, s, state.clamp); const n = run.g[s.l][s.t].filter((g, i) => g < -0.05 && run.u[s.l][s.t][i] < -0.05).length; say("v2", "QIII " + n + "/" + DIMS.F + " \\u00b7 clamp " + (state.clamp ? "on" : "off")); }
  if (which.v4) { body("v4").innerHTML = v4Body(k, P4, run, state.scale, target); say("v4", "s " + state.scale + "x \\u00b7 margin " + run.margin.toFixed(3)); }
  const checks = { resid: [run.resid, 1e-3], dla: [run.dlaGap, 1e-2] };
  for (const [name, [v, lim]] of Object.entries(checks)) {
    const row = q('[data-check="' + name + '"]');
    row.dataset.ok = v < lim ? "1" : "0";
    row.querySelector("[data-val]").textContent = v.toExponential(2).replace("e-", "e\\u2212");
    const f = Math.max(0, Math.min(1, (Math.log10(Math.max(v, 1e-12)) + 9) / 9));
    row.querySelector("[data-mark]").style.width = "calc(" + (f * 100).toFixed(1) + "% - 2px)";
  }
}
const all = { v1: true, v2: true, v4: true };
render(all);
const s1 = q('[data-stage="v1"]');
const centres = [];
for (let l = 0; l < DIMS.L; l++) for (let t = 0; t < DIMS.T; t++) centres.push({ t, l, p: k.iso([t * V1.CX, l * V1.CY, 20], P1) });
s1.addEventListener("pointermove", (e) => {
  const svg = s1.querySelector("svg"); const box = svg.getBoundingClientRect(); const vb = svg.viewBox.baseVal;
  const x = (e.clientX - box.left) * vb.width / box.width + vb.x, y = (e.clientY - box.top) * vb.height / box.height + vb.y;
  let best = centres[0], bd = Infinity;
  for (const c of centres) { const d = (c.p[0] - x) ** 2 + (c.p[1] - y) ** 2; if (d < bd) { bd = d; best = c; } }
  if (best.t !== state.sel.t || best.l !== state.sel.l) { state.sel = { t: best.t, l: best.l }; render({ v1: true, v2: true }); }
});
s1.addEventListener("keydown", (e) => {
  const s = { ...state.sel };
  if (e.key === "ArrowRight") s.t = Math.min(DIMS.T - 1, s.t + 1); else if (e.key === "ArrowLeft") s.t = Math.max(0, s.t - 1);
  else if (e.key === "ArrowUp") s.l = Math.min(DIMS.L - 1, s.l + 1); else if (e.key === "ArrowDown") s.l = Math.max(0, s.l - 1); else return;
  e.preventDefault(); state.sel = s; render({ v1: true, v2: true });
});
const s2 = q('[data-stage="v2"]');
const toggle = () => { state.clamp = !state.clamp; render(all); };
s2.addEventListener("click", toggle);
s2.addEventListener("keydown", (e) => { if (e.key === "c" || e.key === "C" || e.key === " " || e.key === "Enter") { e.preventDefault(); toggle(); } });
const s4 = q('[data-stage="v4"]');
const setScale = (v) => { state.scale = v; render(all); };
s4.addEventListener("click", () => setScale(V4.SCALES[(V4.SCALES.indexOf(state.scale) + 1) % V4.SCALES.length]));
s4.addEventListener("keydown", (e) => {
  const j = "1234".indexOf(e.key); if (j >= 0) { e.preventDefault(); setScale(V4.SCALES[j]); return; }
  const i = V4.SCALES.indexOf(state.scale);
  if (e.key === "ArrowRight" || e.key === "ArrowUp") { e.preventDefault(); setScale(V4.SCALES[Math.min(3, i + 1)]); }
  if (e.key === "ArrowLeft" || e.key === "ArrowDown") { e.preventDefault(); setScale(V4.SCALES[Math.max(0, i - 1)]); }
});
window.__ds = { state, render, all, get run() { return run; } };
`;

const page = k.pageHtml({
  title: "SCA2 workbench design study",
  theme,
  width: 720,
  body: header + `<section id="v1">${v1}</section><section id="v2">${v2}</section><section id="v3">${v3}</section><section id="v4">${v4}</section>` + cbar,
  script: kitScript() + live,
}).replace("</style>", extraCss + "</style>");
const name = theme === "light" ? "index-light.html" : "index.html";
writeFileSync(join(HERE, name), page);
console.log("wrote", name, { target, margin: run.margin, resid: run.resid, dlaGap: run.dlaGap, O });
