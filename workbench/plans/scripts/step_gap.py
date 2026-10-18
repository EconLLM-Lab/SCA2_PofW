"""Measure the step-closure gate on the SmolLM2-135M family, and pin the audit corruption.

(1) Calibration: 3 models x 6 items, float64 and float32, ``step_closure`` rel at the worst
    (layer, position). tau = 10x the largest observed, rounded up to a power of ten.
(2) The audit of t_1547e1a8: scale one layer's *stored* MLP write by 1.001 (largest / median /
    smallest MLP write of the clean pass) and report each gate as a multiple of its tau.

Command (from workbench/):  env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/step_gap.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent))
from f32_gaps import ITEMS, MODELS, _load  # noqa: E402

from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import gates as G  # noqa: E402
from sca2_workbench import items as I  # noqa: E402
from sca2_workbench import llama_capture as LC  # noqa: E402

OUT = Path(__file__).parent / "out"


def _pow10(x: float) -> float:
    return 10.0 ** math.ceil(math.log10(x)) if x > 0 else 0.0


def main():
    one = G.GateTaus(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
    worst = {"float64": 0.0, "float32": 0.0}
    rows, demo = [], {}
    for key in MODELS:
        loaded = {dt: _load(key, dt) for dt in (torch.float64, torch.float32)}
        from transformers import AutoTokenizer  # noqa: PLC0415
        tok = AutoTokenizer.from_pretrained(EX.TOKENIZER_ID)
        for item_id in ITEMS:
            item = EX.item_from_id(item_id)
            ro = I.readout_ids(tok, item)
            jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
            rec = {"model": key, "item": item_id}
            for dt, (hf, W) in loaded.items():
                name = str(dt).replace("torch.", "")
                out = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm)
                g = G.check_capture(out, one)["step_closure"]
                rec[name] = g.rel
                worst[name] = max(worst[name], g.rel)
            rows.append(rec)
            print(f"{key:18s} {item_id:24s} step rel  f64 {rec['float64']:.2e}  f32 {rec['float32']:.2e}",
                  flush=True)
            if key == "smol_inst" and item_id in ("wvs_Q57", "wvs_Q81"):
                demo[item_id] = {}
                for dt, (hf, W) in loaded.items():
                    name = str(dt).replace("torch.", "")
                    taus = EX.TAUS[dt]
                    clean = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm)
                    size = clean["mlp_norm"].amax(-1)                        # (L,) largest MLP write
                    order = size.argsort()
                    picks = {"largest": int(order[-1]), "median": int(order[len(order) // 2]),
                             "smallest": int(order[0])}
                    demo[item_id][name] = {}
                    for label, layer in picks.items():
                        bad = LC.run(W, ro["prompt_ids"], j_plus=jp, j_minus=jm,
                                     scale_mlp_write=(layer, 1.001))
                        gates = G.check_capture(bad, taus)
                        demo[item_id][name][label] = {
                            "layer": layer,
                            **{n: gates[n].rel / gates[n].tau for n in
                               ("step_closure", "residual_closure", "readout")}}
                    clean_ratio = G.check_capture(clean, taus)["step_closure"]
                    demo[item_id][name]["clean_step_over_tau"] = clean_ratio.rel / clean_ratio.tau
    print()
    for name, w in worst.items():
        print(f"{name}: max step_closure rel {w:.3e} -> tau (10x, next power of ten) {_pow10(10 * w):.0e}")
    print(json.dumps(demo, indent=1))
    (OUT / "step_gap.json").write_text(json.dumps({"rows": rows, "worst": worst, "demo": demo}, indent=1))


if __name__ == "__main__":
    main()
