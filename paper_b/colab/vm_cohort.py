"""Score the Paper B cohort on the frozen stack.

Archive log-probability mismatch is recorded only if an archive file is present.
It does not stop the run. The stop condition is the same-weights China adapter
gate: production switch path versus an independent loader, then adapter disable.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
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
from build_scoring_spec import build_scoring_spec, spec_sha256, strict_item_ids  # noqa: E402

E.SAVE_GENERATED_ANSWERS = False
OUT = Path(os.environ.get("SCA2_PB_DATA_ROOT", "/content/paper_b_data"))
OUT.mkdir(parents=True, exist_ok=True)
RUN_ID = os.environ.get("SCORE_RUN_ID", "paper-b-20261011")
REVISION = R.require_revision(os.environ.get("SCA2_PB_ADAPTER_REVISION"))
ADAPTER_TOL_LOGPROB = 1e-6
ADAPTER_TOL_PROB = 1e-4


def versions() -> dict:
    import torch
    import transformers
    import peft
    import bitsandbytes
    try:
        smi = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            text=True,
        ).strip()
    except Exception as exc:  # noqa: BLE001
        smi = f"unavailable: {type(exc).__name__}"
    return {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "peft": peft.__version__,
        "bitsandbytes": bitsandbytes.__version__,
        "cuda": torch.version.cuda,
        "gpu": smi,
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "adapter_revision": REVISION,
        "chat_date": E.ARCHIVE_CHAT_DATE,
    }


def running_code_id() -> str:
    """Identity of the code that is actually executing.

    A Colab tarball has no .git. The parent commit also does not contain these
    untracked paper_b files, so a git SHA would name the wrong code.
    """
    explicit = os.environ.get("SCA2_CODE_REVISION", "").strip()
    if explicit:
        return explicit
    if (REPO / ".git" / "HEAD").is_file():
        return R.code_revision(REPO)
    import hashlib
    digest = hashlib.sha256()
    for path in sorted((REPO / "paper_b").rglob("*.py")):
        digest.update(path.relative_to(REPO).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def persist(store, frame, model_name, adapter_sha, adapter_revision, spec_sha):
    out = frame.copy()
    out["run_id"] = RUN_ID
    out["adapter_revision"] = adapter_revision
    return R.persist_unit_scores(
        scores=out, model_name=model_name, run_id=RUN_ID, repo=R.ARTIFACTS_REPO,
        hub=store, adapter_sha256=adapter_sha, code_revision=running_code_id(),
        local_dir=OUT / "local_scores", spec_sha=spec_sha,
        adapter_revision=adapter_revision,
    )


def _clock(unit, fn):
    t0 = time.time()
    result = fn()
    try:
        import compute_ledger as ledger
        ledger.try_record(ledger.make_event(
            stage="score", unit=unit,
            wall_minutes=(time.time() - t0) / 60,
            scope="score_and_persist",
            source="vm_cohort.py",
            role="live",
            includes=["score_model_questions", "persist"],
            excludes=["session_idle"],
            hardware=ledger.hardware_snapshot(),
            provenance={"run_id": RUN_ID, "adapter_revision": REVISION},
        ))
        ledger.try_upload_ledger("Bonorinoa/SCA2-paper-b-artifacts", RUN_ID)
    except Exception as exc:  # noqa: BLE001
        print(f"compute ledger: {type(exc).__name__}: {exc}")
    return result


def main() -> int:
    if not os.environ.get("HF_TOKEN"):
        print("refusing: HF_TOKEN missing")
        return 2
    info = versions()
    (OUT / "stack_versions.json").write_text(json.dumps(info, indent=2))
    print("STACK", json.dumps(info))
    qmap = L.load_question_map()
    qmap = qmap[qmap.Question.isin(strict_item_ids())]
    spec = build_scoring_spec(qmap, numeric_support={}, battery="strict")
    questions = spec["questions"]
    switch = [q for q in questions if q["question_id"] in {"Q57", "Q58"}]
    spec_sha = spec_sha256({k: v for k, v in spec.items() if k != "spec_sha256"})
    store = R.HuggingFaceArtifactStore()
    t0 = time.time()

    print("loading base")
    base, tok = S.load_base_model_and_tokenizer()
    print("scoring base")
    base_scores = _clock("base", lambda: S.score_model_questions(
        base, tok, "base", questions, prompt_country=None))
    before = S.score_model_questions(base, tok, "base", switch, prompt_country=None)
    base_sha = __import__("hashlib").sha256(b"meta-llama/Llama-3.1-8B-Instruct").hexdigest()
    print("BASE_PERSIST", persist(store, base_scores, "base", base_sha, "", spec_sha))

    from peft import PeftModel
    adapter_dir, source = R.resolve_adapter("CHN", REVISION, E.ADAPTER_CACHE_DIR)
    adapter_sha = R.adapter_sha256(adapter_dir)
    print("CHN adapter", source, adapter_sha)
    print("reference loader")
    reference = PeftModel.from_pretrained(
        base, str(adapter_dir), adapter_name="reference", is_trainable=False)
    reference.set_adapter("reference")
    ref_scores = _clock("CHN_gate_reference", lambda: S.score_model_questions(
        reference, tok, "CHN_adapter", questions, prompt_country=None))
    del reference
    S.cleanup_cuda()
    del base
    S.cleanup_cuda()

    print("reloading base for production path")
    base, tok = S.load_base_model_and_tokenizer()
    before = S.score_model_questions(base, tok, "base", switch, prompt_country=None)
    production = PeftModel.from_pretrained(
        base, str(adapter_dir), adapter_name="CHN", is_trainable=False)
    production.set_adapter("CHN")
    prod_scores = _clock("CHN_gate_production", lambda: S.score_model_questions(
        production, tok, "CHN_adapter", questions, prompt_country=None))
    adapter_ok, adapter_report = R.compare_gate_scores(
        prod_scores, ref_scores, spec, ADAPTER_TOL_LOGPROB, ADAPTER_TOL_PROB)
    with production.disable_adapter():
        after = S.score_model_questions(production, tok, "base", switch, prompt_country=None)
    switch_ok, switch_report = R.compare_gate_scores(
        after, before, {"questions": switch}, ADAPTER_TOL_LOGPROB, ADAPTER_TOL_PROB)
    gate = {
        "gate_pass": bool(adapter_ok and switch_ok),
        "adapter": adapter_report,
        "switchback": switch_report,
        "adapter_sha256": adapter_sha,
        "stack": info,
    }
    (OUT / "adapter_gate.json").write_text(json.dumps(gate, indent=2))
    print("ADAPTER_GATE", json.dumps(gate))
    if not gate["gate_pass"]:
        print("ADAPTER GATE FAILED — cohort will not be scored")
        return 1
    print("CHN_PERSIST", persist(store, prod_scores, "CHN_adapter", adapter_sha, REVISION, spec_sha))

    for cc in [c for c in __import__("config").COHORT if c != "CHN"]:
        started = time.time()
        cc_dir, cc_source = R.resolve_adapter(cc, REVISION, E.ADAPTER_CACHE_DIR)
        cc_sha = R.adapter_sha256(cc_dir)
        production.load_adapter(str(cc_dir), adapter_name=cc, is_trainable=False)
        production.set_adapter(cc)
        scored = S.score_model_questions(
            production, tok, f"{cc}_adapter", questions, prompt_country=None)
        saved = persist(store, scored, f"{cc}_adapter", cc_sha, REVISION, spec_sha)
        production.delete_adapter(cc)
        mins = (time.time() - started) / 60
        print(f"SCORED {cc} from {cc_source} in {mins:.2f} min", saved)
        try:
            import compute_ledger as ledger
            ledger.try_record(ledger.make_event(
                stage="score", unit=cc,
                wall_minutes=mins,
                scope="score_and_persist",
                source="vm_cohort.py",
                role="live",
                includes=["adapter_load", "score_model_questions", "persist"],
                hardware=ledger.hardware_snapshot(),
                provenance={"run_id": RUN_ID, "adapter_revision": REVISION},
            ))
            ledger.try_upload_ledger("Bonorinoa/SCA2-paper-b-artifacts", RUN_ID)
        except Exception as exc:  # noqa: BLE001
            print(f"compute ledger: {type(exc).__name__}: {exc}")
    print(f"COHORT_DONE in {(time.time() - t0) / 60:.2f} min")
    print(f"compute ledger: {OUT / 'compute_ledger.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
