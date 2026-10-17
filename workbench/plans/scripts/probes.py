"""Small premise probes quoted in the memo.

    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/probes.py
"""

import json
import sys
from pathlib import Path

import torch
from transformers import LlamaConfig

from sca2_workbench import llama_capture as LC


def main():
    # 1. Llama-3.x RoPE: does llama_capture accept it?
    cfg = LlamaConfig(rope_theta=500000.0, rope_scaling={
        "rope_type": "llama3", "factor": 8.0, "low_freq_factor": 1.0, "high_freq_factor": 4.0,
        "original_max_position_embeddings": 8192})
    try:
        print("llama3 rope accepted:", LC._rope_theta(cfg))
    except ValueError as e:
        print("llama3 rope REJECTED by llama_capture._rope_theta:", str(e)[:100])
    # 2. device facts
    print("mps available:", torch.backends.mps.is_available(),
          "| recommended max working set GB:", round(torch.mps.recommended_max_memory() / 1e9, 2))
    try:
        torch.zeros(1, dtype=torch.float64, device="mps")
    except Exception as e:  # noqa: BLE001
        print("float64 on MPS:", str(e)[:90])
    # 3. fp32 ulp at the largest residual entry seen in the 135M runs (max|h| ~ 2.6e4)
    x = torch.tensor(25984.0, dtype=torch.float32)
    print("fp32 ulp at 25984:", (torch.nextafter(x, torch.tensor(1e9)) - x).item(),
          "| bf16 ulp:", (torch.nextafter(x.bfloat16(), torch.tensor(1e9).bfloat16()) - x.bfloat16()).item())
    # 4. stored dtype of the shipped 135M checkpoints (config.json torch_dtype)
    for name in ("SmolLM2-135M", "SmolLM2-135M-Instruct"):
        snap = next((Path.home() / ".cache/huggingface/hub" / f"models--HuggingFaceTB--{name}" / "snapshots").iterdir())
        print(name, "config torch_dtype:", json.loads((snap / "config.json").read_text()).get("torch_dtype"))


if __name__ == "__main__":
    sys.exit(main())
