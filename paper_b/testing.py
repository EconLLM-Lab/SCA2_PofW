"""Shared pytest guard for licensed, local-only inputs."""

from __future__ import annotations

from pathlib import Path

import pytest

# A data fence can leave the README directory in place after the parquet/csv
# payload is removed. Existence of that directory is not the licensed input.
_PAYLOAD_SUFFIXES = {".csv", ".parquet", ".jsonl", ".tsv", ".dta", ".sav", ".xlsx"}


def _payload_absent(path: Path) -> str | None:
    if not path.exists():
        return f"{path} (path absent)"
    if path.is_file():
        return None
    if any(child.is_file() and child.suffix.lower() in _PAYLOAD_SUFFIXES for child in path.rglob("*")):
        return None
    return f"{path} (directory has no licensed data files)"


def requires_withheld(*paths: Path, reason: str) -> None:
    """Skip when a file withheld from the public export is absent. Assertions stay intact."""
    missing = [str(Path(path)) for path in paths if not Path(path).is_file()]
    if missing:
        pytest.skip(reason + ": " + ", ".join(missing))


def requires_local_data(*paths: Path) -> None:
    """Skip only when a required local input is absent; assertions stay intact."""
    missing = [reason for path in paths if (reason := _payload_absent(Path(path)))]
    if missing:
        pytest.skip(
            "requires licensed local data absent from this checkout: " + ", ".join(missing)
        )
