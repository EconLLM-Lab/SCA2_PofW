"""Tests for the pure helpers in w3b.run_w3b (LOPO table, degree-matched subset + edge-swap chain)."""
import itertools

import numpy as np

from w3b import run_w3b as R


def _toy():
    nodes = list("ABCDEF")
    one = [R.key("A", "B"), R.key("B", "C"), R.key("D", "E")]
    non = [R.key(a, b) for a, b in itertools.combinations(nodes, 2) if R.key(a, b) not in one]
    S = {e: float(i) for i, e in enumerate(one + non)}
    return nodes, one, non, S


def test_lopo_drops_every_pair_with_the_profile_and_reports_range():
    nodes, one, non, S = _toy()
    rows, summ = R.lopo_table(S, one, non, nodes)
    byp = {r["profile"]: r for r in rows}
    assert byp["B"]["one_bit_pairs_containing"] == 2 and byp["B"]["one_bit_remaining"] == 1
    assert byp["B"]["T_minus_i"] == S[R.key("D", "E")]
    assert byp["F"]["T_minus_i"] == np.mean([S[e] for e in one])          # F is in no one-bit pair
    assert byp["A"]["non_one_bit_remaining"] == len([e for e in non if "A" not in e])
    vals = [r["T_minus_i"] for r in rows]
    assert summ["min"] == min(vals) and summ["max"] == max(vals)
    assert byp[summ["max_profile"]]["T_minus_i"] == max(vals)
    assert all("p_value" not in r for r in rows)                           # prereg 6(2): no p-values


def test_degree_matched_subset_has_exact_degrees_and_lies_in_pool():
    nodes, one, non, S = _toy()
    deg = R.degree_seq(one)
    sub = R.find_degree_matched_subset(nodes, set(non), deg)
    assert sub is not None and len(sub) == len(one) and len(set(sub)) == len(sub)
    assert set(sub) <= set(non)
    assert R.degree_seq(sub) == deg


def test_degree_matched_subset_none_when_infeasible():
    # a star cannot supply a 2-regular triangle degree sequence
    pool = {R.key("A", "B"), R.key("A", "C"), R.key("A", "D")}
    assert R.find_degree_matched_subset(list("ABCD"), pool, {"A": 2, "B": 2, "C": 2}) is None


def _big():
    nodes = list("ABCDEFGHIJ")
    one = [R.key("A", "B"), R.key("B", "C"), R.key("C", "D"), R.key("E", "F"), R.key("G", "H")]
    non = [R.key(a, b) for a, b in itertools.combinations(nodes, 2) if R.key(a, b) not in one]
    g = np.random.default_rng(0)
    S = {e: float(g.random()) for e in one + non}
    return nodes, one, non, S


def test_chain_preserves_degrees_stays_in_pool_and_is_seeded():
    nodes, one, non, S = _big()
    deg = R.degree_seq(one)
    start = R.find_degree_matched_subset(nodes, set(non), deg)
    assert R.degree_seq(start) == deg
    a, info = R.degree_matched_chain(start, non, S, n_draws=200, burn_in=20, thin=5, seed=7)
    b, _ = R.degree_matched_chain(start, non, S, n_draws=200, burn_in=20, thin=5, seed=7)
    c, _ = R.degree_matched_chain(start, non, S, n_draws=200, burn_in=20, thin=5, seed=8)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    assert info["accepted"] == 20 + 5 * 199
    assert info["distinct_subsets_drawn"] > 5
    assert a.min() >= min(S[e] for e in non) and a.max() <= max(S[e] for e in non)


def test_chain_raises_when_no_swap_is_possible():
    nodes, one, non, S = _toy()          # tiny pool: every swap leaves the pool or collides
    start = R.find_degree_matched_subset(nodes, set(non), R.degree_seq(one))
    try:
        R.degree_matched_chain(start, non, S, n_draws=2, burn_in=5, thin=1, seed=1, max_proposals=2000)
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError for a stuck chain")
