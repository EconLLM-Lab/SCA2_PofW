"""Shared utilities for JSON parsing, logging, retries, and git metadata."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

import litellm
from litellm import acompletion
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm

from .config import CostTracker

litellm.drop_params = True


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


@retry(wait=wait_exponential(multiplier=1, min=1, max=20), stop=stop_after_attempt(5), reraise=True)
async def tracked_completion(block: str, tracker: CostTracker, **kwargs: Any) -> Any:
    """Call LiteLLM asynchronously with retries and cost tracking."""

    response = await acompletion(**kwargs)
    if tracker is not None and getattr(response, "usage", None):
        await tracker.log(kwargs.get("model", "unknown"), block, response.usage)
    return response


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
    finally:
        progress_bar.close()

    return results


async def _wrap_index(index: int, task: asyncio.Task[Any]) -> tuple[int, Any]:
    """Return the original index alongside the awaited task result."""

    return index, await task
