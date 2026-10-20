"""No (d_out, d_in) array may be formed for real-size modules (4096 x 14336)."""
import tracemalloc

import numpy as np

from w3b import core

D_OUT, D_IN, R = 4096, 14336, 32
DENSE_BYTES = D_OUT * D_IN * 8          # ~470 MB


def _peak(fn):
    tracemalloc.start()
    try:
        fn()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_lowrank_colspace_peak_far_below_dense():
    rng = np.random.default_rng(0)
    A = rng.standard_normal((R, D_IN))
    B = rng.standard_normal((D_OUT, R))
    peak = _peak(lambda: core.lowrank_colspace(A, B, 64.0, R))
    # real need: a handful of r x d_in and d_out x r float64 arrays (~MBs)
    assert peak < DENSE_BYTES / 20, f"peak {peak/1e6:.1f} MB vs dense {DENSE_BYTES/1e6:.0f} MB"


def test_guard_is_not_vacuous_dense_product_trips_it():
    """The same measurement must flag the dense B @ A route, otherwise the guard proves nothing."""
    rng = np.random.default_rng(1)
    A = rng.standard_normal((R, D_IN))
    B = rng.standard_normal((D_OUT, R))
    peak = _peak(lambda: B @ A)
    assert peak >= DENSE_BYTES * 0.9, f"tracemalloc missed the dense product: {peak/1e6:.1f} MB"
    assert not peak < DENSE_BYTES / 20


def test_pair_overlap_peak_far_below_dense():
    rng = np.random.default_rng(2)
    mk = lambda: {"m": {"A": rng.standard_normal((R, D_IN)), "B": rng.standard_normal((D_OUT, R)),
                        "alpha": 64.0, "r": R}}
    X, Y = mk(), mk()
    peak = _peak(lambda: core.pair_overlap(X, Y, ["m"]))
    assert peak < DENSE_BYTES / 10
