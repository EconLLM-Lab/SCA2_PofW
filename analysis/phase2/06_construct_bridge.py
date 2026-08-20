#!/usr/bin/env python3
"""06_construct_bridge.py — WVS-GPS alignment at TWO layers (human vs adapter).

The construct map (data/merged/CONSTRUCT_MAP.md) says only trust carries a
confirmatory sign-recovery prior against GPS (Falk et al. 2018 Table II:
Q57 vs GPS trust rho=0.49, N=60); patience is directional (Q13 rho=0.09 ns);
risk/altruism/posrecip/negrecip are exploratory.

Layer 1 (HUMAN instrument validity, 42 countries): weighted country means of the
mapped items (polarity recodes per CONSTRUCT_MAP "inv" flags) -> dimension
composites -> Spearman rho vs GPS country z.  This is the Falk-style check on
OUR item set and surface (WVS wave 7).

Layer 2 (ADAPTER transfer, 16 countries): same composites computed from the
adapters' predicted means (model_mean, matched cells) -> Spearman rho vs GPS z.
The contrast rho_human vs rho_adapter per dimension = the construct-transfer gap.

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/06_construct_bridge.py
"""
from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
FIG = OUT / "figures"
WVS_DIR = REPO / "data" / "wvs_eval_full"
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"

# polarity recodes: raw item value -> construct-aligned score
# "inv" per CONSTRUCT_MAP: trust 1-4 (higher = less trust) -> 5-raw
INVERT_1_4 = {"Q57": None, "Q59": True, "Q61": True, "Q62": True, "Q63": True,
              "Q64": True, "Q69": True, "Q70": True, "Q71": True,
              "Q58": True, "Q60": True, "Q73": True, "Q81": True}
# Q57 is binary 1=trust,2=careful -> score = 1 if raw==1
BINARY_TRUST = {"Q57", "Q12", "Q13", "Q14", "Q174"}  # 1=mentioned/trust, 2=no
# Q177/Q179 justifiability 1-10, higher = more justifiable -> 11-raw
INVERT_10 = {"Q177", "Q179"}
DIM_ITEMS = {  # from CONSTRUCT_MAP section 2
    "trust": ["Q57", "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70",
              "Q71", "Q58", "Q60", "Q73"],
    "patience": ["Q13", "Q14", "Q43", "Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q12", "Q174", "Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q101", "Q99", "Q103"],
}
PRIOR = {"trust": "HIGH", "patience": "LOW-MOD", "risktaking": "LOW",
         "posrecip": "VERY LOW", "negrecip": "LOW", "altruism": "LOW"}
FALK_RHO = {"trust": 0.49, "patience": 0.09, "altruism": 0.20,
            "risktaking": 0.32, "posrecip": np.nan, "negrecip": np.nan}
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}


def recode(raw: pd.Series, item: str) -> pd.Series:
    s = raw.astype(float)
    if item in INVERT_1_4 and INVERT_1_4[item]:
        s = 5.0 - s
    elif item in INVERT_10:
        s = 11.0 - s
    elif item in BINARY_TRUST:
        s = (s == 1.0).astype(float)
    return s


def human_composites() -> pd.DataFrame:
    """42 countries x item means (weighted, recoded) -> dimension composites."""
    item_means, gps = [], pd.read_stata(GPS_DTA).set_index("isocode")
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        if cc not in gps.index:
            continue
        items = [q for vals in DIM_ITEMS.values() for q in vals]
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + items)
        w = df["W_WEIGHT"].fillna(0)
        for dim, items in DIM_ITEMS.items():
            for it in items:
                if it not in df.columns:
                    continue
                v = recode(df[it], it)
                m = (v >= 0) & (w > 0)  # WVS negatives = missing
                if m.sum() < 50:
                    continue
                item_means.append({"country": cc, "gps_dimension": dim,
                                   "item": it, "mean": float((v[m] * w[m]).sum() / w[m].sum())})
    im = pd.DataFrame(item_means)
    comp = (im.groupby(["country", "gps_dimension"])["mean"]
              .mean().unstack("gps_dimension"))
    zcols = {"trust": "trust", "patience": "patience", "risktaking": "risktaking",
             "posrecip": "posrecip", "negrecip": "negrecip", "altruism": "altruism"}
    z = gps[list(zcols)].rename(columns={c: c + "_z" for c in zcols})
    comp = comp.join(z, how="inner")
    return comp, im


