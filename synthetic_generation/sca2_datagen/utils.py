"""Shared utilities for JSON parsing, logging, retries, and git metadata."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import litellm
from litellm import acompletion
from tqdm.auto import tqdm

from .config import CostTracker, HF_ENDPOINTS, PipelineConfig, resolve_hf_endpoint_base_url

litellm.drop_params = True
litellm.suppress_debug_info = True


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure logging once and return the package logger."""

    logger = logging.getLogger("sca2_datagen")
    if not logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    logger.setLevel(level)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    return logger

def log_stage_header(logger: logging.Logger, stage_num: int, total_stages: int, title: str) -> None:
    """Print a clean, readable stage header."""
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info(f"STAGE {stage_num}/{total_stages}: {title}")
    logger.info(separator)


def log_banner(logger: logging.Logger, text: str, style: str = "double") -> None:
    """Print a clean, elegant banner for stage transitions."""
    width = 72
    if style == "double":
        line = "=" * width
    elif style == "single":
        line = "-" * width
    else:
        line = "=" * width
    centered = text.center(width)
    logger.info(f"
{line}")
    logger.info(centered)
    logger.info(line)

def compact_error_message(error: Any) -> str:
    """Return a short, single-line error summary."""

    if isinstance(error, Exception):
        text = f"{type(error).__name__}: {error}"
    else:
        text = str(error)
    text = " ".join(text.split())
    if len(text) > 220:
        return f"{text[:217]}..."
    return text


def summarize_error_messages(messages: list[str], top_n: int = 3) -> list[str]:
    """Return most frequent error summaries with counts."""

    if not messages:
        return []
    counts = Counter(messages)
    return [f"{message} (x{count})" for message, count in counts.most_common(top_n)]


def clean_json(content: str) -> str:
    """Strip markdown code fences from JSON-like model output."""

    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped[7:]
    elif stripped.startswith("```"):
        stripped = stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    stripped = stripped.strip()
    if stripped.startswith("{"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1].strip()
    return stripped


def extract_message_content(response: Any) -> str:
    """Extract message text from a LiteLLM response object."""

    content = response.choices[0].message.content
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item) for item in content
        )
    return str(content)


def parse_json_response(response: Any) -> dict[str, Any]:
    """Parse a LiteLLM JSON response into a dictionary."""

    content = clean_json(extract_message_content(response))
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        repaired = re.sub(r",(\s*[}\]])", r"\1", content)
        decoder = json.JSONDecoder()
        payload, _ = decoder.raw_decode(repaired)
    if not isinstance(payload, dict):
        raise ValueError("Model response JSON root must be an object.")
    return payload


