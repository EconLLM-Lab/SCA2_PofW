"""analyze_near_zero tests on synthetic scorer output (no GPU, no Hub, no human data).

The C6 object is the predeclared near-zero refit. `C6_DESIGN.md` section 9 fixes the
comparison: for block R (surfaces whose dimension stays in training) the primary contrast
is (refit composite - size-matched control composite) / SD over the 64 profile composites;
refit - baseline and control - baseline are reported beside it for every surface. The C6
reading (section 9, item 5) is applied to the block-R imprint surfaces only, against the
replicate's |delta| on the same surface as the noise floor.

These tests pin: the composite/SD arithmetic, the block and imprint labels, the intended
direction, the noise floor, the reading rule (including that block D never drives the
decision), and the local-only invariant (no network, no human data).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "heldout"))
import analyze_factorial as AF  # noqa: E402
import analyze_near_zero as NZ  # noqa: E402
import analyze_surface as AS  # noqa: E402
import factorial as F  # noqa: E402
from ceiling import surface_items  # noqa: E402

GBR = "P_1_1_1_1_0_1"
COL = "P_1_0_0_1_1_0"
DROP = {"GBR": ["altruism", "negrecip", "posrecip", "risktaking"],
        "COL": ["altruism", "risktaking", "trust"]}
PROFILE = {"GBR": GBR, "COL": COL}
SURFACES = tuple(surface_items(AS.STRICT_ITEMS))


def _profile_frame(shift=0.0, seed=0, units=None):
    """64 (or fewer) sign profiles x the 23 strict items; each bit tilts its own dimension."""
    rng = np.random.default_rng(seed)
    item_dim = {q: d for d, qs in AS.STRICT_ITEMS.items() for q in qs}
    rows = []
    for u in (units or F.all_units()):
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


def _unit_frame(unit, shift=0.0, seed=0):
    """One unit, no eval_country column -- the shape the near-zero score CSVs have."""
    return _profile_frame(shift=shift, seed=seed, units=[unit]).drop(columns=["eval_country"])


# ------------------------------------------------------------------------- selection
def test_with_country_derives_the_unit_from_the_model_name():
    f = _unit_frame(GBR, seed=1)
    assert "eval_country" not in f.columns
    g = NZ.with_country(f)
    assert set(g.eval_country) == {GBR}
    # an existing eval_country is left alone
    h = NZ.with_country(_profile_frame(seed=1, units=[GBR]))
    assert set(h.eval_country) == {GBR}


def test_surface_composites_matches_the_frozen_factorial_recomputation():
    f = _unit_frame(GBR, shift=0.3, seed=4)
    got = NZ.surface_composites(f)
    exp = (AF.unit_composites(NZ.with_country(f)).set_index("surface").composite)
    assert set(got.index) == set(SURFACES)
    for s in SURFACES:
        assert got[s] == pytest.approx(exp[s], rel=1e-12)


def test_surface_composites_refuses_a_unit_missing_a_surface():
    f = _unit_frame(GBR, seed=1)
    f = f[f.question_id != "Q81"]  # drops the whole posrecip surface
    with pytest.raises(ValueError, match="posrecip"):
        NZ.surface_composites(f)


# --------------------------------------------------------------------------- SD units
def test_sd_over_profiles_is_the_ddof1_spread_of_the_64_composites():
    base = _profile_frame(seed=7)
    got = NZ.sd_over_profiles(base)
    exp = (AF.unit_composites(base).pivot(index="unit", columns="surface", values="composite")
           .std(ddof=1))
    assert set(got.index) == set(SURFACES)
    for s in SURFACES:
        assert got[s] == pytest.approx(exp[s], rel=1e-12)


def test_sd_over_profiles_refuses_when_the_frame_is_not_the_64():
    with pytest.raises(ValueError, match="64"):
        NZ.sd_over_profiles(_profile_frame(seed=7, units=[GBR, COL]))


# ------------------------------------------------------------------------ direction
def test_intended_direction_reads_the_profiles_own_bit():
    assert NZ.intended_direction(GBR, "trust") == "up"        # trust bit 1
    assert NZ.intended_direction(GBR, "posrecip") == "down"   # posrecip bit 0
    assert NZ.intended_direction(COL, "posrecip") == "up"     # posrecip bit 1
    assert NZ.intended_direction(COL, "patience:Q43") == "down"
    assert NZ.intended_direction(COL, "patience:Q50") == "down"
    assert NZ.intended_direction(COL, "negrecip") == "down"
    assert NZ.intended_direction(COL, "trust") == "up"


# ----------------------------------------------------------------------------- table
def _table(seed=7, shift=0.5, control_shift=0.0):
    base = _profile_frame(seed=seed)
    refit = {cc: _unit_frame(PROFILE[cc], shift=shift, seed=100 + i)
             for i, cc in enumerate(("GBR", "COL"))}
    control = {cc: _unit_frame(PROFILE[cc], shift=control_shift, seed=200 + i)
               for i, cc in enumerate(("GBR", "COL"))}
    return NZ.near_zero_table(countries=["GBR", "COL"], refit=refit, control=control,
                              baseline64=base, dropped_by_country=DROP, profile_by_country=PROFILE)


def test_table_labels_the_block_and_the_imprint_surfaces():
    t = _table().set_index(["country", "surface"])
    assert t.loc[("GBR", "trust"), "block"] == "R"          # trust kept for GBR
    assert t.loc[("GBR", "posrecip"), "block"] == "D"       # posrecip dropped for GBR
    assert t.loc[("COL", "posrecip"), "block"] == "R"       # posrecip kept for COL
    assert t.loc[("COL", "trust"), "block"] == "D"          # trust dropped for COL
    assert t.loc[("GBR", "altruism"), "block"] == "D"
    assert t.loc[("COL", "negrecip"), "block"] == "R"
    for cc in ("GBR", "COL"):
        for s in NZ.IMPRINT_SURFACES:
            assert bool(t.loc[(cc, s), "imprint"]) is True
    assert bool(t.loc[("GBR", "negrecip"), "imprint"]) is False
    assert bool(t.loc[("COL", "patience:Q50"), "imprint"]) is False
    assert len(t) == 2 * len(SURFACES)


def test_table_deltas_are_in_sd_units_of_the_64_profile_composites():
    base = _profile_frame(seed=7)
    refit = _unit_frame(GBR, shift=0.5, seed=11)
    control = _unit_frame(GBR, shift=0.0, seed=12)
    t = NZ.near_zero_table(countries=["GBR"], refit={"GBR": refit}, control={"GBR": control},
                           baseline64=base, dropped_by_country={"GBR": DROP["GBR"]},
                           profile_by_country={"GBR": GBR}).set_index("surface")
    sd = NZ.sd_over_profiles(base)
    r = NZ.surface_composites(refit)
    c = NZ.surface_composites(control)
    b = NZ.baseline_composites(base).loc[GBR]
    for s in SURFACES:
        assert t.loc[s, "refit_minus_control_sd"] == pytest.approx((r[s] - c[s]) / sd[s], rel=1e-12)
        assert t.loc[s, "refit_minus_baseline_sd"] == pytest.approx((r[s] - b[s]) / sd[s], rel=1e-12)
        assert t.loc[s, "control_minus_baseline_sd"] == pytest.approx((c[s] - b[s]) / sd[s], rel=1e-12)


def test_against_sign_flags_the_primary_contrast_pointed_the_wrong_way():
    base = _profile_frame(seed=7)
    # GBR intends trust up; a refit that is far below its control points against
    refit = _unit_frame(GBR, shift=-0.9, seed=11)
    control = _unit_frame(GBR, shift=0.0, seed=12)
    t = NZ.near_zero_table(countries=["GBR"], refit={"GBR": refit}, control={"GBR": control},
                           baseline64=base, dropped_by_country={"GBR": DROP["GBR"]},
                           profile_by_country={"GBR": GBR}).set_index("surface")
    assert bool(t.loc["trust", "against_sign"]) is True
    assert t.loc["trust", "intended_direction"] == "up"


# ---------------------------------------------------------------------- noise floor
def test_noise_floor_is_the_absolute_replicate_difference(tmp_path):
    p = tmp_path / "replicate_surface_diff.csv"
    pd.DataFrame({"surface": ["trust", "negrecip"], "diff_sd": [-0.0249, 0.0335]}).to_csv(
        p, index=False)
    s = NZ.noise_floor(p)
    assert s["trust"] == pytest.approx(0.0249) and s["negrecip"] == pytest.approx(0.0335)


def _annotated(rows, noise):
    base = _profile_frame(seed=7)
    refit = {cc: _unit_frame(PROFILE[cc], shift=shift, seed=100 + i)
             for i, (cc, shift) in enumerate(rows)}
    control = {cc: _unit_frame(PROFILE[cc], shift=0.0, seed=200 + i)
               for i, (cc, _) in enumerate(rows)}
    t = NZ.near_zero_table(countries=[cc for cc, _ in rows], refit=refit, control=control,
                           baseline64=base, dropped_by_country={cc: DROP[cc] for cc, _ in rows},
                           profile_by_country={cc: PROFILE[cc] for cc, _ in rows})
    return NZ.apply_noise(t, noise)


def _reading_table(rows):
    """A hand-built annotated table: one row per (country, surface) in `rows`."""
    recs = []
    for country, surface, block, imprint, direction, delta in rows:
        sd_unit = 1.0
        recs.append({"country": country, "profile_unit": PROFILE[country], "surface": surface,
                     "dimension": NZ.SURFACE_DIM[surface], "block": block, "imprint": imprint,
                     "intended_direction": direction, "refit_composite": 0.0, "control_composite": 0.0,
                     "baseline_composite": 0.0, "sd_over_64_profiles": sd_unit,
                     "refit_minus_control": delta, "refit_minus_control_sd": delta,
                     "refit_minus_baseline_sd": delta, "control_minus_baseline_sd": 0.0,
                     "against_sign": (delta > 0) if direction == "down" else (delta < 0)})
    return pd.DataFrame(recs)


def test_reading_says_do_not_promote_when_a_retained_imprint_moves_against_beyond_the_floor():
    t = _reading_table([("GBR", "trust", "R", True, "up", -0.05)])
    noise = pd.Series({"trust": 0.0249})
    out = NZ.c6_reading(NZ.apply_noise(t, noise), noise_known=True)
    assert out["decision"] == NZ.DO_NOT_PROMOTE
    row = out["block_r_imprint"][0]
    assert row["against_intended"] is True and row["beyond_floor"] is True


def test_reading_keeps_the_footnote_when_nothing_retained_moves_against_beyond_the_floor():
    t = _reading_table([("GBR", "trust", "R", True, "up", -0.01),
                        ("COL", "posrecip", "R", True, "up", 0.02)])
    noise = pd.Series({"trust": 0.0249, "posrecip": 0.0114})
    out = NZ.c6_reading(NZ.apply_noise(t, noise), noise_known=True)
    assert out["decision"] == NZ.FOOTNOTE
    assert all(r["against_intended"] is False for r in out["block_r_imprint"])


def test_a_move_within_the_noise_floor_is_not_counted():
    t = _reading_table([("GBR", "trust", "R", True, "up", -0.010)])   # |0.010| < 0.0249
    noise = pd.Series({"trust": 0.0249})
    out = NZ.c6_reading(NZ.apply_noise(t, noise), noise_known=True)
    assert out["block_r_imprint"][0]["beyond_floor"] is False
    assert out["decision"] == NZ.FOOTNOTE


def test_block_d_never_drives_the_decision():
    # a dropped imprint surface moves far against, but no retained imprint surface does
    t = _reading_table([("GBR", "trust", "R", True, "up", 0.005),
                        ("GBR", "altruism", "D", True, "up", -0.60),
                        ("COL", "trust", "D", True, "up", -0.55)])
    noise = pd.Series({"trust": 0.0249, "altruism": 0.0079})
    out = NZ.c6_reading(NZ.apply_noise(t, noise), noise_known=True)
    assert out["decision"] == NZ.FOOTNOTE
    assert len(out["block_r_imprint"]) == 1


def test_unknown_noise_floor_claims_no_direction():
    t = _reading_table([("GBR", "trust", "R", True, "up", -0.05)])
    out = NZ.c6_reading(NZ.apply_noise(t, None), noise_known=False)
    assert out["decision"] == NZ.NOISE_UNKNOWN
    assert out["noise_floor_known"] is False


# -------------------------------------------------------------------------- assembly
def test_analyse_writes_the_table_and_the_reading(tmp_path):
    base = _profile_frame(seed=7)
    refit = {cc: _unit_frame(PROFILE[cc], shift=0.5, seed=11 + i) for i, cc in enumerate(("GBR", "COL"))}
    control = {cc: _unit_frame(PROFILE[cc], shift=0.0, seed=21 + i) for i, cc in enumerate(("GBR", "COL"))}
    manifests = {cc: {"country": cc, "profile_unit": PROFILE[cc],
                      "near_zero_dimensions": DROP[cc]} for cc in ("GBR", "COL")}
    noise = pd.Series({s: 0.01 for s in SURFACES})
    out = NZ.analyse(countries=["GBR", "COL"], refit=refit, control=control, manifests=manifests,
                     baseline64=base, noise=noise, results_dir=tmp_path)
    assert len(out["table"]) == 2 * len(SURFACES)
    assert "decision" in out["reading"] and "block_r_imprint" in out["reading"]
    assert (tmp_path / "near_zero_table.csv").is_file()
    assert (tmp_path / "near_zero_analysis.json").is_file()


# ------------------------------------------------------------- local-only invariants
def test_module_makes_no_network_call():
    """Rule 3/4: the analysis is local-only -- no Hub client, no HTTP, no human means."""
    tree = ast.parse((HERE / "analyze_near_zero.py").read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert mods & {"huggingface_hub", "requests", "urllib"} == set(), sorted(mods)
