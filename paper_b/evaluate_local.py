#!/usr/bin/env python3
"""Paper B — local-only population evaluation (no torch, no GPU, no network).

Consumes the model-only score CSVs written by `score_cohort.py` on the GPU plus
the licensed local WVS population frames, rebuilds the weighted population
distributions, joins them through the audited safe join (explicit skip ledger,
no silent drops), and writes the model-human evaluation surface LOCALLY:

  population_response_distributions.csv      weighted population option rows
  skipped_population_questions.csv           audit ledger of empty cells
  survey_option_evaluation_all_models.csv    joined per-option table
  survey_question_metrics_all_models.csv     per (model, country, question)
  local_eval_manifest.json                   hashes, protocol, join audit

Nothing here talks to the network; nothing here is uploaded anywhere. Human
respondent rows never leave this machine — only population-level distributions
are derived, and only locally.

Score-file contract (validated loudly before any output is written):
  * one CSV per model, exactly full option support per mapped question;
  * per-(model, question) probabilities finite, nonnegative, summing to one;
  * `option_code` read as strings (CSV round-trips coerce '1' -> int64 and
    would corrupt the join keys).

Usage:
  python paper_b/evaluate_local.py --scores-dir data/paper_b/scores \
      --countries CHN GBR JOR --out-dir data/paper_b/local_eval --pairs all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_config as E   # noqa: E402
import eval_lib as L      # noqa: E402

# Analysis-stage sample threshold, DOCUMENTED AND SEPARATE from the scorer's
# population threshold (which lives in the scoring path and is unchanged).
# Cells below this are REPORTED, never dropped here; whether an analysis
# excludes them is an analysis-layer decision (analysis/ uses MIN_N=50).
ANALYSIS_MIN_N = 50

PROB_SUM_TOL = 1e-8

OUTPUT_FILES = (
    "population_response_distributions.csv",
    "skipped_population_questions.csv",
    "survey_option_evaluation_all_models.csv",
    "survey_question_metrics_all_models.csv",
    "local_eval_manifest.json",
)


# ---------------------------------------------------------------- inputs
def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_model_scores(scores_dir) -> pd.DataFrame:
    """All per-model score CSVs in `scores_dir`, keys dtype-safe.

    `option_code` MUST come back as strings: fresh scorer rows carry strings
    and the population side is strings, but a naive CSV re-read infers int64.
    """
    scores_dir = Path(scores_dir)
    paths = sorted(scores_dir.glob("*_option_probabilities.csv"))
    if not paths:
        raise FileNotFoundError(f"no *_option_probabilities.csv under {scores_dir}")
    frames = [pd.read_csv(p, dtype={"option_code": str}) for p in paths]
    return pd.concat(frames, ignore_index=True)


def validate_model_scores(scores: pd.DataFrame, question_specs: list[dict]) -> None:
    """Full option support + valid probability vectors, per model/question."""
    expected = {s["question_id"]: list(s["codes"]) for s in question_specs}
    for (model, qid), group in scores.groupby(["model", "question_id"]):
        codes = group["option_code"].tolist()
        if sorted(codes) != sorted(expected.get(qid, [])):
            raise ValueError(
                f"{model}/{qid}: score file does not have full option support "
                f"(got {sorted(codes)}, expected {sorted(expected.get(qid, []))})")
        if group["option_code"].duplicated().any():
            raise ValueError(f"{model}/{qid}: duplicate option codes in score file")
    probs = pd.to_numeric(scores["model_prob"], errors="coerce")
    if not (probs.notna() & (probs >= 0)).all():
        raise ValueError("model_prob must be finite and nonnegative "
                         "(NaN/inf/negative found)")
    sums = scores.groupby(["model", "question_id"])["model_prob"].sum()
    bad = sums[(sums - 1.0).abs() > PROB_SUM_TOL]
    if len(bad):
        raise ValueError(f"model_prob must sum to one per (model, question); "
                         f"violations: {bad.to_dict()}")


def model_kind(model_name: str) -> tuple[str, str | None]:
    if model_name == "base":
        return "base", None
    if model_name.startswith("persona_"):
        return "persona", model_name[len("persona_"):]
    return "adapter", model_name.replace("_adapter", "")


def broadcast_pairs(model_scores: pd.DataFrame, pairs: str,
                    eval_countries: list[str]) -> pd.DataFrame:
    """Give each model's population-independent scores its eval countries.

    Mirrors score_cohort.build_pairs: base is always evaluated against every
    population; adapters/personas get their own country under `matched`,
    everyone under `all`.
    """
    out = []
    for model_name, group in model_scores.groupby("model"):
        kind, model_country = model_kind(model_name)
        targets = (list(eval_countries)
                   if (kind == "base" or pairs == "all") else [model_country])
        for cc in targets:
            part = group.copy()
            part["eval_country"] = cc
            out.append(part)
    return pd.concat(out, ignore_index=True)


def low_support_cells(population: pd.DataFrame, min_n: int = ANALYSIS_MIN_N) -> list[dict]:
    """Informational report of population cells below the analysis threshold.

    These cells are KEPT in every output file; this ledger exists so the
    analysis layer can apply its own documented MIN_N without re-deriving it.
    """
    per_cell = population.groupby(["eval_country", "question_id"]).agg(
        n_valid=("n_valid", "first")).reset_index()
    low = per_cell[per_cell["n_valid"] < min_n]
    return [{"eval_country": r.eval_country, "question_id": r.question_id,
             "n_valid": int(r.n_valid), "min_n": min_n,
             "note": "kept: informational only, not dropped"}
            for r in low.itertuples()]


# ---------------------------------------------------------------- driver
def run_evaluation(scores_dir, countries: list[str], out_dir,
                   pairs: str = "matched", question_map_path=None,
                   wvs_dir=None) -> dict:
    """Full local half of Paper B. Deterministic: byte-identical inputs give
    byte-identical outputs (no timestamps, sorted writes)."""
    if pairs not in ("matched", "all"):
        raise ValueError(f"pairs must be 'matched' or 'all', got {pairs!r}")
    countries = [c.strip().upper() for c in countries]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    question_map = L.load_question_map(question_map_path)
    frames = L.load_survey_frames(countries, wvs_dir)
    specs = L.build_question_specs(question_map, frames)

    # ---- populations + explicit skip ledger --------------------------------
    skip_ledger: list[dict] = []
    population = L.build_population_distributions(specs, frames, skipped=skip_ledger)
    skipped_cells = {(s["eval_country"], s["question_id"]) for s in skip_ledger}

    # ---- model scores: validate BEFORE writing any derived output ----------
    scores = load_model_scores(scores_dir)
    validate_model_scores(scores, specs)

    # ---- broadcast + audited join ------------------------------------------
    broadcast = broadcast_pairs(scores, pairs, countries)
    dropped: list[dict] = []
    option_eval = L.join_option_evaluation(broadcast, population,
                                           skipped_cells=skipped_cells,
                                           dropped=dropped)

    # ---- metrics ------------------------------------------------------------
    metrics = L.calculate_question_metrics(option_eval)

    # ---- write everything locally ------------------------------------------
    population.to_csv(out_dir / "population_response_distributions.csv", index=False)
    pd.DataFrame(skip_ledger).to_csv(
        out_dir / "skipped_population_questions.csv", index=False)
    option_eval.to_csv(out_dir / "survey_option_evaluation_all_models.csv", index=False)
    metrics.to_csv(out_dir / "survey_question_metrics_all_models.csv", index=False)

    input_paths = ([Path(question_map_path) if question_map_path
                    else E.QUESTION_MAP_FILE]
                   + [Path(wvs_dir or E.WVS_DIR) / f"{cc}_WVS_wave7.parquet"
                      for cc in countries]
                   + sorted(Path(scores_dir).glob("*_option_probabilities.csv")))
    summary = {
        "protocol": "paper_b local population evaluation (model-only scores + local WVS)",
        "question_map": str(input_paths[0]),
        "n_questions": len(specs),
        "n_option_rows": int(sum(len(s["codes"]) for s in specs)),
        "weight_column": E.WEIGHT_COLUMN,
        "use_survey_weights": E.USE_SURVEY_WEIGHTS,
        "completion_prefix": E.COMPLETION_PREFIX,
        "temperature": E.OPTION_SCORE_TEMPERATURE,
        "length_normalize": E.LENGTH_NORMALIZE_OPTION_LOGPROBS,
        "pairs": pairs,
        "eval_countries": countries,
        "models": sorted(scores["model"].unique().tolist()),
        "skip_ledger": skip_ledger,
        "skipped_cells": sorted(f"{c}/{q}" for c, q in skipped_cells),
        "n_skipped_cells": len(skip_ledger),
        "join_audit": {"dropped_rows": option_eval.attrs["dropped_rows"],
                       "dropped_cells": option_eval.attrs["dropped_cells"],
                       "skipped_cells_used": option_eval.attrs["skipped_cells_used"],
                       "dropped_records": dropped},
        "low_support_cells": low_support_cells(population),
        "analysis_min_n": ANALYSIS_MIN_N,
        "analysis_min_n_applied": False,
        "input_hashes": {str(p): _sha256_file(p) for p in input_paths},
    }
    (out_dir / "local_eval_manifest.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True))

    print(f"local eval: {len(summary['models'])} models x {len(countries)} countries "
          f"| {len(option_eval)} joined option rows | "
          f"{len(skip_ledger)} skipped cells {summary['skipped_cells']} | "
          f"{option_eval.attrs['dropped_rows']} model rows dropped (audited) "
          f"-> {out_dir}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--scores-dir", required=True,
                    help="directory of per-model *_option_probabilities.csv")
    ap.add_argument("--countries", nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--pairs", choices=["matched", "all"], default="matched")
    a = ap.parse_args()
    run_evaluation(scores_dir=a.scores_dir, countries=a.countries,
                   out_dir=a.out_dir, pairs=a.pairs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
