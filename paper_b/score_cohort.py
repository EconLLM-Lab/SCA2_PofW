#!/usr/bin/env python3
"""Paper B — score the 42-country cohort on the WVS readout (GPU), and gate it.

Turns trained adapters into the Paper B product: option-probability
distributions per adapter on the mapped WVS items, plus the matched
survey-question metrics. Reproduces the Paper A readout
(`DPO_eval_WVS/DPO_survey_distribution_evaluation.ipynb`) exactly.

Anti-leakage: the primary readout uses the *unconditioned* prompt (no country
name). The country-named `persona` arm is a separate comparator.

Because the unconditioned model distribution does not depend on the target
population, each adapter is scored ONCE and then compared against every
population — matched and cross come for free, with no extra GPU cost.

Usage (Colab GPU):
  export HF_TOKEN=...
  export SCA2_PB_DATA_ROOT=/content/drive/MyDrive/SCA2_paper_b
  python paper_b/score_cohort.py --gate            # reproduce archived base-on-CHN
  python paper_b/score_cohort.py --countries CHN   # one adapter, end to end
  python paper_b/score_cohort.py                   # all arms, full cohort
  python paper_b/score_cohort.py --arms base,adapter --pairs matched

CPU-only gate (no GPU, no HF token):
  python paper_b/score_cohort.py --gate-cpu
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
import eval_config as E
import eval_lib as L

GIT_SHA_FILE = C.REPO / ".git" / "HEAD"


# ---------------------------------------------------------------- provenance
def _git_sha() -> str:
    try:
        head = GIT_SHA_FILE.read_text().strip()
        if head.startswith("ref: "):
            ref = C.REPO / ".git" / head.split("ref: ", 1)[1].strip()
            return ref.read_text().strip()[:12]
        return head[:12]
    except OSError:
        return "unknown"


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# ================================================================ adapter source
REQUIRED_ADAPTER_FILES = ("adapter_config.json", "adapter_model.safetensors")


def _is_complete_adapter(dirpath: Path) -> bool:
    return all((dirpath / f).exists() for f in REQUIRED_ADAPTER_FILES)


def hf_adapter_names() -> set[str]:
    """Countries with a COMPLETE adapter on the hub. Empty set on failure."""
    try:
        from huggingface_hub import HfApi
        files = HfApi(token=os.environ.get("HF_TOKEN")).list_repo_files(
            C.HF_ADAPTER_REPO, repo_type=E.HF_ADAPTER_REPO_TYPE)
    except Exception as e:  # noqa: BLE001
        print(f"  ! hub listing failed: {type(e).__name__}: {e}")
        return set()
    have: dict[str, set] = collections.defaultdict(set)
    for f in files:
        parts = f.split("/")
        if len(parts) >= 3 and parts[0] == "adapters":
            have[parts[1]].add("/".join(parts[2:]))
    return {cc for cc in C.COHORT
            if all(x in have[cc] for x in REQUIRED_ADAPTER_FILES)}


def drive_adapter_names() -> set[str]:
    return {cc for cc in C.COHORT if _is_complete_adapter(C.ADAPTER_DIR / cc)}


def resolve_adapter(cc: str, force: bool = False) -> tuple[Path, str]:
    """Local complete adapter dir for `cc`, plus its source label.

    Hub first (the durable bus), Drive second. Downloads land in
    ADAPTER_CACHE_DIR, which is local scratch — never the Drive FUSE.
    """
    local = E.ADAPTER_CACHE_DIR / "adapters" / cc
    if _is_complete_adapter(local) and not force:
        return local, "cache"

    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=C.HF_ADAPTER_REPO, repo_type=E.HF_ADAPTER_REPO_TYPE,
                          allow_patterns=[f"adapters/{cc}/*"],
                          local_dir=str(E.ADAPTER_CACHE_DIR))
        if _is_complete_adapter(local):
            return local, "hub"
    except Exception as e:  # noqa: BLE001
        print(f"  ! hub download failed for {cc}: {type(e).__name__}: {e}")

    drive = C.ADAPTER_DIR / cc
    if _is_complete_adapter(drive):
        return drive, "drive"
    raise FileNotFoundError(
        f"{cc}: no complete adapter on the hub ({C.HF_ADAPTER_REPO}) or Drive ({drive})")


def inventory() -> int:
    """Per-country availability across both sources. No GPU, no torch."""
    hf, dr = hf_adapter_names(), drive_adapter_names()
    union = hf | dr
    neither = sorted(set(C.COHORT) - union)
    print(f"hub   complete: {len(hf):2d} / {len(C.COHORT)}")
    print(f"drive complete: {len(dr):2d} / {len(C.COHORT)}")
    print(f"UNION usable  : {len(union):2d} / {len(C.COHORT)}")
    only_hf, only_dr = sorted(hf - dr), sorted(dr - hf)
    print(f"  hub only    : {' '.join(only_hf) or '-'}")
    print(f"  drive only  : {' '.join(only_dr) or '-'}")
    print(f"  missing both: {' '.join(neither) or '-'}")
    return 0 if not neither else 1


# ================================================================ CPU gate
def gate_cpu(question_map, specs_archived, population_archived,
             model_scores_archived, tol=1e-9, skipped_cells=None) -> int:
    """Validate population weighting and every metric against archived Paper A
    artifacts, using the archived model probabilities. No model, no GPU."""
    archive = E.ARCHIVE_DIR
    failures = []

    # (1) population distributions
    ref_pop = pd.read_csv(archive / "population_response_distributions.csv")
    keys = ["eval_country", "question_id", "option_code"]
    for frame in (population_archived, ref_pop):
        frame["option_code"] = frame["option_code"].astype(str)
    a = population_archived.sort_values(keys).reset_index(drop=True)
    b = ref_pop.sort_values(keys).reset_index(drop=True)
    a = a[a.eval_country.isin(ref_pop.eval_country.unique())]
    merged = a.merge(b[keys + ["weighted_count", "population_prob", "n_valid", "total_weight"]],
                     on=keys, suffixes=("_mine", "_ref"), how="outer", indicator=True)
    if (merged["_merge"] != "both").any():
        failures.append(f"population join mismatch: {int((merged['_merge']!='both').sum())} rows")
    d = (merged["population_prob_mine"] - merged["population_prob_ref"]).abs().max()
    print(f"population_prob max abs diff: {d:.3e}")
    if d > tol:
        failures.append(f"population_prob differs by {d:.3e}")

    # (2) metrics from archived model probabilities
    ref_metrics = pd.read_csv(archive / "survey_question_metrics_all_models.csv")
    rows = []
    for (model, eval_country, qid), group in model_scores_archived.groupby(
            ["model", "eval_country", "question_id"], sort=False):
        pop = ref_pop[(ref_pop.eval_country == eval_country) & (ref_pop.question_id == qid)]
        g = group.sort_values("option_index")
        pop = pop.sort_values("option_index")
        if len(g) != len(pop):
            failures.append(f"option count mismatch {model}/{eval_country}/{qid}")
            continue
        rows.append(g.merge(pop, on=["eval_country", "question_id", "option_index"],
                            suffixes=("", "_pop")))
    recomputed = L.calculate_question_metrics(pd.concat(rows, ignore_index=True))
    m = recomputed.merge(ref_metrics, on=["model", "eval_country", "question_id"],
                         suffixes=("_mine", "_ref"), how="inner")
    metric_cols = ["tv_distance", "js_divergence", "brier_score", "cross_entropy",
                   "wasserstein_distance", "abs_mean_error", "abs_std_error",
                   "model_mean", "population_mean"]
    print(f"metric gate on {len(m)} (model, country, question) rows")
    for col in metric_cols:
        d = (m[f"{col}_mine"] - m[f"{col}_ref"]).abs().max()
        flag = "OK" if d <= 1e-6 else "FAIL"
        print(f"  {col:22s} max abs diff {d:.3e}  {flag}")
        if d > 1e-6:
            failures.append(f"{col} differs by {d:.3e}")

    if failures:
        print("\nGATE-CPU FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nGATE-CPU PASSED: population + metrics reproduce the archived surface.")
    return 0


def _archived_scores_and_population(specs):
    """Load archived model option probabilities (base + matched adapters) and
    rebuild the (eval_country, question_id, option_index) grid used by the gate."""
    archive = E.ARCHIVE_DIR
    frames = []
    for path in sorted(archive.glob("model_option_probabilities_*.csv")):
        df = pd.read_csv(path)
        if "eval_country" not in df.columns:
            continue
        frames.append(df[["model", "eval_country", "question_id", "option_index",
                          "option_code", "option_value", "model_prob"]])
    return pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=["model", "eval_country", "question_id", "option_index"])


def _archived_numeric_grid() -> dict[str, list[str]]:
    """The archived numeric-open option grids (country-set dependent)."""
    df = pd.read_csv(E.ARCHIVE_DIR / "model_option_probabilities_base_on_CHN.csv")
    grid = {}
    for qid in E.NUMERIC_VALID_RANGES:
        sub = df[(df.question_id == qid)].sort_values("option_index")
        if len(sub):
            grid[qid] = [str(c) for c in sub["option_code"].tolist()]
    return grid


# ================================================================ torch side
def _torch():
    import torch  # noqa: PLC0415
    return torch


def prepare_prompt_for_model(tokenizer, prompt_text, max_prompt_tokens=E.EVAL_MAX_PROMPT_TOKENS):
    formatted = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt_text}], tokenize=False,
        add_generation_prompt=True, date_string=E.ARCHIVE_CHAT_DATE)
    full_ids = tokenizer(formatted, add_special_tokens=False).input_ids
    truncated = len(full_ids) > max_prompt_tokens
    model_ids = full_ids[-max_prompt_tokens:] if truncated else full_ids
    return {
        "formatted_prompt": formatted,
        "model_prompt_ids": model_ids,
        "model_prompt_text": tokenizer.decode(
            model_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False),
        "prompt_token_count_before_truncation": len(full_ids),
        "prompt_token_count_model": len(model_ids),
        "prompt_was_truncated": truncated,
    }


def sequence_logprob(model, tokenizer, prompt_text, completion_text,
                     max_prompt_tokens=E.EVAL_MAX_PROMPT_TOKENS,
                     max_completion_tokens=E.EVAL_MAX_COMPLETION_TOKENS):
    torch = _torch()
    model.eval()
    device = next(model.parameters()).device
    prepared = prepare_prompt_for_model(tokenizer, prompt_text, max_prompt_tokens)
    prompt_ids = prepared["model_prompt_ids"]
    completion_ids = tokenizer(completion_text, add_special_tokens=False).input_ids
    if len(completion_ids) > max_completion_tokens:
        completion_ids = completion_ids[:max_completion_tokens]
    if not completion_ids:
        raise ValueError("Completion tokenized to an empty sequence")

    input_ids = torch.tensor([prompt_ids + completion_ids], device=device)
    labels = torch.tensor([[-100] * len(prompt_ids) + completion_ids], device=device)
    with torch.no_grad():
        logits = model(input_ids=input_ids).logits
    shifted_logits = logits[:, :-1, :]
    shifted_labels = labels[:, 1:]
    log_probs = torch.log_softmax(shifted_logits, dim=-1)
    mask = shifted_labels.ne(-100)
    token_log_probs = log_probs.gather(-1, shifted_labels.masked_fill(~mask, 0).unsqueeze(-1)).squeeze(-1)
    total = (token_log_probs * mask).sum()
    return float(total.detach().cpu()), int(mask.sum().item())


def generate_model_answer(model, tokenizer, prompt_text,
                          max_prompt_tokens=E.EVAL_MAX_PROMPT_TOKENS,
                          max_new_tokens=E.GENERATION_MAX_NEW_TOKENS):
    torch = _torch()
    model.eval()
    device = next(model.parameters()).device
    prepared = prepare_prompt_for_model(tokenizer, prompt_text, max_prompt_tokens)
    input_ids = torch.tensor([prepared["model_prompt_ids"]], device=device)
    with torch.no_grad():
        generated = model.generate(
            input_ids=input_ids,
            attention_mask=torch.ones_like(input_ids),
            max_new_tokens=max_new_tokens,
            do_sample=E.GENERATION_DO_SAMPLE,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            use_cache=True,
        )
    gen_ids = generated[0, input_ids.shape[1]:]
    raw = tokenizer.decode(gen_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    return {"generated_answer_raw": raw, "generated_answer": raw.strip(),
            "generated_token_count": int(gen_ids.numel())}


def score_model_questions(model, tokenizer, model_name, question_specs,
                          prompt_country=None, progress=True):
    rows = []
    for i, spec in enumerate(question_specs, 1):
        prompt_text = L.build_survey_user_prompt(spec, prompt_country=prompt_country)
        prepared = prepare_prompt_for_model(tokenizer, prompt_text)

        if E.SAVE_GENERATED_ANSWERS:
            gen = generate_model_answer(model, tokenizer, prompt_text)
        else:
            gen = {"generated_answer_raw": None, "generated_answer": None,
                   "generated_token_count": 0}
        gen_code = gen["generated_answer"] if gen["generated_answer"] in spec["codes"] else None

        option_scores, option_tokens = [], []
        for code in spec["codes"]:
            logp, ntok = sequence_logprob(model, tokenizer, prompt_text,
                                          f"{E.COMPLETION_PREFIX}{code}")
            option_scores.append(logp if not E.LENGTH_NORMALIZE_OPTION_LOGPROBS else logp / ntok)
            option_tokens.append(ntok)
        probs = L.stable_softmax(option_scores, E.OPTION_SCORE_TEMPERATURE)

        for idx, (code, label, score, ntok, prob) in enumerate(
                zip(spec["codes"], spec["labels"], option_scores, option_tokens, probs)):
            rows.append({
                "model": model_name, "prompt_country": prompt_country,
                "question_id": spec["question_id"], "question_text": spec["question_text"],
                "response_type": spec["response_type"], "gps_dimension": spec["gps_dimension"],
                "is_ordered": spec["is_ordered"], "is_numeric_open": spec["is_numeric_open"],
                "option_index": idx, "option_code": code, "option_value": float(code),
                "option_label": label, "option_logprob": score, "option_token_count": ntok,
                "model_prob": float(prob),
                "prompt_text": prompt_text, "formatted_prompt": prepared["formatted_prompt"],
                "complete_prompt_model_received": prepared["model_prompt_text"],
                "prompt_token_count_before_truncation": prepared["prompt_token_count_before_truncation"],
                "prompt_token_count_model": prepared["prompt_token_count_model"],
                "prompt_was_truncated": prepared["prompt_was_truncated"],
                "generated_answer_raw": gen["generated_answer_raw"],
                "generated_answer": gen["generated_answer"],
                "generated_answer_code": gen_code,
                "generated_answer_is_valid": gen_code is not None,
                "generated_token_count": gen["generated_token_count"],
            })
        if progress and (i % 8 == 0 or i == len(question_specs)):
            print(f"    {model_name}: {i}/{len(question_specs)} questions", flush=True)

    df = pd.DataFrame(rows)
    checks = df.groupby("question_id")["model_prob"].sum().sub(1.0).abs()
    if checks.max() > 1e-8:
        raise AssertionError(f"{model_name}: option probabilities do not sum to one")
    return df


def load_base_model_and_tokenizer():
    import torch  # noqa: PLC0415
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    tok = AutoTokenizer.from_pretrained(C.MODEL_NAME)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    # Match the notebook that produced the archived readout. Passing torch_dtype
    # or a forced fast tokenizer changes the 4-bit result.
    model = AutoModelForCausalLM.from_pretrained(
        C.MODEL_NAME, quantization_config=bnb, device_map="auto")
    model.eval()
    return model, tok


def cleanup_cuda():
    import gc  # noqa: PLC0415
    gc.collect()
    torch = _torch()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ================================================================ orchestration
def expected_rows(specs) -> int:
    return sum(len(s["codes"]) for s in specs)


def score_file(model_name) -> Path:
    return E.SCORE_DIR / f"{model_name}_option_probabilities.csv"


def _load_or_skip(model_name, specs, force):
    path = score_file(model_name)
    if path.exists() and not force:
        df = pd.read_csv(path)
        if len(df) == expected_rows(specs):
            print(f"  {model_name}: scored already ({len(df)} rows), skip")
            return df
        print(f"  {model_name}: partial ({len(df)} rows), rescoring")
    return None


def build_pairs(model_scores: pd.DataFrame, pairs: str, model_kind: str,
                model_country: str | None, eval_countries: list[str]) -> pd.DataFrame:
    """Broadcast a model's (population-independent) scores to eval countries."""
    if model_kind == "adapter":
        targets = [model_country] if pairs == "matched" else list(eval_countries)
    elif model_kind == "persona":
        targets = [model_country] if pairs == "matched" else list(eval_countries)
    else:  # base: always evaluated against all populations
        targets = list(eval_countries)
    out = []
    for cc in targets:
        part = model_scores.copy()
        part["eval_country"] = cc
        out.append(part)
    return pd.concat(out, ignore_index=True)


