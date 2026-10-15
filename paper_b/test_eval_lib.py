"""CPU tests for the Paper B scorer — no torch, no GPU, no HF token.

These pin `paper_b/eval_lib.py` to the archived Paper A artifacts in
`data/phase2/raw/wvs/ksenias_base8/`, so a silent change in prompt building,
option parsing, population weighting, or a metric formula fails loudly.

Run:  env -u PYTHONPATH .venv/bin/python -m pytest paper_b/test_eval_lib.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_config as E           # noqa: E402
import eval_lib as L              # noqa: E402

ARCHIVE = E.ARCHIVE_DIR
BASE8 = ["CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS"]
C16 = BASE8 + ["IND", "IDN", "NGA", "EGY", "TUR", "NLD", "BRA", "GRC"]


@pytest.fixture(scope="module")
def question_map():
    return L.load_question_map()


@pytest.fixture(scope="module")
def archived_grid():
    return _archived_numeric_grid()


def _archived_numeric_grid():
    df = pd.read_csv(ARCHIVE / "model_option_probabilities_base_on_CHN.csv")
    grid = {}
    for qid in E.NUMERIC_VALID_RANGES:
        sub = df[df.question_id == qid].sort_values("option_index")
        grid[qid] = [str(c) for c in sub["option_code"].tolist()]
    return grid


def test_canonical_code():
    assert L.canonical_code(3.0) == "3"
    assert L.canonical_code("2") == "2"
    assert L.canonical_code(2.5) == "2.5"


def test_parse_semicolon_field():
    assert L.parse_semicolon_field("1; 2; 3") == ["1", "2", "3"]
    assert L.parse_semicolon_field(np.nan) == []


def test_item_grid_matches_archive(question_map, archived_grid):
    specs = L.build_question_specs(question_map, {}, numeric_support=archived_grid)
    assert len(specs) == 35
    counts = {s["question_id"]: len(s["codes"]) for s in specs}
    ref = (pd.read_csv(ARCHIVE / "model_option_probabilities_base_on_CHN.csv")
           .groupby("question_id").size().to_dict())
    assert counts == ref


def test_population_reproduces_archive(question_map, archived_grid):
    specs = L.build_question_specs(question_map, {}, numeric_support=archived_grid)
    frames = L.load_survey_frames(BASE8)
    skipped = []
    pop = L.build_population_distributions(specs, frames, skipped=skipped)
    # documented skips: Great Britain was not asked Q174; Egypt not asked Q69-71
    assert {(s["eval_country"], s["question_id"]) for s in skipped} == {("GBR", "Q174")}
    ref = pd.read_csv(ARCHIVE / "population_response_distributions.csv")
    keys = ["eval_country", "question_id", "option_code"]
    pop["option_code"] = pop["option_code"].astype(str)
    ref["option_code"] = ref["option_code"].astype(str)
    m = pop.merge(ref[keys + ["population_prob", "weighted_count", "n_valid", "total_weight"]],
                  on=keys, suffixes=("_mine", "_ref"), how="inner")
    assert len(m) == len(ref)
    assert (m["population_prob_mine"] - m["population_prob_ref"]).abs().max() < 1e-9
    assert (m["weighted_count_mine"] - m["weighted_count_ref"]).abs().max() < 1e-6
    assert (m["n_valid_mine"] == m["n_valid_ref"]).all()


def test_metrics_reproduce_archive():
    ref = pd.read_csv(ARCHIVE / "survey_question_metrics_all_models.csv")
    pop = pd.read_csv(ARCHIVE / "population_response_distributions.csv")
    frames = []
    for path in sorted(ARCHIVE.glob("model_option_probabilities_*.csv")):
        df = pd.read_csv(path)
        if "eval_country" not in df.columns:
            continue
        frames.append(df[["model", "eval_country", "question_id", "option_index",
                          "option_code", "option_value", "model_prob"]])
    scores = pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=["model", "eval_country", "question_id", "option_index"])
    rows = []
    for (model, cc, qid), g in scores.groupby(["model", "eval_country", "question_id"], sort=False):
        p = pop[(pop.eval_country == cc) & (pop.question_id == qid)].sort_values("option_index")
        rows.append(g.sort_values("option_index").merge(
            p, on=["eval_country", "question_id", "option_index"], suffixes=("", "_pop")))
    metrics = L.calculate_question_metrics(pd.concat(rows, ignore_index=True))
    m = metrics.merge(ref, on=["model", "eval_country", "question_id"],
                      suffixes=("_mine", "_ref"))
    assert len(m) == len(ref)
    for col in ["tv_distance", "js_divergence", "brier_score", "cross_entropy",
                "wasserstein_distance", "abs_mean_error", "model_mean"]:
        assert (m[f"{col}_mine"] - m[f"{col}_ref"]).abs().max() < 1e-6, col


def test_prompt_has_no_country_name(question_map, archived_grid):
    specs = L.build_question_specs(question_map, {}, numeric_support=archived_grid)
    spec = next(s for s in specs if s["question_id"] == "Q57")
    plain = L.build_survey_user_prompt(spec)
    assert "the United States" not in plain and "China" not in plain
    persona = L.build_survey_user_prompt(spec, prompt_country="CHN")
    assert "China" in persona


def test_relationship_labels():
    assert L.relationship_label("base", "CHN") == "base"
    assert L.relationship_label("CHN_adapter", "CHN") == "matched"
    assert L.relationship_label("CHN_adapter", "JPN") == "cross"
    assert L.relationship_label("persona_ARG", "ARG") == "persona_matched"
    assert L.relationship_label("persona_ARG", "JPN") == "persona_cross"


def test_softmax():
    p = L.stable_softmax([0.0, 0.0])
    assert np.allclose(p, [0.5, 0.5])
    assert np.isclose(L.stable_softmax([1.0, 2.0]).sum(), 1.0)


def test_cohort_numeric_grid_is_country_set_dependent(question_map, archived_grid):
    """Documented behaviour: the numeric-open grid grows with the cohort.
    Pinning it matters — this is why the gate overrides the grid."""
    specs42 = L.build_question_specs(question_map, L.load_survey_frames(C16))
    q261 = next(s for s in specs42 if s["question_id"] == "Q261")
    assert len(q261["codes"]) > len(archived_grid["Q261"])


# ---------------------------------------------------------------- audited join
def _tiny_scores() -> pd.DataFrame:
    """Model rows broadcast to CHN and JOR; JOR/Q178 has no population cell."""
    rows = []
    for cc in ["CHN", "JOR"]:
        for code, idx, val, p in [("1", 0, 1.0, 0.6), ("2", 1, 2.0, 0.4)]:
            rows.append({"model": "base", "eval_country": cc, "question_id": "Q57",
                         "option_index": idx, "option_code": code,
                         "option_value": val, "model_prob": p})
        if cc == "JOR":
            for i in range(10):
                rows.append({"model": "base", "eval_country": cc, "question_id": "Q178",
                             "option_index": i, "option_code": str(i + 1),
                             "option_value": float(i + 1), "model_prob": 0.1})
    return pd.DataFrame(rows)


def _tiny_population() -> pd.DataFrame:
    rows = []
    for cc in ["CHN", "JOR"]:
        for code, idx, p in [("1", 0, 0.5), ("2", 1, 0.5)]:
            rows.append({"eval_country": cc, "question_id": "Q57",
                         "option_index": idx, "option_code": code,
                         "option_value": float(code), "population_prob": p,
                         "weighted_count": p * 10, "unweighted_count": 5,
                         "n_valid": 10, "total_weight": 10.0})
    return pd.DataFrame(rows)


def test_join_drops_only_explicitly_skipped_cells_and_reports():
    dropped = []
    merged = L.join_option_evaluation(_tiny_scores(), _tiny_population(),
                                      skipped_cells={("JOR", "Q178")}, dropped=dropped)
    assert len(merged) == 4  # two countries x Q57 options; JOR/Q178 rows dropped
    assert merged.attrs["dropped_rows"] == 10
    assert merged.attrs["dropped_cells"] == {"JOR/Q178": 10}
    assert merged.attrs["skipped_cells_used"] == ["JOR/Q178"]
    assert dropped == [{"eval_country": "JOR", "question_id": "Q178",
                        "reason": "explicitly_recorded_empty_population_cell",
                        "dropped_rows": 10}]


def test_join_default_drops_nothing_and_fails_unexpected_missing():
    with pytest.raises(AssertionError, match="not recorded as population skips"):
        L.join_option_evaluation(_tiny_scores(), _tiny_population())


def test_join_rejects_bogus_skip_that_has_population():
    with pytest.raises(ValueError, match="(?i)bogus"):
        L.join_option_evaluation(_tiny_scores(), _tiny_population(),
                                 skipped_cells={("CHN", "Q57")})


def test_join_fails_on_partial_option_support():
    scores = _tiny_scores()
    scores = scores[~((scores.eval_country == "CHN") & (scores.question_id == "Q57")
                      & (scores.option_code == "2"))]
    with pytest.raises(AssertionError, match="not recorded as population skips"):
        L.join_option_evaluation(scores, _tiny_population())


def test_join_canonicalizes_option_code_keys():
    scores = _tiny_scores()
    scores["option_code"] = scores["option_code"].astype(int)  # CSV round-trip hazard
    merged = L.join_option_evaluation(scores, _tiny_population(),
                                      skipped_cells={("JOR", "Q178")})
    assert len(merged) == 4
    assert merged["option_code"].tolist() == ["1", "2", "1", "2"]


def test_join_rejects_nonunique_population_keys():
    pop = pd.concat([_tiny_population(), _tiny_population().iloc[[0]]],
                    ignore_index=True)
    with pytest.raises(AssertionError, match="not unique"):
        L.join_option_evaluation(_tiny_scores(), pop, skipped_cells={("JOR", "Q178")})


def test_builder_skip_ledger_records_reason_n_valid_total_weight(question_map,
                                                                 archived_grid):
    specs = L.build_question_specs(question_map, {}, numeric_support=archived_grid)
    frames = L.load_survey_frames(["GBR", "JOR"])
    skipped: list[dict] = []
    pop = L.build_population_distributions(specs, frames, skipped=skipped)
    by_cell = {(s["eval_country"], s["question_id"]): s for s in skipped}
    assert ("GBR", "Q174") in by_cell and ("JOR", "Q178") in by_cell
    for cell in by_cell.values():
        assert cell["reason"] == "no_valid_responses"
        assert cell["n_valid"] == 0
        assert cell["total_weight"] == 0.0
    assert pop.attrs["skipped_cells"] == sorted(
        {(s["eval_country"], s["question_id"]) for s in skipped})
    assert pop.attrs["n_skipped_cells"] == len(skipped)


def test_builder_default_records_no_skips_and_fail_is_loud(question_map, archived_grid):
    """Default: no skips permitted — an empty cell raises instead of silently
    dropping, so GPU-side callers that never pass `skipped` keep the old
    loud behaviour."""
    specs = L.build_question_specs(question_map, {}, numeric_support=archived_grid)
    frames = L.load_survey_frames(["GBR"])
    with pytest.raises(ValueError, match="no valid responses"):
        L.build_population_distributions(specs, frames)
