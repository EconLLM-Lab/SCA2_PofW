"""analyze_replicate tests on synthetic scorer output (no GPU, no human data, no Hub).

The replicate is an UNSEEDED RETRAIN of one profile unit. These tests pin the three
quantities the card names: max |probability difference|, the Pearson correlation of
expected codes over the 23 strict items and over the 223 held-out items, and every
strict-surface difference in SD units of the 64 profile composites. A final test pins
verifier finding F8: no weight-space cosine is ever computed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_factorial as AF  # noqa: E402
import analyze_replicate as AR  # noqa: E402
import analyze_surface as AS  # noqa: E402
import factorial as F  # noqa: E402
from ceiling import surface_items  # noqa: E402

UNIT = "P_1_0_1_1_0_1"


def _frame(shift=0.0, seed=0, units=None, items=None):
    """64 sign profiles x the 23 strict items; each bit tilts its own dimension's items."""
    rng = np.random.default_rng(seed)
    item_dim = {q: d for d, qs in AS.STRICT_ITEMS.items() for q in qs}
    rows = []
    for u in (units or F.all_units()):
        bits = dict(zip(F.DIMS, F.bits_of_unit(u)))
        for q in (items or AS.all_strict_items()):
            dom = AS._domain(q)
            hi = np.array([AS.recode_value(float(c), q) for c in dom])
            w = np.exp((0.8 * bits[item_dim[q]] + shift) * (hi - hi.mean()) / (hi.std() + 1e-9)
                       + 0.05 * rng.normal(size=len(dom)))
            p = w / w.sum()
            for c, pi in zip(dom, p):
                rows.append({"model": f"{u}_adapter", "eval_country": u, "question_id": q,
                             "option_code": c, "model_prob": float(pi)})
    return pd.DataFrame(rows)


