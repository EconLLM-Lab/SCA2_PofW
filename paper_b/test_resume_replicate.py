"""Resume planning and replicate paths for the bank-2 factorial (no GPU)."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_plan_unit_actions():
    import run_cohort as RC
    plan = RC.plan_unit
    # bank 2: the Hub is the truth
    assert plan(bank2=True, on_hub=True, local_complete=False, recorded_bank="", bank_id="B") == "skip_hub"
    assert plan(bank2=True, on_hub=True, local_complete=True, recorded_bank="B", bank_id="B") == "skip_hub"
    # finished locally but never reached the Hub: upload it, do not retrain 15 minutes of GPU
    assert plan(bank2=True, on_hub=False, local_complete=True, recorded_bank="B", bank_id="B") == "reupload"
    # a different bank on disk is refused, never reused
    assert plan(bank2=True, on_hub=False, local_complete=True, recorded_bank="OTHER", bank_id="B") == "refuse"
    assert plan(bank2=True, on_hub=False, local_complete=False, recorded_bank="", bank_id="B") == "train"
    # cohort 1 behaviour is unchanged
    assert plan(bank2=False, on_hub=False, local_complete=True, recorded_bank="", bank_id="B") == "skip_local"
    assert plan(bank2=False, on_hub=False, local_complete=False, recorded_bank="", bank_id="B") == "train"


def _bank_dirs(tmp_path, F, run_id="gps_sign_relabel_bank2_test"):
    for name, units in (("bank", None), ("profiles", F.all_units())):
        d = tmp_path / name
        d.mkdir()
        body = {"run_id": run_id, "labeling_rule": "deterministic_sign", "n_triplets": 650,
                "per_dimension_triplet_counts": {k: 108 for k in F.DIMS}}
        if units:
            body["units"] = units
        (d / "manifest.json").write_text(json.dumps(body))
    return run_id


def _env(monkeypatch, tmp_path, replicate=None):
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.setenv("SCA2_PB_UNITS", "profiles")
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path / "root"))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(tmp_path / "bank"))
    monkeypatch.setenv("SCA2_PB_PROFILE_DIR", str(tmp_path / "profiles"))
    if replicate:
        monkeypatch.setenv("SCA2_PB_REPLICATE", replicate)
    else:
        monkeypatch.delenv("SCA2_PB_REPLICATE", raising=False)


def test_replicate_gets_its_own_hub_prefix_and_local_dir(tmp_path, monkeypatch, pb_config_guard):
    import factorial as F
    run_id = _bank_dirs(tmp_path, F)
    _env(monkeypatch, tmp_path, replicate="r1")
    import config as C
    importlib.reload(C)
    try:
        unit = "P_1_0_1_1_0_1"
        assert C.hub_adapter_path(unit) == f"bank2/{run_id}/replicates/r1/profiles/{unit}"
        assert C.ADAPTER_DIR == Path(tmp_path / "root") / "adapters_replicate_r1"
        assert "bank2/" + run_id + "/profiles/" not in C.hub_adapter_path(unit)   # cannot collide with the original
    finally:
        monkeypatch.delenv("SCA2_PB_PROTOCOL"); monkeypatch.delenv("SCA2_PB_REPLICATE", raising=False)
        importlib.reload(C)


def test_without_replicate_the_original_paths_are_unchanged(tmp_path, monkeypatch, pb_config_guard):
    import factorial as F
    run_id = _bank_dirs(tmp_path, F)
    _env(monkeypatch, tmp_path)
    import config as C
    importlib.reload(C)
    try:
        assert C.hub_adapter_path("P_0_0_0_0_0_0") == f"bank2/{run_id}/profiles/P_0_0_0_0_0_0"
        assert C.ADAPTER_DIR == Path(tmp_path / "root") / "adapters"
    finally:
        monkeypatch.delenv("SCA2_PB_PROTOCOL")
        importlib.reload(C)


@pytest.mark.parametrize("bad", ["", "R 1", "../x", "r1/", "A" * 40])
def test_replicate_tag_is_validated(tmp_path, monkeypatch, bad, pb_config_guard):
    import factorial as F
    _bank_dirs(tmp_path, F)
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("SCA2_PB_REPLICATE", bad)
    import config as C
    try:
        if bad == "":                                   # empty means "no replicate"
            importlib.reload(C)
        else:
            with pytest.raises(RuntimeError, match="SCA2_PB_REPLICATE"):
                importlib.reload(C)
    finally:
        monkeypatch.delenv("SCA2_PB_PROTOCOL"); monkeypatch.delenv("SCA2_PB_REPLICATE", raising=False)
        importlib.reload(C)
