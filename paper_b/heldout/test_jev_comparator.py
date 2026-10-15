"""Jev comparator tests with a fake client (no network)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jev_comparator as J  # noqa: E402


def _fake(dim_probs, p_first_more=0.9, calls=None):
    def call(state, questions):
        if calls is not None:
            calls.append(next(iter(questions)))
        if "dimension" in questions:
            return {"model": "jev-1.13.0", "answers": {"dimension": {
                "type": "choice", "choice": max(dim_probs, key=dim_probs.get),
                "confidence": 1.0, "probabilities": dim_probs}}}
        return {"model": "jev-1.13.0", "answers": {"direction": {"type": "noul",
                                                                 "noul": p_first_more}}}
    return call


def test_assigns_with_sign_from_direction(tmp_path):
    c = J.Cache(tmp_path / "c.jsonl")
    r = J.classify("Q1", "Confidence: police", ["1", "2"], ["A great deal", "None"],
                   _fake({"trust": 0.8, "none": 0.2}, 0.95), c)
    assert r["dimension"] == "trust" and r["sign"] == -1
    r2 = J.classify("Q2", "Justifiable: violence", ["1", "10"], ["Never", "Always"],
                    _fake({"negrecip": 0.7, "none": 0.3}, 0.1), c)
    assert r2["sign"] == 1


def test_abstains_below_tau_or_on_none(tmp_path):
    c = J.Cache(tmp_path / "c.jsonl")
    calls = []
    r = J.classify("Q3", "x", ["1", "2"], ["a", "b"],
                   _fake({"trust": 0.45, "altruism": 0.3, "none": 0.25}, calls=calls), c)
    assert r["dimension"] == "none" and r["sign"] == 0 and math.isnan(r["p_first_more"])
    assert calls == ["dimension"]                       # no direction call when abstaining
    r = J.classify("Q4", "x", ["1", "2"], ["a", "b"], _fake({"none": 0.9, "trust": 0.1}), c)
    assert r["dimension"] == "none"


def test_cache_prevents_repeat_calls_and_survives_reopen(tmp_path):
    p = tmp_path / "c.jsonl"
    calls = []
    f = _fake({"trust": 0.9, "none": 0.1}, calls=calls)
    J.classify("Q5", "x", ["1", "2"], ["a", "b"], f, J.Cache(p))
    J.classify("Q5", "x", ["1", "2"], ["a", "b"], f, J.Cache(p))
    assert calls == ["dimension", "direction"]


def test_state_and_direction_text_carry_only_item_content():
    s = J.state_text("Do you trust people?", ["1", "2"], ["Yes", "No"])
    assert s == "Survey question: Do you trust people?\nResponse options: 1 = Yes; 2 = No"
    d = J.direction_instructions("posrecip", ["1", "4"], ["Agree", "Disagree"])
    assert "positive reciprocity" in d and "response 1 (Agree)" in d and "response 4 (Disagree)" in d


def test_frozen_battery_has_23_items_and_frozen_directions():
    b = J.frozen_battery()
    assert len(b) == 23 and set(b.frozen_dimension) == set(J.DIMS)
    s = dict(zip(b.question_id, b.frozen_sign))
    assert s["Q58"] == -1 and s["Q57"] == -1 and s["Q107"] == 1


def test_definitions_cover_every_option():
    assert set(J.DEFS) == set(J.DIMS) | {"none"}


def test_descending_code_order_is_normalised_before_the_direction_question(tmp_path):
    """Q99-style items list codes 2;1;0. 'first' must mean the LOWEST code."""
    calls = []

    def call(state, questions):
        calls.append((state, questions))
        if "dimension" in questions:
            return {"model": "m", "answers": {"dimension": {"type": "choice", "choice": "altruism",
                    "confidence": 1, "probabilities": {"altruism": 0.9, "none": 0.1}}}}
        return {"model": "m", "answers": {"direction": {"type": "noul", "noul": 0.1}}}

    r = J.classify("Q99", "Member?", ["2", "1", "0"], ["Active", "Inactive", "None"], call,
                   J.Cache(tmp_path / "c.jsonl"))
    state, q = calls[-1]
    assert "0 = None; 1 = Inactive; 2 = Active" in state
    assert "response 0 (None)" in q["direction"]["instructions"]
    assert r["sign"] == 1          # P(lowest code = more) = 0.1 -> higher codes = more


def test_cache_key_changes_with_the_prompt(tmp_path):
    p = tmp_path / "c.jsonl"
    calls = []
    f = _fake({"trust": 0.9, "none": 0.1}, calls=calls)
    J.classify("Q6", "wording A", ["1", "2"], ["a", "b"], f, J.Cache(p))
    J.classify("Q6", "wording B", ["1", "2"], ["a", "b"], f, J.Cache(p))
    assert calls.count("dimension") == 2


def test_ties_resolve_by_defs_order_and_bad_codes_fail_loudly(tmp_path):
    import pytest
    r = J.classify("Q7", "x", ["1", "2"], ["a", "b"],
                   _fake({"none": 0.4, "altruism": 0.6, "trust": 0.6}), J.Cache(tmp_path / "c.jsonl"))
    assert r["dimension"] == "trust"
    with pytest.raises(ValueError, match="non-numeric"):
        J.classify("Q8", "x", ["1", "DK"], ["a", "b"], _fake({"trust": 0.9}), J.Cache(tmp_path / "d.jsonl"))


def test_majority_aggregation():
    import pandas as pd, pytest
    def run(d, s):
        return pd.DataFrame({"question_id": ["Q1"], "dimension": [d], "sign": [s], "top_prob": [0.6]})
    agg = J.aggregate([run("trust", -1)] * 3 + [run("none", 0)] * 2)
    assert agg.iloc[0].dimension == "trust" and agg.iloc[0].votes == 3
    agg = J.aggregate([run("trust", -1)] * 2 + [run("trust", 1)] * 1 + [run("none", 0)] * 2)
    assert agg.iloc[0].dimension == "none"                 # sign split -> no majority
    with pytest.raises(ValueError):
        J.aggregate([run("trust", -1)] * 4)
