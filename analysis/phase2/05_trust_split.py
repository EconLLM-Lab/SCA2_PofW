#!/usr/bin/env python3
"""05_trust_split.py — trust item-target split: family vs known vs outgroup vs institutions.

Motivation (Ksennia's meeting notes): adapters "over-generalize trusting behavior" —
China fits family-trust items but stays trusting toward foreigners; Japan has a
negative GPS trust sign yet leans trusting on specific questions.

Design (matched cells, trust dimension only):
1. Class-level metrics (adapter vs base): TVD, entropy error, signed mean bias,
   |mean bias| per trust-target class.
2. Over-generalization contrast: within country, adapter spread across classes
   (family minus outgroup mean) vs the population's spread — does the adapter
   differentiate targets LESS than the population does?
3. Country spotlights: CHN and JPN per-item tables.

Trust roster (verified from the eval items, 2026-08-19):
  family    : Q58
  ingroup   : Q59 (neighborhood), Q60 (people you know personally)
  outgroup  : Q57 (generalized), Q61 (first meeting), Q62 (other religion), Q63 (other nationality)
  inst      : Q64 (churches), Q69 (police), Q70 (courts), Q71 (government), Q73 (parliament)

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/05_trust_split.py
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

TRUST_CLASS = {
    "Q58": "family",
    "Q59": "ingroup", "Q60": "ingroup",
    "Q57": "outgroup", "Q61": "outgroup", "Q62": "outgroup", "Q63": "outgroup",
    "Q64": "institutions", "Q69": "institutions", "Q70": "institutions",
    "Q71": "institutions", "Q73": "institutions",
}
CLASS_ORDER = ["family", "ingroup", "outgroup", "institutions"]
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.titlesize": 10})


def matched(wvs: pd.DataFrame) -> pd.DataFrame:
    m = wvs[(wvs["relationship"] == "matched")].copy()
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(subset=["model", "eval_country", "question_id"], keep="first"))
    return m[m["is_adapter"]]


def main() -> None:
    wvs = pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
    t = wvs[wvs["gps_dimension"] == "trust"].copy()
    t = t[t["question_id"].isin(TRUST_CLASS)]
    t["trust_class"] = t["question_id"].map(TRUST_CLASS)
    t["model_kind"] = np.where(t["is_adapter"], "adapter", "base")

    # 1) class-level, matched cells (adapter) + base rows on same countries
    m = matched(wvs)
    m = m[m["gps_dimension"] == "trust"]
    m["trust_class"] = m["question_id"].map(TRUST_CLASS)
    adp = m.groupby("trust_class").agg(
        n_items=("question_id", "nunique"),
        tvd=("tv_distance", "mean"),
        entropy_err=("entropy_error", "mean"),
        signed_bias=("mean_error", "mean"),
        abs_bias=("abs_mean_error", "mean")).reindex(CLASS_ORDER)
    base_rows = wvs[(wvs["model"] == "base") & (wvs["gps_dimension"] == "trust")
                    & (wvs["question_id"].isin(TRUST_CLASS))]
    base_rows["trust_class"] = base_rows["question_id"].map(TRUST_CLASS)
    base = base_rows.groupby("trust_class").agg(
        tvd=("tv_distance", "mean"),
        entropy_err=("entropy_error", "mean"),
        signed_bias=("mean_error", "mean"),
        abs_bias=("abs_mean_error", "mean")).reindex(CLASS_ORDER)
    summary = pd.concat({"adapter": adp, "base": base}, axis=1)
    summary.to_csv(OUT / "trust_split_by_class.csv")
    print("=== trust class-level (matched cells, adapter vs base) ===")
    print(summary.round(4).to_string())

    # 2) over-generalization: per-country contrast family-minus-outgroup mean
    pop = (t[t["model_kind"] == "base"]
             .groupby(["eval_country", "trust_class"])["population_mean"].mean().unstack())
    mod = (m[m["trust_class"].isin(["family", "outgroup"])]
             .groupby(["eval_country", "trust_class"])["model_mean"].mean().unstack())
    over = pd.DataFrame({
        "pop_fam_minus_out": pop["family"] - pop["outgroup"],
        "adp_fam_minus_out": mod["family"] - mod["outgroup"],
    }).dropna()
    over["adp_contrast_smaller"] = over["adp_fam_minus_out"].abs() < over["pop_fam_minus_out"].abs()
    over.to_csv(OUT / "trust_overgeneralization.csv")
    print(f"\n=== over-generalization: family-minus-outgroup mean ===")
    print(over.round(3).to_string())
    print(f"\nadapter differentiates family vs outgroup LESS than population in "
          f"{over['adp_contrast_smaller'].mean():.0%} of {len(over)} countries "
          f"(pop contrast {over['pop_fam_minus_out'].mean():+.3f} vs "
          f"adapter {over['adp_fam_minus_out'].mean():+.3f})")

    # 3) spotlights: CHN and JPN per-item
    spot = m[m["eval_country"].isin(["CHN", "JPN"])]
    spot = spot[["eval_country", "model", "question_id", "trust_class", "question_text",
                 "tv_distance", "mean_error", "abs_mean_error", "model_mean", "population_mean"]]
    spot = spot.sort_values(["eval_country", "trust_class", "question_id"])
    spot.to_csv(OUT / "trust_spotlight_chin_jpn.csv", index=False)
    print("\n=== spotlight CHN / JPN (per item) ===")
    print(spot[["eval_country", "question_id", "trust_class", "tv_distance",
                "mean_error", "model_mean", "population_mean"]].round(3).to_string(index=False))

    # figures
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2))
    x = np.arange(len(CLASS_ORDER))
    w = 0.36
    ax = axes[0]
    ax.bar(x - w / 2, base["tvd"].values, w, label="base", color="#9db4c0")
    ax.bar(x + w / 2, adp["tvd"].values, w, label="adapter", color="#c1666b")
    ax.set_xticks(x, CLASS_ORDER)
    ax.set_title("Mean TVD by trust-target class (matched)")
    ax.legend(frameon=False)
    ax = axes[1]
    ax.bar(x - w / 2, base["entropy_err"].values, w, label="base", color="#9db4c0")
    ax.bar(x + w / 2, adp["entropy_err"].values, w, label="adapter", color="#c1666b")
    ax.set_xticks(x, CLASS_ORDER)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_title("Mean entropy error by trust-target class (matched)")
    ax.legend(frameon=False)
    fig.suptitle("Trust over-generalization: adapter fit by target class")
    fig.tight_layout()
    fig.savefig(FIG / "fig_trust_split.png", bbox_inches="tight")
    plt.close(fig)
    print("\nwrote fig_trust_split.png  (+ trust_split_by_class.csv, "
          "trust_overgeneralization.csv, trust_spotlight_chin_jpn.csv)")


if __name__ == "__main__":
    main()
