#!/usr/bin/env python3
"""18_2x2_analysis.py — the 2x2 interaction: weights {base, adapter} x prompt
{unconditioned, persona}, on the trust bridge, TVD, and top-match.

Cells:
  base_uncond         existing base (unconditioned)           -> unified tables
  base_persona        existing persona_base run               -> persona files
  adapter_uncond      existing adapters (unconditioned)       -> unified tables
  adapter_persona     NEW run (Colab)                         -> this script's input

Inputs:
  data/phase2/raw/wvs/persona_baseline/model_option_probabilities_persona.csv (base persona)
  data/phase2/raw/wvs/<bank>/model_option_probabilities.csv            (adapter/base uncond)
  <2x2dir>/model_option_probabilities_{C}_adapter_persona.csv          (adapter persona)
Outputs: analysis/phase2/outputs/2x2_summary.csv, 2x2_bridge.csv, 2x2_tvd.csv
Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/18_2x2_analysis.py
"""
from __future__ import annotations

import pathlib, sys

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs"
RAW = REPO / "data" / "phase2" / "raw" / "wvs"
CANON = REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7"
P2 = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RAW / "persona_adapter"

ADAPTERS = ["ARG","BRA","CHN","DEU","EGY","GBR","GRC","IDN","IND","JPN",
            "MEX","NGA","NLD","RUS","TUR","USA"]
TRUST_ITEMS = ["Q57","Q59","Q61","Q62","Q63","Q64","Q69","Q70","Q71","Q58","Q60","Q73"]
INVERT_1_4 = {"Q59","Q61","Q62","Q63","Q64","Q69","Q70","Q71","Q58","Q60","Q73"}
BINARY_TRUST = {"Q57"}
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}


def recode(raw, item):
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in BINARY_TRUST:
        return 1.0 if s == 1.0 else 0.0
    return s


def trust_composite(model_rows: pd.DataFrame) -> float:
    """Mean of E[recode(V)] over the 12 trust items (frozen G0, matches script 13)."""
    means = []
    for q in TRUST_ITEMS:
        d = model_rows[model_rows["question_id"] == q]
        if d.empty:
            continue
        pm = d["model_prob"].values.astype(float)
        raw = d["option_value"].values.astype(float)
        if pm.sum() <= 0:
            continue
        pm = pm / pm.sum()
        rec = np.array([recode(v, q) for v in raw])
        means.append(float((rec * pm).sum()))
    return float(np.mean(means)) if means else np.nan


def load_uncond() -> dict[str, pd.DataFrame]:
    fams = []
    for family, path in [
        ("usamex_canonical", CANON / "model_option_probabilities.csv"),
        ("ksenias_base8", RAW / "ksenias_base8" / "model_option_probabilities.csv"),
        ("co2_8", RAW / "co2_8" / "model_option_probabilities.csv"),
    ]:
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=["model","eval_country","question_id",
                                        "option_value","model_prob"])
        df["bank"] = family
        fams.append(df)
    allf = pd.concat(fams, ignore_index=True)
    allf["model"] = allf["model"].replace({"US":"USA","Mexico":"MEX"})
    allf["own"] = allf["model"].str.replace("_adapter","", regex=False)
    matched = allf[((allf["model"] == "base")
                    | ((allf["model"] == allf["own"] + "_adapter")
                       & (allf["eval_country"] == allf["own"])))].copy()
    matched["bank_rank"] = matched["bank"].map(BANK_PRECEDENCE)
    matched = (matched.sort_values("bank_rank")
               .drop_duplicates(["model","eval_country","question_id","option_value"],
                                keep="first"))
    out = {}
    for model in matched["model"].unique():
        out[model] = matched[matched["model"] == model]
    return out


def load_persona() -> dict[str, pd.DataFrame]:
    df = pd.read_csv(RAW / "persona_baseline" / "model_option_probabilities_persona.csv")
    out = {}
    for c in df["prompt_country"].unique():
        out[c] = df[df["prompt_country"] == c]
    return out


def load_2x2(dirp) -> dict[str, pd.DataFrame]:
    out = {}
    for c in ADAPTERS:
        f = dirp / f"model_option_probabilities_{c}_adapter_persona.csv"
        if f.exists():
            out[c] = pd.read_csv(f)
    return out


