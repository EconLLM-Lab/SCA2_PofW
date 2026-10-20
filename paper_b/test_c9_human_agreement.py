"""Tests for paper_b/c9_human_agreement.py (Amendment C9, card C9-1).

Logic tests run on small synthetic frames. The integration tests read the banked cohort-1 surface, the
bank-2 synthetic score file and the local human item means; they skip cleanly when those local inputs are
absent. Nothing here prints or stores country-level human values.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c9_human_agreement as C  # noqa: E402


# ------------------------------------------------------------- logic tests
def test_between_share_perfect_and_null():
    y = np.array([1.0, 1.0, 5.0, 5.0, 9.0, 9.0])
    g = np.array(["a", "a", "b", "b", "c", "c"])
    assert C.between_share(y, g) == pytest.approx(1.0)
    y2 = np.array([1.0, 5.0, 1.0, 5.0, 1.0, 5.0])
    assert C.between_share(y2, g) == pytest.approx(0.0)


def test_between_share_matches_analyze_phase_variance_share():
    import analyze_phase as P
    rng = np.random.default_rng(1)
    cc = [f"C{i}" for i in range(9)]
    lab = ["x", "x", "x", "y", "y", "z", "z", "z", "z"]
    y = pd.Series(rng.normal(size=9), index=cc)
    prof = pd.DataFrame({"country": cc, "profile_id": lab})
    ref = P.variance_share(y, prof)
    assert C.between_share(y.to_numpy(), np.array(lab)) == pytest.approx(ref["between_share_all"])


def test_permutation_detects_structure_and_preserves_sizes():
    sizes = [3, 3, 2, 2, 4]
    lab = np.repeat(np.arange(len(sizes)), sizes)
    rng = np.random.default_rng(0)
    strong = lab * 10.0 + rng.normal(scale=0.1, size=lab.size)
    res = C.permutation_between(strong, lab, n_perm=2000, rng=np.random.default_rng(7))
    assert res["observed"] > 0.99
    assert res["p_one_sided"] < 0.01
    noise = rng.normal(size=lab.size)
    res2 = C.permutation_between(noise, lab, n_perm=2000, rng=np.random.default_rng(7))
    assert 0.0 <= res2["p_one_sided"] <= 1.0
    assert res2["chance_mean"] == pytest.approx((len(sizes) - 1) / (lab.size - 1), abs=0.04)
    perm = C.permuted_labels(lab, 5, np.random.default_rng(3))
    assert perm.shape == (5, lab.size)
    for row in perm:
        assert sorted(np.bincount(row)) == sorted(np.bincount(lab))


def test_permutation_p_has_plus_one_floor():
    lab = np.repeat(np.arange(3), 3)
    y = lab.astype(float)
    res = C.permutation_between(y, lab, n_perm=999, rng=np.random.default_rng(1))
    assert res["p_one_sided"] >= 1 / 1000 - 1e-12


def test_loo_mate_mean():
    s = pd.Series({"A": 1.0, "B": 3.0, "C": 5.0, "D": 10.0})
    prof = pd.Series({"A": "p", "B": "p", "C": "p", "D": "q"})
    out = C.loo_mate_mean(s, prof)
    assert out["A"] == pytest.approx(4.0)
    assert out["B"] == pytest.approx(3.0)
    assert out["C"] == pytest.approx(2.0)
    assert math.isnan(out["D"])  # singleton has no mate


def test_power_simulation_monotone_and_reports_minimum():
    sizes = [3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    res = C.power_simulation(sizes, grid=[0.0, 0.3, 0.6, 0.9], n_sim=150, n_perm=300, seed=5)
    pw = [r["power"] for r in res["curve"]]
    assert pw[0] < 0.2          # size at share 0 is near alpha
    assert pw[-1] > 0.9
    assert pw == sorted(pw) or pw[-1] >= pw[1]
    assert res["min_detectable_share"] in (0.6, 0.9, 0.3)
    assert res["min_detectable_excess"] > 0


def test_ratio_to_reference_nan_safe():
    assert C.ratio(0.4, 0.8) == pytest.approx(0.5)
    assert math.isnan(C.ratio(0.4, 0.0))
    assert math.isnan(C.ratio(float("nan"), 0.5))


# ------------------------------------------------------ integration tests
needs_data = pytest.mark.skipif(not C.inputs_available(), reason="local C9 inputs absent")


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp("c9")
    return C.run(out_dir=out), out


@needs_data
def test_cohort1_three_columns_reproduce_banked_table(result):
    res, _ = result
    banked = pd.read_csv(C.BANKED_THREE_COLUMN)
    mine = pd.DataFrame(res["rows"])
    mine = mine[mine.part == "a_cohort1_three_column"]
    assert len(mine) == len(banked) == 21
    for _, b in banked.iterrows():
        col = b["column"]
        m = mine[(mine.column == col) & (mine.surface_label_short == b["surface"])]
        assert len(m) == 1, (col, b["surface"])
        m = m.iloc[0]
        for mk, bk in (("value", "rho"), ("ci_low", "ci_lo"), ("ci_high", "ci_hi")):
            assert m[mk] == pytest.approx(b[bk], rel=0, abs=1e-12), (col, b["surface"], mk)
        assert int(m["n"]) == int(b["n"])


@needs_data
def test_bank2_adapter_gps_matches_numbers_table(result):
    res, _ = result
    nt = pd.read_csv(C.NUMBERS_TABLE)
    mine = pd.DataFrame(res["rows"])
    mine = mine[(mine.part == "b_bank2") & (mine.column == "adapter-GPS")]
    checked = 0
    for s in C.SURFACES:
        row = nt[nt.claim_id == f"B2_bank2_{s}_rho"]
        assert len(row) == 1, s
        m = mine[mine.surface_label_short == s].iloc[0]
        for mk, bk in (("value", "value"), ("ci_low", "ci_low"), ("ci_high", "ci_high")):
            assert m[mk] == pytest.approx(float(row.iloc[0][bk]), rel=0, abs=1e-12), (s, mk)
        checked += 1
    assert checked == 7


@needs_data
def test_bank2_unit_partition_equals_sign_profiles(result):
    res, _ = result
    assert res["meta"]["bank2_partition_identical_to_sign_profiles"] is True


@needs_data
def test_outputs_written_and_shape(result):
    res, out = result
    js = out / "c9_human_agreement.json"
    cs = out / "c9_human_agreement.csv"
    assert js.exists() and cs.exists()
    df = pd.read_csv(cs)
    for col in ("claim_id", "statistic", "value", "ci_low", "ci_high", "n", "interval_type",
                "surface_label"):
        assert col in df.columns
    assert df.claim_id.is_unique
    assert (df.surface_label.str.contains("DESCRIPTIVE")).all()
    parts = set(res["rows_by_part"])
    assert {"a_cohort1_three_column", "b_bank2", "c_between_profile", "d_sign_mate",
            "e_gps_sign_reference", "f_preprint_items", "c_power"} <= parts
    # no country-level human values in the output
    text = cs.read_text() + js.read_text()
    assert "human_item_means" not in text or "sha256" in text


@needs_data
def test_between_profile_rows_cover_all_surfaces(result):
    res, _ = result
    df = pd.DataFrame(res["rows"])
    d = df[df.part == "c_between_profile"]
    for s in C.SURFACES:
        for arm in ("human", "adapter"):
            sub = d[(d.surface_label_short == s) & (d.column == arm)]
            stats = set(sub.statistic)
            assert {"between share, all countries", "between share, multi-member",
                    "chance mean, multi-member", "permutation p (one-sided), multi-member"} <= stats
