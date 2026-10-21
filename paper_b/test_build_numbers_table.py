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


def test_registered_abs_a_descriptive_rows_match_the_analysis(by_id):
    """Preregistration section 8: item-level descriptive after dropping |a_i| < 0.15 (never the primary)."""
    d = _j("heldout_analysis.json")["s8_abs_a_descriptive"]
    assert d["cut"] == 0.15
    assert int(float(by_id["SCR_absA_n_kept"]["value"])) == d["n_kept"]
    assert int(by_id["SCR_absA_n_kept"]["n"]) == d["n_scored"]
    assert float(by_id["SCR_absA_A_kept"]["value"]) == d["A_kept"]
    assert int(by_id["SCR_absA_A_kept"]["n"]) == d["n_kept"]
    assert float(by_id["SCR_absA_share_pos_kept"]["value"]) == d["share_pos_kept"]
    for k in ("SCR_absA_n_kept", "SCR_absA_A_kept", "SCR_absA_share_pos_kept"):
        assert "descriptive" in by_id[k]["sentence_use"].lower()


def test_registered_face_valid_all_items_rows_match_the_analysis(by_id):
    """Preregistration section 6: A_face on all its items (negrecip included), Amendment 2 applied."""
    d = _j("heldout_analysis.json")["s6_comparators"]["face_valid"]["describe_all"]
    assert float(by_id["CMP_face_valid_A_all"]["value"]) == d["A"]
    assert int(by_id["CMP_face_valid_A_all"]["n"]) == d["n_items"]
    neg = d["per_dimension"]["negrecip"]
    assert float(by_id["CMP_face_valid_all_negrecip_A"]["value"]) == neg["A"]
    assert int(by_id["CMP_face_valid_all_negrecip_A"]["n"]) == neg["n"]
    assert "Amendment 2" in by_id["CMP_face_valid_A_all"]["surface_label"]


def test_every_input_and_producer_lives_in_the_repository(rows):
    """A number whose input sits in a pruned scratch folder is not replicable."""
    assert BN.READOUT_DIR.is_relative_to(BN.ROOT)
    for r in rows:
        assert not Path(r["output_file"]).is_absolute(), (r["claim_id"], r["output_file"])
        assert "scratch" not in r["producing_script"] + r["output_file"], r["claim_id"]


# ------------------------------------------------------------------ C8 persona arm (C8_PERSONA_DESIGN.md)
def _close(row, value, lo=None, hi=None):
    assert float(row["value"]) == value
    if lo is not None:
        assert float(row["ci_low"]) == lo and float(row["ci_high"]) == hi


def test_persona_rows_match_the_persona_json(by_id):
    d = _j("persona/persona_strict.json")
    assert d["replay_checks"]["all_pass"] is True
    for s in BN.SURFACES:
        e = d["E1"][s]
        _close(by_id[f"PX_persona_{s}_rho"], e["point"], e["ci_lo"], e["ci_hi"])
        assert int(by_id[f"PX_persona_{s}_rho"]["n"]) == 42
        e = d["E4"]["persona"][s]
        _close(by_id[f"PX_persona_{s}_rho_country"], e["point"], e["ci_lo"], e["ci_hi"])
        e = d["routes_vs_gps"]["SP"][s]
        _close(by_id[f"PX_signprompt_{s}_rho"], e["point"], e["ci_lo"], e["ci_hi"])
    e2 = d["E2"]
    r = by_id["PX_D_cohort1_trust"]
    _close(r, e2["point"], e2["ci_lo"], e2["ci_hi"])
    assert e2["reading"] in r["sentence_use"] and "primary" in r["sentence_use"]
    e4 = d["E4"]["E2_country_bootstrap"]
    _close(by_id["PX_D_cohort1_trust_country"], e4["point"], e4["ci_lo"], e4["ci_hi"])
    for route, name in (("C1", "cohort1"), ("B2", "bank2"), ("SP", "signprompt")):
        for s, e in d["E3"][route].items():
            row = by_id[f"PX_D_{name}_{s}"]
            _close(row, e["point"], e["ci_lo"], e["ci_hi"])
            assert "descriptive" in row["surface_label"]
    assert "PX_D_cohort1_trust" not in {f"PX_D_cohort1_{s}" for s in d["E3"]["C1"]}
    for key, rid in (("C1_trust", "PX_dev16_cohort1_trust_rho"), ("P_trust", "PX_dev16_persona_trust_rho")):
        e = d["E5"][key]
        _close(by_id[rid], e["point"], e["ci_lo"], e["ci_hi"])
        assert int(by_id[rid]["n"]) == 16
    g3 = by_id["PX_G3_base_max_dlogprob"]
    assert float(g3["value"]) == d["base_parity"]["max_dlogprob"] and int(g3["n"]) == d["base_parity"]["n_rows"]
    assert d["base_parity"]["pass"] is True


