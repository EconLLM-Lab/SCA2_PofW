import numpy as np
import pytest

from w3b import core
import checks
from checks import orth, adapter_from_basis


# ------------------------------------------------------------------ planted / known
def test_planted_subspace():
    checks.check_planted_subspace()


def test_planted_subspace_disjoint_is_zero():
    """Orthogonal subspaces: overlap 0 and angles pi/2 (the other end of the scale)."""
    rng = np.random.default_rng(2)
    U = orth(rng, 512, 12)
    X = adapter_from_basis(rng, U[:, :6], 8)
    Y = adapter_from_basis(rng, U[:, 6:], 8)
    res = core.pair_overlap(X, Y, ["m"])
    assert res["aggregate"] < 1e-20
    assert abs(res["min_angle"] - np.pi / 2) < 1e-8


def test_known_principal_angles_recovered():
    rng = np.random.default_rng(3)
    d, theta = 512, np.array([0.0, 1e-9, 0.1, 0.4, 0.9, 1.3])
    k = len(theta)
    # U1 = e_1..e_k ; U2 column i = cos(theta_i) e_i + sin(theta_i) e_{k+i}  (angles exactly theta)
    U1, U2 = np.zeros((d, k)), np.zeros((d, k))
    for i, t in enumerate(theta):
        U1[i, i] = 1.0
        U2[i, i], U2[k + i, i] = np.cos(t), np.sin(t)
    Rot = orth(rng, d, d)                      # random rotation hides the coordinate structure
    X = adapter_from_basis(rng, Rot @ U1, 8, name="m")
    Y = adapter_from_basis(rng, Rot @ U2, 8, name="m")
    Qx, kx = core.lowrank_colspace(X["m"]["A"], X["m"]["B"], 16.0, 8)
    Qy, ky = core.lowrank_colspace(Y["m"]["A"], Y["m"]["B"], 16.0, 8)
    assert kx == ky == k
    cos, ang = core.principal_angles(Qx, Qy)
    np.testing.assert_allclose(np.sort(ang), np.sort(theta), rtol=0, atol=1e-8)
    np.testing.assert_allclose(np.sort(cos), np.sort(np.cos(theta)), rtol=0, atol=1e-12)
    res = core.pair_overlap(X, Y, ["m"])
    assert abs(res["aggregate"] - np.mean(np.cos(theta) ** 2)) < 1e-10
    assert abs(res["min_angle"] - 0.0) < 1e-8


def test_unequal_k_angles_symmetric():
    rng = np.random.default_rng(4)
    U = orth(rng, 128, 5)
    Q1, Q2 = U, U[:, :3]
    c12, a12 = core.principal_angles(Q1, Q2)
    c21, a21 = core.principal_angles(Q2, Q1)
    assert len(a12) == len(a21) == 3
    np.testing.assert_allclose(a12, a21, atol=1e-12)
    assert np.max(a12) < 1e-8


def test_random_baseline_matches_k_over_d_and_is_distinguishable():
    d, k, r, trials = 512, 8, 8, 300
    rng = np.random.default_rng(5)
    vals = []
    for _ in range(trials):
        X = adapter_from_basis(rng, rng.standard_normal((d, k)), r)
        Y = adapter_from_basis(rng, rng.standard_normal((d, k)), r)
        vals.append(core.pair_overlap(X, Y, ["m"])["aggregate"])
    vals = np.array(vals)
    expected = k / d                           # E||Q1^T Q2||_F^2 = k1 k2 / d, divided by min(k)
    se = vals.std(ddof=1) / np.sqrt(trials)
    assert abs(vals.mean() - expected) < max(5 * se, 0.1 * expected), (vals.mean(), expected, se)
    planted = 1.0                              # checks.check_planted_subspace
    assert vals.max() < 0.1 and planted - vals.mean() > 0.95


# ----------------------------------------------------------------- algebra properties
def test_matches_dense_svd_small():
    rng = np.random.default_rng(6)
    for rank_B in (5, 3):                      # full and deficient
        d_out, d_in, r = 40, 30, 5
        B = rng.standard_normal((d_out, rank_B)) @ rng.standard_normal((rank_B, r))
        A = rng.standard_normal((r, d_in))
        Q, k = core.lowrank_colspace(A, B, 10.0, r)
        U, S, _ = np.linalg.svd((10.0 / r) * (B @ A), full_matrices=False)   # dense reference
        k_ref = int(np.sum(S > 1e-8 * S[0]))
        assert k == k_ref == rank_B
        np.testing.assert_allclose(Q @ Q.T, U[:, :k] @ U[:, :k].T, atol=1e-10)


