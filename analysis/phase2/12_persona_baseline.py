#!/usr/bin/env python3
"""12_persona_baseline.py — country-named prompt baseline analysis.

Compares three fixed distributions on the same 35 WVS items, per country:
  - base (unconditioned, from the committed unified eval)
  - persona_base (base + "typical adult living in COUNTRY", new Colab run)
  - <CC>_adapter (the SCA2 DPO adapter, unconditioned)

Asks: how much does naming the country buy on TVD/dispersion/entropy vs the
weights-only anti-leakage design? And does persona-conditioning beat the
trained adapters at all?

Inputs:
  - /tmp/persona_out/model_option_probabilities_persona.csv (Colab download)
  - local committed unified eval + population distributions
Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/12_persona_baseline.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
CANON = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"
PERSONA_CSV = pathlib.Path("/tmp/persona_out/model_option_probabilities_persona.csv")

ADAPTERS = ["CHN","JPN","GBR","USA","MEX","ARG","DEU","RUS",
            "IND","IDN","NGA","EGY","TUR","NLD","BRA","GRC"]
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}
MULTI_SELECT = "multiple_response_max_5"


def load_unconditioned_options() -> pd.DataFrame:
    """Adapter + unconditioned base option rows (matched cells), deduped by bank."""
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
    # matched cells: base everywhere, adapters on own country
    allf["own"] = allf["model"].str.replace("_adapter", "", regex=False)
    matched = allf[((allf["model"] == "base")
                    | ((allf["model"] == allf["own"] + "_adapter")
                       & (allf["eval_country"] == allf["own"])))].copy()
    matched["bank_rank"] = matched["bank"].map(BANK_PRECEDENCE)
    matched = (matched.sort_values("bank_rank")
               .drop_duplicates(["model", "eval_country", "question_id", "option_value"],
                                keep="first"))
    return matched


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


def metrics(opts: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
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
                "model_entropy": ent, "population_entropy": ent_p,
                "entropy_error": ent - ent_p,
                "model_mean": mean, "population_mean": mean_p,
                "mean_error": mean - mean_p,
                "model_std": std, "population_std": std_p,
                "std_error": std - std_p,
                "top_option_match": float(top == top_p),
            })
    return pd.DataFrame(rows)


def main() -> None:
    if not PERSONA_CSV.exists():
        raise SystemExit(f"missing {PERSONA_CSV} — download from Colab first")
    OUT.mkdir(parents=True, exist_ok=True)

    pop = load_population()
    uncond = load_unconditioned_options()
    uncond = uncond[uncond["response_type"] != MULTI_SELECT].copy()

    persona = pd.read_csv(PERSONA_CSV, usecols=[
        "model", "prompt_country", "eval_country", "question_id", "response_type",
        "is_numeric_open", "option_value", "model_prob"])
    persona = persona[persona["is_numeric_open"] != True].copy()
    persona = persona[persona["response_type"] != MULTI_SELECT].copy()
    persona["model"] = "persona_base"

    m_uncond = metrics(uncond, pop)
    m_persona = metrics(persona, pop)
    m_all = pd.concat([m_uncond, m_persona], ignore_index=True)
    m_all["is_adapter"] = m_all["model"].str.endswith("_adapter")

    agg = m_all.groupby(["model", "eval_country"]).agg(
        tvd=("tv_distance", "mean"),
        entropy_err=("entropy_error", "mean"),
        std_err=("std_error", "mean"),
        top_match=("top_option_match", "mean"),
    ).round(4).reset_index()

    # pivot: one row per country, columns for base / persona / adapter
    piv = agg.pivot(index="eval_country", columns="model", values="tvd").reindex(ADAPTERS)
    cols = [c for c in ["base", "persona_base"] + [f"{c}_adapter" for c in ADAPTERS]
            if c in piv.columns]
    piv = piv[cols]
    # add adapter-matched column
    ad_series = {c: piv.loc[c, f"{c}_adapter"] for c in ADAPTERS if f"{c}_adapter" in piv.columns}
    piv["adapter_own"] = pd.Series(ad_series)

    piv.to_csv(OUT / "persona_vs_base_vs_adapter_tvd.csv")
    print("=== TVD per country: unconditioned base vs persona vs adapter ===")
    print(piv.round(3).to_string())

    # aggregate summary
    base_t = m_all[m_all["model"] == "base"].groupby("eval_country")["tv_distance"].mean()
    pers_t = m_all[m_all["model"] == "persona_base"].groupby("eval_country")["tv_distance"].mean()
    ad_t = m_all[m_all["is_adapter"]].groupby("eval_country")["tv_distance"].mean()
    cmp = pd.DataFrame({"base": base_t, "persona": pers_t, "adapter": ad_t}).reindex(ADAPTERS)
    cmp["persona_minus_base"] = cmp["persona"] - cmp["base"]
    cmp["persona_minus_adapter"] = cmp["persona"] - cmp["adapter"]
    print("\n=== summary: does naming the country help? ===")
    print(cmp.round(3).to_string())
    print(f"\npersona better than base: {(cmp['persona'] < cmp['base']).mean():.0%} of countries")
    print(f"persona better than adapter: {(cmp['persona'] < cmp['adapter']).mean():.0%} of countries")
    print(f"mean Δ persona−base: {cmp['persona_minus_base'].mean():+.4f}")
    print(f"mean Δ persona−adapter: {cmp['persona_minus_adapter'].mean():+.4f}")

    # dispersion/entropy at the model level
    shape = m_all.groupby("model").agg(
        tvd=("tv_distance", "mean"),
        entropy_err=("entropy_error", "mean"),
        std_err=("std_error", "mean"),
        top_match=("top_option_match", "mean"),
    ).round(4)
    print("\n=== pooled shape, by model ===")
    print(shape.to_string())
    shape.to_csv(OUT / "persona_pooled_shape.csv")

    print("\nwrote persona_vs_base_vs_adapter_tvd.csv, persona_pooled_shape.csv")


if __name__ == "__main__":
    main()
