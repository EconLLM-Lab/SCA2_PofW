#!/usr/bin/env python3
"""Paper A locked surface: 16x23 freeze + 42-country human map.

Does not call models. Recodes match Appendix C / 13_unified_comparison.recode_value.
Headline adapter-GPS trust on the 16x9 rectangle must equal 0.74.

Run: env -u PYTHONPATH .venv/bin/python paper_a/22_paper_a_surface.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "paper_a" / "outputs" / "paper_a"
# Optional source for re-freezing the scores: set SCA2_AUDIT_SCORES to country_item_scores.csv.
AUDIT_SCORES = Path(os.environ["SCA2_AUDIT_SCORES"]) if os.environ.get("SCA2_AUDIT_SCORES") else None
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
BINARY = {"Q57", "Q174"}  # 1 = mentioned / trust, 2 = no; Q174 as in 06_construct_bridge and 13_unified_comparison
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


def load_panel_trust_z() -> pd.Series:
    """Trust z for the 16-country panel. Public checkouts read the GPS download."""
    if GPS_JSON.is_file():
        z = json.loads(GPS_JSON.read_text())
        return pd.Series({c: float(z[c]["trust"]) for c in PANEL16})
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from sca2.gps_local import load_country_z

    z = load_country_z()
    return pd.Series({c: float(z[c]["trust"]) for c in PANEL16})


def load_gps() -> pd.DataFrame:
    gps = pd.read_stata(GPS_DTA).set_index("isocode")
    cols = ["trust", "patience", "risktaking", "posrecip", "negrecip", "altruism"]
    return gps[cols]


def human_item_means(items: list[str] | None = None) -> pd.DataFrame:
    items = list(items) if items is not None else ALL_MAPPED
    gps = load_gps()
    rows = []
    for f in sorted(WVS_DIR.glob("*_WVS_wave7.parquet")):
        cc = f.name.split("_")[0]
        if cc not in gps.index:
            continue
        available = set(pq.ParquetFile(f).schema.names)
        cols = ["W_WEIGHT"] + [q for q in items if q in available]
        if "W_WEIGHT" not in available:
            continue
        df = pd.read_parquet(f, columns=cols)
        w = df["W_WEIGHT"].fillna(0).astype(float)
        for it in items:
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


SCORING_BUNDLE = REPO / "paper_a" / "outputs" / "rung_mix" / "wvs_scoring_bundle.parquet"


def item_bounds(items: list[str]) -> dict[str, tuple[float, float]]:
    """Min and max of each item's recoded response options, from the tracked WVS scoring bundle."""
    b = pd.read_parquet(SCORING_BUNDLE, columns=["question_id", "option_value"]).dropna()
    out = {}
    for it in items:
        vals = [recode_value(float(v), it) for v in b.loc[b.question_id == it, "option_value"] if float(v) >= 0]
        out[it] = (min(vals), max(vals))
    return out


def human_score_rows(model: pd.DataFrame, him: pd.DataFrame) -> pd.DataFrame:
    """Human arm rows in the score-file schema, rebuilt from raw WVS (human_item_means).

    The committed score file holds model arms only (survey licence, 2026-11-03). For every (country, item) cell
    scored by the model arms, raw is the weighted recoded WVS mean and normalized rescales it to [0, 1] over the
    item's recoded response options. tvd is 0 by definition: the human arm is the reference.
    """
    cells = model[["country", "item", "dimension"]].drop_duplicates(["country", "item"])
    bounds = item_bounds(sorted(cells["item"].unique()))
    out = cells.merge(him.rename(columns={"mean": "raw"})[["country", "item", "raw"]], on=["country", "item"])
    out["normalized"] = [(r - bounds[i][0]) / (bounds[i][1] - bounds[i][0]) for i, r in zip(out["item"], out["raw"])]
    out.insert(0, "arm", "human")
    out["human_available"] = True
    out["tvd"] = 0.0
    return out[["arm", "country", "item", "dimension", "raw", "normalized", "human_available", "tvd"]]


def freeze_scores() -> pd.DataFrame:
    """Model-arm scores from git, plus human rows rebuilt locally from WVS when the extracts are present."""
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "country_item_scores.csv"
    if not dest.exists():
        if AUDIT_SCORES is None or not AUDIT_SCORES.exists():
            raise SystemExit(f"missing frozen Paper A scores: {dest} (and audit source {AUDIT_SCORES})")
        shutil.copy2(AUDIT_SCORES, dest)
    model = pd.read_csv(dest)
    model = model[model.arm != "human"]
    if "tvd" not in model.columns:  # public checkout: tvd is rebuilt locally (paper_a/tvd_rebuild.py, DATA.md)
        rebuilt = OUT / "country_item_scores_tvd.csv"
        if rebuilt.exists():
            model = model.merge(pd.read_csv(rebuilt), on=["arm", "country", "item"], how="left")
        else:
            print("tvd column absent and no rebuilt file; run paper_a/tvd_rebuild.py (see DATA.md) for model-to-human distances")
    human_file = OUT / "country_item_scores_human.csv"  # gitignored: derived from licensed WVS microdata
    if not human_file.exists():
        if not any(WVS_DIR.glob("*_WVS_wave7.parquet")) or not GPS_DTA.exists():
            return model
        him = human_item_means(sorted(model["item"].unique()))
        human_score_rows(model, him).to_csv(human_file, index=False)
    return pd.concat([model, pd.read_csv(human_file)], ignore_index=True)


def arm_composite(items: pd.DataFrame, arm: str, item_list: list[str], countries: list[str]) -> pd.Series:
    sub = items[(items.arm == arm) & (items.item.isin(item_list)) & (items.country.isin(countries))]
    sub = sub[np.isfinite(sub["raw"])]
    return sub.groupby("country")["raw"].mean().reindex(countries)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    items = freeze_scores()
    try:
        z16 = load_panel_trust_z()
    except FileNotFoundError as exc:
        print(exc)
        print("WVS/GPS extracts absent; adapter-GPS headline not recomputed (see DATA.md).")
        return

    adapter16 = arm_composite(items, "adapter", TRUST9, PANEL16)
    rho_a = spearman(adapter16, z16)
    if abs(rho_a - 0.74) > 5e-3:
        raise SystemExit(f"SURFACE MISMATCH: adapter-GPS trust={rho_a}, expected 0.74")
    if not (items.arm == "human").any():
        meta = {"adapter_gps_trust_16x9": rho_a, "human_gps_trust_16x9": None,
                "scores_sha256": sha256(OUT / "country_item_scores.csv"),
                "gps_json_sha256": sha256(GPS_JSON) if GPS_JSON.exists() else None}
        print("WVS/GPS extracts absent; human rows not rebuilt (see DATA.md). Adapter headline checked.")
        print("LOCK", json.dumps(meta, indent=2))
        return
    human16 = arm_composite(items, "human", TRUST9, PANEL16)
    rho_h = spearman(human16, z16)
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
