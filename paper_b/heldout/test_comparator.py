"""Face-valid comparator tests (text only)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparator as CM  # noqa: E402


def test_single_construct_word_assigns_and_two_abstain():
    assert CM.match_dimensions("How much confidence do you have in the police?") == ["trust"]
    assert CM.match_dimensions("Is it justifiable to use violence?") == ["negrecip"]
    assert len(CM.match_dimensions("Do you trust charities to help people?")) == 2


def test_word_prefix_not_substring():
    assert CM.match_dimensions("The distrust of experts") == []          # 'trust' inside a word
    assert CM.match_dimensions("Saving money") == ["patience"]


def test_sign_from_code1_intensity():
    assert CM.propose_sign(["A great deal", "Quite a lot", "Not very much", "None at all"]) == -1
    assert CM.propose_sign(["Never justifiable", "2", "Always justifiable"]) == 1
    assert CM.propose_sign(["Mentioned", "Not mentioned"]) == -1


def test_review_can_only_flip_or_abstain():
    pool = pd.DataFrame([{"Question": "Q1", "StandaloneQuestion": "Confidence: police",
                          "VariableLabel": "Confidence: police", "ResponseLabels": "A great deal; None"}])
    base = CM.build(pool)
    assert base.iloc[0].dimension == "trust" and base.iloc[0].sign == -1
    assert CM.build(pool, {"Q1": {"action": "flip", "reason": "x"}}).iloc[0].sign == 1
    assert CM.build(pool, {"Q1": {"action": "none", "reason": "x"}}).iloc[0].dimension == "none"
