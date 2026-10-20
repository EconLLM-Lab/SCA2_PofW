"""Tests for c9_label_recovery.py. Each one fails on a specific wrong implementation (named in the docstring)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c9_label_recovery as LR  # noqa: E402


def rows(adapter_margin, ref_margin):
    n = len(adapter_margin)
    return pd.DataFrame({"i": range(n), "ref_chosen": np.asarray(ref_margin, float), "ref_rejected": 0.0,
                         "adapter_chosen": np.asarray(adapter_margin, float), "adapter_rejected": 0.0})


def test_recovery_and_accuracy_are_different_rules():
    """Fails if recovery uses the accuracy rule (adapter_margin > 0) or vice versa."""
    am = [1.0] * 66 + [-1.0] * 66                 # half the pairs prefer the chosen completion outright
    rm = [2.0] * 66 + [-3.0] * 66                 # ...but on those the base preferred it even more
    s = LR.country_stats(rows(am, rm))
    assert s["accuracy"] == pytest.approx(0.5)
    assert s["recovery"] == pytest.approx(0.5)    # moved toward the label only on the second half
    s2 = LR.country_stats(rows([1.0] * 132, [2.0] * 132))
    assert s2["accuracy"] == 1.0 and s2["recovery"] == 0.0
    assert s2["base_accuracy"] == 1.0 and s2["mean_margin_shift"] == pytest.approx(-1.0)


@pytest.mark.parametrize("n", [131, 133])
def test_wrong_pair_count_raises(n):
    """Fails if a country with a missing or duplicated pair is summarised silently."""
    with pytest.raises(ValueError):
        LR.country_stats(rows([1.0] * n, [0.0] * n))


def test_duplicate_pair_ids_raise():
    r = rows([1.0] * 132, [0.0] * 132)
    r.loc[5, "i"] = 4
    with pytest.raises(ValueError):
        LR.country_stats(r)


def test_nonfinite_raises():
    r = rows([1.0] * 132, [0.0] * 132)
    r.loc[0, "adapter_chosen"] = float("-inf")
    with pytest.raises(ValueError):
        LR.country_stats(r)


def _cohort(values_by_country):
    return {cc: rows([1.0] * int(round(v * 132)) + [-1.0] * (132 - int(round(v * 132))), [0.0] * 132)
            for cc, v in values_by_country.items()}


def test_missing_country_raises():
    """Fails if a country absent from the run is dropped instead of refused."""
    cs = ["AAA", "BBB", "CCC"]
    cl = pd.Series({"AAA": "p1", "BBB": "p1", "CCC": "p2"})
    with pytest.raises(ValueError):
        LR.summarize(_cohort({"AAA": 0.5, "BBB": 0.5}), cl, countries=cs, draws=50)


def test_bootstrap_resamples_profiles():
    """Fails on a non-resampling bootstrap (every cluster once -> zero-width interval) or on draws=1."""
    cs = [f"C{i:02d}" for i in range(12)]
    vals = {cc: (i % 4) / 4 + 0.1 for i, cc in enumerate(cs)}         # heterogeneous across profiles
    cl = pd.Series({cc: f"p{i % 6}" for i, cc in enumerate(cs)})
    res = LR.summarize(_cohort(vals), cl, countries=cs, draws=400)
    pb = res["cohort"]["accuracy"]["profile_block"]
    assert pb["unit"] == "profile_block" and pb["draws"] == 400
    assert pb["ci_hi"] - pb["ci_lo"] > 0.05
    const = LR.summarize(_cohort({cc: 0.5 for cc in cs}), cl, countries=cs, draws=400)
    c = const["cohort"]["accuracy"]["profile_block"]
    assert c["ci_lo"] == pytest.approx(c["ci_hi"])                     # a constant input has no spread


def test_country_rows_carry_their_own_interval_and_sorted_order(tmp_path):
    """Fails if one pooled interval is pasted on every country row, or if row order depends on hash order."""
    cs = ["ZZZ", "AAA", "MMM"]
    cl = pd.Series({"ZZZ": "p1", "AAA": "p2", "MMM": "p2"})
    res = LR.summarize(_cohort({"ZZZ": 0.9, "AAA": 0.2, "MMM": 0.6}), cl, countries=cs, draws=100)
    assert list(res["countries"]) == ["AAA", "MMM", "ZZZ"]
    ivs = {tuple(r["accuracy_wilson95"]) for r in res["countries"].values()}
    assert len(ivs) == 3
    df = LR.render_csv(res)
    df.to_csv(tmp_path / "x.csv", index=False)
    assert (tmp_path / "x.csv").exists()
    assert json.dumps(res)                                             # serialisable


def test_wilson_bounds():
    lo, hi = LR.wilson(0.5, 132)
    assert 0.41 < lo < 0.5 < hi < 0.59
    assert LR.wilson(0.0, 132)[0] == pytest.approx(0.0, abs=1e-12)
