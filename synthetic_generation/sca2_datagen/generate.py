"""Scenario and fixed-option response generation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pandas as pd

from .anchors import format_anchor_block, load_anchors
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
        f"Break the cultural trait '{dim_key}' into exactly 5 distinct sub-dimensions (facets).\n"
        f"Trait description: {dim_info['desc']}\n"
        "Return ONLY a valid JSON object, with no markdown or surrounding text, "
        "in the form {\"facets\": [\"...\", \"...\"]}.\n"
        "Each facet should be short, concrete, and behaviorally distinct."
    )
    payload = await utils.tracked_json_completion(
        "C:facets",
        tracker,
        config=config,
        model=config.teacher_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=config.teacher_temperature,
    )
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
    use_anchors: bool = False,
) -> list[dict[str, str]]:
    """Generate exactly n scenarios for one dimension, grouped by facet."""

    tracker = tracker or CostTracker()
    facets = await _generate_facets(dim_key, dim_info, config, tracker)
    counts = _allocate_counts(n, len(facets))
    scenarios: list[dict[str, str]] = []
    anchor_block = ""
    if use_anchors:
        anchors = load_anchors(dim_key)[:3]
        if anchors:
            anchor_block = f"\n\n{format_anchor_block(dim_key, anchors)}\n\n" 

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
            f"{anchor_block}"
            "Return ONLY a valid JSON object, with no markdown or surrounding text: "
            "{\"scenarios\": [\"...\", \"...\"]}."
        )
        payload = await utils.tracked_json_completion(
            "C:scenarios",
            tracker,
            config=config,
            model=config.teacher_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=config.teacher_temperature,
        )
        for scenario in payload.get("scenarios", []):
            text = str(scenario).strip()
            if text:
                scenarios.append({"facet": facet, "prompt": text})

    return scenarios[:n]


async def generate_triplet(
    scenario: str,
    facet: str,
    dim_key: str,
    dim_info: dict[str, str],
    sem: asyncio.Semaphore,
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
    use_anchors: bool = False,
) -> dict[str, Any]:
    """Generate a country-independent scenario and two opposing response options."""

    tracker = tracker or CostTracker()
    async with sem:
        anchor_block = ""
        if use_anchors:
            anchors = load_anchors(dim_key)[:3]
            if anchors:
                anchor_block = f"\n\n{format_anchor_block(dim_key, anchors)}\n\n"

        user_prompt = (
            f"Scenario: {scenario}\n"
            f"Target sub-dimension: {facet}\n"
            f"Target dimension: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}\n"
            f"Dimension rubric: {dim_info['rubric']}\n\n"
            "Generate two opposing responses to this same scenario.\n"
            "- Response A should reflect the high/positive end of the target dimension.\n"
            "- Response B should reflect the low/opposite end of the target dimension.\n"
            "Vary only the target dimension/facet between Response A and Response B; keep the other five GPS traits (trust, risk-taking, patience, altruism, positive reciprocity, and negative reciprocity, excluding the target) as constant as possible.\n"
            "The two responses should be nearly identical in tone, length, and behavioral realism except for the specific choices and reasoning that reflect the target dimension.\n"
            "Both responses must be 2 to 4 sentences, behaviorally realistic, and written in English.\n"
            "Do NOT use phrases like 'As a Mexican' or 'As an American'. Express dispositions "
            "through behavioral choices and reasoning patterns, not national identity labels.\n"
            "Do not create a strawman response.\n"
            f"{anchor_block}"
            "Return ONLY a valid JSON object, with no markdown or surrounding text: "
            "{\"response_a\": \"...\", \"response_b\": \"...\", \"reasoning\": \"...\"}"
        )

        payload = await utils.tracked_json_completion(
            "C:triplets",
            tracker,
            config=config,
            model=config.generator_model,
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
            temperature=config.generator_temperature,
        )
        return {
            "response_a": payload["response_a"],
            "response_b": payload["response_b"],
            "reasoning": payload.get("reasoning", ""),
        }


async def safe_generate_triplet(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Generate a fixed triplet without failing the entire batch on one error."""

    try:
        return await generate_triplet(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - exercised indirectly
        return {"error": utils.compact_error_message(exc)}


async def select_triplet_for_profile(
    scenario: str,
    facet: str,
    dim_key: str,
    dim_info: dict[str, str],
    response_a: str,
    response_b: str,
    country: str,
    profile_text: str,
    z_c: dict[str, float],
    sem: asyncio.Semaphore,
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
) -> dict[str, Any]:
    """Select which fixed response better matches one country's GPS disposition."""

    tracker = tracker or CostTracker()
    async with sem:
        user_prompt = (
            f"Scenario: {scenario}\n"
            f"Target sub-dimension: {facet}\n"
            f"Target dimension: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}\n"
            f"Country/profile code: {country}\n"
            f"Observed standardized disposition on {dim_key}: {z_c[dim_key]:+.2f}\n\n"
            f"Profile description:\n{profile_text}\n\n"
            f"Response A: {response_a}\n\n"
            f"Response B: {response_b}\n\n"
            "Select which fixed response is more aligned with the profile's disposition on the "
            f"target dimension. The profile has a {z_c[dim_key]:+.2f} standardized score. "
            "Choose the response that better matches this specific tendency (pay special attention to the sign).\n"
            "Do not rewrite either response.\n"
            "Return ONLY a valid JSON object, with no markdown or surrounding text: "
            "{\"chosen_option\": \"A\" or \"B\", \"reasoning\": \"...\"}"
        )

        payload = await utils.tracked_json_completion(
            "C:selection",
            tracker,
            config=config,
            model=config.scorer_model,
            messages=[
                {"role": "system", "content": profile_text},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=config.scorer_temperature,
        )
        chosen_option = str(payload.get("chosen_option", "")).strip().upper()
        if chosen_option not in {"A", "B"}:
            raise ValueError(f"Selection returned invalid chosen_option={chosen_option!r}")
        chosen = response_a if chosen_option == "A" else response_b
        rejected = response_b if chosen_option == "A" else response_a
        return {
            "chosen_option": chosen_option,
            "chosen": chosen,
            "rejected": rejected,
            "reasoning": payload.get("reasoning", ""),
        }


async def safe_select_triplet_for_profile(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Select a triplet response without failing the entire batch on one error."""

    try:
        return await select_triplet_for_profile(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - exercised indirectly
        return {"error": utils.compact_error_message(exc)}


async def run_teacher_pipeline(
    cultural_profiles: dict[str, dict[str, Any]],
    countries: list[str],
    config: PipelineConfig = CONFIG,
    tracker: CostTracker | None = None,
    use_anchors: bool = False,
) -> tuple[pd.DataFrame, dict[str, list[dict[str, str]]]]:
    """Run scenario generation, fixed triplet generation, and per-country selection."""

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
            use_anchors=use_anchors,
        )
        LOGGER.info(
            "Scenario bank ready for %s: %d scenarios",
            dim_key,
            len(scenario_bank[dim_key]),
        )

    LOGGER.info("Stage 2/3: generating fixed triplets once per scenario")
    task_specs: list[tuple[str, str, str]] = []
    for dim_key, scenario_rows in scenario_bank.items():
        for scenario_row in scenario_rows:
            task_specs.append((dim_key, scenario_row["facet"], scenario_row["prompt"]))

    window = max(1, config.error_rate_window)
    triplets: list[dict[str, Any]] = []
    failures_in_window: list[bool] = []
    for offset in range(0, len(task_specs), window):
        chunk_specs = task_specs[offset : offset + window]
        chunk_coroutines = [
            safe_generate_triplet(
                prompt,
                facet,
                dim_key,
                GPS_DIMENSIONS[dim_key],
                sem,
                config=config,
                tracker=tracker,
                use_anchors=use_anchors,
            )
            for dim_key, facet, prompt in chunk_specs
        ]
        chunk_results = await utils.gather_with_progress(
            chunk_coroutines,
            description="Generate fixed triplets",
            logger=LOGGER,
            batch_size=10,
        )
        triplets.extend(chunk_results)
        failures_in_window.extend("response_a" not in result for result in chunk_results)
        failures_in_window = failures_in_window[-window:]

        if len(failures_in_window) == window:
            fail_rate = sum(failures_in_window) / window
            if fail_rate > config.max_error_rate_for_continue:
                raise RuntimeError(
                    "Early stop triggered: sustained triplet generation failure rate exceeded threshold "
                    f"fail_rate={fail_rate:.2%} window={window} "
                    f"threshold={config.max_error_rate_for_continue:.2%}"
                )

    fixed_triplets: list[dict[str, Any]] = []
    failed_messages: list[str] = []
    for (dim_key, facet, prompt), triplet in zip(task_specs, triplets):
        if "response_a" not in triplet:
            failed_messages.append(triplet.get("error", "unknown_generation_error"))
            continue
        fixed_triplets.append(
            {
                "prompt": prompt,
                "facet": facet,
                "gps_dimension": dim_key,
                "response_a": triplet["response_a"],
                "response_b": triplet["response_b"],
                "generation_reasoning": triplet.get("reasoning", ""),
            }
        )

    LOGGER.info(
        "Fixed triplets ready: %d/%d successful",
        len(fixed_triplets),
        len(task_specs),
    )
    if failed_messages:
        error_summary = utils.summarize_error_messages(failed_messages, top_n=3)
        LOGGER.warning(
            "Triplet generation had %d failed calls. Top errors: %s",
            len(failed_messages),
            "; ".join(error_summary),
        )

    LOGGER.info("Stage 2b/3: selecting fixed responses for countries=%s", countries)
    for country in countries:
        profile = cultural_profiles[country]
        LOGGER.info("Selecting among %d fixed triplets for country=%s", len(fixed_triplets), country)
        selection_results = await utils.gather_with_progress(
            [
                safe_select_triplet_for_profile(
                    triplet["prompt"],
                    triplet["facet"],
                    triplet["gps_dimension"],
                    GPS_DIMENSIONS[triplet["gps_dimension"]],
                    triplet["response_a"],
                    triplet["response_b"],
                    country,
                    profile["profile_text"],
                    profile["z_c"],
                    sem,
                    config=config,
                    tracker=tracker,
                )
                for triplet in fixed_triplets
            ],
            description=f"Select {country}",
            logger=LOGGER,
            batch_size=10,
        )

        failed_selection_messages: list[str] = []
        for triplet, selection in zip(fixed_triplets, selection_results):
            if "chosen" not in selection:
                failed_selection_messages.append(selection.get("error", "unknown_selection_error"))
                continue
            all_rows.append(
                {
                    "prompt": triplet["prompt"],
                    "facet": triplet["facet"],
                    "gps_dimension": triplet["gps_dimension"],
                    "country": country,
                    "response_a": triplet["response_a"],
                    "response_b": triplet["response_b"],
                    "chosen_option": selection["chosen_option"],
                    "chosen": selection["chosen"],
                    "rejected": selection["rejected"],
                    "reasoning": selection.get("reasoning", ""),
                    "generation_reasoning": triplet.get("generation_reasoning", ""),
                }
            )
        success_count = sum(1 for result in selection_results if "chosen" in result)
        LOGGER.info(
            "Finished country=%s with %d/%d successful selections",
            country,
            success_count,
            len(selection_results),
        )
        if failed_selection_messages:
            error_summary = utils.summarize_error_messages(failed_selection_messages, top_n=3)
            LOGGER.warning(
                "Country=%s had %d failed selections. Top errors: %s",
                country,
                len(failed_selection_messages),
                "; ".join(error_summary),
            )

    return pd.DataFrame(all_rows), scenario_bank
