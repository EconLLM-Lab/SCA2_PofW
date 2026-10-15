#!/usr/bin/env python3
"""Paper B analysis-phase checks on the banked 2026-10-11 surface.

CPU only. No new scoring. Surfaces match the three-column table: patience
items stay unpooled. Variance shares are sums of squares. The all-country
share counts singletons as pure between-profile variance; the multi-member
share is the informative one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_surface as A  # noqa: E402

SURFACES = {
    "trust": A.TRUST9,
    "patience:Q43": ["Q43"],
    "patience:Q50": ["Q50"],
    "risktaking": A.RISK_ITEMS,
    "posrecip": A.POSRECIP_ITEMS,
    "negrecip": A.NEGRECIP_ITEMS,
    "altruism": A.ALTRUISM_ITEMS,
}
PROF_DIMS = ["altruism", "negrecip", "patience", "posrecip", "risktaking", "trust"]
BOUND_TOL = 1e-4


def item_bounds(item: str) -> tuple[float, float]:
    values = [A.recode_value(float(c), item) for c in A._domain(item)]
    return min(values), max(values)


def composite_bounds(items: list[str]) -> tuple[float, float]:
    bounds = [item_bounds(q) for q in items]
    return float(np.mean([b[0] for b in bounds])), float(np.mean([b[1] for b in bounds]))


def surface_values(items: pd.DataFrame, model: str, surface: str,
                   questions: list[str]) -> pd.Series:
    sub = items[(items.model == model) & (items.item.isin(questions))]
    rows = []
    for cc, g in sub.groupby("country"):
        if g.item.nunique() != len(questions):
            continue
        rows.append((cc, float(g.e_recode.mean())))
    return pd.Series(dict(rows), name=surface).sort_index()


def human_surface(human: pd.DataFrame, questions: list[str]) -> pd.Series:
    sub = human[human.item.isin(questions)]
    rows = []
    for cc, g in sub.groupby("country"):
        if g.item.nunique() != len(questions):
            continue
        rows.append((cc, float(g["mean"].mean())))
    return pd.Series(dict(rows), name="human").sort_index()


def variance_share(values: pd.Series, profiles: pd.DataFrame) -> dict:
    d = values.rename("y").to_frame().join(profiles.set_index("country"))
    if d.profile_id.isna().any():
        missing = sorted(d.index[d.profile_id.isna()])
        raise ValueError(f"profile missing for {missing}")
    y = d.y.to_numpy(float)
    total = float(((y - y.mean()) ** 2).sum())
    within = 0.0
    between = 0.0
    for _, g in d.groupby("profile_id"):
        mu = float(g.y.mean())
        within += float(((g.y - mu) ** 2).sum())
        between += len(g) * (mu - float(y.mean())) ** 2
    multi = d.groupby("profile_id").filter(lambda g: len(g) > 1)
    my = multi.y.to_numpy(float)
    mtotal = float(((my - my.mean()) ** 2).sum()) if len(my) else float("nan")
    mwithin = 0.0
    if len(multi):
        for _, g in multi.groupby("profile_id"):
            mwithin += float(((g.y - g.y.mean()) ** 2).sum())
    return {
        "n_countries": int(len(d)),
        "n_profiles": int(d.profile_id.nunique()),
        "n_multi_member_profiles": int((d.groupby("profile_id").size() > 1).sum()),
        "ss_total": total,
        "between_share_all": between / total if total > 0 else float("nan"),
        "within_share_all": within / total if total > 0 else float("nan"),
        "between_share_multi_member": (
            1.0 - mwithin / mtotal if mtotal and mtotal > 0 else float("nan")),
        "within_share_multi_member": (
            mwithin / mtotal if mtotal and mtotal > 0 else float("nan")),
        "within_sd_median_multi": float(
            multi.groupby("profile_id").y.std(ddof=0).median()) if len(multi) else float("nan"),
    }


def at_bound(value: float, lo: float, hi: float) -> str:
    if abs(value - hi) <= BOUND_TOL:
        return "ceiling"
    if abs(value - lo) <= BOUND_TOL:
        return "floor"
    return ""


def main() -> int:
    root = Path("/Users/bonorinoa/Hermes/Projects/SCA2/sprint_2026-10-11/paper-b-20261011")
    out = root / "analysis_phase"
    out.mkdir(parents=True, exist_ok=True)
    probs = pd.read_csv(root / "model_probs.csv", dtype={"option_code": str, "question_id": str})
    human = A.load_human_means(A.DEFAULT_HUMAN_MEANS)
    z = A.load_gps_z(A.DEFAULT_GPS_JSON)
    items = A.model_item_table(probs)
    countries = sorted(set(items.country) & set(human.country))
    profiles = A.sign_profiles(z, countries, PROF_DIMS)
    gps = z.pivot(index="country", columns="dimension", values="z")
    prof_idx = profiles.set_index("country").profile_id

    var_rows = []
    ceil_rows = []
    base_rows = []
    for surface, questions in SURFACES.items():
        for arm, series in (
            ("adapter", surface_values(items, "adapter", surface, questions)),
            ("human", human_surface(human, questions)),
        ):
            share = variance_share(series, profiles)
            share.update({"arm": arm, "surface": surface})
            var_rows.append(share)
        lo, hi = composite_bounds(questions)
        adapter = surface_values(items, "adapter", surface, questions)
        for cc, value in adapter.items():
            where = at_bound(float(value), lo, hi)
            if where:
                ceil_rows.append({
                    "surface": surface, "country": cc, "composite": float(value),
                    "bound": where, "floor": lo, "ceiling": hi,
                    "profile_id": prof_idx.loc[cc],
                })
        humans = human_surface(human, questions)
        base = surface_values(items, "base", surface, questions)
        joined = pd.DataFrame({
            "adapter": adapter, "base": base, "human": humans,
        }).dropna()
        joined["adapter_abs"] = (joined.adapter - joined.human).abs()
        joined["base_abs"] = (joined.base - joined.human).abs()
        joined["adapter_minus_base"] = joined.adapter_abs - joined.base_abs
        base_rows.append({
            "surface": surface,
            "n": int(len(joined)),
            "mean_adapter_minus_base": float(joined.adapter_minus_base.mean()),
            "share_adapter_closer": float((joined.adapter_minus_base < 0).mean()),
            "median_adapter_minus_base": float(joined.adapter_minus_base.median()),
        })

    item_rows = []
    for q in A.NEGRECIP_ITEMS:
        s = items[(items.model == "adapter") & (items.item == q)].set_index("country").e_recode
        target = gps["negrecip"].reindex(s.index)
        r = A.bootstrap_spearman(s, target, clusters=prof_idx.reindex(s.index),
                                 draws=A.BOOT_DRAWS, seed=A.BOOT_SEED)
        item_rows.append({"item": q, "column": "adapter-GPS", **r})

    risk_all = surface_values(items, "adapter", "risktaking", A.RISK_ITEMS)
    risk_drop = risk_all.drop(labels=["JOR"], errors="ignore")
    risk_target = gps["risktaking"]
    risk_rows = []
    for label, series in (("with_JOR", risk_all), ("without_JOR", risk_drop)):
        r = A.bootstrap_spearman(
            series, risk_target.reindex(series.index),
            clusters=prof_idx.reindex(series.index),
            draws=A.BOOT_DRAWS, seed=A.BOOT_SEED)
        risk_rows.append({"sample": label, **r})

    var = pd.DataFrame(var_rows)
    ceil = pd.DataFrame(ceil_rows)
    base = pd.DataFrame(base_rows)
    neg = pd.DataFrame(item_rows)
    risk = pd.DataFrame(risk_rows)
    var.to_csv(out / "variance_shares.csv", index=False)
    ceil.to_csv(out / "ceiling_hits.csv", index=False)
    base.to_csv(out / "base_contrast_by_surface.csv", index=False)
    neg.to_csv(out / "negrecip_items.csv", index=False)
    risk.to_csv(out / "risk_jor_sensitivity.csv", index=False)
    summary = {
        "bound_tolerance": BOUND_TOL,
        "n_ceiling_or_floor_hits": int(len(ceil)),
        "surfaces": list(SURFACES),
        "note": "between_share_all counts singleton profiles as between variance; "
                "between_share_multi_member drops them.",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("VARIANCE")
    print(var.to_string(index=False))
    print("CEILING", len(ceil))
    if len(ceil):
        print(ceil.groupby(["surface", "bound"]).size().to_string())
    print("BASE")
    print(base.to_string(index=False))
    print("NEGRECIP")
    print(neg.to_string(index=False))
    print("RISK")
    print(risk.to_string(index=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
