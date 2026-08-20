#!/usr/bin/env python3
"""10_development_restrictions.py — nomological test: do adapters satisfy the
economic-development restrictions that GPS preferences satisfy in humans?

Logic (from the audit, 2026-08-19): if the adapters carry GPS preferences
(weights-level, no country in prompt, no WVS in training), then their country
rankings on trust/patience should reproduce the well-documented development
gradient — trust and patience rise with log GDP per capita (Falk et al. 2018;
cvprofiles H5 network: corr(trust, log GDP pc | education) >= 0).

Layers compared on the SAME criterion (log GDP pc, WDI NY.GDP.PCAP.PP.KD,
2015-2019 mean):
  - GPS country z (the anchor itself; 76 countries)
  - Human WVS composites (42 countries, survey-weighted, same recodes as 06)
  - Adapter WVS composites (16 countries, matched cells, same recodes)
Education control: Q275 (WVS ISCED) weighted mean per country — the cvprofiles
convention (q275_mean). All data local: WDI cache from the cvprofiles lane,
parquets in data/wvs_eval_full, unified eval in analysis/phase2/outputs.

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/10_development_restrictions.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
WVS_DIR = REPO / "data" / "wvs_eval_full"
WDI_LOCAL = REPO / "data" / "phase2" / "aux" / "wdi.csv"
WDI_CACHE = pathlib.Path("/Users/bonorinoa/Hermes/Projects/cvprofiles/data/h5_trust_aux/wdi.csv")
WDI_CSV = WDI_LOCAL if WDI_LOCAL.exists() else WDI_CACHE

DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]
DIM_ITEMS = {
    "trust": ["Q57", "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70",
              "Q71", "Q58", "Q60", "Q73"],
    "patience": ["Q13", "Q14", "Q43", "Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q12", "Q174", "Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q101", "Q99", "Q103"],
}
# polarity recodes identical to 06_construct_bridge.py (verified 2026-08-19)
INVERT_1_4 = {"Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71",
              "Q58", "Q60", "Q73", "Q81"}
INVERT_10 = {"Q177", "Q179"}
BINARY_TRUST = {"Q57", "Q12", "Q13", "Q14", "Q174"}
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}


def recode(raw: pd.Series, item: str) -> pd.Series:
    s = raw.astype(float)
    if item in INVERT_1_4:
        s = 5.0 - s
    elif item in INVERT_10:
        s = 11.0 - s
    elif item in BINARY_TRUST:
        s = (s == 1.0).astype(float)
    return s


def load_wdi_loggdp() -> pd.Series:
    wdi = pd.read_csv(WDI_CSV)
    g = wdi.groupby("iso3")["gdp_pc_ppp"].mean()
    return np.log(g)  # 2015-2019 mean


def load_gps_z() -> pd.DataFrame:
    g = pd.read_stata(GPS_DTA).set_index("isocode")
    return g[DIMS]


def human_layer() -> pd.DataFrame:
    """42 countries: survey-weighted composite means (recoded) + Q275 education."""
    gps = load_gps_z()
    items = sorted({q for vals in DIM_ITEMS.values() for q in vals})
    rows = []
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        if cc not in gps.index:
            continue
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + items + ["Q275"])
        w = df["W_WEIGHT"].fillna(0)
        for dim, qs in DIM_ITEMS.items():
            vals = []
            for it in qs:
                if it not in df.columns:
                    continue
                v = recode(df[it], it)
                m = (v >= 0) & (w > 0)
                if m.sum() < 50:
                    continue
                vals.append((v[m] * w[m]).sum() / w[m].sum())
            if vals:
                rows.append({"country": cc, "gps_dimension": dim,
                             "composite": float(np.mean(vals))})
        # education: weighted mean of Q275 (ISCED)
        edu = df["Q275"]
        m = (edu >= 0) & (w > 0)
        if m.sum() > 0:
            rows.append({"country": cc, "gps_dimension": "education",
                         "composite": float((edu[m] * w[m]).sum() / w[m].sum())})
    df = pd.DataFrame(rows)
    wide = df.pivot_table(index="country", columns="gps_dimension",
                          values="composite").reset_index()
    return wide


def adapter_layer() -> pd.DataFrame:
    """16 adapters: matched-cell composite means (recoded model_mean)."""
    wvs = pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
    m = wvs[(wvs["relationship"] == "matched") & (wvs["is_adapter"])].copy()
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(subset=["model", "eval_country", "question_id"], keep="first"))
    rows = []
    for _, r in m.iterrows():
        if r["gps_dimension"] not in DIM_ITEMS:
            continue
        if r["question_id"] not in DIM_ITEMS[r["gps_dimension"]]:
            continue
        raw = r["model_mean"]
        if r["question_id"] in INVERT_1_4:
            s = 5.0 - raw
        elif r["question_id"] in INVERT_10:
            s = 11.0 - raw
        elif r["question_id"] in BINARY_TRUST:
            s = 1.0 if raw < 1.5 else 0.0
        else:
            s = raw
        rows.append({"country": r["eval_country"], "gps_dimension": r["gps_dimension"],
                     "composite": float(s)})
    df = pd.DataFrame(rows)
    return df.pivot_table(index="country", columns="gps_dimension",
                          values="composite").reset_index()


def partial_spearman(x: pd.Series, y: pd.Series, z: pd.Series) -> float:
    """Spearman-style partial: correlate rank-residuals of x|z with y|z."""
    rx, ry, rz = x.rank(), y.rank(), z.rank()
    Z = np.column_stack([np.ones(len(rz)), rz])
    bx = np.linalg.lstsq(Z, rx, rcond=None)[0]
    by = np.linalg.lstsq(Z, ry, rcond=None)[0]
    ex = rx - Z @ bx
    ey = ry - Z @ by
    if ex.std() == 0 or ey.std() == 0:
        return float("nan")
    return float(pearsonr(ex, ey)[0])


def corr_table(comp: pd.DataFrame, gdp: pd.Series, edu: pd.Series | None,
               label: str, min_n: int = 8) -> pd.DataFrame:
    rows = []
    for dim in DIMS:
        d = comp[["country", dim]].dropna().merge(
            gdp.rename("log_gdp_pc"), left_on="country", right_index=True, how="inner")
        d = d.dropna()
        if len(d) < min_n:
            rows.append({"layer": label, "dim": dim, "n": len(d),
                         "rho_gdp": np.nan, "partial_rho_gdp_edu": np.nan})
            continue
        rho = spearmanr(d[dim], d["log_gdp_pc"], nan_policy="omit").statistic
        if edu is not None:
            d = d.merge(edu.rename("edu"), left_on="country", right_index=True,
                        how="inner").dropna()
            pr = partial_spearman(d[dim], d["log_gdp_pc"], d["edu"])
        else:
            pr = np.nan
        rows.append({"layer": label, "dim": dim, "n": len(d),
                     "rho_gdp": float(rho), "partial_rho_gdp_edu": float(pr)})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gdp = load_wdi_loggdp()
    gps = load_gps_z()
    human = human_layer()
    adapter = adapter_layer()
    print(f"human countries: {len(human)} | adapter countries: {len(adapter)}")

    edu = human.set_index("country")["education"]

    # GPS anchor layer (76 countries, no education control at country level here)
    gps_comp = gps.reset_index().rename(columns={"isocode": "country"})
    gps_tab = corr_table(gps_comp, gdp, None, "gps_z", min_n=30)
    hum_tab = corr_table(human, gdp, edu, "human_wvs", min_n=10)
    adp_tab = corr_table(adapter, gdp, edu, "adapter", min_n=8)

    tab = pd.concat([gps_tab, hum_tab, adp_tab], ignore_index=True)
    tab.to_csv(OUT / "development_restrictions.csv", index=False)

    print("\n=== development restriction: Spearman rho of composite vs log GDP pc ===")
    piv = tab.pivot(index="dim", columns="layer", values="rho_gdp")
    piv_partial = tab.pivot(index="dim", columns="layer", values="partial_rho_gdp_edu")
    print(piv.round(3).to_string())
    print("\n=== partial rho controlling education (human 42, adapter 16) ===")
    print(piv_partial.round(3).to_string())

    # per-country table for the paper figure
    h = human.merge(gdp.rename("log_gdp_pc"), left_on="country", right_index=True, how="inner")
    a = adapter.merge(gdp.rename("log_gdp_pc"), left_on="country", right_index=True, how="inner")
    h[["country", "trust", "patience", "log_gdp_pc", "education"]].to_csv(
        OUT / "development_human_by_country.csv", index=False)
    a[["country", "trust", "patience", "log_gdp_pc"]].to_csv(
        OUT / "development_adapter_by_country.csv", index=False)

    # sign-agreement summary (paper sentence material)
    print("\n=== sign agreement with GPS z on the GDP criterion (per dimension) ===")
    for dim in DIMS:
        sub = tab[tab["dim"] == dim].set_index("layer")
        g = sub.loc["gps_z", "rho_gdp"]
        hh = sub.loc["human_wvs", "rho_gdp"]
        aa = sub.loc["adapter", "rho_gdp"]
        print(f"  {dim:10s} gps={g:+.3f} human={hh:+.3f} adapter={aa:+.3f}  "
              f"| adapter sign == gps sign: {np.sign(aa) == np.sign(g)}")

    print("\nwrote development_restrictions.csv, development_human_by_country.csv, "
          "development_adapter_by_country.csv")


if __name__ == "__main__":
    main()
