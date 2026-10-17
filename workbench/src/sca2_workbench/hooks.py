"""Tensor conservation hooks for the SCA2 workbench (slice 1).

Frozen API and equations: ``workbench/spec/conservation.md``.
The contract the tests pin: ``workbench/tests/test_conservation.py``.

Convention: ``x`` has shape ``(n_features,)``; ``w_gate`` / ``w_up`` have shape
``(n_features, n_neurons)``, so column ``i`` is neuron ``i``.

Inputs may be plain Python sequences, numpy arrays or torch tensors (anything
exposing ``tolist``); outputs are plain lists of Python floats, so this module
pulls in no tensor framework of its own.
"""

from __future__ import annotations

import math
from typing import Any

#: Quadrant III is ``g_tilde < -EPS_QUADRANT_III and u < -EPS_QUADRANT_III``.
EPS_QUADRANT_III = 0.05


def _as_float_list(values: Any) -> list:
    """Vector -> list of Python floats (accepts sequences, numpy arrays, torch tensors)."""
    tolist = getattr(values, "tolist", None)
    if callable(tolist):
        values = tolist()
    return [float(v) for v in values]


def _as_float_matrix(values: Any) -> list:
    """Matrix -> list of lists of Python floats (same accepted inputs as above)."""
    tolist = getattr(values, "tolist", None)
    if callable(tolist):
        values = tolist()
    return [[float(v) for v in row] for row in values]


def _silu(z: float) -> float:
    """``SiLU(z) = z * sigmoid(z)`` — the Swish in the brief.

    Split at ``z = 0`` so large |z| cannot overflow ``exp``: the naive form
    ``z / (1 + exp(-z))`` raises OverflowError for z below about -709.
    """
    if z >= 0.0:
        return z / (1.0 + math.exp(-z))
    e = math.exp(z)
    return z * e / (1.0 + e)


def _columns(gate: list, up: list, x: list) -> tuple:
    """Column-wise dot products ``x . gate[:, i]`` and ``x . up[:, i]`` for every neuron i."""
    n_features = len(x)
    n_neurons = len(gate[0]) if gate else 0
    if (len(up[0]) if up else 0) != n_neurons:
        raise ValueError(
            "w_gate and w_up must have the same shape (n_features, n_neurons); got "
            f"{n_neurons} and {len(up[0]) if up else 0} neurons"
        )
    for name, matrix in (("w_gate", gate), ("w_up", up)):
        for j, row in enumerate(matrix):
            if len(row) != n_neurons:
                raise ValueError(f"{name} row {j} holds {len(row)} entries; expected {n_neurons}")
    g_tilde = [sum(x[j] * gate[j][i] for j in range(n_features)) for i in range(n_neurons)]
    u = [sum(x[j] * up[j][i] for j in range(n_features)) for i in range(n_neurons)]
    return g_tilde, u


def residual_inf_norm(h0, attn_sum, mlp_sum, h_final) -> float:
    """``inf_norm(h_final - (h0 + attn_sum + mlp_sum))``.

    Zero (within round-off) means the residual stream closes.
    """
    h0_l = _as_float_list(h0)
    attn_l = _as_float_list(attn_sum)
    mlp_l = _as_float_list(mlp_sum)
    final_l = _as_float_list(h_final)
    lengths = (len(h0_l), len(attn_l), len(mlp_l), len(final_l))
    if len(set(lengths)) != 1:
        raise ValueError(f"all four vectors must have the same length; got {lengths}")
    if not final_l:
        return 0.0
    return max(abs(f - (a + m + c)) for f, a, m, c in zip(final_l, attn_l, mlp_l, h0_l))


def dla_abs_gap(logit_margin, attr_sum) -> float:
    """``abs(logit_margin - attr_sum)``: the direct logit attribution closure gap."""
    return abs(float(logit_margin) - float(attr_sum))


def swiglu_poles(x, w_gate, w_up) -> dict:
    """Per-neuron SwiGLU poles, before any clamp.

    ``g_tilde_i = x . w_gate[:, i]``, ``u_i = x . w_up[:, i]``,
    ``c_i = SiLU(g_tilde_i) * u_i``. ``quadrant_iii_i`` is True when both poles sit
    below ``-EPS_QUADRANT_III``. ``c`` is deliberately the *unclamped* product, so a
    quadrant-III neuron can carry a positive value there; ``clamp_quadrant_iii``
    is what zeroes it.
    """
    x_l = _as_float_list(x)
    gate = _as_float_matrix(w_gate)
    up = _as_float_matrix(w_up)
    if len(gate) != len(x_l) or len(up) != len(x_l):
        raise ValueError(
            f"w_gate and w_up must have {len(x_l)} rows (n_features); got {len(gate)} and {len(up)}"
        )
    g_tilde, u = _columns(gate, up, x_l)
    c = [_silu(g) * ui for g, ui in zip(g_tilde, u)]
    quadrant_iii = [
        g < -EPS_QUADRANT_III and ui < -EPS_QUADRANT_III for g, ui in zip(g_tilde, u)
    ]
    return {"g_tilde": g_tilde, "u": u, "c": c, "quadrant_iii": quadrant_iii}


def clamp_quadrant_iii(g_tilde, u, eps: float = 0.05) -> list:
    """``SiLU(g_tilde_i) * u_i`` with quadrant-III products set to 0.

    A neuron is quadrant III when ``g_tilde_i < -eps and u_i < -eps``. Those
    products are positive (two negative poles) yet are the destructive ones, so
    they are the ones the clamp removes.
    """
    g_l = _as_float_list(g_tilde)
    u_l = _as_float_list(u)
    if len(g_l) != len(u_l):
        raise ValueError(f"g_tilde and u must have the same length; got {len(g_l)} and {len(u_l)}")
    return [
        0.0 if (g < -eps and ui < -eps) else _silu(g) * ui
        for g, ui in zip(g_l, u_l)
    ]
