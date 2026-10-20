"""Permutation null and leave-one-profile-out for W3b pair statistics.

Pairs are 2-tuples of profile ids; order inside a pair is ignored.  Caveat the
caller must own: pairs share profiles, so they are not exchangeable in the strict
sense.  The pair-level permutation null is what the task specifies; the
leave-one-profile-out re-run is the sensitivity check for that dependence.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping, Sequence

import numpy as np


def _key(pair) -> tuple:
    a, b = pair
    if a == b:
        raise ValueError(f"degenerate pair {pair!r}")
    return tuple(sorted((a, b)))


def _normalise(pairs: Iterable, name: str) -> list:
    keys = [_key(p) for p in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"duplicate pairs in {name}")
    return keys


def permutation_null(stat_by_pair: Mapping, one_bit_pairs: Sequence, non_one_bit_pairs: Sequence,
                     n_perm: int, seed: int) -> dict:
    """Null of mean(stat) over random size-n sets drawn from the non-one-bit pairs.

    n = len(one_bit_pairs).  p = (1 + #{null >= observed}) / (n_perm + 1), one-sided
    (large = more overlap).  Returns {"observed","null","p_value","n_perm","n_one_bit","n_pool"}.
    """
    if n_perm < 1:
        raise ValueError("n_perm must be >= 1")
    one = _normalise(one_bit_pairs, "one_bit_pairs")
    pool = _normalise(non_one_bit_pairs, "non_one_bit_pairs")
    if not one:
        raise ValueError("one_bit_pairs is empty")
    if set(one) & set(pool):
        raise ValueError("one_bit_pairs and non_one_bit_pairs overlap")
    if len(one) > len(pool):
        raise ValueError(f"pool ({len(pool)}) smaller than one-bit set ({len(one)})")
    stats = {_key(p): v for p, v in stat_by_pair.items()}
    miss = [p for p in one + pool if p not in stats]
    if miss:
        raise KeyError(f"stat_by_pair lacks {len(miss)} pairs, e.g. {miss[:3]}")
    one_vals = np.array([stats[p] for p in one], dtype=np.float64)
    pool_vals = np.array([stats[p] for p in pool], dtype=np.float64)
    if not (np.isfinite(one_vals).all() and np.isfinite(pool_vals).all()):
        raise ValueError("non-finite statistics")
    observed = float(one_vals.mean())
    rng = np.random.default_rng(seed)
    n = len(one)
    null = np.empty(n_perm)
    for i in range(n_perm):
        null[i] = pool_vals[rng.choice(len(pool), size=n, replace=False)].mean()
    p = (1 + int(np.sum(null >= observed))) / (n_perm + 1)
    return {"observed": observed, "null": null, "p_value": float(p), "n_perm": n_perm,
            "n_one_bit": n, "n_pool": len(pool)}


def profile_reuse_counts(pairs: Iterable) -> dict:
    """How many of `pairs` each profile appears in (the dependence structure)."""
    c: Counter = Counter()
    for p in _normalise(pairs, "pairs"):
        c.update(p)
    return dict(c)


def leave_one_profile_out(stat_by_pair: Mapping, one_bit_pairs: Sequence, non_one_bit_pairs: Sequence,
                          n_perm: int, seed: int) -> dict:
    """Re-run permutation_null once per profile, dropping every pair containing it.

    Only profiles that occur in a one-bit pair are dropped.  Returns
    {"reuse_counts": {profile: n one-bit pairs}, "by_profile": {profile: {...}}} where each
    entry has observed, p_value, n_one_bit, n_pool, dropped_one_bit, dropped_pool
    (or {"error": ...} if too few pairs remain).
    """
    one = _normalise(one_bit_pairs, "one_bit_pairs")
    pool = _normalise(non_one_bit_pairs, "non_one_bit_pairs")
    reuse = profile_reuse_counts(one)
    by_profile: dict = {}
    for prof in sorted(reuse, key=str):
        one_k = [p for p in one if prof not in p]
        pool_k = [p for p in pool if prof not in p]
        entry = {"dropped_one_bit": len(one) - len(one_k), "dropped_pool": len(pool) - len(pool_k)}
        if not one_k or len(one_k) > len(pool_k):
            entry["error"] = f"{len(one_k)} one-bit / {len(pool_k)} pool pairs remain"
        else:
            r = permutation_null(stat_by_pair, one_k, pool_k, n_perm, seed)
            entry.update({k: r[k] for k in ("observed", "p_value", "n_one_bit", "n_pool")})
        by_profile[prof] = entry
    return {"reuse_counts": reuse, "by_profile": by_profile}
