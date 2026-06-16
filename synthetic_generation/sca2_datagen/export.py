"""Export helpers for JSONL, Hugging Face datasets, and manifests."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset

from .config import GPS_DIMENSIONS, PipelineConfig, WVS_ITEM_MAP
from .utils import get_git_hash


LOGGER = logging.getLogger("sca2_datagen.export")


FRONT_JSONL_COLUMNS = [
    "prompt",
    "chosen",
    "rejected",
    "country",
    "gps_dimension",
    "z_value",
    "contamination_category",
    "contamination_ratio",
    "qc_status",
    "failure_reason",
    "mono_pass",
    "dist_pass",
    "run_id",
    "export_timestamp",
    "gps_profile_vector",
]


def prepare_ranked_subsets(df_final: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Create deterministic per-country row ranks for nested sample-size exports."""

    ranked_frames: list[pd.DataFrame] = []
    for country, group in df_final.groupby("country", sort=True):
        ordered = group.sample(frac=1.0, random_state=seed).reset_index(drop=True).copy()
        ordered["_sample_rank"] = range(1, len(ordered) + 1)
        ordered["_country_key"] = country
        ranked_frames.append(ordered)
    return pd.concat(ranked_frames, ignore_index=True) if ranked_frames else df_final.copy()


def validate_sample_sizes(
    df_final: pd.DataFrame,
    sample_sizes: list[int],
    sample_size_policy: str,
) -> tuple[list[int], list[dict[str, Any]]]:
    """Resolve sample sizes according to policy and return (effective_sizes, skipped)."""

    counts = df_final["country"].value_counts().to_dict()
    errors = [f"{country}: {count} available" for country, count in sorted(counts.items())]
    min_available = min(counts.values()) if counts else 0
    resolved: list[int] = []
    skipped: list[dict[str, Any]] = []

    for sample_size in sample_sizes:
        missing = [country for country, count in counts.items() if count < sample_size]
        if not missing:
            resolved.append(sample_size)
            continue

        if sample_size_policy == "fail_fast":
            raise ValueError(
                f"Requested sample size {sample_size} exceeds available QC-passed rows. "
                f"Available counts: {', '.join(errors)}"
            )

        if sample_size_policy == "skip_unavailable":
            skipped.append(
                {
                    "requested": sample_size,
                    "applied": None,
                    "reason": f"insufficient rows for countries: {', '.join(sorted(missing))}",
                }
            )
            continue

        if sample_size_policy == "degrade_to_feasible":
            if min_available <= 0:
                skipped.append(
                    {
                        "requested": sample_size,
                        "applied": None,
                        "reason": "no QC-passed rows available",
                    }
                )
                continue
            if min_available not in resolved:
                resolved.append(min_available)
            skipped.append(
                {
                    "requested": sample_size,
                    "applied": min_available,
                    "reason": "degraded to max feasible per-country size",
                }
            )
            continue

        raise ValueError(f"Unknown sample_size_policy={sample_size_policy}")

    return sorted(set(resolved)), skipped


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


def _safe_rate(numerator: float, denominator: float) -> float:
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def _contamination_category(value: Any) -> str | None:
    if pd.isna(value):
        return None
    value = float(value)
    if value < 0.3:
        return "low"
    if value < 0.7:
        return "medium"
    return "high"


