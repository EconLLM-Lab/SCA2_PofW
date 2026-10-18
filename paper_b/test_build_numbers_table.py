"""Tests for paper_b/build_numbers_table.py (card T9, checkpoint C7).

The table is built from committed JSON/CSV outputs only. These tests read the same outputs independently and
compare, so a transcription slip in the builder shows up as a failure. They contain no human rows: the human
side of the screen is already aggregated in the outputs.
"""
from __future__ import annotations

import ast
import csv
import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import build_numbers_table as BN  # noqa: E402

RES = ROOT / "planning/sprint_2026-10-11/paper-b-tier1/results"
COLUMNS = ["claim_id", "sentence_use", "statistic", "value", "ci_low", "ci_high", "n", "surface_label",
           "run_id", "producing_script", "output_file"]


@pytest.fixture(scope="module")
def rows():
    return BN.build_rows()


@pytest.fixture(scope="module")
def by_id(rows):
    return {r["claim_id"]: r for r in rows}


def _j(rel):
    return json.loads((RES / rel).read_text())


def test_columns_are_the_card_columns():
    assert BN.COLUMNS == COLUMNS


def test_every_row_has_every_column_and_a_surface_label(rows):
    assert len(rows) > 100
    for r in rows:
        assert list(r) == COLUMNS, r["claim_id"]
        for k in ("claim_id", "sentence_use", "statistic", "value", "surface_label", "run_id",
                  "producing_script", "output_file"):
            assert str(r[k]).strip(), (r["claim_id"], k)


