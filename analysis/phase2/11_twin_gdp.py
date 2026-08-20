#!/usr/bin/env python3
"""11_twin_gdp.py — do sign-twins stay culturally close after controlling GDP?

Eval-1 follow-up: the 76-country sign(z) bank has 22 multi-country classes, and
twin pairs were closer on human WVS CF_ST (ratio 0.696, perm p=0.0005). This
script asks whether that residual proximity is a development artifact: sign
classes are also closer in log GDP pc, and GDP gap predicts CF_ST.

Answer (verified 2026-08-19): YES, mostly a development artifact. Partial
corr(CF_ST, twin | log GDP gap) = -0.090 (raw twin CF_ST 0.044 vs 0.063);
within every GDP-gap tercile the twin advantage survives in direction but
shrinks. Sign(z) classes are a thin slice of preference space whose cultural
proximity is largely explained by shared development level.

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/11_twin_gdp.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
WDI_LOCAL = REPO / "data" / "phase2" / "aux" / "wdi.csv"
WDI_CACHE = pathlib.Path("/Users/bonorinoa/Hermes/Projects/cvprofiles/data/h5_trust_aux/wdi.csv")
WDI = WDI_LOCAL if WDI_LOCAL.exists() else WDI_CACHE

DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]


def main() -> None:
    gps = pd.read_stata(GPS_DTA).set_index("isocode")[DIMS]
    key = np.sign(gps).astype(int).astype(str).agg("".join, axis=1)
    wdi = pd.read_csv(WDI)
    gdp = np.log(wdi.groupby("iso3")["gdp_pc_ppp"].mean()).rename("log_gdp_pc")
    cd = pd.read_csv(OUT / "cd_country_country.csv", index_col=0)

    ccs = [c for c in cd.index if c in key.index and c in gdp.index]
    rows = []
    for i, a in enumerate(ccs):
        for b in ccs[i + 1:]:
            rows.append({
                "a": a, "b": b,
                "same_sign_class": bool(key[a] == key[b]),
                "cfst": float(cd.loc[a, b]),
                "log_gdp_gap": abs(float(gdp[a] - gdp[b])),
            })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "twin_gdp_pairs.csv", index=False)

    tw = df[df.same_sign_class]["cfst"]
    nt = df[~df.same_sign_class]["cfst"]
    gdp_tw = df[df.same_sign_class]["log_gdp_gap"]
    gdp_nt = df[~df.same_sign_class]["log_gdp_gap"]
    print(f"pairs: {len(df)} | twin pairs: {int(df.same_sign_class.sum())}")
    print(f"raw CF_ST: twins {tw.mean():.4f} vs non-twins {nt.mean():.4f} "
          f"(ratio {tw.mean() / nt.mean():.3f})")
    print(f"log GDP gap: twins {gdp_tw.mean():.3f} vs non-twins {gdp_nt.mean():.3f}")

    r = df[["cfst", "same_sign_class", "log_gdp_gap"]].dropna()
    rx, ry, rz = r["cfst"].rank(), r["same_sign_class"].astype(int), r["log_gdp_gap"].rank()
    Z = np.column_stack([np.ones(len(rz)), rz])
    bx = np.linalg.lstsq(Z, rx, rcond=None)[0]
    by = np.linalg.lstsq(Z, ry, rcond=None)[0]
    ex, ey = rx - Z @ bx, ry - Z @ by
    part = float(np.corrcoef(ex, ey)[0, 1])
    g = spearmanr(r["cfst"], r["log_gdp_gap"], nan_policy="omit").statistic
    print(f"partial corr(CF_ST, twin | log GDP gap): {part:+.3f}")
    print(f"spearman(CF_ST, |ΔlogGDP|): {g:+.3f}")

    df["gap_terc"] = pd.qcut(df["log_gdp_gap"], 3, labels=["low", "mid", "high"])
    print("by GDP-gap tercile (twin vs non-twin CF_ST):")
    for t, gg in df.groupby("gap_terc"):
        twm = gg[gg.same_sign_class]["cfst"].mean() if gg.same_sign_class.sum() else np.nan
        ntm = gg[~gg.same_sign_class]["cfst"].mean() if (~gg.same_sign_class).sum() else np.nan
        print(f"  {t}: twins {twm:.4f} vs non-twins {ntm:.4f} "
              f"(n_tw={int(gg.same_sign_class.sum())})")

    print("\nwrote twin_gdp_pairs.csv")


if __name__ == "__main__":
    main()
