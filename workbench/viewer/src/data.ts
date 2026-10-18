// Typed access to one export (contract: workbench/spec/export_contract.md).
// Nothing here computes model quantities. It decodes what the Python pass wrote, and runs
// one independent closure check on the decoded float32 arrays.

export interface ArrayMeta { dtype: "float32" | "uint16"; shape: number[]; offset: number; nbytes: number; desc: string }

/** One row of `conservation.relative.checks` (capture@1.1, written by `sca2_workbench.gates`):
 * the error relative to the size of the quantity it is an error of, `rel = error / scale`, and the
 * gate is `rel <= tau`. A tau is 10x the largest round-off measured for that check on that model
 * family (`plans/stage1_f32_gaps.md`), so a float32 export passes gates a float64 gate cannot. */
export interface RelativeCheck { error: number; scale: number; scale_desc: string; rel: number; tau: number; pass: boolean }

/** `conservation.relative` of a capture@1.1 manifest: the verdict the exporter computes. An
 * absolute threshold below one ulp of the stream it checks cannot be met, so the manifest states
 * every gate relative to the scale it measures, and `conservation.pass` follows this block. */
export interface RelativeConservation {
  taus: Record<string, number>; tau_multiple?: number; checks: Record<string, RelativeCheck>;
  pass: boolean; reference_key?: string;
}

export interface Conservation {
  residual_closure_inf: number; head_closure_inf: number; dla_gap: number; dla_gap_clamped: number;
  residual_closure_inf_clamped: number; eq6_teacher_forced_max_abs_gap: number;
  hf_hidden_max_rel_gap: number; hf_logits_max_rel_gap: number;
  hf64_hidden_max_rel_gap: number; hf64_logits_max_rel_gap: number;
  thresholds: Record<string, number>; pass: boolean;
  /** @1.1. Read this when it is here: it holds the verdict. Absent on manifests written before
   * relative gates were added. */
  relative?: RelativeConservation;
  /** false when the absolute gate sits below the round-off of the dtype the capture ran in (a
   * float32 export). Absent (older manifests): the absolute gate applies. */
  legacy_absolute_applicable?: boolean;
}

/** Contract @1.1: half-open token range [a, b) of one prompt part, written by the exporter. */
export interface Segment { a: number; b: number; kind: "template" | "system" | "instruction" | "question" | "options" | "answer_cue" | "readout"; label: string }

export interface RunManifest {
  kind: "run";
  schema?: string;
  segments?: Segment[] | null;   // @1.1; absent in @1 files
  model: { key: string; label: string; model_id: string; adapter: { dir: string; sha256: string } | null;
           n_layers: number; n_heads: number; n_kv_heads: number; head_dim: number; d_model: number; d_ffn: number };
  item: { item_id: string; kind: string; codes: string[]; labels: string[]; j_plus: string; j_minus: string; meta: Record<string, unknown> };
  tokens: { id: number; text: string }[];
  readout: { position: number; code_token: Record<string, number>; prefix_tokens: string[];
             probs: Record<string, number>; probs_clamped: Record<string, number>;
             margin: number; margin_clamped: number; embed_attr: number; embed_attr_clamped: number; eps_q3: number };
  conservation: Conservation;
  arrays: Record<string, ArrayMeta>;
  bin: string;
  provenance: Record<string, unknown>;
}

export interface PairManifest {
  kind: "pair"; a: string; b: string; item_id: string; schema?: string;
  d_probs: Record<string, number>; d_margin: number;
  // @1.1 (optional: absent in @1 files)
  d_margin_clamped?: number; d_embed_attr?: number; d_embed_attr_clamped?: number;
  conservation?: { d_attr_gap: number; d_attr_gap_float32: number; d_attr_gap_clamped: number; d_attr_gap_float32_clamped: number;
                   thresholds: Record<string, number>; pass: boolean; relative?: RelativeConservation;
                   legacy_absolute_applicable?: boolean };
  arrays: Record<string, ArrayMeta>; bin: string;
}

export interface IndexFile {
  models: Record<string, { model_id: string; adapter: string | null; label: string }>;
  runs: { file: string; model: string; label: string; item_id: string; T: number; pass: boolean; margin: number }[];
  pairs: { file: string; a: string; b: string; item_id: string; d_margin: number }[];
}

