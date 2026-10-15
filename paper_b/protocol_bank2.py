"""Bank2 protocol switch. Imported only when SCA2_PB_PROTOCOL=bank2.

Does not edit paper_b/config.py. Cohort 1 constants stay the defaults.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

COHORT1_BANK_RUN_ID = "gps_sign_relabel_all_20260816_004545Z"
COHORT1_PREFIX = "adapters"
REQUIRED_TRIPLETS = 658


def bank2_selected() -> bool:
    return os.environ.get("SCA2_PB_PROTOCOL") == "bank2"


def apply(config_module) -> None:
    """Point the imported config module at the new bank. Fail closed."""
    if not bank2_selected():
        return
    root = os.environ.get("SCA2_PB_DATA_ROOT", "").strip()
    if not root:
        raise RuntimeError("SCA2_PB_PROTOCOL=bank2 requires SCA2_PB_DATA_ROOT")
    bank_env = os.environ.get("SCA2_PB_BANK2_DIR", "").strip()
    bank_dir = Path(bank_env) if bank_env else (
        config_module.REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_bank2"
    )
    manifest_path = bank_dir / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"bank2 manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("labeling_rule") != "deterministic_sign":
        raise RuntimeError("bank2 manifest labeling_rule is not deterministic_sign")
    n_triplets = int(manifest.get("n_triplets") or 0)
    if n_triplets != REQUIRED_TRIPLETS:
        raise RuntimeError(
            f"bank2 has {n_triplets} triplets, not {REQUIRED_TRIPLETS}; "
            "refusing to train. Do not pad or drop pairs."
        )
    run_id = str(manifest.get("run_id") or "")
    if not run_id or run_id == COHORT1_BANK_RUN_ID:
        raise RuntimeError(f"bank2 run_id is missing or collides with cohort 1: {run_id!r}")
    data_root = Path(root)
    config_module.BANK_DIR = bank_dir
    config_module.BANK_RUN_ID = run_id
    config_module.N_ROWS = n_triplets
    config_module.DATA_ROOT = data_root
    config_module.PREPARED_DIR = data_root / "prepared"
    config_module.ADAPTER_DIR = data_root / "adapters"
    config_module.REF_CACHE_FILE = data_root / "shared_reference_logps.jsonl"
    config_module.REF_MANIFEST_FILE = data_root / "shared_reference_logps_manifest.json"
    config_module.RUN_MANIFEST_FILE = data_root / "run_manifest.json"
    config_module.LOG_DIR = data_root / "logs"
    config_module.HF_ADAPTER_PREFIX = f"bank2/{run_id}/adapters"


def hub_adapter_path_from_prefix(prefix: str, country_code: str) -> str:
    prefix = str(prefix).strip("/")
    path = f"{prefix}/{country_code}"
    if bank2_selected():
        if prefix == COHORT1_PREFIX or path.startswith("adapters/"):
            raise RuntimeError("bank2 refuses to upload onto adapters/<CC>")
        if not path.startswith("bank2/"):
            raise RuntimeError(f"bank2 upload path must start with bank2/: {path}")
    return path


def hub_adapter_path(config_module, country_code: str) -> str:
    prefix = str(getattr(config_module, "HF_ADAPTER_PREFIX", COHORT1_PREFIX))
    return hub_adapter_path_from_prefix(prefix, country_code)
