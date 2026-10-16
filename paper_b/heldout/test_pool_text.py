"""The held-out pool must contain no unanswerable standalone text, and overrides.json must match the pool.

Defects are matched by their exact observed signatures (Amendment 1, 2026-10-16). A general grammar rule was
tried first and rejected: it flagged legitimate items, because WVS grid rows ("stem — row label") carry no
terminal punctuation and scale items legitimately end with their anchors ("Completely disagree Completely
agree"). Precise signatures do not have that failure mode.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = HERE / "pool_skeleton.csv"
OVERRIDES = HERE / "overrides.json"

REPAIRED = ("Q46", "Q82", "Q121", "Q153", "Q155", "Q157", "Q175", "Q199", "Q253", "Q254", "Q255", "Q256")

EXACT_BAD = {
    "How proud are you to be ?",
    "And which would be the next most important?",
    "And what would be the next most important?",
    "Taking all things together, would you say you are",
    "How much respect is there for individual human rights nowadays in this country? Do you feel there is",
}
BAD_SUFFIXES = ("— Your", "— The", "to be ?", "development of ?", "Are you", "religion is",
                "Do you feel there is", "would you say you are")


def broken(text: str) -> bool:
    t = text.strip()
    return t in EXACT_BAD or t.endswith(BAD_SUFFIXES)


def _rows():
    return list(csv.DictReader(open(POOL)))


def test_pool_is_223_unique_items():
    rows = _rows()
    assert len(rows) == 223
    assert len({r["Question"] for r in rows}) == 223


def test_no_item_matches_a_known_defect_signature():
    bad = {r["Question"]: r["StandaloneQuestion"][-60:] for r in _rows() if broken(r["StandaloneQuestion"])}
    assert bad == {}, f"unanswerable standalone text: {bad}"


def test_the_twelve_repaired_items_are_substantive():
    rows = {r["Question"]: r["StandaloneQuestion"] for r in _rows()}
    for q in REPAIRED:
        t = rows[q]
        assert len(t) >= 45, (q, t)
        assert not t.lower().startswith("and "), (q, t)


def test_every_text_override_matches_the_pool():
    ovr = json.loads(OVERRIDES.read_text())
    pool = {r["Question"]: r["StandaloneQuestion"] for r in _rows()}
    for q, spec in ovr.items():
        if "StandaloneQuestion" in spec:
            assert pool[q] == spec["StandaloneQuestion"], f"{q}: pool and overrides disagree"


def test_every_override_carries_a_reason():
    ovr = json.loads(OVERRIDES.read_text())
    missing = [q for q, spec in ovr.items() if not spec.get("reason")]
    assert missing == [], f"overrides without a reason: {missing}"


def test_excluded_items_absent_and_ordinal_overrides_present():
    ovr = json.loads(OVERRIDES.read_text())
    pool = {r["Question"] for r in _rows()}
    for q, spec in ovr.items():
        if spec.get("exclude"):
            assert q not in pool, f"{q}: excluded but present"
        if spec.get("ordinal") == "TRUE":
            assert q in pool, f"{q}: ordinal override but absent"


def test_option_grids_are_contiguous_non_negative():
    """The registered rule: 2 to 11 contiguous non-negative codes. 27 items legitimately start at 0."""
    for r in _rows():
        codes = [c.strip() for c in r["ResponseCodes"].split(";") if c.strip()]
        first = int(codes[0])
        assert first in (0, 1), (r["Question"], codes)
        assert 2 <= len(codes) <= 11, (r["Question"], codes)
        assert codes == [str(i) for i in range(first, first + len(codes))], (r["Question"], codes)
