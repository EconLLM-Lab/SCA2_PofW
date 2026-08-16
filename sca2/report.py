"""Assemble a paper-citable report.json from stage receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .protocol import load_protocol, repo_root
from .runs import format_receipt, new_run_id, prepare_run_dir, write_receipt

STAGES = ("generate", "label", "train", "eval")


def file_sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_receipt(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_stage_receipts(runs_root: Path, protocol_hash: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not runs_root.is_dir():
        return latest
    for receipt_path in sorted(runs_root.glob("*/receipt.json")):
        try:
            receipt = load_receipt(receipt_path)
        except (OSError, json.JSONDecodeError):
            continue
        if receipt.get("protocol_hash") != protocol_hash:
            continue
        stage = receipt.get("stage")
        if stage not in STAGES:
            continue
        receipt["_receipt_path"] = str(receipt_path)
        receipt["_receipt_sha16"] = file_sha16(receipt_path)
        receipt["_mtime"] = receipt_path.stat().st_mtime
        previous = latest.get(stage)
        if previous is None or receipt["_mtime"] >= previous["_mtime"]:
            latest[stage] = receipt
    return latest


def chain_ok(stages: dict[str, dict[str, Any]]) -> tuple[bool, list[str]]:
    hashes = {stage: rec.get("protocol_hash") for stage, rec in stages.items()}
    unique = {value for value in hashes.values() if value}
    missing = [name for name in STAGES if name not in stages]
    notes: list[str] = []
    if missing:
        notes.append("missing:" + ",".join(missing))
    if len(unique) > 1:
        notes.append("protocol_hash_mismatch")
    ok = not missing and len(unique) == 1
    return ok, notes


def build_report(
    protocol: dict[str, Any],
    stages: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ok, notes = chain_ok(stages)
    return {
        "protocol_name": protocol["name"],
        "protocol_hash": protocol["_hash"],
        "protocol_path": protocol["_path"],
        "stages": {
            name: {
                "run_id": rec.get("run_id"),
                "status": rec.get("status"),
                "receipt_sha16": rec.get("_receipt_sha16"),
                "out": rec.get("out"),
                "rows": rec.get("rows"),
                "rule": rec.get("rule"),
            }
            for name, rec in stages.items()
        },
        "chain_ok": ok,
        "notes": notes,
        "claim_boundary": (
            "This file cites a protocol hash and the latest matching stage receipts. "
            "It is not a trained adapter and not a WVS result."
        ),
    }


def run_report(
    protocol_path: str | Path,
    *,
    runs_root: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    root = Path(runs_root) if runs_root else repo_root() / "runs"
    stages = collect_stage_receipts(root, protocol["_hash"])
    report = build_report(protocol, stages)
    run_id = new_run_id(str(protocol["name"]))
    run_dir = prepare_run_dir(root, run_id, protocol)
    report_path = run_dir / "report.json"
    report["run_id"] = run_id
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "run_id": run_id,
        "stage": "report",
        "status": "chained" if report["chain_ok"] else "incomplete",
        "protocol_name": protocol["name"],
        "protocol_hash": protocol["_hash"],
        "protocol_path": protocol["_path"],
        "out": str(report_path),
        "stages": list(stages),
        "notes": report["notes"],
    }
    write_receipt(run_dir, receipt)
    print(format_receipt(receipt))
    print(f"chain     {'ok' if report['chain_ok'] else 'incomplete'}  {', '.join(report['notes']) or 'all four stages'}")
    return receipt
