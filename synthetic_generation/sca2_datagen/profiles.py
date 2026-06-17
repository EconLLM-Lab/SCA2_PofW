"""Data ingestion and profile construction for country cultural prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import CONFIG, GPS_DIMENSIONS, WVS_ITEM_MAP, resolve_existing_path


def load_gps_data(gps_path: str | Path | None = None) -> pd.DataFrame:
    """Load required GPS country-level data."""

    path = Path(gps_path) if gps_path else resolve_existing_path(CONFIG.gps_path_candidates)
    if path is None:
        raise FileNotFoundError(
            "GPS dataset not found. Provide --gps-path or place country_gps.dta in a configured path."
        )
    return pd.read_stata(path, convert_categoricals=False)


def load_wvs_data(wvs_path: str | Path | None = None) -> pd.DataFrame | None:
    """Load optional WVS data if available."""

    path = Path(wvs_path) if wvs_path else resolve_existing_path(CONFIG.wvs_path_candidates)
    if path is None or not path.exists():
        return None
    return pd.read_stata(path, convert_categoricals=False)


def extract_gps_vector(df_gps: pd.DataFrame, country_iso3: str) -> dict[str, float]:
    """Extract the six-dimensional GPS vector for a country."""

    row = df_gps[df_gps["isocode"] == country_iso3]
    if row.empty:
        raise ValueError(f"Country {country_iso3} not found in GPS data.")
    series = row.iloc[0]
    return {dim: float(series.get(info["col"], 0.0)) for dim, info in GPS_DIMENSIONS.items()}


def build_cultural_profile(z_c: dict[str, float]) -> str:
    """Return an anonymized quantitative cultural profile (no country name)."""

    def magnitude(value: float) -> str:
        absolute = abs(value)
        if absolute < 0.10:
            return "near the global average"
        if absolute < 0.40:
            return f"moderately {'above' if value > 0 else 'below'} average"
        return f"strongly {'above' if value > 0 else 'below'} average"

    dim_lines = []
    for dim_key, info in GPS_DIMENSIONS.items():
        value = z_c[dim_key]
        dim_lines.append(
            f"- {info['symbol']} ({dim_key}) = {value:+.2f}: {magnitude(value)}. {info['desc']}"
        )

    return (
        "GPS CULTURAL STATE VECTOR (Falk et al. 2018, standardized deviations from global mean):\n"
        f"{chr(10).join(dim_lines)}"
    )


def extract_wvs_anchors(df_wvs: pd.DataFrame | None, country_iso3: str) -> dict[str, Any]:
    """Extract optional WVS item means for behavioral anchors."""

    if df_wvs is None:
        return {}

    subset = df_wvs[df_wvs["B_COUNTRY_ALPHA"] == country_iso3]
    if subset.empty:
        return {}

    anchors: dict[str, Any] = {}
    for qcode, info in WVS_ITEM_MAP.items():
        if qcode not in subset.columns:
            continue
        valid = subset[qcode][(subset[qcode].notna()) & (subset[qcode] >= 0)]
        if valid.empty:
            continue
        anchors[qcode] = {"mean": round(float(valid.mean()), 3), **info}
    return anchors


def load_cultural_profiles(
    countries: list[str],
    gps_path: str | Path | None = None,
    wvs_path: str | Path | None = None,
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame]:
    """Load country vectors and natural-language cultural profiles."""

    df_gps = load_gps_data(gps_path)
    df_wvs = load_wvs_data(wvs_path)

    profiles: dict[str, dict[str, Any]] = {}
    for country in countries:
        z_c = extract_gps_vector(df_gps, country)
        profiles[country] = {
            "z_c": z_c,
            "profile_text": build_cultural_profile(z_c),
            "wvs_anchors": extract_wvs_anchors(df_wvs, country),
        }
    return profiles, df_gps


def rank_most_distant_countries(
    df_gps: pd.DataFrame,
    min_delta: float = 0.3,
    min_dims: int = 4,
) -> pd.DataFrame:
    """Rank country pairs by Euclidean distance in GPS space."""

    dims = [GPS_DIMENSIONS[key]["col"] for key in GPS_DIMENSIONS]
    df_clean = df_gps.dropna(subset=dims).copy()
    countries = df_clean["isocode"].tolist()

    rows: list[dict[str, Any]] = []
    for i, country_1 in enumerate(countries):
        z1 = df_clean.loc[df_clean["isocode"] == country_1, dims].iloc[0].to_numpy(dtype=float)
        for country_2 in countries[i + 1 :]:
            z2 = df_clean.loc[df_clean["isocode"] == country_2, dims].iloc[0].to_numpy(dtype=float)
            diffs = np.abs(z1 - z2)
            rows.append(
                {
                    "country_1": country_1,
                    "country_2": country_2,
                    "distance": round(float(np.linalg.norm(z1 - z2)), 4),
                    "strong_dims": int((diffs > min_delta).sum()),
                    "passes_strong_filter": bool((diffs > min_delta).sum() >= min_dims),
                }
            )
    return pd.DataFrame(rows).sort_values("distance", ascending=False).reset_index(drop=True)
