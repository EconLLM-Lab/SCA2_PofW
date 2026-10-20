"""Reusable synthetic constructions and check functions.

The check_* functions raise AssertionError when the core misbehaves.  The real
tests call them on the real core; test_stub_detector calls the same functions on a
monkeypatched random core and requires them to fail.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from w3b import core


def orth(rng, d, k):
    Q, _ = np.linalg.qr(rng.standard_normal((d, k)))
    return Q


def adapter_from_basis(rng, U, r, d_in=96, alpha=16.0, name="m"):
    """Adapter whose delta has column space exactly col(U): B = U G, G (k x r) random."""
    k = U.shape[1]
    B = U @ rng.standard_normal((k, r))
    A = rng.standard_normal((r, d_in))
    return {name: {"A": A, "B": B, "alpha": alpha, "r": r}}


def write_adapter(dirpath: Path, tensors: dict, alpha=16, r=8, config=True):
    """Write adapter_model.safetensors (+adapter_config.json); return (path, sha256)."""
    from safetensors.numpy import save_file
    dirpath.mkdir(parents=True, exist_ok=True)
    path = dirpath / "adapter_model.safetensors"
    save_file({k: np.ascontiguousarray(v.astype(np.float32)) for k, v in tensors.items()}, str(path))
    if config:
        (dirpath / "adapter_config.json").write_text(json.dumps({"r": r, "lora_alpha": alpha}))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def check_planted_subspace(tol=1e-8):
    """Two adapters sharing a known 6-dim column subspace in R^512 must overlap fully."""
    rng = np.random.default_rng(0)
    d_out, k, r = 512, 6, 8
    U = orth(rng, d_out, k)
    X = adapter_from_basis(rng, U, r)
    Y = adapter_from_basis(rng, U, r)
    res = core.pair_overlap(X, Y, ["m"])
    pm = res["per_module"]["m"]
    assert pm["k_x"] == k and pm["k_y"] == k, f"k wrong: {pm}"
    assert abs(res["aggregate"] - 1.0) < tol, f"overlap {res['aggregate']} != 1"
    Q, kk = core.lowrank_colspace(X["m"]["A"], X["m"]["B"], 16.0, r)
    assert kk == k
    assert np.linalg.norm(Q - U @ (U.T @ Q)) < 1e-10, "Q does not lie in the planted subspace"
    assert np.linalg.norm(Q.T @ Q - np.eye(k)) < 1e-10, "Q not orthonormal"
    _, ang = core.principal_angles(Q, U)
    assert np.max(np.abs(ang)) < tol, f"angles to planted subspace: {ang}"


def check_loader_sha(tmp_path: Path):
    """Wrong sha and missing file must raise; right sha must return exactly what was stored."""
    rng = np.random.default_rng(1)
    A, B = rng.standard_normal((8, 40)), rng.standard_normal((24, 8))
    path, sha = write_adapter(tmp_path / "ad", {"mod.lora_A.weight": A, "mod.lora_B.weight": B})
    got = core.load_adapter(path, sha)
    np.testing.assert_allclose(got["mod"]["A"], A.astype(np.float32), rtol=0, atol=0)
    np.testing.assert_allclose(got["mod"]["B"], B.astype(np.float32), rtol=0, atol=0)
    bad = ("0" if sha[0] != "0" else "1") + sha[1:]
    try:
        core.load_adapter(path, bad)
    except Exception:
        pass
    else:
        raise AssertionError("wrong sha256 did not raise")
    try:
        core.load_adapter(tmp_path / "nope.safetensors", sha)
    except Exception:
        pass
    else:
        raise AssertionError("missing file did not raise")
