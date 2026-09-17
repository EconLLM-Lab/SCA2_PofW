#!/usr/bin/env python3
"""Paper A locked surface: 16x23 freeze + 42-country human map.

Does not call models. Recodes match Appendix C / 13_unified_comparison.recode_value.
Headline adapter-GPS trust on the 16x9 rectangle must equal 0.80.

Run: env -u PYTHONPATH .venv/bin/python analysis/phase2/22_paper_a_surface.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "phase2" / "outputs" / "paper_a"
AUDIT_SCORES = Path(
    "/Users/bonorinoa/Hermes/Projects/SCA2_results_audit/external/results/country_item_scores.csv"
)
WVS_DIR = REPO / "data" / "wvs_eval_full"
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
GPS_JSON = REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_all" / "gps_z_vectors.json"

PANEL16 = [
    "ARG", "BRA", "CHN", "DEU", "EGY", "GBR", "GRC", "IDN",
    "IND", "JPN", "MEX", "NGA", "NLD", "RUS", "TUR", "USA",
]
TRUST9 = ["Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"]
TRUST12 = TRUST9 + ["Q69", "Q70", "Q71"]
STRICT_ITEMS = {
    "trust": TRUST9,
    "patience": ["Q43", "Q50"],
    "risktaking": ["Q106", "Q107", "Q109", "Q178"],
    "posrecip": ["Q81"],
    "negrecip": ["Q176", "Q177", "Q179", "Q195"],
    "altruism": ["Q99", "Q101", "Q103"],
}
ALL_MAPPED = [q for qs in STRICT_ITEMS.values() for q in qs] + ["Q69", "Q70", "Q71"]
INVERT_1_4 = {
    "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71",
    "Q58", "Q60", "Q73", "Q81",
}
INVERT_10 = {"Q177", "Q179"}
BINARY = {"Q57"}
MIN_N = 50
BOOT = 2000
BOOT_SEED = 20260905


def recode_value(raw: float, item: str) -> float:
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in INVERT_10:
        return 11.0 - s
    if item in BINARY:
        return 1.0 if s == 1.0 else 0.0
    return s


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def spearman(a: pd.Series, b: pd.Series) -> float:
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(d) < 8 or d["a"].nunique() < 2 or d["b"].nunique() < 2:
        return float("nan")
    return float(spearmanr(d["a"], d["b"]).statistic)


def bootstrap_ci(a: pd.Series, b: pd.Series, seed: int = BOOT_SEED, reps: int = BOOT) -> tuple[float, float, float]:
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    n = len(d)
    if n < 8:
        return (float("nan"), float("nan"), float("nan"))
    x = d["a"].to_numpy()
    y = d["b"].to_numpy()
    rng = np.random.default_rng(seed)
    rhos = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(0, n, n)
        rhos[i] = spearmanr(x[idx], y[idx]).statistic
    point = float(spearmanr(x, y).statistic)
    return point, float(np.quantile(rhos, 0.025)), float(np.quantile(rhos, 0.975))


def load_gps() -> pd.DataFrame:
    gps = pd.read_stata(GPS_DTA).set_index("isocode")
    cols = ["trust", "patience", "risktaking", "posrecip", "negrecip", "altruism"]
    return gps[cols]


def human_item_means() -> pd.DataFrame:
    gps = load_gps()
    rows = []
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        if cc not in gps.index:
            continue
        available = set(pq.ParquetFile(f).schema.names)
        cols = ["W_WEIGHT"] + [q for q in ALL_MAPPED if q in available]
        if "W_WEIGHT" not in available:
            continue
        df = pd.read_parquet(f, columns=cols)
        w = df["W_WEIGHT"].fillna(0).astype(float)
        for it in ALL_MAPPED:
            if it not in df.columns:
                continue
            v = df[it].astype(float)
            mask = (v >= 0) & np.isfinite(v) & (w > 0)
            if int(mask.sum()) < MIN_N:
                continue
            rec = np.array([recode_value(float(x), it) for x in v[mask].to_numpy()])
            ww = w[mask].to_numpy()
            mean = float((rec * ww).sum() / ww.sum())
            rows.append({"country": cc, "item": it, "mean": mean, "n": int(mask.sum())})
    return pd.DataFrame(rows)


def composite(item_means: pd.DataFrame, items: list[str], complete: bool) -> pd.Series:
    sub = item_means[item_means.item.isin(items)]
    if complete:
        counts = sub.groupby("country")["item"].nunique()
        keep = counts[counts == len(items)].index
        sub = sub[sub.country.isin(keep)]
    return sub.groupby("country")["mean"].mean()


def freeze_scores() -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "country_item_scores.csv"
    if dest.exists():
        return pd.read_csv(dest)
    if AUDIT_SCORES.exists():
        shutil.copy2(AUDIT_SCORES, dest)
        return pd.read_csv(dest)
    raise SystemExit(
        f"missing frozen Paper A scores: {dest} (and audit source {AUDIT_SCORES})"
    )


def arm_composite(items: pd.DataFrame, arm: str, item_list: list[str], countries: list[str]) -> pd.Series:
    sub = items[(items.arm == arm) & (items.item.isin(item_list)) & (items.country.isin(countries))]
    sub = sub[np.isfinite(sub["raw"])]
    return sub.groupby("country")["raw"].mean().reindex(countries)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    items = freeze_scores()
    z = json.loads(GPS_JSON.read_text())
    z16 = pd.Series({c: float(z[c]["trust"]) for c in PANEL16})

    adapter16 = arm_composite(items, "adapter", TRUST9, PANEL16)
    human16 = arm_composite(items, "human", TRUST9, PANEL16)
    rho_a = spearman(adapter16, z16)
    rho_h = spearman(human16, z16)
    if abs(rho_a - 0.80) > 5e-3:
        raise SystemExit(f"SURFACE MISMATCH: adapter-GPS trust={rho_a}, expected 0.80")
    if abs(rho_h - 0.39) > 2e-2:
        raise SystemExit(f"SURFACE MISMATCH: human-GPS trust 16x9={rho_h}, expected ~0.39")

    meta = {
        "adapter_gps_trust_16x9": rho_a,
        "human_gps_trust_16x9": rho_h,
        "scores_sha256": sha256(OUT / "country_item_scores.csv"),
        "gps_json_sha256": sha256(GPS_JSON) if GPS_JSON.exists() else None,
    }

    if not any(WVS_DIR.glob("*_WVS_wave7.parquet")) or not GPS_DTA.exists():
        print("WVS/GPS extracts absent; skipping 42-country human map (locked 16x23 still written)")
        (OUT / "SURFACE_LOCK.json").write_text(json.dumps(meta, indent=2) + "\n")
        print("LOCK", json.dumps(meta, indent=2))
        return

    gps = load_gps()
    him = human_item_means()
    him.to_csv(OUT / "human_item_means_42.csv", index=False)

    rows = []
    # 16x9 from frozen scores (sanity)
    rows.append({
        "surface": "16x9_frozen_human",
        "n_countries": 16,
        "n_items": 9,
        "complete_items": True,
        "rho": rho_h,
        "ci_lo": np.nan,
        "ci_hi": np.nan,
    })
    rows.append({
        "surface": "16x9_frozen_adapter",
        "n_countries": 16,
        "n_items": 9,
        "complete_items": True,
        "rho": rho_a,
        "ci_lo": np.nan,
        "ci_hi": np.nan,
    })

    specs = [
        ("42x9_complete", TRUST9, True),
        ("42x9_available", TRUST9, False),
        ("q69q71_complete", ["Q69", "Q70", "Q71"], True),
        ("12item_complete", TRUST12, True),
    ]
    for name, item_list, complete in specs:
        s = composite(him, item_list, complete=complete)
        z = gps["trust"].reindex(s.index)
        point, lo, hi = bootstrap_ci(s, z)
        rows.append({
            "surface": name,
            "n_countries": int(pd.concat([s, z], axis=1).dropna().shape[0]),
            "n_items": len(item_list),
            "complete_items": complete,
            "rho": point,
            "ci_lo": lo,
            "ci_hi": hi,
        })

    # Other Table-2 dimensions, 42-country complete-item composites
    for dim, qs in STRICT_ITEMS.items():
        if dim == "trust":
            continue
        if dim == "patience":
            for q in qs:
                s = composite(him, [q], complete=True)
                z = gps["patience"].reindex(s.index)
                point, lo, hi = bootstrap_ci(s, z)
                rows.append({
                    "surface": f"42_{q}",
                    "n_countries": int(pd.concat([s, z], axis=1).dropna().shape[0]),
                    "n_items": 1,
                    "complete_items": True,
                    "rho": point,
                    "ci_lo": lo,
                    "ci_hi": hi,
                })
            continue
        s = composite(him, qs, complete=True)
        z = gps[dim].reindex(s.index)
        point, lo, hi = bootstrap_ci(s, z)
        rows.append({
            "surface": f"42_{dim}_complete",
            "n_countries": int(pd.concat([s, z], axis=1).dropna().shape[0]),
            "n_items": len(qs),
            "complete_items": True,
            "rho": point,
            "ci_lo": lo,
            "ci_hi": hi,
        })

    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "human_gps_map.csv", index=False)

    tex_lines = [
        r"\begin{table}[htbp]\centering\small",
        r"\caption{Human--GPS country-rank associations on the Paper~A item map. "
        r"The sixteen-country rectangle is the matched evaluation panel. "
        r"The forty-two-country rows use the same recodes and require at least fifty valid weighted responses per item. "
        r"Complete-item rows retain only countries observed on every listed item. "
        r"Intervals are 95\% country bootstrap (2,000 draws) on the human panel; they omit GPS measurement error.}",
        r"\label{tab:human42}",
        r"\begin{tabular}{lccc}\toprule",
        r"Surface & $n$ & $\rho$ & Interval\\\midrule",
    ]
    labels = {
        "42x9_complete": "42 countries, 9 trust items (complete)",
        "q69q71_complete": "Q69--Q71 only (complete)",
        "12item_complete": "12 trust items including Q69--Q71 (complete)",
        "42_Q43": "Q43 vs GPS patience",
        "42_Q50": "Q50 vs GPS patience",
        "42_risktaking_complete": "Risk-taking map (complete)",
        "42_posrecip_complete": "Positive reciprocity Q81 (complete)",
        "42_negrecip_complete": "Negative reciprocity map (complete)",
        "42_altruism_complete": "Altruism map (complete)",
    }
    for r in tab.itertuples(index=False):
        if r.surface not in labels:
            continue
        if np.isfinite(r.ci_lo):
            interval = f"[{r.ci_lo:.2f}, {r.ci_hi:.2f}]"
        else:
            interval = "---"
        tex_lines.append(
            f"{labels[r.surface]} & {int(r.n_countries)} & {r.rho:.2f} & {interval} \\\\"
        )
    tex_lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    (OUT / "human_gps_map.tex").write_text("\n".join(tex_lines) + "\n")

    meta = {
        "adapter_gps_trust_16x9": rho_a,
        "human_gps_trust_16x9": rho_h,
        "scores_sha256": sha256(OUT / "country_item_scores.csv"),
        "gps_json_sha256": sha256(GPS_JSON) if GPS_JSON.exists() else None,
    }
    (OUT / "SURFACE_LOCK.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(tab.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("LOCK", json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
