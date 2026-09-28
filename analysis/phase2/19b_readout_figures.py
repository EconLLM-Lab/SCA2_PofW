#!/usr/bin/env python3
"""19b_readout_figures.py — figures for the softmax-readout experiment."""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = pathlib.Path(__file__).resolve().parent / "outputs"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)

pooled = pd.read_csv(OUT / "readout_pooled_by_tau.csv")
agg = pd.read_csv(OUT / "readout_arm_by_tau.csv")
qm = pd.read_csv(OUT / "readout_question_metrics.csv")
oc = pd.read_csv(OUT / "readout_ordinal_calibration.csv")

# F5a: pooled TVD vs tau
fig, ax = plt.subplots(figsize=(6.4, 4))
for kind, g in pooled.groupby("arm_kind"):
    ax.plot(g.tau, g.tvd_mean, marker="o", label=kind)
ax.set_xlabel(r"readout temperature $\tau$")
ax.set_ylabel("mean TVD to human distribution")
ax.set_title("Softmax readout: dispersion recovery by arm type\n(lower is better; "
             "16 countries, 35 questions)")
ax.legend(frameon=False)
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "F5a_readout_tvd_by_tau.png", dpi=160); plt.close(fig)

# F5b: adapter minus base gap vs tau (within each family)
fig, ax = plt.subplots(figsize=(6.4, 4))
for family, g in agg[agg.arm_kind == "adapter"].groupby("family"):
    b = agg[(agg.arm_kind == "base") & (agg.family == family)].tvd_mean
    if b.empty:
        continue
    m = g.sort_values("tau").merge(
        agg[(agg.arm_kind == "base") & (agg.family == family)][["tau", "tvd_mean"]],
        on="tau", suffixes=("", "_base"))
    ax.plot(m.tau, m.tvd_mean - m.tvd_mean_base, marker="o", label=f"{family} adapter−base")
ax.axhline(0, color="k", lw=.8)
ax.set_xlabel(r"$\tau$"); ax.set_ylabel("Δ mean TVD (adapter − base)")
ax.set_title("Does readout close the adapter–base gap?\n(negative = adapter closer to humans)")
ax.legend(frameon=False); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "F5b_adapter_base_gap.png", dpi=160); plt.close(fig)

# F5c: distance gauge scatter (co2_8 cells, raw probs; tau-invariant by construction)
from scipy.stats import spearmanr
fig, ax = plt.subplots(figsize=(6.4, 4))
DIMS = ["patience", "risktaking", "posrecip", "negrecip", "altruism", "trust"]
gps = pd.read_stata(pathlib.Path(__file__).resolve().parents[2] /
                    "data/GPS/GPS_dataset_country_level/country_gps.dta",
                    convert_categoricals=False)[["isocode"] + DIMS].set_index("isocode")
panel = pd.read_parquet(OUT / "readout_option_panel.parquet")
sub = panel[(panel.family == "co2_8") & (panel.model.str.endswith("_adapter"))]
cells = []
for dim in DIMS:
    qs = [q for q, g in sub.groupby("question_id")
          if (g.gps_dimension.mode().iat[0] if len(g.gps_dimension.mode()) else None) == dim]
    for q in qs:
        g = sub[sub.question_id == q]
        countries = sorted(g.eval_country.unique())
        for i, a in enumerate(countries):
            for b in countries[i + 1:]:
                pa = g[g.eval_country == a].set_index("option_code").model_prob
                pb = g[g.eval_country == b].set_index("option_code").model_prob
                if pa.empty or pb.empty:
                    continue
                idx = pa.index.union(pb.index)
                t = 0.5 * float((pa.reindex(idx, fill_value=0)
                                 - pb.reindex(idx, fill_value=0)).abs().sum())
                dz = abs(float(gps.loc[a, dim]) - float(gps.loc[b, dim]))
                cells.append({"pair": f"{a}-{b}", "dim": dim, "abs_dz": dz, "tvd": t})
c = pd.DataFrame(cells)
rng = np.random.default_rng(7)
for d_, gg in c.groupby("dim"):
    ax.scatter(gg.abs_dz + rng.uniform(-.008, .008, len(gg)), gg.tvd,
               s=10, alpha=.55, label=d_)
rho = spearmanr(c.abs_dz, c.tvd).statistic
ax.set_xlabel("|Δz| (GPS country gap, dimension-level)")
ax.set_ylabel("policy-pair TVD")
ax.set_title(f"Distance gauge, CO2 grid ({c.pair.nunique()} pairs × 6 dims)\n"
             f"Spearman ρ = {rho:.3f}")
ax.legend(frameon=False, fontsize=7, ncol=3); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "F5c_distance_gauge.png", dpi=160); plt.close(fig)

# F5d: ordinal calibration tau=1 vs tau=3
fig, ax = plt.subplots(figsize=(5.2, 5.2))
o = oc.pivot_table(index=["family", "model"], columns="tau", values="calib_rho")
o = o.dropna(subset=[1.0, 3.0])
ax.scatter(o[1.0], o[3.0], s=28)
lim = [.68, .97]
ax.plot(lim, lim, "k--", lw=.8)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel(r"calibration ρ at $\tau$=1"); ax.set_ylabel(r"calibration ρ at $\tau$=3")
ax.set_title("Ordinal calibration is τ-robust\n(each point = one arm; above line = τ=3 better)")
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "F5d_calibration_taurobust.png", dpi=160); plt.close(fig)

print("wrote F5a-F5d to", FIG)
