"""Canonical repository paths for Paper B's committed result artifacts."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "paper_b" / "results"

NUMBERS_TABLE = RESULTS_DIR / "NUMBERS_TABLE.csv"
CLAIM_LOCK = RESULTS_DIR / "CLAIM_LOCK.md"
TIER1_RESULTS_DIR = RESULTS_DIR / "tier1"
ITEM_TABLE_DIR = RESULTS_DIR / "item_table"
QUESTIONNAIRE_TEXT = ITEM_TABLE_DIR / "MasterQuestionnaire.txt"
QUESTION_MAP = REPO_ROOT / "sca2" / "data" / "question_map_wvs_edited.csv"

BANKED_20261011_DIR = RESULTS_DIR / "banked_20261011"
BANKED_20261011_MODEL_PROBS = BANKED_20261011_DIR / "model_probs.csv"
BANKED_20261011_THREE_COLUMN = (
    BANKED_20261011_DIR / "analysis" / "three_column_table.csv"
)
BANKED_20261011_LOCAL_EVAL = BANKED_20261011_DIR / "local_eval"

# The frozen numbers table records these former locations as provenance. Keep
# those strings stable when rebuilding rows, while resolving reads to the new
# public layout.
LEGACY_TIER1_RESULTS = (
    Path("planning") / "sprint_2026-10-11" / "paper-b-tier1" / "results"
)
LEGACY_NUMBERS_TABLE = LEGACY_TIER1_RESULTS.parent / "NUMBERS_TABLE.csv"
LEGACY_CLAIM_LOCK = Path("planning") / "TWO_PAPER_CLAIM_LOCK.md"
LEGACY_BANKED_20261011 = (
    Path("planning") / "sprint_2026-10-11" / "paper-b-20261011"
)


def resolve_recorded_path(path: str | Path) -> Path:
    """Resolve a frozen provenance path after the public-layout move."""

    recorded = Path(path)
    if recorded == LEGACY_NUMBERS_TABLE:
        return NUMBERS_TABLE
    if recorded == LEGACY_TIER1_RESULTS or LEGACY_TIER1_RESULTS in recorded.parents:
        return TIER1_RESULTS_DIR / recorded.relative_to(LEGACY_TIER1_RESULTS)
    if recorded == LEGACY_BANKED_20261011 or LEGACY_BANKED_20261011 in recorded.parents:
        return BANKED_20261011_DIR / recorded.relative_to(LEGACY_BANKED_20261011)
    return recorded if recorded.is_absolute() else REPO_ROOT / recorded


def recorded_path(path: str | Path) -> Path:
    """Return the frozen provenance spelling for a relocated result path."""

    resolved = Path(path).resolve()
    if resolved == NUMBERS_TABLE:
        return LEGACY_NUMBERS_TABLE
    if resolved == TIER1_RESULTS_DIR or TIER1_RESULTS_DIR in resolved.parents:
        return LEGACY_TIER1_RESULTS / resolved.relative_to(TIER1_RESULTS_DIR)
    if resolved == BANKED_20261011_DIR or BANKED_20261011_DIR in resolved.parents:
        return LEGACY_BANKED_20261011 / resolved.relative_to(BANKED_20261011_DIR)
    return resolved.relative_to(REPO_ROOT)
