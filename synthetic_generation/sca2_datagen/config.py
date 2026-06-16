"""Configuration and constants for the SCA 2.0 data generation pipeline."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GPS_DIMENSIONS = {
    "trust": {
        "symbol": "tau",
        "col": "trust",
        "desc": (
            "Belief that others have good intentions; baseline faith in strangers "
            "without institutional enforcement."
        ),
        "rubric": (
            "Does the response assume good faith from unfamiliar others, cooperate "
            "without guarantees, or express confidence in institutional reliability?"
        ),
    },
    "risktaking": {
        "symbol": "gamma",
        "col": "risktaking",
        "desc": (
            "Willingness to take risks, evaluated via hypothetical staircase lotteries "
            "and self-assessment."
        ),
        "rubric": (
            "Does the response embrace uncertainty, frame risky options positively, "
            "or recommend entrepreneurial action over cautious avoidance?"
        ),
    },
    "patience": {
        "symbol": "delta",
        "col": "patience",
        "desc": (
            "Willingness to defer gratification, evaluated via staircase intertemporal "
            "choices."
        ),
        "rubric": (
            "Does the response favor deferred payoffs, future planning, or long-horizon "
            "reasoning over immediate gratification?"
        ),
    },
    "altruism": {
        "symbol": "alpha",
        "col": "altruism",
        "desc": (
            "Willingness to give to good causes and allocate a windfall gain to charity."
        ),
        "rubric": (
            "Does the response prioritize group welfare, share resources, or defer "
            "to community needs over personal benefit?"
        ),
    },
    "posrecip": {
        "symbol": "xi_plus",
        "col": "posrecip",
        "desc": (
            "Willingness to return a favor or thank-you gift to a stranger who helped "
            "at personal cost."
        ),
        "rubric": (
            "Does the response acknowledge or return a favor, express appreciation, "
            "or assume cooperative intentions in others?"
        ),
    },
    "negrecip": {
        "symbol": "xi_minus",
        "col": "negrecip",
        "desc": (
            "Willingness to punish unfair behavior even when costly "
            "(for example, rejecting low offers)."
        ),
        "rubric": (
            "Does the response express indignation at unfair treatment, endorse "
            "sanctions, or advocate for punishment of norm violators?"
        ),
    },
}


WVS_ITEM_MAP = {
    "Q57": {"dim": "trust", "tier": 2, "label": "Most people can be trusted (binary)"},
    "Q59": {"dim": "trust", "tier": 2, "label": "Trust: Your neighborhood (1-4 inv)"},
    "Q61": {"dim": "trust", "tier": 2, "label": "Trust: People met first time (1-4 inv)"},
    "Q62": {"dim": "trust", "tier": 2, "label": "Trust: Other religion (1-4 inv)"},
    "Q63": {"dim": "trust", "tier": 2, "label": "Trust: Other nationality (1-4 inv)"},
    "Q64": {"dim": "trust", "tier": 2, "label": "Confidence: Churches (1-4 inv)"},
    "Q69": {"dim": "trust", "tier": 2, "label": "Confidence: Police (1-4 inv)"},
    "Q70": {"dim": "trust", "tier": 2, "label": "Confidence: Courts (1-4 inv)"},
    "Q71": {"dim": "trust", "tier": 2, "label": "Confidence: Government (1-4 inv)"},
    "Q58": {"dim": "trust", "tier": 3, "label": "Trust: Family (1-4 inv, in-group)"},
    "Q60": {"dim": "trust", "tier": 3, "label": "Trust: Personal acquaintances (1-4 inv)"},
    "Q73": {"dim": "trust", "tier": 3, "label": "Confidence: Parliament (1-4 inv)"},
    "Q13": {"dim": "patience", "tier": 2, "label": "Child quality: Thrift (binary)"},
    "Q14": {"dim": "patience", "tier": 2, "label": "Child quality: Perseverance (binary)"},
    "Q43": {"dim": "patience", "tier": 2, "label": "Less importance on work: good/bad (1-3)"},
    "Q50": {"dim": "patience", "tier": 3, "label": "Financial satisfaction (1-10)"},
    "Q106": {"dim": "risktaking", "tier": 2, "label": "Incomes equal (1) vs different (10)"},
    "Q107": {"dim": "risktaking", "tier": 2, "label": "Private ownership (1) vs govt (10)"},
    "Q109": {"dim": "risktaking", "tier": 2, "label": "Competition good (1) vs harmful (10)"},
    "Q178": {"dim": "risktaking", "tier": 3, "label": "Justifiable: fare avoidance (1-10)"},
    "Q12": {"dim": "posrecip", "tier": 2, "label": "Child quality: Tolerance/respect (binary)"},
    "Q174": {"dim": "posrecip", "tier": 2, "label": "Religion: follow norms vs do good (binary)"},
    "Q81": {"dim": "posrecip", "tier": 3, "label": "Confidence: Charitable orgs (1-4 inv)"},
    "Q176": {"dim": "negrecip", "tier": 2, "label": "Moral clarity (1-10)"},
    "Q177": {"dim": "negrecip", "tier": 2, "label": "Justifiable: Claiming benefits (1-10 inv)"},
    "Q179": {"dim": "negrecip", "tier": 2, "label": "Justifiable: Stealing (1-10 inv)"},
    "Q195": {"dim": "negrecip", "tier": 3, "label": "Justifiable: Death penalty (1-10)"},
    "Q101": {"dim": "altruism", "tier": 2, "label": "Member: Charitable org (0-2)"},
    "Q99": {"dim": "altruism", "tier": 2, "label": "Member: Environmental org (0-2)"},
    "Q103": {"dim": "altruism", "tier": 3, "label": "Member: Self-help group (0-2)"},
}


HF_ENDPOINTS = {
    "hf-teacher": {
        "role": "teacher",
        "endpoint_name": "llama-3-3-70b-instruct-gguf-fnk",
        "hardware": "Nvidia A100",
        "base_url": "https://ekrwkvwahr5lvj8c.us-east-1.aws.endpoints.huggingface.cloud/v1/",
        "base_url_env": "HF_TEACHER_ENDPOINT_URL",
        "api_key_env": "HF_TOKEN",
        "hourly_rate_env": "HF_TEACHER_HOURLY_USD",
        "default_hourly_rate_usd": 2.50,
        "observed_total_runtime_seconds": 14160,
        "observed_total_cost_usd": 9.83,
        "litellm_model": "",
        "custom_llm_provider": "openai",
    },
    "hf-generator": {
        "role": "generator",
        "endpoint_name": "qwen3-32b-chm",
        "hardware": "1x Nvidia H200",
        "base_url": "https://qd7j7zt2xlehhoj3.us-east-2.aws.endpoints.huggingface.cloud/v1/",
        "base_url_env": "HF_GENERATOR_ENDPOINT_URL",
        "api_key_env": "HF_TOKEN",
        "hourly_rate_env": "HF_GENERATOR_HOURLY_USD",
        "default_hourly_rate_usd": 5.00,
        "observed_total_runtime_seconds": 12720,
        "observed_total_cost_usd": 17.67,
        "litellm_model": "",
        "custom_llm_provider": "openai",
    },
    "hf-scorer": {
        "role": "scorer",
        "endpoint_name": "phi-4-uid",
        "hardware": "Nvidia L40S",
        "base_url": "https://hyk3cllaaadt9v5d.us-east-1.aws.endpoints.huggingface.cloud/v1/",
        "base_url_env": "HF_SCORER_ENDPOINT_URL",
        "api_key_env": "HF_TOKEN",
        "hourly_rate_env": "HF_SCORER_HOURLY_USD",
        "default_hourly_rate_usd": 1.80,
        "observed_total_runtime_seconds": 17280,
        "observed_total_cost_usd": 8.64,
        "litellm_model": "",
        "custom_llm_provider": "openai",
    },
}


MODEL_PRICING = {
    # Token usage is tracked for observability. Hugging Face endpoint billing is
    # estimated from elapsed runtime and endpoint hourly-rate environment variables.
    "hf-teacher": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "hf-generator": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "hf-scorer": {"input_per_1m": 0.0, "output_per_1m": 0.0},
}


@dataclass(slots=True)
class EstimateAssumptions:
    """Static estimate inputs for no-network cost projections."""

    estimated_qc_pass_rate: float = 0.65
    estimated_facets_per_dimension: int = 5
    facet_prompt_input_tokens: int = 450
    facet_prompt_output_tokens: int = 150
    scenario_prompt_input_tokens: int = 600
    scenario_prompt_output_tokens: int = 350
    triplet_prompt_input_tokens: int = 950
    triplet_prompt_output_tokens: int = 450
    selection_prompt_input_tokens: int = 900
    selection_prompt_output_tokens: int = 120
    scoring_prompt_input_tokens: int = 1200
    scoring_prompt_output_tokens: int = 250


@dataclass(slots=True)
class PipelineConfig:
    """Runtime configuration for the pipeline."""

    teacher_model: str = "hf-teacher"
    generator_model: str = "hf-generator"
    scorer_model: str = "hf-scorer"
    scenarios_per_dim: int = 20
    qc_distance_thresh: float = 0.20
    qc_mono_epsilon: float = 0.03
    concurrency: int = 2
    max_retries: int = 8
    retry_backoff_min_s: float = 1.0
    retry_backoff_max_s: float = 30.0
    retry_jitter_s: float = 0.75
    cold_start_min_wait_s: float = 15.0
    server_error_min_wait_s: float = 5.0
    request_timeout_s: float = 90.0
    json_parse_retries: int = 2
    rate_limit_cooldown_s: float = 30.0
    error_rate_window: int = 50
    max_error_rate_for_continue: float = 0.75
    sample_size_policy: str = "skip_unavailable"
    use_anchors: bool = False
    keep_labeled_examples: bool = True
    normalize_perspective: str = "second_person"
    normalize_framing: bool = True
    teacher_temperature: float = 0.7
    generator_temperature: float = 0.8
    scorer_temperature: float = 0.1
    seed: int = 42
    default_countries: list[str] = field(default_factory=lambda: ["MEX", "USA"])
    gps_path_candidates: list[str] = field(
        default_factory=lambda: [
            "../data/GPS/GPS_dataset_country_level/country_gps.dta",
            "../data/country_gps.dta",
            "../country_gps.dta",
            "data/GPS/GPS_dataset_country_level/country_gps.dta",
            "data/country_gps.dta",
            "country_gps.dta",
        ]
    )
    wvs_path_candidates: list[str] = field(
        default_factory=lambda: [
            "../data/WVS/WVS_wave7.dta",
            "../data/wvs_wave7.dta",
            "../WVS_wave7.dta",
            "data/WVS/WVS_wave7.dta",
            "data/wvs_wave7.dta",
            "WVS_wave7.dta",
        ]
    )
    estimate: EstimateAssumptions = field(default_factory=EstimateAssumptions)

    def with_overrides(self, **overrides: Any) -> "PipelineConfig":
        """Return a copy with updated fields."""

        return replace(self, **overrides)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable config snapshot."""

        data = asdict(self)
        return data


