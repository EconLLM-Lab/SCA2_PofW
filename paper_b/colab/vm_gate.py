"""One-country Paper B gate. No respondent files, no Drive, no cohort.

1. Reproduce archived base-on-CHN option logprobs.
2. Score the frozen CHN adapter through a fresh loader and the production
   switch path, using the same weights.
3. Score two base questions before the adapter and after disabling it.
4. Upload the strict-battery CHN scores only if every comparison passes.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("SCA2_REPO", "/content/SCA2_PofW"))
sys.path.insert(0, str(REPO / "paper_b"))
os.chdir(REPO)

import eval_config as E  # noqa: E402
import eval_lib as L  # noqa: E402
import score_cohort as S  # noqa: E402
import score_runtime as R  # noqa: E402

E.SAVE_GENERATED_ANSWERS = False
OUT = Path(os.environ.get("SCA2_PB_DATA_ROOT", "/content/paper_b_data"))
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / "gate_report.json"
REVISION = R.require_revision(os.environ.get("SCA2_PB_ADAPTER_REVISION"))
RUN_ID = os.environ.get("SCORE_RUN_ID", "gate-chn-20261011")
BASE_TOL_LOGPROB = 1e-2
BASE_TOL_PROB = 1e-4
ADAPTER_TOL_LOGPROB = 1e-6
ADAPTER_TOL_PROB = 1e-4


def save(report: dict) -> None:
    REPORT.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in report if k != "questions"}, indent=2))


def main() -> int:
    if not os.environ.get("HF_TOKEN"):
        save({"gate_pass": False, "error": "HF_TOKEN missing"})
        return 2
    archive = E.ARCHIVE_DIR / "model_option_probabilities_base_on_CHN.csv"
    if not archive.is_file():
        save({"gate_pass": False, "error": f"archived base file missing: {archive}"})
        return 2
    t0 = time.time()
    question_map = L.load_question_map()
    grid = S._archived_numeric_grid()
    archive_specs = L.build_question_specs(question_map, {}, numeric_support=grid)
    from build_scoring_spec import build_scoring_spec
    strict = build_scoring_spec(question_map, numeric_support={}, battery="strict")
    switch_specs = [q for q in strict["questions"] if q["question_id"] in {"Q57", "Q58"}]
    report = {
        "revision": REVISION, "run_id": RUN_ID,
        "archive_questions": len(archive_specs),
        "strict_questions": strict["n_questions"],
        "generated_answers": False,
    }

    print("checking formatted prompts against the archive before model load")
    from transformers import AutoTokenizer
    import pandas as pd
    tok = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
    ref = pd.read_csv(archive, dtype={"option_code": str, "question_id": str})
    ref["option_index"] = ref["option_index"].astype(int)
    mismatches = []
    for spec in archive_specs:
        built = S.prepare_prompt_for_model(tok, L.build_survey_user_prompt(spec))
        archived = ref.loc[ref.question_id.eq(spec["question_id"]), "formatted_prompt"].iloc[0]
        if built["formatted_prompt"] != archived:
            mismatches.append(spec["question_id"])
    report["formatted_prompt_mismatches"] = mismatches
    if mismatches:
        report["gate_pass"] = False
        report["error"] = "formatted prompt differs from the archive; model was not loaded"
        save(report)
        print("PROMPT MISMATCH — not loading the model:", mismatches[:8])
        return 1

    print("loading base model")
    base, tok = S.load_base_model_and_tokenizer()
    got = S.score_model_questions(base, tok, "base", archive_specs, prompt_country=None)
    ok, base_report = R.compare_gate_scores(
        got, ref, {"questions": archive_specs}, BASE_TOL_LOGPROB, BASE_TOL_PROB)
    report["base_gate"] = base_report
    if not ok:
        merged = got.merge(
            ref[["question_id", "option_index", "option_code", "option_logprob", "model_prob"]],
            on=["question_id", "option_index", "option_code"], suffixes=("_got", "_ref"))
        merged["dlogprob"] = (merged["option_logprob_got"] - merged["option_logprob_ref"]).abs()
        worst = merged.nlargest(5, "dlogprob")[
            ["question_id", "option_code", "option_logprob_got", "option_logprob_ref", "dlogprob"]]
        report["worst_rows"] = worst.to_dict("records")
        report["gate_pass"] = False
        report["elapsed_min"] = round((time.time() - t0) / 60, 2)
        save(report)
        print("BASE GATE FAILED — adapter will not be scored")
        return 1

    adapter_dir, source = R.resolve_adapter("CHN", REVISION, E.ADAPTER_CACHE_DIR)
    report["adapter_source"] = source
    report["adapter_sha256"] = R.adapter_sha256(adapter_dir)

    from peft import PeftModel
    print("scoring independent reference loader")
    reference = PeftModel.from_pretrained(
        base, str(adapter_dir), adapter_name="reference", is_trainable=False)
    reference.set_adapter("reference")
    ref_scores = S.score_model_questions(
        reference, tok, "CHN_adapter", strict["questions"], prompt_country=None)
    del reference
    S.cleanup_cuda()

    print("reloading base for production path")
    del base
    S.cleanup_cuda()
    base, tok = S.load_base_model_and_tokenizer()
    print("scoring production-path base before adapter enable")
    before = S.score_model_questions(base, tok, "base", switch_specs, prompt_country=None)
    print("scoring production switch path")
    production = PeftModel.from_pretrained(
        base, str(adapter_dir), adapter_name="CHN", is_trainable=False)
    production.set_adapter("CHN")
    prod_scores = S.score_model_questions(
        production, tok, "CHN_adapter", strict["questions"], prompt_country=None)
    adapter_ok, adapter_report = R.compare_gate_scores(
        prod_scores, ref_scores, strict, ADAPTER_TOL_LOGPROB, ADAPTER_TOL_PROB)
    report["adapter_gate"] = adapter_report

    print("scoring production model after adapter disable")
    with production.disable_adapter():
        after = S.score_model_questions(
            production, tok, "base", switch_specs, prompt_country=None)
    switch_ok, switch_report = R.compare_gate_scores(
        after, before, {"questions": switch_specs}, ADAPTER_TOL_LOGPROB, ADAPTER_TOL_PROB)
    report["switchback"] = switch_report
    report["gate_pass"] = bool(adapter_ok and switch_ok)
    report["elapsed_min"] = round((time.time() - t0) / 60, 2)
    if not report["gate_pass"]:
        save(report)
        print("ADAPTER GATE FAILED — tolerances will not be widened")
        return 1

    marker = OUT / "adapter_gate.json"
    marker.write_text(json.dumps({
        "gate_pass": True, "country": "CHN", "adapter_revision": REVISION,
        "adapter_sha256": report["adapter_sha256"],
        "base_max_dlogprob": base_report["max_dlogprob"],
        "adapter_max_dlogprob": adapter_report["max_dlogprob"],
        "switchback_max_dlogprob": switch_report["max_dlogprob"],
    }, indent=2))
    store = R.HuggingFaceArtifactStore()
    prod_scores = prod_scores.copy()
    prod_scores["run_id"] = RUN_ID
    prod_scores["adapter_revision"] = REVISION
    persisted = R.persist_unit_scores(
        scores=prod_scores, model_name="CHN_adapter", run_id=RUN_ID,
        repo=R.ARTIFACTS_REPO, hub=store, adapter_sha256=report["adapter_sha256"],
        code_revision=R.code_revision(REPO), local_dir=OUT / "local_scores",
        spec_sha=strict.get("spec_sha256", ""), adapter_revision=REVISION,
    )
    report["persisted"] = persisted
    save(report)
    print("GATE PASSED and one-country upload verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
