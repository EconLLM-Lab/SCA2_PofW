"""CPU tests for paper_b/evaluate_local.py — local-only population evaluation.

Runs the full local half of Paper B (model-only score CSVs + local WVS frames
-> weighted populations -> audited join -> metrics -> skip manifest) on the
real repository inputs plus synthetic model scores with known-by-construction
ground truth, plus deliberately broken score files that must fail loudly.

Run:  env -u PYTHONPATH .venv/bin/python -m pytest paper_b/test_evaluate_local.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_config as E           # noqa: E402
import eval_lib as L              # noqa: E402
import evaluate_local as V        # noqa: E402

COUNTRIES = ["CHN", "GBR", "JOR"]
# documented genuine empty cells on this country set
EXPECTED_SKIPS = {("GBR", "Q174"), ("JOR", "Q178")}


def _specs_and_frames():
    qmap = L.load_question_map()
    frames = L.load_survey_frames(COUNTRIES)
    specs = L.build_question_specs(qmap, frames)
    return qmap, frames, specs


def _write_uniform_scores(scores_dir: Path, specs: list[dict],
                          models: list[str]) -> list[Path]:
    """Model-only score CSVs (as score_cohort writes them): uniform probs."""
    scores_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for model in models:
        rows = []
        for spec in specs:
            k = len(spec["codes"])
            for idx, (code, label) in enumerate(zip(spec["codes"], spec["labels"])):
                rows.append({
                    "model": model, "prompt_country": None,
                    "question_id": spec["question_id"],
                    "question_text": spec["question_text"],
                    "response_type": spec["response_type"],
                    "gps_dimension": spec["gps_dimension"],
                    "is_ordered": spec["is_ordered"],
                    "is_numeric_open": spec["is_numeric_open"],
                    "option_index": idx, "option_code": code,
                    "option_value": float(code), "option_label": label,
                    "model_prob": 1.0 / k,
                })
        path = scores_dir / f"{model}_option_probabilities.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        paths.append(path)
    return paths


@pytest.fixture(scope="module")
def good_run(tmp_path_factory):
    qmap, frames, specs = _specs_and_frames()
    root = tmp_path_factory.mktemp("good")
    scores_dir = root / "scores"
    _write_uniform_scores(scores_dir, specs, ["base", "CHN_adapter"])
    out_dir = root / "out"
    summary = V.run_evaluation(scores_dir=scores_dir, countries=COUNTRIES,
                               out_dir=out_dir, pairs="all")
    return {"summary": summary, "out_dir": out_dir, "scores_dir": scores_dir,
            "specs": specs}


# ---------------------------------------------------------------- unit level
def test_load_model_scores_preserves_string_option_codes(tmp_path):
    df = pd.DataFrame({
        "model": ["base", "base"], "question_id": ["Q57", "Q57"],
        "option_index": [0, 1], "option_code": ["1", "2"],
        "option_value": [1.0, 2.0], "model_prob": [0.5, 0.5],
        "question_text": ["t", "t"], "response_type": ["single_choice_2"] * 2,
        "gps_dimension": ["trust"] * 2, "is_ordered": [True] * 2,
        "is_numeric_open": [False] * 2, "option_label": ["1", "2"],
    })
    path = tmp_path / "base_option_probabilities.csv"
    df.to_csv(path, index=False)  # CSV round-trip would infer int64 codes
    loaded = V.load_model_scores(tmp_path)
    assert loaded["option_code"].tolist() == ["1", "2"]
    assert loaded["option_code"].map(lambda v: isinstance(v, str)).all()


def test_validate_model_scores_requires_full_option_support():
    _, _, specs = _specs_and_frames()
    scores = V.load_model_scores(_scores_dir_helper(specs, drop_q57_option2=True))
    with pytest.raises(ValueError, match="full option support"):
        V.validate_model_scores(scores, specs)


def _scores_dir_helper(specs, drop_q57_option2=False):
    """Small helper: a one-model scores dir, optionally broken."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rows = []
    for spec in specs:
        k = len(spec["codes"])
        for idx, (code, label) in enumerate(zip(spec["codes"], spec["labels"])):
            if drop_q57_option2 and spec["question_id"] == "Q57" and code == "2":
                continue
            rows.append({
                "model": "base", "question_id": spec["question_id"],
                "question_text": spec["question_text"],
                "response_type": spec["response_type"],
                "gps_dimension": spec["gps_dimension"],
                "is_ordered": spec["is_ordered"],
                "is_numeric_open": spec["is_numeric_open"],
                "option_index": idx, "option_code": code,
                "option_value": float(code), "option_label": label,
                "model_prob": 1.0 / k,
            })
    pd.DataFrame(rows).to_csv(tmp / "base_option_probabilities.csv", index=False)
    return tmp


@pytest.mark.parametrize("mutate,match", [
    (lambda df: df.assign(model_prob=df.model_prob / 2), "sum to one"),
    (lambda df: df.assign(model_prob=-df.model_prob.abs()), "nonnegative"),
    (lambda df: df.assign(model_prob=df.model_prob * np.nan), "nonnegative"),
])
def test_validate_model_scores_rejects_bad_probabilities(mutate, match):
    _, _, specs = _specs_and_frames()
    tmp = Path(_scores_dir_helper(specs))
    scores = mutate(V.load_model_scores(tmp))
    with pytest.raises(ValueError, match=match):
        V.validate_model_scores(scores, specs)