class CostTracker:
    """Track token usage and compute endpoint runtime cost summaries."""

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.usage: dict[str, dict[str, dict[str, int]]] = {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_monotonic = time.monotonic()

    async def log(self, model: str, block: str, usage_obj: Any) -> None:
        """Record prompt/completion token usage for a model call."""

        prompt_tokens = int(getattr(usage_obj, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage_obj, "completion_tokens", 0) or 0)
        async with self.lock:
            self.usage.setdefault(model, {}).setdefault(
                block, {"input": 0, "output": 0, "calls": 0}
            )
            block_usage = self.usage[model][block]
            block_usage["input"] += prompt_tokens
            block_usage["output"] += completion_tokens
            block_usage["calls"] += 1

    def summary(self, elapsed_seconds: float | None = None) -> dict[str, Any]:
        """Return a nested summary with per-block and total costs."""

        models: dict[str, Any] = {}
        token_cost = 0.0
        for model, blocks in self.usage.items():
            pricing = MODEL_PRICING.get(model, {"input_per_1m": 0.0, "output_per_1m": 0.0})
            model_total = 0.0
            model_blocks: dict[str, Any] = {}
            for block, counts in blocks.items():
                cost = (
                    counts["input"] / 1_000_000 * pricing["input_per_1m"]
                    + counts["output"] / 1_000_000 * pricing["output_per_1m"]
                )
                model_blocks[block] = {**counts, "cost_usd": round(cost, 6)}
                model_total += cost
            models[model] = {"blocks": model_blocks, "total_cost_usd": round(model_total, 6)}
            token_cost += model_total

        elapsed = max(
            0.0,
            elapsed_seconds if elapsed_seconds is not None else time.monotonic() - self.started_monotonic,
        )
        endpoint_runtime_costs = _estimate_endpoint_runtime_cost(elapsed)
        runtime_total = endpoint_runtime_costs["total_cost_usd"]

        return {
            "created_at": self.created_at,
            "models": models,
            "token_pricing_cost_usd": round(token_cost, 6),
            "endpoint_runtime_cost": endpoint_runtime_costs,
            "total_cost_usd": round(runtime_total if runtime_total > 0 else token_cost, 6),
        }

    def estimate_run(
        self,
        config: PipelineConfig,
        countries: list[str],
        sample_sizes: list[int] | None = None,
    ) -> dict[str, Any]:
        """Return a no-network cost estimate."""

        dims = len(GPS_DIMENSIONS)
        estimated_facets = config.estimate.estimated_facets_per_dimension
        raw_per_country = config.scenarios_per_dim * dims
        fixed_triplets = config.scenarios_per_dim * dims
        expected_pass_per_country = int(raw_per_country * config.estimate.estimated_qc_pass_rate)
        max_requested_sample = max(sample_sizes) if sample_sizes else None

        teacher_calls = dims + dims * estimated_facets
        generator_calls = fixed_triplets
        selection_calls = raw_per_country * len(countries)
        scorer_calls = selection_calls

        teacher_tokens_in = teacher_calls * (
            config.estimate.facet_prompt_input_tokens
            + config.estimate.scenario_prompt_input_tokens
        )
        teacher_tokens_out = dims * config.estimate.facet_prompt_output_tokens + teacher_calls * (
            config.estimate.scenario_prompt_output_tokens
        )
        generator_tokens_in = generator_calls * config.estimate.triplet_prompt_input_tokens
        generator_tokens_out = generator_calls * config.estimate.triplet_prompt_output_tokens
        selection_tokens_in = selection_calls * config.estimate.selection_prompt_input_tokens
        selection_tokens_out = selection_calls * config.estimate.selection_prompt_output_tokens
        scorer_tokens_in = scorer_calls * config.estimate.scoring_prompt_input_tokens
        scorer_tokens_out = scorer_calls * config.estimate.scoring_prompt_output_tokens

        breakdown = {
            "teacher": _estimate_cost_for_tokens(
                config.teacher_model, teacher_calls, teacher_tokens_in, teacher_tokens_out
            ),
            "generator": _estimate_cost_for_tokens(
                config.generator_model,
                generator_calls,
                generator_tokens_in,
                generator_tokens_out,
            ),
            "scorer": _estimate_cost_for_tokens(
                config.scorer_model, scorer_calls, scorer_tokens_in, scorer_tokens_out
            ),
            "selection": _estimate_cost_for_tokens(
                config.scorer_model,
                selection_calls,
                selection_tokens_in,
                selection_tokens_out,
            ),
        }
        stage_estimates = {
            "scenario_generation": {
                **breakdown["teacher"],
                "description": "Facet and scenario-bank generation, shared across countries.",
            },
            "fixed_triplet_generation": {
                **breakdown["generator"],
                "description": "One fixed A/B triplet per generated scenario.",
            },
            "profile_selection": {
                **breakdown["selection"],
                "description": "Country-specific chosen/rejected selection for each fixed triplet.",
            },
            "scoring_qc": {
                **breakdown["scorer"],
                "description": "QC scoring for each country-specific pair.",
            },
            "export": {
                "model": "local",
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "description": "Local JSONL/HF/manifest writes. Nested sample sizes do not add LLM calls.",
            },
        }

        total_pairs = raw_per_country * len(countries)
        total_llm_calls = sum(stage["calls"] for stage in stage_estimates.values())
        total_input_tokens = sum(stage["input_tokens"] for stage in stage_estimates.values())
        total_output_tokens = sum(stage["output_tokens"] for stage in stage_estimates.values())
        effective_concurrency = max(config.concurrency, 1)
        adjusted_seconds_per_pair = 5.6 / (effective_concurrency / 2)
        total_seconds = int(round(adjusted_seconds_per_pair * total_pairs + 30))
        token_cost = round(
            breakdown["teacher"]["cost_usd"]
            + breakdown["generator"]["cost_usd"]
            + breakdown["selection"]["cost_usd"]
            + breakdown["scorer"]["cost_usd"],
            6,
        )
        runtime_cost = _estimate_endpoint_runtime_cost(float(total_seconds))
        country_count = max(len(countries), 1)
        rough_total_cost = (
            runtime_cost["total_cost_usd"] if runtime_cost["total_cost_usd"] > 0 else token_cost
        )
        variable_token_cost = breakdown["selection"]["cost_usd"] + breakdown["scorer"]["cost_usd"]
        fixed_token_cost = breakdown["teacher"]["cost_usd"] + breakdown["generator"]["cost_usd"]

        return {
            "countries": countries,
            "country_count": len(countries),
            "scenarios_per_dim": config.scenarios_per_dim,
            "gps_dimension_count": dims,
            "raw_pairs_per_country": raw_per_country,
            "raw_pairs_total": total_pairs,
            "expected_qc_passed_per_country": expected_pass_per_country,
            "estimated_qc_pass_rate": config.estimate.estimated_qc_pass_rate,
            "sample_sizes": sample_sizes or [],
            "max_requested_sample_size": max_requested_sample,
            "estimated_facets_per_dimension": estimated_facets,
            "total_llm_calls": total_llm_calls,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "stage_estimates": stage_estimates,
            "breakdown": breakdown,
            "token_pricing_cost_usd": token_cost,
            "endpoint_runtime_cost": runtime_cost,
            "total_cost_usd": rough_total_cost,
            "rough_cost_per_country_usd": round(rough_total_cost / country_count, 6),
            "token_cost_basis": {
                "fixed_shared_cost_usd": round(fixed_token_cost, 6),
                "variable_country_cost_usd": round(variable_token_cost / country_count, 6),
                "note": (
                    "Token-pricing costs are zero for the configured Hugging Face endpoints; "
                    "runtime endpoint cost is usually the relevant budget number."
                ),
            },
            "major_cost_drivers": {
                "scenarios_per_dim": config.scenarios_per_dim,
                "gps_dimensions": dims,
                "countries": len(countries),
                "raw_pairs_per_country": raw_per_country,
                "selection_and_scoring_calls_scale_with": "scenarios_per_dim * gps_dimensions * countries",
                "nested_sample_sizes_add_llm_calls": False,
            },
            "estimated_runtime": {
                "seconds": total_seconds,
                "human_readable": _format_duration(total_seconds),
                "concurrency": config.concurrency,
                "note": (
                    "Based on 5.6s/pair at concurrency=2. Actual time depends on API latency "
                    "and rate limits. Fixed triplets are generated once, then selected/scored per country."
                ),
            },
        }


def _estimate_cost_for_tokens(
    model: str, calls: int, input_tokens: int, output_tokens: int
) -> dict[str, Any]:
    pricing = MODEL_PRICING.get(model, {"input_per_1m": 0.0, "output_per_1m": 0.0})
    cost = input_tokens / 1_000_000 * pricing["input_per_1m"] + output_tokens / 1_000_000 * pricing[
        "output_per_1m"
    ]
    return {
        "model": model,
        "calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    }


def _endpoint_hourly_rate_usd(model: str) -> float:
    return _endpoint_hourly_rate_status(model)["hourly_rate_usd"]


def resolve_hf_endpoint_base_url(model: str) -> str:
    """Resolve a Hugging Face endpoint URL, allowing .env overrides."""

    endpoint = HF_ENDPOINTS[model]
    env_name = endpoint.get("base_url_env", "")
    env_value = os.environ.get(env_name, "").strip() if env_name else ""
    return env_value or endpoint["base_url"]


def _endpoint_hourly_rate_status(model: str) -> dict[str, Any]:
    endpoint = HF_ENDPOINTS.get(model)
    if not endpoint:
        return {
            "hourly_rate_usd": 0.0,
            "rate_env": "",
            "rate_status": "unknown_endpoint",
            "rate_source": "missing",
        }

    rate_env = endpoint["hourly_rate_env"]
    default_rate = float(endpoint.get("default_hourly_rate_usd", 0.0) or 0.0)
    raw_rate = os.environ.get(rate_env, "").strip()
    if not raw_rate:
        if default_rate > 0:
            return {
                "hourly_rate_usd": default_rate,
                "rate_env": rate_env,
                "rate_status": "configured",
                "rate_source": "config_default",
            }
        return {
            "hourly_rate_usd": 0.0,
            "rate_env": rate_env,
            "rate_status": "missing",
            "rate_source": "missing",
        }
    try:
        rate = float(raw_rate)
    except ValueError:
        if default_rate > 0:
            return {
                "hourly_rate_usd": default_rate,
                "rate_env": rate_env,
                "rate_status": "invalid",
                "rate_source": "invalid_env_using_default",
            }
        return {
            "hourly_rate_usd": 0.0,
            "rate_env": rate_env,
            "rate_status": "invalid",
            "rate_source": "missing",
        }
    return {
        "hourly_rate_usd": max(0.0, rate),
        "rate_env": rate_env,
        "rate_status": "configured",
        "rate_source": "env_override",
    }


def historical_endpoint_spend_summary() -> dict[str, Any]:
    """Return observed provider-console endpoint spend used for calibration."""

    endpoints: dict[str, Any] = {}
    total_runtime_seconds = 0
    total_cost = 0.0
    for model, endpoint in HF_ENDPOINTS.items():
        runtime_seconds = int(endpoint.get("observed_total_runtime_seconds", 0) or 0)
        observed_cost = float(endpoint.get("observed_total_cost_usd", 0.0) or 0.0)
        total_runtime_seconds += runtime_seconds
        total_cost += observed_cost
        endpoints[model] = {
            "role": endpoint["role"],
            "endpoint_name": endpoint.get("endpoint_name", ""),
            "hardware": endpoint.get("hardware", ""),
            "observed_total_runtime_seconds": runtime_seconds,
            "observed_total_runtime_human": _format_duration(runtime_seconds),
            "observed_total_cost_usd": round(observed_cost, 2),
        }

    return {
        "basis": (
            "Historical Hugging Face provider-console spend since endpoint creation. "
            "This is calibration metadata only and is not added to per-run cost estimates."
        ),
        "endpoints": endpoints,
        "total_observed_runtime_seconds": total_runtime_seconds,
        "total_observed_runtime_human": _format_duration(total_runtime_seconds),
        "total_observed_cost_usd": round(total_cost, 2),
    }


def _format_duration(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if seconds:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{hours}h {minutes}m"


def _estimate_endpoint_runtime_cost(elapsed_seconds: float) -> dict[str, Any]:
    hours = max(0.0, elapsed_seconds) / 3600
    endpoints: dict[str, Any] = {}
    total = 0.0
    missing_rate_envs: list[str] = []
    invalid_rate_envs: list[str] = []
    for model in HF_ENDPOINTS:
        rate_status = _endpoint_hourly_rate_status(model)
        hourly_rate = rate_status["hourly_rate_usd"]
        cost = hourly_rate * hours
        if rate_status["rate_status"] == "missing":
            missing_rate_envs.append(rate_status["rate_env"])
        elif rate_status["rate_status"] == "invalid":
            invalid_rate_envs.append(rate_status["rate_env"])
        endpoints[model] = {
            "role": HF_ENDPOINTS[model]["role"],
            "endpoint_name": HF_ENDPOINTS[model].get("endpoint_name", ""),
            "hardware": HF_ENDPOINTS[model].get("hardware", ""),
            "hourly_rate_usd": hourly_rate,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "cost_usd": round(cost, 6),
            "rate_env": rate_status["rate_env"],
            "rate_status": rate_status["rate_status"],
            "rate_source": rate_status["rate_source"],
        }
        total += cost

    return {
        "basis": (
            "Elapsed wall-clock runtime multiplied by Hugging Face endpoint hourly rates. "
            "Configured defaults are used unless HF_TEACHER_HOURLY_USD, "
            "HF_GENERATOR_HOURLY_USD, or HF_SCORER_HOURLY_USD provide valid overrides."
        ),
        "elapsed_seconds": round(max(0.0, elapsed_seconds), 3),
        "endpoints": endpoints,
        "rates_configured": not missing_rate_envs,
        "missing_rate_envs": missing_rate_envs,
        "invalid_rate_envs": invalid_rate_envs,
        "historical_endpoint_spend": historical_endpoint_spend_summary(),
        "total_cost_usd": round(total, 6),
    }


CONFIG = PipelineConfig()


def resolve_existing_path(candidates: list[str] | list[Path]) -> Path | None:
    """Return the first existing path from the candidate list."""

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return None
