#!/usr/bin/env python3
"""Recompute trust adapter-GPS on the 0-1 scale. Theoretical ranges, not sample ranges."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
SCORES = REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv"
GPS = REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"
PANEL = [
    "ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
    "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA",
]
TRUST9 = ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]
# theoretical post-recode ranges from the instrument codes in the unit-range report
RANGES = {"Q57": (0.0, 1.0)}
for q in ["Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]:
    RANGES[q] = (1.0, 4.0)


def spearman(a, b):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    return float(spearmanr(d["a"], d["b"]).statistic)


def boot(a, b, seed=20260905, reps=2000):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    x = d["a"].to_numpy()
    y = d["b"].to_numpy()
    rng = np.random.default_rng(seed)
    rhos = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(0, len(d), len(d))
        rhos[i] = spearmanr(x[idx], y[idx]).statistic
    point = float(spearmanr(x, y).statistic)
    return point, float(np.quantile(rhos, 0.025)), float(np.quantile(rhos, 0.975))


def main() -> None:
    items = pd.read_csv(SCORES)
    z = json.loads(GPS.read_text())
    z16 = pd.Series({c: float(z[c]["trust"]) for c in PANEL})
    sub = items[(items.arm == "adapter") & (items.item.isin(TRUST9)) & (items.country.isin(PANEL))].copy()
    sub = sub[np.isfinite(sub["raw"])]
    raw = sub.groupby("country")["raw"].mean().reindex(PANEL)
    sub["unit"] = sub.apply(lambda r: (r["raw"] - RANGES[r["item"]][0]) / (RANGES[r["item"]][1] - RANGES[r["item"]][0]), axis=1)
    unit = sub.groupby("country")["unit"].mean().reindex(PANEL)
    rp, rlo, rhi = boot(raw, z16)
    up, ulo, uhi = boot(unit, z16)
    print(f"raw {rp:.6f} [{rlo:.4f}, {rhi:.4f}]")
    print(f"unit {up:.6f} [{ulo:.4f}, {uhi:.4f}]")
    print("rounded_move", round(up, 2) - round(rp, 2))


if __name__ == "__main__":
    main()
