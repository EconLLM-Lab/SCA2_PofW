#!/usr/bin/env python3
"""The preregistered held-out screen test (PREREGISTRATION.md sections 1 and 4).

Inputs
  selection  question_id, top_dimension, sign (+1/-1 from the probe), primary_selected
  human      country x item frame of weighted WVS-7 country means (raw codes; never
             recoded), read only through `load_heldout_human` after the freeze
  gps        country x dimension GPS z

Statistic
  a_i = sign_i * Spearman(human_i, gps[top_dimension_i]) over countries
  A   = mean of a_i over the primary-selected items

Inference
  permutation null over items: draw |S| items uniformly from the whole pool and give
  them the selected items' (dimension, sign) pairs in random order; one-sided
  p = #{A_null >= A} / draws   (as registered)
  country bootstrap: resample countries with replacement; percentile 95% interval
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import freeze as FR  # noqa: E402

PERM_SEED = 20261015
PERM_DRAWS = 10_000
BOOT_DRAWS = 2_000


def load_heldout_human(path: Path, *, freeze_path: Path) -> pd.DataFrame:
    FR.require_freeze(freeze_path)
    return pd.read_csv(path, index_col=0)


def _rank(a: np.ndarray) -> np.ndarray:
    return pd.DataFrame(a).rank(axis=0).to_numpy()


def _spearman_cols(h: np.ndarray, g: np.ndarray) -> np.ndarray:
    """Column-wise Spearman of h[:, j] with g[:, j]; countries with NaN in either dropped."""
    out = np.full(h.shape[1], np.nan)
    for j in range(h.shape[1]):
        ok = ~(np.isnan(h[:, j]) | np.isnan(g[:, j]))
        if ok.sum() < 8:
            continue
        x = pd.Series(h[ok, j]).rank().to_numpy()
        y = pd.Series(g[ok, j]).rank().to_numpy()
        if x.std() == 0 or y.std() == 0:
            continue
        out[j] = float(np.corrcoef(x, y)[0, 1])
    return out


def _no_abstentions(sel: pd.DataFrame, name: str) -> None:
    if (sel["sign"] == 0).any() or (sel["top_dimension"] == "none").any():
        raise ValueError(f"{name}: abstained rows (sign 0 / 'none') must be dropped before scoring")


def item_agreement(sel: pd.DataFrame, human: pd.DataFrame, gps: pd.DataFrame) -> pd.DataFrame:
    _no_abstentions(sel, "item_agreement")
    countries = human.index.intersection(gps.index)
    h = human.loc[countries, sel.question_id].to_numpy(float)
    g = gps.loc[countries, sel.top_dimension].to_numpy(float)
    rho = _spearman_cols(h, g)
    return sel.assign(rho=rho, a_i=sel.sign.to_numpy() * rho)


def _A(human_mat, gps, countries, items_idx, dims, signs) -> float:
    h = human_mat[:, items_idx]
    g = gps.loc[countries, dims].to_numpy(float)
    return float(np.nanmean(np.asarray(signs) * _spearman_cols(h, g)))


def compare(sel_a: pd.DataFrame, sel_b: pd.DataFrame, human: pd.DataFrame, gps: pd.DataFrame,
            *, boot: int = BOOT_DRAWS, seed: int = PERM_SEED) -> dict:
    """D = A(sel_a) - A(sel_b), each on its own items and signs; paired country bootstrap.

    sel_*: question_id, top_dimension, sign (already restricted to the items each route uses).
    """
    _no_abstentions(sel_a, "sel_a")
    _no_abstentions(sel_b, "sel_b")
    countries = human.index.intersection(gps.index)

    def A(sel, h, g):
        return float(np.nanmean(sel.sign.to_numpy() * _spearman_cols(
            h[sel.question_id].to_numpy(float), g[list(sel.top_dimension)].to_numpy(float))))

    h0, g0 = human.loc[countries], gps.loc[countries]
    a, b = A(sel_a, h0, g0), A(sel_b, h0, g0)
    rng = np.random.default_rng(seed)
    ds = np.empty(boot)
    for k in range(boot):
        cb = countries[rng.integers(0, len(countries), len(countries))]
        h, g = human.loc[cb].reset_index(drop=True), gps.loc[cb].reset_index(drop=True)
        ds[k] = A(sel_a, h, g) - A(sel_b, h, g)
    return {"A_a": a, "A_b": b, "D": a - b, "n_a": int(len(sel_a)), "n_b": int(len(sel_b)),
            "ci95": [float(np.nanpercentile(ds, 2.5)), float(np.nanpercentile(ds, 97.5))],
            "boot": boot, "seed": seed}


def screen(selection: pd.DataFrame, human: pd.DataFrame, gps: pd.DataFrame, *,
           draws: int = PERM_DRAWS, seed: int = PERM_SEED, boot: int = BOOT_DRAWS) -> dict:
    sel = selection[selection.primary_selected.astype(bool)].reset_index(drop=True)
    if sel.empty:
        raise ValueError("no primary-selected items")
    countries = human.index.intersection(gps.index)
    pool = [q for q in selection.question_id if q in human.columns]
    hm = human.loc[countries, pool].to_numpy(float)
    col = {q: i for i, q in enumerate(pool)}
    dims, signs = list(sel.top_dimension), sel.sign.to_numpy()
    A = _A(hm, gps, countries, [col[q] for q in sel.question_id], dims, signs)

    rng = np.random.default_rng(seed)
    null = np.empty(draws)
    for b in range(draws):
        idx = rng.choice(len(pool), size=len(sel), replace=False)
        perm = rng.permutation(len(sel))
        null[b] = _A(hm, gps, countries, idx, [dims[i] for i in perm], signs[perm])
    p = int((null >= A).sum()) / draws          # the registered statistic (PREREGISTRATION.md section 4)

    ci = [float("nan"), float("nan")]
    if boot:
        bs = np.empty(boot)
        sel_idx = [col[q] for q in sel.question_id]
        for b in range(boot):
            r = rng.integers(0, len(countries), len(countries))
            cb = countries[r]
            bs[b] = _A(human.loc[cb, pool].to_numpy(float), gps.loc[cb].reset_index(drop=True)
                       .set_index(pd.RangeIndex(len(cb))), pd.RangeIndex(len(cb)), sel_idx, dims, signs)
        ci = [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]
    return {"A": A, "n_selected": int(len(sel)), "n_pool": len(pool), "n_countries": int(len(countries)),
            "p_perm": p, "null_mean": float(null.mean()), "null_q95": float(np.quantile(null, 0.95)),
            "ci95": ci, "draws": draws, "seed": seed}
