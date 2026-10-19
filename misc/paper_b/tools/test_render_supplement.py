"""Tests for the online-supplement renderer (placeholders -> audited number macros)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_numbers as AN  # noqa: E402
import render_supplement as RS  # noqa: E402

BS = chr(92)
TABLE = {
    "SCR_A_primary": {"value": "0.06057460871332797", "ci_low": "-0.0067258505657922735",
                      "ci_high": "0.12648524013553836", "n": "56"},
    "SCR_share_a_pos": {"value": "0.6071428571428571", "ci_low": "", "ci_high": "", "n": "56"},
    "HASH_overrides": {"value": "0f5cd2bbd88ef6ea" + "a" * 48, "ci_low": "", "ci_high": "", "n": "11194"},
    "PD_adapter_primary_trust_A": {"value": "0.06", "ci_low": "", "ci_high": "", "n": "2"},
    "PD_adapter_primary_risktaking_A": {"value": "0.1", "ci_low": "", "ci_high": "", "n": "1"},
    "PD_adapter_primary_posrecip_A": {"value": "-0.1", "ci_low": "", "ci_high": "", "n": "0"},
    "PD_adapter_primary_altruism_A": {"value": "0.1", "ci_low": "", "ci_high": "", "n": "0"},
}


def test_value_interval_n_pct_and_hash_render_as_macros_that_pass_the_audit():
    out = RS.render("«v|SCR_A_primary|3» «ci|SCR_A_primary|3» «n|SCR_A_primary» «pct|SCR_share_a_pos|1»"
                    " «h|HASH_overrides|16»", TABLE)
    assert out == (f"{BS}cl{{0.061}}{{SCR_A_primary}} {BS}ci{{-0.007}}{{0.126}}{{SCR_A_primary}} "
                   f"{BS}cl{{56}}{{SCR_A_primary:n}} {BS}cl{{60.7}}{{SCR_share_a_pos:pct}} "
                   f"{BS}clh{{0f5cd2bbd88ef6ea}}{{HASH_overrides}}")
    cls, _, residual = AN.extract(out)
    assert all(AN.check(p, r, TABLE)[0] == "PASS" for p, r in cls) and len(cls) == 6 and not residual


def test_section_sign_becomes_one_backslash():
    assert RS.render("§section{A}§§", TABLE) == f"{BS}section{{A}}{BS}{BS}"


def test_half_up_rounding_matches_the_audit():
    t = {"X": {"value": "0.0625", "ci_low": "", "ci_high": "", "n": "1"}}
    assert RS.render("«v|X|3»", t) == f"{BS}cl{{0.063}}{{X}}"


def test_unknown_claim_or_placeholder_or_leftover_fails():
    with pytest.raises(KeyError):
        RS.render("«v|NOPE|3»", TABLE)
    with pytest.raises(ValueError):
        RS.render("«zz|SCR_A_primary|3»", TABLE)
    with pytest.raises(ValueError):
        RS.render("«items»", TABLE)  # needs a selection


def test_item_rows_group_by_dimension_and_sign_and_check_counts():
    sel = pd.DataFrame({"question_id": ["Q10", "Q9", "Q200", "Q5"], "top_dimension": ["trust", "trust", "risktaking", "trust"],
                        "t_top": [2.5, -3.0, 4.0, 1.0], "primary_selected": [True, True, True, False]})
    out = RS.item_rows(sel, TABLE)
    assert out.splitlines()[0] == f"Trust & {BS}cl{{2}}{{PD_adapter_primary_trust_A:n}} & Q10 & Q9 {BS}{BS}"
    assert "Risk taking" in out and "Q5" not in out
    bad = dict(TABLE, PD_adapter_primary_trust_A=dict(TABLE["PD_adapter_primary_trust_A"], n="3"))
    with pytest.raises(AssertionError):
        RS.item_rows(sel, bad)
