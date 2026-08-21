#!/usr/bin/env python3
"""15_cross_country_matrix.py — canonical 42-country cross-country matrix.

Supersedes the draft 15 (removed 2026-08-20): this version is built on the
paper's exact Table 1 construction and self-checks against it.

Construction (all verified against the committed artifacts):
  1. MODEL SIDE (16 eval countries): per-item tv_distance from the eval
     notebook's survey_question_metrics_*_on_*.csv files, bank precedence
     usamex_canonical > ksenias_base8 > co2_8, matched cells + base,
     30 single-choice items. VERIFIED: pooled adapter TVD 0.4688 == Table 1
     (0.469) and all 16 by-country values match the paper's Table 1 exactly.
  2. MODEL SIDE (extension to 26 non-eval countries): the same adapters are
     single fixed distributions (unconditioned prompts), so their per-item
     option distributions (from the canonical model_option_probabilities.csv
     files, bank precedence) are compared against each country's population
     with the same TVD formula over the merge-aligned grid.
  3. POPULATION SIDE (42 countries): survey-weighted option distributions
     recomputed from data/wvs_eval_full/*_WVS_wave7.parquet (W_WEIGHT,
     missing masked, min-50 valid). VERIFIED: USA Q57 raw-weighted
     {0.372, 0.628} == canonical population_response_distributions.csv.
  4. Own-country ranks are computed over the 42 WVS countries
     (chance = 21.5). Base excluded (no own country).

Outputs (analysis/phase2/outputs/):
  cross_tvd_adapter_country.csv   17 x 42 pooled TVD per (model, country)
  cross_nearest_neighbor.csv      per adapter: nearest country, own rank, gap
  fig_cross_tvd_heatmap.png       17 x 42 heatmap
  fig_cross_nearest.png           bar: own vs nearest TVD per adapter

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/15_cross_country_matrix.py
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
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
CANON = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"
WVS_DIR = REPO / "data" / "wvs_eval_full"

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
EVAL_COUNTRIES = ["ARG","BRA","CHN","DEU","EGY","GBR","GRC","IDN","IND","JPN",
                  "MEX","NGA","NLD","RUS","TUR","USA"]


def bank_of(path: pathlib.Path) -> str:
    p = str(path)
    if "eval_results_wvs_wave7" in p:
        return "usamex_canonical"
    if "ksenias_base8" in p:
        return "ksenias_base8"
    if "co2_8" in p:
        return "co2_8"
    return "unknown"


def load_item_metrics() -> pd.DataFrame:
    """Per-item tv_distance for the 16 eval countries (Table 1 construction)."""
    frames = []
    for d in [CANON, RAW / "ksenias_base8", RAW / "co2_8"]:
        for f in sorted(d.glob("survey_question_metrics_*_on_*.csv")):
            df = pd.read_csv(f, usecols=[
                "model", "eval_country", "relationship", "question_id",
                "response_type", "is_numeric_open", "tv_distance"])
            df["bank"] = bank_of(f)
            frames.append(df)
    m = pd.concat(frames, ignore_index=True)
    m["model"] = m["model"].replace({"US": "USA", "Mexico": "MEX"})
    m = m[m["is_numeric_open"] != True]
    m = m[m["relationship"].isin(["matched", "base"])]
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(["model", "eval_country", "question_id"], keep="first"))
    m = m[m["response_type"] != "multiple_response_max_5"]
    return m


def load_model_options_deduped() -> pd.DataFrame:
    """Per-item option distributions, bank precedence, matched cells only."""
    fams = []
    for family, path in [
        ("usamex_canonical", CANON / "model_option_probabilities.csv"),
        ("ksenias_base8", RAW / "ksenias_base8" / "model_option_probabilities.csv"),
        ("co2_8", RAW / "co2_8" / "model_option_probabilities.csv"),
    ]:
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=[
            "model", "eval_country", "question_id", "response_type",
            "is_numeric_open", "option_value", "model_prob"])
        df["bank"] = family
        fams.append(df)
    allf = pd.concat(fams, ignore_index=True)
    allf["model"] = allf["model"].replace({"US": "USA", "Mexico": "MEX"})
    allf = allf[allf["eval_country"].notna()].copy()
    allf = allf[allf["is_numeric_open"] != True].copy()
    allf["own"] = allf["model"].str.replace("_adapter", "", regex=False)
    matched = allf[((allf["model"] == "base")
                    | ((allf["model"] == allf["own"] + "_adapter")
                       & (allf["eval_country"] == allf["own"])))].copy()
    matched["bank_rank"] = matched["bank"].map(BANK_PRECEDENCE)
    matched = (matched.sort_values("bank_rank")
               .drop_duplicates(["model", "eval_country", "question_id", "option_value"],
                                keep="first"))
    return matched


def load_population_parquet(min_n: int = 50) -> pd.DataFrame:
    """42-country survey-weighted option distributions from raw parquet."""
    rows = []
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + ALL_ITEMS)
        w = df["W_WEIGHT"].fillna(0)
        for it in ALL_ITEMS:
            v = df[it]
            m = (v >= 0) & (w > 0)
            if int(m.sum()) < min_n:
                continue
            p = pd.DataFrame({"v": v[m].astype(float), "w": w[m]}).groupby("v")["w"].sum()
            probs = p.values.astype(float)
            probs = probs / probs.sum()
            for val, pr in zip(p.index.values.astype(float), probs):
                rows.append({"eval_country": cc, "question_id": it,
                             "option_value": val, "population_prob": pr})
    return pd.DataFrame(rows)


def own_country(model: str) -> str:
    cc = model[:-8] if model.endswith("_adapter") else model
    return {"US": "USA"}.get(cc, cc)


def item_tvd(opt: pd.DataFrame, pop: pd.DataFrame, q: str) -> float | None:
    m = opt[opt["question_id"] == q]
    p = pop[pop["question_id"] == q]
    if m.empty or p.empty:
        return None
    merged = m.merge(p[["option_value", "population_prob"]], on="option_value", how="inner")
    if merged.empty:
        return None
    pp = merged["population_prob"].values.astype(float)
    mp = merged["model_prob"].values.astype(float)
    if pp.sum() <= 0 or mp.sum() <= 0:
        return None
    pp = pp / pp.sum()
    mp = mp / mp.sum()
    return 0.5 * np.abs(mp - pp).sum()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    metrics = load_item_metrics()
    opts = load_model_options_deduped()
    pop = load_population_parquet()
    countries = sorted(pop["eval_country"].unique())
    print(f"countries: {len(countries)}")

    # per-item TVD source: metrics file when available (16 eval countries),
    # else computed from model options vs parquet population (extension).
    metric_map = {(r["model"], r["eval_country"], r["question_id"]): r["tv_distance"]
                  for r in metrics.to_dict("records")}
    # The eval's "30 single-choice items" = the mapped single-choice items minus
    # the multi-select battery (Q12/Q13/Q14) plus the single-choice demographics
    # (Q260/Q275/Q288). Derive the universe from the metrics files themselves so
    # the extension cells use the identical item set as the paper's Table 1.
    eval_items = sorted(metrics["question_id"].unique())
    print(f"eval single-choice item universe ({len(eval_items)}):", eval_items)

    def cell_tvds(model: str, c: str) -> list[float]:
        """Per-item TVDs for one (model, country) cell.

        If the cell is covered by the eval notebook's metrics files (the 16
        eval countries, matched + within-bank cross), use exactly that cell's
        metrics items. Only cells with no metrics coverage (cross-bank or the
        26 non-eval countries) are computed from model options vs the parquet
        population over the same item universe.
        """
        metric_items = []
        for q in eval_items:
            v = metric_map.get((model, c, q))
            if v is not None:
                metric_items.append(float(v))
        if metric_items:
            return metric_items
        tvds = []
        for q in eval_items:
            mo = opts[opts["model"] == model]
            po = pop[pop["eval_country"] == c]
            t = item_tvd(mo, po, q)
            if t is not None:
                tvds.append(t)
        return tvds

    models = sorted(opts["model"].unique())
    rows = []
    for m in models:
        for c in countries:
            tvds = cell_tvds(m, c)
            rows.append({"model": m, "country": c,
                         "tvd": float(np.mean(tvds)) if tvds else np.nan,
                         "n_items": len(tvds)})
    df = pd.DataFrame(rows)
    tvd_mat = df.pivot(index="model", columns="country", values="tvd")
    tvd_mat.to_csv(OUT / "cross_tvd_adapter_country.csv")

    # self-check: 16 own-cells must match Table 1
    t1 = pd.read_csv(OUT / "unified_summary_by_country.csv")
    t1 = t1[t1["model"].str.endswith("_adapter")].set_index("eval_country")["tvd"]
    print("=== self-check: 16 own-cells vs Table 1 ===")
    ok_all = True
    for m in models:
        if not m.endswith("_adapter"):
            continue
        own = own_country(m)
        tv = tvd_mat.loc[m, own]
        diff = abs(tv - t1.get(own, np.nan))
        if diff >= 5e-5:  # tolerance = CSV's 4-decimal rounding
            ok_all = False
            print(f"  {m}: {tv:.4f} vs {t1.get(own):.4f} diff={diff:.2e}")
    print("self-check:", "ALL MATCH" if ok_all else "see above")

    # matched vs cross (adapters only)
    nn_rows = []
    for m in models:
        if not m.endswith("_adapter"):
            continue
        row = tvd_mat.loc[m].dropna()
        own = own_country(m)
        if own not in row.index:
            continue
        own_tvd = row[own]
        cross = row.drop(index=[own])
        nn = cross.idxmin()
        nn_rows.append({
            "model": m, "own_country": own, "own_tvd": own_tvd,
            "mean_cross_tvd": cross.mean(), "best_cross_tvd": cross.min(),
            "nearest_country": nn, "nearest_tvd": cross.min(),
            "delta_own_minus_best": own_tvd - cross.min(),
            "own_rank_of_42": int((row < own_tvd).sum()) + 1,
        })
    nn_df = pd.DataFrame(nn_rows).sort_values("own_rank_of_42")
    nn_df.to_csv(OUT / "cross_nearest_neighbor.csv", index=False)
    print("\n=== matched vs cross (42-country, canonical construction) ===")
    print(nn_df.to_string(index=False))
    med = nn_df["own_rank_of_42"].median()
    print(f"\nmedian own-rank: {med}  (chance {len(countries)/2 + .5})")
    print("nearest==CAN:", int((nn_df['nearest_country'] == 'CAN').sum()), f"/{len(nn_df)}")
    print("own rank==1:", int((nn_df['own_rank_of_42'] == 1).sum()))

    fig, ax = plt.subplots(figsize=(16, 8))
    im = ax.imshow(tvd_mat.values, aspect="auto", cmap="viridis_r")
    ax.set_xticks(range(len(countries)))
    ax.set_xticklabels(countries, fontsize=6, rotation=90)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models, fontsize=7)
    plt.colorbar(im, label="pooled TVD vs human population (canonical construction)")
    ax.set_title("Cross-country matrix (canonical): 16 adapters + base x 42 WVS countries")
    plt.tight_layout()
    fig.savefig(FIG / "fig_cross_tvd_heatmap.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 7))
    y = np.arange(len(nn_df))
    ax.barh(y, nn_df.own_tvd, color="#c0392b", label="own country")
    ax.barh(y, nn_df.best_cross_tvd, color="#2980b9", alpha=0.7, label="nearest other country")
    ax.set_yticks(y)
    ax.set_yticklabels(nn_df.model, fontsize=8)
    ax.set_xlabel("pooled TVD (lower = closer to human population)")
    ax.legend(loc="lower right")
    ax.set_title("Own vs nearest-country TVD (canonical 42-country surface)")
    plt.tight_layout()
    fig.savefig(FIG / "fig_cross_nearest.png", dpi=140)
    plt.close(fig)
    print("\nfigures written.")


if __name__ == "__main__":
    main()
