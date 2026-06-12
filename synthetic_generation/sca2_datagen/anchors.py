"""Scenario anchor loading and prompt formatting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ANCHOR_DIR = Path(__file__).resolve().parents[1] / "config" / "anchors"
ANCHOR_FILE_ALIASES = {
    "risktaking": "risk_aversion",
    "posrecip": "pos_reciprocity",
    "negrecip": "neg_reciprocity",
}
ANCHOR_FIELDS = {
    "anchor_id",
    "dimension",
    "primary_facet",
    "archetype_name",
    "narrative",
    "high_response",
    "low_response",
}


def load_anchors(dimension: str) -> list[dict[str, Any]]:
    """Load curated scenario anchors for one GPS dimension from JSONL."""

    anchor_dimension = ANCHOR_FILE_ALIASES.get(dimension, dimension)
    anchor_path = ANCHOR_DIR / f"{anchor_dimension}_anchors.jsonl"
    if not anchor_path.exists():
        return []

    anchors: list[dict[str, Any]] = []
    with anchor_path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            anchor = json.loads(line)
            missing_fields = ANCHOR_FIELDS - set(anchor)
            extra_fields = set(anchor) - ANCHOR_FIELDS
            if missing_fields or extra_fields:
                raise ValueError(
                    f"Invalid anchor schema in {anchor_path}:{line_number}; "
                    f"missing={sorted(missing_fields)} extra={sorted(extra_fields)}"
                )
            anchors.append(anchor)
    return anchors


def format_anchor_block(dimension: str, anchors: list[dict[str, Any]]) -> str:
    """Format sampled anchors as the generator few-shot guidance block."""

    examples = []
    for index, anchor in enumerate(anchors, start=1):
        examples.append(
            f"Example {index}\n"
            f"Archetype: {anchor['archetype_name']}\n"
            f"Narrative: {anchor['narrative']}\n"
            f"Response A (higher on dimension): {anchor['high_response']}\n"
            f"Response B (lower on dimension): {anchor['low_response']}"
        )

    return (
        f"## High-Quality Reference Anchors for the {dimension} dimension\n\n"
        "Study the following curated examples. They show diverse narrative structures and how the "
        f"{dimension} preference appears in natural language. Use them only as structural guidance.\n\n"
        "Your new triplet MUST:\n"
        "- Use a completely different archetype and situational frame from every example below.\n"
        "- Vary the narrative stage (micro-dyadic, small-community resource, one-shot high-stakes "
        "anonymous encounter, or repeated-interaction dilemma).\n"
        "- Maintain absolute cultural neutrality — no countries, ethnic groups, religions, or "
        "specific institutions.\n"
        "- Produce responses whose contrast loads primarily on the target dimension with minimal "
        "confounding.\n\n"
        + "\n\n".join(examples)
        + "\n\n[Repeat for the other 1-2 sampled anchors]\n\n"
        "Now generate ONE new triplet in exactly this format:\n\n"
        "scenario: <fresh narrative>\n"
        "response_a: <higher on dimension>\n"
        "response_b: <lower on dimension>"
    )
