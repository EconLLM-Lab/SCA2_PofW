"""C9-2: the 2x2 TVD analysis (base, adapter, persona, adapter+persona) on the 42 cohort countries."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_surface as AS  # noqa: E402
import c9_tvd as T  # noqa: E402

LOCAL = T.COHORT1_DIR / "local_eval"
REAL = (T.MODEL_PROBS.is_file() and T.HUMAN_DISTS.is_file() and T.METRICS_ALL.is_file()
        and T.PERSONA_STRICT.is_file())
needs_real = pytest.mark.skipif(not REAL, reason="local-only human data or score files absent")


def _scores(country, item, probs, model="m"):
    codes = [str(i + 1) for i in range(len(probs))]
    return pd.DataFrame({"model": model, "eval_country": country, "question_id": item,
                         "option_code": codes, "model_prob": probs})


def _human(country, item, probs):
    codes = [str(i + 1) for i in range(len(probs))]
    return pd.DataFrame({"eval_country": country, "question_id": item, "option_code": codes,
                         "human_prob": probs})


# ---- the cell TVD
def test_cell_tvd_is_half_the_l1_distance():
    s = _scores("AAA", "Q43", [0.5, 0.3, 0.2])
    h = _human("AAA", "Q43", [0.2, 0.3, 0.5])
    t, skipped = T.cell_tvd(s, h)
    assert skipped == []
    assert t.loc[0, "tvd"] == pytest.approx(0.3)


def test_cell_with_no_human_distribution_is_skipped_and_listed():
    s = pd.concat([_scores("AAA", "Q43", [0.5, 0.5]), _scores("JOR", "Q178", [0.5, 0.5])])
    h = _human("AAA", "Q43", [1.0, 0.0])
    t, skipped = T.cell_tvd(s, h)
    assert list(t.country) == ["AAA"]
    assert skipped == [("JOR", "Q178")]


def test_model_option_missing_from_human_counts_as_zero_human_mass():
    s = _scores("AAA", "Q43", [0.25, 0.25, 0.5])
    h = _human("AAA", "Q43", [0.5, 0.5])  # no mass on code 3
    t, _ = T.cell_tvd(s, h)
    assert t.loc[0, "tvd"] == pytest.approx(0.5)


def test_probabilities_that_do_not_sum_to_one_are_rejected():
    s = _scores("AAA", "Q43", [0.5, 0.3])
    h = _human("AAA", "Q43", [0.5, 0.5])
    with pytest.raises(ValueError):
        T.cell_tvd(s, h)


# ---- aggregation
def _tvd(rows):
    return pd.DataFrame(rows, columns=["country", "item", "tvd"])


def test_country_equal_mean_differs_from_the_pooled_cell_mean_when_unbalanced():
    t = _tvd([("A", "Q43", 0.2), ("A", "Q50", 0.2), ("A", "Q57", 0.2), ("B", "Q43", 0.8)])
    assert T.country_equal_mean(t) == pytest.approx(0.5)
    assert T.pooled_mean(t) == pytest.approx(0.35)


def test_dimension_means_are_country_equal_within_dimension():
    t = _tvd([("A", "Q57", 0.1), ("A", "Q58", 0.3), ("B", "Q57", 0.5), ("A", "Q43", 0.9)])
    d = T.dimension_means(t)
    assert d["trust"] == pytest.approx((0.2 + 0.5) / 2)
    assert d["patience"] == pytest.approx(0.9)
    assert "risktaking" not in d


def test_every_battery_item_belongs_to_exactly_one_dimension():
    items = AS.all_strict_items()
    assert len(items) == 23
    assert sorted(T.ITEM_DIM) == sorted(items)


# ---- bootstrap
def _units(n=12, block=2):
    idx = [f"C{i:02d}" for i in range(n)]
    return idx, pd.Series([f"p{i // block}" for i in range(n)], index=idx)


def test_constant_difference_has_a_zero_width_interval():
    idx, cl = _units()
    r = T.bootstrap_mean(pd.Series(0.1, index=idx), cl, draws=200, seed=1)
    assert r["point"] == pytest.approx(0.1)
    assert r["ci_lo"] == pytest.approx(0.1) and r["ci_hi"] == pytest.approx(0.1)


def test_bootstrap_is_reproducible_and_labels_its_resampling_unit():
    idx, cl = _units()
    v = pd.Series(np.arange(12.0), index=idx)
    a = T.bootstrap_mean(v, cl, draws=300, seed=7)
    b = T.bootstrap_mean(v, cl, draws=300, seed=7)
    assert a == b and a["unit"] == "profile_block"
    assert T.bootstrap_mean(v, None, draws=300, seed=7)["unit"] == "country"


def test_profile_blocks_move_together():
    # two blocks; block p0 values 0, block p1 values 10: every resample mean is 0, 5 or 10
    idx = ["a", "b", "c", "d"]
    cl = pd.Series(["p0", "p0", "p1", "p1"], index=idx)
    v = pd.Series([0.0, 0.0, 10.0, 10.0], index=idx)
    r = T.bootstrap_mean(v, cl, draws=500, seed=3)
    assert r["ci_lo"] == 0.0 and r["ci_hi"] == 10.0
    assert r["point"] == 5.0


def test_missing_cluster_id_is_an_error():
    v = pd.Series([1.0, 2.0], index=["a", "b"])
    with pytest.raises(ValueError):
        T.bootstrap_mean(v, pd.Series(["p0"], index=["a"]), draws=10, seed=1)


# ---- paired contrasts
def test_contrast_requires_the_same_support():
    a = _tvd([("A", "Q43", 0.5), ("A", "Q50", 0.5)])
    b = _tvd([("A", "Q43", 0.1)])
    with pytest.raises(ValueError):
        T.paired_country_differences(a, b)


def test_paired_differences_are_country_means_of_the_cell_differences():
    a = _tvd([("A", "Q43", 0.5), ("A", "Q50", 0.7), ("B", "Q43", 0.2)])
    b = _tvd([("A", "Q43", 0.4), ("A", "Q50", 0.4), ("B", "Q43", 0.5)])
    d = T.paired_country_differences(a, b)
    assert d["A"] == pytest.approx(0.2) and d["B"] == pytest.approx(-0.3)


# ---- country recovery from model names
def test_country_from_model_name():
    c = ["ARG", "USA", "GBR"]
    assert T.country_of_model("persona_ARG", c) == "ARG"
    assert T.country_of_model("USA_adapter_persona", c) == "USA"
    assert T.country_of_model("adapter_persona_GBR", c) == "GBR"
    with pytest.raises(ValueError):
        T.country_of_model("ARG_USA", c)
    with pytest.raises(ValueError):
        T.country_of_model("persona_XYZ", c)


# ---- the fourth cell fills without code changes
def _toy_world(tmp_path, with_fourth):
    countries = [f"C{i:02d}" for i in range(8)]
    items = ["Q57", "Q58"]
    rng = np.random.default_rng(0)

    def draw(model_name, shift):
        rows = []
        for c in countries:
            for q in items:
                p = rng.dirichlet(np.ones(2) + shift)
                for k, pk in enumerate(p):
                    rows.append({"model": model_name(c), "eval_country": c, "question_id": q,
                                 "option_code": str(k + 1), "model_prob": pk})
        return pd.DataFrame(rows)

    hum = []
    for c in countries:
        for q in items:
            p = rng.dirichlet(np.ones(2))
            for k, pk in enumerate(p):
                hum.append({"eval_country": c, "question_id": q, "option_code": str(k + 1),
                            "human_prob": pk})
    cells = {"base": draw(lambda c: "base", 0), "adapter": draw(lambda c: "adapter", 1),
             "persona": draw(lambda c: f"persona_{c}", 2)}
    if with_fourth:
        cells["adapter_persona"] = draw(lambda c: f"{c}_adapter_persona", 3)
    clusters = pd.Series([f"p{i // 2}" for i in range(8)], index=countries)
    return countries, cells, pd.DataFrame(hum), clusters


@pytest.mark.parametrize("with_fourth", [False, True])
def test_summarize_marks_the_fourth_cell_pending_then_fills_it(tmp_path, with_fourth):
    countries, cells, human, clusters = _toy_world(tmp_path, with_fourth)
    res = T.summarize(cells, human, clusters, gps_trust=None, draws=50)
    assert set(res["cells"]) == set(T.CELLS)
    ap = res["cells"]["adapter_persona"]
    if with_fourth:
        assert ap["status"] == "ok" and np.isfinite(ap["mean_tvd_country_equal"])
        assert "interaction" in res["contrasts"]
    else:
        assert ap["status"] == "pending"
        assert "interaction" not in res["contrasts"]
        assert {"adapter_minus_base", "persona_minus_base"} <= set(res["contrasts"])
    for c in res["contrasts"].values():
        assert c["label"].startswith("DESCRIPTIVE / NOT PREREGISTERED")


# ---- real data (local only)
@needs_real
def test_base_cell_reproduces_the_banked_question_metrics():
    probs = T.load_cohort1_scores()
    human = T.load_human(T.HUMAN_DISTS)
    t, skipped = T.cell_tvd(probs[probs.model == "base"], human)
    banked = pd.read_csv(T.METRICS_ALL, usecols=["model", "eval_country", "question_id", "tv_distance"],
                         dtype={"question_id": str})
    banked = banked[banked.model == "base"].rename(columns={"eval_country": "country",
                                                             "question_id": "item"})
    m = t.merge(banked, on=["country", "item"], how="outer", indicator=True)
    assert (m["_merge"] == "both").all(), m[m["_merge"] != "both"].head()
    assert len(m) == 965 and skipped == [("JOR", "Q178")]
    assert np.abs(m["tvd"] - m["tv_distance"]).max() < 1e-6


@needs_real
def test_adapter_cell_reproduces_the_banked_matched_adapter_rows():
    probs = T.load_cohort1_scores()
    human = T.load_human(T.HUMAN_DISTS)
    t, _ = T.cell_tvd(probs[probs.model == "adapter"], human)
    banked = pd.read_csv(T.METRICS_ALL, usecols=["model", "eval_country", "relationship", "question_id",
                                                 "tv_distance"], dtype={"question_id": str})
    banked = banked[(banked.relationship == "matched") & (banked.model != "base")]
    banked = banked.rename(columns={"eval_country": "country", "question_id": "item"})
    m = t.merge(banked, on=["country", "item"], how="inner")
    assert len(m) == len(t) == 965
    assert np.abs(m["tvd"] - m["tv_distance"]).max() < 1e-6


@needs_real
def test_trust_gps_replays_the_banked_cohort1_value():
    import json
    probs = T.load_cohort1_scores()
    gps = T.load_trust_gps()
    prof = T.load_profiles(sorted(gps.index))
    comp = T.trust_composite(probs[probs.model == "adapter"])
    r = AS.bootstrap_spearman(comp, gps, clusters=prof, draws=200, seed=AS.BOOT_SEED)
    banked = json.loads((T.RESULTS / "persona" / "persona_strict.json").read_text())
    assert r["point"] == pytest.approx(banked["routes_vs_gps"]["C1"]["trust"]["point"], abs=1e-12)
