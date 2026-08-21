#!/usr/bin/env python3
"""02_heatmaps_and_scale.py — per-dimension correlation heatmaps + scale-level layer + specificity.

Design facts encoded here (verified 2026-08-19 from the eval CSVs):
- usamex_canonical: 2x2 grid (base, USA_adapter, MEX_adapter x {USA, MEX}), 35 items/cell.
- ksenias_base8: MATCHED-ONLY (8 adapters on own country) + base x 8.
- co2_8: FULL 8x8 cross grid (277 matched + 1939 cross + 277 base rows).
Model names collide across banks (MEX_adapter in usamex AND base8), so every
aggregation is keyed by (bank, model, eval_country) and MEX/USA use usamex.

Anti-leakage boundary: prompts are unconditioned, so each adapter is a FIXED
output distribution; "matched vs cross" measures distributional proximity to each
country's population, not country-conditioned inference.

Outputs (analysis/phase2/outputs/):
- corr_by_dim_model.csv / fig_corr_dim_heatmap.png     (matched cells)
- matched_vs_cross_tvd.csv / fig_matched_vs_cross.png  (CO2 8x8 + USA/MEX 2x2)
- scale_by_model_kind.csv / scale_adapter_vs_base_delta.csv / fig_scale_layer.png
- entropy_by_dim.csv / fig_modal_collapse_dim.png

Run: unset PYTHONPATH && .venv/bin/python analysis/phase2/02_heatmaps_and_scale.py
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

DIMS = ["altruism", "negrecip", "patience", "posrecip", "risktaking", "trust"]
BANK_PRECEDENCE = {"usamex_canonical": 0, "ksenias_base8": 1, "co2_8": 2}

plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.titlesize": 10})


def load() -> pd.DataFrame:
    df = pd.read_parquet(OUT / "wvs_question_metrics_long.parquet")
    df.loc[df["n_options"] > 12, "scale_class"] = "other_numeric"
    df["scale_family"] = df["scale_class"].map(
        lambda s: "binary" if s == "binary_yn"
        else ("multi_select" if "max5" in s else ("other" if s == "other_numeric" else "ordered")))
    return df


def matched_frame(wvs: pd.DataFrame) -> pd.DataFrame:
    """Matched adapter cells only, MEX/USA resolved to the canonical bank."""
    m = wvs[wvs["relationship"] == "matched"].copy()
    m = m[m["is_adapter"]]
    # resolve duplicate model x eval_country across banks (MEX/USA live in both
    # usamex_canonical and ksenias_base8); keep the canonical (usamex) one
    m["bank_rank"] = m["bank"].map(BANK_PRECEDENCE)
    m = (m.sort_values("bank_rank")
         .drop_duplicates(subset=["model", "eval_country", "question_id"], keep="first"))
    m = m.drop(columns=["bank_rank"])
    return m


def base_for(eval_country: str, bank: str, wvs: pd.DataFrame) -> pd.DataFrame:
    b = wvs[(wvs["model"] == "base") & (wvs["eval_country"] == eval_country)
            & (wvs["bank"] == bank)]
    if b.empty:  # base8/USA-MEX fallback: usamex base for USA/MEX
        b = wvs[(wvs["model"] == "base") & (wvs["eval_country"] == eval_country)
                & (wvs["bank"] == "usamex_canonical")]
    return b


def corr_heatmaps(wvs: pd.DataFrame) -> None:
    m = matched_frame(wvs)
    rows = []
    for (bank, model, eval_country), g in m.groupby(["bank", "model", "eval_country"]):
        for dim, h in g.groupby("gps_dimension"):
            h = h.dropna(subset=["model_mean", "population_mean"])
            n = len(h)
            r = np.nan
            if n >= 3 and h["model_mean"].nunique() > 1 and h["population_mean"].nunique() > 1:
                r = h["model_mean"].corr(h["population_mean"])
            b = base_for(eval_country, bank, wvs)
            dtvd = np.nan
            if not b.empty and dim in b["gps_dimension"].values:
                dtvd = h["tv_distance"].mean() - b[b["gps_dimension"] == dim]["tv_distance"].mean()
            rows.append({"bank": bank, "model": model, "eval_country": eval_country,
                         "gps_dimension": dim, "n_questions": n, "r_mean": r,
                         "delta_tvd_base_to_adapter": dtvd})
    corr = pd.DataFrame(rows)
    corr.to_csv(OUT / "corr_by_dim_model.csv", index=False)

    # order models by eval_country for the display
    order = ["USA", "MEX", "ARG", "DEU", "GBR", "RUS", "CHN", "JPN",
             "BRA", "EGY", "GRC", "IDN", "IND", "NGA", "NLD", "TUR"]
    corr["model"] = pd.Categorical(corr["model"], ordered=True,
                                   categories=[c + "_adapter" for c in order])
    corr = corr.sort_values("model")
    pivot_r = corr.pivot_table(index="model", columns="gps_dimension", values="r_mean")
    pivot_tvd = corr.pivot_table(index="model", columns="gps_dimension",
                                 values="delta_tvd_base_to_adapter")

    fig, axes = plt.subplots(1, 2, figsize=(13, 8))
    for ax, pv, title, cmap, vmin, vmax in [
        (axes[0], pivot_r, "r(adapter mean, population mean), matched cells",
         "RdBu_r", -1, 1),
        (axes[1], pivot_tvd, "Delta TVD (base -> adapter), matched cells",
         "RdBu_r", None, None),
    ]:
        im = ax.imshow(pv.values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_xticks(range(len(pv.columns)), pv.columns, rotation=30, ha="right")
        ax.set_yticks(range(len(pv.index)), pv.index)
        ax.set_title(title)
        for i in range(len(pv.index)):
            for j in range(len(pv.columns)):
                v = pv.values[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5,
                            color="black")
        fig.colorbar(im, ax=ax, shrink=0.8)
    fig.suptitle("Adapter-vs-population alignment by GPS dimension (matched cells)",
                 y=1.01, fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig_corr_dim_heatmap.png", bbox_inches="tight")
    plt.close(fig)
    print(f"corr_heatmaps: {len(corr)} matched cells (bank precedence applied)")


def matched_vs_cross(wvs: pd.DataFrame) -> None:
    """For each eval country x dimension: matched-adapter TVD vs cross-adapter TVD."""
    rows = []
    for bank in ["usamex_canonical", "co2_8"]:
        grid = wvs[(wvs["bank"] == bank) & (wvs["is_adapter"]) &
                   (wvs["relationship"].isin(["matched", "cross"]))]
        for (eval_country, dim), h in grid.groupby(["eval_country", "gps_dimension"]):
            agg = h.groupby("model")["tv_distance"].mean()
            if len(agg) < 2 or eval_country + "_adapter" not in agg.index:
                continue
            matched_tvd = agg[eval_country + "_adapter"]
            cross = agg.drop(index=eval_country + "_adapter")
            rows.append({
                "bank": bank, "eval_country": eval_country, "gps_dimension": dim,
                "matched_tvd": matched_tvd,
                "mean_cross_tvd": cross.mean(),
                "best_cross_tvd": cross.min(),
                "delta_vs_mean_cross": matched_tvd - cross.mean(),
                "delta_vs_best_cross": matched_tvd - cross.min(),
                "n_cross_adapters": len(cross),
            })
    mvc = pd.DataFrame(rows)
    mvc.to_csv(OUT / "matched_vs_cross_tvd.csv", index=False)

    # aggregate
    print("\n=== matched vs cross (TVD), per dimension ===")
    g = mvc.groupby("gps_dimension").agg(
        n=("delta_vs_mean_cross", "size"),
        mean_delta=("delta_vs_mean_cross", "mean"),
        frac_better=("delta_vs_mean_cross", lambda s: (s < 0).mean()),
        mean_delta_vs_best=("delta_vs_best_cross", "mean"))
    print(g.round(4).to_string())
    print(f"\nOverall: matched better than mean-cross in "
          f"{(mvc['delta_vs_mean_cross'] < 0).mean():.1%} of country-dim cells; "
          f"mean delta {mvc['delta_vs_mean_cross'].mean():+.4f}")

    fig, ax = plt.subplots(figsize=(9, 4))
    mvc["d"] = mvc["eval_country"] + "·" + mvc["gps_dimension"].str[:3]
    colors = np.where(mvc["delta_vs_mean_cross"] < 0, "#3a7d44", "#c1666b")
    ax.bar(np.arange(len(mvc)), mvc["delta_vs_mean_cross"], color=colors, width=0.75)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(np.arange(len(mvc)), mvc["d"], rotation=90, fontsize=5.5)
    ax.set_ylabel("TVD(matched) - TVD(mean cross)")
    ax.set_title("Matched vs cross adapter fit by country·dimension (green = matched better)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_matched_vs_cross.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_matched_vs_cross.png  (+ matched_vs_cross_tvd.csv)")


def scale_layer(wvs: pd.DataFrame) -> None:
    """Scale-level layer on MATCHED + base cells only (comparable across banks)."""
    m = wvs[(wvs["relationship"] != "cross")].copy()
    m["model_kind"] = np.where(m["is_adapter"], "adapter", "base")
    g = (m.groupby(["model_kind", "scale_family"])
            .agg(n=("tv_distance", "size"),
                 tvd=("tv_distance", "mean"),
                 jsd=("js_divergence", "mean"),
                 entropy_err=("entropy_error", "mean"),
                 abs_mean_err=("abs_mean_error", "mean"))
            .reset_index())
    g.to_csv(OUT / "scale_by_model_kind.csv", index=False)
    print("\n=== scale layer (matched + base cells) ===")
    print(g.round(4).to_string(index=False))

    piv = g.pivot_table(index="scale_family", columns="model_kind",
                        values=["tvd", "jsd", "entropy_err", "abs_mean_err"])
    piv["delta_tvd"] = piv[("tvd", "adapter")] - piv[("tvd", "base")]
    piv["delta_entropy_err"] = piv[("entropy_err", "adapter")] - piv[("entropy_err", "base")]
    piv.to_csv(OUT / "scale_adapter_vs_base_delta.csv")

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    fams = ["binary", "multi_select", "ordered"]
    for ax, col, title in [
        (axes[0], "tvd", "Mean TVD by response scale"),
        (axes[1], "entropy_err", "Mean entropy error (model - population)"),
        (axes[2], "abs_mean_err", "Mean |mean error| (location)"),
    ]:
        base_v = [g.loc[(g.model_kind == "base") & (g.scale_family == f), col].iloc[0]
                  for f in fams]
        adp_v = [g.loc[(g.model_kind == "adapter") & (g.scale_family == f), col].iloc[0]
                 for f in fams]
        x = np.arange(len(fams))
        ax.bar(x - 0.18, base_v, 0.36, label="base", color="#9db4c0")
        ax.bar(x + 0.18, adp_v, 0.36, label="adapter", color="#c1666b")
        ax.set_xticks(x, fams)
        ax.set_title(title)
        if ax is axes[0]:
            ax.legend(frameon=False)
        ax.axhline(0, color="k", lw=0.6)
    fig.suptitle("Response-scale layer: does binary DPO training hurt non-binary items?")
    fig.tight_layout()
    fig.savefig(FIG / "fig_scale_layer.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_scale_layer.png  (+ scale_by_model_kind.csv, scale_adapter_vs_base_delta.csv)")


def modal_collapse_diag(wvs: pd.DataFrame) -> None:
    m = wvs[wvs["relationship"] != "cross"].copy()
    m["model_kind"] = np.where(m["is_adapter"], "adapter", "base")
    g = (m.groupby(["model_kind", "gps_dimension"])
           .agg(n=("entropy_error", "size"),
                entropy_err=("entropy_error", "mean"),
                tvd=("tv_distance", "mean"))
           .reset_index())
    g.to_csv(OUT / "entropy_by_dim.csv", index=False)
    print("\n=== modal collapse by dimension (matched + base cells) ===")
    print(g.round(4).to_string(index=False))

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, col, title in [(axes[0], "entropy_err", "Mean entropy error by dimension"),
                           (axes[1], "tvd", "Mean TVD by dimension")]:
        base_v = [g.loc[(g.model_kind == "base") & (g.gps_dimension == d), col].iloc[0] for d in DIMS]
        adp_v = [g.loc[(g.model_kind == "adapter") & (g.gps_dimension == d), col].iloc[0] for d in DIMS]
        x = np.arange(len(DIMS))
        ax.bar(x - 0.18, base_v, 0.36, label="base", color="#9db4c0")
        ax.bar(x + 0.18, adp_v, 0.36, label="adapter", color="#c1666b")
        ax.set_xticks(x, DIMS, rotation=25, ha="right")
        ax.set_title(title)
        ax.legend(frameon=False)
        ax.axhline(0, color="k", lw=0.6)
    fig.tight_layout()
    fig.savefig(FIG / "fig_modal_collapse_dim.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_modal_collapse_dim.png  (+ entropy_by_dim.csv)")


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    wvs = load()
    corr_heatmaps(wvs)
    matched_vs_cross(wvs)
    scale_layer(wvs)
    modal_collapse_diag(wvs)
    print("\ndone")


if __name__ == "__main__":
    main()
