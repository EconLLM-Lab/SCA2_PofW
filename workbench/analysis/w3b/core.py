"""Low-rank LoRA column-space algebra for W3b.

The delta of a LoRA module is  s * B @ A  with s = alpha / r,  A (r x d_in),
B (d_out x r).  The d_out x d_in product is never formed (4096 x 14336 float64 is
~470 MB).  Column space of B @ A:

    B = Q_B R_B                 (thin QR, Q_B d_out x r)
    R_B @ A = U S V^T           (SVD of an r x d_in matrix)
    col(B A) = Q_B @ U[:, :k]   k = #{ S_i > rel_tol * S_0 }

Everything here is float64.  Nothing falls back to random or empty data: bad
input raises.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np

DEFAULT_REL_TOL = 1e-8
LORA_A_SUFFIX = ".lora_A.weight"
LORA_B_SUFFIX = ".lora_B.weight"


class ShaMismatchError(ValueError):
    """The adapter file's sha256 differs from the pinned one."""


# --------------------------------------------------------------------------- loader
def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _read_lora_config(adapter_dir: Path) -> tuple[float, int]:
    """(alpha, r) from adapter_config.json (PEFT), else run_record.json['lora'].

    The Bank-2 snapshot ships run_record.json with lora.{alpha,r} and no
    adapter_config.json; that is the only fallback, and it is read, not guessed.
    """
    cfg_path = adapter_dir / "adapter_config.json"
    rec_path = adapter_dir / "run_record.json"
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text())
        for key in ("rank_pattern", "alpha_pattern"):
            if cfg.get(key):
                raise NotImplementedError(f"{key} (per-module rank/alpha) is not supported")
        missing = [k for k in ("r", "lora_alpha") if k not in cfg]
        if missing:
            raise KeyError(f"{cfg_path} lacks {missing}")
        return float(cfg["lora_alpha"]), int(cfg["r"])
    if rec_path.is_file():
        lora = json.loads(rec_path.read_text()).get("lora")
        if not isinstance(lora, dict) or "alpha" not in lora or "r" not in lora:
            raise KeyError(f"{rec_path} has no lora.{{alpha,r}}")
        return float(lora["alpha"]), int(lora["r"])
    raise FileNotFoundError(f"no adapter_config.json or run_record.json beside {adapter_dir}")


