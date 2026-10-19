"""NF4 CUDA-vs-CPU code equality. CUDA files: benchmark/<dev>/bench (instrument.json hashes + 3 shipped layers).
CPU files: the Mac local_nf4 (bnb 0.50.2, CPU quantize_4bit of the fp16-cast checkpoint)."""
import hashlib, json, sys
from pathlib import Path
import torch
from safetensors.torch import load_file
import bitsandbytes as bnb

dev = Path(sys.argv[1]); cpu = Path(sys.argv[2]); out = Path(sys.argv[3])
inst = json.loads((dev / "nf4_instrument.json").read_text())
cuda_hash = inst["files"]
res = {"cuda_device": inst["device_name"], "cuda_versions": inst["versions"], "cpu_instrument": json.loads((cpu / "instrument.json").read_text()),
       "n_cuda_files": len(cuda_hash)}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
same, diff, missing = [], [], []
for name, h in cuda_hash.items():
    p = cpu / name
    if not p.exists(): missing.append(name); continue
    (same if sha(p) == h else diff).append(name)
res.update(files_sha256_identical=len(same), files_sha256_different=len(diff), files_missing_on_cpu=len(missing), different_files_head=diff[:10])
layers = {}
for f in sorted((dev / "nf4_layers").glob("*.safetensors")):
    a, b = load_file(str(f)), load_file(str(cpu / f.name))
    rec = {"tensors": {}}
    assert set(a) == set(b), (set(a) ^ set(b))
    for k in sorted(a):
        x, y = a[k], b[k]
        same_bits = x.dtype == y.dtype and x.shape == y.shape and bool(torch.equal(x.view(torch.uint8) if x.dtype != torch.uint8 else x, y.view(torch.uint8) if y.dtype != torch.uint8 else y))
        rec["tensors"][k] = {"dtype": str(x.dtype), "shape": list(x.shape), "bitwise_equal": same_bits,
                             "n_diff_elems": int((x.view(torch.uint8) != y.view(torch.uint8)).sum()) if x.shape == y.shape and x.dtype == y.dtype else None}
    # dequantized weight max |delta|
    deq = []
    for d in (a, b):
        d = dict(d); codes = d.pop("codes")
        st = bnb.functional.QuantState.from_dict(d, device=torch.device("cpu"))
        deq.append(bnb.functional.dequantize_4bit(codes, st).float())
    rec["dequant_max_abs_delta"] = float((deq[0] - deq[1]).abs().max())
    rec["all_bitwise_equal"] = all(t["bitwise_equal"] for t in rec["tensors"].values())
    layers[f.name] = rec
res["three_layers"] = layers
out.write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k not in ("cpu_instrument", "three_layers")}, indent=1))
for n, r in layers.items(): print(n, "bitwise_equal:", r["all_bitwise_equal"], "dequant max|d|:", r["dequant_max_abs_delta"], list(r["tensors"]))
