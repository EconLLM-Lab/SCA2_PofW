#!/usr/bin/env python3
"""Supplementary views of the 2^6 factorial on the strict battery, beside the plan's V5 check.

The plan's V5 rule (analyze_factorial.py -> mtmm_summary.json) is row-wise diagonal dominance on raw
main effects: for each sign bit, is its own surface the largest |effect| in the row? That compares
effects across surfaces whose response scales differ (10-point vs 4-point items), so this script adds
two scale-free views and the diagonal itself. None of them replaces V5; all are labelled.

  column-wise dominance  for each surface, is its own bit the largest |effect| among the six bits?
                         (one surface, one unit of measure: scale-free by construction)
  standardized rows      row-wise dominance on effects divided by the surface's SD over the 64 units
  diagonal               own effect, its OLS t (df 42) and Lenth t, sign
  general factor         share of variance of the first principal component of the 64 x 7 standardized
                         composites (how much one common direction explains)
  route contrast         EXPLORATORY: the strict-battery sign-prompt cell has only the 26 cohort sign
                         profiles, so both routes are refit on those 26 cells, main effects only
                         (intercept + 6 bits, df 19), and compared on the same footing.
  route contrast (64)    the same two routes on the full 64-cell sign-prompt run, each fitted with the
                         full 2^6 design (intercept + 6 main effects + 15 two-way interactions,
                         factorial_effects.fit, error df 42) -> route_contrast_64_cells.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "heldout"))
import analyze_factorial as AF  # noqa: E402
import factorial as F  # noqa: E402
import factorial_effects as FE  # noqa: E402

OWN = {"trust": ["trust"], "risktaking": ["risktaking"], "patience": ["patience:Q43", "patience:Q50"],
       "altruism": ["altruism"], "posrecip": ["posrecip"], "negrecip": ["negrecip"]}
SURF_OWNER = {s: d for d, ss in OWN.items() for s in ss}


def wide(comp: pd.DataFrame) -> pd.DataFrame:
    return comp.pivot(index="unit", columns="surface", values="composite")


def column_dominance(m: pd.DataFrame) -> dict:
    hits = {s: bool(abs(m.loc[SURF_OWNER[s], s]) >= m[s].abs().max() - 1e-12) for s in m.columns}
    top = {s: m[s].abs().idxmax() for s in m.columns}
    return {"hits": int(sum(hits.values())), "n": len(hits), "chance": 1 / 6,
            "per_surface": hits, "largest_bit": top}


def row_dominance(m: pd.DataFrame) -> dict:
    hits = {}
    for d in F.DIMS:
        own = max(abs(m.loc[d, s]) for s in OWN[d])
        hits[d] = bool(own >= m.loc[d].abs().max() - 1e-12)
    return {"hits": int(sum(hits.values())), "n": 6, "per_dimension": hits,
            "largest_surface": {d: m.loc[d].abs().idxmax() for d in F.DIMS}}


def main_effects_fit(w: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Intercept + six bits (x = +-0.5), OLS on whichever units are present."""
    X = np.column_stack([np.ones(len(w))] + [np.array([F.bits_of_unit(u)[i] for u in w.index]) - 0.5
                                              for i in range(6)])
    beta, *_ = np.linalg.lstsq(X, w.to_numpy(float), rcond=None)
    df = len(w) - X.shape[1]
    resid = w.to_numpy(float) - X @ beta
    s2 = (resid ** 2).sum(axis=0) / df
    se = np.sqrt(np.outer(np.diag(np.linalg.inv(X.T @ X)), s2))
    b = pd.DataFrame(beta[1:], index=F.DIMS, columns=w.columns)
    t = pd.DataFrame(beta[1:] / se[1:], index=F.DIMS, columns=w.columns)
    return b, t


def diag(b: pd.DataFrame, t: pd.DataFrame, tl: pd.DataFrame | None = None,
         with_sign: bool = False) -> dict:
    out = {}
    for s, d in SURF_OWNER.items():
        if s in b.columns:
            out[s] = {"bit": d, "beta": float(b.loc[d, s]), "t": float(t.loc[d, s])}
            if tl is not None:
                out[s]["t_lenth"] = float(tl.loc[d, s])
            if with_sign:
                out[s]["sign"] = int(np.sign(b.loc[d, s]))
    return out


def general_factor(w: pd.DataFrame) -> dict:
    z = (w - w.mean()) / w.std(ddof=1)
    ev = np.linalg.eigvalsh(np.corrcoef(z.to_numpy(float), rowvar=False))[::-1]
    r = np.corrcoef(z.to_numpy(float), rowvar=False)
    off = r[~np.eye(len(r), dtype=bool)]
    return {"pc1_share": float(ev[0] / ev.sum()), "pc2_share": float(ev[1] / ev.sum()),
            "mean_abs_inter_surface_r": float(np.abs(off).mean())}


