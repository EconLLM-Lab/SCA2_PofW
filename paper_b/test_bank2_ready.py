"""CPU checks for the bank2 switch and the sign-profile prompt. No GPU."""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "paper_b"))


def test_cohort1_upload_path_unchanged(monkeypatch):
    monkeypatch.delenv("SCA2_PB_PROTOCOL", raising=False)
    import protocol_bank2 as pb
    assert pb.hub_adapter_path_from_prefix("adapters", "CHN") == "adapters/CHN"


def test_bank2_refuses_cohort1_prefix(monkeypatch):
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    import protocol_bank2 as pb
    with pytest.raises(RuntimeError, match="refuses"):
        pb.hub_adapter_path_from_prefix("adapters", "CHN")


def test_bank2_apply_requires_fresh_root_and_658(tmp_path, monkeypatch):
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.delenv("SCA2_PB_DATA_ROOT", raising=False)
    import protocol_bank2 as pb
    mod = type("C", (), {"REPO": tmp_path})()
    with pytest.raises(RuntimeError, match="SCA2_PB_DATA_ROOT"):
        pb.apply(mod)

    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "manifest.json").write_text(json.dumps({
        "run_id": "gps_sign_relabel_bank2_test",
        "labeling_rule": "deterministic_sign",
        "n_triplets": 100,
    }))
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path / "fresh"))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(bank))
    with pytest.raises(RuntimeError, match="outside the frozen band"):
        pb.apply(mod)


def test_sign_prompt_has_no_country_and_uses_training_sign():
    import sign_prompt as sp
    signs = {d: "positive" for d in sp.DIMS}
    signs["patience"] = "negative"
    text = sp.sign_prompt(signs)
    assert sp.leak_hits(text) == []
    assert "patience: negative" in text
    assert sp.sign_word(0.0) == "positive"
    assert sp.sign_word(-0.01) == "negative"
    assert "0.01" not in text


def test_profiles_collapse_sign_mates():
    import sign_prompt as sp
    z = {
        "AUS": {d: 1.0 for d in sp.DIMS},
        "CAN": {d: 0.2 for d in sp.DIMS},
        "EGY": {d: -1.0 for d in sp.DIMS},
    }
    rows = sp.profiles_from_gps(z, ["AUS", "CAN", "EGY"])
    assert len(rows) == 2
    positive = next(r for r in rows if "AUS" in r["members"])
    assert positive["members"] == ["AUS", "CAN"]
    assert sp.leak_hits(positive["prompt"]) == []


def _write_manifest(d, n=650, run_id="gps_sign_relabel_bank2_test", units=None, per_dim=108):
    d.mkdir(parents=True, exist_ok=True)
    body = {"run_id": run_id, "labeling_rule": "deterministic_sign", "n_triplets": n,
            "per_dimension_triplet_counts": {k: per_dim for k in
                ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]}}
    if units is not None:
        body["units"] = units
    (d / "manifest.json").write_text(json.dumps(body))


def _profiles_env(monkeypatch, tmp_path, **kw):
    import factorial as F
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.setenv("SCA2_PB_UNITS", "profiles")
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path / "root"))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(tmp_path / "bank"))
    monkeypatch.setenv("SCA2_PB_PROFILE_DIR", str(tmp_path / "profiles"))
    _write_manifest(tmp_path / "bank", **kw)
    _write_manifest(tmp_path / "profiles", units=F.all_units(), **kw)


def test_profiles_switch_sets_units_rows_and_prefix(tmp_path, monkeypatch):
    import protocol_bank2 as pb
    _profiles_env(monkeypatch, tmp_path, n=655)
    mod = type("C", (), {"REPO": tmp_path, "TRAIN_FRAC": 0.80})()
    pb.apply(mod)
    assert mod.N_ROWS == 655 and mod.TRAIN_ROWS == 524
    assert len(mod.COHORT) == 64 and mod.UNITS == "profiles"
    assert mod.BANK_DIR == tmp_path / "profiles"
    assert mod.HF_ADAPTER_PREFIX == "bank2/gps_sign_relabel_bank2_test/profiles"
    assert pb.hub_adapter_path(mod, "P_1_1_1_1_1_1") == \
        "bank2/gps_sign_relabel_bank2_test/profiles/P_1_1_1_1_1_1"


def test_band_and_thin_dimension_refusals(tmp_path, monkeypatch):
    import protocol_bank2 as pb
    mod = type("C", (), {"REPO": tmp_path, "TRAIN_FRAC": 0.80})()
    _profiles_env(monkeypatch, tmp_path, n=661)
    with pytest.raises(RuntimeError, match="outside the frozen band"):
        pb.apply(mod)
    _profiles_env(monkeypatch, tmp_path, n=650, per_dim=99)
    with pytest.raises(RuntimeError, match="thin dimensions"):
        pb.apply(mod)


def test_profiles_require_matching_bank(tmp_path, monkeypatch):
    import factorial as F
    import protocol_bank2 as pb
    _profiles_env(monkeypatch, tmp_path, n=650)
    _write_manifest(tmp_path / "profiles", n=651, units=F.all_units())
    mod = type("C", (), {"REPO": tmp_path, "TRAIN_FRAC": 0.80})()
    with pytest.raises(RuntimeError, match="does not match"):
        pb.apply(mod)


def test_cohort1_config_is_untouched_without_the_switch(monkeypatch):
    import importlib
    for k in ("SCA2_PB_PROTOCOL", "SCA2_PB_UNITS"):
        monkeypatch.delenv(k, raising=False)
    import config as C
    importlib.reload(C)
    assert C.N_ROWS == 658 and C.TRAIN_ROWS == 526 and len(C.COHORT) == 42
    assert C.hub_adapter_path("CHN") == "adapters/CHN"
