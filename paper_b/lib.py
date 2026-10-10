"""Paper B — shared pure logic, mirroring DPO_data_preparation_599_multi_country_cached_ref.

Fidelity note: these functions reproduce the notebook's normalization, shared-bank
verification, and split exactly, so the script path and the notebook agree.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterable

# same renames as the notebook
DIMENSION_RENAMES = {
    "negrecip": "negative_reciprocity",
    "posrecip": "positive_reciprocity",
    "risktaking": "risk_taking",
}
REQUIRED_DPO_FIELDS = ("prompt", "chosen", "rejected")


# ---------------------------------------------------------------- io
def load_jsonl(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(rows: Iterable[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- normalization
def normalize_prompt(text: str | None) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return text
    text = text.strip()
    first = text.split()[0]
    if first == "Context:":
        return text
    if first == "context:":
        return text[:1].upper() + text[1:]
    return "Context: " + text


def normalize_row(row: dict) -> dict:
    row = dict(row)
    row["prompt"] = normalize_prompt(row.get("prompt"))
    for field in ("chosen", "rejected"):
        value = row.get(field)
        if isinstance(value, str):
            row[field] = value.strip()
    if "gps_dimension" in row:
        row["gps_dimension"] = DIMENSION_RENAMES.get(row["gps_dimension"], row["gps_dimension"])
    return row


def validate_rows(rows: list[dict], source_name: str = "dataset") -> None:
    if not rows:
        raise ValueError(f"{source_name} is empty")
    for i, row in enumerate(rows):
        for field in REQUIRED_DPO_FIELDS:
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{source_name}: row {i} has missing/empty required field {field!r}")
        if row["chosen"] == row["rejected"]:
            raise ValueError(f"{source_name}: row {i} has identical chosen and rejected")


def load_country(raw_path: str | Path) -> tuple[list[dict], dict[str, dict]]:
    rows = [normalize_row(r) for r in load_jsonl(raw_path)]
    validate_rows(rows, source_name=str(raw_path))
    by_prompt: dict[str, dict] = {}
    for row in rows:
        p = row["prompt"]
        if p in by_prompt:
            raise ValueError(f"{raw_path}: duplicate normalized prompt (expected one DPO row per prompt)")
        by_prompt[p] = row
    return rows, by_prompt


# ---------------------------------------------------------------- shared-bank checks
def response_pair(row: dict) -> frozenset:
    return frozenset((row["chosen"], row["rejected"]))


def verify_shared_questions(country_rows_by_prompt: dict[str, dict[str, dict]],
                            reference_code: str) -> set[str]:
    reference_map = country_rows_by_prompt[reference_code]
    reference_prompts = set(reference_map)
    for cc, current_map in country_rows_by_prompt.items():
        if cc == reference_code:
            continue
        current_prompts = set(current_map)
        missing = reference_prompts - current_prompts
        extra = current_prompts - reference_prompts
        if missing or extra:
            raise ValueError(
                f"{cc}: prompt set differs from {reference_code} (missing={len(missing)}, extra={len(extra)})"
            )
        for prompt in reference_prompts:
            if response_pair(reference_map[prompt]) != response_pair(current_map[prompt]):
                raise ValueError(f"{cc}: response texts differ for prompt: {prompt[:120]}...")
    return reference_prompts


def make_shared_split(all_prompts: set[str], train_frac: float, seed: int) -> tuple[set[str], set[str]]:
    prompt_list = sorted(all_prompts)
    rng = random.Random(seed)
    rng.shuffle(prompt_list)
    n_train = int(len(prompt_list) * train_frac)
    return set(prompt_list[:n_train]), set(prompt_list[n_train:])


# ---------------------------------------------------------------- prompt wrapper
def build_user_prompt(prompt_text: str) -> str:
    return (
        "You are answering a questionnaire as an individual person. "
        "Respond naturally and thoughtfully, as someone would in real life. "
        "Do not mention being an AI or assistant. "
        "Keep the answer short, under 3 sentences. "
        "Give a sincere, human-like answer.\n\n"
        "Situation:\n"
        f"{prompt_text.strip()}\n\n"
        "Answer:"
    )


# ---------------------------------------------------------------- ref cache
def load_shared_cache(path: str | Path) -> dict[tuple[str, str], float]:
    """Compact cache schema: rows of {prompt, completion, ref_logp}."""
    rows = load_jsonl(path)
    if not rows:
        raise ValueError(f"Shared ref cache is empty: {path}")
    cache: dict[tuple[str, str], float] = {}
    for i, row in enumerate(rows):
        p = normalize_prompt(row.get("prompt"))
        completion = row.get("completion")
        value = row.get("ref_logp")
        if not p or not isinstance(completion, str) or value is None:
            raise ValueError(f"{path}: invalid cache row {i}")
        cache[(p, completion.strip())] = float(value)
    return cache


def write_shared_cache(cache: dict[tuple[str, str], float], path: str | Path) -> None:
    rows = [
        {"prompt": prompt, "completion": completion, "ref_logp": value}
        for (prompt, completion), value in sorted(cache.items())
    ]
    write_jsonl(rows, path)


def cache_coverage(cache: dict[tuple[str, str], float], train_prompts: set[str],
                   shared_response_pairs: dict[str, frozenset]) -> list[tuple[str, str]]:
    missing = []
    for prompt in sorted(train_prompts):
        for completion in shared_response_pairs[prompt]:
            if (prompt, completion) not in cache:
                missing.append((prompt, completion))
    return missing
