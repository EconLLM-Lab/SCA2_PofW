#!/usr/bin/env python3
"""The preregistered probe: held-out item -> GPS dimension, from the 2^6 factorial.

Model per item: y(unit) = b0 + sum_d b_d x_d + sum_{d<e} b_de x_d x_e + e, with
x_d = +/-0.5, so b_d is the effect of flipping sign bit d. OLS on all 64 units
(error df = 64 - 22 = 42). y is a model-only composite (adapter expected code);
everything here runs BEFORE any held-out human value is read.

Rules (direction-free: item code direction is arbitrary, so |t| is used):
  top_dimension  argmax_d |t_d|, or "none" when max |t_d| < T_FLOOR
  PRIMARY        among items whose top dimension is in IMPRINT and |t_top| >= T_FLOOR,
                 the TOP_SHARE of all scored items by |t_top|
  SECONDARY      top dimension in IMPRINT and |t_top| >= t_crit (reliability check)
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "paper_b"))
import factorial as F  # noqa: E402

IMPRINT = ("trust", "risktaking", "posrecip", "altruism")
T_FLOOR = 2.0
TOP_SHARE = 0.25


def design() -> tuple[np.ndarray, list[str]]:
    units = F.all_units()
    x = np.array([[0.5 if b else -0.5 for b in F.bits_of_unit(u)] for u in units], float)
    names = ["intercept"] + list(F.DIMS)
    cols = [np.ones(len(units))] + [x[:, i] for i in range(6)]
    for i, j in itertools.combinations(range(6), 2):
        cols.append(x[:, i] * x[:, j])
        names.append(f"{F.DIMS[i]}:{F.DIMS[j]}")
    return np.column_stack(cols), names


def effects(values: pd.DataFrame) -> pd.DataFrame:
    """values: columns unit, item, value (one row per unit x item)."""
    X, _ = design()
    units = F.all_units()
    order = {u: i for i, u in enumerate(units)}
    xtx_inv = np.linalg.inv(X.T @ X)
    rows = []
    for item, g in values.groupby("item", sort=True):
        y = np.full(len(units), np.nan)
        for u, v in zip(g["unit"], g["value"]):
            y[order[u]] = float(v)
        if np.isnan(y).any():
            raise ValueError(f"{item}: missing units {[units[i] for i in np.where(np.isnan(y))[0]]}")
        beta = xtx_inv @ X.T @ y
        resid = y - X @ beta
        df = len(units) - X.shape[1]
        s2 = max(float(resid @ resid) / df, 1e-12)
        se = np.sqrt(s2 * np.diag(xtx_inv))
        t = {F.DIMS[i]: float(beta[1 + i] / se[1 + i]) for i in range(6)}
        top = max(t, key=lambda d: abs(t[d]))
        rows.append({
            "question_id": str(item), "error_df": df, "sigma": float(np.sqrt(s2)),
            **{f"b_{d}": float(beta[1 + i]) for i, d in enumerate(F.DIMS)},
            **{f"t_{d}": t[d] for d in F.DIMS},
            "top_dimension": top if abs(t[top]) >= T_FLOOR else "none",
            "t_top": t[top],
        })
    return pd.DataFrame(rows).sort_values("question_id").reset_index(drop=True)


def _eligible(df: pd.DataFrame, imprint, t_min: float) -> pd.Series:
    return df["top_dimension"].isin(imprint) & (df["t_top"].abs() >= t_min)


def dichotomize(df: pd.DataFrame, *, top_share: float = TOP_SHARE,
                imprint=IMPRINT) -> pd.Series:
    """PRIMARY rule -> boolean mask aligned with df."""
    cut = max(1, int(np.ceil(top_share * len(df))))
    elig = _eligible(df, imprint, T_FLOOR)
    ranked = df.loc[elig, "t_top"].abs().sort_values(ascending=False, kind="mergesort")
    keep = set(ranked.index[:cut])
    return pd.Series([i in keep for i in df.index], index=df.index)


def select(df: pd.DataFrame, imprint=IMPRINT, t_crit: float = T_FLOOR) -> list[str]:
    """SECONDARY rule: fixed |t| threshold."""
    return sorted(df.loc[_eligible(df, imprint, t_crit), "question_id"].astype(str))


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="probe selection (model-only)")
    ap.add_argument("--items", required=True, help="CSV: unit,item,value (model composites)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--t-crit", type=float, default=T_FLOOR)
    a = ap.parse_args()
    df = effects(pd.read_csv(a.items))
    df["primary_selected"] = dichotomize(df)
    df["secondary_selected"] = df.question_id.isin(select(df, t_crit=a.t_crit))
    Path(a.out).write_text(df.to_csv(index=False))
    print(f"items {len(df)} | primary {int(df.primary_selected.sum())} "
          f"| secondary {int(df.secondary_selected.sum())} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