async def tracked_json_completion(
    block: str,
    tracker: CostTracker,
    *,
    config: PipelineConfig | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Call a model for JSON and retry when the response is malformed."""

    parse_retries = max(0, int(config.json_parse_retries)) if config is not None else 2
    for attempt in range(parse_retries + 1):
        response = await tracked_completion(block, tracker, config=config, **kwargs)
        try:
            return parse_json_response(response)
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt >= parse_retries:
                raise
            logging.getLogger("sca2_datagen.reliability").warning(
                "Retrying malformed JSON response block=%s attempt=%d/%d error=%s",
                block,
                attempt + 1,
                parse_retries,
                compact_error_message(exc),
            )

    raise RuntimeError("tracked_json_completion retry loop exited unexpectedly")


async def tracked_completion(
    block: str,
    tracker: CostTracker,
    *,
    config: PipelineConfig | None = None,
    **kwargs: Any,
) -> Any:
    """Call LiteLLM asynchronously with retries and cost tracking."""

    if config is not None:
        kwargs.setdefault("request_timeout", config.request_timeout_s)

    max_retries = max(0, int(config.max_retries)) if config is not None else 5
    min_backoff = float(config.retry_backoff_min_s) if config is not None else 1.0
    max_backoff = float(config.retry_backoff_max_s) if config is not None else 20.0
    jitter = float(config.retry_jitter_s) if config is not None else 0.75
    model_name = kwargs.get("model", "unknown")
    endpoint = HF_ENDPOINTS.get(str(model_name))
    endpoint_role = str(endpoint["role"]) if endpoint is not None else "unknown"
    if endpoint is not None:
        token_env = endpoint["api_key_env"]
        token = os.environ.get(token_env, "").strip()
        if not token:
            raise RuntimeError(
                f"Missing {token_env}. Add it to synthetic_generation/.env or export it before running. "
                f"This HF-only pipeline needs {token_env} to call the {endpoint_role} endpoint "
                f"({model_name})."
            )
        kwargs["model"] = endpoint["litellm_model"]
        base_url = resolve_hf_endpoint_base_url(str(model_name))
        kwargs["base_url"] = base_url
        kwargs["api_key"] = token
        kwargs["custom_llm_provider"] = endpoint["custom_llm_provider"]
    elif model_name not in {"unknown", None}:
        raise ValueError(
            f"Unsupported model {model_name!r}. This pipeline is configured for Hugging Face "
            f"endpoint aliases only: {', '.join(sorted(HF_ENDPOINTS))}."
        )

    for attempt in range(max_retries + 1):
        try:
            if endpoint is not None and attempt == 0:
                logging.getLogger("sca2_datagen.api").debug(
                    "Calling Hugging Face endpoint block=%s model_alias=%s base_url=%s",
                    block,
                    model_name,
                    kwargs["base_url"],
                )
            response = await acompletion(**kwargs)
            if tracker is not None and getattr(response, "usage", None):
                await tracker.log(model_name, block, response.usage)
            return response
        except Exception as exc:
            retry_reason = _retryable_error_reason(exc)
            if attempt >= max_retries or retry_reason is None:
                raise

            retry_after_s = _extract_retry_after_seconds(exc)
            backoff = min(max_backoff, min_backoff * (2**attempt))
            minimum_wait_s = _minimum_wait_for_retry_reason(retry_reason, config)
            wait_s = max(backoff + random.uniform(0, jitter), retry_after_s, minimum_wait_s)
            _log_retry(
                block=block,
                model_name=str(model_name),
                endpoint_role=endpoint_role,
                attempt=attempt + 1,
                max_retries=max_retries,
                wait_s=wait_s,
                retry_reason=retry_reason,
                exc=exc,
            )
            await asyncio.sleep(wait_s)

    raise RuntimeError("tracked_completion retry loop exited unexpectedly")


def _is_retryable_error(exc: Exception) -> bool:
    """Classify transient provider errors that should be retried."""

    return _retryable_error_reason(exc) is not None


def _retryable_error_reason(exc: Exception) -> str | None:
    """Return a user-facing retry category for transient provider errors."""

    transient_classes = {
        "RateLimitError",
        "Timeout",
        "TimeoutError",
        "APITimeoutError",
        "APIConnectionError",
        "ServiceUnavailableError",
        "InternalServerError",
    }

    text = compact_error_message(exc).lower()
    if any(marker in text for marker in ("429", "rate limit", "rate_limited")):
        return "rate_limit"

    cold_start_markers = [
        "503",
        "service unavailable",
        "starting",
        "warming",
        "waking",
        "loading",
        "cold start",
        "scale to zero",
        "scaled to zero",
    ]
    if any(marker in text for marker in cold_start_markers):
        return "cold_start"

    server_error_markers = [
        "500",
        "502",
        "504",
        "internal server error",
        "bad gateway",
        "gateway timeout",
        "upstream",
        "temporary",
    ]
    if any(marker in text for marker in server_error_markers):
        return "server_error"

    if type(exc).__name__ in transient_classes:
        return "network"

    transient_markers = [
        "timeout",
        "connection timed out",
        "cannot connect",
        "connection error",
        "connection reset",
        "dns",
    ]
    if any(marker in text for marker in transient_markers):
        return "network"

    return None


def _minimum_wait_for_retry_reason(reason: str, config: PipelineConfig | None) -> float:
    if reason == "cold_start":
        return float(config.cold_start_min_wait_s) if config is not None else 15.0
    if reason == "server_error":
        return float(config.server_error_min_wait_s) if config is not None else 5.0
    return 0.0


def _log_retry(
    *,
    block: str,
    model_name: str,
    endpoint_role: str,
    attempt: int,
    max_retries: int,
    wait_s: float,
    retry_reason: str,
    exc: Exception,
) -> None:
    logger = logging.getLogger("sca2_datagen.reliability")
    if retry_reason == "cold_start":
        logger.warning(
            "%s endpoint appears to be waking up or temporarily unavailable; retrying block=%s "
            "alias=%s attempt=%d/%d wait_s=%.1f error=%s",
            endpoint_role,
            block,
            model_name,
            attempt,
            max_retries,
            wait_s,
            compact_error_message(exc),
        )
        return

    reason_label = {
        "rate_limit": "rate limited",
        "server_error": "returning a transient server error",
        "network": "temporarily unreachable",
    }.get(retry_reason, "temporarily unavailable")
    logger.warning(
        "%s endpoint is %s; retrying block=%s alias=%s attempt=%d/%d wait_s=%.1f error=%s",
        endpoint_role,
        reason_label,
        block,
        model_name,
        attempt,
        max_retries,
        wait_s,
        compact_error_message(exc),
    )


def _extract_retry_after_seconds(exc: Exception) -> float:
    """Best-effort parse of provider retry-after hints from exception payloads."""

    for attr in ("retry_after", "retry_after_seconds"):
        value = getattr(exc, attr, None)
        if value is not None:
            try:
                return max(0.0, float(value))
            except (TypeError, ValueError):
                pass

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) if response is not None else None
    if isinstance(headers, dict):
        for key in ("retry-after", "Retry-After"):
            value = headers.get(key)
            if value is not None:
                try:
                    return max(0.0, float(value))
                except (TypeError, ValueError):
                    continue

    return 0.0


def get_git_hash(cwd: str | Path | None = None) -> str | None:
    """Return the short current git hash if available."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def json_dumps_pretty(payload: dict[str, Any]) -> str:
    """Serialize a payload with deterministic formatting."""

    return json.dumps(payload, indent=2, sort_keys=True)


async def gather_with_progress(
    coroutines: list[Any],
    *,
    description: str,
    logger: logging.Logger,
    batch_size: int = 10,
) -> list[Any]:
    """Await coroutines with a progress bar and batched log updates."""

    if not coroutines:
        return []

    tasks = [asyncio.create_task(coroutine) for coroutine in coroutines]
    indexed_tasks = [_wrap_index(index, task) for index, task in enumerate(tasks)]
    results: list[Any] = [None] * len(tasks)
    completed = 0
    progress_bar = tqdm(
        total=len(tasks),
        desc=description,
        unit="task",
        leave=False,
        disable=not sys.stderr.isatty(),
    )
    try:
        for wrapped_task in asyncio.as_completed(indexed_tasks):
            index, result = await wrapped_task
            results[index] = result
            completed += 1
            progress_bar.update(1)
            if completed % batch_size == 0 or completed == len(tasks):
                logger.info("%s progress: %d/%d", description, completed, len(tasks))
    except Exception:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    finally:
        progress_bar.close()

    return results


async def _wrap_index(index: int, task: asyncio.Task[Any]) -> tuple[int, Any]:
    """Return the original index alongside the awaited task result."""

    return index, await task
