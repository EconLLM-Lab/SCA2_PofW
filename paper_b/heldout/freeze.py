"""The blinding gate: no held-out human value is read before FREEZE.json exists.

`freeze()` records the hashes of the selection and the pool and refuses to run twice.
`require_freeze()` is called by every reader of held-out human data; it fails closed
when FREEZE.json is absent or when either frozen file has changed since.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze(*, selection_path: Path, pool_path: Path, freeze_path: Path,
           code_revision: str, run_ids: dict[str, str], rubric: dict | None = None) -> dict:
    import pandas as pd
    freeze_path = Path(freeze_path)
    if freeze_path.exists():
        raise RuntimeError(f"already frozen: {freeze_path} (a selection is frozen once)")
    sel = pd.read_csv(selection_path)
    payload = {
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "selection_path": str(selection_path), "selection_sha256": _sha(selection_path),
        "pool_path": str(pool_path), "pool_sha256": _sha(pool_path),
        "code_revision": code_revision, "run_ids": run_ids,
        "selected_items": int(sel["primary_selected"].astype(bool).sum())
        if "primary_selected" in sel else None,
        "n_items": int(len(sel)),
        "rubric": rubric or {},
    }
    freeze_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def require_freeze(freeze_path: Path) -> dict:
    fp = Path(freeze_path)
    if not fp.is_file():
        raise RuntimeError(
            f"BLOCKED: {fp} does not exist. The held-out human criterion may not be read "
            "before the item selection is frozen (FREEZE guard, preregistration section 5).")
    payload = json.loads(fp.read_text())
    for key in ("selection", "pool"):
        path = payload.get(f"{key}_path")
        if path and Path(path).is_file() and _sha(Path(path)) != payload[f"{key}_sha256"]:
            raise RuntimeError(f"BLOCKED: {path} changed after the freeze")
    return payload
