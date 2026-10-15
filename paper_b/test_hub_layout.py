"""Adapter resolution must follow config.hub_adapter_path (cohort 1 and bank-2 profiles)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "paper_b"))

SHA = "a" * 40


def _place(dest_root: Path, rel: str, unit: str, run_id: str, n_train: int):
    d = dest_root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "adapter_config.json").write_text("{}")
    (d / "adapter_model.safetensors").write_bytes(b"w")
    (d / "run_record.json").write_text(json.dumps({
        "country": unit, "model_name": "meta-llama/Llama-3.1-8B-Instruct", "beta": 0.1,
        "lr": 1e-4, "epochs": 1, "max_length": 768, "grad_accum": 16,
        "bank_run_id": run_id, "lora": {"r": 16, "alpha": 32}, "n_train": n_train}))


def test_cohort1_layout_unchanged(tmp_path):
    import score_runtime as R
    seen = {}

    def dl(cc, dest, rev):
        seen["rel"] = f"adapters/{cc}"
        _place(dest, f"adapters/{cc}", cc, "gps_sign_relabel_all_20260816_004545Z", 526)

    path, src = R.resolve_adapter("CHN", SHA, tmp_path, downloader=dl)
    assert path == R.revision_cache_dir(tmp_path, SHA) / "adapters" / "CHN" and src == "hub"


def test_profile_layout_uses_hub_prefix(tmp_path, monkeypatch):
    import importlib
    import factorial as F
    run_id = "gps_sign_relabel_bank2_test"
    for name, units in (("bank", None), ("profiles", F.all_units())):
        d = tmp_path / name
        d.mkdir()
        body = {"run_id": run_id, "labeling_rule": "deterministic_sign", "n_triplets": 650,
                "per_dimension_triplet_counts": {k: 108 for k in F.DIMS}}
        if units:
            body["units"] = units
        (d / "manifest.json").write_text(json.dumps(body))
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.setenv("SCA2_PB_UNITS", "profiles")
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path / "root"))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(tmp_path / "bank"))
    monkeypatch.setenv("SCA2_PB_PROFILE_DIR", str(tmp_path / "profiles"))
    import config as C
    importlib.reload(C)
    import score_runtime as R
    importlib.reload(R)
    try:
        unit = "P_1_0_1_0_1_0"
        rel = f"bank2/{run_id}/profiles/{unit}"
        assert C.hub_adapter_path(unit) == rel
        patterns = {}

        def dl(cc, dest, rev):
            patterns["p"] = rel
            _place(dest, rel, cc, run_id, 520)

        path, _ = R.resolve_adapter(unit, SHA, tmp_path / "cache", downloader=dl)
        assert path == R.revision_cache_dir(tmp_path / "cache", SHA) / rel
        assert R.default_allow_patterns(unit) == [f"{rel}/*"]
    finally:
        for k in ("SCA2_PB_PROTOCOL", "SCA2_PB_UNITS"):
            monkeypatch.delenv(k)
        importlib.reload(C)
        importlib.reload(R)
