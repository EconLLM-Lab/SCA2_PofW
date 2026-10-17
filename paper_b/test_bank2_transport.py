"""Tests for paper_b/bank2_transport.py (T2, checkpoint C3).

Logic tests run on small synthetic frames. The two integration tests read the
synthetic score files named on card T2 (they contain no human data); they skip
cleanly when those files are absent, so the suite still runs on a bare checkout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_surface as AS  # noqa: E402
import bank2_transport as BT  # noqa: E402
import factorial as F  # noqa: E402


# --------------------------------------------------------------- pure logic
def test_country_units_follow_unit_of_z():
    raw = {"AAA": {d: 1.0 for d in F.DIMS}, "BBB": {d: -1.0 for d in F.DIMS}}
    raw["AAA"]["negrecip"] = -2.0  # one negative bit
    units = BT.country_units(raw, ["AAA", "BBB"])
    assert units["AAA"] == F.unit_of_z(raw["AAA"])
    assert units["BBB"] == "P_0_0_0_0_0_0"
    assert units["AAA"].startswith("P_1_1_1_1_1_0")


def test_unit_series_repeats_within_a_cell():
    comp = pd.DataFrame([
        {"unit": "P_1_1_1_1_1_1", "surface": "trust", "composite": 2.0},
        {"unit": "P_0_0_0_0_0_0", "surface": "trust", "composite": 5.0},
    ])
    units = pd.Series({"AAA": "P_1_1_1_1_1_1", "BBB": "P_1_1_1_1_1_1", "CCC": "P_0_0_0_0_0_0"})
    s = BT.unit_series(comp, "trust", units)
    assert s["AAA"] == s["BBB"] == 2.0
    assert s["CCC"] == 5.0


def test_unit_series_raises_on_missing_unit():
    comp = pd.DataFrame([{"unit": "P_1_1_1_1_1_1", "surface": "trust", "composite": 2.0}])
    units = pd.Series({"AAA": "P_0_0_0_0_0_0"})
    with pytest.raises(ValueError):
        BT.unit_series(comp, "trust", units)


def test_bootstrap_cell_corr_is_deterministic_and_brackets_the_point():
    x = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
    y = pd.Series([0.0, 1.1, 1.9, 3.2, 3.8, 5.1, 5.9, 7.2, 7.8, 9.1])
    a = BT.bootstrap_cell_corr(x, y, draws=500, seed=20261011)
    b = BT.bootstrap_cell_corr(x, y, draws=500, seed=20261011)
    assert a == b  # same seed -> identical dict
    assert a["n_cells"] == 10
    assert a["pearson_lo"] <= a["pearson"] <= a["pearson_hi"]
    assert a["spearman_lo"] <= a["spearman"] <= a["spearman_hi"]
    assert a["pearson"] > 0.99


def test_bootstrap_cell_corr_counts_degenerate_draws():
    # five cells, one variable constant -> every draw is degenerate for Spearman
    x = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0])
    y = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    r = BT.bootstrap_cell_corr(x, y, draws=50, seed=20261011)
    assert r["degenerate_draws"] == 50
    assert np.isnan(r["spearman"])


def test_c3_reading_holds_drops_or_reports():
    assert BT.c3_reading("trust", {"ci_lo": 0.61, "ci_hi": 0.88}) == "transport holds"
    assert BT.c3_reading("risktaking",
                         {"ci_lo": -0.20, "ci_hi": 0.58}) == "transport dropped: interval includes 0"
    assert BT.c3_reading("negrecip",
                         {"ci_lo": -0.24, "ci_hi": 0.60}) == "reported (not an imprint dimension)"
    # an interval lying wholly below zero still "holds" (a sign flip is still transport)
    assert BT.c3_reading("posrecip", {"ci_lo": -0.9, "ci_hi": -0.3}) == "transport holds"


# ------------------------------------------------------- integration (real inputs)
needs_inputs = pytest.mark.skipif(
    not (BT.COHORT1_STRICT.exists() and BT.ADAPTER_STRICT_V1.exists()),
    reason="card T2 synthetic score files are not present on this machine")


@needs_inputs
def test_reproduction_matches_the_banked_cohort1_run():
    res = BT.run(draws=BT.DRAWS, seed=BT.SEED)
    c1 = res["cohort1_adapter_gps"]
    trust = c1["trust"]
    assert trust["n"] == 42
    assert trust["point"] == pytest.approx(0.7441, abs=1e-3)
    assert trust["ci_lo"] == pytest.approx(0.5002, abs=1e-2)
    assert trust["ci_hi"] == pytest.approx(0.8648, abs=1e-2)
    # journey C0: the four imprint dimensions all exclude 0 on cohort 1
    for surf in BT.IMPRINT:
        r = c1[surf]
        assert r["ci_lo"] > 0 or r["ci_hi"] < 0, surf


@needs_inputs
def test_bank2_series_covers_the_42_countries_over_26_cells():
    res = BT.run(draws=BT.DRAWS, seed=BT.SEED)
    for surf, r in res["bank2_adapter_gps"].items():
        assert r["n"] == 42, surf
        assert r["degenerate_draws"] == 0, surf
    assert res["n_cells"] == 26


@needs_inputs
def test_bank_to_bank_points_reproduce_the_committed_robustness_table():
    committed = pd.read_csv(BT.OUT_DIR / "factorial" / "bank_robustness.csv").set_index("surface")
    res = BT.run(draws=BT.DRAWS, seed=BT.SEED)
    for surf, r in res["bank_to_bank"].items():
        assert r["n_cells"] == 26
        assert r["pearson"] == pytest.approx(float(committed.loc[surf, "pearson"]), abs=1e-9)
        assert r["spearman"] == pytest.approx(float(committed.loc[surf, "spearman"]), abs=1e-9)
        assert r["pearson_lo"] <= r["pearson"] <= r["pearson_hi"]
        assert r["spearman_lo"] <= r["spearman"] <= r["spearman_hi"]


@needs_inputs
def test_outputs_are_written_with_the_two_required_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(BT, "OUT_DIR", tmp_path)
    code = BT.main(["--out-dir", str(tmp_path)])
    assert code == 0
    js = json.loads((tmp_path / BT.JSON_NAME).read_text())
    md = (tmp_path / BT.MD_NAME).read_text()
    assert len(js["surfaces_table"]) == 7
    assert len(js["bank_to_bank_table"]) == 7
    assert js["c3_pass"]["imprint"] == ["trust", "risktaking", "posrecip", "altruism"]
    assert "| Surface |" in md and "| Bank-to-bank |" in md
