"""Fit the runtime formula to out/scale.jsonl and print predicted vs measured, then the extrapolations.

    python3 plans/scripts/fit_time.py        (stdlib + numpy; run with `uv run python` for numpy)

Model per mode:  t = a * P * T / 1e9  +  b * L  +  c      (seconds)
    P  matmul parameters per token: layers only for our own pass in f32 / w16c32 (it reads the last logits row
       only); layers + V*d for LC.run (f64, all-T logits) and for stock HF (all-T logits).
    L  number of layers (per-layer launch overhead);  c  fixed overhead.
"""

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
ARCH = {  # layers, d, ffn, heads, kv, head_dim, vocab
    "135m": (30, 576, 1536, 9, 3, 64, 49152), "360m": (32, 960, 2560, 15, 5, 64, 49152),
    "1b": (16, 2048, 8192, 32, 8, 64, 128256), "8b": (32, 4096, 14336, 32, 8, 128, 128256),
    "8bv": (32, 4096, 14336, 32, 8, 128, 32000)}


def sizes(name):
    base, _, nl = name.partition("-L")
    L, d, f, h, kv, hd, V = ARCH[base]
    L = int(nl) if nl else L
    per_layer = 2 * d * h * hd + 2 * d * kv * hd + 3 * d * f
    return L, per_layer * L, V * d


def feats(name, mode, T):
    L, body, head = sizes(name)
    P = body + (head if (mode.startswith("hf-") or mode.startswith("f64-")) else 0)
    return [P * T / 1e9, L, 1.0]


def main():
    rows = [json.loads(line) for line in (HERE / "out" / "scale.jsonl").read_text().splitlines() if line]
    rows = [r for r in rows if "mode" in r]
    coef = {}
    for mode in sorted({r["mode"] for r in rows}):
        g = [r for r in rows if r["mode"] == mode]
        X = np.array([feats(r["model"], mode, r["T"]) for r in g])
        y = np.array([r["seconds"] for r in g])
        n_par = 3 if len(g) >= 6 else 2
        # relative-error weighting so that small models count as much as large ones
        w = 1 / y
        A = (X[:, :n_par] * w[:, None])
        sol, *_ = np.linalg.lstsq(A, y * w, rcond=None)
        sol = np.clip(sol, 0, None)
        full = np.zeros(3); full[:n_par] = sol
        coef[mode] = full
        pred = X @ full
        err = np.abs(pred / y - 1)
        print(f"{mode:12s} a={full[0]:.5f} s/(Gparam*tok)  b={full[1] * 1e3:.2f} ms/layer  c={full[2] * 1e3:.1f} ms  "
              f"n={len(g)}  max rel err {err.max() * 100:.0f}%  median {np.median(err) * 100:.0f}%")
        for r, p in zip(g, pred):
            print(f"      {r['model']:7s} T={r['T']:3d} measured {r['seconds']:.3f}  fit {p:.3f}")
    json.dump({k: list(v) for k, v in coef.items()}, open(HERE / "out" / "fit_coef.json", "w"), indent=1)

    print("\nExtrapolation (ESTIMATES from the fits above; the 1B f64 fit has one point per size):")
    for name, T in [("135m", 136), ("135m", 306), ("360m", 140), ("360m", 306), ("1b", 140), ("1b", 306), ("8b", 170), ("8b", 330)]:
        out = [f"{name:5s} T={T}"]
        for mode in ("f64-cpu", "f32-cpu", "f32-mps", "w16c32-mps", "hf-f64-cpu", "hf-f32-cpu", "hf-f32-mps"):
            if mode in coef:
                out.append(f"{mode}={np.array(feats(name, mode, T)) @ coef[mode]:.2f}s")
        print("  " + "  ".join(out))


if __name__ == "__main__":
    main()