/** A dense row-major tensor view: get(i, j, ...) with bounds taken from the manifest shape. */
export class Tensor {
  constructor(readonly data: Float32Array | Uint16Array, readonly shape: number[], readonly desc: string) {}
  private strides(): number[] {
    const s = new Array(this.shape.length).fill(1);
    for (let i = this.shape.length - 2; i >= 0; i--) s[i] = s[i + 1] * this.shape[i + 1];
    return s;
  }
  get(...idx: number[]): number {
    const st = this.strides();
    let o = 0;
    for (let i = 0; i < idx.length; i++) {
      if (idx[i] < 0 || idx[i] >= this.shape[i]) throw new RangeError(`index ${idx} outside ${this.shape}`);
      o += idx[i] * st[i];
    }
    return this.data[o];
  }
  max(): number { let m = -Infinity; for (const v of this.data) if (v > m) m = v; return m; }
  absMax(): number { let m = 0; for (const v of this.data) if (Math.abs(v) > m) m = Math.abs(v); return m; }
  sum(): number { let s = 0; for (const v of this.data) s += v; return s; }
}

async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json() as Promise<T>;
}

async function fetchArrays(binName: string, arrays: Record<string, ArrayMeta>): Promise<Record<string, Tensor>> {
  const r = await fetch(`/exports/${binName}`);
  if (!r.ok) throw new Error(`${binName}: HTTP ${r.status}`);
  const buf = await r.arrayBuffer();
  const out: Record<string, Tensor> = {};
  for (const [name, m] of Object.entries(arrays)) {
    const n = m.shape.reduce((a, b) => a * b, 1);
    const data = m.dtype === "uint16" ? new Uint16Array(buf, m.offset, n) : new Float32Array(buf, m.offset, n);
    if (data.byteLength !== m.nbytes) throw new Error(`${name}: ${data.byteLength} bytes, manifest says ${m.nbytes}`);
    out[name] = new Tensor(data, m.shape, m.desc);
  }
  return out;
}

export interface Run { m: RunManifest; t: Record<string, Tensor>; clientCheck: ClientCheck }
export interface Pair { m: PairManifest; t: Record<string, Tensor> }

/** Closure recomputed in the browser from the float32 arrays that are drawn. Python passes
 * it at ~1e-14. Here it bounds what float32 storage did to the numbers on screen. */
export interface ClientCheck { dlaSum: number; dlaGap: number; headSumVsAttn: number;
  /** The manifest's absolute `dla_gap` gate, or null when the manifest says that gate does not
   * apply (`legacy_absolute_applicable === false`, i.e. a float32 capture, where the absolute gate
   * is narrower than the round-off of the stream). Then this page does not overrule the verdict the
   * manifest's relative gates carry: it shows the number and says where the verdict comes from. */
  pass: boolean | null }

function clientCheck(m: RunManifest, t: Record<string, Tensor>): ClientCheck {
  const dlaSum = m.readout.embed_attr + t.head_attr.sum() + t.neuron_attr.sum();
  const dlaGap = Math.abs(m.readout.margin - dlaSum);
  let headSumVsAttn = 0;
  const [L, H] = t.head_attr.shape;
  for (let l = 0; l < L; l++) {
    let s = 0;
    for (let h = 0; h < H; h++) s += t.head_attr.get(l, h);
    headSumVsAttn = Math.max(headSumVsAttn, Math.abs(s - t.attn_attr.get(l)));
  }
  const applicable = m.conservation.legacy_absolute_applicable !== false;
  return { dlaSum, dlaGap, headSumVsAttn, pass: applicable ? dlaGap < m.conservation.thresholds.dla_gap : null };
}

export const loadIndex = () => fetchJson<IndexFile>("/exports/index.json");

export async function loadRun(file: string): Promise<Run> {
  const m = await fetchJson<RunManifest>(`/exports/${file}`);
  const t = await fetchArrays(m.bin, m.arrays);
  return { m, t, clientCheck: clientCheck(m, t) };
}

export async function loadPair(file: string): Promise<Pair> {
  const m = await fetchJson<PairManifest>(`/exports/${file}`);
  return { m, t: await fetchArrays(m.bin, m.arrays) };
}

/** A, B and their pair export for one item. Cached, so switching tabs does not refetch. */
export interface Bundle { A: Run; B: Run; P: Pair; key: string }
const cache = new Map<string, Promise<Bundle>>();
export function loadBundle(a: string, b: string, item: string): Promise<Bundle> {
  const key = `${a}|${b}|${item}`;
  if (!cache.has(key)) {
    cache.set(key, Promise.all([
      loadRun(`run__${a}__${item}.json`), loadRun(`run__${b}__${item}.json`), loadPair(`pair__${a}__${b}__${item}.json`),
    ]).then(([A, B, P]) => ({ A, B, P, key })));
    if (cache.size > 6) cache.delete(cache.keys().next().value!);
  }
  return cache.get(key)!;
}
