"""Scoring and quality control for generated pairs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np
import pandas as pd

from . import utils
from .config import CONFIG, CostTracker, GPS_DIMENSIONS, PipelineConfig


LOGGER = logging.getLogger("sca2_datagen.score")


def unwrap(response_obj: Any) -> str:
    """Flatten nested response objects into plain text."""

    if isinstance(response_obj, dict):
        return str(response_obj.get("response", response_obj.get("narrative", response_obj)))
    return str(response_obj)


async def score_pair(
    scenario: str,
    chosen_text: str,
    rejected_text: str,
    dim_key: str,
    dim_info: dict[str, str],
    sem: asyncio.Semaphore,
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
) -> tuple[dict[str, float] | None, dict[str, float] | None, str]:
    """Score both responses across all six GPS dimensions in one call."""

    tracker = tracker or CostTracker()
    rubric_block = "\n".join(
        f"- {GPS_DIMENSIONS[key]['symbol']} ({key}): {GPS_DIMENSIONS[key]['rubric']}"
        for key in GPS_DIMENSIONS
    )

    async with sem:
        prompt = (
            "You are a cultural behavioral scientist scoring responses on six dimensions.\n\n"
            "DIMENSIONS AND RUBRICS:\n"
            f"{rubric_block}\n\n"
            f"SCENARIO: {scenario}\n\n"
            f"TARGET DIMENSION: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}\n\n"
            f"RESPONSE A: {chosen_text}\n\n"
            f"RESPONSE B: {rejected_text}\n\n"
            "Score each response on all 6 dimensions from 0.0 to 1.0.\n"
            "Return ONLY a valid JSON object, with no markdown or surrounding text: "
            "{\"scores_a\": {\"trust\": <float>, \"risktaking\": <float>, \"patience\": <float>, "
            "\"altruism\": <float>, \"posrecip\": <float>, \"negrecip\": <float>}, "
            "\"scores_b\": {\"trust\": <float>, \"risktaking\": <float>, \"patience\": <float>, "
            "\"altruism\": <float>, \"posrecip\": <float>, \"negrecip\": <float>}, "
            "\"reasoning\": \"<brief justification>\"}"
        )

        payload = await utils.tracked_json_completion(
            "D:scoring",
            tracker,
            config=config,
            model=config.scorer_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=config.scorer_temperature,
        )

    try:
        scores_a = {key: _clip_score(payload["scores_a"][key]) for key in GPS_DIMENSIONS}
        scores_b = {key: _clip_score(payload["scores_b"][key]) for key in GPS_DIMENSIONS}
    except (KeyError, TypeError, ValueError):
        return None, None, ""
    return scores_a, scores_b, str(payload.get("reasoning", ""))


async def safe_score_pair(
    *args: Any, **kwargs: Any
) -> tuple[dict[str, float] | None, dict[str, float] | None, str, str | None]:
    """Score a pair and return an error message instead of raising."""

    try:
        scores_a, scores_b, reasoning = await score_pair(*args, **kwargs)
        return scores_a, scores_b, reasoning, None
    except Exception as exc:  # pragma: no cover - exercised indirectly
        return None, None, "", utils.compact_error_message(exc)


def _clip_score(value: Any) -> float:
    return max(0.0, min(1.0, float(value)))


async def run_scoring_qc_export(
    df_raw: pd.DataFrame,
    cultural_profiles: dict[str, dict[str, Any]],
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Score all rows and apply QC filters.

    The monotonicity check applies a small negative tolerance
    (qc_mono_epsilon) for scorer-noise robustness near zero.
    """

    tracker = tracker or CostTracker()
    sem = asyncio.Semaphore(config.concurrency)
    df = df_raw.copy()
    df["chosen_text"] = df["chosen"].apply(unwrap)
    df["rejected_text"] = df["rejected"].apply(unwrap)

    tasks = [
        safe_score_pair(
            row["prompt"],
            row["chosen_text"],
            row["rejected_text"],
            row["gps_dimension"],
            GPS_DIMENSIONS[row["gps_dimension"]],
            sem,
            config=config,
            tracker=tracker,
        )
        for _, row in df.iterrows()
    ]
    LOGGER.info(
        "Stage 3/3: scoring %d raw pairs across countries=%s",
        len(df),
        sorted(df["country"].unique().tolist()) if not df.empty else [],
    )
    results = await utils.gather_with_progress(
        tasks,
        description="Score pairs",
        logger=LOGGER,
        batch_size=10,
    )

    df["scores_a"] = [result[0] for result in results]
    df["scores_b"] = [result[1] for result in results]
    df["score_reasoning"] = [result[2] for result in results]
    score_errors = [result[3] for result in results if result[3]]
    if score_errors:
        error_summary = utils.summarize_error_messages(score_errors, top_n=3)
        LOGGER.warning(
            "Scoring had %d failed calls. Top errors: %s",
            len(score_errors),
            "; ".join(error_summary),
        )

    stats: dict[str, Any] = {
        "total": len(df),
        "score_fail": 0,
        "mono_fail": 0,
        "dist_fail": 0,
        "pass": 0,
        "per_dimension": {
            dim: {"total": 0, "score_fail": 0, "mono_fail": 0, "dist_fail": 0, "pass": 0}
            for dim in GPS_DIMENSIONS
        },
    }
    contamination_counts = {"low": 0, "medium": 0, "high": 0}
    rows: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        dim = row["gps_dimension"]
        dim_stats = stats["per_dimension"].setdefault(
            dim, {"total": 0, "score_fail": 0, "mono_fail": 0, "dist_fail": 0, "pass": 0}
        )
        dim_stats["total"] += 1
        scores_a = row["scores_a"]
        scores_b = row["scores_b"]
        if not isinstance(scores_a, dict) or not isinstance(scores_b, dict):
            stats["score_fail"] += 1
            dim_stats["score_fail"] += 1
            continue

        chosen_target = scores_a.get(dim)
        rejected_target = scores_b.get(dim)
        if chosen_target is None or rejected_target is None:
            stats["score_fail"] += 1
            dim_stats["score_fail"] += 1
            continue

        z_value = float(cultural_profiles[row["country"]]["z_c"][dim])
        z_sign = np.sign(z_value) if z_value != 0 else 1.0
        signed_diff = chosen_target - rejected_target
        mono_pass = (signed_diff * z_sign) > -config.qc_mono_epsilon
        dist_pass = abs(signed_diff) >= config.qc_distance_thresh

        if not mono_pass:
            stats["mono_fail"] += 1
            dim_stats["mono_fail"] += 1
            continue
        if not dist_pass:
            stats["dist_fail"] += 1
            dim_stats["dist_fail"] += 1
            continue

        target_diff = abs(signed_diff)
        cross_diffs = sum(abs(scores_a[key] - scores_b[key]) for key in GPS_DIMENSIONS if key != dim)
        contamination = round(cross_diffs / target_diff, 4) if target_diff > 0 else None
        if contamination is None:
            contamination_category = None
        elif contamination < 0.3:
            contamination_category = "low"
        elif contamination < 0.7:
            contamination_category = "medium"
        else:
            contamination_category = "high"
        if contamination_category is not None:
            contamination_counts[contamination_category] += 1

        output_row = {
            "prompt": row["prompt"],
            "facet": row.get("facet", ""),
            "chosen": row["chosen_text"],
            "rejected": row["rejected_text"],
            "gps_dimension": dim,
            "country": row["country"],
            "generation_reasoning": row.get("generation_reasoning", row.get("reasoning", "")),
            "selection_reasoning": row.get("reasoning", ""),
            "chosen_option": row.get("chosen_option", ""),
            "reasoning": row["score_reasoning"],
            "m_chosen": round(chosen_target, 4),
            "m_rejected": round(rejected_target, 4),
            "m_diff_signed": round(signed_diff, 4),
            "m_diff_abs": round(abs(signed_diff), 4),
            "z_value": round(z_value, 4),
            "contamination_ratio": contamination,
            "contamination_category": contamination_category,
        }
        for key in GPS_DIMENSIONS:
            output_row[f"m_chosen_{key}"] = round(scores_a[key], 4)
            output_row[f"m_rejected_{key}"] = round(scores_b[key], 4)

        rows.append(output_row)
        stats["pass"] += 1
        dim_stats["pass"] += 1

    passed_with_contamination = sum(contamination_counts.values())
    if passed_with_contamination:
        LOGGER.info(
            "Contamination distribution among passed rows: %s",
            {
                key: {
                    "count": count,
                    "share": round(count / passed_with_contamination, 4),
                }
                for key, count in contamination_counts.items()
            },
        )
    else:
        LOGGER.info("Contamination distribution among passed rows: no scored contamination values")

    return pd.DataFrame(rows), stats
