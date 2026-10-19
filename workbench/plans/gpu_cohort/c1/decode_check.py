"""C1 decode-equality: dequantize frozen NF4 layers with bitsandbytes.functional.dequantize_4bit.

usage: decode_check.py FROZEN_DIR OUT_JSON DEVICE [DEVICE ...]   (devices: cpu, cuda)
Mirrors nf4_source.load_quant (load_file -> QuantState.from_dict -> dequantize_4bit); fp16 output.
Hashes are sha256 of the raw dequantized tensor bytes. With >1 device, reports bitwise equality.
"""
import hashlib, json, sys
from pathlib import Path
import torch
from safetensors.torch import load_file
import bitsandbytes as bnb

LAYERS = {"early": "model.layers.0.self_attn.q_proj", "middle": "model.layers.16.mlp.gate_proj",
          "late": "model.layers.31.mlp.down_proj"}

def deq(path, device):
    sd = load_file(str(path), device=device)
    codes = sd.pop("codes")
    state = bnb.functional.QuantState.from_dict(sd, device=torch.device(device))
    out = bnb.functional.dequantize_4bit(codes, state)
    return out.cpu().contiguous()

def sha(t):
    return hashlib.sha256(t.view(torch.uint8).numpy().tobytes() if t.dtype != torch.uint8 else t.numpy().tobytes()).hexdigest()

frozen, out_path, devices = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
rec = {"torch": torch.__version__, "bitsandbytes": bnb.__version__, "devices": devices,
       "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "layers": {}}
for tag, name in LAYERS.items():
    f = frozen / f"{name}.weight.safetensors"
    r = {"file": f.name, "file_sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "per_device": {}}
    outs = {}
    for d in devices:
        t = deq(f, d); outs[d] = t
        r["per_device"][d] = {"dtype": str(t.dtype), "shape": list(t.shape), "dequant_sha256": sha(t),
                              "finite": bool(torch.isfinite(t.float()).all())}
    if len(devices) > 1:
        a, b = outs[devices[0]], outs[devices[1]]
        r["n_diff"] = int((a.view(torch.int16) != b.view(torch.int16)).sum())
        r["max_abs_delta"] = float((a.float() - b.float()).abs().max())
        r["bitwise_equal"] = r["n_diff"] == 0
    rec["layers"][tag] = r
    print(tag, name, {d: v["dequant_sha256"][:16] for d, v in r["per_device"].items()}, r.get("n_diff"), r.get("max_abs_delta"), flush=True)
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
if len(devices) > 1 and not all(l["bitwise_equal"] for l in rec["layers"].values()):
    print("DECODE_EQUALITY_FAIL"); sys.exit(1)
print("DECODE_CHECK_OK")
