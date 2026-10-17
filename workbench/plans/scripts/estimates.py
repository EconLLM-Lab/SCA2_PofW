"""ESTIMATES for the memo: time, peak RAM and export size per (model, prompt). Nothing here is measured.

    env -u PYTHONPATH uv run python plans/scripts/estimates.py

Inputs: out/fit_coef.json (Mac fits of out/scale.jsonl), the architecture table below (public configs),
and the byte formulas derived from export.py (checked against the real 135M files in the memo).

Mac time per (model, prompt):   t = 2*t_pass + (n_ref + n_codes)*t_hf + 10% serialisation
    t_pass = our capture pass (one forward with every tensor kept); t_hf = one stock HF forward.
    n_ref = 2 in f64 (stock HF + HF with the three casts removed), 1 in f32.
Colab time: roofline,  t_pass = 2*P_body*T / (peak_flops * eff) + 1 ms * L ;  t_hf = 0.8 * t_pass.
Peak RAM (current code, no streaming):  P*b + b*(2LHTd + 2LHT^2 + 7LTF + 6LTd + 3TV) + 0.5 GB
    (matches the measured 4.3 GB for 135M f64 T=306 and 14.1 GB for 1B f64 T=140 within 10%).
Peak RAM (streamed capture, one layer of activations alive): P*b + b*(2HTd + 2HT^2 + 7TF + 6Td + 3TV)/1 + 0.5 GB.
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
COEF = json.loads((HERE / "out" / "fit_coef.json").read_text())
# L, d, F, H, KV, hd, V, tied
ARCH = {"SmolLM2-135M": (30, 576, 1536, 9, 3, 64, 49152, True),
        "SmolLM2-360M": (32, 960, 2560, 15, 5, 64, 49152, True),
        "Llama-3.2-1B": (16, 2048, 8192, 32, 8, 64, 128256, True),
        "Llama-3.1-8B": (32, 4096, 14336, 32, 8, 128, 128256, False)}
LORA_R = 16   # paper recipe: r16 on q,k,v,o
# peak fp32 FLOP/s (no TF32), assumed efficiency  (vendor spec sheets; efficiency is an assumption)
COLAB = {"T4 16GB f32": (8.1e12, 0.4, 16), "L4 24GB f32": (30.3e12, 0.3, 24), "A100 40GB f32": (19.5e12, 0.4, 40),
         "A100 40GB f64": (9.7e12, 0.5, 40)}


def dims(a):
    L, d, F, H, KV, hd, V, tied = a
    body = L * (2 * d * H * hd + 2 * d * KV * hd + 3 * d * F)
    emb = V * d * (1 if tied else 2)
    return body, emb, body + emb


def lora_params(a, r=LORA_R):
    L, d, F, H, KV, hd, V, tied = a
    return L * r * ((d + H * hd) + 2 * (d + KV * hd) + (H * hd + d))


def run_bytes(a, T):
    L, d, F, H, KV, hd, V, tied = a
    return (4 * (L + 1) + 4 * L + 4 * L + 4 * L * H) * T \
        + 2 * L * H * 16 * T + 4 * L * H * 16 * T + 4 * L * H * T + 4 * L * T * 2 \
        + 4 * 4 * L * F + 4 * (L * H * 2 + L * 2 + (L + 1) * 2 + 2 * L) \
        + 0  # last line: small clamped arrays + attr sums


def pair_bytes(a, T):
    L, d, F, H, KV, hd, V, tied = a
    return 4 * ((L + 1) + L + L + L * H) * T + 4 * L * H * 4 + 4 * L * 3


def mem_gb(a, T, b, weights_b, streamed):
    L, d, F, H, KV, hd, V, tied = a
    _, _, P = dims(a)
    keep = 1 if streamed else L
    act = b * (2 * keep * H * T * d + 2 * keep * H * T * T + 7 * keep * T * F + 6 * keep * T * d + 3 * T * V)
    return (P * weights_b + act) / 1e9 + 0.5


def mac_time(a, T, mode, hf_mode, n_codes, n_ref):
    L, d, F, H, KV, hd, V, tied = a
    body, emb, P = dims(a)
    def f(m, tied_head):
        Pm = body + (V * d if tied_head else 0)
        c = COEF[m]
        return c[0] * Pm * T / 1e9 + c[1] * L + c[2]
    t_pass = f(mode, mode.startswith("f64-"))
    t_hf = f(hf_mode, True)
    return 1.10 * (2 * t_pass + (n_ref + n_codes) * t_hf)


def colab_time(a, T, peak, eff, n_codes, n_ref):
    L = a[0]
    body, _, _ = dims(a)
    t_pass = 2 * body * T / (peak * eff) + 1e-3 * L
    return 1.10 * (2 * t_pass + (n_ref + n_codes) * 0.8 * t_pass)


def main():
    print("== sizes ==")
    for name, a in ARCH.items():
        body, emb, P = dims(a)
        print(f"{name:13s} params {P / 1e9:6.3f} B | f64 {P * 8 / 1e9:6.1f} GB  f32 {P * 4 / 1e9:6.1f} GB  bf16 {P * 2 / 1e9:6.1f} GB | "
              f"LoRA r{LORA_R} qkvo {lora_params(a) / 1e6:5.2f} M params = {lora_params(a) * 4 / 1e6:5.1f} MB fp32")
    print("\n== export size (MB), run / pair, T = 140 and 306 (330 for 8B: +~25 template tokens, estimate) ==")
    for name, a in ARCH.items():
        for T in (140, 306):
            T2 = T + (25 if "Llama" in name else 0)
            print(f"{name:13s} T={T2:3d}  run {run_bytes(a, T2) / 1e6:6.1f} MB   pair {pair_bytes(a, T2) / 1e6:5.2f} MB   "
                  f"pair-of-runs-per-item {(2 * run_bytes(a, T2) + pair_bytes(a, T2)) / 1e6:6.1f} MB")
    print("\n== Mac M4 Pro 24 GB: time per (model, prompt) in s (n_codes=2) and peak RAM in GB ==")
    cases = [("f64-cpu", "hf-f64-cpu", 2, 8, 8), ("f32-cpu", "hf-f32-cpu", 1, 4, 4), ("f32-mps", "hf-f32-mps", 1, 4, 4)]
    for name, a in ARCH.items():
        for T in (140, 306):
            T2 = T + (25 if "Llama" in name else 0)
            parts = []
            for m, hm, n_ref, b, wb in cases:
                if m not in COEF:
                    continue
                t = mac_time(a, T2, m, hm, 2, n_ref)
                ram = mem_gb(a, T2, b, wb, False)
                parts.append(f"{m}: {t:5.2f}s {ram:5.1f}GB")
            ram_bf = mem_gb(a, T2, 4, 2, True)
            parts.append(f"w16c32+streamed: {mac_time(a, T2, 'f32-mps', 'hf-f32-mps', 2, 1) * 1.15:5.2f}s {ram_bf:5.1f}GB")
            print(f"{name:13s} T={T2:3d}  " + " | ".join(parts))
    print("\n== Colab Pro roofline ESTIMATES: time per (model, prompt) in s; memory need = weights + streamed activations ==")
    for name, a in ARCH.items():
        for T in (140, 306):
            T2 = T + (25 if "Llama" in name else 0)
            parts = []
            for g, (peak, eff, mem) in COLAB.items():
                f64 = "f64" in g
                need = mem_gb(a, T2, 8 if f64 else 4, 8 if f64 else (2 if "Llama-3.1" in name else 4), True)
                t = colab_time(a, T2, peak, eff, 2, 2 if f64 else 1)
                parts.append(f"{g}: {t:5.2f}s ({'fits' if need < mem * 0.9 else 'NO FIT'} {need:4.0f}GB)")
            print(f"{name:13s} T={T2:3d}  " + " | ".join(parts))


if __name__ == "__main__":
    main()
