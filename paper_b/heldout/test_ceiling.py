"""Ceiling crosswalk tests (synthetic frames; no survey file is read)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import ceiling as CE  # noqa: E402


def test_shortlist_prefers_matching_labels():
    ts = {"A165": "Most people can be trusted", "D001_B": "How much you trust: Your family",
          "E018": "Future changes: Greater respect for authority", "S020": "Year survey"}
    assert CE.shortlist("Most people can be trusted", ts, k=1) == ["A165"]
    assert CE.shortlist("Trust: Your family", ts, k=2)[0] == "D001_B"


def test_accept_requires_near_identity():
    ctry = [f"C{i}" for i in range(32)]
    item = pd.Series(np.linspace(1, 3, 32), index=ctry)
    cands = {"good": item * 1.0, "close": item + np.random.default_rng(0).normal(0, 0.2, 32),
             "short": item.iloc[:10]}
    best, table = CE.accept(item, cands, min_r=0.999, min_countries=30)
    assert best == "good"
    assert table["close"] < 0.999 and np.isnan(table["short"])
    best2, _ = CE.accept(item, {"close": cands["close"]}, min_r=0.999, min_countries=30)
    assert best2 is None


def test_wave_means_drop_missing_codes_and_weight():
    df = pd.DataFrame({"country": ["A", "A", "A", "B", "B"], "wave": [7] * 5,
                       "w": [1.0, 3.0, 1.0, 1.0, 1.0], "x": [1, 3, -2, 2, 4]})
    m = CE.wave_means(df, "x", wave=7, weight="w")
    assert m["A"] == pytest.approx((1 * 1 + 3 * 3) / 4) and m["B"] == pytest.approx(3.0)


def test_heldout_items_require_the_freeze(tmp_path):
    with pytest.raises(RuntimeError, match="BLOCKED"):
        CE.guard_items(["Q150"], strict_ids={"Q57"}, freeze_path=tmp_path / "FREEZE.json")
    assert CE.guard_items(["Q57"], strict_ids={"Q57"}, freeze_path=tmp_path / "FREEZE.json") == ["Q57"]


def test_hints_join_the_shortlist_but_still_face_the_identity_check():
    ts = {"E035": "Income equality", "E129B": "How much more foreign aid this country should give"}
    c = CE.candidates("Incomes should be made more equal", ts, k=1, hint=["E035"])
    assert "E035" in c and len(c) == 2
    ctry = [f"C{i}" for i in range(32)]
    item = pd.Series(np.linspace(1, 3, 32), index=ctry)
    best, _ = CE.accept(item, {"E035": -item}, min_r=0.999, min_countries=30)
    assert best is None                       # a wrong hint is rejected, not trusted


def test_surface_ceiling_uses_frozen_recodes_and_patience_split():
    rows = []
    for w in (6, 7):
        for i, cc in enumerate([f"C{j}" for j in range(12)]):
            # Q58 inverted 1-4: higher raw = less trust; identical ordering across waves
            rows += [{"country": cc, "item": "Q58", "wave": w, "mean": 1 + i * 0.2},
                     {"country": cc, "item": "Q43", "wave": w, "mean": 1 + i * 0.1},
                     {"country": cc, "item": "Q50", "wave": w, "mean": 10 - i * (0.5 if w == 6 else -0.5)}]
    out = CE.surface_ceiling(pd.DataFrame(rows), {"trust": ["Q58"], "patience": ["Q43", "Q50"]})
    out = out.set_index("surface")
    assert set(out.index) == {"trust", "patience:Q43", "patience:Q50"}
    assert out.loc["trust", "spearman_w6_w7"] == pytest.approx(1.0)
    assert out.loc["patience:Q50", "spearman_w6_w7"] == pytest.approx(-1.0)
    assert out.loc["trust", "n_countries"] == 12
