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
        "You are a behavioral scientist who designs realistic decision scenarios.\n"
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
    if len(facets) != 5:
        raise ValueError(f"Facet generation for {dim_key} returned {len(facets)} facets; expected exactly 5.")
    return facets


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
            "You are a behavioral scientist who designs realistic decision scenarios.\n"
            f"Generate exactly {count} diverse scenarios for the GPS dimension '{dim_key}'.\n"
            f"Dimension description: {dim_info['desc']}\n"
            f"Target sub-dimension/facet: {facet}\n"
            "Each scenario should describe one concrete decision situation using this exact light template:\n"
            "Context: One realistic sentence establishing the agent, setting, and stakes.\n"
            "Decision: One sentence stating the two behaviorally plausible options the agent is choosing between.\n"
            "Trade-off: One sentence making the core target-facet tension explicit without naming high/low GPS scores.\n"
            "The Decision line must make clear what choice the agent is actually facing.\n"
            "The Trade-off line must make the relevant target dimension/facet easy to infer while avoiding labels like "
            "'high trust' or 'low altruism'.\n"
            "Write the scenario in first-person.\n"
            "Vary social setting and stakes while staying realistic and culturally neutral.\n"
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
            "You are a behavioral scientist who designs realistic decision scenarios.\n\n"
            "CONTEXT\n"
            f"Scenario:\n{scenario}\n\n"
            f"Target sub-dimension: {facet}\n"
            f"Target dimension: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}\n"
            f"Dimension rubric: {dim_info['rubric']}\n\n"
            "TASK\n"
            "Generate two opposing responses to this same scenario.\n"
            "- Response A should load positively on the target dimension: it should express a higher level of the target trait/facet.\n"
            "- Response B should load negatively on the target dimension: it should express a lower level or absence of the target trait/facet.\n"
            "- Positive loading does not mean morally better, more polite, or more socially desirable.\n"
            "- Negative loading does not mean irrational, careless, hostile, or cartoonishly selfish.\n\n"
            "CONTROL REQUIREMENTS\n"
            "- Vary only the target dimension/facet between Response A and Response B.\n"
            "- Keep the other five GPS traits as constant as possible: trust, risk-taking, patience, altruism, positive reciprocity, and negative reciprocity, excluding the target.\n"
            "- Match the two responses on perspective, tone, emotional intensity, specificity, length, social distance, stakes, and behavioral realism.\n"
            "- Do not let both responses drift toward the high-loading option just because it sounds prudent, prosocial, or cooperative.\n"
            "- Do not introduce extra cues about non-target traits unless the same cue appears in both responses.\n\n"
            "STYLE REQUIREMENTS\n"
            "- Write both responses in first person, present tense.\n"
            "- Use 2 to 3 sentences per response and aim for similar word counts.\n"
            "- Start each response with the concrete decision, then give the reasoning behind that decision.\n"
            "- Do not mention GPS dimensions, profile scores, countries, or national identity labels in either response.\n"
            "- Do NOT use phrases like 'As a Mexican' or 'As an American'. Express dispositions through behavioral choices and reasoning patterns.\n"
            "- Do not create a strawman response; both responses must sound like plausible choices by reasonable people.\n"
            f"{anchor_block}"
            "Reasoning field: Briefly explain (1) how Response A loads positively and Response B loads negatively on the target dimension, and (2) how the two responses remain similar on the other five GPS traits.\n"
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
        z_value = float(z_c[dim_key])
        if z_value > 0:
            sign_guidance = (
                "The z-score is positive, so the profile expresses an above-average level of the target trait. "
                "Because Response A is the positive-loading option and Response B is the negative-loading option, "
                "Response A should be preferred unless the response text clearly contradicts the loading."
            )
        elif z_value < 0:
            sign_guidance = (
                "The z-score is negative, so the profile expresses a below-average level of the target trait. "
                "Because Response A is the positive-loading option and Response B is the negative-loading option, "
                "Response B should be preferred unless the response text clearly contradicts the loading."
            )
        else:
            sign_guidance = (
                "The z-score is exactly zero, so the profile is at the global average on the target trait. "
                "Use the profile description to choose the less extreme response, while remembering that "
                "Response A is positive-loading and Response B is negative-loading."
            )

        user_prompt = (
            "You are a behavioral scientist who designs realistic decision scenarios.\n\n"
            "CONTEXT\n"
            f"Scenario:\n{scenario}\n\n"
            f"Target sub-dimension: {facet}\n"
            f"Target dimension: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}\n"
            f"Observed standardized disposition on {dim_key}: {z_value:+.2f}\n"
            f"Profile description:\n{profile_text}\n\n"
            "Fixed response loadings:\n"
            "- Response A was generated to load positively on the target dimension.\n"
            "- Response B was generated to load negatively on the target dimension.\n\n"
            f"Response A: {response_a}\n\n"
            f"Response B: {response_b}\n\n"
            "TASK\n"
            "Select which fixed response is more aligned with the profile's disposition on the target dimension.\n"
            f"- Sign rule: {sign_guidance}\n"
            "- The profile description is supporting context for interpreting the target disposition, not a separate instruction to prefer socially desirable behavior.\n"
            "- Focus on the target dimension first; use the other GPS dimensions only as secondary context when the target signal is near zero or ambiguous.\n"
            "- Please pay special attention to the sign of the z-score. Magnitude affects how strong the explanation should be, but the sign determines the expected direction.\n"
            "- Do not rewrite either response.\n"
            "Reasoning field: Explain which response better matches the profile's disposition on the target dimension and why, paying special attention to the sign of the z-score.\n"
            "Return ONLY a valid JSON object, with no markdown or surrounding text: "
            "{\"chosen_option\": \"A\" or \"B\", \"reasoning\": \"...\"}"
        )

        payload = await utils.tracked_json_completion(
            "C:selection",
            tracker,
            config=config,
            model=config.generator_model,
            messages=[
                {"role": "system", "content": "You are a behavioral scientist who designs realistic decision scenarios."},
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
