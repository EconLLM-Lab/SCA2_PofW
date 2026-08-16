"""Load and hash a frozen SCA2 protocol file."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

REQUIRED_TABLES = ("anchor", "profile", "generation", "qc", "prompts", "train", "eval")

REPO_ROOT = Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return REPO_ROOT


def load_protocol(path: str | Path) -> dict[str, Any]:
    protocol_path = Path(path).expanduser().resolve()
    if not protocol_path.is_file():
        raise FileNotFoundError(f"protocol not found: {protocol_path}")
    if protocol_path.suffix.lower() != ".toml":
        raise ValueError(f"protocol must be a .toml file, got {protocol_path.suffix}")
    with protocol_path.open("rb") as handle:
        data = tomllib.load(handle)
    missing = [name for name in REQUIRED_TABLES if name not in data]
    if missing:
        raise ValueError(f"protocol missing tables: {', '.join(missing)}")
    data["_path"] = str(protocol_path)
    data["_hash"] = protocol_hash(protocol_path)
    return data


def protocol_hash(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    return hashlib.sha256(raw).hexdigest()[:16]


def resolve_repo_path(relative: str, root: Path | None = None) -> Path:
    base = root or REPO_ROOT
    candidate = Path(relative)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def public_protocol(data: dict[str, Any]) -> dict[str, Any]:
    """Drop loader bookkeeping before writing a receipt."""

    return {key: value for key, value in data.items() if not key.startswith("_")}


def dump_public_protocol(data: dict[str, Any]) -> str:
    return json.dumps(public_protocol(data), indent=2, sort_keys=True) + "\n"