def adapter_composites(wvs: pd.DataFrame) -> pd.DataFrame:
    """16 adapters: dimension composites from model_mean (matched, recoded)."""
    m = wvs[wvs["relationship"] == "matched"].copy()
    m = m[m["is_adapter"]]
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(subset=["model", "eval_country", "question_id"], keep="first"))
    rows = []
    for _, r in m.iterrows():
        if r["gps_dimension"] not in DIM_ITEMS or r["question_id"] not in DIM_ITEMS[r["gps_dimension"]]:
            continue
        raw = r["model_mean"]
        # option-value scale for model_mean mirrors the raw codes
        s = raw
        if r["question_id"] in INVERT_1_4 and INVERT_1_4[r["question_id"]]:
            s = 5.0 - raw
        elif r["question_id"] in INVERT_10:
            s = 11.0 - raw
        elif r["question_id"] in BINARY_TRUST:
            s = 1.0 if raw < 1.5 else 0.0
        rows.append({"country": r["eval_country"], "gps_dimension": r["gps_dimension"],
                     "item": r["question_id"], "mean": s})
    comp = (pd.DataFrame(rows).groupby(["country", "gps_dimension"])["mean"]
            .mean().unstack("gps_dimension"))
    gps = pd.read_stata(GPS_DTA).set_index("isocode")
    zcols = {"trust": "trust", "patience": "patience", "risktaking": "risktaking",
             "posrecip": "posrecip", "negrecip": "negrecip", "altruism": "altruism"}
    z = gps[list(zcols)].rename(columns={c: c + "_z" for c in zcols})
    comp = comp.join(z, how="inner")
    return comp


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    hcomp, him = human_composites()
    wvs = pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
    acomp = adapter_composites(wvs)
    print(f"human layer: {len(hcomp)} countries; adapter layer: {len(acomp)} countries")

    rows = []
    for dim in DIM_ITEMS:
        h = hcomp[[dim, dim + "_z"]].dropna()
        a = acomp[[dim, dim + "_z"]].dropna()
        rho_h = spearmanr(h[dim], h[dim + "_z"]).statistic if len(h) >= 10 else np.nan
        rho_a = spearmanr(a[dim], a[dim + "_z"]).statistic if len(a) >= 8 else np.nan
        rows.append({"gps_dimension": dim, "prior": PRIOR[dim],
                     "falk_rho": FALK_RHO[dim], "human_rho_42": rho_h,
                     "adapter_rho_16": rho_a, "n_human": len(h), "n_adapter": len(a)})
    bridge = pd.DataFrame(rows)
    bridge.to_csv(OUT / "construct_bridge_by_dimension.csv", index=False)
    print("\n=== construct bridge (Spearman rho vs GPS country z) ===")
    print(bridge.round(3).to_string(index=False))

    # item-level human layer (identifies the best proxy items)
    item_rows = []
    for (dim, item), g in him.groupby(["gps_dimension", "item"]):
        m = g.merge(pd.read_stata(GPS_DTA).set_index("isocode")[[dim]].reset_index(),
                    left_on="country", right_on="isocode", how="inner").dropna()
        if len(m) >= 10 and m["mean"].nunique() > 1:
            rho = spearmanr(m["mean"], m[dim]).statistic
        else:
            rho = np.nan
        item_rows.append({"gps_dimension": dim, "item": item, "rho_vs_gps": rho,
                          "n": len(m)})
    by_item = pd.DataFrame(item_rows).sort_values("rho_vs_gps", key=lambda s: s.abs(),
                                                  ascending=False)
    by_item.to_csv(OUT / "construct_bridge_by_item.csv", index=False)
    print("\n=== item-level human rho (sorted by |rho|) ===")
    print(by_item.round(3).to_string(index=False))

    # figure
    dims = list(DIM_ITEMS)
    x = np.arange(len(dims))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.bar(x - 0.24, bridge["human_rho_42"], 0.24, label="human (42 countries)",
           color="#3a7d44")
    ax.bar(x, bridge["adapter_rho_16"], 0.24, label="adapter (16 countries)",
           color="#c1666b")
    ax.scatter(x + 0.24, bridge["falk_rho"], marker="D", s=26, color="#5b7a9d",
               label="Falk et al. 2018 (published)")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_xticks(x, [f"{d}\n({bridge.loc[i,'prior']})" for i, d in enumerate(dims)],
                  fontsize=7.5)
    ax.set_ylabel("Spearman rho vs GPS country z-score")
    ax.set_title("WVS-GPS construct bridge: human instrument validity vs adapter transfer")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_construct_bridge.png", bbox_inches="tight")
    plt.close(fig)
    print("\nwrote fig_construct_bridge.png (+ construct_bridge_by_dimension.csv, "
          "construct_bridge_by_item.csv)")


if __name__ == "__main__":
    main()
