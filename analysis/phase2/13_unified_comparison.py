#!/usr/bin/env python3
"""13_unified_comparison.py — every model through the same pipeline.

Models (per country):
  - base            : Llama-3.1-8B-Instruct, unconditioned prompt (committed evals)
  - persona_base    : same base + "typical adult living in COUNTRY" (new run)
  - <CC>_adapter    : SCA2 DPO/QLoRA adapter, unconditioned (committed evals)
  - noise           : uniform over the population option grid (random-guess floor)
  - human (WVS)     : survey-weighted population (the target; TVD=0 by construction)

Surfaces (identical for every model):
  1. Distributional fit vs WVS population: TVD, JSD, entropy error, std error,
     mean error, top-option match  (single-choice items, per country/item/dim)
  2. Construct bridge: Spearman of country-level dimension composites vs GPS z
     (human 42 ctry; adapter/persona/base/noise 16 ctry)
  3. Development restrictions: Spearman of composite vs log GDP pc, plus
     education partial; Gini aux (WDI)
  4. Direction: top-option match rate by dimension

All item recodes identical to 06_construct_bridge.py. All data local.

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/13_unified_comparison.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
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
INVERT_1_4 = {"Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71",
              "Q58", "Q60", "Q73", "Q81"}
INVERT_10 = {"Q177", "Q179"}
BINARY_TRUST = {"Q57", "Q12", "Q13", "Q14", "Q174"}
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}
MULTI_SELECT = "multiple_response_max_5"


def recode(raw, item):
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in INVERT_10:
        return 11.0 - s
    if item in BINARY_TRUST:
        return 1.0 if s == 1.0 else 0.0
    return s


# ---------------------------------------------------------------- loaders ----
def load_model_options() -> pd.DataFrame:
    """base + adapters from committed banks (matched cells, precedence)."""
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


def load_persona_options() -> pd.DataFrame:
    df = pd.read_csv(PERSONA_CSV, usecols=[
        "model", "prompt_country", "eval_country", "question_id", "response_type",
        "is_numeric_open", "option_value", "model_prob"])
    df = df[df["is_numeric_open"] != True].copy()
    df["model"] = "persona_base"
    return df


def load_population() -> pd.DataFrame:
    fams = []
    for family, path in [
        ("usamex_canonical", CANON / "population_response_distributions.csv"),
        ("ksenias_base8", RAW / "ksenias_base8" / "population_response_distributions.csv"),
        ("co2_8", RAW / "co2_8" / "population_response_distributions.csv"),
    ]:
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=[
            "eval_country", "question_id", "option_value", "population_prob"])
        df["bank"] = family
        fams.append(df)
    pop = pd.concat(fams, ignore_index=True)
    pop["bank_rank"] = pop["bank"].map(BANK_PRECEDENCE)
    return (pop.sort_values("bank_rank")
            .drop_duplicates(["eval_country", "question_id", "option_value"],
                             keep="first"))


def noise_options(pop: pd.DataFrame) -> pd.DataFrame:
    """Uniform over the population option grid per (country, item)."""
    rows = []
    for (ec, q), g in pop.groupby(["eval_country", "question_id"]):
        k = len(g)
        for _, r in g.iterrows():
            rows.append({"model": "noise", "eval_country": ec, "question_id": q,
                         "response_type": None, "is_numeric_open": False,
                         "option_value": r["option_value"], "model_prob": 1.0 / k})
    return pd.DataFrame(rows)


def load_gps_z() -> pd.DataFrame:
    return pd.read_stata(GPS_DTA).set_index("isocode")[DIMS]


def load_wdi() -> pd.DataFrame:
    w = pd.read_csv(WDI_LOCAL)
    g = w.groupby("iso3").agg(
        log_gdp_pc=("gdp_pc_ppp", lambda s: np.log(s.mean())),
        gini=("gini", "mean")).reset_index()
    return g.set_index("iso3")


# ------------------------------------------------------------ metrics -------
def item_metrics(opts: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, ec), g in opts.groupby(["model", "eval_country"]):
        for q, d in g.groupby("question_id"):
            d = d.sort_values("option_value")
            p2 = pop[(pop["eval_country"] == ec) & (pop["question_id"] == q)]
            merged = pd.DataFrame({
                "option_value": d["option_value"].values.astype(float),
                "pm": d["model_prob"].values.astype(float),
            }).merge(p2[["option_value", "population_prob"]], on="option_value", how="inner")
            if len(merged) < 2:
                continue
            m = merged["option_value"].values.astype(float)
            pm = merged["pm"].values.astype(float)
            pp = merged["population_prob"].values.astype(float)
            pm = pm / pm.sum()
            pp = pp / pp.sum()
            tvd = 0.5 * np.abs(pm - pp).sum()
            mj = 0.5 * (pm + pp)
            jsd = 0.5 * (np.sum(pm * np.log2(np.maximum(pm, 1e-12) / np.maximum(mj, 1e-12)))
                         + np.sum(pp * np.log2(np.maximum(pp, 1e-12) / np.maximum(mj, 1e-12))))
            ent = float(-np.sum(pm * np.log2(np.maximum(pm, 1e-12))))
            ent_p = float(-np.sum(pp * np.log2(np.maximum(pp, 1e-12))))
            mean = float((m * pm).sum())
            mean_p = float((m * pp).sum())
            std = float(np.sqrt((((m - mean) ** 2) * pm).sum()))
            std_p = float(np.sqrt((((m - mean_p) ** 2) * pp).sum()))
            top = float(m[np.argmax(pm)])
            top_p = float(m[np.argmax(pp)])
            rows.append({
                "model": model, "eval_country": ec, "question_id": q,
                "n_options": int(len(m)),
                "tv_distance": tvd, "js_divergence": jsd,
                "entropy_error": ent - ent_p, "std_error": std - std_p,
                "mean_error": mean - mean_p, "top_option_match": float(top == top_p),
            })
    return pd.DataFrame(rows)


def composites_from_options(opts: pd.DataFrame) -> pd.DataFrame:
    """model x country x dim composite from option-level data (recoded means)."""
    rows = []
    for (model, ec), g in opts.groupby(["model", "eval_country"]):
        for q, d in g.groupby("question_id"):
            d = d.sort_values("option_value")
            pm = d["model_prob"].values.astype(float)
            pm = pm / pm.sum()
            mean = float((d["option_value"].values.astype(float) * pm).sum())
            for dim, items in DIM_ITEMS.items():
                if q in items:
                    rows.append({"model": model, "eval_country": ec,
                                 "gps_dimension": dim, "item": q,
                                 "mean": recode(mean, q)})
    return pd.DataFrame(rows)


def human_composites() -> pd.DataFrame:
    """42-country survey-weighted recoded means (as in 06)."""
    gps = load_gps_z()
    rows = []
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        if cc not in gps.index:
            continue
        df = pd.read_parquet(f, columns=["W_WEIGHT"] + ALL_ITEMS)
        w = df["W_WEIGHT"].fillna(0)
        for dim, items in DIM_ITEMS.items():
            vals = []
            for it in items:
                if it not in df.columns:
                    continue
                v = df[it].astype(float)
                mask = (v >= 0) & (w > 0)
                if mask.sum() < 50:
                    continue
                vv = v[mask].copy()
                if it in INVERT_1_4:
                    vv = 5.0 - vv
                elif it in INVERT_10:
                    vv = 11.0 - vv
                elif it in BINARY_TRUST:
                    vv = (vv == 1.0).astype(float)
                vals.append(float((vv * w[mask]).sum() / w[mask].sum()))
            if vals:
                rows.append({"model": "human", "eval_country": cc,
                             "gps_dimension": dim, "item": dim + "_composite",
                             "mean": float(np.mean(vals))})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ analysis ------
def spearman_r(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 8 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return np.nan, len(d)
    return float(spearmanr(d["x"], d["y"]).statistic), len(d)


def partial_spearman(x, y, z):
    d = pd.DataFrame({"x": x, "y": y, "z": z}).dropna()
    if len(d) < 8:
        return np.nan
    rx, ry, rz = d["x"].rank(), d["y"].rank(), d["z"].rank()
    Z = np.column_stack([np.ones(len(rz)), rz])
    bx = np.linalg.lstsq(Z, rx, rcond=None)[0]
    by = np.linalg.lstsq(Z, ry, rcond=None)[0]
    ex, ey = rx - Z @ bx, ry - Z @ by
    if ex.std() == 0 or ey.std() == 0:
        return np.nan
    return float(np.corrcoef(ex, ey)[0, 1])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pop = load_population()
    gps = load_gps_z()
    wdi = load_wdi()

    uncond = load_model_options()
    persona = load_persona_options()
    noise = noise_options(pop)

    # ---- distributional surface (single-choice items only) ----
    sc = pop[~pop["question_id"].isin(
        set(pop["question_id"]) & set(
            pd.read_csv(RAW / "co2_8" / "population_response_distributions.csv",
                        usecols=["question_id", "response_type"])
            .loc[lambda d: d["response_type"] == MULTI_SELECT, "question_id"]))]
    # simpler: multi-select ids from the committed map
    multi_ids = set(pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
                    .loc[lambda d: d["scale_family"] == "multi_select", "question_id"])
    u = uncond[~uncond["question_id"].isin(multi_ids)].copy()
    p = persona[~persona["question_id"].isin(multi_ids)].copy()
    n = noise[~noise["question_id"].isin(multi_ids)].copy()
    pop_sc = pop[~pop["question_id"].isin(multi_ids)].copy()

    m_u = item_metrics(u, pop_sc)
    m_p = item_metrics(p, pop_sc)
    m_n = item_metrics(n, pop_sc)
    metrics = pd.concat([m_u, m_p, m_n], ignore_index=True)
    metrics["model"] = metrics["model"].replace("persona_base", "persona")
    metrics.to_csv(OUT / "unified_metrics_long.csv", index=False)

    agg = metrics.groupby("model").agg(
        tvd=("tv_distance", "mean"), jsd=("js_divergence", "mean"),
        entropy_err=("entropy_error", "mean"), std_err=("std_error", "mean"),
        top_match=("top_option_match", "mean")).round(4)
    by_country = metrics.groupby(["model", "eval_country"]).agg(
        tvd=("tv_distance", "mean"), entropy_err=("entropy_error", "mean"),
        std_err=("std_error", "mean"), top_match=("top_option_match", "mean")).round(4)
    agg.to_csv(OUT / "unified_summary_pooled.csv")
    by_country.to_csv(OUT / "unified_summary_by_country.csv")
    print("=== distributional surface (single-choice) ===")
    print(agg.to_string())
    print("\n=== TVD by country ===")
    print(by_country["tvd"].unstack().reindex(ADAPTERS).round(3).to_string())

    # ---- construct bridge: composites vs GPS z (all models) ----
    comp_opts = composites_from_options(pd.concat([u, p, n], ignore_index=True))
    comp_opts["model"] = comp_opts["model"].replace("persona_base", "persona")
    # matched adapters form ONE family of 16 country-composites (as in 06/10):
    # each per-country adapter contributes its own country's composite point
    comp_opts["model"] = np.where(comp_opts["model"].str.endswith("_adapter"),
                                  "adapter", comp_opts["model"])
    comp_opts = pd.concat([comp_opts, human_composites()], ignore_index=True)

    rows = []
    for (model, dim), g in comp_opts.groupby(["model", "gps_dimension"]):
        comp = g.groupby("eval_country")["mean"].mean()
        j = comp.to_frame("m").join(gps[dim].rename("z"), how="inner").dropna()
        r, nn = spearman_r(j["m"], j["z"])
        # base and noise are (near-)constant across countries by construction:
        # base is one unconditioned distribution; noise is uniform per grid.
        # Their cross-country Spearman is undefined -> NaN (honest, not artifact).
        if model in ("base", "noise"):
            r = np.nan
        rows.append({"model": model, "gps_dimension": dim, "rho": r, "n": nn})
    bridge = pd.DataFrame(rows)
    bridge.to_csv(OUT / "unified_construct_bridge.csv", index=False)
    print("\n=== construct bridge (Spearman composite vs GPS z) ===")
    print(bridge.pivot(index="gps_dimension", columns="model", values="rho").round(3).to_string())

    # ---- development restrictions (all models, log GDP + education partial) ----
    edu = human_composites()
    edu = edu[edu["gps_dimension"] == "education"] if "education" in edu["gps_dimension"].values else edu
    # education from the human parquet path: recompute via Q275
    edu_rows = []
    gps_idx = load_gps_z().index
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        if cc not in gps_idx:
            continue
        df = pd.read_parquet(f, columns=["W_WEIGHT", "Q275"])
        w = df["W_WEIGHT"].fillna(0)
        v = df["Q275"].astype(float)
        m = (v >= 0) & (w > 0)
        if m.sum() > 0:
            edu_rows.append({"eval_country": cc,
                             "edu": float((v[m] * w[m]).sum() / w[m].sum())})
    edu_df = pd.DataFrame(edu_rows).set_index("eval_country")

    dev_rows = []
    for (model, dim), g in comp_opts.groupby(["model", "gps_dimension"]):
        comp = g.groupby("eval_country")["mean"].mean().to_frame("m")
        j = comp.join(wdi[["log_gdp_pc", "gini"]], how="inner").join(edu_df, how="left").dropna(
            subset=["log_gdp_pc"])
        if len(j) < 8:
            continue
        r, nn = spearman_r(j["m"], j["log_gdp_pc"])
        pr = partial_spearman(j["m"], j["log_gdp_pc"], j["edu"]) if j["edu"].notna().sum() >= 8 else np.nan
        rg, _ = spearman_r(j["m"], j["gini"])
        # base/noise cross-country correlations undefined (see bridge note)
        if model in ("base", "noise"):
            r = pr = rg = np.nan
        dev_rows.append({"model": model, "gps_dimension": dim,
                         "rho_gdp": r, "n": nn, "partial_rho_gdp_edu": pr, "rho_gini": rg})
    dev = pd.DataFrame(dev_rows)
    dev.to_csv(OUT / "unified_development.csv", index=False)
    print("\n=== development: rho(composite, log GDP pc) ===")
    print(dev.pivot(index="gps_dimension", columns="model", values="rho_gdp").round(3).to_string())
    print("\n=== development partial | edu ===")
    print(dev.pivot(index="gps_dimension", columns="model", values="partial_rho_gdp_edu").round(3).to_string())

    # ---- direction: top-option match by dimension (all models) ----
    dim_map = {q: dim for dim, items in DIM_ITEMS.items() for q in items}
    metrics["gps_dimension"] = metrics["question_id"].map(dim_map)
    dir_tab = metrics.groupby(["model", "gps_dimension"])["top_option_match"].mean().round(3)
    dir_tab.to_csv(OUT / "unified_direction.csv")
    print("\n=== top-option match by dimension ===")
    print(dir_tab.unstack().to_string())

    print("\nwrote unified_metrics_long.csv, unified_summary_*.csv, "
          "unified_construct_bridge.csv, unified_development.csv, unified_direction.csv")


if __name__ == "__main__":
    main()
