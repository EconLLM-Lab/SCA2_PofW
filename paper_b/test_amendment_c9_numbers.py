"""Amendment C9 quotes only numbers the table holds, at the precision printed (skill: writing a claim-lock amendment).

Every decimal in the amendment must equal some table value (value, ci_low or ci_high) rounded to the same number of
places. A second check ties the named readings to their claim ids and verifies the sentence-level facts (which
intervals include 0, ranges, the append-only rule) from the table, not from the prose.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv"
LOCK = ROOT / "planning/TWO_PAPER_CLAIM_LOCK.md"


def _rows():
    with open(TABLE, newline="") as fh:
        return {r["claim_id"]: r for r in csv.DictReader(fh)}


def _amendment() -> str:
    text = LOCK.read_text().replace("\u2212", "-")
    start = text.index("### Amendment C9 ")
    end = text.index("## Never quote as current")
    return text[start:end]


def _fv(rows, cid, key="value"):
    return float(rows[cid][key])


def _fmt(rows, cid, dp=3):
    r = rows[cid]
    return f"{float(r['value']):.{dp}f} [{float(r['ci_low']):.{dp}f}, {float(r['ci_high']):.{dp}f}]"


def test_every_decimal_in_the_amendment_is_a_table_value_at_printed_precision():
    rows = _rows()
    allowed = set()
    for r in rows.values():
        for key in ("value", "ci_low", "ci_high"):
            if r[key] == "" or len(r[key]) == 64:
                continue
            try:
                v = float(r[key])
            except ValueError:
                continue
            for dp in (2, 3, 4):
                allowed.add(f"{v:.{dp}f}")
    text = _amendment().replace("arXiv:2610.06562", "arXiv")  # an identifier, not a statistic
    found = re.findall(r"(?<![\w.])-?\d+\.\d+", text)
    assert len(found) > 80
    bad = [x for x in found if x not in allowed]
    assert not bad, f"decimals in Amendment C9 that no table value rounds to: {sorted(set(bad))}"


def test_amendment_names_the_table_it_describes():
    text = _amendment()
    digest = hashlib.sha256(TABLE.read_bytes()).hexdigest()
    assert digest in text
    assert f"{len(_rows())} rows" in text
    assert "DESCRIPTIVE / NOT PREREGISTERED" in text
    assert "coauthor sign-off pending" in text.splitlines()[0]
    assert "2026-10-20" in text.splitlines()[0]


def test_named_readings_match_their_claim_ids():
    rows = _rows()
    quoted = {
        "C9_a_adapter_gps_trust_spearman_rho": 3, "C9_a_adapter_human_trust_spearman_rho": 3,
        "C9_a_human_gps_trust_spearman_rho": 3, "C9_a_human_gps_patience_q50_spearman_rho": 3,
        "C9_a_human_gps_negrecip_spearman_rho": 3, "C9_a_human_gps_patience_q43_spearman_rho": 3,
        "C9_b_adapter_gps_trust_spearman_rho": 3, "C9_b_adapter_human_trust_spearman_rho": 3,
        "C9_b_adapter_human_posrecip_spearman_rho": 3, "C9_TVD_persona_trust_gps_profile_block": 3,
        "C9_TVD_adapter_minus_base_profile_block": 3, "C9_TVD_adapter_minus_base_country": 3,
        "C9_TVD_persona_minus_base_profile_block": 3, "C9_TVD_persona_minus_base_country": 3,
    }
    text = _amendment()
    for cid, dp in quoted.items():
        pretty = _fmt(rows, cid, dp).replace("-", "-")
        assert pretty in text or pretty.split(" [")[0] in text, (cid, pretty)
    for cid in ("C9_TVD_base_mean_tvd_country_equal", "C9_TVD_adapter_mean_tvd_country_equal",
                "C9_TVD_persona_mean_tvd_country_equal"):
        assert f"{_fv(rows, cid):.3f}" in text, cid
    assert f"{_fv(rows, 'C9_W1_trust_spearman_full_vs_gps'):.3f}" in text
    assert f"{_fv(rows, 'C9_W1_patience_Q43_cross_var_share'):.3f}" in text


def test_interval_and_range_sentences_are_true_of_the_table():
    rows = _rows()
    sfc = ["trust", "patience_q43", "patience_q50", "risktaking", "posrecip", "negrecip", "altruism"]

    def excludes0(cid):
        r = rows[cid]
        return float(r["ci_low"]) > 0 or float(r["ci_high"]) < 0

    # "All seven adapter-human intervals include 0" (cohort 1)
    assert not any(excludes0(f"C9_a_adapter_human_{s}_spearman_rho") for s in sfc)
    # "Positive reciprocity is the only bank-2 adapter-human interval that excludes 0"
    assert [s for s in sfc if excludes0(f"C9_b_adapter_human_{s}_spearman_rho")] == ["posrecip"]
    # human-GPS: four exclude 0 (trust, Q43, Q50, negrecip), three include it
    assert sorted(s for s in sfc if excludes0(f"C9_a_human_gps_{s}_spearman_rho")) == \
        sorted(["trust", "patience_q43", "patience_q50", "negrecip"])
    # I1: ranges of the human between-share, chance mean and permutation p; adapter shares
    sh = [_fv(rows, f"C9_c_human_{s}_between_share_multi_member") for s in sfc]
    ch = [_fv(rows, f"C9_c_human_{s}_chance_mean_multi_member") for s in sfc]
    pv = [_fv(rows, f"C9_c_human_{s}_permutation_p_one_sided_multi_member") for s in sfc]
    ad = [_fv(rows, f"C9_c_adapter_{s}_between_share_multi_member") for s in sfc]
    assert (f"{min(sh):.3f}", f"{max(sh):.3f}") == ("0.318", "0.626")
    assert (f"{min(ch):.3f}", f"{max(ch):.3f}") == ("0.402", "0.408")
    assert (f"{min(pv):.3f}", f"{max(pv):.3f}") == ("0.059", "0.738")
    assert pv.index(min(pv)) == sfc.index("negrecip")
    assert (f"{min(ad):.3f}", f"{max(ad):.4f}") == ("0.957", "0.9999")
    # only negative reciprocity's share reaches the interpolated 80%-power value
    power = [k for k in rows if k.startswith("C9_c_design") and "interpolated" in k][0]
    assert [s for s, v in zip(sfc, sh) if v >= _fv(rows, power)] == ["negrecip"]
    # sign-mate agreement: range, and every interval spans 0
    sm = [_fv(rows, f"C9_d_human_vs_loo_sign_mates_{s}_spearman_rho") for s in sfc]
    assert (f"{min(sm):.3f}", f"{max(sm):.3f}") == ("-0.350", "0.332")
    assert not any(excludes0(f"C9_d_human_vs_loo_sign_mates_{s}_spearman_rho") for s in sfc)
    # I2: own-only range, covariance share, variance ratio, main-effect share
    wsf = ["trust", "risktaking", "patience_Q43", "patience_Q50", "altruism", "posrecip", "negrecip"]
    own = [_fv(rows, f"C9_W1_{s}_spearman_own_vs_gps") for s in wsf]
    assert (f"{min(own):.3f}", f"{max(own):.3f}") == ("0.817", "0.866")
    full = {s: _fv(rows, f"C9_W1_{s}_spearman_full_vs_gps") for s in wsf}
    assert max(full, key=lambda k: full[k]) == "trust"
    assert max(v for s, v in full.items() if s != "trust") < 0.5
    cov = {s: _fv(rows, f"C9_W1_{s}_cross_cov_share") for s in wsf}
    rest = [v for s, v in cov.items() if s != "trust"]
    assert f"{cov['trust']:.3f}" == "0.287" and (f"{min(rest):.3f}", f"{max(rest):.3f}") == ("0.727", "0.985")
    var = {s: _fv(rows, f"C9_W1_{s}_cross_var_share") for s in wsf}
    vrest = [v for s, v in var.items() if s != "trust"]
    assert f"{var['trust']:.3f}" == "0.147" and (f"{min(vrest):.3f}", f"{max(vrest):.3f}") == ("0.830", "1.049")
    assert [s for s, v in var.items() if v > 1] == ["patience_Q43"]
    me = [_fv(rows, f"C9_W1_{s}_main_effect_share_64") for s in wsf]
    assert (f"{min(me):.3f}", f"{max(me):.3f}") == ("0.483", "0.925")
    assert len([k for k in rows if k.endswith("_spearman_main_plus_2way_vs_gps")]) == 4
    assert int(_fv(rows, "C9_W1_bank1_label_rows_checked")) == 27636 == int(_fv(rows, "C9_W1_bank2_label_rows_checked"))
    assert _fv(rows, "C9_W1_bank1_label_mismatches") == 0 == _fv(rows, "C9_W1_bank2_label_mismatches")
    assert _fv(rows, "FX_adapter64_own_effects_wrong_signed") == 0
    # TVD: the persona and adapter contrasts have the signs the prose gives
    assert _fv(rows, "C9_TVD_adapter_minus_base_profile_block") > 0
    assert _fv(rows, "C9_TVD_persona_minus_base_profile_block") < 0


def test_amendment_forbids_the_overreaches():
    text = _amendment()
    for phrase in ("inconclusive", "WEAK", "behavioral decomposition", "not a percentage of variance explained",
                   "C9-4 did not run", "No claim is earned", "retrospective screen", "Pre-piloting stays untested"):
        assert phrase in text, phrase
    assert "transport" not in text.replace("Transport and pre-piloting stay unearned", "").lower()


def test_lock_file_only_grew_by_this_amendment():
    """Append-only: the text before the C9 heading is the committed text of the C8 lock, unchanged."""
    import subprocess
    old = subprocess.run(["git", "-C", str(ROOT), "show", "1cf9db7:planning/TWO_PAPER_CLAIM_LOCK.md"],
                         capture_output=True, text=True, check=True).stdout
    now = LOCK.read_text()
    head, tail = old.split("---\n\n## Never quote as current")
    assert now.startswith(head)
    assert now.endswith("---\n\n## Never quote as current" + tail)