def test_claim_ids_are_unique(rows):
    ids = [r["claim_id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_every_output_file_exists(rows):
    for r in rows:
        p = Path(r["output_file"])
        p = p if p.is_absolute() else ROOT / p
        assert p.is_file(), (r["claim_id"], r["output_file"])


def test_numeric_values_are_finite_and_intervals_are_ordered(rows):
    for r in rows:
        if r["statistic"].startswith("sha256"):
            assert len(r["value"]) == 64 and int(r["value"], 16) >= 0
            continue
        assert math.isfinite(float(r["value"])), r["claim_id"]
        if r["ci_low"] != "":
            assert float(r["ci_low"]) <= float(r["ci_high"]), r["claim_id"]


def test_builder_has_no_hand_typed_numbers():
    tree = ast.parse((HERE / "build_numbers_table.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            raise AssertionError(f"float literal {node.value} at line {node.lineno}")
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            assert abs(node.value) < 10, f"integer literal {node.value} at line {node.lineno}"


def test_screen_primary_row_matches_screen_result(by_id):
    s = json.loads((ROOT / "paper_b/heldout/screen_result.json").read_text())
    r = by_id["SCR_A_primary"]
    assert float(r["value"]) == s["A"]
    assert (float(r["ci_low"]), float(r["ci_high"])) == tuple(s["ci95"])
    assert int(r["n"]) == s["n_selected"]
    assert float(by_id["SCR_p_perm"]["value"]) == s["p_perm"]


def test_per_dimension_rows_match_per_dimension_json(by_id):
    d = _j("heldout_per_dimension.json")["routes"]["adapter_primary"]["per_dimension"]
    r = by_id["PD_adapter_primary_risktaking_A"]
    assert float(r["value"]) == d["risktaking"]["A"]
    assert [float(r["ci_low"]), float(r["ci_high"])] == d["risktaking"]["ci95"]
    assert int(r["n"]) == d["risktaking"]["n"]
    t = by_id["PD_adapter_primary_trust_A"]
    assert float(t["ci_low"]) < 0 < float(t["ci_high"])


def test_bonferroni_rows_are_exploratory_and_match_per_dimension_json(by_id):
    """Orchestrator 2026-10-18: SMR asks for multiplicity adjustment; the adjusted interval is a separate,
    unregistered row so the registered row stays as it was."""
    routes = _j("heldout_per_dimension.json")["routes"]
    for route in ("adapter_primary", "adapter_secondary"):
        for dim, cell in routes[route]["per_dimension"].items():
            r = by_id[f"PD_{route}_{dim}_A_bonf"]
            assert float(r["value"]) == cell["A"]
            assert [float(r["ci_low"]), float(r["ci_high"])] == cell["ci_bonf"]
            assert "not registered" in r["sentence_use"]


def test_bank2_rows_match_transport_json(by_id):
    b = _j("bank2_transport_strict.json")
    r = by_id["B2_bank2_trust_rho"]
    assert float(r["value"]) == b["bank2_adapter_gps"]["trust"]["point"]
    assert float(r["ci_low"]) == b["bank2_adapter_gps"]["trust"]["ci_lo"]
    assert float(r["ci_high"]) == b["bank2_adapter_gps"]["trust"]["ci_hi"]
    assert float(by_id["B2_cohort1_trust_rho"]["value"]) == b["cohort1_adapter_gps"]["trust"]["point"]
    assert float(by_id["B2_bank2_risktaking_rho"]["ci_low"]) < 0


def test_factorial_rows_match_factorial_report(by_id):
    f = _j("factorial/factorial_report.json")["route_contrast_64_cells"]
    assert float(by_id["FX_signprompt64_trust_own_beta"]["value"]) == f["signprompt"]["diagonal"]["trust"]["beta"]
    assert float(by_id["FX_adapter64_trust_own_beta"]["value"]) == f["adapter"]["diagonal"]["trust"]["beta"]
    assert float(by_id["FX_adapter64_pc1_share"]["value"]) == f["adapter"]["general_factor"]["pc1_share"]
    assert float(by_id["FX_signprompt64_pc1_share"]["value"]) == f["signprompt"]["general_factor"]["pc1_share"]
    assert int(float(by_id["FX_adapter64_V5_hits"]["value"])) == f["adapter"]["plan_V5_rowwise_raw"]["hits"]


def test_wrong_signed_and_trust_largest_counts_are_derived(by_id):
    assert int(float(by_id["FX_adapter64_own_effects_wrong_signed"]["value"])) == 0
    assert int(float(by_id["FX_signprompt64_own_effects_wrong_signed"]["value"])) == 3
    assert int(float(by_id["FX_signprompt64_surfaces_largest_mover_is_trust_bit"]["value"])) == 7
    assert int(float(by_id["FX_adapter64_surfaces_largest_mover_is_trust_bit"]["value"])) == 3


def test_cross_talk_rows_read_the_main_effect_matrix(by_id):
    with open(RES / "factorial/mtmm_adapter.csv") as fh:
        rows = {r["dimension"]: r for r in csv.DictReader(fh)}
    assert float(by_id["FX_adapter64_risktaking_bit_on_altruism"]["value"]) == float(rows["risktaking"]["altruism"])
    assert float(by_id["FX_adapter64_risktaking_bit_on_negrecip"]["value"]) == float(rows["risktaking"]["negrecip"])


def test_replicate_and_near_zero_rows(by_id):
    r = _j("replicate/replicate_analysis.json")
    assert float(by_id["RP_strict_max_abs_prob_diff"]["value"]) == r["strict"]["max_abs_prob_diff"]
    assert float(by_id["RP_max_abs_surface_diff_sd"]["value"]) == r["max_abs_surface_diff_sd"]
    z = _j("near_zero/near_zero_analysis.json")
    row = [t for t in z["table"] if t["country"] == "COL" and t["surface"] == "posrecip"][0]
    assert float(by_id["NZ_COL_posrecip_refit_minus_control_sd"]["value"]) == row["refit_minus_control_sd"]
    assert float(by_id["NZ_COL_posrecip_noise_floor_sd"]["value"]) == row["noise_floor_sd"]


def test_readout_robustness_matches_the_freeze_record(by_id):
    freeze = json.loads((ROOT / "paper_b/heldout/FREEZE.json").read_text())["readout_robustness"]
    for variant in ("heldout_reverse", "heldout_para_a", "heldout_para_b"):
        num, den = freeze[variant].split(" = ")[0].split("/")
        r = by_id[f"RO_{variant}_ds_unchanged"]
        assert int(float(r["value"])) == int(num) and int(r["n"]) == int(den)


def test_pool_hash_rows_record_both_line_ending_forms(by_id):
    crlf, lf = by_id["HASH_pool_worktree"], by_id["HASH_pool_git_blob_lf"]
    assert crlf["value"] != lf["value"]
    assert crlf["value"] == "19241f6f103c51d64e295045162bb370920223b7ffad7c5f3c8991f5c101bd44"


def test_cli_is_deterministic(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    BN.main(["--out", str(a)])
    BN.main(["--out", str(b)])
    assert a.read_bytes() == b.read_bytes()
    with open(a, newline="") as fh:
        assert next(csv.reader(fh)) == COLUMNS


def test_near_zero_subsample_variation_rows_are_the_max_of_control_minus_baseline(by_id):
    z = _j("near_zero/near_zero_analysis.json")["table"]
    for cc in ("GBR", "COL"):
        mx = max(abs(r["control_minus_baseline_sd"]) for r in z if r["country"] == cc)
        row = by_id[f"NZ_{cc}_max_abs_control_minus_baseline_sd"]
        assert float(row["value"]) == mx
        assert float(row["value"]) > 1  # larger than every declared noise floor, the point of the footnote