def spearman(a, b):
    ra = pd.Series(a).rank().values
    rb = pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> None:
    uncond = load_uncond()
    persona = load_persona()
    two = load_2x2(P2)
    print(f"2x2 files found: {len(two)}/16")

    import json
    z = json.loads((REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_all"
                    / "gps_z_vectors.json").read_text())
    z_trust = {c: z[c]["trust"] for c in ADAPTERS}

    # 4 cells x trust composite per country
    cells = {}
    def comp_or_nan(df):
        return trust_composite(df) if df is not None and len(df) else np.nan
    cells["adapter_uncond"] = {c: comp_or_nan(uncond.get(f"{c}_adapter")) for c in ADAPTERS}
    cells["base_uncond"] = {"USA": comp_or_nan(uncond.get("base"))}  # single fixed
    cells["adapter_persona"] = {c: comp_or_nan(two.get(c)) for c in ADAPTERS}
    cells["base_persona"] = {c: comp_or_nan(persona.get(c)) for c in ADAPTERS}

    # ---- completeness gate: refuse to write headline outputs with missing cells
    missing = [c for c in ADAPTERS if pd.isna(cells["adapter_persona"][c])]
    if missing:
        print(f"INCOMPLETE 2x2: missing adapter_persona for {missing} — bridge table NOT written")
        return

    # trust bridge rho per cell (16 countries)
    rows = []
    for cell, comps in cells.items():
        if cell == "base_uncond":
            continue  # single fixed distribution -> undefined
        comps_arr = np.array([comps[c] for c in ADAPTERS])
        zs = np.array([z_trust[c] for c in ADAPTERS])
        rho = spearman(comps_arr, zs) if len(comps_arr) == 16 else np.nan
        rows.append({"cell": cell, "trust_bridge_rho": rho,
                     "mean_trust_composite": float(np.nanmean(list(comps.values())))})
    bridge = pd.DataFrame(rows)
    bridge.to_csv(OUT / "2x2_bridge.csv", index=False)
    print("\n=== 2x2 trust bridge ===")
    print(bridge.to_string(index=False))

    # ---- TVD / top-match on the like-for-like surface (metrics byte-identical to 13/16)
    def load_population() -> pd.DataFrame:
        fams = []
        for family, path in [
            ("usamex_canonical", CANON / "population_response_distributions.csv"),
            ("ksenias_base8", RAW / "ksenias_base8" / "population_response_distributions.csv"),
            ("co2_8", RAW / "co2_8" / "population_response_distributions.csv"),
        ]:
            if path.exists():
                d = pd.read_csv(path, usecols=["eval_country", "question_id",
                                               "option_value", "population_prob"])
                d["bank"] = family
                fams.append(d)
        pop = pd.concat(fams, ignore_index=True)
        pop["bank_rank"] = pop["bank"].map(BANK_PRECEDENCE)
        pop = (pop.sort_values("bank_rank")
                  .drop_duplicates(["eval_country", "question_id", "option_value"], keep="first"))
        return pop.drop(columns=["bank", "bank_rank"])

    def to_long(df: pd.DataFrame, model: str) -> pd.DataFrame:
        """Collapse repeated-option rows (measurement blocks) by summing probs."""
        g = (df.groupby(["question_id", "option_value"], as_index=False)["model_prob"].sum())
        g["model"] = model
        g["eval_country"] = df["prompt_country"].iloc[0] if "prompt_country" in df else None
        return g[["model", "eval_country", "question_id", "option_value", "model_prob"]]

    pop = load_population()

    def item_metrics(opts: pd.DataFrame) -> pd.DataFrame:
        rows_m = []
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
                top = float(m[np.argmax(pm)])
                top_p = float(m[np.argmax(pp)])
                rows_m.append({"model": model, "eval_country": ec, "question_id": q,
                               "tv_distance": tvd, "top_option_match": float(top == top_p)})
        return pd.DataFrame(rows_m)

    metrics_parts = []
    for c in ADAPTERS:
        metrics_parts.append(item_metrics(to_long(two[c], f"{c}_adapter_persona")))
    for c in ADAPTERS:
        metrics_parts.append(item_metrics(to_long(persona[c], f"{c}_persona")))
    metrics = pd.concat(metrics_parts, ignore_index=True)

    def cell_label(model: str) -> str:
        if model.endswith("_adapter_persona"):
            return "adapter_persona"
        return "base_persona"

    by_cell = (metrics.assign(cell=metrics["model"].map(cell_label))
                     .groupby("cell")[["tv_distance", "top_option_match"]].mean().reset_index())
    by_cell.to_csv(OUT / "2x2_tvd.csv", index=False)
    print("\n=== 2x2 shape metrics (pooled over 16 countries; lower TVD better) ===")
    print(by_cell.to_string(index=False))
    print("\nOutputs: 2x2_bridge.csv, 2x2_tvd.csv")


if __name__ == "__main__":
    main()