def _run_model_only(a) -> int:
    """Score from a local spec. Respondent files are never opened."""
    import score_runtime as R
    if not a.spec_file or not a.run_id:
        print("refusing: --model-only requires --spec-file and --run-id")
        return 2
    try:
        R.require_path_token("run_id", a.run_id)
    except ValueError as exc:
        print(f"refusing: {exc}")
        return 2
    spec_path = Path(a.spec_file)
    if not spec_path.is_file():
        print(f"refusing: spec file not found: {spec_path}")
        return 2
    spec = R.load_spec(spec_path)
    missing = [q.get("question_id") for q in spec["questions"] if not q.get("question_text")]
    if missing:
        print(f"refusing: scoring spec is missing question_text for {missing[:5]}")
        return 2
    if a.dry_run_spec:
        print(f"spec ok: {spec['n_questions']} questions, battery={spec['battery']}")
        return 0
    marker_path = Path(a.gate_marker) if a.gate_marker else None
    if marker_path is None or not marker_path.is_file():
        print("BLOCKED: adapter-path gate marker missing; no model will be loaded")
        return 2
    marker = json.loads(marker_path.read_text())
    if not marker.get("gate_pass"):
        print("BLOCKED: gate_pass is not true; no model will be loaded")
        return 2
    if not os.environ.get("HF_TOKEN"):
        print("refusing: HF_TOKEN is required before model-only scoring")
        return 2
    return _score_model_only_gpu(a, spec)