def signprompt_units(path, unit_col: str = "profile_id") -> pd.DataFrame:
    """A sign-prompt option-probability file -> composites frame keyed by the unit code.

    The 26-profile cell wrote profile_id "0_0_0_0_0_0"; the 64-cell run writes "P_0_0_0_0_0_0".
    Both normalise to the unit code P_<bits>, so eval_country is never P_P_...
    """
    sp = pd.read_csv(path, dtype={"option_code": str, "question_id": str})
    sp = sp.assign(eval_country="P_" + sp[unit_col].astype(str).str.removeprefix("P_"))
    return AF.unit_composites(sp)


def route_contrast_64(adapter_comp: pd.DataFrame, signprompt_comp: pd.DataFrame,
                      results_dir) -> dict:
    """Both routes on the 64-cell sign-prompt run, full 2^6 design (FE.fit, error df 42).

    Same views as route_contrast_26_cells: the plan's V5 row-wise own-surface dominance on the raw
    main effects, the same on rows standardized by the surface's SD over the 64 units, column-wise
    dominance, the diagonal with the OLS t and the Lenth t plus the sign of every own effect, and the
    share of the first principal component.
    """
    R = Path(results_dir)
    out = {"n_cells": 64,
           "note": "full 2^6 design (intercept + six main effects + fifteen two-way interactions, "
                   "factorial_effects.fit, error df 42); same views as route_contrast_26_cells"}
    for name, comp in (("adapter", adapter_comp), ("signprompt", signprompt_comp)):
        comp = comp[comp.unit.isin(F.all_units())]
        w = wide(comp)
        if len(w) != 64:
            raise SystemExit(f"{name}: expected 64 units, got {len(w)}")
        m = FE.effect_matrix(comp)
        cells = FE.fit(comp)
        t = cells.pivot(index="dimension", columns="surface", values="t").loc[F.DIMS]
        tl = cells.pivot(index="dimension", columns="surface", values="t_lenth").loc[F.DIMS]
        sd = w.std(ddof=1)
        out[name] = {
            "plan_V5_rowwise_raw": FE.diagonal_dominance(m),
            "rowwise_standardized": row_dominance(m / sd),
            "columnwise": column_dominance(m),
            "diagonal": diag(m, t, tl, with_sign=True),
            "general_factor": general_factor(w),
            "surface_sd_over_units": sd.to_dict(),
        }
        (m / sd).to_csv(R / f"route64_{name}_standardized.csv")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--signprompt-strict", required=True, help="26-profile C1 cell, profile_id column")
    ap.add_argument("--signprompt-strict-64", default=None,
                    help="64-cell strict sign-prompt run, profile_id column (P_<bits>)")
    ap.add_argument("--results", required=True, help="dir holding analyze_factorial.py outputs")
    a = ap.parse_args()
    R = Path(a.results)
    comp = AF.unit_composites(pd.read_csv(a.adapter, dtype={"option_code": str}))
    comp = comp[comp.unit.isin(F.all_units())]
    w = wide(comp)
    if len(w) != 64:
        raise SystemExit(f"expected 64 units, got {len(w)}")
    m = FE.effect_matrix(comp)
    cells = FE.fit(comp)
    t = cells.pivot(index="dimension", columns="surface", values="t").loc[F.DIMS]
    tl = cells.pivot(index="dimension", columns="surface", values="t_lenth").loc[F.DIMS]
    sd = w.std(ddof=1)
    out = {
        "plan_V5_rowwise_raw": json.loads((R / "mtmm_summary.json").read_text())["adapter"],
        "rowwise_standardized": row_dominance(m / sd),
        "columnwise": column_dominance(m),
        "diagonal": diag(m, t, tl),
        "general_factor": general_factor(w),
        "surface_sd_over_units": sd.to_dict(),
    }
    (m / sd).to_csv(R / "mtmm_adapter_standardized.csv")

    sp = pd.read_csv(a.signprompt_strict, dtype={"option_code": str})
    sp = sp.assign(eval_country="P_" + sp.profile_id.astype(str))
    spc = AF.unit_composites(sp)
    sw = wide(spc)
    shared = sorted(set(sw.index) & set(w.index))
    rc = {"n_cells": len(shared), "note": "main effects only, df 19; standardized by each route's own SD over the shared cells"}
    for name, ww in (("adapter", w.loc[shared]), ("signprompt", sw.loc[shared, w.columns])):
        b, tt = main_effects_fit(ww)
        bs = b / ww.std(ddof=1)
        rc[name] = {"columnwise": column_dominance(bs), "rowwise_standardized": row_dominance(bs),
                    "diagonal": diag(bs, tt), "general_factor": general_factor(ww)}
        bs.to_csv(R / f"route26_{name}_standardized.csv")
    out["route_contrast_26_cells"] = rc
    if a.signprompt_strict_64:
        out["route_contrast_64_cells"] = route_contrast_64(comp, signprompt_units(a.signprompt_strict_64), R)
    (R / "factorial_report.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
