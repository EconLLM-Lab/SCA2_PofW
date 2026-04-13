"""Scenario and paired response generation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pandas as pd

from .config import CONFIG, CostTracker, GPS_DIMENSIONS, PipelineConfig
from . import utils


LOGGER = logging.getLogger("sca2_datagen.generate")


def _allocate_counts(total: int, buckets: int) -> list[int]:
    base = total // buckets
    remainder = total % buckets
    return [base + (1 if index < remainder else 0) for index in range(buckets)]


async def _generate_facets(
    dim_key: str,
    dim_info: dict[str, str],
    config: PipelineConfig,
    tracker: CostTracker,
) -> list[str]:
    prompt = (
        "You are an expert experimental economist.\n"
        f"Break the cultural trait '{dim_key}' into 4 to 6 distinct sub-dimensions or facets.\n"
        f"Trait description: {dim_info['desc']}\n"
        "Return ONLY JSON in the form {\"facets\": [\"...\", \"...\"]}.\n"
        "Each facet should be short, concrete, and behaviorally distinct."
    )
    response = await utils.tracked_completion(
        "C:facets",
        tracker,
        model=config.teacher_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=config.teacher_temperature,
    )
    payload = utils.parse_json_response(response)
    facets = [str(item).strip() for item in payload.get("facets", []) if str(item).strip()]
    if len(facets) < 4:
        raise ValueError(f"Facet generation for {dim_key} returned fewer than 4 facets.")
    return facets[:6]


async def generate_scenarios(
    dim_key: str,
    dim_info: dict[str, str],
    n: int,
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
) -> list[dict[str, str]]:
    """Generate exactly n scenarios for one dimension, grouped by facet."""

    tracker = tracker or CostTracker()
    facets = await _generate_facets(dim_key, dim_info, config, tracker)
    counts = _allocate_counts(n, len(facets))
    scenarios: list[dict[str, str]] = []

    for facet, count in zip(facets, counts):
        if count <= 0:
            continue
        prompt = (
            "You are an expert experimental economist.\n"
            f"Generate exactly {count} diverse scenarios for the GPS dimension '{dim_key}'.\n"
            f"Dimension description: {dim_info['desc']}\n"
            f"Target sub-dimension/facet: {facet}\n"
            "Each scenario should be 1 to 3 sentences and describe a concrete decision situation.\n"
            "Vary social setting and stakes while staying realistic.\n"
            "Do NOT generate scenarios requiring numerical calculations, lottery-style gambles, "
            "or hypothetical pricing decisions.\n"
            "Return ONLY JSON: {\"scenarios\": [\"...\", \"...\"]}."
        )
        response = await utils.tracked_completion(
            "C:scenarios",
            tracker,
            model=config.teacher_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=config.teacher_temperature,
        )
        payload = utils.parse_json_response(response)
        for scenario in payload.get("scenarios", []):
            text = str(scenario).strip()
            if text:
                scenarios.append({"facet": facet, "prompt": text})

    return scenarios[:n]


async def generate_pair(
    scenario: str,
    facet: str,
    dim_key: str,
    dim_info: dict[str, str],
    country: str,
    profile_text: str,
    z_c: dict[str, float],
    sem: asyncio.Semaphore,
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
) -> dict[str, Any]:
    """Generate aligned and contrasting responses for a scenario."""

    tracker = tracker or CostTracker()
    async with sem:
        user_prompt = (
            f"Scenario: {scenario}\n"
            f"Target sub-dimension: {facet}\n"
            f"Target dimension: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}\n\n"
            "Generate two responses to this scenario.\n"
            f"- Response A reflects {country}'s actual disposition on {dim_key} ({z_c[dim_key]:+.2f}).\n"
            f"- Response B reflects the opposite disposition on {dim_key}.\n"
            "Both responses must be 2 to 4 sentences, behaviorally realistic, and written in English.\n"
            "Do NOT use phrases like 'As a Mexican' or 'As an American'. Express cultural "
            "dispositions through behavioral choices and reasoning patterns, not national "
            "identity labels.\n"
            "Do not create a strawman response.\n"
            "Return ONLY JSON: "
            "{\"response_a\": \"...\", \"response_b\": \"...\", \"reasoning\": \"...\"}"
        )

        response = await utils.tracked_completion(
            "C:pairs",
            tracker,
            model=config.generator_model,
            messages=[
                {"role": "system", "content": profile_text},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=config.generator_temperature,
        )
        payload = utils.parse_json_response(response)
        return {
            "response_a": payload["response_a"],
            "response_b": payload["response_b"],
            "reasoning": payload.get("reasoning", ""),
        }


async def safe_generate_pair(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Generate a pair without failing the entire batch on one error."""

    try:
        return await generate_pair(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - exercised indirectly
        return {"error": utils.compact_error_message(exc)}


async def run_teacher_pipeline(
    cultural_profiles: dict[str, dict[str, Any]],
    countries: list[str],
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
) -> tuple[pd.DataFrame, dict[str, list[dict[str, str]]]]:
    """Run scenario generation and paired response generation."""

    tracker = tracker or CostTracker()
    sem = asyncio.Semaphore(config.concurrency)
    all_rows: list[dict[str, Any]] = []
    scenario_bank: dict[str, list[dict[str, str]]] = {}

    LOGGER.info("Stage 1/3: generating facets and scenarios for %d GPS dimensions", len(GPS_DIMENSIONS))
    for dim_key, dim_info in GPS_DIMENSIONS.items():
        LOGGER.info("Generating facet/scenario bank for dimension=%s", dim_key)
        scenario_bank[dim_key] = await generate_scenarios(
            dim_key,
            dim_info,
            config.scenarios_per_dim,
            config=config,
            tracker=tracker,
        )
        LOGGER.info(
            "Scenario bank ready for %s: %d scenarios",
            dim_key,
            len(scenario_bank[dim_key]),
        )

    LOGGER.info("Stage 2/3: generating paired responses for countries=%s", countries)
    for country in countries:
        profile = cultural_profiles[country]
        coroutines: list[Any] = []
        task_meta: list[tuple[str, str, str]] = []
        for dim_key, scenario_rows in scenario_bank.items():
            for scenario_row in scenario_rows:
                coroutines.append(
                    safe_generate_pair(
                        scenario_row["prompt"],
                        scenario_row["facet"],
                        dim_key,
                        GPS_DIMENSIONS[dim_key],
                        country,
                        profile["profile_text"],
                        profile["z_c"],
                        sem,
                        config=config,
                        tracker=tracker,
                    )
                )
                task_meta.append((dim_key, scenario_row["facet"], scenario_row["prompt"]))

        LOGGER.info("Generating %d paired responses for country=%s", len(coroutines), country)
        results = await utils.gather_with_progress(
            coroutines,
            description=f"Generate {country}",
            logger=LOGGER,
            batch_size=10,
        )
        failed_messages: list[str] = []
        for (dim_key, facet, prompt), result in zip(task_meta, results):
            if "response_a" not in result:
                failed_messages.append(result.get("error", "unknown_generation_error"))
                continue
            all_rows.append(
                {
                    "prompt": prompt,
                    "facet": facet,
                    "gps_dimension": dim_key,
                    "country": country,
                    "chosen": result["response_a"],
                    "rejected": result["response_b"],
                    "reasoning": result.get("reasoning", ""),
                }
            )
        success_count = sum(1 for result in results if "response_a" in result)
        LOGGER.info(
            "Finished country=%s with %d/%d successful pairs",
            country,
            success_count,
            len(results),
        )
        if failed_messages:
            error_summary = utils.summarize_error_messages(failed_messages, top_n=3)
            LOGGER.warning(
                "Country=%s had %d failed generations. Top errors: %s",
                country,
                len(failed_messages),
                "; ".join(error_summary),
            )

    return pd.DataFrame(all_rows), scenario_bank
