"""Export helpers for JSONL, Hugging Face datasets, and manifests."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset

from .config import GPS_DIMENSIONS, PipelineConfig, WVS_ITEM_MAP
from .utils import get_git_hash


LOGGER = logging.getLogger("sca2_datagen.export")


def prepare_ranked_subsets(df_final: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Create deterministic per-country row ranks for nested sample-size exports."""

    ranked_frames: list[pd.DataFrame] = []
    for country, group in df_final.groupby("country", sort=True):
        ordered = group.sample(frac=1.0, random_state=seed).reset_index(drop=True).copy()
        ordered["_sample_rank"] = range(1, len(ordered) + 1)
        ordered["_country_key"] = country
        ranked_frames.append(ordered)
    return pd.concat(ranked_frames, ignore_index=True) if ranked_frames else df_final.copy()


def validate_sample_sizes(df_final: pd.DataFrame, sample_sizes: list[int]) -> None:
    """Raise if any requested sample size exceeds available country counts."""

    counts = df_final["country"].value_counts().to_dict()
    errors = [f"{country}: {count} available" for country, count in sorted(counts.items())]
    for sample_size in sample_sizes:
        missing = [country for country, count in counts.items() if count < sample_size]
        if missing:
            raise ValueError(
                f"Requested sample size {sample_size} exceeds available QC-passed rows. "
                f"Available counts: {', '.join(errors)}"
            )


def summarize_qc(df_final: pd.DataFrame, qc_stats: dict[str, Any]) -> None:
    """Log a compact QC summary."""

    total = qc_stats["total"] or 0
    LOGGER.info(
        "QC summary: total=%s pass=%s mono_fail=%s dist_fail=%s score_fail=%s",
        total,
        qc_stats["pass"],
        qc_stats["mono_fail"],
        qc_stats["dist_fail"],
        qc_stats["score_fail"],
    )
    if not df_final.empty:
        LOGGER.info("Per-country counts: %s", df_final["country"].value_counts().to_dict())
        LOGGER.info("Per-dimension counts: %s", df_final["gps_dimension"].value_counts().to_dict())


def export_sample_runs(
    df_final: pd.DataFrame,
    sample_sizes: list[int],
    cultural_profiles: dict[str, dict[str, Any]],
    config: PipelineConfig,
    output_dir: str | Path,
    cost_summary: dict[str, Any],
    scenario_bank: dict[str, list[dict[str, str]]],
    qc_stats: dict[str, Any],
    raw_pair_count: int,
    git_cwd: str | Path | None = None,
) -> list[dict[str, Path]]:
    """Export nested sample-size subsets and manifests."""

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    ranked = prepare_ranked_subsets(df_final, config.seed)
    if sample_sizes:
        validate_sample_sizes(ranked, sample_sizes)
    else:
        sample_sizes = [min(group_size for group_size in ranked["country"].value_counts())] if not ranked.empty else []

    exports: list[dict[str, Path]] = []
    for sample_size in sample_sizes:
        subset = ranked[ranked["_sample_rank"] <= sample_size].drop(
            columns=["_sample_rank", "_country_key"], errors="ignore"
        )
        LOGGER.info(
            "Exporting sample size %d with %d rows (%s)",
            sample_size,
            len(subset),
            subset["country"].value_counts().to_dict() if not subset.empty else {},
        )
        for country, group in subset.groupby("country", sort=True):
            jsonl_path = output_root / f"D_syn_{country}_{sample_size}.jsonl"
            group.to_json(jsonl_path, orient="records", lines=True)

        hf_path = output_root / f"D_syn_combined_hf_{sample_size}"
        Dataset.from_pandas(subset.reset_index(drop=True)).save_to_disk(str(hf_path))

        manifest = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sample_size": sample_size,
            "raw_pair_count": raw_pair_count,
            "config": config.snapshot(),
            "countries": {country: cultural_profiles[country]["z_c"] for country in cultural_profiles},
            "wvs_item_map_n": len(WVS_ITEM_MAP),
            "tier_2_items": [q for q, value in WVS_ITEM_MAP.items() if value["tier"] == 2],
            "tier_3_items": [q for q, value in WVS_ITEM_MAP.items() if value["tier"] == 3],
            "qc_stats": qc_stats,
            "per_dim_counts": subset["gps_dimension"].value_counts().to_dict(),
            "per_country_counts": subset["country"].value_counts().to_dict(),
            "mean_feature_distance": round(float(subset["m_diff_abs"].mean()), 4) if not subset.empty else 0.0,
            "mean_contamination_ratio": (
                round(float(subset["contamination_ratio"].dropna().mean()), 4)
                if not subset["contamination_ratio"].dropna().empty
                else 0.0
            ),
            "per_dim_contamination": {
                dim: round(
                    float(subset.loc[subset["gps_dimension"] == dim, "contamination_ratio"].dropna().mean()),
                    4,
                )
                for dim in GPS_DIMENSIONS
                if not subset.loc[subset["gps_dimension"] == dim].empty
            },
            "cost_breakdown": cost_summary,
            "git_hash": get_git_hash(git_cwd),
            "scenario_bank_counts": {
                dim: len(rows) for dim, rows in scenario_bank.items()
            },
        }
        manifest_path = output_root / f"manifest_{sample_size}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        exports.append({"manifest": manifest_path, "hf": hf_path})

    return exports
