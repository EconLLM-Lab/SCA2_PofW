#!/usr/bin/env python3
"""04_direction_cardinal.py — the paper's two headline figures.

FIG A (ordinal claim — "we capture the direction"):
  left  : GPS reward-recovery accuracy per adapter (16 bars, 95% Wilson CI,
          chance at 0.5) — direction recovered on held-out GPS pairs.
  right : WVS-side direction — fraction of matched (country x dimension) cells
          where the adapter shrank the SIGNED |mean bias| vs base, per dimension.

FIG B (cardinal claim — "we do not capture magnitude with hard DPO"):
  left  : scatter adapter model_mean vs population_mean (matched, pooled) with
          identity line + slope — points off the diagonal => no magnitude.
  right : GPS z-score vs adapter signed mean bias (per country x dim) — sign
          relationship only, magnitude does not scale with z.

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/04_direction_cardinal.py
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
RAW_GPS = REPO / "data" / "phase2" / "raw" / "gps"
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
CO2_SUMMARY = REPO / "DPO_train_test" / "CO2_run" / "eval_results_summary.csv"

DIMS = ["altruism", "negrecip", "patience", "posrecip", "risktaking", "trust"]
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.titlesize": 10})


def wilson(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def reward_accuracy() -> pd.DataFrame:
    """Per-adapter GPS reward-recovery accuracy (+ Wilson CI)."""
    rows = []
    # base-8: recompute from row files (132 items each)
    for f in sorted((RAW_GPS / "ksenias_base8").glob("reward_recovery_*_on_*.csv")):
        d = pd.read_csv(f)
        acc = d["dpo_prefers_chosen"].mean()
        lo, hi = wilson(acc, len(d))
        rows.append({"model": d["model"].iloc[0].replace("_adapter", ""), "bank": "base8",
                     "accuracy": acc, "wilson_lo": lo, "wilson_hi": hi, "n": len(d)})
    # CO2-8: committed summary (already has Wilson CIs)
    c = pd.read_csv(CO2_SUMMARY)
    for _, r in c.iterrows():
        rows.append({"model": r["adapter"], "bank": "co2_8", "accuracy": r["accuracy"],
                     "wilson_lo": r["wilson_lo"], "wilson_hi": r["wilson_hi"],
                     "n": 132})
    acc = pd.DataFrame(rows)
    acc.to_csv(OUT / "reward_accuracy_16.csv", index=False)
    return acc


def wvs_direction(wvs: pd.DataFrame) -> pd.DataFrame:
    """Per matched (country x dim): base/adapter signed bias + GPS-z alignment."""
    gps = pd.read_stata(GPS_DTA).set_index("isocode")
    dimmap = {"altruism": "altruism", "negrecip": "negrecip", "patience": "patience",
              "posrecip": "posrecip", "risktaking": "risktaking", "trust": "trust"}
    m = wvs[wvs["relationship"] == "matched"].copy()
    m = m[m["is_adapter"]]
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(subset=["model", "eval_country", "question_id"], keep="first"))
    cells, questions = [], []
    for (bank, model, country), g in m.groupby(["bank", "model", "eval_country"]):
        b = wvs[(wvs["bank"] == bank) & (wvs["model"] == "base")
                & (wvs["eval_country"] == country)]
        for dim, h in g.groupby("gps_dimension"):
            hb = b[b["gps_dimension"] == dim]
            if hb.empty or h.empty:
                continue
            bias_a = (h["model_mean"] - h["population_mean"]).mean()
            bias_b = (hb["model_mean"] - hb["population_mean"]).mean()
            z = gps.loc[country, dimmap[dim]] if country in gps.index else np.nan
            movement = bias_a - bias_b
            cells.append({"model": model, "eval_country": country, "gps_dimension": dim,
                          "z": z, "bias_base": bias_b, "bias_adapter": bias_a,
                          "movement": movement,
                          "shrunk": abs(bias_a) < abs(bias_b),
                          "z_aligned": (not np.isnan(z)) and (np.sign(movement) == np.sign(z))
                                       and abs(movement) > 1e-9})
        # question-level: fraction where adapter bias closer to zero than base's
        h = g.merge(b[["question_id", "model_mean", "population_mean"]],
                    on="question_id", suffixes=("_a", "_b"), how="inner")
        for _, r in h.iterrows():
            ba = r["model_mean_a"] - r["population_mean_a"]
            bb = r["model_mean_b"] - r["population_mean_b"]
            questions.append({"question_id": r["question_id"],
                              "shrunk": abs(ba) < abs(bb)})
    cells = pd.DataFrame(cells)
    qfrac = pd.DataFrame(questions)["shrunk"].mean()
    cells.to_csv(OUT / "wvs_direction_cells.csv", index=False)
    print(f"WVS direction: {qfrac:.1%} of question rows shrink |bias| vs base "
          f"({len(questions)} q); {cells['shrunk'].mean():.1%} of country-dim cells")
    za = cells["z_aligned"].dropna()
    print(f"z-aligned movement (toward GPS-sign direction): "
          f"{za.mean():.1%} of {len(za)} country-dim cells")
    per_dim = cells.groupby("gps_dimension")[["shrunk", "z_aligned"]].mean()
    print(per_dim.round(3).to_string())
    return cells


def fig_a(acc: pd.DataFrame, cells: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    # left: reward accuracy
    ax = axes[0]
    order = acc.sort_values("accuracy")["model"].tolist()
    acc = acc.set_index("model").loc[order].reset_index()
    x = np.arange(len(acc))
    cols = ["#c1666b" if b == "base8" else "#3a7d44" for b in acc["bank"]]
    ax.barh(x, acc["accuracy"], color=cols, xerr=[acc["accuracy"] - acc["wilson_lo"],
                                                  acc["wilson_hi"] - acc["accuracy"]],
            capsize=2.5, error_kw={"lw": 1})
    ax.axvline(0.5, color="k", ls="--", lw=0.8)
    ax.set_yticks(x, acc["model"], fontsize=8)
    ax.set_xlim(0.5, 1.02)
    ax.set_xlabel("held-out pair accuracy (chance = 0.5)")
    ax.set_title("Direction recovered: GPS reward recovery\n(base8 gray · CO2 green)")
    # right: WVS direction per dimension — composite-level Spearman vs GPS z
    ax = axes[1]
    bridge = pd.read_csv(OUT / "construct_bridge_by_dimension.csv").set_index("gps_dimension")
    frac = bridge["adapter_rho_16"].reindex(DIMS)
    cols = ["#3a7d44" if v >= 0.3 else "#c1666b" for v in frac.fillna(0)]
    ax.bar(np.arange(len(DIMS)), frac.values, color=cols, width=0.6)
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(0.3, color="k", ls=":", lw=0.8)
    ax.set_xticks(np.arange(len(DIMS)), DIMS, rotation=25, ha="right")
    ax.set_ylim(-0.3, 1)
    ax.set_ylabel("Spearman rho(adapter composite, GPS z), 16 countries")
    ax.set_title("WVS OOS items: adapter composite vs GPS z per dimension\n"
                 "trust/patience/risk/posrecip captured; negrecip/altruism not")
    fig.suptitle("FIG A — direction claim: recovered in-distribution (GPS pairs)\n"
                 "and on WVS composites for most dimensions (levels, not magnitude)",
                 y=1.02, fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG / "fig_direction_ordinal.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_direction_ordinal.png")


def fig_b(wvs: pd.DataFrame, cells: pd.DataFrame) -> None:
    m = wvs[wvs["relationship"] == "matched"].copy()
    m = m[m["is_adapter"]]
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(subset=["model", "eval_country", "question_id"], keep="first"))
    m = m.dropna(subset=["model_mean", "population_mean"])

    gps = pd.read_stata(GPS_DTA).set_index("isocode")
    dimmap = {"altruism": "altruism", "negrecip": "negrecip", "patience": "patience",
              "posrecip": "posrecip", "risktaking": "risktaking", "trust": "trust"}

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    # left: |bias| adapter vs base (paired per question) — magnitude NOT improved
    ax = axes[0]
    base = wvs[(wvs["relationship"] != "cross") & (wvs["model"] == "base")].copy()
    base = base[["bank", "eval_country", "question_id", "model_mean", "population_mean"]]
    pairs = m.merge(base, on=["bank", "eval_country", "question_id"],
                    suffixes=("_adp", "_base"))
    pairs["abs_bias_adp"] = (pairs["model_mean_adp"] - pairs["population_mean_adp"]).abs()
    pairs["abs_bias_base"] = (pairs["model_mean_base"] - pairs["population_mean_base"]).abs()
    ax.scatter(pairs["abs_bias_base"], pairs["abs_bias_adp"], s=9, alpha=0.5,
               color="#5b7a9d", edgecolors="none")
    lo = min(pairs["abs_bias_base"].min(), pairs["abs_bias_adp"].min())
    hi = max(pairs["abs_bias_base"].max(), pairs["abs_bias_adp"].max())
    ax.plot([lo, hi], [lo, hi], "k--", lw=0.9, label="no change")
    above = (pairs["abs_bias_adp"] > pairs["abs_bias_base"]).mean()
    ax.set_xlabel("|mean bias| base")
    ax.set_ylabel("|mean bias| adapter")
    ax.set_title(f"|bias| per question, adapter vs base (paired, n={len(pairs)})\n"
                 f"{(1-above):.0%} below the line — magnitude not improved")
    ax.legend(frameon=False, fontsize=7)
    print(f"[cardinal] |bias| paired: adapter smaller in {(1-above):.0%} of "
          f"{len(pairs)} questions; mean base {pairs['abs_bias_base'].mean():.3f} vs "
          f"adapter {pairs['abs_bias_adp'].mean():.3f}")

    # right: GPS z vs adapter signed bias (sign only, no magnitude scaling)
    ax = axes[1]
    zs = gps[list(dimmap.values())].reset_index().melt(id_vars="isocode", var_name="dim_dta",
                                                       value_name="z")
    cells2 = cells.drop(columns=["z"]).merge(zs, left_on=["eval_country", "gps_dimension"],
                                             right_on=["isocode", "dim_dta"], how="left")
    colors = plt.cm.tab10(np.linspace(0, 1, len(DIMS)))
    cdict = dict(zip(DIMS, colors))
    for dim in DIMS:
        h = cells2[cells2["gps_dimension"] == dim].dropna(subset=["z", "bias_adapter"])
        ax.scatter(h["z"], h["bias_adapter"], s=28, color=cdict[dim], alpha=0.8,
                   edgecolors="none", label=dim)
    zb = cells2.dropna(subset=["z", "bias_adapter"])
    rr = zb[["z", "bias_adapter"]].corr().iloc[0, 1]
    sign_agree = (np.sign(zb["z"]) == np.sign(zb["bias_adapter"])).mean()
    ax.axhline(0, color="k", lw=0.7)
    ax.axvline(0, color="k", lw=0.7)
    ax.set_xlabel("GPS country z-score (per dimension)")
    ax.set_ylabel("adapter signed mean bias (matched)")
    ax.set_title(f"Sign mostly agrees, magnitude does not scale with z\n"
                 f"r = {rr:.2f}, sign agreement {sign_agree:.0%}")
    ax.legend(frameon=False, fontsize=6.5, ncol=2)
    print(f"[cardinal] z vs bias: r = {rr:.2f}, sign agreement {sign_agree:.0%} (n={len(zb)})")
    fig.suptitle("FIG B — we do NOT capture MAGNITUDE with hard DPO (cardinal claim)",
                 y=1.02, fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG / "fig_magnitude_cardinal.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_magnitude_cardinal.png")


def main() -> None:
    wvs = pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
    acc = reward_accuracy()
    cells = wvs_direction(wvs)
    fig_a(acc, cells)
    fig_b(wvs, cells)
    print("done")


if __name__ == "__main__":
    main()
