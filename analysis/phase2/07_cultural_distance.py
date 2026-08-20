#!/usr/bin/env python3
"""07_cultural_distance.py — CF_ST cultural-distance replication.

Replicates the Muthukrishna et al. (2020, Psych. Science) cultural fixation index
(CF_ST): questions = loci, answers = alleles; pairwise distance between two
populations = mean over items of F_ST = sigma2_g / sigma2_T (continuous
formulation; between-group / total variance of the response distributions).

Populations:
  - 42 WVS wave-7 countries  (survey-weighted response distributions from
    data/wvs_eval_full/*.parquet)
  - 16 country adapters + base model (option-likelihood distributions from the
    eval model_option_probabilities files; unconditioned prompts => each adapter
    is ONE fixed distribution, so its distance to every country is well defined)

Outputs:
  cd_country_country.csv   (42x42)
  cd_adapter_country.csv   (17 x 42; adapters + base)
  cd_adapter_adapter.csv   (17x17)
  fig_cultural_distance_map.png   (classical-MDS joint map: countries + adapters)
  fig_cd_matched_rank.png         (per adapter: rank of own country + nearest)

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/07_cultural_distance.py
"""
from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
FIG = OUT / "figures"
WVS_DIR = REPO / "data" / "wvs_eval_full"
RAW_WVS = REPO / "data" / "phase2" / "raw" / "wvs"

DIM_ITEMS = {
    "trust": ["Q57", "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70",
              "Q71", "Q58", "Q60", "Q73"],
    "patience": ["Q13", "Q14", "Q43", "Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q12", "Q174", "Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q101", "Q99", "Q103"],
}
ALL_ITEMS = [q for vals in DIM_ITEMS.values() for q in vals]
REGIONS = {  # compact continent map for the 42-country set (fallback: other)
    "USA": "Anglo", "CAN": "Anglo", "GBR": "Anglo", "AUS": "Anglo", "NZL": "Anglo",
    "MEX": "LatAm", "ARG": "LatAm", "BRA": "LatAm", "BOL": "LatAm", "COL": "LatAm",
    "CHL": "LatAm", "GTM": "LatAm", "PER": "LatAm", "VEN": "LatAm",
    "DEU": "W.Eur", "NLD": "W.Eur", "FRA": "W.Eur", "CHE": "W.Eur", "AUT": "W.Eur",
    "ESP": "S.Eur", "ITA": "S.Eur", "GRC": "S.Eur", "PRT": "S.Eur",
    "CZE": "E.Eur", "POL": "E.Eur", "ROU": "E.Eur", "HUN": "E.Eur", "RUS": "E.Eur",
    "UKR": "E.Eur", "BLR": "E.Eur", "SRB": "E.Eur", "HRV": "E.Eur",
    "TUR": "MENA", "EGY": "MENA", "IRN": "MENA", "IRQ": "MENA", "JOR": "MENA",
    "LBN": "MENA", "TUN": "MENA",
    "CHN": "E.Asia", "JPN": "E.Asia", "KOR": "E.Asia", "TWN": "E.Asia",
    "IDN": "SE.Asia", "VNM": "SE.Asia", "THA": "SE.Asia", "PHL": "SE.Asia", "MYS": "SE.Asia",
    "IND": "S.Asia", "BGD": "S.Asia", "PAK": "S.Asia", "NPL": "S.Asia", "LKA": "S.Asia",
    "NGA": "Africa", "KEN": "Africa", "ZAF": "Africa", "GHA": "Africa", "ETH": "Africa",
    "TZA": "Africa", "UGA": "Africa", "ZMB": "Africa",
    "AZE": "Caucasus", "GEO": "Caucasus", "ARM": "Caucasus",
}
REGION_COLORS = {"Anglo": "#c1666b", "LatAm": "#e8a13c", "W.Eur": "#5b7a9d",
                 "S.Eur": "#7a9d5b", "E.Eur": "#9d5b7a", "MENA": "#d4b36a",
                 "E.Asia": "#6a5b9d", "SE.Asia": "#5b9d8f", "S.Asia": "#b36a5b",
                 "Africa": "#8f6a4a", "Caucasus": "#9d9d5b", "other": "#bbbbbb"}


