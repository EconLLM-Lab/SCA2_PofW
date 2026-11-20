"""Continuous GPS z from the researcher's own download.

The public bank ships sign labels only. Real z-scores are not in git.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GPS_DTA = REPO / "data" / "GPS" / "GPS_dataset_country_level" / "country_gps.dta"
DIMS = ("trust", "risktaking", "patience", "altruism", "posrecip", "negrecip")

MISSING = (
    "GPS z-scores are not in this checkout. The public bank ships sign labels only. "
    "Download the GPS country file and place it at "
    "data/GPS/GPS_dataset_country_level/country_gps.dta (see DATA.md)."
)


def missing_gps_error() -> FileNotFoundError:
    return FileNotFoundError(MISSING)


def _continuous(value: object) -> bool:
    if isinstance(value, bool) or isinstance(value, str) or value is None:
        return False
    if isinstance(value, (int, float)):
        return float(value) not in (-1.0, 0.0, 1.0)
    if isinstance(value, dict):
        return any(_continuous(v) for v in value.values())
    return False


def load_country_z() -> dict[str, dict[str, float]]:
    """Read country_gps.dta. Raise a clear error if the file is absent."""
    if not GPS_DTA.is_file():
        raise missing_gps_error()
    import pandas as pd

    frame = pd.read_stata(GPS_DTA, convert_categoricals=False)
    if not isinstance(frame, pd.DataFrame):
        raise TypeError(f"expected a table from {GPS_DTA}, got {type(frame).__name__}")
    missing = [dim for dim in DIMS if dim not in frame.columns]
    if missing or "isocode" not in frame.columns:
        raise ValueError(f"GPS file missing required columns: {missing or 'isocode'}")
    vectors: dict[str, dict[str, float]] = {}
    for _, row in frame.iterrows():
        iso = str(row["isocode"]).strip().upper()
        values = {dim: float(row[dim]) for dim in DIMS}
        if any(v != v for v in values.values()):  # NaN
            continue
        vectors[iso] = values
    if not vectors:
        raise ValueError(f"GPS file at {GPS_DTA} has no complete country vectors")
    return vectors


def load_z_source(path: Path) -> dict[str, dict[str, float]]:
    """Continuous z from a private json if it still has magnitudes, else the dta.

    A public checkout has neither the z file nor, until the researcher downloads
    it, the dta. The dta path raises FileNotFoundError with the DATA.md pointer.
    """
    path = Path(path)
    if path.is_file():
        raw = json.loads(path.read_text())
        if isinstance(raw, dict) and raw and _continuous(next(iter(raw.values()))):
            return {iso: {dim: float(vals[dim]) for dim in DIMS} for iso, vals in raw.items()}
    return load_country_z()
