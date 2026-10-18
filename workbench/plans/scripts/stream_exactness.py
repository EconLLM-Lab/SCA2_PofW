"""Streamed vs in-memory capture on SmolLM2-135M-Instruct, float64: every gap, printed.

Run (from workbench/):  env -u PYTHONPATH uv run python plans/scripts/stream_exactness.py
"""
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
import test_stream_capture as T  # noqa: E402

LC, SC, I = T.LC, T.SC, T.I
model, tok = LC.load_hf(T.MODEL)
W = LC.weights_from_hf(model)
src = SC.SafetensorsSource(T.SNAP)
worst_all = 0.0
for qid in ("Q57", "Q81"):
    item = I.wvs_item(qid)
    ro = I.readout_ids(tok, item)
    jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
    outs = SC.run_streamed(src, ro["prompt_ids"], j_plus=jp, j_minus=jm, clamps=(False, True), keep_resid=True)
    for got, clamp in zip(outs, (False, True)):
        ref = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm, clamp_q3=clamp)
        gaps = {k: T._rel(got[k], ref[k]) for k in T.SAME_NAME}
        gaps.update({k: T._rel(torch.tensor(got[k]), torch.tensor(ref[k])) for k in T.SCALARS})
        gaps["resid_all"] = T._rel(got["_resid"], ref["_resid"])
        gaps["attn_topk_val"] = T._rel(got["attn_topk_val"], ref["attn_probs"].topk(SC.TOPK, -1)[0])
        w = max(gaps, key=gaps.get)
        worst_all = max(worst_all, gaps[w])
        print(f"{qid} T={got['T']} clamp={clamp}: worst {w} {gaps[w]:.2e}; "
              f"resid_all {gaps['resid_all']:.2e}; margin {got['margin']:+.6f} (ref {ref['margin']:+.6f})")
print(f"WORST over all arrays / items / modes: {worst_all:.2e}  (gate 1e-12)")
