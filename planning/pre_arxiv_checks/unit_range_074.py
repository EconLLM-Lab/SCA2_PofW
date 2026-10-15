#!/usr/bin/env python3
"""0-1 trust composite on the current score file. No model calls."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
SCORES = REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv"
GPS = json.loads((REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json").read_text())
PANEL = ["ARG","BRA","CHN","DEU","EGY","GBR","GRC","IDN","IND","JPN","MEX","NGA","NLD","RUS","TUR","USA"]
TRUST = ["Q57","Q58","Q59","Q60","Q61","Q62","Q63","Q64","Q73"]
# theoretical ranges after the paper recode
RANGES = {
    "Q57": (0, 1),
    "Q58": (1, 4), "Q59": (1, 4), "Q60": (1, 4), "Q61": (1, 4),
    "Q62": (1, 4), "Q63": (1, 4), "Q64": (1, 4), "Q73": (1, 4),
}

def boot(a, b, seed=20260905, reps=2000):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    x, y = d["a"].to_numpy(), d["b"].to_numpy()
    rng = np.random.default_rng(seed)
    rhos = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(0, len(d), len(d))
        rhos[i] = spearmanr(x[idx], y[idx]).statistic
    point = float(spearmanr(x, y).statistic)
    return point, float(np.quantile(rhos, 0.025)), float(np.quantile(rhos, 0.975))

df = pd.read_csv(SCORES)
sub = df[(df.arm == "adapter") & (df.item.isin(TRUST)) & (df.country.isin(PANEL))].copy()
sub["unit"] = [(raw - RANGES[item][0]) / (RANGES[item][1] - RANGES[item][0]) for raw, item in zip(sub["raw"], sub["item"])]
z = pd.Series({c: float(GPS[c]["trust"]) for c in PANEL})
raw = sub.groupby("country")["raw"].mean().reindex(PANEL)
unit = sub.groupby("country")["unit"].mean().reindex(PANEL)
print("raw", boot(raw, z))
print("unit", boot(unit, z))
