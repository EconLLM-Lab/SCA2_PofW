"""Closure / DLA gaps and fidelity of the capture pass in float32 and bfloat16 (SmolLM2-135M-Instruct).

Run from workbench/:
    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/dtype_gaps.py
Output: plans/scripts/out/dtype_gaps.jsonl (one row per model x item x variant x device)
        plus a summary table on stdout (max over the cases, computed here, not by hand).
"""

import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent))
import lowprec as LP  # noqa: E402

from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import items as I  # noqa: E402
from sca2_workbench import llama_capture as LC  # noqa: E402

OUT = Path(__file__).parent / "out" / "dtype_gaps.jsonl"
MODELS = ["smol_inst", "smol_inst_usa_e3"]
ITEMS = ["wvs_Q57", "wvs_Q43", "wvs_Q81", "bank_USA_00023ac74dac"]
COMBOS = [("f64", "cpu"), ("f32", "cpu"), ("f32", "mps"), ("bf16", "cpu"), ("bf16", "mps"),
          ("hfmixed", "cpu"), ("hfmixed", "mps"), ("w16c32", "cpu"), ("w16c32", "mps")]


def main():
    sess = EX.Session()
    rows = []
    for key in MODELS:
        hf, W, _ = sess.model(key)
        for item_id in ITEMS:
            item = EX.item_from_id(item_id)
            ro = I.readout_ids(sess.tok, item)
            ids = ro["prompt_ids"]
            jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
            truth = LC.run(W, ids, j_plus=jp, j_minus=jm)
            p64 = LC.code_probs(truth["logits_last"], ro["code_token"])
            for variant, device in COMBOS:
                wdt, mdt, sdt = LP.VARIANTS[variant]
                Wd = LP.to_device(W, wdt, device)
                sec, r = LP.timed(lambda: LP.run(Wd, ids, jp, jm, mdt, sdt, device), device, reps=3)
                p = LC.code_probs(r["logits_last"], ro["code_token"])
                ha, na = truth["head_attr"].double(), truth["neuron_attr"].double()
                top = lambda x: set(x.abs().flatten().topk(50).indices.tolist())  # noqa: E731
                rows.append({
                    "model": key, "item": item_id, "T": len(ids), "variant": variant, "device": device,
                    "seconds": round(sec, 4),
                    "closure": r["closure"], "max_h": r["max_h"], "closure_rel": r["closure"] / r["max_h"],
                    "dla_gap": r["dla_gap"], "margin": r["margin"], "margin64": truth["margin"],
                    "margin_err": abs(r["margin"] - truth["margin"]),
                    "prob_err": max(abs(p[c] - p64[c]) for c in p),
                    "head_attr_relerr": ((r["head_attr"] - ha).abs().max() / ha.abs().max()).item(),
                    "neuron_attr_rel_l2": ((r["neuron_attr"] - na).norm() / na.norm()).item(),
                    "neuron_top50_overlap": len(top(r["neuron_attr"]) & top(na)) / 50,
                    "pass_closure_1e-3": r["closure"] < 1e-3, "pass_dla_1e-2": r["dla_gap"] < 1e-2,
                })
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"{len(rows)} rows -> {OUT}")
    hdr = ("variant", "device", "closure max", "closure/max|h| max", "dla_gap max", "margin_err max",
           "prob_err max", "head_attr relerr max", "neuron top50 min", "closure ok", "dla ok", "s @T=306")
    print(" | ".join(hdr))
    for variant, device in COMBOS:
        g = [r for r in rows if r["variant"] == variant and r["device"] == device]
        t306 = [r["seconds"] for r in g if r["T"] == max(x["T"] for x in g)]
        print(" | ".join(str(v) for v in (
            variant, device, f"{max(r['closure'] for r in g):.2e}", f"{max(r['closure_rel'] for r in g):.2e}",
            f"{max(r['dla_gap'] for r in g):.2e}", f"{max(r['margin_err'] for r in g):.2e}",
            f"{max(r['prob_err'] for r in g):.2e}", f"{max(r['head_attr_relerr'] for r in g):.2e}",
            f"{min(r['neuron_top50_overlap'] for r in g):.2f}",
            f"{sum(r['pass_closure_1e-3'] for r in g)}/{len(g)}", f"{sum(r['pass_dla_1e-2'] for r in g)}/{len(g)}",
            f"{max(t306):.3f}")))
    print("T values:", sorted({r["T"] for r in rows}), "max_h range:",
          f"{min(r['max_h'] for r in rows):.1f}..{max(r['max_h'] for r in rows):.1f}")


if __name__ == "__main__":
    sys.exit(main())
