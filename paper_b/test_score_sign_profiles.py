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


# ---- verifier F2: a profile is done only with its CSV AND its manifest; manifests carry the stack
def test_done_profiles_require_csv_and_manifest():
    run = "r1"
    files = [f"runs/{run}/synthetic/P_0_0_0_0_0_0_option_probabilities.csv",
             f"runs/{run}/manifests/P_0_0_0_0_0_0_manifest.json",
             f"runs/{run}/synthetic/P_0_0_0_0_0_1_option_probabilities.csv",          # CSV only: a bare CSV is not done
             f"runs/other/synthetic/P_0_0_0_0_1_0_option_probabilities.csv",
             f"runs/other/manifests/P_0_0_0_0_1_0_manifest.json"]
    assert SSP.done_profiles(files, run) == {"P_0_0_0_0_0_0"}


def test_profile_manifest_records_stack_spec_and_hash():
    m = SSP.profile_manifest(run_id="r1", profile_id="P_0_0_0_0_0_0", csv_sha256="a" * 64, n_rows=1087,
                             spec_sha256="b" * 64, code_revision="c" * 40)
    assert m["stack_versions"]["python"] and "bitsandbytes" in m["stack_versions"]
    assert m["spec_sha256"] == "b" * 64 and m["n_rows"] == 1087 and m["contains_human_data"] is False
