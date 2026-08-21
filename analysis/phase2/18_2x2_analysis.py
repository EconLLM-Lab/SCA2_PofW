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
P2 = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else OUT  # 2x2 CSVs dir

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
    """Mean of recoded item means over the 12 trust items."""
    means = []
    for q in TRUST_ITEMS:
        d = model_rows[model_rows["question_id"] == q]
        if d.empty:
            continue
        pm = d["model_prob"].values.astype(float)
        raw = d["option_value"].values.astype(float)
        if pm.sum() <= 0:
            continue
        means.append(recode(float((raw * pm).sum()), q))
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
    cells["adapter_uncond"] = {c: trust_composite(uncond.get(f"{c}_adapter", pd.DataFrame())) for c in ADAPTERS}
    cells["base_uncond"] = {"USA": trust_composite(uncond.get("base", pd.DataFrame()))}  # single fixed
    cells["adapter_persona"] = {c: trust_composite(two.get(c, pd.DataFrame())) for c in ADAPTERS}
    cells["base_persona"] = {c: trust_composite(persona.get(c, pd.DataFrame())) for c in ADAPTERS}

    # trust bridge rho per cell (16 countries)
    rows = []
    for cell, comps in cells.items():
        if cell == "base_uncond":
            continue  # single fixed distribution -> undefined
        comps_arr = np.array([comps[c] for c in ADAPTERS if pd.notna(comps[c])])
        zs = np.array([z_trust[c] for c in ADAPTERS if pd.notna(comps[c])])
        rho = spearman(comps_arr, zs) if len(comps_arr) == 16 else np.nan
        rows.append({"cell": cell, "trust_bridge_rho": rho,
                     "mean_trust_composite": float(np.nanmean(list(comps.values())))})
    bridge = pd.DataFrame(rows)
    bridge.to_csv(OUT / "2x2_bridge.csv", index=False)
    print("\n=== 2x2 trust bridge ===")
    print(bridge.to_string(index=False))

    # TVD per cell (pooled, 30-item surface) — reuse canonical for uncond, compute for persona
    # (TVD needs the population; use the like-for-like 27-item surface for consistency)
    print("\n(analysis continues once CSVs land)")


if __name__ == "__main__":
    main()
