"""Canonical paths for the public protocol package."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS_DIR = REPO_ROOT / "sca2" / "protocols"
DEFAULT_PROTOCOL = PROTOCOLS_DIR / "gps_sign_dpo_wvs.toml"
QUESTION_MAP = REPO_ROOT / "sca2" / "data" / "question_map_wvs_edited.csv"
