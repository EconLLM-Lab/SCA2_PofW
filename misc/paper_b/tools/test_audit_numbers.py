"""Tests for the rounding-aware number audit of the Paper B manuscript (card T10)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_numbers as AN  # noqa: E402

TABLE = {
    "SCR_A_primary": {"value": "0.06057460871332797", "ci_low": "-0.0067258505657922735",
                      "ci_high": "0.12648524013553836", "n": "56"},
    "SCR_p_perm": {"value": "0.0097", "ci_low": "", "ci_high": "", "n": "10000"},
    "SCR_secondary_p_perm": {"value": "0.0", "ci_low": "", "ci_high": "", "n": "185"},
    "SCR_A_over_ceiling": {"value": "0.08121487008566211", "ci_low": "", "ci_high": "", "n": "34"},
    "FX_adapter64_trust_own_t": {"value": "16.74", "ci_low": "", "ci_high": "", "n": "64"},
}


def test_value_rounded_to_printed_precision_passes():
    assert AN.check("0.061", "SCR_A_primary", TABLE)[0] == "PASS"


def test_wrong_rounding_fails():
    assert AN.check("0.060", "SCR_A_primary", TABLE)[0] == "FAIL"


def test_interval_fields_and_unicode_minus():
    assert AN.check("-0.007", "SCR_A_primary:lo", TABLE)[0] == "PASS"
    assert AN.check("$-0.007$", "SCR_A_primary:lo", TABLE)[0] == "PASS"
    assert AN.check("0.126", "SCR_A_primary:hi", TABLE)[0] == "PASS"


def test_p_value_three_decimals():
    assert AN.check("0.010", "SCR_p_perm", TABLE)[0] == "PASS"


def test_below_threshold_form():
    assert AN.check("<0.001", "SCR_secondary_p_perm", TABLE)[0] == "PASS"
    assert AN.check("<0.001", "SCR_p_perm", TABLE)[0] == "FAIL"


def test_percent_field():
    assert AN.check("8.1", "SCR_A_over_ceiling:pct", TABLE)[0] == "PASS"
    assert AN.check("8.2", "SCR_A_over_ceiling:pct", TABLE)[0] == "FAIL"


def test_n_field_and_thousands_separator():
    assert AN.check("56", "SCR_A_primary:n", TABLE)[0] == "PASS"
    assert AN.check("10{,}000", "SCR_p_perm:n", TABLE)[0] == "PASS"


def test_unknown_claim_fails():
    assert AN.check("0.5", "NOT_A_CLAIM", TABLE)[0] == "FAIL"


def test_extract_macros_and_residual_numerals():
    tex = r"A is \cl{0.061}{SCR_A_primary} over \dc{223}{pool_items} items in Q82 and 4 stray. % 99 in a comment"
    cls, dcs, residual = AN.extract(tex)
    assert cls == [("0.061", "SCR_A_primary")]
    assert dcs == [("223", "pool_items")]
    assert [r[0] for r in residual] == ["4"]


def test_ci_macro_expands_to_two_checks():
    tex = r"interval \ci{-0.007}{0.126}{SCR_A_primary} here"
    cls, _, residual = AN.extract(tex)
    assert cls == [("-0.007", "SCR_A_primary:lo"), ("0.126", "SCR_A_primary:hi")]
    assert residual == []


def test_claim_id_containing_colon_resolves_with_and_without_field():
    table = {"B2_bank2_patience:Q43_rho": {"value": "0.005353886803974467", "ci_low": "-0.40296284758533274",
                                           "ci_high": "0.4703697004725019", "n": "42"}}
    assert AN.check("0.005", "B2_bank2_patience:Q43_rho", table)[0] == "PASS"
    assert AN.check("-0.403", "B2_bank2_patience:Q43_rho:lo", table)[0] == "PASS"
    assert AN.check("0.470", "B2_bank2_patience:Q43_rho:hi", table)[0] == "PASS"
    assert AN.split_ref("B2_bank2_patience:Q43_rho:lo", table) == ("B2_bank2_patience:Q43_rho", "lo")


def test_files_argument_audits_only_the_named_files(tmp_path):
    (tmp_path / "abstract.tex").write_text("unexplained 99")
    (tmp_path / "supp.tex").write_text("ok")
    table = tmp_path / "t.csv"
    table.write_text("claim_id,value,ci_low,ci_high,n\n")
    out = tmp_path / "audit.txt"
    rc = AN.main(["--table", str(table), "--root", str(tmp_path), "--out", str(out), "--files", "supp.tex"])
    assert rc == 0 and "supp.tex" in out.read_text() and "abstract.tex" not in out.read_text()


def test_supplement_design_constants_are_registered():
    assert AN.DESIGN["abs_a_cut"][0] == {"0.15"} and AN.DESIGN["face_valid_registered"][0] == {"30"}


def test_c8_design_constants_are_registered():
    assert AN.DESIGN["seed_country"][0] == {"20260905"}
    assert AN.DESIGN["dev_countries"][0] == {"16"}
