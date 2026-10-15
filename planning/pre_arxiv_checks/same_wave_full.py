#!/usr/bin/env python3
"""Headline associations from the two wave files only. USA/MEX from ksenias_base8."""
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
KSENIA = REPO / "data/phase2/raw/wvs/ksenias_base8"
CO2 = REPO / "data/phase2/raw/wvs/co2_8"
OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/same_wave")
WAVE1 = ["CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS"]
WAVE2 = ["IND", "IDN", "NGA", "EGY", "TUR", "NLD", "BRA", "GRC"]
PANEL = WAVE1 + WAVE2
ITEMS = {
    "trust": ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"],
    "patience": ["Q43", "Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q99", "Q101", "Q103"],
}
INVERT_1_4 = {
    "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71",
    "Q58", "Q60", "Q73", "Q81",
}
INVERT_10 = {"Q177", "Q179"}
BINARY = {"Q57"}


def recode(v, item):
    s = float(v)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in INVERT_10:
        return 11.0 - s
    if item in BINARY:
        return 1.0 if s == 1.0 else 0.0
    return s


def load_country(cc: str) -> pd.DataFrame:
    root = KSENIA if cc in WAVE1 else CO2
    path = root / f"model_option_probabilities_{cc}_adapter_on_{cc}.csv"
    df = pd.read_csv(path, usecols=["question_id", "option_value", "model_prob"])
    rows = []
    for q, g in df.groupby("question_id"):
        pm = g.model_prob.to_numpy(float)
        if pm.sum() <= 0:
            continue
        pm = pm / pm.sum()
        rec = np.array([recode(v, q) for v in g.option_value.to_numpy(float)])
        rows.append({"country": cc, "item": q, "raw": float((rec * pm).sum())})
    return pd.DataFrame(rows)


def spearman(a, b):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(d) < 8 or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return float("nan")
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
    return point, float(np.nanquantile(rhos, 0.025)), float(np.nanquantile(rhos, 0.975))


def composite(item_scores, items, countries):
    sub = item_scores[item_scores.item.isin(items) & item_scores.country.isin(countries)]
    return sub.groupby("country")["raw"].mean().reindex(countries)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parts = [load_country(c) for c in PANEL]
    scores = pd.concat(parts, ignore_index=True)
    scores.to_csv(OUT / "adapter_item_scores_two_waves.csv", index=False)
    frozen = pd.read_csv(FROZEN)
    fr = frozen[(frozen.arm == "adapter") & (frozen.country.isin(PANEL))]
    merged = scores.merge(fr[["country", "item", "raw"]], on=["country", "item"], suffixes=("_wave", "_frozen"))
    delta = (merged.raw_wave - merged.raw_frozen).abs()
    changed = merged.loc[delta > 1e-8, "country"].unique().tolist()
    print("countries_whose_adapter_scores_change", sorted(changed))
    print("max_abs_delta", float(delta.max()))

    z = {dim: pd.Series({c: float(GPS[c][dim]) for c in PANEL}) for dim in ITEMS}
    human = frozen[(frozen.arm == "human") & (frozen.country.isin(PANEL))]
    rows = []
    for dim, items in ITEMS.items():
        if dim == "patience":
            for q in items:
                a = composite(scores, [q], PANEL)
                h = composite(human.rename(columns={"raw": "raw"}), [q], PANEL)
                # human composite uses frozen raw
                h = human[human.item == q].set_index("country")["raw"].reindex(PANEL)
                point, lo, hi = boot(a, z["patience"])
                rows.append({
                    "dim": q, "pair": "adapter-gps", "rho": point, "lo": lo, "hi": hi,
                    "frozen_rho": spearman(
                        fr[fr.item == q].set_index("country")["raw"].reindex(PANEL),
                        z["patience"],
                    ),
                })
                rows.append({
                    "dim": q, "pair": "adapter-human",
                    "rho": spearman(a, h), "lo": np.nan, "hi": np.nan,
                    "frozen_rho": spearman(
                        fr[fr.item == q].set_index("country")["raw"].reindex(PANEL), h
                    ),
                })
            continue
        a = composite(scores, items, PANEL)
        h = human[human.item.isin(items)].groupby("country")["raw"].mean().reindex(PANEL)
        point, lo, hi = boot(a, z[dim])
        rows.append({
            "dim": dim, "pair": "adapter-gps", "rho": point, "lo": lo, "hi": hi,
            "frozen_rho": spearman(
                fr[fr.item.isin(items)].groupby("country")["raw"].mean().reindex(PANEL),
                z[dim],
            ),
        })
        rows.append({
            "dim": dim, "pair": "adapter-human",
            "rho": spearman(a, h), "lo": np.nan, "hi": np.nan,
            "frozen_rho": spearman(
                fr[fr.item.isin(items)].groupby("country")["raw"].mean().reindex(PANEL), h
            ),
        })
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "same_wave_associations.csv", index=False)
    print(tab.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
