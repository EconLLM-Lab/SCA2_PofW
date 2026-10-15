"""CPU tests for the 2^6 sign-profile factorial design. No GPU, no network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "paper_b"))

import factorial as F  # noqa: E402

GPS = ROOT / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"


def test_dims_order_and_unit_count():
    assert F.DIMS == ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
    units = F.all_units()
    assert len(units) == 64 and len(set(units)) == 64 and units == sorted(units)


def test_unit_roundtrip_and_z_vector():
    u = "P_1_0_1_0_0_1"
    assert F.bits_of_unit(u) == (1, 0, 1, 0, 0, 1)
    assert F.unit_of_bits((1, 0, 1, 0, 0, 1)) == u
    assert F.z_vector(u) == {"trust": 1.0, "risktaking": -1.0, "patience": 1.0,
                             "altruism": -1.0, "posrecip": -1.0, "negrecip": 1.0}


def test_unit_ids_match_sign_prompt_profile_ids():
    import sign_prompt as SP
    signs = {d: ("positive" if b else "negative") for d, b in zip(F.DIMS, (1, 0, 1, 0, 0, 1))}
    assert "P_" + SP.profile_id(signs) == "P_1_0_1_0_0_1"


def test_cohort_occupies_26_cells():
    import config as C
    members = F.unit_members(GPS, C.COHORT)
    assert len(members) == 26
    assert sum(len(v) for v in members.values()) == 42
    assert set(members) <= set(F.all_units())


def test_flip_changes_exactly_one_bit():
    u = "P_1_1_0_0_1_0"
    v = F.flip(u, "patience")
    assert sum(a != b for a, b in zip(F.bits_of_unit(u), F.bits_of_unit(v))) == 1


def test_build_profile_bank_labels_follow_sign_rule(tmp_path):
    bank = [{"triplet_id": "t1", "prompt": "P1", "facet": "f", "gps_dimension": "trust",
             "response_a": "A1", "response_b": "B1", "source_qc_status": None},
            {"triplet_id": "t2", "prompt": "P2", "facet": "f", "gps_dimension": "patience",
             "response_a": "A2", "response_b": "B2", "source_qc_status": None}]
    bpath = tmp_path / "triplets_bank.jsonl"
    bpath.write_text("\n".join(json.dumps(r) for r in bank) + "\n")
    m = F.build_profile_bank(bpath, tmp_path / "profiles", bank_run_id="bank2_test",
                             source_run_id="gen_test",
                             units=["P_1_1_1_1_1_1", "P_0_0_0_0_0_0"])
    assert m["units"] == ["P_0_0_0_0_0_0", "P_1_1_1_1_1_1"]
    assert m["n_triplets"] == 2 and m["run_id"] == "bank2_test"
    for u in m["units"]:
        rows = [json.loads(l) for l in (tmp_path / "profiles" / f"D_syn_{u}.jsonl").read_text().splitlines()]
        assert [r["triplet_id"] for r in rows] == ["t1", "t2"]
        for r in rows:
            z = r["gps_profile_vector"][r["gps_dimension"]]
            assert r["chosen_option"] == ("A" if z >= 0 else "B")
            assert r["country"] == u and r["source_run_id"] == "gen_test"


def test_profile_rows_equal_bank1_relabel_rows_for_a_real_country():
    """factorial.label_row must reproduce relabel.py's training fields exactly."""
    bank_dir = ROOT / "synthetic_generation/outputs/gps_sign_relabel_all"
    triplets = {json.loads(l)["triplet_id"]: json.loads(l)
                for l in (bank_dir / "triplets_bank.jsonl").read_text().splitlines() if l.strip()}
    raw = json.loads(GPS.read_text())
    unit = F.unit_of_z(raw["ARG"])
    real = [json.loads(l) for l in (bank_dir / "D_syn_ARG.jsonl").read_text().splitlines()]
    assert len(real) == 658
    for r in real:
        mine = F.label_row(triplets[r["triplet_id"]], unit, run_id="x", source_run_id="y",
                           export_timestamp="t")
        for k in ("prompt", "chosen", "rejected", "chosen_option", "gps_dimension", "triplet_id"):
            assert mine[k] == r[k], (k, r["triplet_id"])
