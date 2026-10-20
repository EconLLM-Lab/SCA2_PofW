"""Path setup, plus optional random-stub injection (W3B_INJECT_STUB=1).

The injection exists only so run_with_stub.sh can prove the suite notices a
random-matrix core.  It replaces the core functions for the whole session.
"""
import os
import sys
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parents[2]   # workbench/analysis
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))


def install_random_stubs(core, stats):
    import numpy as np
    rng = np.random.default_rng()                 # unseeded on purpose

    def stub_lowrank_colspace(A, B, alpha, r, rel_tol=1e-8):
        d_out = np.asarray(B).shape[0]
        Q, _ = np.linalg.qr(rng.standard_normal((d_out, r)))
        return Q, r

    def stub_load_adapter(path, expected_sha256, modules=None):   # no sha check, no file read
        return {m: {"A": rng.standard_normal((8, 64)), "B": rng.standard_normal((64, 8)),
                    "alpha": 16.0, "r": 8} for m in (modules or ["stub.module"])}

    def stub_permutation_null(stat_by_pair, one, non_one, n_perm, seed):
        return {"observed": 0.0, "null": rng.random(n_perm), "p_value": float(rng.random()),
                "n_perm": n_perm, "n_one_bit": len(one), "n_pool": len(non_one)}

    core.lowrank_colspace = stub_lowrank_colspace
    core.load_adapter = stub_load_adapter
    stats.permutation_null = stub_permutation_null


def pytest_configure(config):
    if os.environ.get("W3B_INJECT_STUB") == "1":
        from w3b import core, stats
        install_random_stubs(core, stats)
        sys.stderr.write("\n*** W3B_INJECT_STUB=1: random stubs installed in w3b.core / w3b.stats ***\n")
