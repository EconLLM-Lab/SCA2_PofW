"""Verifier: (a) streamed == in-memory on SmolLM2-135M f64; (5) 135M behavior unchanged.

Written independently of the producer's tests: my own key list, my own comparison,
my own read of the stored export.
"""
import json, sys
from pathlib import Path
import numpy as np
import torch

WB = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WB / "src"))
import sca2_workbench.llama_capture as LC
import sca2_workbench.stream_capture as SC
from sca2_workbench import items as I, gates as G

MODEL_INST = "HuggingFaceTB/SmolLM2-135M-Instruct"
MODEL_BASE = "HuggingFaceTB/SmolLM2-135M"


def rel(a, b):
    a, b = torch.as_tensor(a).double(), torch.as_tensor(b).double()
    return ((a - b).abs().max() / max(b.abs().max().item(), 1.0)).item()


def snapshot(mid):
    root = Path.home() / ".cache" / "huggingface" / "hub" / ("models--" + mid.replace("/", "--"))
    hits = sorted(root.glob("snapshots/*/model.safetensors"))
    return hits[0].parent


print("### 1. streaming exactness, 135M-Instruct, float64")
model, tok = LC.load_hf(MODEL_INST)
print("   loaded dtype:", next(model.parameters()).dtype)
W = LC.weights_from_hf(model)
for qid in ("Q57", "Q81"):
    item = I.wvs_item(qid)
    ro = I.readout_ids(tok, item)
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    src = SC.SafetensorsSource(snapshot(MODEL_INST))
    plain, clamped = SC.run_streamed(src, ro["prompt_ids"], j_plus=jp, j_minus=jm,
                                     clamps=(False, True), keep_resid=True)
    for got, clamp in ((plain, False), (clamped, True)):
        ref = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm, clamp_q3=clamp)
        keys = ["resid_norm", "attn_norm", "mlp_norm", "head_norm", "q3_write_norm", "g_last",
                "u_last", "c_last", "head_attr", "neuron_attr", "attn_attr", "mlp_attr",
                "running_margin", "margin", "embed_attr", "rho_final", "attr_sum",
                "residual_scale_inf", "attn_scale_inf", "residual_closure_inf", "head_closure_inf",
                "dla_gap"]
        gaps = {k: rel(got[k], ref[k]) for k in keys}
        gaps["resid (L+1,T,d)"] = rel(got["_resid"], ref["_resid"])
        gaps["topk_val"] = rel(got["attn_topk_val"], ref["attn_probs"].topk(SC.TOPK, -1)[0])
        worst = max(gaps, key=gaps.get)
        print(f"   {qid} clamp={clamp}: worst {worst} = {gaps[worst]:.3e} (gate 1e-12) "
              f"| resid bit-identical={torch.equal(got['_resid'], ref['_resid'])}")
        print(f"      equal: q3_count={torch.equal(got['q3_count'], ref['q3_count'])} "
              f"topk_idx={torch.equal(got['attn_topk_idx'], ref['attn_probs'].topk(SC.TOPK, -1)[1])} "
              f"code_logits vs logits_last={rel(got['code_logits'], ref['logits_last'][[jp, jm]]):.3e}")
        print(f"      streamed own gates: closure rel={got['residual_closure_inf']/got['residual_scale_inf']:.3e} "
              f"step rel={got['step_err_inf']/got['step_scale_inf']:.3e} dla rel={got['dla_gap']/(abs(got['margin'])+1):.3e}")
        print(f"      max|h| in-memory={ref['_resid'].abs().max().item():.4g} "
              f"streamed resid_scale={got['residual_scale_inf']:.4g}")

print("\n### 2. 135M behavior unchanged: fresh f64 pass vs the export on disk")
def read_array(binp, man, name):
    a = man["arrays"][name]
    dt = np.uint16 if a["dtype"] == "uint16" else np.float32
    buf = np.fromfile(binp, dtype=dt, count=a["nbytes"] // np.dtype(dt).itemsize, offset=a["offset"])
    return buf.reshape(a["shape"])

for key, mid, qid in (("smol_base", MODEL_BASE, "Q81"), ("smol_inst", MODEL_INST, "Q43")):
    man = json.loads((WB / "exports" / f"run__{key}__wvs_{qid}.json").read_text())
    binp = WB / "exports" / man["bin"]
    m2, t2 = LC.load_hf(mid)
    if mid == MODEL_BASE:
        from transformers import AutoTokenizer
        t2 = AutoTokenizer.from_pretrained(MODEL_INST)   # base has no chat template
    W2 = LC.weights_from_hf(m2)
    item = I.wvs_item(qid)
    ro = I.readout_ids(t2, item)
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    out = LC.run(W2, ro["prompt_ids"], j_plus=jp, j_minus=jm, clamp_q3=False)
    stored = {n: read_array(binp, man, n) for n in ("resid_norm", "attn_norm", "mlp_norm", "head_norm")}
    print(f"   {key}/{qid}: T={out['T']} stored T={man['tokens']['T'] if isinstance(man.get('tokens'), dict) else '?'} "
          f"readout.pos={man['readout']['position']}")
    for n, v in stored.items():
        print(f"      {n}: max rel gap fresh-vs-stored = {rel(v, out[n]):.3e}")
    sp = man["readout"]["probs"]
    print(f"      probs stored={ {k: round(v, 8) for k, v in sp.items()} }")
    print(f"      probs fresh ={ {c: round(float(LC.code_probs(out['logits_last'], ro['code_token'])[c]), 8) for c in sp} }")
    print(f"      margin fresh={out['margin']:.10f} stored={man['readout'].get('margin')}")
