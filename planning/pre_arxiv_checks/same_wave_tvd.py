#!/usr/bin/env python3
"""Two-wave TVD and paired adapter-minus-persona trust difference."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
KSENIA = REPO / "data/phase2/raw/wvs/ksenias_base8"
CO2 = REPO / "data/phase2/raw/wvs/co2_8"
PERSONA = REPO / "data/phase2/raw/wvs/persona_baseline"
FROZEN = REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv"
GPS = json.loads((REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json").read_text())
WAVE1 = ["CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS"]
WAVE2 = ["IND", "IDN", "NGA", "EGY", "TUR", "NLD", "BRA", "GRC"]
PANEL = WAVE1 + WAVE2
STRICT = [
    "Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73",
    "Q43", "Q50", "Q106", "Q107", "Q109", "Q178", "Q81",
    "Q176", "Q177", "Q179", "Q195", "Q99", "Q101", "Q103",
]
TRUST9 = STRICT[:9]


def metrics(cc: str) -> pd.DataFrame:
    root = KSENIA if cc in WAVE1 else CO2
    path = root / f"survey_question_metrics_{cc}_adapter_on_{cc}.csv"
    df = pd.read_csv(path, usecols=["question_id", "tv_distance", "response_type"])
    df = df[df.question_id.isin(STRICT)]
    df["country"] = cc
    return df


def boot_diff(adapter, persona, z, seed=20260905, reps=2000):
    d = pd.concat([
        adapter.rename("a"), persona.rename("p"), z.rename("z")
    ], axis=1).dropna()
    x = d.to_numpy()
    rng = np.random.default_rng(seed)
    diffs = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(0, len(d), len(d))
        s = x[idx]
        diffs[i] = spearmanr(s[:, 0], s[:, 2]).statistic - spearmanr(s[:, 1], s[:, 2]).statistic
    point = spearmanr(d["a"], d["z"]).statistic - spearmanr(d["p"], d["z"]).statistic
    return float(point), float(np.nanquantile(diffs, 0.025)), float(np.nanquantile(diffs, 0.975))


def main() -> None:
    parts = [metrics(c) for c in PANEL]
    m = pd.concat(parts, ignore_index=True)
    print("adapter_cells", len(m), "expected", 16 * 23)
    print("adapter_mean_tvd", round(float(m.tv_distance.mean()), 4))
    # persona metrics if present
    pfiles = list(PERSONA.glob("survey_question_metrics*.csv"))
    print("persona_metric_files", len(pfiles))
    frozen = pd.read_csv(FROZEN)
    for arm in ("adapter", "persona"):
        sub = frozen[(frozen.arm == arm) & (frozen.item.isin(STRICT)) & (frozen.country.isin(PANEL))]
        print(arm, "frozen_tvd_cells", len(sub), "mean", round(float(sub.tvd.mean()), 4))

    scores = pd.read_csv("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/same_wave/adapter_item_scores_two_waves.csv")
    adapter = scores[scores.item.isin(TRUST9)].groupby("country").raw.mean().reindex(PANEL)
    persona = frozen[(frozen.arm == "persona") & (frozen.item.isin(TRUST9))]
    persona = persona.groupby("country").raw.mean().reindex(PANEL)
    z = pd.Series({c: float(GPS[c]["trust"]) for c in PANEL})
    point, lo, hi = boot_diff(adapter, persona, z)
    print("paired_diff", round(point, 4), round(lo, 4), round(hi, 4))
    print("adapter_rho", round(float(spearmanr(adapter, z).statistic), 4))
    print("persona_rho", round(float(spearmanr(persona, z).statistic), 4))


if __name__ == "__main__":
    main()
