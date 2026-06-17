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
        "Use these anchors as positive structural exemplars. Emulate the facet logic, core tradeoff phrasing, "
        "storyline skeleton style, and behavioral contrast pattern of the anchors for the target facet. "
        "Adapt the setting, stakes, social relationships, and decision objects to new realistic contexts "
        "while preserving the underlying decision skeleton and facet emphasis.\n\n"
        "Your generation MUST:\n"
        "- Vary the specific setting, decision object, social distance, timing, opportunity cost, and domain from every anchor below.\n"
        "- Keep the scenario and both responses culturally neutral: no countries, names, ethnic "
        "references, or specific institutions.\n"
        "- Make the behavioral contrast load primarily on the target dimension.\n"
        "- Do not reuse the exact scenario text or identical decision object from any anchor.\n\n"
        "Keep prohibited frames minimal unless the facet specifically requires them.\n\n"
        + "\n\n".join(examples)
    )