def test_rows_of_the_c71_table_are_unchanged_by_later_additions(rows):
    """Amendment C7.1 (commit 92406dd) fixed 225 rows; a later amendment may add rows, never move these."""
    import subprocess
    old = subprocess.run(["git", "-C", str(ROOT), "show",
                          "92406dd:planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"],
                         capture_output=True, text=True, check=True).stdout
    before = {r["claim_id"]: r for r in csv.DictReader(old.splitlines())}
    now = {r["claim_id"]: r for r in rows}
    assert len(before) == 225
    for cid, r in before.items():
        assert now[cid] == r, cid


# ------------------------------------------------------------------ C9 descriptive rows (Amendment C9)
C9 = RES / "c9"
LABEL = "DESCRIPTIVE / NOT PREREGISTERED"


def _num(x):
    return "" if x is None else repr(float(x))


def test_rows_of_the_c8_table_are_unchanged_by_c9_additions(rows):
    """Amendment C8 (commit 1cf9db7) fixed 271 rows (sha 51ddcce1...97855); Amendment C9 adds rows, never moves these."""
    import hashlib
    import subprocess
    rel = "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
    old = subprocess.run(["git", "-C", str(ROOT), "show", f"1cf9db7:{rel}"], capture_output=True, check=True).stdout
    assert hashlib.sha256(old).hexdigest() == "51ddcce1dd205ee29ecf6e3450fd30bf09948399e98adb32abfc0846e1b97855"
    before = {r["claim_id"]: r for r in csv.DictReader(old.decode().splitlines())}
    now = {r["claim_id"]: r for r in rows}
    assert len(before) == 271
    for cid, r in before.items():
        assert now[cid] == r, cid
    # a rebuilt row order must not move them either: the first 271 rows are the old rows, in order
    assert [r["claim_id"] for r in rows[:271]] == list(before)


def test_c9_rows_exist_and_are_all_labelled_descriptive(rows):
    c9 = [r for r in rows if r["claim_id"].startswith("C9_")]
    assert len(c9) == len(rows) - 271
    assert len(c9) > 200
    for r in c9:
        assert LABEL in r["surface_label"], r["claim_id"]
        assert "C9-" in r["sentence_use"] or "W1" in r["sentence_use"], r["claim_id"]


def test_c9_1_rows_match_the_human_agreement_json(by_id):
    d = json.loads((C9 / "c9_human_agreement.json").read_text())
    assert len(d["rows"]) == 167
    for src in d["rows"]:
        r = by_id[src["claim_id"]]
        assert float(r["value"]) == src["value"], src["claim_id"]
        assert r["ci_low"] == _num(src["ci_low"]) and r["ci_high"] == _num(src["ci_high"]), src["claim_id"]
        assert int(r["n"]) == src["n"], src["claim_id"]
        assert src["interval_type"] in r["surface_label"], src["claim_id"]
        assert r["output_file"].endswith("results/c9/c9_human_agreement.json")


def test_c9_1_interval_types_follow_the_sprint_rule(by_id):
    """Human-GPS uses the country bootstrap; every adapter-side interval is profile-block."""
    d = json.loads((C9 / "c9_human_agreement.json").read_text())
    for src in d["rows"]:
        if src["ci_low"] is None:
            continue
        if src["interval_type"].startswith("permutation null"):
            assert "not a confidence interval" in by_id[src["claim_id"]]["sentence_use"], src["claim_id"]
            continue
        want = "country bootstrap" if src["column"] == "human-GPS" else "profile-block bootstrap"
        assert src["interval_type"].startswith(want), src["claim_id"]


def test_c9_2_rows_match_the_tvd_json_and_the_label_recovery_cell_has_none(rows, by_id):
    d = json.loads((C9 / "c9_tvd.json").read_text())
    # the adapter+persona cell is filled once its run (C9-4) exists on the Hub; before that it is "pending"
    assert d["cells"]["adapter_persona"]["status"] == "ok"
    assert d["cells"]["adapter_persona"]["n_countries"] == 42
    assert [r for r in rows if "C9_TVD_adapter_persona" in r["claim_id"]]      # rows exist for the filled cell
    for cell in ("base", "adapter", "persona", "adapter_persona"):
        c = d["cells"][cell]
        r = by_id[f"C9_TVD_{cell}_mean_tvd_country_equal"]
        assert float(r["value"]) == c["mean_tvd_country_equal"] and int(r["n"]) == c["n_countries"]
        r = by_id[f"C9_TVD_{cell}_mean_tvd_pooled"]
        assert float(r["value"]) == c["mean_tvd_pooled"] and int(r["n"]) == c["n_cells"]
        for dim, v in c["per_dimension"].items():
            assert float(by_id[f"C9_TVD_{cell}_{dim}_mean_tvd_country_equal"]["value"]) == v
    for cell in ("adapter", "persona"):
        for unit in ("profile_block", "country"):
            g = d["cells"][cell]["trust_gps"][unit]
            r = by_id[f"C9_TVD_{cell}_trust_gps_{unit}"]
            assert (float(r["value"]), float(r["ci_low"]), float(r["ci_high"])) == (g["point"], g["ci_lo"], g["ci_hi"])
    assert "C9_TVD_base_trust_gps_profile_block" not in by_id  # undefined: the base trust composite is constant
    for name, c in d["contrasts"].items():
        for unit in ("profile_block", "country"):
            g = c[unit]
            r = by_id[f"C9_TVD_{name}_{unit}"]
            assert (float(r["value"]), float(r["ci_low"]), float(r["ci_high"])) == (g["point"], g["ci_lo"], g["ci_hi"])
            assert int(r["n"]) == g["n"]


