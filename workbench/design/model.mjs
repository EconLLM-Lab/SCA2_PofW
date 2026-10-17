// Toy forward pass for the workbench design study.
//
// This is NOT Llama and NOT an SCA2 adapter. It is a seeded, four-layer,
// pre-norm transformer with GQA-free 2-head attention and a SwiGLU MLP, small
// enough to run in the page. Every number and every moving part in index.html
// comes from forward() below, so the figures obey the anatomy rule: the
// readout and the geometry come from one model. When the real hook lands
// (workbench/src/sca2_workbench/hooks.py, frozen API), each array here is
// replaced by the tensor named in BIND.
//
// The toy omits the final RMSNorm so that direct logit attribution is exact.
// Llama has a final norm; the real DLA will need a frozen-scale convention.

export const DIMS = { T: 6, L: 4, d: 16, H: 2, dh: 8, F: 32 };
export const TOKENS = ["How", "much", "trust", ",", "Answer", ":"];
export const CODES = [" 1", " 2"];
export const EPS = 0.05;

// The tensor each mark will bind to. Names follow the frozen hook API
// (h0, attn_sum, mlp_sum, h_final, g_tilde, u, c, logit_margin, attr_sum) and
// Hugging Face Llama module paths.
export const BIND = {
  resid: "h[l, t] = residual stream after model.layers.{l} (output_hidden_states[l+1][0, t, :])",
  head: "attn_out[l, h, t] = per-head slice of model.layers.{l}.self_attn.o_proj input x o_proj.weight[:, h*dh:(h+1)*dh]",
  poles: "c[l, t, :] = SiLU(g_tilde) * u = input to model.layers.{l}.mlp.down_proj",
  g_tilde: "g_tilde[l, t, i] = output of model.layers.{l}.mlp.gate_proj (pre-SiLU)",
  u: "u[l, t, i] = output of model.layers.{l}.mlp.up_proj",
  quadrant_iii: "quadrant_iii[l, t, i] = (g_tilde < -0.05) & (u < -0.05); clamp_quadrant_iii sets c to 0 there",
  overlap: "O_l = cos(c_clamped[l, T-1, :] | bank item, c_clamped[l, T-1, :] | WVS item)",
  adapter: "PeftModel adapter name (USA, MEX) on q_proj/k_proj/v_proj/o_proj; label only, no weights loaded",
  steer: "scale s written on c[l, :, i] (down_proj input column i) by a forward pre-hook on model.layers.{l}.mlp.down_proj",
  margin: "logit_margin = logits[0, T-1, id(' 1')] - logits[0, T-1, id(' 2')]",
  residual_check: "residual_inf_norm(h0, attn_sum, mlp_sum, h_final) < 1e-3",
  dla_check: "dla_abs_gap(logit_margin, attr_sum) < 1e-2",
};

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gaussFrom(rand) {
  return () => {
    const u1 = Math.max(rand(), 1e-12);
    const u2 = rand();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  };
}

const mat = (rows, cols, g, scale) => Array.from({ length: rows }, () => Array.from({ length: cols }, () => g() * scale));

export function weights(seed = 20261016) {
  const { T, L, d, H, dh, F } = DIMS;
  const g = gaussFrom(mulberry32(seed));
  const s = 1 / Math.sqrt(d);
  const layers = Array.from({ length: L }, () => ({
    Wq: Array.from({ length: H }, () => mat(d, dh, g, s)),
    Wk: Array.from({ length: H }, () => mat(d, dh, g, s)),
    Wv: Array.from({ length: H }, () => mat(d, dh, g, s)),
    Wo: Array.from({ length: H }, () => mat(dh, d, g, 1 / Math.sqrt(dh))),
    Wg: mat(d, F, g, s),
    Wu: mat(d, F, g, s),
    Wd: mat(F, d, g, 1 / Math.sqrt(F)),
  }));
  const inputs = { wvs: mat(T, d, g, 1), bank: mat(T, d, g, 1) };
  const WU = mat(CODES.length, d, g, s);
  return { layers, inputs, WU };
}

const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
const norm = (a) => Math.sqrt(dot(a, a));
const rms = (v) => { const r = Math.sqrt(dot(v, v) / v.length + 1e-6); return v.map((x) => x / r); };
const vecMat = (v, M) => { const out = new Array(M[0].length).fill(0); for (let i = 0; i < v.length; i++) { const row = M[i]; for (let j = 0; j < row.length; j++) out[j] += v[i] * row[j]; } return out; };
const silu = (z) => z / (1 + Math.exp(-z));
const f32 = Math.fround;

