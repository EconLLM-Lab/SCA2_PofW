from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_heldout as AH  # noqa: E402
import run_screen as RS  # noqa: E402


def test_amendment2_excludes_exactly_the_items_amendment1_repaired():
    """Amendment 2 must track Amendment 1's list, not a hand copy that can drift from it."""
    text = (HERE / "PREREGISTRATION.md").read_text()
    line = next(ln for ln in text.splitlines() if ln.startswith("What changed. 12 items"))
    registered = set(re.findall(r"Q\d+", line))
    assert len(registered) == 12
    assert set(AH.REPAIRED) == registered


def test_the_registered_human_surface_has_no_respondent_floor():
    """Section 4 sets only codes < 0 missing; a floor is a labelled sensitivity, never the default."""
    assert RS.MIN_N == 1
    assert RS.SENSITIVITY_MIN_N > RS.MIN_N


def test_routes_drop_abstentions():
    df = pd.DataFrame({"question_id": ["Q1", "Q2", "Q3"], "dimension": ["trust", "none", "altruism"],
                       "sign": [1, 0, 0]})
    out = AH.route(df, dim_col="dimension", sign_col="sign")
    assert list(out.question_id) == ["Q1"]


def test_coverage_matched_pairs_hold_the_same_items_in_the_same_order():
    a = pd.DataFrame({"question_id": ["Q10", "Q2", "Q5"], "top_dimension": ["trust"] * 3, "sign": [1.0] * 3})
    b = pd.DataFrame({"question_id": ["Q5", "Q99", "Q2"], "top_dimension": ["altruism"] * 3,
                      "sign": [-1.0] * 3})
    x, y = AH.common(a, b)
    assert list(x.question_id) == list(y.question_id) == ["Q2", "Q5"]
    assert set(x.top_dimension) == {"trust"} and set(y.top_dimension) == {"altruism"}, \
        "each route keeps its own (dimension, sign) on the shared items"


def test_adapter_route_signs_come_from_t_top():
    sel = pd.DataFrame({"question_id": ["Q1", "Q2", "Q3"], "top_dimension": ["trust", "altruism", "trust"],
                        "t_top": [3.0, -4.0, 9.0], "primary_selected": [True, True, False]})
    out = AH.adapter_route(sel)
    assert list(out.question_id) == ["Q1", "Q2"] and list(out.sign) == [1.0, -1.0]


def test_abs_a_cut_is_the_registered_value():
    """Section 8 registers 'dropping items whose |a_i| < 0.15'; the code must carry that cut, not a hand copy."""
    text = (HERE / "PREREGISTRATION.md").read_text()
    m = re.search(r"dropping items whose \|a_i\| < ([0-9.]+)", text)
    assert m is not None
    assert AH.ABS_A_CUT == float(m.group(1))


def test_abs_a_descriptive_keeps_items_at_or_above_the_cut():
    ia = pd.DataFrame({"question_id": ["Q1", "Q2", "Q3", "Q4", "Q5"],
                       "top_dimension": ["trust", "trust", "altruism", "altruism", "trust"],
                       "a_i": [0.30, -0.15, 0.149, -0.40, float("nan")]})
    out = AH.abs_a_descriptive(ia, cut=0.15)
    assert out["cut"] == 0.15
    assert out["n_items"] == 5 and out["n_scored"] == 4
    assert out["n_kept"] == 3 and out["n_dropped"] == 1, "|a_i| = 0.15 is kept; 0.149 is dropped; NaN is neither"
    assert abs(out["A_kept"] - (0.30 - 0.15 - 0.40) / 3) < 1e-12
    assert abs(out["share_pos_kept"] - 1 / 3) < 1e-12
    assert out["per_dimension_kept"]["trust"]["n"] == 2
    assert out["per_dimension_kept"]["altruism"]["n"] == 1
