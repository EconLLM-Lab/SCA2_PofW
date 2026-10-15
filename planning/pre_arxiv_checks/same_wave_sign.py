#!/usr/bin/env python3
"""Sign separation on the two-wave trust composites."""
import json
from pathlib import Path
import pandas as pd
from scipy.stats import spearmanr

OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/same_wave")
GPS = json.loads(Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json").read_text())
TRUST9 = ["Q57","Q58","Q59","Q60","Q61","Q62","Q63","Q64","Q73"]
scores = pd.read_csv(OUT / "adapter_item_scores_two_waves.csv")
comp = scores[scores.item.isin(TRUST9)].groupby("country").raw.mean()
z = pd.Series({c: float(GPS[c]["trust"]) for c in comp.index})
sign = (z >= 0).astype(int)
pos, neg = comp[sign == 1], comp[sign == 0]
c = d = 0
for pv in pos:
    for nv in neg:
        if pv > nv:
            c += 1
        elif pv < nv:
            d += 1
rb = (c - d) / (len(pos) * len(neg))
print("rho", round(float(spearmanr(comp, z).statistic), 4))
print("rank_biserial", round(rb, 4), "C", c, "D", d)
print("between", round(float(pos.mean() - neg.mean()), 4))
print("USA", round(float(comp["USA"]), 4), "z", round(float(z["USA"]), 4))
print("MEX", round(float(comp["MEX"]), 4), "z", round(float(z["MEX"]), 4))