def test_low_support_cells_helper_is_informational_only():
    pop = pd.DataFrame({
        "eval_country": ["XXX"] * 3, "question_id": ["Q57"] * 3,
        "n_valid": [10, 10, 10], "population_prob": [0.5, 0.3, 0.2],
    })
    low = V.low_support_cells(pop, min_n=50)
    assert low == [{"eval_country": "XXX", "question_id": "Q57",
                    "n_valid": 10, "min_n": 50,
                    "note": "kept: informational only, not dropped"}]
    assert V.ANALYSIS_MIN_N == 50


# ---------------------------------------------------------------- end to end
def test_run_evaluation_good_fixture_complete(good_run):
    out = good_run["out_dir"]
    for name in ["population_response_distributions.csv",
                 "skipped_population_questions.csv",
                 "survey_option_evaluation_all_models.csv",
                 "survey_question_metrics_all_models.csv",
                 "local_eval_manifest.json"]:
        assert (out / name).exists(), name

    manifest = json.loads((out / "local_eval_manifest.json").read_text())
    skips = {(s["eval_country"], s["question_id"]): s
             for s in manifest["skip_ledger"]}
    assert set(skips) == EXPECTED_SKIPS
    for cell in skips.values():
        assert cell["reason"] == "no_valid_responses"
    assert manifest["skipped_cells"] == sorted(f"{c}/{q}" for c, q in EXPECTED_SKIPS)

    # analysis MIN_N=50 is documented, separate from the scorer threshold
    assert manifest["analysis_min_n"] == 50
    assert manifest["analysis_min_n_applied"] is False

    # model scores are never modified in place; inputs hashed
    assert "base_option_probabilities.csv" in {
        Path(k).name for k in manifest["input_hashes"]}
    assert all(len(h) == 64 for h in manifest["input_hashes"].values())

    # join audit: under pairs=all BOTH models carry GBR/Q174 + JOR/Q178 rows
    assert manifest["join_audit"]["dropped_cells"] == {
        "GBR/Q174": 4, "JOR/Q178": 20}
    assert manifest["join_audit"]["dropped_rows"] == 24
    assert manifest["join_audit"]["skipped_cells_used"] == ["GBR/Q174", "JOR/Q178"]
    assert manifest["models"] == ["CHN_adapter", "base"]


def test_run_evaluation_metrics_known_by_construction(good_run):
    """Uniform model probs => tv_distance = 0.5 * L1(p, uniform), computed
    independently from the written population file."""
    out = good_run["out_dir"]
    metrics = pd.read_csv(out / "survey_question_metrics_all_models.csv")
    pop = pd.read_csv(out / "population_response_distributions.csv")
    pop["option_code"] = pop["option_code"].astype(str)
    cell = metrics[(metrics.model == "base") & (metrics.eval_country == "CHN")
                   & (metrics.question_id == "Q57")].iloc[0]
    p = pop[(pop.eval_country == "CHN") & (pop.question_id == "Q57")].sort_values(
        "option_index")["population_prob"].to_numpy()
    k = len(p)
    expected_tv = 0.5 * np.abs(p - np.full(k, 1.0 / k)).sum()
    assert abs(cell.tv_distance - expected_tv) < 1e-12
    # pairs=all: every model is evaluated against every requested population
    assert set(metrics.model) == {"base", "CHN_adapter"}
    assert set(metrics[metrics.model == "CHN_adapter"].eval_country) == set(COUNTRIES)
    countries = set(metrics[metrics.model == "base"].eval_country)
    assert countries == set(COUNTRIES)
    # no metrics rows for skipped cells
    assert not ((metrics.model == "base") & (metrics.eval_country == "GBR")
                & (metrics.question_id == "Q174")).any()


def test_run_evaluation_idempotent_rerun(good_run, tmp_path):
    """Second run into the SAME directory: byte-identical outputs, no
    duplicate rows."""
    out = good_run["out_dir"]
    before = {p.name: p.read_bytes() for p in sorted(out.iterdir())}
    V.run_evaluation(scores_dir=good_run["scores_dir"], countries=COUNTRIES,
                     out_dir=out, pairs="all")
    after = {p.name: p.read_bytes() for p in sorted(out.iterdir())}
    assert before.keys() == after.keys()
    for name, blob in before.items():
        assert after[name] == blob, name
    opt = pd.read_csv(out / "survey_option_evaluation_all_models.csv")
    dup = opt.duplicated(subset=["model", "eval_country", "question_id",
                                 "option_index"]).sum()
    assert dup == 0


def test_run_evaluation_fails_loud_on_partial_support(tmp_path):
    _, _, specs = _specs_and_frames()
    scores_dir = Path(_scores_dir_helper(specs, drop_q57_option2=True))
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="full option support"):
        V.run_evaluation(scores_dir=scores_dir, countries=["CHN"],
                         out_dir=out, pairs="all")
    assert not (out / "survey_question_metrics_all_models.csv").exists()
    assert not (out / "local_eval_manifest.json").exists()
