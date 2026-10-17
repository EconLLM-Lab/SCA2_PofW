"""CPU tests for the C6 near-zero refit bank. No GPU, no network, no human data beyond the committed GPS file."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "paper_b"))

import config as C  # noqa: E402
import factorial as F  # noqa: E402
import near_zero_bank as NZ  # noqa: E402

REAL_TRIPLETS = ROOT / "synthetic_generation/outputs/gps_sign_relabel_bank2/triplets_bank.jsonl"
REAL_PROFILES = ROOT / "synthetic_generation/outputs/gps_sign_relabel_bank2_profiles"
REAL_COUNTRIES = ROOT / "synthetic_generation/outputs/gps_sign_relabel_bank2"
needs_bank = pytest.mark.skipif(not (REAL_TRIPLETS.is_file() and REAL_PROFILES.is_dir()),
                                reason="bank-2 outputs are not on this machine")


def _triplets(per_dim: int = 5) -> list[dict]:
    out = []
    for d in F.DIMS:
        for i in range(per_dim):
            out.append({"triplet_id": f"{d[:3]}{i:02d}", "prompt": f"{d} question {i}", "facet": "f",
                        "gps_dimension": d, "response_a": f"A-{d}-{i}", "response_b": f"B-{d}-{i}",
                        "source_qc_status": None})
    return out


Z = {"trust": 0.50, "risktaking": -0.05, "patience": -0.30, "altruism": 0.08,
     "posrecip": 0.20, "negrecip": -0.09}          # near zero: risktaking, altruism, negrecip


def _unit_rows(triplets, unit):
    return [F.label_row(t, unit, run_id="r", source_run_id="s", export_timestamp="t") for t in triplets]


def test_country_labels_equal_profile_unit_labels_synthetic():
    ts = _triplets()
    unit = F.unit_of_z(Z)
    mine = NZ.country_rows(ts, Z, run_id="r", source_run_id="s", export_timestamp="t")
    ref = _unit_rows(ts, unit)
    assert [NZ.label_key(r) for r in mine] == [NZ.label_key(r) for r in ref]


def test_country_rows_flag_near_zero_but_unit_rows_never_do():
    ts = _triplets()
    mine = NZ.country_rows(ts, Z, run_id="r", source_run_id="s", export_timestamp="t")
    flagged = {r["gps_dimension"] for r in mine if r["near_zero_z"]}
    assert flagged == {"risktaking", "altruism", "negrecip"}
    assert not any(r["near_zero_z"] for r in _unit_rows(ts, F.unit_of_z(Z)))


def test_near_zero_dims_is_strict_below_threshold():
    z = {**Z, "trust": 0.10, "patience": -0.0999}
    assert NZ.near_zero_dims(z) == {"risktaking", "altruism", "negrecip", "patience"}   # 0.10 itself is kept


def test_label_equality_catches_a_flipped_label():
    ts = _triplets()
    ref = _unit_rows(ts, F.unit_of_z(Z))
    bad = [dict(r) for r in ref]
    bad[0]["chosen"], bad[0]["rejected"] = bad[0]["rejected"], bad[0]["chosen"]
    assert [NZ.label_key(r) for r in bad] != [NZ.label_key(r) for r in ref]


def test_reduced_bank_drops_only_near_zero_rows_and_keeps_split():
    ts = _triplets(per_dim=20)
    unit = F.unit_of_z(Z)
    rows = _unit_rows(ts, unit)
    train = NZ.train_prompts(rows)
    red = NZ.reduced_bank(rows, Z, train)
    kept, dropped = red["kept"], red["dropped"]
    assert len(kept) + len(dropped) == len(rows)
    assert {r["gps_dimension"] for r in dropped} <= {"risktaking", "altruism", "negrecip"}
    assert not ({r["gps_dimension"] for r in kept} & {"risktaking", "altruism", "negrecip"})
    by_id = {r["triplet_id"]: r for r in rows}
    for r in kept:                                     # kept rows are the unit's rows, untouched except `split`
        assert {k: v for k, v in r.items() if k != "split"} == by_id[r["triplet_id"]]
    n_train = int(len(rows) * C.TRAIN_FRAC)
    assert sum(r["split"] == "train" for r in kept) + red["train_dropped"] == n_train
    assert red["train_dropped"] == sum(1 for r in dropped if r["split"] == "train")


def test_split_matches_the_pipeline_split_on_the_full_bank():
    import lib
    ts = _triplets(per_dim=20)
    rows = _unit_rows(ts, F.unit_of_z(Z))
    prompts = {lib.normalize_prompt(r["prompt"]) for r in rows}
    want, _ = lib.make_shared_split(prompts, C.TRAIN_FRAC, C.SEED)
    assert NZ.train_prompts(rows) == want


def _ex(cc, unit, n_train_nz):
    return {"cc": cc, "unit": unit, "exposure": n_train_nz}


def test_declare_subset_rule_and_ties():
    cands = [
        {"cc": "AAA", "profile": "P1", "members": 1, "exposure": 10},
        {"cc": "BBB", "profile": "P2", "members": 1, "exposure": 30},
        {"cc": "CCC", "profile": "P3", "members": 1, "exposure": 30},     # tie with BBB -> BBB
        {"cc": "DDD", "profile": "P4", "members": 3, "exposure": 5},
        {"cc": "EEE", "profile": "P4", "members": 3, "exposure": 50},
        {"cc": "FFF", "profile": "P5", "members": 2, "exposure": 50},     # tie with EEE -> EEE
        {"cc": "GGG", "profile": "P5", "members": 2, "exposure": 0},      # no near-zero rows: not a candidate
    ]
    s = NZ.declare_subset(cands)
    assert s["singleton"] == "BBB" and s["multi"] == "EEE"
    s2 = NZ.declare_subset([c for c in cands if c["cc"] != "EEE"])
    assert s2["multi"] == "FFF"


def test_declare_subset_refuses_when_a_class_is_empty():
    with pytest.raises(ValueError):
        NZ.declare_subset([{"cc": "AAA", "profile": "P1", "members": 1, "exposure": 4}])


def test_write_bank_manifest_hashes_match_files(tmp_path):
    ts = _triplets(per_dim=20)
    rows = _unit_rows(ts, F.unit_of_z(Z))
    train = NZ.train_prompts(rows)
    red = NZ.reduced_bank(rows, Z, train)
    m = NZ.write_bank(tmp_path, "XXX", F.unit_of_z(Z), Z, red, bank_run_id="bank_t", source_rows=len(rows))
    p = tmp_path / "XXX" / "D_syn_XXX_nearzero.jsonl"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == m["sha256"]["D_syn_XXX_nearzero.jsonl"]
    assert m["n_kept"] == len(red["kept"]) and m["n_dropped"] == len(red["dropped"])
    assert json.loads((tmp_path / "XXX" / "manifest.json").read_text())["country"] == "XXX"
    text = json.dumps(m)
    assert not any(str(v) in text for v in Z.values())            # no country-level z values in the manifest


# ----------------------------------------------------------------- real bank-2 data
@needs_bank
def test_every_cohort_country_labels_equal_its_profile_unit_labels():
    triplets = NZ.load_triplets(REAL_TRIPLETS)
    gps = json.loads(NZ.GPS_JSON.read_text())
    for cc in C.COHORT:
        unit = F.unit_of_z(gps[cc])
        mine = NZ.country_rows(triplets, gps[cc], run_id="r", source_run_id="s", export_timestamp="t")
        ref = _unit_rows(triplets, unit)
        assert [NZ.label_key(r) for r in mine] == [NZ.label_key(r) for r in ref], cc


@needs_bank
def test_profile_files_on_disk_equal_label_row():
    triplets = NZ.load_triplets(REAL_TRIPLETS)
    for unit in ("P_0_0_0_0_0_0", "P_1_0_1_1_0_1", "P_1_1_1_1_1_1"):
        disk = [json.loads(l) for l in (REAL_PROFILES / f"D_syn_{unit}.jsonl").read_text().splitlines() if l.strip()]
        disk.sort(key=lambda r: r["triplet_id"])
        assert [NZ.label_key(r) for r in disk] == [NZ.label_key(r) for r in _unit_rows(triplets, unit)]


@needs_bank
def test_relabel_country_files_on_disk_equal_profile_labels():
    """Independent producer: relabel.py wrote D_syn_<CC>.jsonl with the country's real z."""
    triplets = NZ.load_triplets(REAL_TRIPLETS)
    gps = json.loads(NZ.GPS_JSON.read_text())
    for cc in C.COHORT:
        disk = [json.loads(l) for l in (REAL_COUNTRIES / f"D_syn_{cc}.jsonl").read_text().splitlines() if l.strip()]
        disk.sort(key=lambda r: r["triplet_id"])
        assert [NZ.label_key(r) for r in disk] == [NZ.label_key(r) for r in _unit_rows(triplets, F.unit_of_z(gps[cc]))], cc
