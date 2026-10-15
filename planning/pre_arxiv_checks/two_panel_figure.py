#!/usr/bin/env python3
"""Two-panel association figure from the two-wave score file."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
SCORES = REPO / "analysis/phase2/outputs/paper_a/country_item_scores.csv"
GPS_JSON = REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"
FIG = REPO / "misc/position_paper/rewrite/figures/associations.pdf"
VALUES = REPO / "misc/position_paper/rewrite/figures/associations_values.csv"
PANEL = [
    "ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
    "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA",
]
DIMS = [
    ("trust", "Trust", ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]),
    ("risktaking", "Risk taking", ["Q106", "Q107", "Q109", "Q178"]),
    ("posrecip", "Positive reciprocity", ["Q81"]),
    ("negrecip", "Negative reciprocity", ["Q176", "Q177", "Q179", "Q195"]),
    ("altruism", "Altruism", ["Q99", "Q101", "Q103"]),
]


def spearman(a, b):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(d) < 8 or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return float("nan")
    return float(spearmanr(d["a"], d["b"]).statistic)


def boot(a, b, seed=20260905, reps=2000):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    x = d["a"].to_numpy()
    y = d["b"].to_numpy()
    rng = np.random.default_rng(seed)
    rhos = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(0, len(d), len(d))
        rhos[i] = spearmanr(x[idx], y[idx]).statistic
    point = spearman(a, b)
    return point, float(np.nanquantile(rhos, 0.025)), float(np.nanquantile(rhos, 0.975))


def composite(df, arm, items):
    sub = df[(df.arm == arm) & (df.item.isin(items)) & (df.country.isin(PANEL))]
    sub = sub[np.isfinite(sub["raw"])]
    return sub.groupby("country")["raw"].mean().reindex(PANEL)


def main():
    df = pd.read_csv(SCORES)
    print("arms", sorted(df.arm.unique()))
    z = json.loads(GPS_JSON.read_text())
    rows = []
    for key, label, items in DIMS:
        zser = pd.Series({c: float(z[c][key]) for c in PANEL})
        human = composite(df, "human", items)
        adapter = composite(df, "adapter", items)
        persona = composite(df, "persona", items)
        specs = [
            ("A", "Human–GPS", boot(human, zser)),
            ("A", "Profile adapter + neutral prompt", boot(adapter, zser)),
            ("A", "Base model + country prompt", boot(persona, zser)),
            ("B", "Profile adapter + neutral prompt", boot(adapter, human)),
            ("B", "Base model + country prompt", boot(persona, human)),
        ]
        for panel, series, (rho, lo, hi) in specs:
            rows.append({
                "panel": panel,
                "dimension": label,
                "series": series,
                "rho": rho,
                "lo": lo,
                "hi": hi,
            })
    out = pd.DataFrame(rows)
    trust = out[(out.panel == "A") & (out.dimension == "Trust") & (out.series.str.startswith("Profile"))]
    rho = float(trust.rho.iloc[0])
    if abs(rho - 0.74) > 5e-3:
        raise SystemExit(f"trust adapter-GPS {rho}, expected 0.74")
    VALUES.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(VALUES, index=False)
    print(out.to_string(index=False))

    labels = [d[1] for d in DIMS][::-1]
    series_a = [
        ("Human–GPS", "o", "0.15"),
        ("Profile adapter + neutral prompt", "s", "0.45"),
        ("Base model + country prompt", "D", "0.75"),
    ]
    series_b = series_a[1:]
    fig, axes = plt.subplots(2, 1, figsize=(6.6, 5.8), sharex=True)
    for ax, panel, series in (
        (axes[0], "A", series_a),
        (axes[1], "B", series_b),
    ):
        for i, (name, marker, color) in enumerate(series):
            ys, xs, xerr_lo, xerr_hi = [], [], [], []
            for j, lab in enumerate(labels):
                row = out[(out.panel == panel) & (out.dimension == lab) & (out.series == name)].iloc[0]
                y = j + (i - (len(series) - 1) / 2) * 0.18
                ys.append(y)
                xs.append(row.rho)
                xerr_lo.append(row.rho - row.lo)
                xerr_hi.append(row.hi - row.rho)
            ax.errorbar(
                xs, ys, xerr=[xerr_lo, xerr_hi], fmt=marker, color=color,
                ecolor=color, elinewidth=1.1, capsize=2.5, markersize=5.5,
                label=name, linestyle="none",
            )
        ax.axvline(0, color="0.6", linewidth=0.6)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-0.6, len(labels) - 0.4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_title("A  Association with GPS anchors", loc="left", fontsize=10)
    axes[1].set_title("B  Agreement with WVS respondents", loc="left", fontsize=10)
    axes[1].set_xlabel("Spearman rank correlation")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.14)
    fig.savefig(FIG, bbox_inches="tight")
    print("wrote", FIG)


if __name__ == "__main__":
    main()
