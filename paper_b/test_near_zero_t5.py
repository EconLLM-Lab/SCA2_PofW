"""Card T5 (C6): the four near-zero adapters (refit GBR, COL; size-matched control GBR, COL).

CPU only: banks, protocol switch, preparation, scoring plan. No GPU, no network.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import factorial as F  # noqa: E402
import lib  # noqa: E402
import near_zero_bank as NZ  # noqa: E402
import protocol_bank2 as P2  # noqa: E402
import score_plan as SPL  # noqa: E402

REAL_PROFILES = ROOT / "synthetic_generation/outputs/gps_sign_relabel_bank2_profiles"
REAL_NZ = Path("/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero")
needs_real = pytest.mark.skipif(not (REAL_PROFILES.is_dir() and REAL_NZ.is_dir()),
                                reason="bank-2 outputs or near_zero banks are not on this machine")
UNITS = ["GBR", "COL", "GBR_control", "COL_control"]


# ------------------------------------------------------------------ synthetic fixtures
def _rows(per_dim: int = 20, unit: str = "P_1_1_1_1_0_1") -> list[dict]:
    ts = []
    for d in F.DIMS:
        for i in range(per_dim):
            ts.append({"triplet_id": f"{d[:3]}{i:03d}", "prompt": f"{d} situation number {i}", "facet": "f",
                       "gps_dimension": d, "response_a": f"A-{d}-{i}", "response_b": f"B-{d}-{i}",
                       "source_qc_status": None})
    return [F.label_row(t, unit, run_id="r", source_run_id="s", export_timestamp="t") for t in ts]


# ------------------------------------------------------------------ control bank
def test_control_bank_is_a_uniform_subsample_of_training_rows_only():
    rows = _rows()
    train = NZ.train_prompts(rows)
    c = NZ.control_bank(rows, train, k=30)
    assert len(c["kept"]) == 30
    assert all(r["split"] == "train" for r in c["kept"])
    assert len({r["triplet_id"] for r in c["kept"]}) == 30                # without replacement
    train_ids = {r["triplet_id"] for r in rows if lib.normalize_prompt(r["prompt"]) in train}
    assert {r["triplet_id"] for r in c["kept"]} <= train_ids
    by_id = {r["triplet_id"]: r for r in rows}
    for r in c["kept"]:                                                    # rows are the unit's rows plus `split`
        assert {k: v for k, v in r.items() if k != "split"} == by_id[r["triplet_id"]]


def test_control_bank_is_deterministic_and_seed_dependent():
    rows = _rows()
    train = NZ.train_prompts(rows)
    a = [r["triplet_id"] for r in NZ.control_bank(rows, train, k=30)["kept"]]
    b = [r["triplet_id"] for r in NZ.control_bank(rows, train, k=30)["kept"]]
    c = [r["triplet_id"] for r in NZ.control_bank(rows, train, k=30, seed=1)["kept"]]
    assert a == b and a != c
    assert NZ.CONTROL_SEED == 20261018


def test_control_bank_uses_default_rng_choice_on_triplet_sorted_training_rows():
    import numpy as np
    rows = _rows()
    train = NZ.train_prompts(rows)
    tr = sorted((r for r in rows if lib.normalize_prompt(r["prompt"]) in train), key=lambda r: r["triplet_id"])
    idx = np.random.default_rng(20261018).choice(len(tr), size=25, replace=False)
    want = sorted(tr[i]["triplet_id"] for i in idx)
    got = sorted(r["triplet_id"] for r in NZ.control_bank(rows, train, k=25)["kept"])
    assert got == want


def test_control_bank_refuses_more_rows_than_the_unit_trains_on():
    rows = _rows(per_dim=5)
    with pytest.raises(ValueError):
        NZ.control_bank(rows, NZ.train_prompts(rows), k=10_000)


def test_write_control_manifest_hashes_and_matches_refit_fields(tmp_path):
    rows = _rows()
    train = NZ.train_prompts(rows)
    c = NZ.control_bank(rows, train, k=30)
    m = NZ.write_control_bank(tmp_path, "XXX_control", "P_1_1_1_1_0_1", c, bank_run_id="bank_t", source_rows=len(rows),
                              matched_to="XXX")
    p = tmp_path / "XXX_control" / m["file"]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == m["sha256"][m["file"]]
    assert m["train_kept"] == 30 and m["arm"] == "control" and m["seed"] == 20261018
    assert m["n_source"] == len(rows) and m["matched_to"] == "XXX"
    assert json.loads((tmp_path / "XXX_control" / "manifest.json").read_text())["bank_run_id"] == "bank_t"


@needs_real
def test_real_control_banks_have_the_refit_sizes_and_refits_are_unchanged():
    for unit, n in (("GBR", 164), ("COL", 260)):
        m = json.loads((REAL_NZ / f"{unit}_control" / "manifest.json").read_text())
        assert m["train_kept"] == n and m["arm"] == "control"
        refit = json.loads((REAL_NZ / unit / "manifest.json").read_text())
        assert refit["train_kept"] == n and m["profile_unit"] == refit["profile_unit"]
    shas = {u: json.loads((REAL_NZ / u / "manifest.json").read_text())["sha256"] for u in ("GBR", "COL")}
    assert shas["GBR"] == {"D_syn_GBR_nearzero.jsonl": "3fa619125d2ff2660050a1ba6d9a3331a50b71f2914d97fb6cede473d77590c8"}
    assert shas["COL"] == {"D_syn_COL_nearzero.jsonl": "87a9cf9db1ae478b6435fc9126e9836e6bededcbbb7cbabcb7358d3be7652fa5"}


# ------------------------------------------------------------------ a synthetic near-zero directory
def _make_nz_dir(tmp_path, run_id="bank_t", per_dim=20, k=30):
    """profile dir + near-zero dir with four unit banks built from the same synthetic profile file."""
    unit = "P_1_1_1_1_0_1"
    rows = _rows(per_dim, unit)
    prof = tmp_path / "profiles"
    prof.mkdir()
    lib.write_jsonl(rows, prof / f"D_syn_{unit}.jsonl")
    train = NZ.train_prompts(rows)
    nzd = tmp_path / "nz"
    z = {"trust": 0.5, "risktaking": 0.01, "patience": 0.4, "altruism": 0.01, "posrecip": 0.3, "negrecip": -0.5}
    red = NZ.reduced_bank(rows, z, train)
    for cc in ("GBR", "COL"):
        NZ.write_bank(nzd, cc, unit, z, red, bank_run_id=run_id, source_rows=len(rows))
        NZ.write_control_bank(nzd, f"{cc}_control", unit, NZ.control_bank(rows, train, red["train_kept"]),
                              bank_run_id=run_id, source_rows=len(rows), matched_to=cc)
    return prof, nzd, rows, red


def _bank2_env(monkeypatch, tmp_path, nzd, run_id="bank_t"):
    full = tmp_path / "bank"
    full.mkdir(exist_ok=True)
    body = {"run_id": run_id, "labeling_rule": "deterministic_sign", "n_triplets": 650,
            "per_dimension_triplet_counts": {k: 108 for k in F.DIMS}}
    (full / "manifest.json").write_text(json.dumps(body))
    prof = tmp_path / "profiles"
    (prof / "manifest.json").write_text(json.dumps({**body, "units": F.all_units()}))
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.setenv("SCA2_PB_UNITS", "profiles")
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path / "root"))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(full))
    monkeypatch.setenv("SCA2_PB_PROFILE_DIR", str(prof))
    monkeypatch.delenv("SCA2_PB_REPLICATE", raising=False)
    monkeypatch.setenv("SCA2_PB_NEARZERO", str(nzd))


def _reload_config():
    import config as C
    return importlib.reload(C)


def test_nearzero_switch_sets_units_paths_and_expected_train_rows(tmp_path, monkeypatch, pb_config_guard):
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    _bank2_env(monkeypatch, tmp_path, nzd)
    C = _reload_config()
    assert C.COHORT == UNITS
    assert C.HF_ADAPTER_PREFIX == "bank2/bank_t/near_zero"
    assert C.ADAPTER_DIR == tmp_path / "root" / "adapters_nearzero"
    assert C.EXPECTED_N_TRAIN == {u: red["train_kept"] for u in UNITS}
    assert C.BANK_RUN_ID == "bank_t"
    assert C.hub_adapter_path("GBR") == "bank2/bank_t/near_zero/GBR"
    assert C.hub_adapter_path("COL_control") == "bank2/bank_t/near_zero_control/COL"
    for u in UNITS:
        assert not C.hub_adapter_path(u).startswith("adapters/")


def test_nearzero_does_not_touch_the_frozen_bank_constants(tmp_path, monkeypatch, pb_config_guard):
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    _bank2_env(monkeypatch, tmp_path, nzd)
    C = _reload_config()
    assert C.N_ROWS == 650                  # the FULL bank manifest defines this, never the reduced one
    assert C.TRAIN_ROWS == int(650 * C.TRAIN_FRAC)


def test_nearzero_refuses_a_tampered_bank_file(tmp_path, monkeypatch, pb_config_guard):
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    f = nzd / "GBR" / "D_syn_GBR_nearzero.jsonl"
    f.write_text(f.read_text() + "\n")
    _bank2_env(monkeypatch, tmp_path, nzd)
    with pytest.raises(RuntimeError, match="sha256"):
        _reload_config()


def test_nearzero_refuses_a_bank_of_another_run(tmp_path, monkeypatch, pb_config_guard):
    prof, nzd, rows, red = _make_nz_dir(tmp_path, run_id="other_run")
    _bank2_env(monkeypatch, tmp_path, nzd, run_id="bank_t")
    with pytest.raises(RuntimeError, match="bank_run_id"):
        _reload_config()


def test_nearzero_refuses_a_missing_unit(tmp_path, monkeypatch, pb_config_guard):
    import shutil
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    shutil.rmtree(nzd / "COL_control")
    _bank2_env(monkeypatch, tmp_path, nzd)
    with pytest.raises(RuntimeError, match="COL_control"):
        _reload_config()


def test_nearzero_needs_profile_units_and_no_replicate(tmp_path, monkeypatch, pb_config_guard):
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    _bank2_env(monkeypatch, tmp_path, nzd)
    monkeypatch.setenv("SCA2_PB_REPLICATE", "r1")
    with pytest.raises(RuntimeError, match="REPLICATE"):
        _reload_config()


def test_default_cohort_one_config_is_unchanged_without_the_switch(monkeypatch, pb_config_guard):
    for k in ("SCA2_PB_PROTOCOL", "SCA2_PB_NEARZERO"):
        monkeypatch.delenv(k, raising=False)
    C = _reload_config()
    assert len(C.COHORT) == 42 and C.EXPECTED_N_TRAIN == {} and C.NEARZERO_DIR is None
    assert C.hub_adapter_path("ARG") == "adapters/ARG"


def test_run_record_n_train_is_per_unit_under_the_switch(tmp_path, monkeypatch, pb_config_guard):
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    _bank2_env(monkeypatch, tmp_path, nzd)
    C = _reload_config()
    import score_runtime as R
    R = importlib.reload(R)
    rec = {"country": "GBR_control", "model_name": C.MODEL_NAME, "beta": C.DPO_BETA, "lr": C.LEARNING_RATE,
           "epochs": C.NUM_TRAIN_EPOCHS, "max_length": C.MAX_LENGTH, "grad_accum": C.GRADIENT_ACCUMULATION_STEPS,
           "bank_run_id": C.BANK_RUN_ID, "lora": {"r": C.LORA_R, "alpha": C.LORA_ALPHA},
           "n_train": red["train_kept"]}
    assert R.validate_run_record(rec, country="GBR_control") is True
    with pytest.raises(ValueError, match="n_train"):
        R.validate_run_record({**rec, "n_train": C.TRAIN_ROWS}, country="GBR_control")   # the full-bank count


# ------------------------------------------------------------------ preparation
def _cache_for(rows):
    cache = {}
    for i, r in enumerate(rows):
        n = lib.normalize_row(r)
        cache[(n["prompt"], n["chosen"])] = -1.0 - i * 0.001
        cache[(n["prompt"], n["rejected"])] = -2.0 - i * 0.001
    return cache


def test_prepare_writes_the_manifest_train_rows_with_reference_logps(tmp_path):
    import near_zero_prepare as NP
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    cache = _cache_for(rows)
    out = tmp_path / "prepared"
    n = NP.prepare_unit("GBR", nzd, prof, cache, out)
    assert n == red["train_kept"]
    got = lib.load_jsonl(out / "GBR_train_with_ref.jsonl")
    assert len(got) == n
    for r in got:
        assert {"prompt", "chosen", "rejected", "ref_chosen_logps", "ref_rejected_logps", "country"} <= set(r)
        assert r["prompt"].startswith("Context: ") and r["country"] == "GBR"
        assert r["ref_chosen_logps"] == cache[(r["prompt"], r["chosen"])]
        assert r["ref_rejected_logps"] == cache[(r["prompt"], r["rejected"])]
    assert [r["prompt"] for r in got] == sorted(r["prompt"] for r in got)      # same order rule as prepare_data


def test_prepare_fails_when_a_pair_is_missing_from_the_cache(tmp_path):
    import near_zero_prepare as NP
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    cache = _cache_for(rows)
    cache.pop(next(iter(cache)))
    with pytest.raises(RuntimeError, match="reference cache"):
        NP.prepare_unit("GBR", nzd, prof, cache, tmp_path / "prepared")
    assert not (tmp_path / "prepared" / "GBR_train_with_ref.jsonl").exists()      # no half-written file


def test_prepare_fails_when_the_row_count_is_not_the_declared_one(tmp_path):
    import near_zero_prepare as NP
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    mpath = nzd / "GBR" / "manifest.json"
    m = json.loads(mpath.read_text())
    m["train_kept"] += 1
    mpath.write_text(json.dumps(m))
    with pytest.raises(RuntimeError, match="train rows"):
        NP.prepare_unit("GBR", nzd, prof, _cache_for(rows), tmp_path / "prepared")


def test_prepare_fails_when_a_train_row_is_not_a_training_row_of_the_full_bank(tmp_path):
    import near_zero_prepare as NP
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    f = nzd / "GBR" / "D_syn_GBR_nearzero.jsonl"
    data = lib.load_jsonl(f)
    ev = next(r for r in data if r["split"] == "eval")
    ev["split"] = "train"                                                    # an eval row relabelled as training
    lib.write_jsonl(data, f)
    m = json.loads((nzd / "GBR" / "manifest.json").read_text())
    m["sha256"][m["file"]] = hashlib.sha256(f.read_bytes()).hexdigest()
    m["train_kept"] += 1
    (nzd / "GBR" / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(RuntimeError, match="split"):
        NP.prepare_unit("GBR", nzd, prof, _cache_for(rows), tmp_path / "prepared")


def test_prepare_fails_when_a_label_differs_from_the_profile_file(tmp_path):
    import near_zero_prepare as NP
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    f = nzd / "GBR" / "D_syn_GBR_nearzero.jsonl"
    data = lib.load_jsonl(f)
    r0 = next(r for r in data if r["split"] == "train")
    r0["chosen"], r0["rejected"] = r0["rejected"], r0["chosen"]
    lib.write_jsonl(data, f)
    m = json.loads((nzd / "GBR" / "manifest.json").read_text())
    m["sha256"][m["file"]] = hashlib.sha256(f.read_bytes()).hexdigest()
    (nzd / "GBR" / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(RuntimeError, match="label"):
        NP.prepare_unit("GBR", nzd, prof, _cache_for(rows), tmp_path / "prepared")


@needs_real
def test_real_prepare_counts_are_164_and_260_for_refit_and_control(tmp_path):
    import near_zero_prepare as NP
    import config as C
    cache_path = Path("/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/refcache/shared_reference_logps.jsonl")
    if not cache_path.is_file():
        pytest.skip("the pinned reference cache is not downloaded on this machine")
    cache = lib.load_shared_cache(cache_path)
    for unit, n in (("GBR", 164), ("GBR_control", 164), ("COL", 260), ("COL_control", 260)):
        assert NP.prepare_unit(unit, REAL_NZ, REAL_PROFILES, cache, tmp_path) == n
    assert NP.EXPECTED_TRAIN_ROWS == {"GBR": 164, "COL": 260, "GBR_control": 164, "COL_control": 260}


# ------------------------------------------------------------------ scoring plan
OLD_PINS = {
    "strict_v1": "ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6",
    "heldout_v1": "46447de63f7cc161c016bdc38a3a7c9e8d351be308c44cf1ccd28d9091d13b38",
    "replicate_strict_v1": "ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6",
}


def _pins():
    return json.loads(SPL.PINS.read_text())


def test_nearzero_condition_run_id_units_and_strict_spec_pin():
    c = SPL.CONDITIONS["nearzero_strict_v1"]
    assert c["run_id"] == "bank2-nearzero-strict-v1-20261018"
    assert c["battery"] == "strict" and c["variant"] == "v1" and c["kind"] == "adapter"
    assert SPL.condition_units("nearzero_strict_v1") == UNITS
    pins = _pins()["spec_sha256"]
    assert pins["nearzero_strict_v1"] == pins["strict_v1"] == SPL.spec_hash(SPL.build_spec("nearzero_strict_v1"))
    assert pins["nearzero_strict_v1"].startswith("ed3bb964b606")
    for name, sha in OLD_PINS.items():                                 # append-only
        assert pins[name] == sha
    assert len({c["run_id"] for c in SPL.CONDITIONS.values()}) == len(SPL.CONDITIONS)


def test_existing_orders_and_run_ids_are_unchanged():
    assert SPL.ORDER == ["strict_v1", "heldout_v1", "signprompt_heldout_v1", "heldout_reverse", "heldout_para_a",
                         "heldout_para_b"]
    assert SPL.T4_ORDER == ["replicate_strict_v1", "replicate_heldout_v1", "signprompt_strict_v1"]
    assert SPL.ADAPTER_REVISION == "902f262e92bea5450f69335aa3977f28319ff3a1"
    assert _pins()["adapter_revision"] == SPL.ADAPTER_REVISION


def test_adapter_revision_for_a_nearzero_condition_comes_from_its_own_pin(tmp_path, monkeypatch):
    sha = "a" * 40
    monkeypatch.setattr(SPL, "PINS", tmp_path / "pins.json")
    (tmp_path / "pins.json").write_text(json.dumps({"adapter_revision": SPL.ADAPTER_REVISION, "spec_sha256": {}}))
    with pytest.raises(RuntimeError, match="nearzero_adapter_revision"):
        SPL.adapter_revision_for("nearzero_strict_v1")
    assert SPL.adapter_revision_for("strict_v1") == SPL.ADAPTER_REVISION
    SPL.pin_nearzero_revision(sha)
    assert SPL.adapter_revision_for("nearzero_strict_v1") == sha
    assert json.loads((tmp_path / "pins.json").read_text())["adapter_revision"] == SPL.ADAPTER_REVISION


def test_pin_nearzero_revision_is_append_only_and_validates_the_sha(tmp_path, monkeypatch):
    monkeypatch.setattr(SPL, "PINS", tmp_path / "pins.json")
    (tmp_path / "pins.json").write_text(json.dumps({"adapter_revision": SPL.ADAPTER_REVISION, "spec_sha256": {}}))
    with pytest.raises(ValueError):
        SPL.pin_nearzero_revision("main")
    SPL.pin_nearzero_revision("b" * 40)
    with pytest.raises(RuntimeError, match="already"):
        SPL.pin_nearzero_revision("c" * 40)
    SPL.pin_nearzero_revision("b" * 40)                                # same value again is a no-op


def test_nearzero_marker_must_match_unit_revision_and_weights():
    rev, sha = "d" * 40, "e" * 64
    good = {"gate_pass": True, "unit": "GBR", "adapter_revision": rev, "adapter_sha256": sha}
    SPL.check_marker_nearzero(good, "GBR", sha, rev)
    for bad, why in (({**good, "gate_pass": False}, "gate_pass"), ({**good, "unit": "COL"}, "unit"),
                     ({**good, "adapter_revision": "f" * 40}, "revision"), ({**good, "adapter_sha256": "0" * 64}, "weights")):
        with pytest.raises(RuntimeError, match=why):
            SPL.check_marker_nearzero(bad, "GBR", sha, rev)
    with pytest.raises(RuntimeError, match="weights"):
        SPL.check_marker_nearzero(good, "GBR", None, rev)             # no adapter SHA to compare against


def test_gate_marker_names_and_run_ids_are_per_unit_and_path_safe():
    import score_runtime as R
    names = {SPL.gate_marker_name(u) for u in UNITS}
    assert len(names) == 4
    runs = {SPL.gate_run_id_nearzero(u) for u in UNITS}
    assert len(runs) == 4
    for r in runs:
        R.require_path_token("run_id", r)
        assert r.endswith("20261018") and "nearzero" in r


def test_nearzero_chains_are_wired_to_the_right_scripts_and_env():
    rev = "9" * 40
    train = SPL.nearzero_train_steps()
    assert [s[0] for s in train] == ["nz_prepare", "nz_train"]
    assert train[0][1] == ["paper_b/near_zero_prepare.py"]
    assert train[1][1][:1] == ["paper_b/run_cohort.py"] and train[1][1][-1] == "--skip-prepare"
    assert train[1][1][train[1][1].index("--countries") + 1:-1] == UNITS
    for _, _, env in train:
        assert env["SCA2_PB_NEARZERO"] == SPL.NEARZERO_DIR_VM
    score = SPL.nearzero_score_steps(rev)
    names = [s[0] for s in score]
    assert names == [f"nz_gate_{u}" for u in UNITS] + ["nz_score"]
    for (name, args, env), u in zip(score[:4], UNITS):
        assert args == ["paper_b/colab/vm_gate_factorial.py"]
        assert env["GATE_UNIT"] == u and env["SCA2_PB_ADAPTER_REVISION"] == rev
        assert env["SCORE_RUN_ID"] == SPL.gate_run_id_nearzero(u)
        assert env["GATE_MARKER_NAME"] == SPL.gate_marker_name(u)
        assert env["SCA2_PB_NEARZERO"] == SPL.NEARZERO_DIR_VM
    assert score[4][1] == ["paper_b/colab/vm_score_t4.py", "nearzero_strict_v1"]
    assert score[4][2]["SCA2_PB_NEARZERO"] == SPL.NEARZERO_DIR_VM and score[4][2]["SCA2_PB_ADAPTER_REVISION"] == rev


def test_condition_env_for_nearzero_has_the_switch_and_no_replicate():
    env = SPL.condition_env("nearzero_strict_v1")
    assert env == {"SCA2_PB_NEARZERO": SPL.NEARZERO_DIR_VM}
    assert SPL.condition_env("strict_v1") == {}


def test_nearzero_resume_reads_the_hub_listing_and_spec(monkeypatch):
    run = SPL.CONDITIONS["nearzero_strict_v1"]["run_id"]
    spec = _pins()["spec_sha256"]["nearzero_strict_v1"]
    files = [f"runs/{run}/synthetic/{u}_adapter_option_probabilities.csv" for u in UNITS[:2]] + \
            [f"runs/{run}/manifests/{u}_adapter_manifest.json" for u in UNITS[:2]]
    seen = lambda r, m: {"spec_sha256": spec}  # noqa: E731
    assert SPL.todo_condition("nearzero_strict_v1", files, spec, seen) == UNITS[2:]
    assert SPL.todo_condition("nearzero_strict_v1", files, "x" * 64, seen) == UNITS


# ------------------------------------------------------------------ run record and state tag
def test_nearzero_record_fields_carry_arm_bank_and_row_count(tmp_path, monkeypatch, pb_config_guard):
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    _bank2_env(monkeypatch, tmp_path, nzd)
    C = _reload_config()
    f = P2.nearzero_record_fields(C, "COL_control")
    m = json.loads((nzd / "COL_control" / "manifest.json").read_text())
    assert f == {"nearzero_arm": "control", "nearzero_profile_unit": "P_1_1_1_1_0_1", "nearzero_bank_file": m["file"],
                 "nearzero_bank_sha256": m["sha256"][m["file"]], "nearzero_train_rows": red["train_kept"]}
    assert P2.nearzero_record_fields(C, "GBR")["nearzero_arm"] == "refit"


def test_no_nearzero_record_fields_outside_the_switch(monkeypatch, pb_config_guard):
    monkeypatch.delenv("SCA2_PB_NEARZERO", raising=False)
    monkeypatch.delenv("SCA2_PB_PROTOCOL", raising=False)
    C = _reload_config()
    assert P2.nearzero_record_fields(C, "GBR") == {}


def test_run_tag_gives_each_kind_of_run_its_own_state_folder():
    import run_cohort as RC
    assert RC.run_tag("r1", None, False) == "replicate_r1"
    assert RC.run_tag("", 1, False) == "wave1"
    assert RC.run_tag("", None, False) == "units"
    assert RC.run_tag("", None, True) == "nearzero"


# ------------------------------------------------------------------ bundle
def test_bundle_holds_only_the_four_units_and_is_byte_reproducible(tmp_path):
    import tarfile
    import near_zero_bundle as B
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    (nzd / "subset_declaration.json").write_text("{}")
    (nzd / "logs").mkdir()
    (nzd / "logs" / "x.txt").write_text("not for the Hub")
    sha1 = B.build_bundle(nzd, tmp_path / "a.tgz")
    sha2 = B.build_bundle(nzd, tmp_path / "b.tgz")
    assert sha1 == sha2 == hashlib.sha256((tmp_path / "a.tgz").read_bytes()).hexdigest()
    with tarfile.open(tmp_path / "a.tgz") as tf:
        names = tf.getnames()
    assert sorted(n.split("/")[0] for n in names) == sorted(u for u in UNITS for _ in range(2))
    assert not any("logs" in n or "subset" in n for n in names)
    assert all(n.endswith("manifest.json") or n.endswith(".jsonl") for n in names)


def test_bundle_extracts_to_banks_that_pass_the_manifest_check(tmp_path):
    import tarfile
    import near_zero_bundle as B
    prof, nzd, rows, red = _make_nz_dir(tmp_path)
    B.build_bundle(nzd, tmp_path / "a.tgz")
    dest = tmp_path / "vm"
    with tarfile.open(tmp_path / "a.tgz") as tf:
        tf.extractall(dest, filter="data")
    assert set(P2.load_nearzero_manifests(dest, "bank_t")) == set(UNITS)


def test_bundle_pin_is_append_only(tmp_path, monkeypatch):
    monkeypatch.setattr(SPL, "PINS", tmp_path / "pins.json")
    (tmp_path / "pins.json").write_text(json.dumps({"adapter_revision": SPL.ADAPTER_REVISION, "spec_sha256": {}}))
    with pytest.raises(ValueError):
        SPL.pin_nearzero_bundle("banks/x.tgz", "short")
    SPL.pin_nearzero_bundle("banks/x.tgz", "a" * 64)
    SPL.pin_nearzero_bundle("banks/x.tgz", "a" * 64)
    with pytest.raises(RuntimeError, match="already"):
        SPL.pin_nearzero_bundle("banks/y.tgz", "b" * 64)
    assert json.loads((tmp_path / "pins.json").read_text())["nearzero_bank_bundle"] == {
        "hub_path": "banks/x.tgz", "sha256": "a" * 64}


def test_run_cohort_keeps_the_case_of_unit_names_that_exist():
    import run_cohort as RC
    cohort = ["GBR", "COL", "GBR_control", "COL_control"]
    assert RC.resolve_units(["GBR", "COL_control"], cohort) == ["GBR", "COL_control"]
    assert RC.resolve_units(["gbr", "col"], cohort) == ["GBR", "COL"]           # cohort-1 behaviour: upper-cased
    assert RC.resolve_units(["ARG"], ["ARG", "AUS"]) == ["ARG"]
    assert RC.resolve_units(["nope"], cohort) == ["NOPE"]                       # unknown names still fail the later check


# ---- scoring run found these on the VM: three places still upper-cased 'GBR_control' to 'GBR_CONTROL' ----
def test_config_resolve_units_keeps_existing_unit_names():
    import config as C
    cohort = ["GBR", "COL", "GBR_control", "COL_control"]
    assert C.resolve_units(["GBR", "COL_control"], cohort) == ["GBR", "COL_control"]
    assert C.resolve_units(["gbr"], cohort) == ["GBR"]
    assert C.resolve_units(["nope"], cohort) == ["NOPE"]


def test_run_unit_accepts_a_mixed_case_unit_name(tmp_path, monkeypatch):
    import config as C
    import score_runtime as R
    import test_run_unit as T
    monkeypatch.setattr(C, "COHORT", ["GBR", "GBR_control"])
    spec = T._spec()
    prod, ref, sb = T._loaders(tmp_path, cc="GBR_control")
    result = R.run_unit(
        country="GBR_control", spec=spec, spec_sha=T._spec_sha(spec), revision=T.FULL_SHA,
        cache_root=tmp_path / "cache", run_id="run-1", repo=R.ARTIFACTS_REPO, hub=T.FakeHub(),
        code_revision=T.CODE_REV, local_dir=tmp_path / "out", downloader=None,
        production_scorer=prod, reference_scorer=ref, switchback_scorer=sb,
        tol_logprob=1e-9, tol_prob=1e-12)
    assert result["gate"]["gate_pass"] is True


def test_score_cohort_does_not_upper_case_unit_names_blindly():
    src = (HERE / "score_cohort.py").read_text()
    assert "c.upper() for c in" not in src
