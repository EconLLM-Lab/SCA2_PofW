"""Screen-test tests (synthetic countries and items only)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import screen_test as ST  # noqa: E402

DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]


def _world(n_items=80, n_sel=20, signal=1.0, seed=0):
    rng = np.random.default_rng(seed)
    ctry = [f"C{i:02d}" for i in range(42)]
    gps = pd.DataFrame(rng.normal(size=(42, 6)), index=ctry, columns=DIMS)
    sel_rows, hum = [], {}
    for i in range(n_items):
        d = DIMS[i % 4]
        s = 1 if i % 3 else -1
        y = signal * s * gps[d] + rng.normal(size=42)
        hum[f"Q{i}"] = pd.Series(y.to_numpy(), index=ctry)
        sel_rows.append({"question_id": f"Q{i}", "top_dimension": d, "sign": s,
                         "primary_selected": i < n_sel})
    return pd.DataFrame(sel_rows), pd.DataFrame(hum), gps


def test_signed_agreement_positive_when_assignment_is_right():
    sel, hum, gps = _world(signal=1.0)
    a = ST.item_agreement(sel[sel.primary_selected], hum, gps)
    assert (a.a_i > 0).mean() > 0.9 and a.a_i.mean() > 0.5


def test_permutation_rejects_with_signal_and_not_without():
    sel, hum, gps = _world(signal=1.0)
    res = ST.screen(sel, hum, gps, draws=2000, seed=1, boot=200)
    assert res["p_perm"] < 0.01 and res["ci95"][0] > 0
    sel0, hum0, gps0 = _world(signal=0.0, seed=4)
    res0 = ST.screen(sel0, hum0, gps0, draws=2000, seed=1, boot=200)
    assert res0["p_perm"] > 0.05


def test_null_is_calibrated():
    ps = [ST.screen(*_world(signal=0.0, seed=s), draws=400, seed=s, boot=0)["p_perm"]
          for s in range(40)]
    ps = np.array(ps)
    assert float(np.mean(ps < 0.05)) <= 0.15          # type-I rate near 5% (40 worlds)
    assert 0.35 < float(ps.mean()) < 0.65             # p roughly uniform under the null


def test_wrong_signs_give_negative_A():
    sel, hum, gps = _world(signal=1.0)
    sel = sel.assign(sign=-sel.sign)
    assert ST.screen(sel, hum, gps, draws=200, seed=0, boot=0)["A"] < -0.5


def test_human_read_is_guarded(tmp_path):
    with pytest.raises(RuntimeError, match="BLOCKED"):
        ST.load_heldout_human(tmp_path / "human.csv", freeze_path=tmp_path / "FREEZE.json")


def test_compare_detects_a_better_route_and_ties_with_itself():
    sel, hum, gps = _world(signal=1.0)
    good = sel[sel.primary_selected][["question_id", "top_dimension", "sign"]]
    bad = good.assign(top_dimension=["negrecip"] * len(good))      # wrong dimension
    res = ST.compare(good, bad, hum, gps, boot=300, seed=2)
    assert res["D"] > 0.4 and res["ci95"][0] > 0
    same = ST.compare(good, good, hum, gps, boot=50, seed=2)
    assert same["D"] == 0 and same["ci95"] == [0.0, 0.0]


def test_abstained_rows_are_refused():
    sel, hum, gps = _world(signal=1.0)
    s = sel[sel.primary_selected][["question_id", "top_dimension", "sign"]].copy()
    bad = s.copy(); bad.iloc[0, bad.columns.get_loc("sign")] = 0
    with pytest.raises(ValueError, match="abstained"):
        ST.compare(s, bad, hum, gps, boot=5)
    with pytest.raises(ValueError, match="abstained"):
        ST.item_agreement(bad, hum, gps)


def test_p_is_the_registered_share_of_null_draws_at_or_above_A():
    """Preregistration section 4: p = share of null A >= observed A, over `draws` draws (verifier F3)."""
    sel, hum, gps = _world(signal=3.0)
    res = ST.screen(sel, hum, gps, draws=500, seed=1, boot=0)
    assert res["p_perm"] == 0.0                                  # no null draw reaches a very strong A
    assert (res["p_perm"] * 500) == int(res["p_perm"] * 500)     # a multiple of 1/draws, no +1 correction
