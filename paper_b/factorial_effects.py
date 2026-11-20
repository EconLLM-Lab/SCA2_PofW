#!/usr/bin/env python3
"""Factorial effect matrix (sign bit -> measured surface), diagonal dominance, bank robustness.

Each surface composite is regressed on the 64 factorial units with the probe's design
(`heldout/probe_select.design`: intercept, six main effects with x = +/-0.5, fifteen
two-way interactions; error df 42). A main-effect coefficient is the change in the
surface when one sign bit flips from negative to positive.

Diagonal dominance: a dimension "hits" when its own surface carries the largest
|main effect| in its row. Chance is 1/7 per row for one-surface dimensions (2/7 for
patience, which owns two surface columns); the binomial p uses 1/7, the conservative
side for the other five and slightly liberal for patience — stated here, not hidden.

Two noise yardsticks per cell: the OLS t (residual df 42) and Lenth's pseudo standard
error over the fifteen interaction coefficients of that surface (robust to a few
real interactions).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "heldout"))
import factorial as F  # noqa: E402
from probe_select import design  # noqa: E402

OWN_SURFACE = {"patience": "patience:Q43"}          # primary patience surface


def own_surface(dim: str) -> str:
    return OWN_SURFACE.get(dim, dim)


def _y(g: pd.DataFrame, surface: str) -> np.ndarray:
    units = F.all_units()
    order = {u: i for i, u in enumerate(units)}
    y = np.full(len(units), np.nan)
    for u, v in zip(g["unit"], g["composite"]):
        y[order[u]] = float(v)
    if np.isnan(y).any():
        raise ValueError(f"{surface}: missing units {[units[i] for i in np.where(np.isnan(y))[0]]}")
    return y


def lenth_pse(effects: np.ndarray) -> float:
    a = np.abs(np.asarray(effects, float))
    s0 = 1.5 * float(np.median(a))
    trimmed = a[a < 2.5 * s0] if s0 > 0 else a
    return 1.5 * float(np.median(trimmed)) if len(trimmed) else s0


def fit(composites: pd.DataFrame) -> pd.DataFrame:
    """Long frame: surface, dimension, beta, se, t, error_df, lenth_pse, t_lenth."""
    X, names = design()
    xtx_inv = np.linalg.inv(X.T @ X)
    df = X.shape[0] - X.shape[1]
    rows = []
    for surface, g in composites.groupby("surface", sort=True):
        y = _y(g, surface)
        beta = xtx_inv @ X.T @ y
        resid = y - X @ beta
        s2 = max(float(resid @ resid) / df, 1e-12)
        se = np.sqrt(s2 * np.diag(xtx_inv))
        pse = lenth_pse(beta[7:])
        for i, d in enumerate(F.DIMS):
            b = float(beta[1 + i])
            rows.append({"surface": surface, "dimension": d, "beta": b, "se": float(se[1 + i]),
                         "t": b / float(se[1 + i]), "error_df": df, "lenth_pse": pse,
                         "t_lenth": b / pse if pse > 0 else float("inf")})
    return pd.DataFrame(rows)


def effect_matrix(composites: pd.DataFrame) -> pd.DataFrame:
    """Rows = sign dimension (F.DIMS order), columns = surface, values = main effect."""
    f = fit(composites)
    m = f.pivot(index="dimension", columns="surface", values="beta")
    return m.loc[F.DIMS]


def diagonal_dominance(matrix: pd.DataFrame) -> dict:
    hits = []
    for dim in F.DIMS:
        col = own_surface(dim)
        if col not in matrix.columns:
            raise ValueError(f"surface column {col!r} missing")
        row = matrix.loc[dim].abs()
        if dim == "patience":                        # either patience surface counts as own
            own = max(row.get("patience:Q43", 0.0), row.get("patience:Q50", 0.0))
        else:
            own = row[col]
        hits.append(bool(own >= row.max() - 1e-12))
    k, n, p0 = sum(hits), len(hits), 1.0 / matrix.shape[1]
    p = sum(math.comb(n, j) * p0 ** j * (1 - p0) ** (n - j) for j in range(k, n + 1))
    return {"hits": k, "n": n, "share": k / n, "chance": p0, "p_binomial": p,
            "per_dimension": dict(zip(F.DIMS, hits))}


def bank_contract(bank1: pd.Series, bank2: pd.Series) -> dict:
    """Agreement of one surface composite between banks over the units both carry."""
    d = pd.concat([bank1.rename("bank1"), bank2.rename("bank2")], axis=1).dropna()
    ok = len(d) > 2
    return {"n_units": int(len(d)),
            "pearson": float(d.bank1.corr(d.bank2)) if ok else float("nan"),
            "spearman": float(d.bank1.corr(d.bank2, method="spearman")) if ok else float("nan"),
            "max_abs_diff": float((d.bank1 - d.bank2).abs().max()) if len(d) else float("nan")}
