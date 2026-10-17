"""Time and memory of the capture pass on random-weight models with the real Llama architectures.

Timing and memory do not depend on weight values, so random init is enough. The models are NOT the
real checkpoints (none of 360M / 1B / 8B is in the HF cache). Run one model per process so that
ru_maxrss is that model's own peak:

    env -u PYTHONPATH PYTHONPATH=src uv run python plans/scripts/scale_bench.py 360m f64-cpu f32-cpu f32-mps w16c32-mps

Modes: <variant>-<device> with variant in f64|f32|w16c32 (see lowprec.py), plus hf-<dtype>-<device> for
one stock HF forward pass (the cost of one reference check). T in {140, 306}.
RoPE is the plain default here. The real Llama-3.x configs use rope_type=llama3, which
llama_capture refuses today; that does not change the timing.
"""

import gc
import json
import resource
import sys
import time
from pathlib import Path

import torch
from transformers import LlamaConfig, LlamaForCausalLM

sys.path.insert(0, str(Path(__file__).parent))
import lowprec as LP  # noqa: E402

from sca2_workbench import llama_capture as LC  # noqa: E402

CFG = {   # layers, d_model, d_ffn, heads, kv heads, head_dim, vocab, tied   (values from the public configs)
    "135m": (30, 576, 1536, 9, 3, 64, 49152, True),
    "360m": (32, 960, 2560, 15, 5, 64, 49152, True),
    "1b": (16, 2048, 8192, 32, 8, 64, 128256, True),
    "8b": (32, 4096, 14336, 32, 8, 128, 128256, False),
    # 8B layer probe: real layer widths, vocab cut to 32000 so that a float64 copy of 1-2 layers fits in RAM.
    # use name "8bv-L1" / "8bv-L2". The lm_head cost is added analytically in the memo.
    "8bv": (32, 4096, 14336, 32, 8, 128, 32000, False),
}
TS = (140, 306)


def build(name):
    base, _, nl = name.partition("-L")
    L, d, f, h, kv, hd, V, tied = CFG[base]
    L = int(nl) if nl else L
    cfg = LlamaConfig(vocab_size=V, hidden_size=d, intermediate_size=f, num_hidden_layers=L,
                      num_attention_heads=h, num_key_value_heads=kv, head_dim=hd,
                      tie_word_embeddings=tied, rope_theta=500000.0, attn_implementation="eager")
    torch.manual_seed(0)
    return LlamaForCausalLM(cfg).eval(), cfg


def peak_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9


def sync(dev):
    if dev == "mps":
        torch.mps.synchronize()


def main():
    name, modes = sys.argv[1], sys.argv[2:]
    t0 = time.perf_counter()
    model, cfg = build(name)
    n_params = sum(p.numel() for p in model.parameters())
    print(json.dumps({"model": name, "n_params": n_params, "build_s": round(time.perf_counter() - t0, 1)}), flush=True)
    for mode in modes:
        gc.collect()
        if mode.startswith("hf-"):
            _, dt, dev = mode.split("-")
            dtype = {"f64": torch.float64, "f32": torch.float32}[dt]
            m = model.to(dtype).to(dev)
            for T in TS:
                ids = torch.randint(100, 5000, (1, T), device=dev)
                with torch.no_grad():
                    m(input_ids=ids); sync(dev)
                    ts = []
                    for _ in range(3):
                        t = time.perf_counter(); m(input_ids=ids); sync(dev); ts.append(time.perf_counter() - t)
                print(json.dumps({"model": name, "mode": mode, "T": T, "seconds": round(sorted(ts)[1], 4),
                                  "peak_rss_gb": round(peak_gb(), 2)}), flush=True)
            model = model.to(torch.float32).to("cpu")
            continue
        variant, dev = mode.split("-")
        wdt, mdt, sdt = LP.VARIANTS[variant]
        if variant == "f64":
            model64 = model.to(torch.float64)
            W = LC.weights_from_hf(model64)
            for T in TS:
                if name.startswith("1b") and T > 140:
                    continue          # 1B f64 at T=306 stacks ~5 GB of per-head outputs; skipped (memory)
                ids = torch.randint(100, 5000, (T,))
                LC.run(W, ids, j_plus=7, j_minus=9)
                ts = []
                for _ in range(3):
                    t = time.perf_counter(); LC.run(W, ids, j_plus=7, j_minus=9); ts.append(time.perf_counter() - t)
                print(json.dumps({"model": name, "mode": mode, "T": T, "seconds": round(sorted(ts)[1], 4),
                                  "peak_rss_gb": round(peak_gb(), 2)}), flush=True)
            del W, model64
            model = model.to(torch.float32)
            continue
        W = LC.weights_from_hf(model.to(torch.float32))           # float64 copy, then cast: fine for <= 1B
        Wd = LP.to_device(W, wdt, dev)
        del W
        gc.collect()
        for T in TS:
            ids = torch.randint(100, 5000, (T,))
            sec, _ = LP.timed(lambda: LP.run(Wd, ids, 7, 9, mdt, sdt, dev), dev, reps=3)
            row = {"model": name, "mode": mode, "T": T, "seconds": round(sec, 4), "peak_rss_gb": round(peak_gb(), 2)}
            if dev == "mps":
                row["mps_driver_gb"] = round(torch.mps.driver_allocated_memory() / 1e9, 2)
            print(json.dumps(row), flush=True)
        del Wd
        if dev == "mps":
            torch.mps.empty_cache()


if __name__ == "__main__":
    main()