def _score_model_only_gpu(a, spec: dict) -> int:
    """GPU path. Reached only after the spec, gate marker, and token checks."""
    import score_runtime as R
    revision = R.require_revision(a.adapter_revision)
    questions = spec["questions"]
    arms = {x.strip() for x in a.arms.split(",") if x.strip()}
    countries = [c.upper() for c in (a.countries or C.COHORT)]
    unknown = [c for c in countries if c not in C.COHORT]
    if unknown:
        print(f"refusing unknown: {unknown}")
        return 2
    E.SAVE_GENERATED_ANSWERS = False
    base, tok = load_base_model_and_tokenizer()
    store = R.HuggingFaceArtifactStore()
    local_dir = E.DATA_ROOT / "local_scores"
    code_rev = R.code_revision(C.REPO)
    spec_sha = spec.get("spec_sha256", "")

    def persist(frame, model_name, adapter_sha, adapter_revision=""):
        out = frame.copy()
        out["run_id"] = a.run_id
        out["adapter_revision"] = adapter_revision
        R.persist_unit_scores(
            scores=out, model_name=model_name, run_id=a.run_id,
            repo=a.artifact_repo, hub=store, adapter_sha256=adapter_sha,
            code_revision=code_rev, local_dir=local_dir, spec_sha=spec_sha,
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
                source="score_cohort.py",
                role="live",
                includes=["score_model_questions", "persist"],
                excludes=["session_idle"],
                hardware=ledger.hardware_snapshot(),
                provenance={"run_id": a.run_id, "adapter_revision": revision},
            ))
            ledger.try_upload_ledger(a.artifact_repo, a.run_id)
        except Exception as exc:  # noqa: BLE001
            print(f"compute ledger: {type(exc).__name__}: {exc}")
        return result

    if "base" in arms:
        print("scoring base (unconditioned, model-only)")
        _clock("base", lambda: persist(
            score_model_questions(base, tok, "base", questions, prompt_country=None),
            "base", hashlib.sha256(C.MODEL_NAME.encode()).hexdigest()))
    if "persona" in arms:
        for cc in countries:
            name = f"persona_{cc}"
            print(f"scoring {name}")
            _clock(name, lambda name=name, cc=cc: persist(
                score_model_questions(base, tok, name, questions, prompt_country=cc),
                name, hashlib.sha256(f"persona:{cc}".encode()).hexdigest()))
    if "adapter" in arms:
        from peft import PeftModel
        peft = None
        for cc in countries:
            adapter_dir, source = R.resolve_adapter(cc, revision, E.ADAPTER_CACHE_DIR)
            print(f"  {cc}: adapter from {source}")
            if peft is None:
                peft = PeftModel.from_pretrained(
                    base, str(adapter_dir), adapter_name=cc, is_trainable=False)
            else:
                peft.load_adapter(str(adapter_dir), adapter_name=cc, is_trainable=False)
            peft.set_adapter(cc)
            name = f"{cc}_adapter"
            print(f"scoring {name}")
            _clock(name, lambda name=name, adapter_dir=adapter_dir: persist(
                score_model_questions(peft, tok, name, questions, prompt_country=None),
                name, R.adapter_sha256(adapter_dir), revision))
        del peft
        cleanup_cuda()
    print("model-only scoring complete")
    print(f"compute ledger: {C.DATA_ROOT / 'compute_ledger.jsonl'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", nargs="*", help="adapter countries (default: full cohort)")
    ap.add_argument("--arms", default="base,adapter",
                    help="comma list of base,adapter,persona (default base,adapter)")
    ap.add_argument("--pairs", choices=["matched", "all"], default="matched")
    ap.add_argument("--force", action="store_true", help="rescore even if outputs exist")
    ap.add_argument("--gate", action="store_true", help="GPU: reproduce archived base-on-CHN")
    ap.add_argument("--gate-cpu", action="store_true",
                    help="CPU only: reproduce archived population + metrics")
    ap.add_argument("--inventory", action="store_true",
                    help="report adapter availability on the hub vs Drive, then exit")
    ap.add_argument("--model-only", action="store_true",
                    help="score from a local spec; do not read respondent files")
    ap.add_argument("--spec-file", help="local scoring spec JSON, including question text")
    ap.add_argument("--run-id", help="artifact run id, a safe path token")
    ap.add_argument("--adapter-revision", help="full adapter repository SHA")
    ap.add_argument("--artifact-repo", default="Bonorinoa/SCA2-paper-b-artifacts")
    ap.add_argument("--gate-marker", help="JSON marker from the exact-weights adapter gate")
    ap.add_argument("--dry-run-spec", action="store_true",
                    help="validate the spec and exit before any model load")
    a = ap.parse_args()

    assert E.DATA_ROOT == C.DATA_ROOT, (E.DATA_ROOT, C.DATA_ROOT)
    if a.inventory:
        return inventory()
    if a.model_only:
        return _run_model_only(a)
    if not a.gate_cpu and not a.gate:
        print("refusing: legacy population-join scoring is disabled. "
              "Use --model-only with a local scoring spec.")
        return 2
    arms = {x.strip() for x in a.arms.split(",") if x.strip()}
    countries = [c.upper() for c in (a.countries or C.COHORT)]
    unknown = [c for c in countries if c not in C.COHORT]
    if unknown:
        print(f"refusing unknown: {unknown}")
        return 2

    question_map = L.load_question_map()

    # ---- CPU-only gate: no model, no tokenizer, no torch -------------------
    if a.gate_cpu:
        grid = _archived_numeric_grid()
        specs = L.build_question_specs(question_map, {}, numeric_support=grid)
        # The archived metric file was produced from these eight populations.
        archive_countries = ["CHN", "JPN", "GBR", "USA", "MEX", "ARG", "DEU", "RUS"]
        frames = L.load_survey_frames(archive_countries)
        skips: list[dict] = []
        population = L.build_population_distributions(specs, frames, skipped=skips)
        skipped_cells = {(s["eval_country"], s["question_id"]) for s in skips}
        archived_scores = _archived_scores_and_population(specs)
        return gate_cpu(question_map, specs, population, archived_scores,
                        skipped_cells=skipped_cells)

    # ---- build the item grid and the populations ---------------------------
    frames = L.load_survey_frames(countries)
    specs = L.build_question_specs(question_map, frames)
    print(f"items: {len(specs)} questions / {expected_rows(specs)} option rows "
          f"| eval countries: {len(countries)}")

    base_model, tok = load_base_model_and_tokenizer()

    if a.gate:
        chn_grid = _archived_numeric_grid()
        gate_specs = L.build_question_specs(question_map, frames, numeric_support=chn_grid)
        scored = score_model_questions(base_model, tok, "base", gate_specs, prompt_country=None)
        ref = pd.read_csv(E.ARCHIVE_DIR / "model_option_probabilities_base_on_CHN.csv")
        ref = ref[["question_id", "option_index", "option_logprob", "model_prob"]]
        m = scored.merge(ref, on=["question_id", "option_index"], suffixes=("_mine", "_ref"))
        dl = (m["option_logprob_mine"] - m["option_logprob_ref"]).abs().max()
        dp = (m["model_prob_mine"] - m["model_prob_ref"]).abs().max()
        print(f"GATE (base on CHN): n={len(m)} | max |dlogprob|={dl:.4f} | max |dprob|={dp:.6f}")
        ok = dl < 1e-2 and dp < 1e-4
        print("GATE PASSED" if ok else "GATE FAILED — do not trust the cohort readout")
        return 0 if ok else 1

    from peft import PeftModel  # noqa: PLC0415
    E.SCORE_DIR.mkdir(parents=True, exist_ok=True)
    all_option_probs = []
    adapter_sources: dict[str, str] = {}
    t0 = time.time()

    # ---- base (unconditioned) --------------------------------------------
    if "base" in arms:
        cached = _load_or_skip("base", specs, a.force)
        if cached is None:
            print("scoring base (unconditioned)")
            cached = score_model_questions(base_model, tok, "base", specs, prompt_country=None)
            cached.to_csv(score_file("base"), index=False)
        all_option_probs.append(cached)

    # ---- persona (country-named prompt, base weights) --------------------
    if "persona" in arms:
        for cc in countries:
            name = f"persona_{cc}"
            cached = _load_or_skip(name, specs, a.force)
            if cached is None:
                print(f"scoring {name} (country-named prompt)")
                cached = score_model_questions(base_model, tok, name, specs, prompt_country=cc)
                cached.to_csv(score_file(name), index=False)
            all_option_probs.append(cached)

    # ---- adapters (loaded once, swapped per country) ---------------------
    if "adapter" in arms:
        todo = []
        for cc in countries:
            cached = _load_or_skip(f"{cc}_adapter", specs, a.force)
            if cached is None:
                todo.append(cc)
            else:
                all_option_probs.append(cached)
        if todo:
            adapter_dirs: dict[str, Path] = {}
            for cc in todo:
                adapter_dirs[cc], adapter_sources[cc] = resolve_adapter(cc)
                print(f"  {cc}: adapter from {adapter_sources[cc]}")
            first, rest = todo[0], todo[1:]
            peft = PeftModel.from_pretrained(base_model, str(adapter_dirs[first]),
                                             adapter_name=first, is_trainable=False)
            for cc in rest:
                peft.load_adapter(str(adapter_dirs[cc]), adapter_name=cc, is_trainable=False)
            for cc in todo:
                print(f"scoring {cc}_adapter")
                peft.set_adapter(cc)
                df = score_model_questions(peft, tok, f"{cc}_adapter", specs, prompt_country=None)
                df.to_csv(score_file(f"{cc}_adapter"), index=False)
                all_option_probs.append(df)
            del peft
            cleanup_cuda()

    # ---- combine, join to populations, write metrics ----------------------
    model_scores_long = pd.concat(all_option_probs, ignore_index=True)
    model_scores_long.to_csv(E.SCORE_DIR / "model_option_probabilities.csv", index=False)

    eval_rows = []
    for name, group in model_scores_long.groupby("model"):
        if name == "base":
            kind, mc = "base", None
        elif name.startswith("persona_"):
            kind, mc = "persona", name[len("persona_"):]
        else:
            kind, mc = "adapter", name.replace("_adapter", "")
        eval_rows.append(build_pairs(group, a.pairs, kind, mc, countries))
    model_scores_eval = pd.concat(eval_rows, ignore_index=True)

    population = L.build_population_distributions(specs, frames)
    population.to_csv(E.SCORE_DIR / "population_response_distributions.csv", index=False)
    option_eval = L.join_option_evaluation(model_scores_eval, population)
    option_eval.to_csv(E.SCORE_DIR / "survey_option_evaluation_all_models.csv", index=False)
    metrics = L.calculate_question_metrics(option_eval)
    metrics.to_csv(E.SCORE_DIR / "survey_question_metrics_all_models.csv", index=False)

    manifest = {
        "protocol": "paper_b readout (mirrors Paper A DPO_eval_WVS notebook)",
        "model_name": C.MODEL_NAME, "bank_run_id": C.BANK_RUN_ID,
        "question_map": str(E.QUESTION_MAP_FILE.relative_to(C.REPO)),
        "question_map_sha256_16": _hash_file(E.QUESTION_MAP_FILE),
        "n_questions": len(specs), "n_option_rows": expected_rows(specs),
        "weight_column": E.WEIGHT_COLUMN, "completion_prefix": E.COMPLETION_PREFIX,
        "temperature": E.OPTION_SCORE_TEMPERATURE,
        "length_normalize": E.LENGTH_NORMALIZE_OPTION_LOGPROBS,
        "max_prompt_tokens": E.EVAL_MAX_PROMPT_TOKENS,
        "max_completion_tokens": E.EVAL_MAX_COMPLETION_TOKENS,
        "arms": sorted(arms), "pairs": a.pairs,
        "adapter_source": {"hub": C.HF_ADAPTER_REPO, "drive": str(C.ADAPTER_DIR)},
        "adapter_sources": adapter_sources,
        "countries_scored": countries, "eval_countries": countries,
        "git_sha": _git_sha(), "elapsed_min": round((time.time() - t0) / 60, 2),
    }
    E.SCORE_MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))
    print(f"\nscored {model_scores_long['model'].nunique()} models -> {E.SCORE_DIR} "
          f"in {manifest['elapsed_min']} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
