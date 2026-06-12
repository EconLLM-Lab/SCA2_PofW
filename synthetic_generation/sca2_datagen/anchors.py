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
    "id",
    "dimension",
    "facet",
    "archetype",
    "storyline_skeleton",
    "full_scenario",
    "core_tradeoff",
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
            f"Anchor {index}: {anchor['id']}\n"
            f"Facet: {anchor['facet']}\n"
            f"Archetype: {anchor['archetype']}\n"
            f"Structure: {anchor['storyline_skeleton']}\n"
            f"Scenario: {anchor['full_scenario']}\n"
            f"Core tradeoff: {anchor['core_tradeoff']}"
        )

    return (
        f"## High-Quality Reference Anchors for the {dimension} dimension\n\n"
        "Use these anchors only as calibration examples for realistic economic tradeoffs. "
        "Do not copy their setting, objects, social distance, timing, opportunity cost, "
        "decision stage, or domain.\n\n"
        "Your generation MUST:\n"
        "- Create scenarios that are structurally different from every anchor below.\n"
        "- Use a new combination of social distance, stakes, domain, and decision stage.\n"
        "- Keep the scenario and both responses culturally neutral: no countries, names, ethnic "
        "references, or specific institutions.\n"
        "- Make the behavioral contrast load primarily on the target dimension.\n"
        "- Avoid reusing the same cost type, social relationship, or time horizon from the anchors.\n\n"
        "Anti-pattern frames to avoid: generic shared shelves, community gardens, music festivals, "
        "vague strangers on the street, lost wallets, generic fundraisers, volunteer cleanups, "
        "and undifferentiated shared supplies.\n\n"
        + "\n\n".join(examples)
    )
