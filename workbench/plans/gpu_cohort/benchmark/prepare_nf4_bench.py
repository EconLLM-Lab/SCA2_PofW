"""Prepare CUDA NF4 using the frozen production loader, not manual CUDA requantization.

Run in the separate frozen quantization environment. Does not capture or train.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.dont_write_bytecode = True

from sca2_workbench.cohort import PACKAGE, digest, json_bytes, publish


def main():
    import torch
    import bitsandbytes as bnb
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    from sca2_workbench.nf4_source import save_quant
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", type=Path, required=True)
    args = ap.parse_args()
    # B0 BENCHMARK COPY: only change vs runner/prepare_nf4.py is this device check (any CUDA GPU).
    if not torch.cuda.is_available():
        raise ValueError("CUDA preparation requires a CUDA GPU; no CPU fallback")
    versions = {p: importlib.metadata.version(p) for p in ("torch", "transformers", "bitsandbytes", "huggingface_hub", "accelerate")}
    expected = {"torch": "2.11.0+cu130", "transformers": "4.46.3", "bitsandbytes": "0.50.2",
                "huggingface_hub": "0.36.2", "accelerate": "0.34.0"}
    if versions != expected:
        raise ValueError(f"production preparation stack differs: {versions} != {expected}")
    registry = json.loads((PACKAGE / "models.json").read_text())
    base = registry["base"]
    # Exactly score_cohort's BitsAndBytesConfig + from_pretrained arguments; revision/token added.
    config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    print("PRODUCTION_LOAD", json.dumps(versions), torch.cuda.get_device_name(), flush=True)
    model = AutoModelForCausalLM.from_pretrained(base["model_id"], revision=base["revision"],
                                                quantization_config=config, device_map="auto",
                                                token=os.environ.get("HF_TOKEN"))
    model.eval()
    hashes = {}
    for name, module in model.named_modules():
        if isinstance(module, bnb.nn.Linear4bit):
            path = args.frozen / f"{name}.weight.safetensors"
            save_quant(path, module.weight.data, module.weight.quant_state)
            hashes[path.name] = digest(path)
    if len(hashes) != 224:
        raise ValueError(f"expected 224 quantized Linears, found {len(hashes)}")
    # Production leaves embedding/norm/head unquantized at fp16; fail rather than assume it.
    for name, p in model.named_parameters():
        if name.endswith(("embed_tokens.weight", "norm.weight", "lm_head.weight")):
            if p.dtype != torch.float16:
                raise ValueError(f"production non-Linear {name} uses {p.dtype}, expected fp16")
    record = {"quantization_device": "cuda", "device_name": torch.cuda.get_device_name(),
              "python": platform.python_version(), "cuda": torch.version.cuda,
              "nvidia_smi": subprocess.check_output(["nvidia-smi"], text=True),
              "versions": versions, "quant_type": "nf4", "double_quant": True, "blocksize": 64,
              "non_linear_dtype": "float16", "base_snapshot": base["revision"],
              "diagnostic": False, "files": hashes}
    publish(args.frozen / "instrument.json", json_bytes(record))
    print("NF4_PREPARED", len(hashes), flush=True)


if __name__ == "__main__":
    main()
