"""Conservation tests for the SCA2 workbench hooks.

RED by design. ``workbench/src/sca2_workbench/hooks.py`` does not exist yet, so
this file fails at import until the hook is implemented (t_f53c6218). These
tests pin the frozen API and the conservation equations recorded in
``workbench/spec/conservation.md`` so the implementation has a contract.

The hand-computed fixtures below are derived with plain Python (stdlib only) so
the test file carries no heavy dependency; the hook itself may use torch/numpy.
"""

from __future__ import annotations

import math

import pytest

from sca2_workbench.hooks import (
    clamp_quadrant_iii,
    dla_abs_gap,
    residual_inf_norm,
    swiglu_poles,
)

TOL_RESIDUAL = 1e-3
TOL_DLA = 1e-2
EPS = 0.05


def _silu(z: float) -> float:
    """SiLU(z) = z * sigmoid(z), used only to build hand-checked expectations."""
    return z / (1.0 + math.exp(-z))


# ---------------------------------------------------------------------------
# Fixture 1 - residual stream conservation.
#   h_final - (h0 + attn_sum + mlp_sum) has inf-norm < 1e-3 when it closes.
# ---------------------------------------------------------------------------
H0 = [0.1, -0.2, 0.3, 0.5]
ATTN_SUM = [0.05, 0.1, -0.1, 0.0]
MLP_SUM = [0.02, -0.03, 0.04, -0.01]
# h0 + attn_sum + mlp_sum, term by term: exact conservation.
H_FINAL = [0.17, -0.13, 0.24, 0.49]


def test_residual_inf_norm_conserves():
    r = residual_inf_norm(H0, ATTN_SUM, MLP_SUM, H_FINAL)
    assert r == pytest.approx(0.0, abs=TOL_RESIDUAL)


def test_residual_inf_norm_is_the_max_absolute_component():
    # Last component off by 0.009, everything else exact -> inf-norm is 0.009.
    perturbed = [0.17, -0.13, 0.24, 0.49 - 0.009]
    r = residual_inf_norm(H0, ATTN_SUM, MLP_SUM, perturbed)
    assert r == pytest.approx(0.009, abs=1e-9)


# ---------------------------------------------------------------------------
# Fixture 2 - Direct Logit Attribution conservation.
#   |logit_margin - attr_sum| < 1e-2.
# ---------------------------------------------------------------------------
def test_dla_abs_gap_value():
    assert dla_abs_gap(2.500, 2.495) == pytest.approx(0.005, abs=1e-9)


def test_dla_abs_gap_within_tolerance():
    gap = dla_abs_gap(2.500, 2.495)
    assert gap < TOL_DLA


# ---------------------------------------------------------------------------
# Fixture 3 - SwiGLU poles. One hand-computed neuron in quadrant III.
#
#   Convention: x is shape (n_features,); w_gate / w_up are
#   (n_features, n_neurons) so column i is neuron i.
#   g_tilde_i = x . W_gate[:, i]      u_i = x . W_up[:, i]
#   c_i       = SiLU(g_tilde_i) * u_i
#   quadrant III: g_tilde_i < -0.05 AND u_i < -0.05
#
#   x = [1.0, 1.0]
#   W_gate col 0 = [1, 0]  -> g_0 = 1.0   W_up col 0 = [1, 1]   -> u_0 = 2.0
#   W_gate col 1 = [-1, -2] -> g_1 = -3.0 W_up col 1 = [-2, -1] -> u_1 = -3.0
#
#   c_0 = SiLU(1.0)  *  2.0 =  1.4621171572600098
#   c_1 = SiLU(-3.0) * -3.0 =  0.42683285859810105   (> 0 before the clamp)
# ---------------------------------------------------------------------------
X = [1.0, 1.0]
W_GATE = [[1.0, -1.0], [0.0, -2.0]]
W_UP = [[1.0, -2.0], [1.0, -1.0]]

G_TILDE_EXPECTED = [1.0, -3.0]
U_EXPECTED = [2.0, -3.0]
C_EXPECTED = [1.4621171572600098, 0.42683285859810105]
QUADRANT_III_EXPECTED = [False, True]


def test_swiglu_poles_match_hand_computed_values():
    out = swiglu_poles(X, W_GATE, W_UP)
    assert list(out["g_tilde"]) == pytest.approx(G_TILDE_EXPECTED)
    assert list(out["u"]) == pytest.approx(U_EXPECTED)
    assert list(out["c"]) == pytest.approx(C_EXPECTED)
    assert [bool(q) for q in out["quadrant_iii"]] == QUADRANT_III_EXPECTED


def test_quadrant_iii_neuron_product_is_positive_before_clamp():
    out = swiglu_poles(X, W_GATE, W_UP)
    assert bool(out["quadrant_iii"][1]) is True
    assert float(out["c"][1]) > 0.0
    assert float(out["c"][1]) == pytest.approx(_silu(-3.0) * -3.0)


def test_clamp_quadrant_iii_zeroes_the_quadrant_iii_product():
    clamped = list(clamp_quadrant_iii(G_TILDE_EXPECTED, U_EXPECTED, eps=EPS))
    # quadrant-III neuron: positive product -> 0
    assert clamped[1] == pytest.approx(0.0)
    # non quadrant-III neuron: untouched
    assert clamped[0] == pytest.approx(C_EXPECTED[0])


def test_clamp_quadrant_iii_respects_eps():
    # g = -0.04, u = -1.0: g is NOT below -eps, so the neuron is not clamped.
    g = [-0.04]
    u = [-1.0]
    clamped = list(clamp_quadrant_iii(g, u, eps=EPS))
    assert clamped[0] == pytest.approx(_silu(-0.04) * -1.0)