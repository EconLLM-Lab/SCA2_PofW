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
    with pytest.raises(RuntimeError, match="not 658"):
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
