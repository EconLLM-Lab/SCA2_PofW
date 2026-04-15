"""Shared utilities for JSON parsing, logging, retries, and git metadata."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import litellm
from litellm import acompletion
from tqdm.auto import tqdm

from .config import CostTracker, PipelineConfig

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
    return stripped.strip()


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

    return json.loads(clean_json(extract_message_content(response)))


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

    for attempt in range(max_retries + 1):
        try:
            response = await acompletion(**kwargs)
            if tracker is not None and getattr(response, "usage", None):
                await tracker.log(model_name, block, response.usage)
            return response
        except Exception as exc:
            if attempt >= max_retries or not _is_retryable_error(exc):
                raise

            retry_after_s = _extract_retry_after_seconds(exc)
            backoff = min(max_backoff, min_backoff * (2**attempt))
            wait_s = max(backoff + random.uniform(0, jitter), retry_after_s)
            logging.getLogger("sca2_datagen.reliability").warning(
                "Retrying model call block=%s model=%s attempt=%d/%d wait_s=%.2f error_class=%s",
                block,
                model_name,
                attempt + 1,
                max_retries,
                wait_s,
                type(exc).__name__,
            )
            await asyncio.sleep(wait_s)

    raise RuntimeError("tracked_completion retry loop exited unexpectedly")


def _is_retryable_error(exc: Exception) -> bool:
    """Classify transient provider errors that should be retried."""

    transient_classes = {
        "RateLimitError",
        "Timeout",
        "TimeoutError",
        "APITimeoutError",
        "APIConnectionError",
        "ServiceUnavailableError",
        "InternalServerError",
    }
    if type(exc).__name__ in transient_classes:
        return True

    text = compact_error_message(exc).lower()
    transient_markers = [
        "429",
        "rate limit",
        "rate_limited",
        "timeout",
        "connection timed out",
        "cannot connect",
        "temporary",
        "service unavailable",
        "internal server error",
    ]
    return any(marker in text for marker in transient_markers)


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