def cfst(pA: np.ndarray, pB: np.ndarray, vals: np.ndarray) -> float:
    """F_ST = sigma2_g / sigma2_T for two option distributions on one item."""
    xA = float((vals * pA).sum()); xB = float((vals * pB).sum())
    x = (xA + xB) / 2.0
    vT = 0.5 * float(((pA * (vals - x) ** 2).sum() + (pB * (vals - x) ** 2).sum()))
    vG = 0.5 * ((xA - x) ** 2 + (xB - x) ** 2)
    return vG / vT if vT > 1e-12 else 0.0


def country_dists() -> dict[str, dict[str, tuple[np.ndarray, np.ndarray]]]:
    """country -> item -> (probs over option values, option values)."""
    out = {}
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + ALL_ITEMS)
        w = df["W_WEIGHT"].fillna(0)
        dist = {}
        for it in ALL_ITEMS:
            v = df[it]
            m = (v >= 0) & (w > 0)
            if m.sum() < 50:
                continue
            p = pd.DataFrame({"v": v[m].astype(float), "w": w[m]}).groupby("v")["w"].sum()
            probs = p.values.astype(float)
            probs = probs / probs.sum()
            dist[it] = (probs, p.index.values.astype(float))
        out[cc] = dist
    return out


def adapter_dists() -> dict[str, dict[str, tuple[np.ndarray, np.ndarray]]]:
    """model -> item -> (probs, option values) from model_option_probabilities."""
    out = {}
    files = []
    for d in [RAW_WVS / "ksenias_base8", RAW_WVS / "co2_8",
              REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"]:
        files += sorted(d.glob("model_option_probabilities_*adapter_on_*.csv"))
        files += sorted(d.glob("model_option_probabilities_base_on_*.csv"))
    seen = set()
    for f in files:
        name = f.name.replace("model_option_probabilities_", "").replace(".csv", "")
        model = name.rsplit("_on_", 1)[0]
        if model in seen:
            continue
        seen.add(model)
        d = pd.read_csv(f)
        dist = {}
        for q, g in d.groupby("question_id"):
            g = g.sort_values("option_value")
            p = g["model_prob"].values.astype(float)
            p = p / p.sum()
            dist[q] = (p, g["option_value"].values.astype(float))
        out[model] = dist
    return out


def distance(a: dict[str, tuple[np.ndarray, np.ndarray]],
             b: dict[str, tuple[np.ndarray, np.ndarray]]) -> float:
    items = [q for q in ALL_ITEMS if q in a and q in b]
    if not items:
        return np.nan
    vals = []
    for q in items:
        pA, vA = a[q]; pB, vB = b[q]
        if len(pA) != len(pB) or not np.allclose(vA, vB):
            continue  # option grids must match
        vals.append(cfst(pA, pB, vA))
    if not vals:
        return np.nan
    return float(np.mean(vals))


OWN_MAP = {"US": "USA", "Mexico": "MEX"}


def own_country(model: str) -> str:
    cc = model[:-8] if model.endswith("_adapter") else model
    return OWN_MAP.get(cc, cc)


def classical_mds(D: np.ndarray, k: int = 2) -> np.ndarray:
    n = D.shape[0]
    D2 = D ** 2
    A = -0.5 * (D2 - D2.mean(0, keepdims=True) - D2.mean(1, keepdims=True)
                + D2.mean())
    w, v = np.linalg.eigh(A)
    idx = np.argsort(w)[::-1][:k]
    return v[:, idx] * np.sqrt(np.maximum(w[idx], 0))


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    countries = country_dists()
    models = adapter_dists()
    print(f"countries: {len(countries)} | models: {sorted(models)}")

    cnames = sorted(countries)
    mnames = [m for m in models if m != "base"] + ["base"]
    # mnames order: adapters then base (base last for plotting)

    # country x country
    n = len(cnames)
    Dcc = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(i + 1, n):
            Dcc[i, j] = Dcc[j, i] = distance(countries[cnames[i]], countries[cnames[j]])
    pd.DataFrame(Dcc, index=cnames, columns=cnames).to_csv(OUT / "cd_country_country.csv")

    # adapter x country (17 x 42)
    rows = []
    for m in mnames:
        for c in cnames:
            rows.append({"model": m, "country": c,
                         "cd": distance(models[m], countries[c])})
    ac = pd.DataFrame(rows)
    ac.to_csv(OUT / "cd_adapter_country.csv", index=False)

    # adapter x adapter (17 x 17)
    k = len(mnames)
    Dmm = np.zeros((k, k))
    for i in range(k):
        for j in range(i + 1, k):
            Dmm[i, j] = Dmm[j, i] = distance(models[mnames[i]], models[mnames[j]])
    pd.DataFrame(Dmm, index=mnames, columns=mnames).to_csv(OUT / "cd_adapter_adapter.csv")

    # matched rank: where does the adapter's own country rank among the 42?
    rank_rows = []
    for m in mnames[:-1]:  # adapters only
        own = own_country(m)
        sub = ac[(ac["model"] == m)].dropna().sort_values("cd")
        order = sub["country"].tolist()
        rank = order.index(own) + 1 if own in order else np.nan
        rank_rows.append({"adapter": m, "own_country": own, "rank_of_42": rank,
                          "nearest": order[0] if order else np.nan,
                          "cd_own": sub.loc[sub["country"] == own, "cd"].iloc[0]
                          if own in sub["country"].values else np.nan})
    ranks = pd.DataFrame(rank_rows).sort_values("rank_of_42")
    ranks.to_csv(OUT / "cd_matched_rank.csv", index=False)
    print("\n=== matched-country rank among 42 (CF_ST) ===")
    print(ranks.round(3).to_string(index=False))
    med = ranks["rank_of_42"].median()
    print(f"\nmedian rank of own country: {med} (chance = 21.5)")

    # ---- figure 1: joint MDS map -----------------------------------------
    labels = cnames + mnames
    D = np.full((len(labels), len(labels)), np.nan)
    D[:n, :n] = Dcc
    for j, m in enumerate(mnames):
        for i, c in enumerate(cnames):
            D[i, n + j] = D[n + j, i] = distance(models[m], countries[c])
    for i in range(n, len(labels)):
        for j in range(i + 1, len(labels)):
            D[i, j] = D[j, i] = distance(models[labels[i]], models[labels[j]])
    D = np.nan_to_num(D, nan=Dcc[~np.isnan(Dcc)].mean())
    xy = classical_mds(D)

    fig, ax = plt.subplots(figsize=(12, 9))
    for i, c in enumerate(cnames):
        ax.scatter(xy[i, 0], xy[i, 1], s=60, color=REGION_COLORS.get(REGIONS.get(c, "other"), "#bbb"),
                   alpha=0.8, edgecolors="k", linewidths=0.4, zorder=2)
        ax.annotate(c, (xy[i, 0], xy[i, 1]), fontsize=5.5, xytext=(2, 2),
                    textcoords="offset points", alpha=0.75)
    for j, m in enumerate(mnames):
        kk = n + j
        if m == "base":
            ax.scatter(xy[kk, 0], xy[kk, 1], marker="s", s=90, color="k", zorder=3)
            ax.annotate("BASE", (xy[kk, 0], xy[kk, 1]), fontsize=6, xytext=(3, 3),
                        textcoords="offset points", weight="bold")
        else:
            own = own_country(m)
            ax.scatter(xy[kk, 0], xy[kk, 1], marker="D", s=70, color="white",
                       edgecolors="red", linewidths=1.4, zorder=3)
            ax.annotate(own + "*", (xy[kk, 0], xy[kk, 1]), fontsize=6.5, xytext=(3, 3),
                        textcoords="offset points", color="red", weight="bold")
    ax.set_title("CF_ST cultural distance — classical MDS (42 countries + 16 adapters + base)\n"
                 "countries by region · diamonds = adapters (red label = their country)", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    import matplotlib.patches as mpatches
    handles = [mpatches.Patch(color=c, label=r) for r, c in REGION_COLORS.items()
               if r in [REGIONS.get(x, "other") for x in cnames]]
    ax.legend(handles=handles, frameon=False, fontsize=6.5, loc="upper left",
              bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    fig.savefig(FIG / "fig_cultural_distance_map.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_cultural_distance_map.png")

    # ---- figure 2: matched rank + nearest ---------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = np.arange(len(ranks))
    ax.barh(x, ranks["rank_of_42"], color="#3a7d44")
    ax.axvline(21.5, color="k", ls="--", lw=0.9)
    ax.set_yticks(x, [f"{r['adapter']} -> {r['nearest']}" for _, r in ranks.iterrows()], fontsize=7)
    ax.set_xlabel("rank of own country among 42 (1 = closest; chance = 21.5)")
    ax.set_title("CF_ST: where does each adapter's own country rank? (green = better than chance)")
    ax.set_xlim(0, 43)
    fig.tight_layout()
    fig.savefig(FIG / "fig_cd_matched_rank.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_cd_matched_rank.png  (+ cd_*.csv)")


if __name__ == "__main__":
    main()
