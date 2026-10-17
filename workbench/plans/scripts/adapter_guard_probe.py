"""Probe what ``llama_capture.load_hf`` rejects when an adapter is not the one we trained (upload scenario).

    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/adapter_guard_probe.py
Copies models/usa_e1 into $TMPDIR, damages the copy, and calls load_hf on SmolLM2-135M-Instruct.
Expected by the memo's design: each case should be REJECTED by an upload validator. The script prints what
load_hf does today (ACCEPTED / REJECTED + message), without changing src/.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

from sca2_workbench import export as EX
from sca2_workbench import llama_capture as LC

SRC = EX.WORKBENCH / "models" / "usa_e1"
BASE = "HuggingFaceTB/SmolLM2-135M-Instruct"


def attempt(tag, adapter_dir):
    try:
        model, _ = LC.load_hf(BASE, str(adapter_dir))
        # does the merged model differ from the unmodified one?  (max abs diff on layer-0 q_proj)
        print(f"  {tag:46s} ACCEPTED by load_hf", flush=True)
        return model
    except Exception as e:  # noqa: BLE001
        print(f"  {tag:46s} REJECTED: {type(e).__name__}: {str(e)[:110]}", flush=True)


def fresh(tmp, name):
    d = Path(tmp) / name
    shutil.copytree(SRC, d)
    return d


def main():
    tmp = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
    sd = load_file(str(SRC / "adapter_model.safetensors"))
    print(f"adapter file: {len(sd)} tensors, dtypes {sorted({str(v.dtype) for v in sd.values()})}")

    d = fresh(tmp, "intact")
    ref = attempt("intact adapter (control)", d)
    w_ref = ref.model.layers[29].self_attn.q_proj.weight.detach().clone()

    d = fresh(tmp, "missing_layer29")
    cut = {k: v for k, v in sd.items() if ".layers.29." not in k}
    save_file(cut, str(d / "adapter_model.safetensors"))
    m = attempt(f"adapter file missing layer 29 ({len(sd) - len(cut)} tensors)", d)
    if m is not None:
        diff = (m.model.layers[29].self_attn.q_proj.weight - w_ref).abs().max().item()
        print(f"      layer-29 q_proj differs from the intact merge by {diff:.2e} (nonzero = silently different model)")

    d = fresh(tmp, "wrong_base_name")
    cfg = json.loads((d / "adapter_config.json").read_text())
    cfg["base_model_name_or_path"] = "meta-llama/Llama-3.2-1B"
    (d / "adapter_config.json").write_text(json.dumps(cfg))
    attempt("adapter_config says base=Llama-3.2-1B, loaded on 135M", d)

    d = fresh(tmp, "bias_lora")
    cfg = json.loads((d / "adapter_config.json").read_text())
    cfg["bias"] = "all"
    (d / "adapter_config.json").write_text(json.dumps(cfg))
    attempt("adapter_config bias='all' (file has no bias)", d)

    d = fresh(tmp, "extra_key")
    bad = dict(sd)
    bad["base_model.model.model.layers.99.self_attn.q_proj.lora_A.weight"] = torch.zeros(16, 576)
    save_file(bad, str(d / "adapter_model.safetensors"))
    attempt("adapter file with a tensor for layer 99", d)

    d = fresh(tmp, "nan")
    bad = dict(sd)
    k0 = next(iter(bad))
    bad[k0] = torch.full_like(bad[k0], float("nan"))
    save_file(bad, str(d / "adapter_model.safetensors"))
    m = attempt("adapter tensor all-NaN", d)
    if m is not None:
        print("      merged weights contain NaN:", bool(any(torch.isnan(p).any() for p in m.parameters())))


if __name__ == "__main__":
    sys.exit(main())