// options: { input: "wvs" | "bank", clamp: bool, steer: { l, i, scale } | null }
export function forward(W, { input = "wvs", clamp = false, steer = null } = {}) {
  const { T, L, d, H, dh, F } = DIMS;
  const h = W.inputs[input].map((row) => row.slice());
  const h32 = h.map((row) => Float32Array.from(row));
  const h0 = h.map((row) => row.slice());
  const attnSum = h.map(() => new Array(d).fill(0));
  const mlpSum = h.map(() => new Array(d).fill(0));
  const rec = { residNorm: [], headNorm: [], pattern: [], g: [], u: [], c: [], headOut: [] };
  for (let l = 0; l < L; l++) {
    const Lw = W.layers[l];
    const x = h.map(rms);
    const heads = [];
    const pats = [];
    for (let hh = 0; hh < H; hh++) {
      const q = x.map((v) => vecMat(v, Lw.Wq[hh]));
      const k = x.map((v) => vecMat(v, Lw.Wk[hh]));
      const v = x.map((vv) => vecMat(vv, Lw.Wv[hh]));
      const out = [];
      const pat = [];
      for (let t = 0; t < T; t++) {
        const sc = [];
        for (let s = 0; s <= t; s++) sc.push(dot(q[t], k[s]) / Math.sqrt(dh));
        const m = Math.max(...sc);
        const e = sc.map((z) => Math.exp(z - m));
        const Z = e.reduce((a, b) => a + b, 0);
        const p = e.map((z) => z / Z);
        const mix = new Array(dh).fill(0);
        p.forEach((ps, s) => { for (let j = 0; j < dh; j++) mix[j] += ps * v[s][j]; });
        out.push(vecMat(mix, Lw.Wo[hh]));
        pat.push(p);
      }
      heads.push(out);
      pats.push(pat);
    }
    for (let t = 0; t < T; t++) for (let j = 0; j < d; j++) {
      let a = 0;
      for (let hh = 0; hh < H; hh++) a += heads[hh][t][j];
      h[t][j] += a; attnSum[t][j] += a; h32[t][j] = f32(h32[t][j] + f32(a));
    }
    const x2 = h.map(rms);
    const gl = x2.map((v) => vecMat(v, Lw.Wg));
    const ul = x2.map((v) => vecMat(v, Lw.Wu));
    const cl = gl.map((gr, t) => gr.map((gv, i) => {
      let c = silu(gv) * ul[t][i];
      if (clamp && gv < -EPS && ul[t][i] < -EPS) c = 0;
      if (steer && steer.l === l && steer.i === i) c *= steer.scale;
      return c;
    }));
    for (let t = 0; t < T; t++) {
      const m = vecMat(cl[t], Lw.Wd);
      for (let j = 0; j < d; j++) { h[t][j] += m[j]; mlpSum[t][j] += m[j]; h32[t][j] = f32(h32[t][j] + f32(m[j])); }
    }
    rec.residNorm.push(h.map(norm));
    rec.headNorm.push(heads.map((out) => out.map(norm)));
    rec.headOut.push(heads);
    rec.pattern.push(pats);
    rec.g.push(gl); rec.u.push(ul); rec.c.push(cl);
  }
  // Conservation 1: fp32-accumulated h_final against the fp64 decomposition.
  let resid = 0;
  for (let t = 0; t < T; t++) for (let j = 0; j < d; j++) resid = Math.max(resid, Math.abs(h32[t][j] - (h0[t][j] + attnSum[t][j] + mlpSum[t][j])));
  // Logits at the final token from the fp32 h_final, as a real model would.
  const last = Array.from(h32[T - 1]);
  const logits = W.WU.map((row) => dot(last, row));
  const margin = logits[0] - logits[1];
  const mx = Math.max(...logits);
  const ex = logits.map((z) => Math.exp(z - mx));
  const probs = ex.map((e) => e / ex.reduce((a, b) => a + b, 0));
  // Conservation 2: direct logit attribution along WU[' 1'] - WU[' 2'].
  const dir = W.WU[0].map((v, j) => v - W.WU[1][j]);
  const attrEmbed = dot(h0[T - 1], dir);
  const attrHead = rec.headOut.map((heads) => heads.map((out) => dot(out[T - 1], dir)));
  const attrNeuron = rec.c.map((cl, l) => cl[T - 1].map((c, i) => c * dot(W.layers[l].Wd[i], dir)));
  let attrSum = attrEmbed;
  attrHead.forEach((row) => row.forEach((a) => { attrSum += a; }));
  attrNeuron.forEach((row) => row.forEach((a) => { attrSum += a; }));
  return { ...rec, resid, logits, margin, probs, attrEmbed, attrHead, attrNeuron, attrSum, dlaGap: Math.abs(margin - attrSum) };
}

// Layer overlap O_l between a bank-scenario stand-in and a WVS stand-in, both
// with the quadrant III clamp on, at the final token.
export function overlap(W) {
  const a = forward(W, { input: "bank", clamp: true });
  const b = forward(W, { input: "wvs", clamp: true });
  return a.c.map((cl, l) => { const x = cl[DIMS.T - 1], y = b.c[l][DIMS.T - 1]; return dot(x, y) / (norm(x) * norm(y)); });
}

// The neuron the steering console holds: largest |DLA| in layer 2, base pass.
export function steerTarget(W) {
  const base = forward(W);
  const l = 2;
  const row = base.attrNeuron[l];
  let i = 0;
  row.forEach((a, j) => { if (Math.abs(a) > Math.abs(row[i])) i = j; });
  return { l, i };
}
