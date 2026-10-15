"""analyze_factorial tests on synthetic scorer output (no GPU, no human data)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_factorial as AF  # noqa: E402
import analyze_surface as AS  # noqa: E402
import factorial as F  # noqa: E402

OWN = {"trust": "trust", "patience": "patience", "risktaking": "risktaking",
       "posrecip": "posrecip", "negrecip": "negrecip", "altruism": "altruism"}


def _probs(shift=0.0, seed=0):
    """Each unit tilts the items of a dimension toward its high end iff that bit is 1."""
    rng = np.random.default_rng(seed)
    rows = []
    item_dim = {q: d for d, qs in AS.STRICT_ITEMS.items() for q in qs}
    for u in F.all_units():
        bits = dict(zip(F.DIMS, F.bits_of_unit(u)))
        for q in AS.all_strict_items():
            dom = AS._domain(q)
            hi = np.array([AS.recode_value(float(c), q) for c in dom])
            w = np.exp((0.8 * bits[item_dim[q]] + shift) * (hi - hi.mean()) / (hi.std() + 1e-9)
                       + 0.05 * rng.normal(size=len(dom)))
            p = w / w.sum()
            for c, pi in zip(dom, p):
                rows.append({"model": f"{u}_adapter", "eval_country": u, "question_id": q,
                             "option_code": c, "model_prob": float(pi)})
    return pd.DataFrame(rows)


def test_unit_composites_cover_64_units_and_7_surfaces():
    comp = AF.unit_composites(_probs())
    assert comp.unit.nunique() == 64 and comp.surface.nunique() == 7


def test_planted_factorial_is_diagonal():
    m, cells, dd = AF.mtmm(AF.unit_composites(_probs()))
    assert m.shape == (6, 7) and dd["hits"] == 6
    assert (cells[cells.dimension == cells.surface.str.split(":").str[0]].t > 5).all()


def test_readout_variant_deviation_zero_for_identity_and_positive_for_shift():
    v1 = AF.unit_composites(_probs())
    out = AF.readout_variants(v1, {"same": v1, "shifted": AF.unit_composites(_probs(shift=0.3))})
    assert (out[out.variant == "same"].max_abs_dev == 0).all()
    assert (out[out.variant == "shifted"].max_abs_dev > 0).all()


def test_cohort1_cells_average_sign_mates(tmp_path):
    gps = {"AAA": {d: 1.0 for d in F.DIMS}, "BBB": {d: 0.5 for d in F.DIMS},
           "CCC": {d: -1.0 for d in F.DIMS}}
    p = tmp_path / "gps.json"
    p.write_text(json.dumps(gps))
    comp = pd.DataFrame([{"unit": cc, "surface": "trust", "composite": v}
                         for cc, v in (("AAA", 1.0), ("BBB", 3.0), ("CCC", 5.0))])
    cells = AF.cohort1_cells(comp, p).set_index("unit").composite
    assert cells["P_1_1_1_1_1_1"] == 2.0 and cells["P_0_0_0_0_0_0"] == 5.0
