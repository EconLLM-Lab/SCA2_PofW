"""C8 persona analysis (design: planning/sprint_2026-10-11/paper-b-tier1/C8_PERSONA_DESIGN.md, sections 3-4)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_surface as AS  # noqa: E402
import bank2_transport as BT  # noqa: E402
import persona_strict as PS  # noqa: E402
import score_plan as SPL  # noqa: E402

REAL = BT.COHORT1_STRICT.is_file() and BT.ADAPTER_STRICT_V1.is_file() and PS.SIGNPROMPT_STRICT_64.is_file()


def _world(n=42, seed=0):
    rng = np.random.default_rng(seed)
    idx = [f"C{i:02d}" for i in range(n)]
    y = pd.Series(rng.normal(size=n), index=idx)
    clusters = pd.Series([f"p{i // 2}" for i in range(n)], index=idx)       # 21 blocks of two
    return idx, y, clusters


# ---- the paired contrast
def test_identical_columns_give_a_zero_difference_with_a_zero_interval():
    idx, y, cl = _world()
    a = y + pd.Series(np.random.default_rng(1).normal(size=len(idx)), index=idx)
    r = PS.paired_diff(a, a.copy(), y, clusters=cl, draws=300, seed=7)
    assert r["point"] == 0.0 and r["ci_lo"] == 0.0 and r["ci_hi"] == 0.0 and r["degenerate_draws"] == 0


def test_a_perfect_and_an_inverted_column_differ_by_two():
    idx, y, cl = _world()
    r = PS.paired_diff(y, -y, y, clusters=cl, draws=200, seed=7)
    assert r["point"] == pytest.approx(2.0) and r["ci_lo"] == pytest.approx(2.0) and r["ci_hi"] == pytest.approx(2.0)
    assert r["rho_a"] == pytest.approx(1.0) and r["rho_b"] == pytest.approx(-1.0)


@pytest.mark.parametrize("blocks", [True, False])
def test_each_column_inside_the_contrast_reproduces_the_shared_bootstrap(blocks):
    """Same seed, same clusters: the per-column intervals equal analyze_surface.bootstrap_spearman's."""
    idx, y, cl = _world(seed=3)
    rng = np.random.default_rng(4)
    a = 0.6 * y + pd.Series(rng.normal(size=len(idx)), index=idx)
    b = 0.2 * y + pd.Series(rng.normal(size=len(idx)), index=idx)
    clusters = cl if blocks else None
    r = PS.paired_diff(a, b, y, clusters=clusters, draws=400, seed=11)
    ra = AS.bootstrap_spearman(a, y, clusters=clusters, draws=400, seed=11)
    rb = AS.bootstrap_spearman(b, y, clusters=clusters, draws=400, seed=11)
    assert (r["rho_a"], r["rho_a_lo"], r["rho_a_hi"]) == (ra["point"], ra["ci_lo"], ra["ci_hi"])
    assert (r["rho_b"], r["rho_b_lo"], r["rho_b_hi"]) == (rb["point"], rb["ci_lo"], rb["ci_hi"])
    assert r["point"] == ra["point"] - rb["point"]


def test_the_contrast_refuses_misaligned_or_unclustered_rows():
    idx, y, cl = _world()
    with pytest.raises(ValueError):
        PS.paired_diff(y, y.iloc[1:], y, clusters=cl, draws=10, seed=1)          # a country missing from one route
    with pytest.raises(ValueError):
        PS.paired_diff(y, y, y, clusters=cl.iloc[1:], draws=10, seed=1)         # a country without a cluster


# ---- persona composites
def _persona_long(countries, items=("Q57", "Q58")):
    rows = []
    for cc in countries:
        for q in items:
            for code, p in (("1", 0.25), ("2", 0.75)):
                rows.append({"model": f"persona_{cc}", "question_id": q, "option_code": code, "model_prob": p})
    return pd.DataFrame(rows)


def test_persona_frame_takes_the_country_from_the_model_name():
    df = PS.persona_frame(_persona_long(SPL.PERSONA_COUNTRIES))
    assert set(df.eval_country) == set(SPL.PERSONA_COUNTRIES)
    assert (df.model.str.removeprefix("persona_") == df.eval_country).all()


