#!/usr/bin/env python3
"""Trust Spearman by arm on the frozen score file."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
items = pd.read_csv(REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv")
z = json.loads((REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json").read_text())
PANEL = ["ARG","BRA","CHN","DEU","EGY","GBR","GRC","IDN","IND","JPN","MEX","NGA","NLD","RUS","TUR","USA"]
TRUST9 = ["Q57","Q58","Q59","Q60","Q61","Q62","Q63","Q64","Q73"]
z16 = pd.Series({c: float(z[c]["trust"]) for c in PANEL})
print("arms", sorted(items.arm.unique()))
for arm in sorted(items.arm.unique()):
    sub = items[(items.arm == arm) & (items.item.isin(TRUST9)) & (items.country.isin(PANEL))]
    sub = sub[np.isfinite(sub["raw"])]
    comp = sub.groupby("country")["raw"].mean().reindex(PANEL)
    d = pd.concat([comp.rename("a"), z16.rename("b")], axis=1).dropna()
    rho = float(spearmanr(d["a"], d["b"]).statistic) if len(d) >= 8 else float("nan")
    print(f"{arm:20} n_countries={comp.notna().sum():2} n_rows={len(sub):4} rho={rho:.4f}")