def _contamination_distribution(df: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    if df.empty:
        return {key: {"count": 0, "share": 0.0} for key in ("low", "medium", "high")}
    if "contamination_category" in df.columns:
        categories = df["contamination_category"].dropna()
    else:
        categories = df["contamination_ratio"].dropna().map(_contamination_category)
    counts = categories.value_counts().to_dict()
    total = sum(int(counts.get(key, 0)) for key in ("low", "medium", "high"))
    return {
        key: {
            "count": int(counts.get(key, 0)),
            "share": _safe_rate(int(counts.get(key, 0)), total),
        }
        for key in ("low", "medium", "high")
    }


def _slugify_run_name(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    return slug or "sca2_generation"


def _build_run_id(output_root: Path, timestamp: datetime) -> str:
    return f"{_slugify_run_name(output_root.name)}_{timestamp.strftime('%Y%m%d_%H%M%SZ')}"


def _ordered_columns(df: pd.DataFrame) -> list[str]:
    front = [column for column in FRONT_JSONL_COLUMNS if column in df.columns]
    rest = [column for column in df.columns if column not in front]
    return front + rest


def _add_export_metadata(
    subset: pd.DataFrame,
    cultural_profiles: dict[str, dict[str, Any]],
    run_id: str,
    export_timestamp: str,
) -> pd.DataFrame:
    """Add reproducibility metadata without renaming or dropping existing fields."""

    enriched = subset.copy()
    if "contamination_category" not in enriched.columns and "contamination_ratio" in enriched.columns:
        enriched["contamination_category"] = enriched["contamination_ratio"].map(_contamination_category)
    enriched["run_id"] = run_id
    enriched["export_timestamp"] = export_timestamp
    enriched["gps_profile_vector"] = enriched["country"].map(
        lambda country: cultural_profiles.get(str(country), {}).get("z_c", {})
    )
    return enriched[_ordered_columns(enriched)]


def _per_country_dimension_counts(subset: pd.DataFrame) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    if subset.empty:
        return counts
    working = subset.copy()
    working["country"] = working["country"].astype(str)
    grouped = working.groupby(["country", "gps_dimension"]).size()
    for country in sorted(working["country"].dropna().unique()):
        country_counts: dict[str, int] = {}
        for dim in GPS_DIMENSIONS:
            country_counts[dim] = int(grouped.get((country, dim), 0))
        counts[country] = country_counts
    return counts


def _per_country_contamination_counts(subset: pd.DataFrame) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    if subset.empty:
        return counts
    working = subset.copy()
    working["country"] = working["country"].astype(str)
    if "contamination_category" not in working.columns and "contamination_ratio" in working.columns:
        working["contamination_category"] = working["contamination_ratio"].map(_contamination_category)
    if "contamination_category" not in working.columns:
        return {
            country: {"low": 0, "medium": 0, "high": 0}
            for country in sorted(working["country"].dropna().unique())
        }
    grouped = working.groupby(["country", "contamination_category"]).size()
    for country in sorted(working["country"].dropna().unique()):
        counts[country] = {
            category: int(grouped.get((country, category), 0))
            for category in ("low", "medium", "high")
        }
    return counts


def _per_dimension_qc_breakdown(df: pd.DataFrame, qc_stats: dict[str, Any]) -> dict[str, dict[str, float | int]]:
    per_dimension_stats = qc_stats.get("per_dimension", {})
    breakdown: dict[str, dict[str, float | int]] = {}
    for dim in GPS_DIMENSIONS:
        dim_subset = df.loc[df["gps_dimension"] == dim] if not df.empty else df
        dim_stats = per_dimension_stats.get(dim, {})
        total = int(dim_stats.get("total", 0))
        passed = int(dim_stats.get("pass", len(dim_subset)))
        contamination = dim_subset["contamination_ratio"].dropna() if "contamination_ratio" in dim_subset else pd.Series(dtype=float)
        breakdown[dim] = {
            "total": total,
            "pass": passed,
            "pass_rate": _safe_rate(passed, total) if total else (1.0 if passed else 0.0),
            "mean_contamination_ratio": (
                round(float(contamination.mean()), 4) if not contamination.empty else 0.0
            ),
        }
    return breakdown


def _qc_health_summary(
    qc_pass_rate: float,
    mono_fail_rate: float,
    dist_fail_rate: float,
    contamination_distribution: dict[str, dict[str, float | int]],
) -> str:
    low_share = float(contamination_distribution.get("low", {}).get("share", 0.0))
    high_share = float(contamination_distribution.get("high", {}).get("share", 0.0))
    if qc_pass_rate >= 0.7 and mono_fail_rate <= 0.1 and high_share <= 0.25:
        return "Good: high QC pass rate, low monotonicity failure, and limited high contamination."
    if qc_pass_rate >= 0.5 and mono_fail_rate <= 0.25 and low_share >= high_share:
        return "Usable: moderate QC pass rate with contamination concentrated outside the high bucket."
    return "Review: inspect monotonicity failures, distance failures, and high-contamination dimensions before downstream use."


def build_qc_manifest_summary(subset: pd.DataFrame, qc_stats: dict[str, Any]) -> dict[str, Any]:
    """Build manifest-ready QC observability metrics for the exported rows."""

    total = int(qc_stats.get("total", 0))
    passed = int(qc_stats.get("pass", len(subset)))
    mono_fail = int(qc_stats.get("mono_fail", 0))
    dist_fail = int(qc_stats.get("dist_fail", 0))
    contamination_distribution = _contamination_distribution(subset)
    qc_pass_rate = _safe_rate(passed, total)
    mono_fail_rate = _safe_rate(mono_fail, total)
    dist_fail_rate = _safe_rate(dist_fail, total)
    contamination_values = subset["contamination_ratio"].dropna() if "contamination_ratio" in subset else pd.Series(dtype=float)
    mean_m_diff_abs = round(float(subset["m_diff_abs"].mean()), 4) if not subset.empty else 0.0
    mean_contamination_ratio = (
        round(float(contamination_values.mean()), 4) if not contamination_values.empty else 0.0
    )
    return {
        "qc_pass_rate": qc_pass_rate,
        "mono_fail_rate": mono_fail_rate,
        "dist_fail_rate": dist_fail_rate,
        "mean_contamination_ratio": mean_contamination_ratio,
        "contamination_distribution": contamination_distribution,
        "mean_m_diff_abs": mean_m_diff_abs,
        "per_dimension_qc": _per_dimension_qc_breakdown(subset, qc_stats),
        "qc_health_summary": _qc_health_summary(
            qc_pass_rate,
            mono_fail_rate,
            dist_fail_rate,
            contamination_distribution,
        ),
    }


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
    export_time = datetime.now(timezone.utc)
    export_timestamp = export_time.isoformat()
    run_id = _build_run_id(output_root, export_time)

    ranked = prepare_ranked_subsets(df_final, config.seed)
    skipped_sizes: list[dict[str, Any]] = []
    if sample_sizes:
        sample_sizes, skipped_sizes = validate_sample_sizes(
            ranked,
            sample_sizes,
            config.sample_size_policy,
        )
    else:
        sample_sizes = [min(group_size for group_size in ranked["country"].value_counts())] if not ranked.empty else []

    exports: list[dict[str, Path]] = []
    for sample_size in sample_sizes:
        subset = ranked[ranked["_sample_rank"] <= sample_size].drop(
            columns=["_sample_rank", "_country_key"], errors="ignore"
        )
        export_subset = _add_export_metadata(
            subset,
            cultural_profiles=cultural_profiles,
            run_id=run_id,
            export_timestamp=export_timestamp,
        )
        LOGGER.info(
            "Exporting sample size %d with %d rows (%s)",
            sample_size,
            len(export_subset),
            export_subset["country"].value_counts().to_dict() if not export_subset.empty else {},
        )
        for country, group in export_subset.groupby("country", sort=True):
            jsonl_path = output_root / f"D_syn_{country}_{sample_size}.jsonl"
            group.to_json(jsonl_path, orient="records", lines=True)

        hf_path = output_root / f"D_syn_combined_hf_{sample_size}"
        Dataset.from_pandas(export_subset.reset_index(drop=True)).save_to_disk(str(hf_path))
        qc_manifest_summary = build_qc_manifest_summary(subset, qc_stats)

        manifest = {
            "run_id": run_id,
            "timestamp": export_timestamp,
            "sample_size": sample_size,
            "sample_size_policy": config.sample_size_policy,
            "skipped_sample_sizes": skipped_sizes,
            "raw_pair_count": raw_pair_count,
            "config": config.snapshot(),
            "countries": {country: cultural_profiles[country]["z_c"] for country in cultural_profiles},
            "wvs_item_map_n": len(WVS_ITEM_MAP),
            "tier_2_items": [q for q, value in WVS_ITEM_MAP.items() if value["tier"] == 2],
            "tier_3_items": [q for q, value in WVS_ITEM_MAP.items() if value["tier"] == 3],
            "qc_stats": qc_stats,
            **qc_manifest_summary,
            "per_dim_counts": subset["gps_dimension"].value_counts().to_dict(),
            "per_country_counts": subset["country"].value_counts().to_dict(),
            "per_country_dimension_counts": _per_country_dimension_counts(subset),
            "per_country_contamination_counts": _per_country_contamination_counts(subset),
            "mean_feature_distance": qc_manifest_summary["mean_m_diff_abs"],
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
