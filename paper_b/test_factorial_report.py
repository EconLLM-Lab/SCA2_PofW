"""Tests for the additive 64-cell route-contrast block in paper_b/factorial_report.py.

Written test-first by kanban card T6 in its scratch folder (its write boundary named no test file) and
moved into the repository by the orchestrator so it survives scratch pruning.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "paper_b"))
sys.path.insert(0, str(REPO / "paper_b" / "heldout"))
import factorial as F  # noqa: E402
import factorial_report as FR  # noqa: E402

SURFACES = (("trust", "trust"), ("risktaking", "risktaking"), ("posrecip", "posrecip"),
            ("altruism", "altruism"), ("patience:Q43", "patience"), ("patience:Q50", "patience"),
            ("negrecip", "negrecip"))


def _planted(noise=0.1, seed=0, effect=3.0, driver=None):
    """driver=None: each surface follows its own bit (diagonal). driver='trust': one common bit."""
    rng = np.random.default_rng(seed)
    rows = []
    for u in F.all_units():
        bits = dict(zip(F.DIMS, F.bits_of_unit(u)))
        for surface, dim in SURFACES:
            b = bits[driver or dim]
            rows.append({"unit": u, "surface": surface,
                         "composite": 10.0 + effect * b + noise * rng.normal()})
    return pd.DataFrame(rows)


def test_route_contrast_64_reports_both_routes_and_the_sign_of_every_own_effect(tmp_path):
    out = FR.route_contrast_64(_planted(seed=1), _planted(seed=2), tmp_path)
    assert out["n_cells"] == 64
    for route in ("adapter", "signprompt"):
        blk = out[route]
        assert blk["plan_V5_rowwise_raw"]["hits"] == 6            # planted: diagonal
        assert blk["plan_V5_rowwise_raw"]["per_dimension"]["trust"] is True
        assert blk["columnwise"]["n"] == 7 and blk["columnwise"]["hits"] == 7
        diag = blk["diagonal"]
        assert len(diag) == 7                                     # one own effect per surface
        for s, e in diag.items():
            assert e["sign"] == 1 and e["beta"] > 0
            assert e["t"] > 5 and "t_lenth" in e
        assert 1 / 7 - 1e-9 <= blk["general_factor"]["pc1_share"] <= 0.5
    assert (tmp_path / "route64_adapter_standardized.csv").is_file()
    assert (tmp_path / "route64_signprompt_standardized.csv").is_file()


def test_general_factor_is_one_when_every_surface_follows_one_common_bit(tmp_path):
    out = FR.route_contrast_64(_planted(seed=3, driver="trust"),
                               _planted(seed=4, driver="trust"), tmp_path)
    for route in ("adapter", "signprompt"):
        blk = out[route]
        assert blk["general_factor"]["pc1_share"] > 0.9
        assert blk["columnwise"]["hits"] == 1                     # only trust's own bit moves


def test_diag_keeps_the_26_cell_shape_when_sign_is_not_requested():
    """The 26-cell block must not change: no 'sign' key unless asked for."""
    m = pd.DataFrame(np.ones((6, 7)), index=F.DIMS, columns=[s for s, _ in SURFACES])
    assert "sign" not in next(iter(FR.diag(m, m, m).values()))
    assert next(iter(FR.diag(m, m, m, with_sign=True).values()))["sign"] == 1


def test_signprompt_units_normalises_both_profile_id_styles(tmp_path):
    """The 26-cell file writes '0_0_0_0_0_0'; the 64-cell file writes 'P_0_0_0_0_0_0'."""
    import analyze_surface as AS
    dom = AS._domain("Q43")
    rows = [{"model": "sign_prompt", "profile_id": pid, "question_id": "Q43",
             "option_code": c, "model_prob": p}
            for pid in ("0_0_0_0_0_0", "P_1_1_1_1_1_1")
            for c, p in zip(dom, (0.5, 0.3, 0.2))]
    f = tmp_path / "sp.csv"
    pd.DataFrame(rows).to_csv(f, index=False)
    comp = FR.signprompt_units(f)
    assert set(comp.unit) == {"P_0_0_0_0_0_0", "P_1_1_1_1_1_1"}
