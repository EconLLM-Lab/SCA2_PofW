"""Held-out pool tests. Text and metadata only: no WVS response is read here."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import build_pool as B  # noqa: E402
import questionnaire_text as QT  # noqa: E402


def test_standalone_item_text():
    t = QT.extract()
    assert t["Q57"].startswith("Generally speaking, would you say that most people can be trusted")
    assert "(Code" not in t["Q57"]


def test_grid_row_gets_its_battery_intro():
    t = QT.extract()
    assert "confidence" in t["Q65"].lower() and "armed forces" in t["Q65"].lower()
    assert "claiming government benefits" in t["Q177"].lower()
    assert "justif" in t["Q177"].lower()


def test_every_questionnaire_item_is_found():
    assert len(QT.extract()) >= 270   # 291 Q items; misses are demographics (Q260+)


def test_select_pool_rules():
    items = {
        "Q57": {"codes": ["1", "2"], "labels": ["a", "b"]},
        "Q150": {"codes": ["1", "2"], "labels": ["Freedom", "Security"]},
        "Q94": {"codes": ["0", "1", "2"], "labels": ["no", "inactive", "active"]},
        "Q164": {"codes": [str(i) for i in range(1, 11)], "labels": ["x"] * 10},
        "Q223": {"codes": [str(i) for i in range(1, 40)], "labels": ["p"] * 39},
        "Q262": {"codes": ["1", "2"], "labels": ["m", "f"]},
        "Q300": {"codes": ["1", "3"], "labels": ["a", "b"]},
    }
    assert B.select_pool(items) == ["Q94", "Q150", "Q164"]


def test_ordinal_heuristic():
    assert B.ordinal_guess(["Freedom", "Security"]) == "TRUE"          # binary
    assert B.ordinal_guess(["Not at all important", "2", "3", "Very important"]) == "TRUE"
    assert B.ordinal_guess(["A great deal", "Quite a lot", "Not very much", "None at all"]) == "TRUE"
    assert B.ordinal_guess(["Economic growth", "Strong defence", "Say at work", "Beautiful cities"]) == "REVIEW"