def test_persona_frame_refuses_an_incomplete_or_foreign_file():
    with pytest.raises(ValueError, match="missing"):
        PS.persona_frame(_persona_long(SPL.PERSONA_COUNTRIES[1:]))
    bad = pd.concat([_persona_long(SPL.PERSONA_COUNTRIES), _persona_long(["ARG"]).assign(model="ARG_adapter")])
    with pytest.raises(ValueError, match="not a persona"):
        PS.persona_frame(bad)


# ---- the estimands on route tables
def _routes(idx, y, persona):
    rng = np.random.default_rng(5)
    noisy = {s: 0.7 * y + pd.Series(rng.normal(size=len(idx)), index=idx) for s in PS.SURFACES}
    tab = pd.DataFrame(noisy)
    return {"C1": tab, "B2": tab * 0.5, "SP": -tab, "P": persona}


def test_a_persona_equal_to_the_gps_has_rho_one_on_every_surface():
    idx, y, cl = _world()
    gps = pd.DataFrame({d: y for d in PS.GPS_DIMS})
    est = PS.estimates(_routes(idx, y, pd.DataFrame({s: y for s in PS.SURFACES})), gps, cl, draws=200, seed=3)
    for s in PS.SURFACES:
        assert est["E1"][s]["point"] == pytest.approx(1.0)
        assert est["E4"]["persona"][s]["point"] == pytest.approx(1.0)


def test_estimand_set_matches_the_design():
    idx, y, cl = _world()
    gps = pd.DataFrame({d: y for d in PS.GPS_DIMS})
    rng = np.random.default_rng(9)
    persona = pd.DataFrame({s: pd.Series(rng.normal(size=len(idx)), index=idx) for s in PS.SURFACES})
    est = PS.estimates(_routes(idx, y, persona), gps, cl, draws=100, seed=3)
    assert est["E2"]["route"] == "C1" and est["E2"]["surface"] == "trust" and est["E2"]["resampling"] == "profile-block"
    assert set(est["E3"]) == {"C1", "B2", "SP"}
    assert set(est["E3"]["C1"]) == set(PS.SURFACES) - {"trust"}
    assert set(est["E3"]["B2"]) == set(est["E3"]["SP"]) == set(PS.SURFACES)
    assert est["E4"]["E2_country_bootstrap"]["resampling"] == "country"
    assert est["E2"]["reading"] in {"adapters closer", "persona closer", "unresolved"}


def test_reading_rule():
    assert PS.reading(0.1, 0.5) == "adapters closer"
    assert PS.reading(-0.5, -0.1) == "persona closer"
    assert PS.reading(-0.1, 0.5) == "unresolved"
    assert PS.reading(float("nan"), 0.5) == "unresolved"


def test_development_panel_is_the_preprint_sixteen():
    assert PS.DEV16 == ["CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS",
                        "IND", "IDN", "NGA", "EGY", "TUR", "NLD", "BRA", "GRC"]
    assert set(PS.DEV16) <= set(SPL.PERSONA_COUNTRIES)


# ---- replay on the banked inputs (design section 4); the persona column is a relabelled cohort-1 file here
@pytest.mark.skipif(not REAL, reason="banked strict inputs not on this machine")
def test_replay_reproduces_the_banked_c3_rows_and_a_cohort1_persona_gives_zero(tmp_path):
    c1 = pd.read_csv(BT.COHORT1_STRICT, dtype={"option_code": str, "question_id": str})
    fake = c1.assign(model="persona_" + c1["eval_country"]).drop(columns=["eval_country"])
    p = tmp_path / "persona_from_cohort1.csv"
    fake.to_csv(p, index=False)
    res = PS.run(persona_path=p, draws=2000)
    checks = PS.replay_checks(res)
    assert checks["all_pass"], checks
    assert res["E2"]["point"] == 0.0 and res["E2"]["ci_lo"] == 0.0 and res["E2"]["ci_hi"] == 0.0
    for s in PS.SURFACES:
        assert res["E1"][s]["point"] == res["routes_vs_gps"]["C1"][s]["point"]