def test_scaling_invariance():
    rng = np.random.default_rng(7)
    A, B = rng.standard_normal((8, 50)), rng.standard_normal((60, 8))
    Q0, k0 = core.lowrank_colspace(A, B, 16.0, 8)
    for alpha in (1e-3, 1.0, 8.0, 1e4):
        Q, k = core.lowrank_colspace(A, B, alpha, 8)
        assert k == k0
        np.testing.assert_allclose(Q @ Q.T, Q0 @ Q0.T, atol=1e-10)


@pytest.mark.parametrize("which", ["B_rank3", "A_rank2", "both_zero_B"])
def test_rank_deficiency_reduces_k(which):
    rng = np.random.default_rng(8)
    r, d_out, d_in = 8, 64, 80
    A = rng.standard_normal((r, d_in))
    B = rng.standard_normal((d_out, r))
    if which == "B_rank3":
        B = rng.standard_normal((d_out, 3)) @ rng.standard_normal((3, r)); want = 3
    elif which == "A_rank2":
        A = rng.standard_normal((r, 2)) @ rng.standard_normal((2, d_in)); want = 2
    else:
        B = np.zeros((d_out, r)); want = 0
    Q, k = core.lowrank_colspace(A, B, 16.0, r)
    assert k == want and Q.shape == (d_out, want)
    if want:
        # Q really spans col(BA): residual of the dense product is ~0
        D = B @ A
        assert np.linalg.norm(D - Q @ (Q.T @ D)) < 1e-9 * np.linalg.norm(D)


def test_rel_tol_threshold_controls_k():
    rng = np.random.default_rng(9)
    Qb = orth(rng, 64, 4)
    B = Qb * np.array([1.0, 1.0, 1.0, 1e-12])  # one tiny singular direction
    A = orth(rng, 80, 4).T
    assert core.lowrank_colspace(A, B, 4.0, 4, rel_tol=1e-8)[1] == 3
    assert core.lowrank_colspace(A, B, 4.0, 4, rel_tol=1e-14)[1] == 4


def test_pair_overlap_guards_and_pluggable_aggregate():
    rng = np.random.default_rng(10)
    U = orth(rng, 64, 4)
    X = {**adapter_from_basis(rng, U, 4, name="a"), **adapter_from_basis(rng, orth(rng, 64, 4), 4, name="b")}
    Y = {**adapter_from_basis(rng, U, 4, name="a"), **adapter_from_basis(rng, orth(rng, 64, 4), 4, name="b")}
    res = core.pair_overlap(X, Y, ["a", "b"])
    ov = {m: v["overlap"] for m, v in res["per_module"].items()}
    assert abs(ov["a"] - 1) < 1e-10 and ov["b"] < 0.5
    assert abs(res["aggregate"] - np.mean(list(ov.values()))) < 1e-14       # unweighted mean
    assert core.pair_overlap(X, Y, ["a", "b"], aggregate=lambda d: max(d.values()))["aggregate"] == pytest.approx(ov["a"])
    with pytest.raises(KeyError):
        core.pair_overlap(X, Y, ["a", "zzz"])
    with pytest.raises(ValueError):
        core.pair_overlap(X, Y, [])
    Z = adapter_from_basis(rng, U, 4, name="a"); Z["a"]["B"] = np.zeros_like(Z["a"]["B"])
    with pytest.raises(ValueError):
        core.pair_overlap(X, Z, ["a"])         # zero-rank: undefined, not silently 0 or nan


def test_lowrank_colspace_rejects_bad_input():
    with pytest.raises(ValueError):
        core.lowrank_colspace(np.ones((4, 10)), np.ones((10, 3)), 8.0, 4)   # r mismatch
    with pytest.raises(ValueError):
        core.lowrank_colspace(np.full((4, 10), np.nan), np.ones((10, 4)), 8.0, 4)


# ------------------------------------------------------------------------ loader
def test_loader_integrity(tmp_path):
    checks.check_loader_sha(tmp_path)


