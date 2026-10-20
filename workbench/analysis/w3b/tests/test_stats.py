import itertools

import numpy as np
import pytest

from w3b import stats


def _synthetic(effect, seed, n_one=10, n_pool=200):
    rng = np.random.default_rng(seed)
    one = [(f"a{i}", f"b{i}") for i in range(n_one)]
    pool = [(f"c{i}", f"d{i}") for i in range(n_pool)]
    s = {p: rng.normal(0, 1) for p in pool}
    s.update({p: rng.normal(effect, 1) for p in one})
    return s, one, pool


def test_strong_effect_hits_minimum_p():
    s, one, pool = _synthetic(effect=6.0, seed=0)
    n_perm = 999
    r = stats.permutation_null(s, one, pool, n_perm=n_perm, seed=1)
    assert r["p_value"] <= 2 / (n_perm + 1)          # floor is exactly 1/(n_perm+1)
    assert r["p_value"] >= 1 / (n_perm + 1)
    assert r["observed"] > r["null"].max()
    assert len(r["null"]) == n_perm and r["n_one_bit"] == 10 and r["n_pool"] == 200


def test_no_effect_p_roughly_uniform_over_seeds():
    ps = np.array([stats.permutation_null(*_synthetic(0.0, seed), n_perm=199, seed=seed)["p_value"]
                   for seed in range(150)])
    assert 0.38 < ps.mean() < 0.62, ps.mean()
    assert 0.02 < np.mean(ps <= 0.1) < 0.22
    assert 0.3 < np.mean(ps <= 0.5) < 0.7


def test_null_distribution_centres_on_pool_mean_and_is_seeded():
    s, one, pool = _synthetic(0.0, 3)
    r1 = stats.permutation_null(s, one, pool, 500, seed=7)
    r2 = stats.permutation_null(s, one, pool, 500, seed=7)
    r3 = stats.permutation_null(s, one, pool, 500, seed=8)
    np.testing.assert_array_equal(r1["null"], r2["null"])
    assert not np.array_equal(r1["null"], r3["null"])
    pool_mean = np.mean([s[p] for p in pool])
    assert abs(r1["null"].mean() - pool_mean) < 4 * np.std([s[p] for p in pool]) / np.sqrt(len(one) * 500)


def test_p_value_exact_on_tiny_case_and_ties():
    # pool values 0,1,2,3 ; one-bit set size 1 ; observed 2.0 -> P(null>=2) = 2/4
    one, pool = [("x", "y")], [("p", "q"), ("p", "r"), ("p", "s"), ("q", "r")]
    s = {("x", "y"): 2.0, ("p", "q"): 0.0, ("p", "r"): 1.0, ("p", "s"): 2.0, ("q", "r"): 3.0}
    r = stats.permutation_null(s, one, pool, n_perm=20000, seed=0)
    assert abs(r["p_value"] - (1 + 0.5 * 20000) / 20001) < 0.02
    # all-equal statistics: every null draw ties the observed value -> p = 1
    flat = {k: 1.0 for k in s}
    assert stats.permutation_null(flat, one, pool, 50, 0)["p_value"] == 1.0


def test_pair_order_irrelevant_and_input_validation():
    s = {("b", "a"): 1.0, ("c", "d"): 0.0, ("d", "e"): 0.5}
    r = stats.permutation_null(s, [("a", "b")], [("d", "c"), ("e", "d")], 10, 0)
    assert r["observed"] == 1.0
    with pytest.raises(KeyError):
        stats.permutation_null(s, [("a", "b")], [("c", "z")], 10, 0)
    with pytest.raises(ValueError):
        stats.permutation_null(s, [("a", "b"), ("c", "d")], [("d", "e")], 10, 0)    # pool smaller
    with pytest.raises(ValueError):
        stats.permutation_null(s, [], [("d", "e")], 10, 0)
    with pytest.raises(ValueError):
        stats.permutation_null(s, [("a", "b")], [("a", "b")], 10, 0)               # overlapping sets
    s_nan = dict(s); s_nan[("c", "d")] = float("nan")
    with pytest.raises(ValueError):
        stats.permutation_null(s_nan, [("a", "b")], [("c", "d"), ("d", "e")], 10, 0)


def _profile_world(driver="P0"):
    """8 profiles; one-bit pairs are a star around P0 plus a few others."""
    profs = [f"P{i}" for i in range(8)]
    one = [("P0", "P1"), ("P0", "P2"), ("P0", "P3"), ("P4", "P5"), ("P6", "P7")]
    pool = [p for p in itertools.combinations(profs, 2) if tuple(sorted(p)) not in {tuple(sorted(o)) for o in one}]
    rng = np.random.default_rng(0)
    s = {p: rng.normal(0, 0.1) for p in pool}
    for o in one:
        s[o] = 5.0 if driver in o else rng.normal(0, 0.1)
    return s, one, pool


def test_reuse_counts():
    _, one, _ = _profile_world()
    c = stats.profile_reuse_counts(one)
    assert c == {"P0": 3, "P1": 1, "P2": 1, "P3": 1, "P4": 1, "P5": 1, "P6": 1, "P7": 1}
    assert sum(c.values()) == 2 * len(one)


def test_leave_one_profile_out_finds_driver():
    s, one, pool = _profile_world()
    full = stats.permutation_null(s, one, pool, 999, 0)
    lopo = stats.leave_one_profile_out(s, one, pool, 999, 0)
    assert lopo["reuse_counts"]["P0"] == 3
    byp = lopo["by_profile"]
    assert set(byp) == set(lopo["reuse_counts"])
    assert byp["P0"]["dropped_one_bit"] == 3 and byp["P1"]["dropped_one_bit"] == 1
    # dropped pool pairs really contain the profile
    assert byp["P0"]["dropped_pool"] == sum(1 for p in pool if "P0" in p)
    assert full["p_value"] < 0.05
    # removing the driver profile removes the effect; removing a bystander keeps it
    assert byp["P0"]["observed"] < 0.5 < full["observed"]
    assert byp["P0"]["p_value"] > 0.05      # not significant once the driver profile is gone
    assert byp["P7"]["observed"] > full["observed"] * 0.5 and byp["P7"]["p_value"] < 0.05
