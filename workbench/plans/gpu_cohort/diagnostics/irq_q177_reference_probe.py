"""PM probe: is IRQ x wvs_Q177's paper_b_parity miss on the capture side or the float32 reference side?

Reuses the cohort unit's own inputs (registry, items, frozen T4 instrument, adapter) and reruns ONLY the
independent HF reference forward, in float32 (as the gate did) and in float64. Read-only on the run outputs.
"""
import json, sys
from pathlib import Path
import torch

WB = Path(sys.argv[1])
sys.path.insert(0, str(WB / "src"))
from sca2_workbench import cohort as CO, items as I, llama_capture as LC          # noqa: E402
from sca2_workbench.nf4_source import FrozenNF4Source                            # noqa: E402
from sca2_workbench.offload_hf import build_offloaded_hf                         # noqa: E402
from transformers import AutoTokenizer                                           # noqa: E402

torch.set_grad_enabled(False)
torch.use_deterministic_algorithms(True)
PKG = CO.PACKAGE
registry = json.loads((PKG / "models.json").read_text())
rec = next(x for x in json.loads((PKG / "items.json").read_text())["items"] if x["item_id"] == "wvs_Q177")
snap, adapter_dir, entry = CO.fetch_inputs(registry, "IRQ")
tok = AutoTokenizer.from_pretrained(snap)
item = I.Item(**{**{k: v for k, v in rec.items() if k != "archive"}, "codes": tuple(rec["codes"]),
                 "labels": tuple(rec["labels"]), "parts": tuple(tuple(x) for x in rec["parts"])})
ro = I.readout_ids(tok, item, {"date_string": "26 Jul 2024"})
frozen = PKG / "frozen_nf4_t4"

man = json.loads(next((WB / "exports/phase1_nf4_t4").glob("run__*_irq__wvs_Q177.json")).read_text())
cap = man["readout"]["probs"]
print("capture f64 probs:", {k: round(v, 8) for k, v in cap.items()})
for dt in (torch.float32, torch.float64):
    src = FrozenNF4Source(snap, frozen, dt, "cpu", prepare_cpu=True)
    model = build_offloaded_hf(snap, dt, adapter_dir=adapter_dir, model_id=registry["base"]["model_id"], source=src)
    logits = model(input_ids=torch.tensor([ro["prompt_ids"]])).logits[0, -1].double()
    del model
    src.drop_handles()
    p = LC.code_probs(logits, ro["code_token"])
    gap = max(abs(p[c] - cap[c]) for c in p)
    print(f"HF reference {str(dt):14s} max|p_ref - p_capture| = {gap:.3e}   probs:", {k: round(v, 8) for k, v in p.items()})