def test_loader_error_types_and_structure(tmp_path):
    rng = np.random.default_rng(11)
    t = {"x.lora_A.weight": rng.standard_normal((8, 20)), "x.lora_B.weight": rng.standard_normal((12, 8)),
         "y.lora_A.weight": rng.standard_normal((8, 20)), "y.lora_B.weight": rng.standard_normal((12, 8))}
    p, sha = checks.write_adapter(tmp_path / "a", t, alpha=32, r=8)
    ad = core.load_adapter(p, sha)
    assert set(ad) == {"x", "y"} and ad["x"]["alpha"] == 32.0 and ad["x"]["r"] == 8
    assert ad["x"]["A"].shape == (8, 20) and ad["x"]["B"].shape == (12, 8) and ad["x"]["A"].dtype == np.float64
    with pytest.raises(core.ShaMismatchError):
        core.load_adapter(p, "0" * 64)
    with pytest.raises(ValueError):
        core.load_adapter(p, "not-a-digest")
    with pytest.raises(FileNotFoundError):
        core.load_adapter(tmp_path / "missing.safetensors", sha)
    with pytest.raises(KeyError):
        core.load_adapter(p, sha, modules=["x", "absent"])             # missing module is loud
    assert set(core.load_adapter(p, sha, modules=["y"])) == {"y"}
    # config r disagrees with tensor shapes
    p2, sha2 = checks.write_adapter(tmp_path / "b", t, alpha=32, r=4)
    with pytest.raises(ValueError):
        core.load_adapter(p2, sha2)
    # no config at all
    p3, sha3 = checks.write_adapter(tmp_path / "c", t, config=False)
    with pytest.raises(FileNotFoundError):
        core.load_adapter(p3, sha3)
    # unpaired tensors
    p4, sha4 = checks.write_adapter(tmp_path / "d", {"x.lora_A.weight": t["x.lora_A.weight"]})
    with pytest.raises(KeyError):
        core.load_adapter(p4, sha4)
    # no LoRA tensors
    p5, sha5 = checks.write_adapter(tmp_path / "e", {"other.weight": t["x.lora_A.weight"]})
    with pytest.raises(KeyError):
        core.load_adapter(p5, sha5)


def test_loader_run_record_fallback_and_end_to_end(tmp_path):
    import json
    rng = np.random.default_rng(12)
    U = orth(rng, 96, 5)
    paths = []
    for i in range(2):
        d = tmp_path / f"p{i}"
        ad = adapter_from_basis(rng, U, 8, name="mod")["mod"]
        p, sha = checks.write_adapter(d, {"mod.lora_A.weight": ad["A"], "mod.lora_B.weight": ad["B"]}, config=False)
        (d / "run_record.json").write_text(json.dumps({"lora": {"r": 8, "alpha": 16}}))
        paths.append((p, sha))
    X, Y = (core.load_adapter(p, s) for p, s in paths)
    assert X["mod"]["alpha"] == 16.0
    # float32 storage turns the exact rank-5 delta into rank 8 at ~1e-7 relative; rel_tol must
    # sit above storage precision (bf16 ~1e-3, fp32 ~1e-7) or the "extra" directions are noise.
    res = core.pair_overlap(X, Y, ["mod"], rel_tol=1e-5)
    assert res["per_module"]["mod"]["k_x"] == 5
    assert abs(res["aggregate"] - 1.0) < 1e-5
    assert core.pair_overlap(X, Y, ["mod"], rel_tol=1e-10)["per_module"]["mod"]["k_x"] == 8


# -------------------------------------------------------------- stub detector
def _random_stub_lowrank(A, B, alpha, r, rel_tol=1e-8):
    rng = np.random.default_rng()
    Q, _ = np.linalg.qr(rng.standard_normal((np.asarray(B).shape[0], r)))
    return Q, r


def _random_stub_loader(path, expected_sha256, modules=None):
    rng = np.random.default_rng()
    return {"mod": {"A": rng.standard_normal((8, 40)), "B": rng.standard_normal((24, 8)), "alpha": 16.0, "r": 8}}


def test_stub_detector_random_colspace_fails_planted_check(monkeypatch):
    monkeypatch.setattr(core, "lowrank_colspace", _random_stub_lowrank)
    with pytest.raises(AssertionError):
        checks.check_planted_subspace()


def test_stub_detector_random_loader_fails_sha_check(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "load_adapter", _random_stub_loader)
    with pytest.raises(AssertionError):
        checks.check_loader_sha(tmp_path)


def test_stub_detector_checks_pass_on_real_core_then_fail_on_stub(monkeypatch, tmp_path):
    """Same checks, same process: pass on the real core, fail once it is swapped."""
    if core.lowrank_colspace is _random_stub_lowrank or core.lowrank_colspace.__name__.startswith("stub_"):
        pytest.fail("a stub is installed in w3b.core (W3B_INJECT_STUB); the real-core half cannot run")
    checks.check_planted_subspace()
    checks.check_loader_sha(tmp_path)
    monkeypatch.setattr(core, "lowrank_colspace", _random_stub_lowrank)
    with pytest.raises(AssertionError):
        checks.check_planted_subspace()
