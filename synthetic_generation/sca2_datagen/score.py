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
            "Return ONLY JSON: "
            "{\"scores_a\": {\"trust\": <float>, \"risktaking\": <float>, \"patience\": <float>, "
            "\"altruism\": <float>, \"posrecip\": <float>, \"negrecip\": <float>}, "
            "\"scores_b\": {\"trust\": <float>, \"risktaking\": <float>, \"patience\": <float>, "
            "\"altruism\": <float>, \"posrecip\": <float>, \"negrecip\": <float>}, "
            "\"reasoning\": \"<brief justification>\"}"
        )

        response = await utils.tracked_completion(
            "D:scoring",
            tracker,
            model=config.scorer_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=config.scorer_temperature,
        )
        payload = utils.parse_json_response(response)

    try:
        scores_a = {key: _clip_score(payload["scores_a"][key]) for key in GPS_DIMENSIONS}
        scores_b = {key: _clip_score(payload["scores_b"][key]) for key in GPS_DIMENSIONS}
    except (KeyError, TypeError, ValueError):
        return None, None, ""
    return scores_a, scores_b, str(payload.get("reasoning", ""))


def _clip_score(value: Any) -> float:
    return max(0.0, min(1.0, float(value)))


async def run_scoring_qc_export(
    df_raw: pd.DataFrame,
    cultural_profiles: dict[str, dict[str, Any]],
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Score all rows and apply QC filters."""

    tracker = tracker or CostTracker()
    sem = asyncio.Semaphore(config.concurrency)
    df = df_raw.copy()
    df["chosen_text"] = df["chosen"].apply(unwrap)
    df["rejected_text"] = df["rejected"].apply(unwrap)

    tasks = [
        score_pair(
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

    stats = {"total": len(df), "score_fail": 0, "mono_fail": 0, "dist_fail": 0, "pass": 0}
    rows: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        scores_a = row["scores_a"]
        scores_b = row["scores_b"]
        if scores_a is None or scores_b is None:
            stats["score_fail"] += 1
            continue

        dim = row["gps_dimension"]
        chosen_target = scores_a.get(dim)
        rejected_target = scores_b.get(dim)
        if chosen_target is None or rejected_target is None:
            stats["score_fail"] += 1
            continue

        z_value = float(cultural_profiles[row["country"]]["z_c"][dim])
        z_sign = np.sign(z_value) if z_value != 0 else 1.0
        signed_diff = chosen_target - rejected_target
        mono_pass = (signed_diff * z_sign) > 0
        dist_pass = abs(signed_diff) >= config.qc_distance_thresh

        if not mono_pass:
            stats["mono_fail"] += 1
            continue
        if not dist_pass:
            stats["dist_fail"] += 1
            continue

        target_diff = abs(signed_diff)
        cross_diffs = sum(abs(scores_a[key] - scores_b[key]) for key in GPS_DIMENSIONS if key != dim)
        contamination = round(cross_diffs / target_diff, 4) if target_diff > 0 else None

        output_row = {
            "prompt": row["prompt"],
            "facet": row.get("facet", ""),
            "chosen": row["chosen_text"],
            "rejected": row["rejected_text"],
            "gps_dimension": dim,
            "country": row["country"],
            "generation_reasoning": row.get("reasoning", ""),
            "reasoning": row["score_reasoning"],
            "m_chosen": round(chosen_target, 4),
            "m_rejected": round(rejected_target, 4),
            "m_diff_signed": round(signed_diff, 4),
            "m_diff_abs": round(abs(signed_diff), 4),
            "z_value": round(z_value, 4),
            "contamination_ratio": contamination,
        }
        for key in GPS_DIMENSIONS:
            output_row[f"m_chosen_{key}"] = round(scores_a[key], 4)
            output_row[f"m_rejected_{key}"] = round(scores_b[key], 4)

        rows.append(output_row)
        stats["pass"] += 1

    return pd.DataFrame(rows), stats
