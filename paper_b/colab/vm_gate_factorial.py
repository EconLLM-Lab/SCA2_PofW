"""One-unit Paper B gate for the bank-2 profile adapters. No respondent files, no Drive.

Same checks as vm_gate.py (cohort 1), with GATE_UNIT in place of CHN:
1. Compare base to the archived base-on-CHN option logprobs (report-only; formatted prompts must match).
2. Score GATE_UNIT through a fresh loader and the production switch path, using the same weights.
3. Score two base questions before the adapter and after disabling it.
4. Upload the strict-battery scores of GATE_UNIT only if the adapter-path and switch-back checks pass.
(The archive comparison is report-only per PAPER_B_STACK_FREEZE.md; the full report is uploaded either way.)
The marker records the unit, adapter revision and SHA-256; scoring refuses to start without it.
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
GATE_UNIT = os.environ["GATE_UNIT"]            # required: no default, so a typo cannot gate the wrong cell
RUN_ID = os.environ.get("SCORE_RUN_ID", f"gate-bank2-{GATE_UNIT}-20261016")
BASE_TOL_LOGPROB = 1e-2
BASE_TOL_PROB = 1e-4
ADAPTER_TOL_LOGPROB = 1e-6
ADAPTER_TOL_PROB = 1e-4


def save(report: dict) -> None:
    REPORT.write_text(json.dumps(report, indent=2))
    try:                                   # the full report, including the adapter gaps, must outlive the VM
        import hub_io
        from huggingface_hub import HfApi
        hub_io._retry(lambda: HfApi().upload_file(
            path_or_fileobj=str(REPORT), path_in_repo=f"runs/{RUN_ID}/gate_report.json", repo_id=R.ARTIFACTS_REPO,
            repo_type="dataset", commit_message=f"{RUN_ID}: gate report"), "upload gate report")
    except Exception as exc:  # noqa: BLE001 - best effort; the marker and local report still exist
        print(f"gate report upload failed: {type(exc).__name__}: {exc}")
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
    from build_scoring_spec import build_scoring_spec, spec_sha256
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
    # PAPER_B_STACK_FREEZE.md (2026-10-11): the August archive is not a bit-level target for Paper B, and an
    # archive log-probability mismatch is REPORTED, not a stop condition. The binding checks are the
    # same-weights adapter path and the switch-back below, which stay fatal. The tolerance is not widened:
    # the gap is recorded in full next to the package versions so a later reader can judge the stack.
    base_report["pass_vs_archive"] = bool(ok)
    base_report.pop("pass", None)
    report["base_archive_check"] = {**base_report, **R.archive_gap_summary(got, ref, BASE_TOL_LOGPROB),
                                    "policy": "report-only per PAPER_B_STACK_FREEZE.md"}
    report["stack_versions"] = R.package_versions()
    try:
        import subprocess
        report["gpu_driver"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version,name", "--format=csv,noheader"],
            capture_output=True, text=True).stdout.strip()
    except OSError:
        report["gpu_driver"] = "unavailable"
    print("base vs archive (report-only):", json.dumps(
        {k: report["base_archive_check"][k] for k in ("n_compared", "n_over_tol", "max_dlogprob", "questions_over_tol")}))
    print("stack:", json.dumps(report["stack_versions"]))

    adapter_dir, source = R.resolve_adapter(GATE_UNIT, REVISION, E.ADAPTER_CACHE_DIR)
    report["adapter_source"] = source
    report["adapter_sha256"] = R.adapter_sha256(adapter_dir)

    from peft import PeftModel
    print("scoring independent reference loader")
    reference = PeftModel.from_pretrained(
        base, str(adapter_dir), adapter_name="reference", is_trainable=False)
    reference.set_adapter("reference")
    ref_scores = S.score_model_questions(
        reference, tok, f"{GATE_UNIT}_adapter", strict["questions"], prompt_country=None)
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
        base, str(adapter_dir), adapter_name="production", is_trainable=False)
    production.set_adapter("production")
    prod_scores = S.score_model_questions(
        production, tok, f"{GATE_UNIT}_adapter", strict["questions"], prompt_country=None)
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
        "gate_pass": True, "unit": GATE_UNIT, "adapter_revision": REVISION,
        "adapter_sha256": report["adapter_sha256"],
        "base_max_dlogprob": base_report["max_dlogprob"],
        "base_archive_pass": bool(ok),
        "base_archive_questions_over_tol": report["base_archive_check"]["questions_over_tol"],
        "stack_versions": report["stack_versions"], "gpu_driver": report["gpu_driver"],
        "adapter_max_dlogprob": adapter_report["max_dlogprob"],
        "switchback_max_dlogprob": switch_report["max_dlogprob"],
    }, indent=2))
    store = R.HuggingFaceArtifactStore()
    prod_scores = prod_scores.copy()
    prod_scores["run_id"] = RUN_ID
    prod_scores["adapter_revision"] = REVISION
    persisted = R.persist_unit_scores(
        scores=prod_scores, model_name=f"{GATE_UNIT}_adapter", run_id=RUN_ID,
        repo=R.ARTIFACTS_REPO, hub=store, adapter_sha256=report["adapter_sha256"],
        code_revision=R.code_revision(REPO), local_dir=OUT / "local_scores",
        spec_sha=spec_sha256(strict), adapter_revision=REVISION,
    )
    report["persisted"] = persisted
    save(report)
    print("GATE PASSED and one-country upload verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
