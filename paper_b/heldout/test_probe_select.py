"""Probe-selection tests (synthetic values only; no human data)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import probe_select as P  # noqa: E402


def _frame(signal: float, item: str = "Q150") -> pd.DataFrame:
    import factorial as F
    rng = np.random.default_rng(1)
    rows = []
    for u in F.all_units():
        bits = np.array(F.bits_of_unit(u), dtype=float)
        y = signal * bits[0] + 0.05 * rng.normal()          # trust bit dominates
        rows.append({"unit": u, "item": item, "value": float(y)})
    return pd.DataFrame(rows)


def test_probe_recovers_the_planted_dimension():
    row = P.effects(_frame(1.0)).iloc[0]
    assert row["question_id"] == "Q150"
    assert row["top_dimension"] == "trust"
    assert row["t_top"] > 3
    assert row["error_df"] == 42           # 64 units - 1 - 6 - 15 parameters


def test_negative_effects_count_by_magnitude():
    row = P.effects(_frame(-1.0)).iloc[0]
    assert row["top_dimension"] == "trust" and row["t_top"] < -3


def test_null_items_are_flagged_at_the_familywise_rate():
    """|t| >= 2 on any of 6 dimensions: about 1 - 0.95**6 = 26% of pure-noise items.

    The selection rule does not control this rate; the permutation null over items
    in the human-criterion analysis does. This test documents the rate honestly.
    """
    import factorial as F
    rng = np.random.default_rng(0)
    rows = [{"unit": u, "item": f"N{k:03d}", "value": float(rng.normal())}
            for k in range(400) for u in F.all_units()]
    out = P.effects(pd.DataFrame(rows))
    rate = float((out.top_dimension != "none").mean())
    assert 0.18 < rate < 0.36, rate


def test_missing_unit_refused():
    df = _frame(1.0).iloc[1:]
    import pytest
    with pytest.raises(ValueError, match="missing units"):
        P.effects(df)


def test_secondary_rule_requires_imprint_and_threshold():
    df = pd.DataFrame([
        {"question_id": "Q1", "top_dimension": "trust", "t_top": 5.0},
        {"question_id": "Q2", "top_dimension": "patience", "t_top": 9.0},
        {"question_id": "Q3", "top_dimension": "altruism", "t_top": 1.0},
        {"question_id": "Q4", "top_dimension": "posrecip", "t_top": -4.0},
    ])
    assert P.select(df, t_crit=3.0) == ["Q1", "Q4"]


def test_primary_rule_is_top_quarter_within_eligible_items():
    df = pd.DataFrame([
        {"question_id": f"Q{i}", "top_dimension": d, "t_top": t}
        for i, (d, t) in enumerate([("trust", 9), ("patience", 20), ("altruism", -7),
                                    ("risktaking", 3), ("trust", 2.5), ("posrecip", 1.0),
                                    ("none", 0.5), ("trust", 6)])])
    sel = df[P.dichotomize(df)].question_id.tolist()
    # top 25% of 8 = 2 items by |t| among imprint items with |t| >= 2
    assert sel == ["Q0", "Q2"]
