#!/usr/bin/env python3
"""01_build_unified_eval.py — assemble the phase-2 unified eval tables.

Reads every eval family from the local mirror (data/phase2/raw/) and the
canonical USA/MEX eval (DPO_eval_WVS/eval_results_wvs_wave7/), and writes
model-agnostic long-format tables to analysis/phase2/outputs/.

Schema is future-proof by design: new adapter waves (soft DPO, extended
prompt) drop in as new `model` rows with zero rework.

Outputs:
  wvs_question_metrics_long.parquet  — per question × model × eval_country
  gps_reward_recovery_long.parquet   — per GPS item × model (row-level)
  (+ .csv mirrors)

Run:  unset PYTHONPATH && .venv/bin/python analysis/phase2/01_build_unified_eval.py
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "phase2" / "raw"
OUT = REPO / "analysis" / "phase2" / "outputs"

# Family -> local location of the per-question metrics file
WVS_FAMILIES = {
    "usamex_canonical": REPO / "DPO_eval_WVS" / "eval_results_wvs_wave7" / "survey_question_metrics_all_models.csv",
    "ksenias_base8": RAW / "wvs" / "ksenias_base8" / "survey_question_metrics_all_models.csv",
    "co2_8": RAW / "wvs" / "co2_8" / "survey_question_metrics_all_models.csv",
}
GPS_FAMILIES = {
    "ksenias_base8": RAW / "gps" / "ksenias_base8",
    "co2_8": RAW / "gps" / "co2_8",
}
QMAP = REPO / "DPO_eval_WVS" / "question_map_wvs_edited.csv"

METRIC_COLS = [
    "tv_distance", "js_divergence", "brier_score", "cross_entropy",
    "population_entropy", "model_entropy", "entropy_error",
    "top_option_match", "population_mean", "model_mean", "mean_error",
    "abs_mean_error", "population_std", "model_std", "std_error",
    "abs_std_error", "wasserstein_distance",
]


def load_wvs_question_metrics() -> pd.DataFrame:
    fams, missing = [], []
    for family, path in WVS_FAMILIES.items():
        if not path.exists():
            missing.append(family)
            continue
        df = pd.read_csv(path)
        df["bank"] = family
        fams.append(df)
    if missing:
        print(f"WARN: missing families (skipped): {missing}", file=sys.stderr)
    if not fams:
        raise SystemExit("no WVS metric files found")
    return pd.concat(fams, ignore_index=True)


def load_question_map() -> pd.DataFrame:
    qmap = pd.read_csv(QMAP)
    qmap = qmap.rename(columns={"Question": "question_id"})
    keep = ["question_id", "Section", "ResponseType", "ResponseLabels",
            "ResponseCodes", "StandaloneQuestion"]
    # note: gps_dimension excluded — the eval metrics file already carries it
    return qmap[[c for c in keep if c in qmap.columns]]


def load_gps_reward() -> pd.DataFrame:
    fams = []
    for family, d in GPS_FAMILIES.items():
        files = sorted(d.glob("reward_recovery_*_on_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df["bank"] = family
            fams.append(df)
    if not fams:
        raise SystemExit("no GPS reward files found")
    return pd.concat(fams, ignore_index=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- WVS question-level metrics -------------------------------------
    wvs = load_wvs_question_metrics()
    qmap = load_question_map()

    # model_country: ISO3 of the adapter that produced this row (NA for base)
    wvs["model_country"] = wvs["model"].str.extract(r"^([A-Za-z]+)_adapter$", expand=False)
    wvs["model_country"] = wvs["model_country"].str.upper().replace(
        {"US": "USA", "MEXICO": "MEX", "UK": "GBR"})
    wvs["is_adapter"] = wvs["model_country"].notna()
    wvs["is_base"] = wvs["model"] == "base"

    wvs = wvs.merge(qmap, on="question_id", how="left", validate="many_to_one")

    # response-scale class for the scale-level analysis layer
    def scale_class(r):
        if r["response_type"] == "multiple_response_max_5":
            return "multiple_response_max5"
        n = r["n_options"]
        if n == 2:
            return "binary_yn"
        if pd.notna(r["is_ordered"]) and r["is_ordered"]:
            return f"ordered_{int(n)}pt"
        return f"single_choice_{int(n)}"

    wvs["scale_class"] = wvs.apply(scale_class, axis=1)
    wvs["scale_family"] = wvs["scale_class"].map(
        lambda s: "binary" if s == "binary_yn" else ("multi_select" if "max5" in s else "ordered_single"))

    wvs = wvs.sort_values(["bank", "eval_country", "model", "question_id"]).reset_index(drop=True)
    wvs.to_parquet(OUT / "wvs_question_metrics_long.parquet", index=False)
    wvs.to_csv(OUT / "wvs_question_metrics_long.csv", index=False)

    # ---- GPS reward-recovery (row level) --------------------------------
    gps = load_gps_reward()
    gps["model_country"] = gps["model"].str.extract(r"^([A-Za-z]+)_adapter$", expand=False)
    gps["model_country"] = gps["model_country"].str.upper().replace({"US": "USA"})
    gps = gps.sort_values(["bank", "model", "item_id"]).reset_index(drop=True)
    gps.to_parquet(OUT / "gps_reward_recovery_long.parquet", index=False)
    gps.to_csv(OUT / "gps_reward_recovery_long.csv", index=False)

    # ---- report ----------------------------------------------------------
    print(f"WVS question metrics : {len(wvs):>6,} rows  "
          f"({wvs['bank'].value_counts().to_dict()})")
    print(f"  adapters: {wvs['is_adapter'].sum():,} rows | "
          f"models: {sorted(wvs['model'].unique())}")
    print(f"  countries: {sorted(wvs['eval_country'].unique())}")
    print(f"  dims: {sorted(wvs['gps_dimension'].dropna().unique())}")
    print(f"  scale classes: {wvs['scale_class'].value_counts().to_dict()}")
    print(f"GPS reward recovery : {len(gps):>6,} rows "
          f"({gps['bank'].value_counts().to_dict()}) "
          f"| {len(gps['item_id'].unique()):,} unique items")
    print(f"\nWrote:\n  {OUT / 'wvs_question_metrics_long.parquet'}\n"
          f"  {OUT / 'gps_reward_recovery_long.parquet'}")


if __name__ == "__main__":
    main()
