"""Engine tests for the minimal validity-profile engine (sca2_validity).

Mirrors the ideas extracted from cvprofiles: menu/roles, slack convention
s_r(m) >= -delta, M*, [L,U] = min/max beta on survivors, empty-M* honesty,
theta-grid as an additive diagnostic, and run-id discipline.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sca2_validity.engine import (
    Beta,
    Network,
    Restriction,
    Roles,
    SlackError,
    evaluate_slack,
    run_identify,
    run_theta_grid,
    slack_matrix,
)
from sca2_validity.freeze import compute_run_id, hash_payload


def _frame(n: int = 200, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=n)
    return pd.DataFrame(
        {
            "unit_id": np.arange(n),
            "m_clean": v + 0.3 * rng.normal(size=n),
            "m_noise": rng.normal(size=n),
            "m_slop": 0.9 * rng.normal(size=n) + 0.9 * (v + rng.normal(size=n)),
            "v_aux": v + 0.5 * rng.normal(size=n),
            "y": 0.6 * v + rng.normal(size=n),
            "g": rng.integers(0, 2, size=n),
        }
    )


def _roles() -> Roles:
    return Roles(
        unit_id="unit_id",
        measures=("m_clean", "m_noise", "m_slop"),
        aux=("v_aux",),
        outcome="y",
    )


def _network() -> Network:
    return Network(
        name="test_oracle",
        delta=0.0,
        restrictions=(
            Restriction(id="r_corr_min_aux", type="corr_min", theta=0.35, params={"variable": "v_aux"}),
            Restriction(id="r_corr_sign_aux", type="corr_sign", theta=0.10, params={"variable": "v_aux", "sign": 1}),
        ),
    )


def test_corr_min_signed_slack() -> None:
    df = _frame()
    r = Restriction(id="r1", type="corr_min", theta=0.0, params={"variable": "v_aux"})
    c = np.corrcoef(df["m_clean"], df["v_aux"])[0, 1]
    assert evaluate_slack(df["m_clean"].to_numpy(dtype=float), df, r) == pytest.approx(float(c))


def test_corr_abs_min_uses_absolute_value() -> None:
    df = _frame()
    # flip m_clean sign: correlation with v_aux becomes negative
    df["m_flip"] = -df["m_clean"]
    r = Restriction(id="r1", type="corr_abs_min", theta=0.30, params={"variable": "v_aux"})
    slack = evaluate_slack(df["m_flip"].to_numpy(dtype=float), df, r)
    assert slack >= 0.0  # abs(corr) high enough -> admissible


def test_unknown_restriction_fails_loud() -> None:
    df = _frame()
    r = Restriction(id="r1", type="rank_agree", theta=0.5, params={"ref_measure": "m_clean"})
    with pytest.raises(SlackError, match="no evaluator"):
        evaluate_slack(df["m_clean"].to_numpy(dtype=float), df, r)


def test_mean_order_slack_direction() -> None:
    df = _frame()
    r_up = Restriction(id="r_up", type="mean_order", theta=0.0, params={"group": "g", "direction": 1})
    r_dn = Restriction(id="r_dn", type="mean_order", theta=0.0, params={"group": "g", "direction": -1})
    df["m_hi_in_g1"] = df["g"] * 1.0
    s_up = evaluate_slack(df["m_hi_in_g1"].to_numpy(dtype=float), df, r_up)
    assert s_up > 0
    s_dn = evaluate_slack(df["m_hi_in_g1"].to_numpy(dtype=float), df, r_dn)
    assert s_dn < 0

def test_corr_min_signed_rejects_negative_correlation() -> None:
    df = _frame()
    df["m_flip"] = -df["m_clean"]
    r = Restriction(id="r1", type="corr_min", theta=0.30, params={"variable": "v_aux"})
    # signed floor: a negative correlation yields a negative slack (measure rejected by M*)
    slack = evaluate_slack(df["m_flip"].to_numpy(dtype=float), df, r)
    assert slack < 0.0


def test_identify_admissible_and_range() -> None:
    result = run_identify(_frame(), _roles(), _network(), beta=Beta(type="corr_y", outcome="y"))
    assert "m_clean" in result.admissible
    assert "m_noise" in result.rejected
    assert result.empty is False
    assert result.range_L is not None and result.range_U is not None
    assert result.range_L <= result.range_U
    # range is image of beta on survivors only
    b_star = [result.beta_values[m] for m in result.admissible]
    assert result.range_L == pytest.approx(min(b_star))
    assert result.range_U == pytest.approx(max(b_star))


def test_empty_m_star_is_honest_not_error() -> None:
    harsh = Network(
        name="harsh",
        delta=0.0,
        restrictions=(Restriction(id="r", type="corr_min", theta=0.99, params={"variable": "v_aux"}),),
    )
    result = run_identify(_frame(), _roles(), harsh)
    assert result.empty is True
    assert result.admissible == []
    assert result.range_L is None and result.range_U is None


def test_beta_optional_validity_only_profile() -> None:
    roles = Roles(unit_id="unit_id", measures=("m_clean", "m_noise"), aux=("v_aux",))
    result = run_identify(_frame(), roles, _network(), beta=None)
    assert result.beta_values is None
    assert result.range_L is None
    assert "m_clean" in result.admissible


def test_delta_tolerance() -> None:
    net = Network(
        name="tol",
        delta=0.05,
        restrictions=(Restriction(id="r", type="corr_min", theta=0.5, params={"variable": "v_aux"}),),
    )
    result = run_identify(_frame(), _roles(), net)
    # with tolerance some near-miss may pass; the rule is s >= -delta
    for m in result.admissible:
        assert float(result.slacks.at[m, "r"]) >= -0.05


def test_theta_grid_lambda_1_is_headline() -> None:
    frame, roles, net = _frame(), _roles(), _network()
    grid = run_theta_grid(frame, roles, net, [0.5, 1.0, 2.0])
    rows = {row.lambda_value: row for row in grid.rows}
    assert rows[1.0].admissible == run_identify(frame, roles, net).admissible
    # stricter thresholds cannot admit more measures than the baseline
    assert set(rows[2.0].admissible) <= set(rows[1.0].admissible)
    assert set(rows[0.5].admissible) >= set(rows[1.0].admissible)


def test_hash_payload_stable_and_sensitive() -> None:
    a = hash_payload({"x": [1, 2], "y": "z"})
    b = hash_payload({"x": [1, 2], "y": "z"})
    c = hash_payload({"x": [1, 2], "y": "w"})
    assert a == b
    assert a != c


def test_run_id_changes_with_network_not_grid() -> None:
    net_a = _network()
    net_b = Network(name="other", delta=0.0, restrictions=net_a.restrictions)
    base = compute_run_id(hash_payload({"s": 1}), hash_payload(net_a), hash_payload({"p": 1}), seed=0)
    with_other_net = compute_run_id(hash_payload({"s": 1}), hash_payload(net_b), hash_payload({"p": 1}), seed=0)
    same_again = compute_run_id(hash_payload({"s": 1}), hash_payload(net_a), hash_payload({"p": 1}), seed=0)
    assert base == same_again
    assert base != with_other_net
