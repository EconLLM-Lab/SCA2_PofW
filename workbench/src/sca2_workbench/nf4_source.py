"""Frozen NF4 codes/scales, streamed dequantization, and CPU-only diagnostic preparation.

CUDA codes MUST be prepared by the production HF loader (runner/prepare_nf4.py).
CPU preparation is a diagnostic, not a reconstruction of historical CUDA codes.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
from safetensors.torch import load_file, save

from sca2_workbench.stream_capture import SafetensorsSource

LINEARS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


def save_quant(path, codes, state):
    from sca2_workbench.cohort import publish
    tensors = {"codes": codes.detach().cpu().contiguous(),
               **{k: v.detach().cpu().contiguous() for k, v in state.as_dict(packed=True).items()}}
    publish(Path(path), save(tensors))


def load_quant(path, device, dtype):
    import bitsandbytes as bnb
    sd = load_file(str(path), device=str(device))
    codes = sd.pop("codes")
    state = bnb.functional.QuantState.from_dict(sd, device=torch.device(device))
    return bnb.functional.dequantize_4bit(codes, state).to(dtype)


class FrozenNF4Source(SafetensorsSource):
    """Same source API; quantized Linears, fp16 non-Linears, high precision forward.

    No LoRA enters this class. Exact F32 LoRA files are loaded separately, unmerged.
    """
    def __init__(self, snapshot, frozen, dtype=torch.float64, device="cpu", prepare_cpu=False):
        super().__init__(snapshot, dtype, device=device)
        self.frozen = Path(frozen)
        self.prepare_cpu = prepare_cpu
        if prepare_cpu and str(device) != "cpu":
            raise ValueError("CPU diagnostic quantization cannot prepare CUDA codes")
        provenance = self.frozen / "instrument.json"
        if provenance.exists():
            self.instrument = json.loads(provenance.read_text())
            if self.instrument["base_snapshot"] != Path(snapshot).name:
                raise ValueError("frozen quantization uses a different base snapshot")
            if str(device) == "cuda" and self.instrument["quantization_device"] != "cuda":
                raise ValueError("quantization device differs: never substitute CPU for CUDA codes")
        elif prepare_cpu:
            import bitsandbytes as bnb
            from sca2_workbench.cohort import json_bytes, publish
            self.instrument = {"quantization_device": "cpu", "bitsandbytes": bnb.__version__,
                               "quant_type": "nf4", "double_quant": True, "blocksize": 64,
                               "non_linear_dtype": "float16", "diagnostic": True,
                               "base_snapshot": Path(snapshot).name}
            publish(provenance, json_bytes(self.instrument))
        else:
            raise ValueError("missing frozen NF4 instrument; run prepare_nf4.py first")

    def _get(self, name):
        if name.endswith(tuple(f"{x}.weight" for x in LINEARS)):
            path = self.frozen / f"{name}.safetensors"
            if not path.exists():
                if not self.prepare_cpu:
                    raise ValueError(f"missing frozen codes: {name}")
                import bitsandbytes as bnb
                # Production bnb loads the checkpoint into fp16 before quantization.
                w = self._handle(name).get_tensor(name).to(torch.float16).contiguous()
                q, state = bnb.functional.quantize_4bit(w, blocksize=64,
                                                       compress_statistics=True, quant_type="nf4")
                save_quant(path, q, state)
                del w, q, state
            expected = self.instrument.get("files", {}).get(path.name)
            if expected:
                from sca2_workbench.cohort import digest
                if digest(path) != expected:
                    raise ValueError(f"frozen quantized codes digest mismatch: {name}")
            return load_quant(path, self.device, self.dtype)
        return self._handle(name).get_tensor(name).to(torch.float16).to(device=self.device, dtype=self.dtype)

    def _rows(self, name, ids):
        sl = self._handle(name).get_slice(name)
        return torch.cat([sl[int(i):int(i) + 1] for i in ids]).to(torch.float16).to(device=self.device, dtype=self.dtype)

    def unembed_chunks(self, chunk=4096):
        sl = self._handle(self._unembed_name).get_slice(self._unembed_name)
        for start in range(0, sl.get_shape()[0], chunk):
            yield start, sl[start:start + chunk].to(torch.float16).to(device=self.device, dtype=self.dtype)
