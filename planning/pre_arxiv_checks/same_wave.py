#!/usr/bin/env python3
"""Same-wave trust Spearman versus the precedence stitch. No model calls."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
GPS = json.loads(
    (REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json").read_text()
)
FROZEN = REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv"
CANON = REPO / "DPO_eval_WVS/eval_results_wvs_wave7"
KSENIA = REPO / "data/phase2/raw/wvs/ksenias_base8"
CO2 = REPO / "data/phase2/raw/wvs/co2_8"
TRUST9 = ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]
INVERT = {"Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"}
WAVE1 = ["CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS"]
WAVE2 = ["IND", "IDN", "NGA", "EGY", "TUR", "NLD", "BRA", "GRC"]
PANEL = WAVE1 + WAVE2


def recode(v, item):
    s = float(v)
    if item in INVERT:
        return 5.0 - s
    if item == "Q57":
        return 1.0 if s == 1.0 else 0.0
    return s


def composite(path: Path) -> float:
    df = pd.read_csv(path, usecols=["question_id", "option_value", "model_prob"])
    vals = []
    for q in TRUST9:
        d = df[df.question_id == q]
        if d.empty:
            return np.nan
        pm = d.model_prob.to_numpy(float)
        if pm.sum() <= 0:
            return np.nan
        pm = pm / pm.sum()
        rec = np.array([recode(v, q) for v in d.option_value.to_numpy(float)])
        vals.append(float((rec * pm).sum()))
    return float(np.mean(vals))


def rho(scores: dict[str, float]) -> float:
    a = pd.Series(scores)
    z = pd.Series({c: float(GPS[c]["trust"]) for c in a.index})
    return float(spearmanr(a, z).statistic)


def main() -> None:
    stitch = {}
    same_wave = {}
    for c in WAVE1:
        if c in ("USA", "MEX"):
            stitch[c] = composite(CANON / f"model_option_probabilities_{c}_adapter_on_{c}.csv")
        else:
            stitch[c] = composite(KSENIA / f"model_option_probabilities_{c}_adapter_on_{c}.csv")
        same_wave[c] = composite(KSENIA / f"model_option_probabilities_{c}_adapter_on_{c}.csv")
    for c in WAVE2:
        p = CO2 / f"model_option_probabilities_{c}_adapter_on_{c}.csv"
        stitch[c] = composite(p)
        same_wave[c] = composite(p)

    frozen = pd.read_csv(FROZEN)
    fr = frozen[(frozen.arm == "adapter") & (frozen.item.isin(TRUST9))]
    frozen_comp = fr.groupby("country")["raw"].mean().to_dict()

    print("stitched_rho", round(rho(stitch), 6))
    print("same_wave_rho", round(rho(same_wave), 6))
    print("frozen_rho", round(rho({c: frozen_comp[c] for c in PANEL}), 6))
    print("max_abs_stitch_vs_frozen", max(abs(stitch[c] - frozen_comp[c]) for c in PANEL))
    for c in ("USA", "MEX"):
        print(
            c,
            "canonical", round(stitch[c], 6),
            "same_wave", round(same_wave[c], 6),
            "delta", round(same_wave[c] - stitch[c], 6),
            "z", round(float(GPS[c]["trust"]), 4),
        )
    moved = [c for c in PANEL if abs(same_wave[c] - stitch[c]) > 1e-8]
    print("countries_that_change", moved)


if __name__ == "__main__":
    main()
