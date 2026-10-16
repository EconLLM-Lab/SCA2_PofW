"""Bank2 protocol switch. Imported only when SCA2_PB_PROTOCOL=bank2.

Does not edit paper_b/config.py. Cohort 1 constants stay the defaults.

Bank-size rule (amended 2026-10-14, Augusto: a second bank must be statistically
similar to bank 1, not byte-identical): a bank is accepted when it carries
MIN_TRIPLETS..MAX_TRIPLETS shared triplets with at least MIN_PER_DIMENSION per GPS
dimension. Pairs are never padded or trimmed to hit a count.

Units (SCA2_PB_UNITS):
  countries  (default) the 42 GPS∩WVS7 countries; hub prefix bank2/<run>/adapters
  profiles   the 64 sign-profile factorial cells (paper_b/factorial.py); hub prefix
             bank2/<run>/profiles; requires SCA2_PB_PROFILE_DIR
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

COHORT1_BANK_RUN_ID = "gps_sign_relabel_all_20260816_004545Z"
COHORT1_PREFIX = "adapters"
MIN_TRIPLETS = 640
MAX_TRIPLETS = 660
MIN_PER_DIMENSION = 100
N_FACTORIAL_UNITS = 64


def bank2_selected() -> bool:
    return os.environ.get("SCA2_PB_PROTOCOL") == "bank2"


_REPLICATE_TAG = re.compile(r"^[a-z0-9]{1,16}$")


def replicate_tag() -> str:
    """Optional SCA2_PB_REPLICATE: retrain units to separate paths (training-noise audit).

    A replicate never shares a Hub prefix or a local adapter directory with the original run, so
    it can neither overwrite nor be mistaken for it.
    """
    tag = os.environ.get("SCA2_PB_REPLICATE", "").strip()
    if tag and not _REPLICATE_TAG.match(tag):
        raise RuntimeError(f"SCA2_PB_REPLICATE must match [a-z0-9]{{1,16}}, got {tag!r}")
    return tag


def load_bank_manifest(path: Path) -> dict:
    """Validate a bank (or profile-bank) manifest against the frozen band. Fail closed."""
    path = Path(path)
    if not path.is_file():
        raise RuntimeError(f"bank2 manifest missing: {path}")
    manifest = json.loads(path.read_text())
    if manifest.get("labeling_rule") != "deterministic_sign":
        raise RuntimeError("bank2 manifest labeling_rule is not deterministic_sign")
    n = int(manifest.get("n_triplets") or 0)
    if not MIN_TRIPLETS <= n <= MAX_TRIPLETS:
        raise RuntimeError(
            f"{path}: {n} triplets is outside the frozen band [{MIN_TRIPLETS}, {MAX_TRIPLETS}]; "
            "refusing to train. Do not pad or drop pairs.")
    per_dim = manifest.get("per_dimension_triplet_counts") or {}
    if not per_dim:
        raise RuntimeError(f"{path}: per_dimension_triplet_counts missing")
    thin = {d: int(v) for d, v in per_dim.items() if int(v) < MIN_PER_DIMENSION}
    if thin:
        raise RuntimeError(f"{path}: thin dimensions {thin} (< {MIN_PER_DIMENSION})")
    run_id = str(manifest.get("run_id") or "")
    if not run_id or run_id == COHORT1_BANK_RUN_ID:
        raise RuntimeError(f"bank2 run_id is missing or collides with cohort 1: {run_id!r}")
    return manifest


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
    manifest = load_bank_manifest(bank_dir / "manifest.json")
    run_id = manifest["run_id"]
    n_triplets = int(manifest["n_triplets"])

    units = os.environ.get("SCA2_PB_UNITS", "countries").strip() or "countries"
    if units not in ("countries", "profiles"):
        raise RuntimeError(f"SCA2_PB_UNITS must be countries|profiles, got {units!r}")
    prefix = f"bank2/{run_id}/adapters"
    if units == "profiles":
        prof_env = os.environ.get("SCA2_PB_PROFILE_DIR", "").strip()
        if not prof_env:
            raise RuntimeError("SCA2_PB_UNITS=profiles requires SCA2_PB_PROFILE_DIR")
        prof_dir = Path(prof_env)
        prof = load_bank_manifest(prof_dir / "manifest.json")
        if prof["run_id"] != run_id or int(prof["n_triplets"]) != n_triplets:
            raise RuntimeError(
                "profile bank does not match the bank2 manifest "
                f"(run_id {prof['run_id']!r} vs {run_id!r}, n {prof['n_triplets']} vs {n_triplets})")
        unit_list = [str(u) for u in prof.get("units") or []]
        if len(unit_list) != N_FACTORIAL_UNITS or len(set(unit_list)) != N_FACTORIAL_UNITS:
            raise RuntimeError(f"expected {N_FACTORIAL_UNITS} distinct units, got {len(unit_list)}")
        bank_dir = prof_dir
        config_module.COHORT = unit_list
        prefix = f"bank2/{run_id}/profiles"

    data_root = Path(root)
    rep = replicate_tag()
    adapter_dir = data_root / "adapters"
    if rep:
        head, _, tail = prefix.rpartition("/")                 # bank2/<run>/profiles -> .../replicates/<tag>/profiles
        prefix = f"{head}/replicates/{rep}/{tail}"
        adapter_dir = data_root / f"adapters_replicate_{rep}"
    config_module.BANK_DIR = bank_dir
    config_module.BANK_RUN_ID = run_id
    config_module.N_ROWS = n_triplets
    config_module.TRAIN_ROWS = int(n_triplets * config_module.TRAIN_FRAC)
    config_module.UNITS = units
    config_module.DATA_ROOT = data_root
    config_module.PREPARED_DIR = data_root / "prepared"
    config_module.ADAPTER_DIR = adapter_dir
    config_module.REF_CACHE_FILE = data_root / "shared_reference_logps.jsonl"
    config_module.REF_MANIFEST_FILE = data_root / "shared_reference_logps_manifest.json"
    config_module.RUN_MANIFEST_FILE = data_root / "run_manifest.json"
    config_module.LOG_DIR = data_root / "logs"
    config_module.HF_ADAPTER_PREFIX = prefix


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
