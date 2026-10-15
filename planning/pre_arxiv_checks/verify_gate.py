#!/usr/bin/env python3
"""Independent spot-check of the pre-arXiv subagent reports. Does not edit the repo."""
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


def spearman(a, b):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    return float(spearmanr(d["a"], d["b"]).statistic), int(len(d))


def main() -> None:
    items = pd.read_csv(SCORES)
    z = json.loads(GPS.read_text())
    z16 = pd.Series({c: float(z[c]["trust"]) for c in PANEL})
    sub = items[(items.arm == "adapter") & (items.item.isin(TRUST9)) & (items.country.isin(PANEL))]
    sub = sub[np.isfinite(sub["raw"])]
    adapter = sub.groupby("country")["raw"].mean().reindex(PANEL)
    rho, n = spearman(adapter, z16)
    sign = (z16 >= 0).astype(int)
    rho_sz, _ = spearman(sign, z16)
    pos = adapter[sign == 1]
    neg = adapter[sign == 0]
    # rank-biserial
    c = d = 0
    for pv in pos:
        for nv in neg:
            if pv > nv:
                c += 1
            elif pv < nv:
                d += 1
    rb = (c - d) / (len(pos) * len(neg))
    # within negative
    neg_c = [cc for cc in PANEL if z16[cc] < 0]
    rho_wn, n_wn = spearman(adapter.reindex(neg_c), z16.reindex(neg_c))
    print("sanity_adapter_gps", round(rho, 10), "n", n)
    print("sign_vs_z", round(rho_sz, 10))
    print("n_pos", int((z16 > 0).sum()), "n_neg", int((z16 < 0).sum()), "n_zero", int((z16 == 0).sum()))
    print("between_sign_diff", float(pos.mean() - neg.mean()))
    print("rank_biserial", rb, "C", c, "D", d)
    print("within_neg", rho_wn, "n", n_wn)
    print("pos_countries", " ".join(cc for cc in PANEL if z16[cc] >= 0))
    print("neg_countries", " ".join(cc for cc in PANEL if z16[cc] < 0))
    # USA Q57 logprob stitch
    canon = REPO / "DPO_eval_WVS/eval_results_wvs_wave7/model_option_probabilities_USA_adapter_on_USA.csv"
    later = REPO / "data/phase2/raw/wvs/ksenias_base8"
    print("canon_exists", canon.exists())
    print("later_dir", later.exists(), "files", len(list(later.glob("*.csv"))) if later.exists() else 0)
    if canon.exists():
        cdf = pd.read_csv(canon)
        cols = list(cdf.columns)
        print("canon_cols", cols[:12])
        q = cdf[cdf["question_id"].astype(str).str.contains("Q57") | cdf.get("item", pd.Series(dtype=str)).astype(str).eq("Q57")] if "question_id" in cdf.columns or "item" in cdf.columns else cdf.head(0)
        # try common id columns
        idcol = next((c for c in ("item", "question_id", "q_id", "variable", "wvs_item") if c in cdf.columns), None)
        print("idcol", idcol)
        if idcol:
            hit = cdf[cdf[idcol].astype(str).str.contains("Q57")]
            print("q57_rows", len(hit))
            lp = next((c for c in ("option_logprob", "logprob", "option_log_prob") if c in cdf.columns), None)
            code = next((c for c in ("option_code", "code", "response_code") if c in cdf.columns), None)
            print("lp", lp, "code", code)
            if lp and code and len(hit):
                one = hit[hit[code].astype(str).str.strip().isin(["1", "1.0"])]
                print("canon_q57_code1", one[lp].tolist()[:5])


if __name__ == "__main__":
    main()