def load_adapter(path, expected_sha256: str, modules: Sequence[str] | None = None) -> dict:
    """Load a LoRA adapter safetensors file after verifying its sha256.

    Returns {module_name: {"A": (r,d_in) f64, "B": (d_out,r) f64, "alpha": float, "r": int}}.
    module_name is the key with '.lora_A.weight' / '.lora_B.weight' stripped.
    `modules=None` loads every module found.  Raises on: missing file, bad/mismatching
    sha, missing config, A without B (or B without A), requested module absent,
    shapes inconsistent with r, no modules at all.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"adapter file not found: {path}")
    expected = str(expected_sha256).strip().lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError(f"expected_sha256 is not a 64-char hex digest: {expected_sha256!r}")
    actual = sha256_file(path)
    if actual != expected:
        raise ShaMismatchError(f"sha256 mismatch for {path}: expected {expected}, got {actual}")
    alpha, r = _read_lora_config(path.parent)

    import torch  # lazy: bf16 tensors cannot go through numpy directly
    from safetensors import safe_open

    out: dict = {}
    with safe_open(str(path), framework="pt") as f:
        keys = set(f.keys())
        a_mods = {k[: -len(LORA_A_SUFFIX)] for k in keys if k.endswith(LORA_A_SUFFIX)}
        b_mods = {k[: -len(LORA_B_SUFFIX)] for k in keys if k.endswith(LORA_B_SUFFIX)}
        if a_mods != b_mods:
            raise KeyError(f"unpaired LoRA tensors: A-only={sorted(a_mods - b_mods)[:5]}, "
                           f"B-only={sorted(b_mods - a_mods)[:5]}")
        if not a_mods:
            raise KeyError(f"{path} contains no lora_A/lora_B tensors")
        wanted = sorted(a_mods) if modules is None else list(modules)
        absent = [m for m in wanted if m not in a_mods]
        if absent:
            raise KeyError(f"modules missing from {path}: {absent[:5]}{' ...' if len(absent) > 5 else ''}")
        for m in wanted:
            A = f.get_tensor(m + LORA_A_SUFFIX).to(torch.float64).numpy()
            B = f.get_tensor(m + LORA_B_SUFFIX).to(torch.float64).numpy()
            if A.ndim != 2 or B.ndim != 2 or A.shape[0] != r or B.shape[1] != r:
                raise ValueError(f"{m}: A{A.shape}/B{B.shape} inconsistent with config r={r}")
            out[m] = {"A": A, "B": B, "alpha": alpha, "r": r}
    return out


# ----------------------------------------------------------------------- column space
def lowrank_colspace(A, B, alpha: float, r: int, rel_tol: float = DEFAULT_REL_TOL):
    """Orthonormal basis Q (d_out x k) of col((alpha/r) B A), and k.  float64.

    Never forms B @ A.  k is the numerical rank: singular values of R_B A above
    rel_tol times the largest.  A zero delta gives k = 0 and an empty Q.
    """
    A = np.asarray(A, dtype=np.float64)
    B = np.asarray(B, dtype=np.float64)
    if A.ndim != 2 or B.ndim != 2 or A.shape[0] != r or B.shape[1] != r:
        raise ValueError(f"shape mismatch: A{A.shape}, B{B.shape}, r={r}")
    if not (np.isfinite(A).all() and np.isfinite(B).all()):
        raise ValueError("non-finite entries in A or B")
    scale = float(alpha) / r
    Qb, Rb = np.linalg.qr(B, mode="reduced")            # d_out x r, r x r
    U, S, _ = np.linalg.svd(scale * (Rb @ A), full_matrices=False)  # r x d_in
    if S.size == 0 or S[0] == 0.0:
        return np.zeros((B.shape[0], 0)), 0
    k = int(np.sum(S > rel_tol * S[0]))
    return Qb @ U[:, :k], k


def principal_angles(Q1, Q2):
    """(cosines, angles) between col(Q1) and col(Q2); both orthonormal bases.

    cosines = singular values of Q1^T Q2 clipped to [0, 1], descending.
    angles  = accurate to ~1e-16 absolute even near 0 (arccos alone is only good
    to ~1.5e-8 there): theta_i = arctan2(sin_i, cos_i), sines from the residual
    Q2 - Q1 Q1^T Q2 (Bjorck-Golub / Knyazev-Argentati).  Length min(k1, k2).
    """
    Q1 = np.asarray(Q1, dtype=np.float64)
    Q2 = np.asarray(Q2, dtype=np.float64)
    if Q1.shape[0] != Q2.shape[0]:
        raise ValueError(f"ambient dimensions differ: {Q1.shape[0]} vs {Q2.shape[0]}")
    if Q1.shape[1] < Q2.shape[1]:       # residual trick needs the smaller basis as Q2
        Q1, Q2 = Q2, Q1
    if Q2.shape[1] == 0:
        return np.zeros(0), np.zeros(0)
    C = Q1.T @ Q2
    cos = np.clip(np.linalg.svd(C, compute_uv=False), 0.0, 1.0)            # descending
    sin = np.clip(np.linalg.svd(Q2 - Q1 @ C, compute_uv=False), 0.0, 1.0)   # descending
    angles = np.arctan2(sin[::-1], cos)     # largest cosine <-> smallest sine
    return cos, angles


# ---------------------------------------------------------------------------- overlap
def mean_aggregate(per_module_overlap: Mapping[str, float]) -> float:
    """Default aggregation: unweighted mean over modules."""
    return float(np.mean(list(per_module_overlap.values())))


def pair_overlap(adapter_x: Mapping, adapter_y: Mapping, modules: Sequence[str],
                 rel_tol: float = DEFAULT_REL_TOL,
                 aggregate: Callable[[Mapping[str, float]], float] = mean_aggregate) -> dict:
    """Per-module normalised overlap ||Q1^T Q2||_F^2 / min(k1,k2) between two adapters.

    `adapter_*` are load_adapter() outputs.  `aggregate` maps {module: overlap} to a
    float (swap it to follow W3b_PREREG.md).  Raises on missing modules, mismatched
    d_out, empty module list, or a zero-rank module (overlap undefined).
    Returns {"per_module": {m: {"overlap","min_angle","k_x","k_y"}},
             "aggregate": float, "min_angle": float (smallest over modules)}.
    """
    modules = list(modules)
    if not modules:
        raise ValueError("modules is empty")
    per: dict = {}
    for m in modules:
        for name, ad in (("x", adapter_x), ("y", adapter_y)):
            if m not in ad:
                raise KeyError(f"module {m!r} missing from adapter {name}")
        mx, my = adapter_x[m], adapter_y[m]
        Q1, k1 = lowrank_colspace(mx["A"], mx["B"], mx["alpha"], mx["r"], rel_tol)
        Q2, k2 = lowrank_colspace(my["A"], my["B"], my["alpha"], my["r"], rel_tol)
        if min(k1, k2) == 0:
            raise ValueError(f"{m}: zero-rank delta (k_x={k1}, k_y={k2}); overlap undefined")
        cos, ang = principal_angles(Q1, Q2)
        per[m] = {"overlap": float(np.sum(cos ** 2) / min(k1, k2)),
                  "min_angle": float(ang.min()), "k_x": k1, "k_y": k2}
    return {"per_module": per,
            "aggregate": float(aggregate({m: v["overlap"] for m, v in per.items()})),
            "min_angle": float(min(v["min_angle"] for v in per.values()))}
