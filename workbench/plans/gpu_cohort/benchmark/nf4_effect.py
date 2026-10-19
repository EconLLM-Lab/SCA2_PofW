"""Size of the CUDA-vs-CPU NF4 difference: weight level (3 layers) and readout level (Mac vs A100, f64)."""
import json, glob, sys
from pathlib import Path
import torch, bitsandbytes as bnb
from safetensors import safe_open
from safetensors.torch import load_file

B = Path("plans/gpu_cohort/benchmark"); cpu = Path("plans/gpu_cohort/local_nf4")
snap = sorted(Path.home().glob(".cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f2*"))[0]
idx = json.loads((snap / "model.safetensors.index.json").read_text())["weight_map"]
res = {"weights": {}, "readout": {}}
def deq(path):
    d = load_file(str(path)); c = d.pop("codes")
    return bnb.functional.dequantize_4bit(c, bnb.functional.QuantState.from_dict(d, device=torch.device("cpu"))).float()
for f in sorted((B / "a100/bench/nf4_layers").glob("*.safetensors")):
    name = f.name.replace(".safetensors", "")
    with safe_open(str(snap / idx[name]), "pt") as h: w = h.get_tensor(name).to(torch.float16).float()
    a, b = deq(f).reshape(w.shape), deq(cpu / f.name).reshape(w.shape)
    d = (a - b).abs()
    res["weights"][name] = {"max_abs_w": float(w.abs().max()), "rms_w": float(w.pow(2).mean().sqrt()),
        "frac_elements_differing": float((d > 0).float().mean()), "max_abs_delta_cuda_vs_cpu": float(d.max()),
        "rms_delta_cuda_vs_cpu": float(d.pow(2).mean().sqrt()),
        "rms_quant_error_cuda": float((w - a).pow(2).mean().sqrt()), "rms_quant_error_cpu": float((w - b).pow(2).mean().sqrt()),
        "max_quant_error_cuda": float((w - a).abs().max()), "max_quant_error_cpu": float((w - b).abs().max())}
    print(name, json.dumps(res["weights"][name]))
# readout level, same unit, Mac vs A100, float64
for item in ("wvs_Q57", "wvs_Q81", "wvs_Q107"):
    for arm in ("", "_arg"):
        m = glob.glob(str(B / f"mac/out/run__*float64_cpu*{arm}__{item}.json")); g = glob.glob(str(B / f"a100/bench/out/run__*float64_cuda*{arm}__{item}.json"))
        m = [x for x in m if (arm == "_arg") == x.split("__")[-2].endswith("_arg")]; g = [x for x in g if (arm == "_arg") == x.split("__")[-2].endswith("_arg")]
        if not (m and g): continue
        a, b = json.load(open(m[0]))["readout"], json.load(open(g[0]))["readout"]
        dl = max(abs(a["option_logprobs"][k] - b["option_logprobs"][k]) for k in a["option_logprobs"])
        dp = max(abs(a["probs"][k] - b["probs"][k]) for k in a["probs"])
        res["readout"][f"{item}{arm or '_base'}"] = {"max_abs_logprob_diff_nats_mac_vs_a100": dl, "max_abs_prob_diff": dp}
        print(item, arm or "base", "max |dlogp| nats", round(dl, 5), "max |dp|", round(dp, 6))
Path(sys.argv[1]).write_text(json.dumps(res, indent=1))