def _heldout_frame(shift=0.0, seed=0):
    """One unit x three held-out items with a shared 4-option grid."""
    rng = np.random.default_rng(seed)
    rows = []
    for q in ("Q1", "Q2", "Q3"):
        w = np.exp(shift * np.arange(4) + 0.05 * rng.normal(size=4))
        p = w / w.sum()
        for c, pi in zip("1234", p):
            rows.append({"model": f"{UNIT}_adapter", "question_id": q,
                         "option_code": c, "model_prob": float(pi)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ probability diff
def test_max_abs_prob_diff_is_the_largest_cell_difference():
    a = _heldout_frame(seed=1)
    b = a.copy()
    b.loc[0, "model_prob"] = b.loc[0, "model_prob"] + 0.25
    b.loc[1, "model_prob"] = b.loc[1, "model_prob"] - 0.25
    d = AR.max_abs_prob_diff(a, b)
    assert d["grids_match"] is True and d["n_cells_compared"] == 12
    assert d["max_abs_prob_diff"] == pytest.approx(0.25)


def test_max_abs_prob_diff_flags_a_grid_that_does_not_match():
    a = _heldout_frame(seed=1)
    b = a[a.question_id != "Q3"]
    d = AR.max_abs_prob_diff(a, b)
    assert d["grids_match"] is False and d["n_cells_only_replicate"] == 4 and d["n_cells_only_original"] == 0
    assert d["n_cells_compared"] == 8


def test_prob_table_refuses_a_duplicated_cell():
    a = pd.concat([_heldout_frame(seed=1), _heldout_frame(seed=1)], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        AR.prob_table(a)


# ------------------------------------------------------------------- expected codes
def test_expected_codes_is_the_probability_weighted_code():
    f = pd.DataFrame([{"question_id": "Q150", "option_code": "1", "model_prob": 0.2},
                      {"question_id": "Q150", "option_code": "2", "model_prob": 0.3},
                      {"question_id": "Q150", "option_code": "3", "model_prob": 0.5}])
    assert AR.expected_codes(f, ["Q150"])["Q150"] == pytest.approx(0.2 * 1 + 0.3 * 2 + 0.5 * 3)


def test_expected_codes_recoded_applies_the_frozen_recode():
    """Q81 is in INVERT_1_4, so E[recode] = 5 - E[code]."""
    f = pd.DataFrame([{"question_id": "Q81", "option_code": "1", "model_prob": 0.25},
                      {"question_id": "Q81", "option_code": "2", "model_prob": 0.25},
                      {"question_id": "Q81", "option_code": "3", "model_prob": 0.25},
                      {"question_id": "Q81", "option_code": "4", "model_prob": 0.25}])
    raw = AR.expected_codes(f, ["Q81"])["Q81"]
    rec = AR.expected_codes_recoded(f, ["Q81"])["Q81"]
    assert raw == pytest.approx(2.5) and rec == pytest.approx(2.5)


def test_expected_codes_refuses_a_probability_vector_that_does_not_sum_to_one():
    f = pd.DataFrame([{"question_id": "Q150", "option_code": "1", "model_prob": 0.2},
                      {"question_id": "Q150", "option_code": "2", "model_prob": 0.3}])
    with pytest.raises(ValueError, match="sum"):
        AR.expected_codes(f, ["Q150"])


# ------------------------------------------------------------------------- Pearson
def test_pearson_over_items_is_the_item_level_correlation():
    a = _heldout_frame(seed=1)
    b = _heldout_frame(seed=1)
    assert AR.pearson_over_items(AR.expected_codes(a, ["Q1", "Q2", "Q3"]),
                                 AR.expected_codes(b, ["Q1", "Q2", "Q3"]))["pearson"] == pytest.approx(1.0)
    assert AR.pearson_over_items(AR.expected_codes(a, ["Q1", "Q2", "Q3"]),
                                 AR.expected_codes(_heldout_frame(shift=1.0, seed=2),
                                                   ["Q1", "Q2", "Q3"]))["pearson"] < 1.0


# ------------------------------------------------------- strict surfaces in SD units
def test_surface_diff_is_in_sd_units_of_the_64_profile_composites():
    profiles = _frame(seed=3)
    orig = AR.unit_frame(profiles, UNIT)
    rep = AR.unit_frame(_frame(shift=0.4, seed=9), UNIT)
    out = AR.surface_sd_units(rep, orig, profiles).set_index("surface")

    # independent recomputation with the frozen surface definitions
    sd = (AF.unit_composites(profiles).pivot(index="unit", columns="surface", values="composite")
          .std(ddof=1))
    a = AS.model_item_table(rep.assign(eval_country=UNIT)).set_index("item").e_recode
    b = AS.model_item_table(orig.assign(eval_country=UNIT)).set_index("item").e_recode
    for surface, qs in surface_items(AS.STRICT_ITEMS).items():
        expect = (a[qs].mean() - b[qs].mean()) / sd[surface]
        assert out.loc[surface, "diff_sd"] == pytest.approx(expect, rel=1e-9)
    assert set(out.index) == set(surface_items(AS.STRICT_ITEMS))


def test_unit_frame_selects_by_eval_country_or_by_model_name():
    f = _frame(seed=3, units=[UNIT])
    assert AR.unit_frame(f, UNIT).shape[0] == f.shape[0]
    g = f.drop(columns=["eval_country"])
    assert AR.unit_frame(g, UNIT).shape[0] == f.shape[0]
    with pytest.raises(ValueError, match="no rows"):
        AR.unit_frame(f, "P_0_0_0_0_0_0")


# ------------------------------------------------------------------------- assembly
def test_analyse_returns_the_three_named_quantities(tmp_path):
    strict64 = _frame(seed=3)
    rep_strict = _frame(shift=0.4, seed=9, units=[UNIT])
    ho_orig = _heldout_frame(seed=5)
    ho_rep = _heldout_frame(shift=0.2, seed=6)
    items = AS.all_strict_items()
    out = AR.analyse(rep_strict=rep_strict, orig_strict64=strict64,
                     rep_heldout=ho_rep, orig_heldout=ho_orig, unit=UNIT,
                     heldout_items=["Q1", "Q2", "Q3"], strict_items=items,
                     results_dir=tmp_path)
    assert out["unit"] == UNIT and out["interpretation"] == "an unseeded retrain"
    for route in ("strict", "heldout"):
        assert set(out[route]) >= {"max_abs_prob_diff", "n_cells_compared", "grids_match",
                                  "pearson_expected_codes", "n_items"}
    assert len(out["strict_surface_diff_sd_units"]) == 7
    assert (tmp_path / "replicate_analysis.json").is_file()
    assert (tmp_path / "replicate_surface_diff.csv").is_file()


def test_module_never_computes_a_weight_space_cosine():
    """Verifier finding F8: the replicate is an unseeded retrain; no weight-space cosine.

    The docstring may name the thing it refuses to do, so this checks the calls, not the prose.
    """
    import ast
    tree = ast.parse((HERE / "analyze_replicate.py").read_text())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            called.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
    assert not [n for n in called if "cos" in n.lower()], sorted(called)
    assert "cos" not in {n.lower() for n in called}


def test_analyse_output_has_no_weight_space_cosine_key(tmp_path):
    out = AR.analyse(rep_strict=_frame(shift=0.4, seed=9, units=[UNIT]),
                     orig_strict64=_frame(seed=3), rep_heldout=_heldout_frame(seed=6),
                     orig_heldout=_heldout_frame(seed=5), unit=UNIT,
                     heldout_items=["Q1", "Q2", "Q3"], strict_items=AS.all_strict_items(),
                     results_dir=tmp_path)
    keys = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                keys.add(str(k).lower())
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(out)
    assert not [k for k in keys if "cos" in k]
    assert "weight-space cosine (verifier finding f8)" in {s.lower() for s in out["not_computed"]}
