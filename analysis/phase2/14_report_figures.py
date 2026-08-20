#!/usr/bin/env python3
"""14_report_figures.py — all report figures + LaTeX table fragments (v2).

Fixes vs v1 (2026-08-19 audit):
  - persona distributions are now PER-COUNTRY (keyed persona_<CC>), not pooled;
    affects MDS map, PCA map, histograms, radar, development scatter
  - base/noise are single fixed distributions: MDS/PCA show one point each;
    bridge/development tables mark them '---' (undefined by construction)
  - MDS country labels decluttered (16 adapter countries shown as diamonds
    only; other countries get tiny labels)
  - development scatter: 2x2 (trust/patience x adapter/persona) with human
    reference overlay
  - histograms trimmed to 2x2 (Q57/Q69 x USA/CHN)
  - construct heatmap: NaN cells rendered gray with '--'

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/14_report_figures.py
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
TAB = REPO / "analysis" / "phase2" / "tables"
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
CANON = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"
WVS_DIR = REPO / "data" / "wvs_eval_full"
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
WDI_LOCAL = REPO / "data" / "phase2" / "aux" / "wdi.csv"
PERSONA_CSV = RAW / "persona_baseline" / "model_option_probabilities_persona.csv"

ADAPTERS = ["CHN","JPN","GBR","USA","MEX","ARG","DEU","RUS",
            "IND","IDN","NGA","EGY","TUR","NLD","BRA","GRC"]
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
ALL_ITEMS = [q for vals in DIM_ITEMS.values() for q in vals]
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}
REGIONS = {
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
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.titlesize": 10})


def cfst(pA, pB, vals):
    xA = float((vals * pA).sum()); xB = float((vals * pB).sum())
    x = (xA + xB) / 2.0
    vT = 0.5 * float(((pA * (vals - x) ** 2).sum() + (pB * (vals - x) ** 2).sum()))
    vG = 0.5 * ((xA - x) ** 2 + (xB - x) ** 2)
    return vG / vT if vT > 1e-12 else 0.0


def classical_mds(D, k=2):
    n = D.shape[0]
    D2 = D ** 2
    A = -0.5 * (D2 - D2.mean(0, keepdims=True) - D2.mean(1, keepdims=True) + D2.mean())
    w, v = np.linalg.eigh(A)
    idx = np.argsort(w)[::-1][:k]
    return v[:, idx] * np.sqrt(np.maximum(w[idx], 0))


def country_dists():
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


def load_banks():
    banks = {}
    for bname, path in [
        ("usamex_canonical", CANON / "model_option_probabilities.csv"),
        ("ksenias_base8", RAW / "ksenias_base8" / "model_option_probabilities.csv"),
        ("co2_8", RAW / "co2_8" / "model_option_probabilities.csv"),
    ]:
        if path.exists():
            df = pd.read_csv(path, usecols=[
                "model", "eval_country", "question_id", "response_type",
                "is_numeric_open", "option_value", "model_prob"])
            df["model"] = df["model"].replace({"US": "USA", "Mexico": "MEX"})
            df = df[df["is_numeric_open"] != True]
            banks[bname] = df
    return banks


def model_option_dists(model: str, banks: dict) -> dict:
    dfs = []
    for bname, df in banks.items():
        d = df[df["model"] == model].copy()
        d["bank"] = bname
        dfs.append(d)
    df = pd.concat(dfs, ignore_index=True)
    df["bank_rank"] = df["bank"].map(BANK_PRECEDENCE)
    df = (df.sort_values("bank_rank")
          .drop_duplicates(["model", "eval_country", "question_id", "option_value"],
                           keep="first"))
    out = {}
    for q, g in df.groupby("question_id"):
        g = g.sort_values("option_value")
        p = g["model_prob"].values.astype(float)
        p = p / p.sum()
        out[q] = (p, g["option_value"].values.astype(float))
    return out


def persona_option_dists_per_country() -> dict:
    """One distribution per prompted country (keyed 'persona_<CC>')."""
    df = pd.read_csv(PERSONA_CSV, usecols=[
        "prompt_country", "question_id", "option_value", "model_prob"])
    out = {}
    for cc, g in df.groupby("prompt_country"):
        d = {}
        for q, gg in g.groupby("question_id"):
            gg = gg.sort_values("option_value")
            p = gg["model_prob"].values.astype(float)
            p = p / p.sum()
            d[q] = (p, gg["option_value"].values.astype(float))
        out[f"persona_{cc}"] = d
    return out


def distance(a, b):
    items = [q for q in ALL_ITEMS if q in a and q in b]
    vals = []
    for q in items:
        pA, vA = a[q]; pB, vB = b[q]
        if len(pA) != len(pB) or not np.allclose(vA, vB):
            continue
        vals.append(cfst(pA, pB, vA))
    return float(np.mean(vals)) if vals else np.nan


def recode(v, item):
    v = float(v)
    if item in {"Q59","Q61","Q62","Q63","Q64","Q69","Q70","Q71","Q58","Q60","Q73","Q81"}:
        return 5.0 - v
    if item in {"Q177", "Q179"}:
        return 11.0 - v
    if item in {"Q57","Q12","Q13","Q14","Q174"}:
        return 1.0 if v == 1.0 else 0.0
    return v


def composite_from_dist(d, dim):
    vals = []
    for q in DIM_ITEMS[dim]:
        if q in d:
            p, vv = d[q]
            vals.append(recode(float((vv * p).sum()), q))
    return float(np.mean(vals)) if vals else np.nan


def greedy_label_mask(xy, min_frac=0.035):
    """Return boolean mask: annotate point only if farther than min_frac of the
    x-range from every already-annotated point (label collision avoidance)."""
    xs = xy[:, 0]
    span = xs.max() - xs.min()
    thresh = min_frac * span if span > 0 else 1.0
    keep = np.zeros(len(xy), dtype=bool)
    order = np.argsort(xs)
    for i in order:
        if np.any(np.hypot(xy[i, 0] - xy[keep, 0], xy[i, 1] - xy[keep, 1]) < thresh):
            continue
        keep[i] = True
    return keep


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)

    banks = load_banks()
    countries = country_dists()
    cnames = sorted(countries)

    # model distributions
    model_dists = {}
    for cc in ADAPTERS:
        d = model_option_dists(f"{cc}_adapter", banks)
        if d:
            model_dists[f"{cc}_adapter"] = d
    model_dists["base"] = model_option_dists("base", banks)
    model_dists.update(persona_option_dists_per_country())   # persona_<CC> x16

    # noise: uniform over the global union grid per item (single reference point)
    pop_frames = []
    for bname, path in [
        ("usamex_canonical", CANON / "population_response_distributions.csv"),
        ("co2_8", RAW / "co2_8" / "population_response_distributions.csv"),
        ("ksenias_base8", RAW / "ksenias_base8" / "population_response_distributions.csv"),
    ]:
        if path.exists():
            d = pd.read_csv(path, usecols=[
                "eval_country", "question_id", "option_value", "population_prob"])
            d["bank"] = bname
            pop_frames.append(d)
    pop = pd.concat(pop_frames)
    pop = (pop.sort_values("bank", key=lambda s: s.map(BANK_PRECEDENCE))
           .drop_duplicates(["eval_country", "question_id", "option_value"], keep="first"))
    noise_dist = {}
    for q, g in pop[pop["question_id"].isin(ALL_ITEMS)].groupby("question_id"):
        vals = np.sort(g["option_value"].unique().astype(float))
        noise_dist[q] = (np.full(len(vals), 1.0 / len(vals)), vals)
    model_dists["noise"] = noise_dist

    # ---------------------------------------------------------- fig 1: MDS --
    adapters = [f"{cc}_adapter" for cc in ADAPTERS]
    personas = [f"persona_{cc}" for cc in ADAPTERS]
    singles = ["base", "noise"]
    mnames = adapters + personas + singles
    labels = cnames + mnames
    n = len(cnames)
    N = len(labels)
    D = np.full((N, N), np.nan)
    for i in range(n):
        for j in range(i + 1, n):
            D[i, j] = D[j, i] = distance(countries[cnames[i]], countries[cnames[j]])
    for j, m in enumerate(mnames):
        for i, c in enumerate(cnames):
            D[i, n + j] = D[n + j, i] = distance(model_dists[m], countries[c])
    for i in range(n, N):
        for j in range(i + 1, N):
            D[i, j] = D[j, i] = distance(model_dists[mnames[i - n]], model_dists[mnames[j - n]])
    D = np.nan_to_num(D, nan=np.nanmean(D))
    xy = classical_mds(D)

    fig, ax = plt.subplots(figsize=(12, 9))
    # countries: adapter countries shown by their diamond only; others get dots
    # with collision-avoided labels
    cidx = [i for i, c in enumerate(cnames) if c not in ADAPTERS]
    cmask = greedy_label_mask(xy[cidx], min_frac=0.03)
    for k, i in enumerate(cidx):
        c = cnames[i]
        ax.scatter(xy[i, 0], xy[i, 1], s=45,
                   color=REGION_COLORS.get(REGIONS.get(c, "other"), "#bbb"),
                   alpha=0.75, edgecolors="k", linewidths=0.3, zorder=2)
        if cmask[k]:
            ax.annotate(c, (xy[i, 0], xy[i, 1]), fontsize=4.2, xytext=(2, 2),
                        textcoords="offset points", alpha=0.65)
    # adapters
    for j, m in enumerate(adapters):
        k = n + j
        cc = m.replace("_adapter", "")
        ax.scatter(xy[k, 0], xy[k, 1], marker="D", s=70, color="white",
                   edgecolors="red", linewidths=1.4, zorder=3)
        ax.annotate(cc + "*", (xy[k, 0], xy[k, 1]), fontsize=6, xytext=(3, 3),
                    textcoords="offset points", color="red", weight="bold")
    # personas (per country, small triangles, blue)
    for j, m in enumerate(personas):
        k = n + len(adapters) + j
        cc = m.replace("persona_", "")
        ax.scatter(xy[k, 0], xy[k, 1], marker="^", s=45, color="#1f77b4",
                   alpha=0.85, edgecolors="k", linewidths=0.4, zorder=3)
        ax.annotate(cc + "·", (xy[k, 0], xy[k, 1]), fontsize=4.5, xytext=(2, 2),
                    textcoords="offset points", color="#1f77b4")
    # base + noise
    for j, m in enumerate(singles):
        k = n + len(adapters) + len(personas) + j
        marker = "s" if m == "base" else "X"
        color = "k" if m == "base" else "#d62728"
        ax.scatter(xy[k, 0], xy[k, 1], marker=marker, s=90, color=color, zorder=3)
        ax.annotate(m.upper(), (xy[k, 0], xy[k, 1]), fontsize=6.5, xytext=(3, 3),
                    textcoords="offset points", weight="bold")
    ax.set_title("CF_ST cultural distance (Muthukrishna et al. 2020)\n"
                 "42 countries (dots) · 16 adapters (red diamonds, * = own country) · "
                 "16 persona prompts (blue triangles) · base (square) · noise (X)",
                 fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(FIG / "fig_map_cultural_distance.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_map_cultural_distance.png")

    # --------------------------------------------------- fig 2: PCA axes ----
    gps = pd.read_stata(GPS_DTA).set_index("isocode")
    hmeans = {}
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        if cc not in gps.index:
            continue
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + ALL_ITEMS)
        w = df["W_WEIGHT"].fillna(0)
        row = {}
        for it in ALL_ITEMS:
            if it not in df.columns:
                continue
            v = df[it].astype(float)
            m = (v >= 0) & (w > 0)
            if m.sum() < 50:
                continue
            row[it] = float((v[m].map(lambda x: recode(x, it)) * w[m]).sum() / w[m].sum())
        hmeans[cc] = row
    H = pd.DataFrame(hmeans).T.dropna(axis=1)
    X = H.values.astype(float)
    Xc = X - X.mean(0)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    proj_h = Xc @ Vt[:2].T
    col_idx = {q: i for i, q in enumerate(H.columns)}

    def model_item_means(m):
        d = model_dists[m]
        return {q: recode(float((vals * p).sum()), q)
                for q, (p, vals) in d.items() if q in col_idx}

    fig, ax = plt.subplots(figsize=(12, 9))
    hidx = [i for i, c in enumerate(H.index) if c not in ADAPTERS]
    hmask = greedy_label_mask(proj_h[hidx], min_frac=0.03)
    for k, i in enumerate(hidx):
        c = H.index[i]
        ax.scatter(proj_h[i, 0], proj_h[i, 1], s=45,
                   color=REGION_COLORS.get(REGIONS.get(c, "other"), "#bbb"),
                   alpha=0.75, edgecolors="k", linewidths=0.3)
        if hmask[k]:
            ax.annotate(c, (proj_h[i, 0], proj_h[i, 1]), fontsize=4.2, xytext=(2, 2),
                        textcoords="offset points", alpha=0.65)
    def project_model(m):
        r = model_item_means(m)
        keys = [q for q in H.columns if q in r]
        if not keys:
            return None
        vec = np.array([r[q] for q in keys]) - X.mean(0)[[col_idx[q] for q in keys]]
        return vec @ Vt[:2].T
    for cc in ADAPTERS:
        p = project_model(f"{cc}_adapter")
        if p is not None:
            ax.scatter(p[0], p[1], marker="D", s=70, color="white",
                       edgecolors="red", linewidths=1.4)
            ax.annotate(cc + "*", (p[0], p[1]), fontsize=6, xytext=(3, 3),
                        textcoords="offset points", color="red", weight="bold")
    for cc in ADAPTERS:
        p = project_model(f"persona_{cc}")
        if p is not None:
            ax.scatter(p[0], p[1], marker="^", s=45, color="#1f77b4",
                       alpha=0.85, edgecolors="k", linewidths=0.4)
    for m, (marker, color, lab) in [("base", ("s", "k", "BASE")),
                                    ("noise", ("X", "#d62728", "NOISE"))]:
        p = project_model(m)
        if p is not None:
            ax.scatter(p[0], p[1], marker=marker, s=90, color=color)
            ax.annotate(lab, (p[0], p[1]), fontsize=6.5, xytext=(3, 3),
                        textcoords="offset points", weight="bold")
    ax.set_title("Two-axis projection of the 30 mapped WVS items "
                 "(PCA on human country means)\n"
                 "adapters (red diamonds), persona prompts (blue triangles), "
                 "base (square), noise (X)",
                 fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(FIG / "fig_map_pca_axes.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_map_pca_axes.png")

    # ------------------------------------------------- fig 3: TVD heatmap ---
    mdf = pd.read_csv(OUT / "unified_metrics_long.csv")
    mdf["model_family"] = np.where(mdf["model"] == "persona", "persona",
                          np.where(mdf["model"] == "noise", "noise",
                          np.where(mdf["model"] == "base", "base", "adapter")))
    tvd = mdf.groupby(["model_family", "eval_country"])["tv_distance"].mean().unstack()
    tvd = tvd.loc[["adapter", "base", "persona", "noise"]].T.reindex(ADAPTERS)
    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(tvd.values, cmap="viridis_r", aspect="auto")
    ax.set_xticks(range(4), ["adapter", "base", "persona", "noise"])
    ax.set_yticks(range(16), ADAPTERS)
    for i in range(16):
        for j in range(4):
            ax.text(j, i, f"{tvd.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
    ax.set_title("Mean TVD vs WVS population, by country and model (single-choice items)")
    fig.colorbar(im, ax=ax, label="TVD")
    fig.tight_layout()
    fig.savefig(FIG / "fig_heatmap_tvd.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_heatmap_tvd.png")

    # --------------------------------------------- fig 4: construct heatmap -
    br = pd.read_csv(OUT / "unified_construct_bridge.csv")
    br["model_family"] = np.where(br["model"].str.endswith("_adapter"), "adapter", br["model"])
    brf = br.groupby(["model_family", "gps_dimension"])["rho"].mean().unstack()
    brf = brf.loc[["human", "adapter", "persona", "base", "noise"]].T.reindex(DIMS)
    fig, ax = plt.subplots(figsize=(8, 5))
    masked = np.ma.masked_invalid(brf.values.astype(float))
    cmap = plt.cm.RdBu_r.copy()
    cmap.set_bad("#dddddd")
    im = ax.imshow(masked, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(5), ["human", "adapter", "persona", "base", "noise"])
    ax.set_yticks(range(6), DIMS)
    for i in range(6):
        for j in range(5):
            v = brf.values[i, j]
            ax.text(j, i, f"{v:.2f}" if np.isfinite(v) else "--",
                    ha="center", va="center", fontsize=8)
    ax.set_title("Construct bridge: Spearman rho of country composite vs GPS z "
                 "(-- = undefined: single fixed distribution)")
    fig.colorbar(im, ax=ax, label="rho")
    fig.tight_layout()
    fig.savefig(FIG / "fig_heatmap_construct.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_heatmap_construct.png")

    # ------------------------------------------- fig 5: development scatter -
    wdi = pd.read_csv(WDI_LOCAL).groupby("iso3").agg(
        log_gdp_pc=("gdp_pc_ppp", lambda s: np.log(s.mean()))).reset_index()
    wdi_map = dict(zip(wdi["iso3"], wdi["log_gdp_pc"]))
    # human reference composites (trust/patience) — hmeans are ALREADY recoded;
    # do NOT re-apply recode() here (double recoding returns the raw scale)
    hum = {}
    for cc, row in hmeans.items():
        hum[cc] = {d: float(np.mean([row[q] for q in DIM_ITEMS[d] if q in row]))
                   for d in ["trust", "patience"]}
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, (dim, model) in zip(axes.flat, [
            ("trust", "adapter"), ("trust", "persona"),
            ("patience", "adapter"), ("patience", "persona")]):
        # model points
        pts = {}
        for cc in ADAPTERS:
            key = f"{cc}_adapter" if model == "adapter" else f"persona_{cc}"
            d = model_dists.get(key)
            if d is None:
                continue
            cval = composite_from_dist(d, dim)
            if cc in wdi_map and np.isfinite(wdi_map[cc]) and np.isfinite(cval):
                pts[cc] = (wdi_map[cc], cval)
        if pts:
            x = np.array([v[0] for v in pts.values()])
            y = np.array([v[1] for v in pts.values()])
            ax.scatter(x, y, s=40, color="#d62728" if model == "adapter" else "#1f77b4",
                       alpha=0.85, zorder=3)
            for cc, (xx, yy) in pts.items():
                ax.annotate(cc, (xx, yy), fontsize=5.5, xytext=(2, 2),
                            textcoords="offset points", alpha=0.85)
            if len(x) > 3:
                b, a = np.polyfit(x, y, 1)
                xs = np.sort(x)
                ax.plot(xs, a + b * xs, "--", color="#d62728" if model == "adapter"
                        else "#1f77b4", lw=1.2)
                r, _ = spearmanr(x, y)
            else:
                r = np.nan
        else:
            r = np.nan
        # human reference overlay (gray)
        hx = np.array([wdi_map[c] for c in hum
                       if c in wdi_map and np.isfinite(wdi_map[c]) and np.isfinite(hum[c][dim])])
        hy = np.array([hum[c][dim] for c in hum
                       if c in wdi_map and np.isfinite(wdi_map[c]) and np.isfinite(hum[c][dim])])
        ax.scatter(hx, hy, s=14, color="#999999", alpha=0.5, zorder=1, label="human (42)")
        if len(hx) > 3:
            bh, ah = np.polyfit(hx, hy, 1)
            ax.plot(np.sort(hx), ah + bh * np.sort(hx), "-", color="#999999", lw=1)
            rh, _ = spearmanr(hx, hy)
        else:
            rh = np.nan
        ax.set_title(f"{dim} composite vs log GDP pc — {model}  "
                     f"(rho_model={r:.2f}, rho_human={rh:.2f})")
        ax.legend(fontsize=6)
    fig.suptitle("Development restriction by dimension and model "
                 "(gray = human reference)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig_scatter_development.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_scatter_development.png")

    # ---------------------------------------------- fig 6: item histograms --
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    items = ["Q57", "Q69"]
    for col, cc in enumerate(["USA", "CHN"]):
        pop_cc = pop[pop["eval_country"] == cc]
        for row, q in enumerate(items):
            ax = axes[row, col]
            pg = pop_cc[pop_cc["question_id"] == q].sort_values("option_value")
            if pg.empty:
                continue
            vals = pg["option_value"].values.astype(float)
            pp = pg["population_prob"].values.astype(float)
            pp = pp / pp.sum()
            ax.plot(vals, pp, "-o", color="k", lw=1.5, label="population")
            for m, color in [("adapter", "#d62728"), ("persona", "#1f77b4"),
                             ("base", "#2ca02c"), ("noise", "#999999")]:
                key = f"{cc}_adapter" if m == "adapter" else (f"persona_{cc}" if m == "persona" else m)
                d = model_dists.get(key)
                if d and q in d:
                    p, vv = d[q]
                    mask = np.isin(vv, vals)
                    if mask.sum() < 2:
                        continue
                    pv = p[mask].astype(float)
                    pv = pv / pv.sum()
                    ax.plot(vv[mask], pv, "-o", color=color, lw=1.2, ms=3, label=m)
            ax.set_title(f"{q} — {cc}")
            if row == 0:
                ax.legend(fontsize=6, loc="upper right")
    fig.suptitle("Option distributions: population vs models "
                 "(Q57 generalized trust, Q69 confidence in police)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig_histograms_items.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_histograms_items.png")

    # --------------------------------------------------- fig 7: radar ------
    fig, axes = plt.subplots(2, 2, figsize=(11, 10), subplot_kw=dict(polar=True))
    for ax, cc in zip(axes.flat, ["USA", "CHN", "BRA", "EGY"]):
        ang = np.linspace(0, 2 * np.pi, len(DIMS), endpoint=False).tolist()
        ang += ang[:1]
        gz = gps.loc[cc, DIMS].values.astype(float)
        gz = (gz - gz.mean()) / gz.std()
        ax.plot(ang, np.append(gz, gz[0]), color="k", lw=2, label="GPS z")
        for m, color in [("adapter", "#d62728"), ("persona", "#1f77b4"), ("base", "#2ca02c")]:
            key = f"{cc}_adapter" if m == "adapter" else (f"persona_{cc}" if m == "persona" else m)
            d = model_dists.get(key, {})
            vals = np.array([composite_from_dist(d, dim) for dim in DIMS])
            if np.isfinite(vals).all():
                vals = (vals - vals.mean()) / vals.std()
                ax.plot(ang, np.append(vals, vals[0]), color=color, lw=1.5, label=m)
        ax.set_xticks(ang[:-1]); ax.set_xticklabels(DIMS, fontsize=7)
        ax.set_title(cc, fontsize=10)
        ax.legend(fontsize=6, loc="upper right", bbox_to_anchor=(1.25, 1.1))
    fig.suptitle("GPS preference profile: GPS z vs model composites "
                 "(z-scored within country)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig_radar_gps.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_radar_gps.png")

    # ------------------------------------------------- fig 8: violin TVD ----
    fig, ax = plt.subplots(figsize=(8, 5))
    fams = ["adapter", "base", "persona", "noise"]
    data = [mdf[mdf["model_family"] == f]["tv_distance"].values for f in fams]
    parts = ax.violinplot(data, positions=range(4), showmeans=True, widths=0.8)
    ax.set_xticks(range(4), fams)
    ax.set_ylabel("per-item TVD (across countries)")
    ax.set_title("Distribution of per-item TVD by model")
    fig.tight_layout()
    fig.savefig(FIG / "fig_violin_tvd.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_violin_tvd.png")

    # ----------------------------------------------- fig 9: direction bar --
    ddir = pd.read_csv(OUT / "unified_direction.csv")
    ddir["model_family"] = np.where(ddir["model"].str.endswith("_adapter"), "adapter", ddir["model"])
    ddir["model_family"] = np.where(ddir["model_family"] == "persona", "persona", ddir["model_family"])
    ddir = (ddir.groupby(["gps_dimension", "model_family"])["top_option_match"]
            .mean().reset_index())
    piv = ddir.pivot(index="gps_dimension", columns="model_family", values="top_option_match")
    piv = piv.reindex(DIMS)[["adapter", "base", "persona", "noise"]]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(DIMS))
    w = 0.2
    for j, m in enumerate(["adapter", "base", "persona", "noise"]):
        ax.bar(x + (j - 1.5) * w, piv[m].values, w, label=m)
    ax.axhline(0.5, color="k", ls="--", lw=0.8)
    ax.set_xticks(x, DIMS)
    ax.set_ylabel("top-option match rate")
    ax.set_title("Direction: modal answer matches population mode, by dimension and model")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "fig_direction_bar.png", bbox_inches="tight")
    plt.close(fig)
    print("fig_direction_bar.png")

    # ---------------------------------------------------- LaTeX tables ----
    def tex_round(v, nd=2):
        return "---" if not np.isfinite(v) else f"{v:.{nd}f}"

    with open(TAB / "table_distributional.tex", "w") as f:
        agg = mdf.groupby("model_family").agg(
            tvd=("tv_distance", "mean"), jsd=("js_divergence", "mean"),
            entropy=("entropy_error", "mean"), std=("std_error", "mean"),
            top=("top_option_match", "mean")).round(3)
        agg = agg.reindex(["adapter", "base", "persona", "noise"])
        f.write("\\begin{tabular}{lccccc}\n\\toprule\nModel & TVD & JSD & Entropy err & Std err & Top-match \\\\\n\\midrule\n")
        for m in agg.index:
            r = agg.loc[m]
            f.write(f"{m} & {r['tvd']:.3f} & {r['jsd']:.3f} & {r['entropy']:.3f} "
                    f"& {r['std']:.3f} & {r['top']:.3f} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    with open(TAB / "table_construct.tex", "w") as f:
        f.write("\\begin{tabular}{lccccc}\n\\toprule\nDimension & Human (42) & Adapter (16) & Persona (16) & Base & Noise \\\\\n\\midrule\n")
        for dim in DIMS:
            row = [tex_round(brf.loc[dim, m]) for m in ["human", "adapter", "persona", "base", "noise"]]
            f.write(f"{dim} & " + " & ".join(row) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    with open(TAB / "table_development.tex", "w") as f:
        dev = pd.read_csv(OUT / "unified_development.csv")
        dev["model_family"] = np.where(dev["model"].str.endswith("_adapter"),
                                       "adapter", dev["model"])
        dpiv = dev.pivot(index="gps_dimension", columns="model_family", values="rho_gdp")
        f.write("\\begin{tabular}{lccccc}\n\\toprule\nDimension & Human (42) & Adapter (16) & Persona (16) & Base & Noise \\\\\n\\midrule\n")
        for dim in DIMS:
            row = [tex_round(dpiv.loc[dim, m]) for m in ["human", "adapter", "persona", "base", "noise"]]
            f.write(f"{dim} & " + " & ".join(row) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    with open(TAB / "table_direction.tex", "w") as f:
        f.write("\\begin{tabular}{lccccc}\n\\toprule\nDimension & Adapter & Base & Persona & Noise \\\\\n\\midrule\n")
        for dim in DIMS:
            row = [tex_round(piv.loc[dim, m]) for m in ["adapter", "base", "persona", "noise"]]
            f.write(f"{dim} & " + " & ".join(row) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    with open(TAB / "table_bycountry.tex", "w") as f:
        f.write("\\begin{tabular}{lcccc}\n\\toprule\nCountry & Adapter & Base & Persona & Noise \\\\\n\\midrule\n")
        for cc in ADAPTERS:
            row = [tex_round(tvd.loc[cc, m]) for m in ["adapter", "base", "persona", "noise"]]
            f.write(f"{cc} & " + " & ".join(row) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    print("wrote tables/table_{distributional,construct,development,direction,bycountry}.tex")


if __name__ == "__main__":
    main()
