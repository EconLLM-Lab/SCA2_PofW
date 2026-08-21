#!/usr/bin/env python3
"""03_sign_vector_profiles.py — verify GPS sign(z) profile classes for the 16 adapters.

Answers:
1. How many DISTINCT sign-vector profiles among the 16 adapter countries?
2. Does the adapter's per-dimension item-ordering r (corr_by_dim_model.csv)
   track the country's GPS dimension sign?  (altruism: r ~ -1 for negative signs?)

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/03_sign_vector_profiles.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
CORR = REPO / "analysis" / "phase2" / "outputs" / "corr_by_dim_model.csv"
OUT = REPO / "analysis" / "phase2" / "outputs"

ADAPTER_COUNTRIES = ["CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS",
                     "IND", "IDN", "NGA", "EGY", "TUR", "NLD", "BRA", "GRC"]
DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]


def main() -> None:
    gps = pd.read_stata(GPS_DTA)
    gps = gps.set_index("isocode")
    assert set(ADAPTER_COUNTRIES) <= set(gps.index), "missing countries in GPS file"

    sub = gps.loc[ADAPTER_COUNTRIES, DIMS]
    signs = np.sign(sub)

    # 1) distinct profiles within the 16
    sig_str = signs.astype(int).astype(str).agg("".join, axis=1)
    classes = sig_str.groupby(sig_str).apply(lambda s: ",".join(sorted(s.index))).to_dict()
    print("=== sign-vector profiles among the 16 adapter countries ===")
    for sig, members in classes.items():
        print(f"  {sig}  ->  {members}")
    print(f"\n16 adapters -> {len(classes)} distinct profiles")
    print("(Ksennia reported 6 unique among base-8; CO2_RUN.md implied 13 among 16)")

    # duplicate pairs (label-identical) within the 16
    print("\n=== label-identical pairs within the 16 ===")
    seen = []
    for c1 in ADAPTER_COUNTRIES:
        for c2 in ADAPTER_COUNTRIES:
            if c1 < c2 and (signs.loc[c1] == signs.loc[c2]).all():
                seen.append(f"{c1}=={c2}")
    print(", ".join(seen) if seen else "none")

    # save the sign table for downstream analyses
    out = signs.astype(int)
    out.to_csv(OUT / "gps_sign_vectors_16.csv")

    # 2) adapter r vs GPS sign per dimension (matched cells)
    corr = pd.read_csv(CORR)
    melted = signs.reset_index().melt(id_vars="isocode", var_name="dim_dta",
                                      value_name="gps_sign")
    merged = corr.merge(melted, left_on=["eval_country", "gps_dimension"],
                        right_on=["isocode", "dim_dta"], how="left")
    merged = merged.drop(columns=["isocode", "dim_dta"])
    merged = merged.rename(columns={"gps_sign": "gps_z_sign"})
    m = merged[merged["gps_z_sign"].notna()].copy()
    m["r_sign"] = np.sign(m["r_mean"])
    m["r_aligns"] = m["r_sign"] == m["gps_z_sign"]

    print("\n=== adapter item-ordering r vs GPS sign (matched cells) ===")
    tab = (m.groupby("gps_dimension")
            .agg(n=("r_mean", "size"),
                 frac_r_positive=("r_mean", lambda s: (s > 0).mean()),
                 mean_r=("r_mean", "mean"),
                 frac_r_aligns_gps=("r_aligns", "mean"))
            .round(3))
    print(tab.to_string())
    m.to_csv(OUT / "corr_vs_gps_sign.csv", index=False)

    # per-dimension detail for altruism (the striking pattern)
    print("\n=== altruism detail (r vs GPS sign) ===")
    a = m[m["gps_dimension"] == "altruism"].sort_values("r_mean")
    print(a[["model", "eval_country", "r_mean", "gps_z_sign"]].to_string(index=False))


if __name__ == "__main__":
    main()
