#!/usr/bin/env python3
"""Independent check of sign_only_results.csv against frozen inputs.

Does not write results. Prints mismatches and stops nonzero if any check fails.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/sign_only")
SCORES = REPO / "analysis" / "phase2" / "outputs" / "paper_a" / "country_item_scores.csv"
GPS_JSON = REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_all" / "gps_z_vectors.json"
PANEL16 = [
    "ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
    "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA",
]
TRUST9 = ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]

tab = pd.read_csv(OUT / "sign_only_results.csv")
countries = tab[tab.record_type == "country"].set_index("country").reindex(PANEL16)
stats = tab[tab.record_type == "statistic"].set_index("statistic")

items = pd.read_csv(SCORES)
sub = items[(items.arm == "adapter") & (items.item.isin(TRUST9)) & (items.country.isin(PANEL16))]
sub = sub[np.isfinite(sub["raw"])]
composite = sub.groupby("country")["raw"].mean().reindex(PANEL16)
z = pd.Series({c: float(json.loads(GPS_JSON.read_text())[c]["trust"]) for c in PANEL16})

fails = []

def check(name, ok, detail):
    print(f"{'OK' if ok else 'FAIL'} {name}: {detail}")
    if not ok:
        fails.append(name)

check(
    "composite",
    np.allclose(composite.to_numpy(), countries.adapter_composite.to_numpy()),
    f"max abs diff {(composite - countries.adapter_composite).abs().max()}",
)
check(
    "z",
    np.allclose(z.to_numpy(), countries.z_trust.to_numpy()),
    f"max abs diff {(z - countries.z_trust).abs().max()}",
)
rho = float(spearmanr(composite, z).statistic)
check("sanity", rho == float(stats.loc["sanity_adapter_gps_spearman", "estimate"]), f"{rho!r}")
sign = (z >= 0).astype(float)
rho_sz = float(spearmanr(sign, z).statistic)
check("sign_vs_z", abs(rho_sz - float(stats.loc["sign_vs_z_spearman", "estimate"])) < 1e-15, f"{rho_sz!r}")
pos = composite[z > 0]
neg = composite[z < 0]
diff = float(pos.mean() - neg.mean())
check("diff", abs(diff - float(stats.loc["between_sign_adapter_diff", "estimate"])) < 1e-12, f"{diff!r}")
y1 = pos.to_numpy()
y0 = neg.to_numpy()
delta = y1[:, None] - y0[None, :]
c = int(np.sum(delta > 0))
d = int(np.sum(delta < 0))
rb = (c - d) / (len(y1) * len(y0))
check("rank_biserial", abs(rb - float(stats.loc["rank_biserial_adapter_vs_sign", "estimate"])) < 1e-15, f"{rb!r} C={c} D={d}")
inversions = [
    f"{a}({composite[a]:.6f}) < {b}({composite[b]:.6f})"
    for a in pos.index for b in neg.index if composite[a] < composite[b]
]
print("inversions", inversions)
neg_rho = float(spearmanr(composite[z < 0], z[z < 0]).statistic)
check("within_neg", abs(neg_rho - float(stats.loc["within_negative_spearman", "estimate"])) < 1e-15, f"{neg_rho!r}")
check("n_pos", int((z > 0).sum()) == 7, int((z > 0).sum()))
check("n_neg", int((z < 0).sum()) == 9, int((z < 0).sum()))
check("n_zero", int((z == 0).sum()) == 0, int((z == 0).sum()))
check("within_pos_gate", int((z >= 0).sum()) < 8, int((z >= 0).sum()))
if fails:
    raise SystemExit("FAILED " + ",".join(fails))
print("ALL CHECKS PASSED")
