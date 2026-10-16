"""The 64-profile sign-prompt arm: one prompt per factorial cell, no country information."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factorial as F  # noqa: E402
import score_sign_profiles as SSP  # noqa: E402
import sign_prompt as SP  # noqa: E402


def test_all_profile_rows_cover_the_64_cells_in_factorial_order():
    rows = SSP.all_profile_rows()
    assert [r["profile_id"] for r in rows] == F.all_units()
    assert len({r["prompt"] for r in rows}) == 64


def test_bits_map_to_signs_with_one_meaning_positive():
    rows = {r["profile_id"]: r for r in SSP.all_profile_rows()}
    r = rows["P_1_0_1_1_0_1"]
    assert [r["signs"][d] for d in F.DIMS] == ["positive", "negative", "positive", "positive", "negative", "positive"]
    assert "trust: positive" in r["prompt"] and "risktaking: negative" in r["prompt"]


def test_no_prompt_names_a_country_or_a_number():
    for r in SSP.all_profile_rows():
        assert SP.leak_hits(r["prompt"]) == []
        assert not any(ch.isdigit() for ch in r["prompt"]), r["profile_id"]


def test_profile_ids_join_to_adapter_units():
    assert set(r["profile_id"] for r in SSP.all_profile_rows()) == set(F.all_units())


def test_only_filter_keeps_order_and_rejects_unknown():
    rows = SSP.select_profiles(SSP.all_profile_rows(), ["P_1_1_1_1_1_1", "P_0_0_0_0_0_0"])
    assert [r["profile_id"] for r in rows] == ["P_0_0_0_0_0_0", "P_1_1_1_1_1_1"]
    with pytest.raises(SystemExit, match="unknown"):
        SSP.select_profiles(SSP.all_profile_rows(), ["P_9_9_9_9_9_9"])


def test_expected_rows_per_profile_follow_the_spec():
    spec = {"questions": [{"codes": ["1", "2", "3"]}, {"codes": ["1", "2"]}]}
    assert SSP.rows_per_profile(spec) == 5
