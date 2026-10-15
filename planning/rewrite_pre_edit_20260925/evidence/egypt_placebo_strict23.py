#!/usr/bin/env python3
"""CPU-only Egypt paired check and 16x23 assignment placebo.

Reads frozen country-item scores from the September 2026 external audit.
Does not call models. Headline adapter-GPS trust on the primary 16x9 surface
must equal 0.80 before any table is written.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

AUDIT = Path("/Users/bonorinoa/Hermes/Projects/SCA2_results_audit/external/results")
GPS_Z = Path(
    "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/"
    "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"
)
OUT = Path("/Users/bonorinoa/Downloads/position_paper_sca2_latex")
EVIDENCE = OUT / "evidence"
TABLES = OUT / "tables"

TRUST9 = ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]
TRUST12 = TRUST9 + ["Q69", "Q70", "Q71"]
PANEL16 = [
    "ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
    "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA",
]
PANEL15 = [c for c in PANEL16 if c != "EGY"]
SEED = 20260820
N_PERM = 1000
# GPS order used in Appendix A Argentina metadata.
SIGN_ORDER = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
SIGN_LABEL = {
    "trust": "trust",
    "risktaking": "risk",
    "patience": "patience",
    "altruism": "altruism",
    "posrecip": "pos.\\ recip.",
    "negrecip": "neg.\\ recip.",
}


def composite(items: pd.DataFrame, countries: list[str], item_list: list[str], arm: str) -> pd.Series:
    sub = items[(items.arm == arm) & (items.item.isin(item_list)) & (items.country.isin(countries))]
    sub = sub[np.isfinite(sub["raw"])]
    means = sub.groupby("country")["raw"].mean()
    return means.reindex(countries)


def spearman(scores: pd.Series, gps: pd.Series) -> float:
    aligned = pd.concat([scores.rename("s"), gps.rename("z")], axis=1).dropna()
    r, _ = spearmanr(aligned["s"], aligned["z"])
    return float(r)


def fmt_rho(x: float) -> str:
    return f"{x:.2f}"


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    items = pd.read_csv(AUDIT / "country_item_scores.csv")
    z = json.loads(GPS_Z.read_text())
    gps_trust = pd.Series({c: float(z[c]["trust"]) for c in PANEL16})

    specs = [
        ("primary_16x9", "16 countries, 9 trust items", PANEL16, TRUST9),
        ("drop_egy_15x9", "15 countries (Egypt omitted), 9 items", PANEL15, TRUST9),
        ("restore_q69_15x12", "15 countries, 12 items (Q69--Q71 restored)", PANEL15, TRUST12),
    ]
    rows = []
    for key, label, countries, item_list in specs:
        adapter = composite(items, countries, item_list, "adapter")
        human = composite(items, countries, item_list, "human")
        assert adapter.notna().all() and human.notna().all(), (key, adapter, human)
        rows.append(
            {
                "key": key,
                "label": label,
                "n_countries": len(countries),
                "n_items": len(item_list),
                "adapter_gps": spearman(adapter, gps_trust),
                "human_gps": spearman(human, gps_trust),
            }
        )
    tab = pd.DataFrame(rows)
    primary = float(tab.loc[tab.key == "primary_16x9", "adapter_gps"].iloc[0])
    if abs(primary - 0.80) > 5e-4:
        raise SystemExit(f"SURFACE MISMATCH: primary adapter-GPS trust is {primary}, expected 0.80")

    tab.to_csv(EVIDENCE / "egypt_q69_paired.csv", index=False)

    tex_rows = "\n".join(
        f"{r.label} & {fmt_rho(r.adapter_gps)} & {fmt_rho(r.human_gps)} \\\\"
        for r in tab.itertuples(index=False)
    )
    (TABLES / "egypt_robustness.tex").write_text(
        "\\begin{table}[htbp]\\centering\\small\n"
        "\\caption{Paired missingness check for Egypt and Q69--Q71. "
        "Entries are Spearman correlations between country trust composites and GPS trust $z$. "
        "The primary panel retains Egypt and omits Q69--Q71 everywhere because those items were not asked in Egypt. "
        "Adapters were not refit.}\\label{tab:egypt}\n"
        "\\begin{tabular}{lcc}\\toprule\n"
        "Surface & Adapter--GPS & Human--GPS \\\\\\midrule\n"
        f"{tex_rows}\n"
        "\\bottomrule\n"
        "\\end{tabular}\\end{table}\n"
    )

    # Assignment placebo on the paper surface (adapters not refit).
    adapter16 = composite(items, PANEL16, TRUST9, "adapter")
    real = spearman(adapter16, gps_trust)
    if abs(real - 0.80) > 5e-4:
        raise SystemExit(f"PLACEBO SURFACE MISMATCH: real rho={real}")

    rng = np.random.default_rng(SEED)
    z_vals = gps_trust.reindex(PANEL16).to_numpy()
    s_vals = adapter16.reindex(PANEL16).to_numpy()
    null = np.empty(N_PERM)
    for i in range(N_PERM):
        perm = rng.permutation(z_vals)
        null[i] = spearmanr(s_vals, perm).statistic
    p = float((np.sum(null >= real) + 1) / (N_PERM + 1))
    report = (
        "# PLACEBO STRICT 16x23 (assignment, adapters not refit)\n"
        f"Seed: {SEED}\n"
        f"N: {N_PERM}\n"
        "Surface: strict 16-country, 9 trust items (Q57--Q64, Q73). No Q69--Q71.\n"
        "Null: permute the 16 observed GPS trust z values across the 16 frozen adapter composites, without replacement.\n"
        "Adapters were not refit. This is not a sign-retrain test.\n"
        f"Real adapter-GPS trust rho: {real:.6f}\n"
        f"Null median: {float(np.median(null)):.6f}\n"
        f"Null q95: {float(np.quantile(null, 0.95)):.6f}\n"
        f"One-sided p (real >= null, plus-one): {p:.4f}\n"
    )
    (EVIDENCE / "PLACEBO_STRICT23.md").write_text(report)
    np.save(EVIDENCE / "placebo_strict23_null.npy", null)

    # Sign-profile table in Appendix-A GPS order.
    signs = pd.read_csv(
        "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/analysis/phase2/outputs/gps_sign_vectors_16.csv",
        index_col=0,
    )
    # csv columns: patience,risktaking,posrecip,negrecip,altruism,trust with +/-1
    colmap = {
        "trust": "trust",
        "risktaking": "risktaking",
        "patience": "patience",
        "altruism": "altruism",
        "posrecip": "posrecip",
        "negrecip": "negrecip",
    }
    recs = []
    for c in PANEL16:
        vec = tuple(int(signs.loc[c, colmap[k]] > 0) for k in SIGN_ORDER)
        recs.append((c, vec))
    from collections import defaultdict

    groups: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for c, vec in recs:
        groups[vec].append(c)
    assert len(groups) == 13, len(groups)

    def pm(bit: int) -> str:
        return "$+$" if bit else "$-$"

    body = []
    for vec, members in sorted(groups.items(), key=lambda kv: (len(kv[1]) == 1, kv[1][0])):
        bits = " & ".join(pm(b) for b in vec)
        body.append(f"{', '.join(members)} & {bits} \\\\")
    header = " & ".join(SIGN_LABEL[k] for k in SIGN_ORDER)
    (TABLES / "sign_profiles.tex").write_text(
        "\\begin{table}[htbp]\\centering\\small\n"
        "\\caption{Thirteen distinct GPS sign profiles among the sixteen adapter countries. "
        "Coordinates are ordered trust, risk taking, patience, altruism, positive reciprocity, and negative reciprocity, "
        "matching Appendix~\\ref{app:protocol}. "
        "The United States is non-negative on every coordinate; Mexico and Russia are negative on every coordinate. "
        "Identical sign vectors induce identical labels on the shared bank.}\\label{tab:signprofiles}\n"
        "\\begin{tabular}{lcccccc}\\toprule\n"
        f"Members & {header} \\\\\\midrule\n"
        + "\n".join(body)
        + "\n\\bottomrule\n"
        "\\end{tabular}\\end{table}\n"
    )
    print(tab.to_string(index=False))
    print(report)
    print("wrote", EVIDENCE, TABLES / "egypt_robustness.tex", TABLES / "sign_profiles.tex")


if __name__ == "__main__":
    main()
