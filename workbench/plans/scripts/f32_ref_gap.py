"""f32 analogue of the hf64 gate: last-row logits of (our f32 pass) vs (stock HF f32) vs (our f64 truth).

    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/f32_ref_gap.py
Model: SmolLM2-135M-Instruct, CPU, 4 items. Relative gap = max|a-b| / max|b| over the vocabulary at t*.
"""

import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM

sys.path.insert(0, str(Path(__file__).parent))
import lowprec as LP  # noqa: E402

from sca2_workbench import export as EX  # noqa: E402
from sca2_workbench import items as I  # noqa: E402
from sca2_workbench import llama_capture as LC  # noqa: E402


def rel(a, b):
    return ((a - b).abs().max() / b.abs().max()).item()


def main():
    sess = EX.Session()
    _, W, _ = sess.model("smol_inst")
    hf32 = AutoModelForCausalLM.from_pretrained(EX.MODELS["smol_inst"]["model_id"], dtype=torch.float32,
                                                attn_implementation="eager").eval()
    Wd = LP.to_device(W, torch.float32, "cpu")
    print("item | ours32 vs f64 | stockHF32 vs f64 | ours32 vs stockHF32   (relative, last-row logits)")
    for item_id in EX.DEFAULT_ITEMS:
        item = EX.item_from_id(item_id)
        ro = I.readout_ids(sess.tok, item)
        ids = ro["prompt_ids"]
        jp, jm = ro["code_token"][item.j_plus], ro["code_token"][item.j_minus]
        truth = LC.run(W, ids, j_plus=jp, j_minus=jm)["logits_last"]
        ours = LP.run(Wd, ids, jp, jm, torch.float32, torch.float32, "cpu")["logits_last"]
        with torch.no_grad():
            ref = hf32(input_ids=torch.tensor([ids])).logits[0, -1].double()
        print(f"{item_id:24s} {rel(ours, truth):.2e}   {rel(ref, truth):.2e}   {rel(ours, ref):.2e}")


if __name__ == "__main__":
    sys.exit(main())
