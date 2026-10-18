"""Per-dimension interval tests (synthetic countries and items only; no human data is read).

Card T1, step 5: the same seed must give identical intervals on a small synthetic frame, and the
dimension grouping must match the selection file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_heldout as AH  # noqa: E402
import per_dimension as PD  # noqa: E402
import screen_test as ST  # noqa: E402

RESULTS = HERE.parents[1] / "planning/sprint_2026-10-11/paper-b-tier1/results"
DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]


def _world(n_items: int = 40, signal: float = 1.0, seed: int = 0):
    """A synthetic 42-country world: `sel` is a probe-selection frame, `hum`/`gps` the surfaces."""
    rng = np.random.default_rng(seed)
    ctry = [f"C{i:02d}" for i in range(42)]
    gps = pd.DataFrame(rng.normal(size=(42, len(DIMS))), index=ctry, columns=DIMS)
    rows, hum = [], {}
    for i in range(n_items):
        d = DIMS[i % len(DIMS)]
        s = 1 if i % 3 else -1
        y = signal * s * gps[d].to_numpy() + rng.normal(size=42)
        hum[f"Q{i}"] = pd.Series(y, index=ctry)
        rows.append({"question_id": f"Q{i}", "top_dimension": d, "sign": s, "t_top": s * (2.0 + i),
                     "primary_selected": i < 24, "secondary_selected": i < 30})
    return pd.DataFrame(rows), pd.DataFrame(hum), gps


def _comparator(items, dims, signs):
    return pd.DataFrame({"question_id": list(items), "dimension": list(dims), "sign": list(signs)})


# --- step 5: determinism -------------------------------------------------------------

def test_the_same_seed_gives_identical_intervals():
    sel, hum, gps = _world(seed=3)
    a = PD.point_interval(sel, hum, gps, boot=50, seed=7)
    b = PD.point_interval(sel, hum, gps, boot=50, seed=7)
    assert a == b, "the same seed must reproduce the intervals exactly"
    assert PD.point_interval(sel, hum, gps, boot=50, seed=8) != a


def test_bonferroni_interval_comes_from_the_same_draws_and_is_wider():
    """Exploratory, not registered: Bonferroni over the imprint dimensions, read off the same draws."""
    sel, hum, gps = _world(seed=3)
    out = PD.point_interval(sel, hum, gps, boot=200, seed=7)
    assert PD.BONF_M == len(AH.IMPRINT)
    for d, v in out.items():
        assert v["bonf_m"] == PD.BONF_M
        assert v["ci_bonf"][0] <= v["ci95"][0] and v["ci_bonf"][1] >= v["ci95"][1]
    again = PD.point_interval(sel, hum, gps, boot=200, seed=7)
    assert {d: v["ci95"] for d, v in again.items()} == {d: v["ci95"] for d, v in out.items()}


def test_the_same_seed_gives_the_same_permutation_p():
    sel, hum, gps = _world(seed=3)
    pool = list(sel.question_id)
    assert PD.perm_p(sel, hum, gps, pool, draws=100, seed=5) == PD.perm_p(sel, hum, gps, pool, draws=100, seed=5)


def test_the_registered_seed_is_the_screen_test_seed():
    assert PD.SEED == ST.PERM_SEED


# --- step 5: grouping -----------------------------------------------------------------

def test_dimension_grouping_matches_the_selection_file():
    sel, _, _ = _world(seed=1)
    prim = AH.adapter_route(sel)
    groups = PD.dimension_groups(prim)
    assert set(groups) == set(sel[sel.primary_selected].top_dimension)
    for d, g in groups.items():
        want = sel[sel.primary_selected & (sel.top_dimension == d)]
        assert list(g.question_id) == list(want.question_id), "items must not move between dimensions"
        assert list(g.sign) == list(np.sign(want.t_top.astype(float)))
    assert sum(len(g) for g in groups.values()) == int(sel.primary_selected.sum())


def test_primary_route_grouping_matches_the_committed_descriptives():
    """The real selection file, against the per-dimension A/n already committed by analyze_heldout."""
    routes = PD.build_routes(
        sel=pd.read_csv(HERE / "selection_amended_20261016.csv"),
        sp_sel=pd.read_csv(RESULTS / "signprompt_selection_20261017.csv"),
        face=pd.read_csv(HERE / "face_valid.csv"),
        jev=pd.read_csv(HERE / "jev/majority_face_valid_jev.csv"),
    )
    prim = routes["adapter_primary"]
    committed = json.loads((RESULTS / "heldout_analysis.json").read_text())["s4_descriptives"]["per_dimension"]
    assert len(prim) == 56
    assert {d: int((prim.top_dimension == d).sum()) for d in committed} == {d: v["n"] for d, v in committed.items()}


# --- step 3: the statistic ------------------------------------------------------------

def test_A_d_and_n_are_the_mean_and_count_over_the_dimension_items():
    sel, hum, gps = _world(seed=2)
    ia = ST.item_agreement(sel, hum, gps)
    out = PD.point_interval(sel, hum, gps, boot=20, seed=1)
    assert set(out) == set(ia.top_dimension)
    for d, g in ia.groupby("top_dimension"):
        assert out[d]["n"] == int(len(g))
        assert out[d]["A"] == pytest.approx(float(g.a_i.mean()))
        assert out[d]["ci95"][0] <= out[d]["ci95"][1]
        assert out[d]["boot"] == 20


def test_intervals_come_from_country_resamples_of_the_full_country_set():
    """A dimension whose items are all-NaN on one country still yields an interval (countries resampled)."""
    sel, hum, gps = _world(seed=4)
    hum = hum.copy()
    hum.loc["C00", ["Q0", "Q6"]] = np.nan
    out = PD.point_interval(sel, hum, gps, boot=30, seed=1)
    assert np.isfinite(out["trust"]["ci95"]).all()


# --- step 4: the descriptive permutation p -------------------------------------------

def test_permutation_p_is_zero_under_a_strong_signal_and_one_under_flipped_signs():
    sel, hum, gps = _world(signal=3.0, seed=5)
    pool = list(sel.question_id)
    strong = PD.perm_p(sel, hum, gps, pool, draws=400, seed=1)
    assert all(v["p"] == 0.0 for v in strong.values())
    flipped = PD.perm_p(sel.assign(sign=-sel.sign), hum, gps, pool, draws=400, seed=1)
    assert all(v["p"] == 1.0 for v in flipped.values())


def test_permutation_draws_as_many_items_as_the_dimension_has():
    sel, hum, gps = _world(seed=6)
    out = PD.perm_p(sel, hum, gps, list(sel.question_id), draws=50, seed=1)
    for d, g in PD.dimension_groups(sel).items():
        assert out[d]["n"] == len(g)
        assert out[d]["p"] * 50 == int(out[d]["p"] * 50), "p is a share of the draws, no +1 correction"


# --- step 3: the routes ---------------------------------------------------------------

def test_comparator_routes_keep_the_imprint_set_and_drop_the_repaired_items():
    face = _comparator(["Q1", "Q82", "Q5", "Q6"], ["trust", "trust", "negrecip", "altruism"], [1, -1, 1, -1])
    jev = _comparator(["Q1", "Q82", "Q5", "Q6"], ["trust", "trust", "negrecip", "altruism"], [1, -1, 1, -1])
    sel, _, _ = _world(seed=7)
    routes = PD.build_routes(sel=sel, sp_sel=sel, face=face, jev=jev)
    for name in ("face_valid", "jev_majority"):
        r = routes[name]
        assert set(r.question_id) == {"Q1", "Q6"}, "Q82 (repaired) and the negrecip item must leave"
        assert list(r.top_dimension) == ["trust", "altruism"]
        assert list(r.sign) == [1.0, -1.0]


def test_adapter_routes_take_their_signs_from_t_top_and_their_rule_from_the_flag():
    sel, _, _ = _world(seed=8)
    routes = PD.build_routes(sel=sel, sp_sel=sel, face=_comparator([], [], []), jev=_comparator([], [], []))
    assert list(routes["adapter_primary"].question_id) == list(sel[sel.primary_selected].question_id)
    assert list(routes["adapter_secondary"].question_id) == list(sel[sel.secondary_selected].question_id)
    assert list(routes["adapter_primary"].sign) == list(np.sign(sel[sel.primary_selected].t_top.astype(float)))


def test_the_c5_reading_is_the_mechanical_interval_rule():
    assert PD.c5_reading([0.01, 0.2]) == "interval excludes 0: transport"
    assert PD.c5_reading([-0.2, -0.01]) == "interval excludes 0: transport"
    assert PD.c5_reading([-0.01, 0.2]) == "interval includes 0: not transport"
    assert PD.c5_reading([0.0, 0.2]) == "interval includes 0: not transport"