def test_c9_w1_rows_match_the_decomposition_json(by_id):
    w = json.loads((C9 / "w1_why_trust.json").read_text())
    for blk in w["adapter"]["cohort1_observed"]:
        s = blk["surface"].replace(":", "_")
        for key in ("spearman_full_vs_gps", "spearman_own_vs_gps", "spearman_cross_vs_gps", "cross_var_share",
                    "cross_cov_share"):
            r = by_id[f"C9_W1_{s}_{key}"]
            assert float(r["value"]) == blk[key] and int(r["n"]) == blk["n"]
        assert float(by_id[f"C9_W1_cohort1_{s}_spearman_full_vs_observed"]["value"]) == blk["spearman_full_vs_observed"]
    for blk in w["adapter"]["bank2_observed"]:
        s = blk["surface"].replace(":", "_")
        assert float(by_id[f"C9_W1_{s}_main_effect_share_64"]["value"]) == blk["main_effect_share_64"]
        assert float(by_id[f"C9_W1_bank2_{s}_spearman_full_vs_observed"]["value"]) == blk["spearman_full_vs_observed"]
        if "spearman_main_plus_2way_vs_gps" in blk:
            assert float(by_id[f"C9_W1_{s}_spearman_main_plus_2way_vs_gps"]["value"]) == blk["spearman_main_plus_2way_vs_gps"]
    assert float(by_id["C9_W1_rank_cross_var_share_vs_failure_bank2"]["value"]) == \
        w["adapter"]["rank_bank2_observed"]["spearman_share_vs_failure"]
    assert float(by_id["C9_W1_rank_cross_var_share_vs_failure_cohort1"]["value"]) == \
        w["adapter"]["rank_cohort1_observed"]["spearman_share_vs_failure"]
    for bank in ("bank1", "bank2"):
        lc = w["bank_composition"][bank]["label_check"]
        assert float(by_id[f"C9_W1_{bank}_label_rows_checked"]["value"]) == lc["rows_checked"]
        assert float(by_id[f"C9_W1_{bank}_label_mismatches"]["value"]) == lc["label_mismatches_vs_own_dimension_sign"]


def test_c9_w1_uses_the_covariance_share_beside_the_variance_ratio(by_id):
    """cross_var_share is a ratio that can exceed 1 (covariance); the row text must say so."""
    r = by_id["C9_W1_patience_Q43_cross_var_share"]
    assert float(r["value"]) > 1
    assert "not a share" in r["sentence_use"] or "ratio" in r["sentence_use"]
    assert "behavioral" in r["sentence_use"].lower()


def test_c9_4b_label_recovery_rows_match_the_json(rows, by_id):
    """C9-4 B: eight rows (four quantities x two bootstraps), equal to the analysis JSON; construction checks only."""
    d = json.loads((C9 / "c9_label_recovery.json").read_text())
    assert d["n_countries"] == 42 and d["n_pairs_per_country"] == 132
    lr = [r for r in rows if r["claim_id"].startswith("C9_label_recovery_")]
    assert len(lr) == 8
    for q in BN.C9_LR_QUANTITIES:
        for unit in ("profile_block", "country"):
            g = d["cohort"][q][unit]
            r = by_id[f"C9_label_recovery_{q}_{unit}"]
            assert (float(r["value"]), float(r["ci_low"]), float(r["ci_high"])) == (g["point"], g["ci_lo"], g["ci_hi"])
            assert int(r["n"]) == 42
            assert "construction check" in r["surface_label"] and LABEL in r["surface_label"]
    # the reading the amendment gives: training installed the labels, the base model sits at chance
    assert float(by_id["C9_label_recovery_base_accuracy_profile_block"]["ci_low"]) < 0.5 < float(
        by_id["C9_label_recovery_base_accuracy_profile_block"]["ci_high"])
    assert float(by_id["C9_label_recovery_accuracy_profile_block"]["ci_low"]) > 0.5


def test_rows_of_the_c9_table_are_unchanged_by_the_c9_4b_addition(rows):
    """Commit 0d4d701 fixed 554 rows (sha 02c5d0cf...dd9dd1); the C9-4 B rows are appended, never move these."""
    import hashlib
    import subprocess
    rel = "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
    old = subprocess.run(["git", "-C", str(ROOT), "show", f"0d4d701:{rel}"], capture_output=True, check=True).stdout
    assert hashlib.sha256(old).hexdigest() == "02c5d0cf9281f2927b8222386160412f1276437bf9dca8f70eafdc042dda9dd1"
    before = {r["claim_id"]: r for r in csv.DictReader(old.decode().splitlines())}
    assert len(before) == 554
    now = {r["claim_id"]: r for r in rows}
    for cid, r in before.items():
        assert now[cid] == r, cid
    assert [r["claim_id"] for r in rows[:554]] == list(before)
