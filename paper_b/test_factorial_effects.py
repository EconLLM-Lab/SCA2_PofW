"""Factorial effect-matrix tests (synthetic composites only)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factorial as F  # noqa: E402
import factorial_effects as FE  # noqa: E402

SURFACES = (("trust", "trust"), ("risktaking", "risktaking"), ("posrecip", "posrecip"),
            ("altruism", "altruism"), ("patience:Q43", "patience"), ("patience:Q50", "patience"),
            ("negrecip", "negrecip"))


def _planted(noise=0.0, seed=0, effect=3.0):
    rng = np.random.default_rng(seed)
    rows = []
    for u in F.all_units():
        bits = dict(zip(F.DIMS, F.bits_of_unit(u)))
        for surface, dim in SURFACES:
            rows.append({"unit": u, "surface": surface,
                         "composite": 10.0 + effect * bits[dim] + noise * rng.normal()})
    return pd.DataFrame(rows)


def test_matrix_is_6_by_7_and_main_effects_are_recovered():
    m = FE.effect_matrix(_planted())
    assert m.shape == (6, 7)
    assert list(m.index) == F.DIMS
    assert abs(m.loc["trust", "trust"] - 3.0) < 1e-9          # effect of flipping the bit
    assert abs(m.loc["trust", "altruism"]) < 1e-9


def test_diagonal_dominance_full_when_planted():
    dd = FE.diagonal_dominance(FE.effect_matrix(_planted(noise=0.1)))
    assert dd["share"] == 1.0 and dd["hits"] == 6
    assert dd["p_binomial"] < 1e-4                            # chance = 1/7 per dimension


def test_diagonal_dominance_near_chance_under_noise():
    shares = [FE.diagonal_dominance(FE.effect_matrix(_planted(noise=1.0, seed=s, effect=0.0)))["share"]
              for s in range(60)]
    assert 0.08 < float(np.mean(shares)) < 0.30             # ~1/7 (patience gets 2 of 7 columns)


def test_fit_reports_t_and_lenth_pse():
    fit = FE.fit(_planted(noise=0.5, seed=3))
    cell = fit[(fit.surface == "trust") & (fit.dimension == "trust")].iloc[0]
    assert cell.t > 10 and cell.error_df == 42
    assert cell.lenth_pse > 0 and abs(cell.t_lenth) > 5


def test_missing_unit_refused():
    import pytest
    with pytest.raises(ValueError, match="missing units"):
        FE.effect_matrix(_planted().iloc[1:])


def test_bank_contract_over_shared_units():
    a = pd.Series({f"P_{i}": float(i) for i in range(26)})
    b = pd.Series({f"P_{i}": float(i) + 0.01 for i in range(64)})
    out = FE.bank_contract(a, b)
    assert out["n_units"] == 26 and out["pearson"] > 0.99 and out["spearman"] > 0.99
