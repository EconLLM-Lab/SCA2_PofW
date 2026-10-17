"""Read one local synthetic DPO record. Do not copy the file."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def first_record(path: Path) -> dict:
    """Return the first JSON object in a JSONL bank.

    The caller keeps the file in place. This function does not write a copy.
    """
    with path.open(encoding="utf-8") as handle:
        line = handle.readline()
    if not line:
        raise ValueError(f"empty bank: {path}")
    record = json.loads(line)
    prompt = record.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise ValueError(f"bank record has no prompt: {path}")
    return record


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
