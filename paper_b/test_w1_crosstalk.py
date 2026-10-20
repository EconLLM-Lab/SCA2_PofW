"""W1 cross-talk decomposition tests (synthetic planted data, plus a pin to the numbers table)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factorial as F  # noqa: E402
import w1_crosstalk as W  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
NUMBERS = REPO / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
SURF = [("trust", "trust"), ("risktaking", "risktaking"), ("patience:Q43", "patience"),
        ("patience:Q50", "patience"), ("altruism", "altruism"), ("posrecip", "posrecip"),
        ("negrecip", "negrecip")]


def _planted(cross=0.0, effect=2.0):
    """risktaking bit leaks into altruism by `cross`; everything else is own-bit only."""
    rows = []
    for u in F.all_units():
        bits = dict(zip(F.DIMS, F.bits_of_unit(u)))
        for s, d in SURF:
            v = 10 + effect * bits[d] + (cross * bits["risktaking"] if s == "altruism" else 0.0)
            rows.append({"unit": u, "surface": s, "composite": v})
    return pd.DataFrame(rows)


def test_decompose_is_exact_and_cross_is_zero_without_leakage():
    comp = _planted(cross=0.0)
    m = W.effect_matrix(comp)
    bits = pd.DataFrame([F.bits_of_unit(u) for u in F.all_units()], columns=F.DIMS,
                        index=F.all_units())
    d = W.decompose(m, "trust", bits)
    assert np.allclose(d["full"], d["own"] + d["cross"])
    assert np.allclose(d["cross"], 0.0, atol=1e-9)
    assert W.cross_variance_share(d) == pytest.approx(0.0, abs=1e-12)


def test_leakage_shows_up_as_cross_share():
    comp = _planted(cross=6.0, effect=2.0)
    m = W.effect_matrix(comp)
    bits = pd.DataFrame([F.bits_of_unit(u) for u in F.all_units()], columns=F.DIMS,
                        index=F.all_units())
    d = W.decompose(m, "altruism", bits)
    # own 2.0 vs leak 6.0 on independent +-0.5 bits: cross var share = 36/(36+4)
    assert W.cross_variance_share(d) == pytest.approx(36 / 40, abs=1e-9)


def test_main_effect_share_is_one_for_additive_surface():
    y = _planted(cross=3.0).query("surface == 'altruism'").set_index("unit").composite
    assert W.main_effect_share(y) == pytest.approx(1.0, abs=1e-9)


def test_main_effect_share_drops_with_interaction():
    units = F.all_units()
    y = pd.Series({u: float(F.bits_of_unit(u)[0] * F.bits_of_unit(u)[1]) for u in units})
    assert W.main_effect_share(y) < 0.8


def test_keyword_share_counts_family_stems():
    rows = [{"gps_dimension": "trust", "prompt": "I trust my friend", "response_a": "ok", "response_b": "no"},
            {"gps_dimension": "trust", "prompt": "plain", "response_a": "ok", "response_b": "no"}]
    out = W.keyword_shares(rows)
    assert out.loc["trust", "trust"] == pytest.approx(0.5)


def test_own_beta_matches_numbers_table_for_both_routes():
    """The matrix reproduces every FX_*_own_beta row (needs the local synthetic inputs)."""
    if not W.INPUTS.exists():
        pytest.skip("local synthetic inputs absent")
    res = W.load_routes()
    table = {r["id"] if "id" in r else list(r.values())[0]: r
             for r in csv.DictReader(NUMBERS.open())}
    checked = 0
    for route, tag in (("adapter", "adapter64"), ("signprompt", "signprompt64")):
        for surf, dim in SURF:
            key = f"FX_{tag}_{surf.replace(':', '_')}_own_beta" if dim == "patience" \
                else f"FX_{tag}_{dim}_own_beta"
            if key not in table:
                continue
            val = float(list(table[key].values())[3])
            assert res[route]["matrix"].loc[dim, surf] == pytest.approx(val, abs=1e-9)
            checked += 1
    assert checked >= 10
