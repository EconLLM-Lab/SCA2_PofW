"""Run-directory layout and receipts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .protocol import dump_public_protocol


def new_run_id(protocol_name: str, when: datetime | None = None, stage: str | None = None) -> str:
    stamp = (when or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%SZ")
    suffix = f"_{stage}" if stage else ""
    return f"{stamp}_{protocol_name}{suffix}"


def prepare_run_dir(runs_root: Path, run_id: str, protocol: dict[str, Any]) -> Path:
    run_dir = runs_root / run_id
    (run_dir / "data").mkdir(parents=True, exist_ok=True)
    (run_dir / "protocol.toml").write_text(
        Path(protocol["_path"]).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (run_dir / "protocol.json").write_text(dump_public_protocol(protocol), encoding="utf-8")
    return run_dir


def write_receipt(run_dir: Path, receipt: dict[str, Any]) -> Path:
    path = run_dir / "receipt.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def format_receipt(receipt: dict[str, Any]) -> str:
    lines = [
        f"run_id    {receipt.get('run_id')}",
        f"stage     {receipt.get('stage')}",
        f"protocol  {receipt.get('protocol_name')}  hash={receipt.get('protocol_hash')}",
        f"status    {receipt.get('status')}",
    ]
    for key in ("rows", "countries", "triplets", "rule", "out"):
        if key in receipt:
            lines.append(f"{key:<9} {receipt[key]}")
    return "\n".join(lines)
