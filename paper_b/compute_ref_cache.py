#!/usr/bin/env python3
"""Paper B — compute the SHARED reference log-probability cache ONCE (GPU).

The base-model reference log-prob of a (prompt, completion) pair is
country-independent, so this pass covers the 526 train prompts x 2 response
texts = 1052 pairs and is reused by every country's data-prep.

Resumable: pairs already present in config.REF_CACHE_FILE are skipped, and each
new pair is appended immediately, so a mid-run death costs only the in-flight
pair. Writes an updated manifest.

Usage (on a Colab GPU session):
  export HF_TOKEN=...
  SCA2_PB_DATA_ROOT=/content/drive/MyDrive/SCA2_paper_b python paper_b/compute_ref_cache.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
from lib import build_user_prompt, load_country, make_shared_split, response_pair, verify_shared_questions


def main() -> int:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if not torch.cuda.is_available():
        print("no CUDA available — run this on a GPU session")
        return 2

    # ---- rules of engagement are unity: build the split from the shared bank ----
    by_prompt_all = {}
    for cc in C.COHORT:
        _, by_prompt = load_country(C.BANK_DIR / C.BANK_FILE.format(cc=cc))
        by_prompt_all[cc] = by_prompt
    all_prompts = verify_shared_questions(by_prompt_all, C.COHORT[0])
    train_prompts, _ = make_shared_split(all_prompts, C.TRAIN_FRAC, C.SEED)
    shared_pairs = {p: response_pair(by_prompt_all[C.COHORT[0]][p]) for p in all_prompts}

    wanted = [(p, c) for p in sorted(train_prompts) for c in sorted(shared_pairs[p])]
    print(f"train prompts: {len(train_prompts)} | (prompt, completion) pairs to score: {len(wanted)}")

    C.DATA_ROOT.mkdir(parents=True, exist_ok=True)
    have = set()
    if C.REF_CACHE_FILE.exists():
        for line in open(C.REF_CACHE_FILE):
            if line.strip():
                r = json.loads(line)
                have.add((r["prompt"], r["completion"]))
        print(f"existing cache: {len(have)} pairs — skipping those")
    todo = [(p, c) for (p, c) in wanted if (p, c) not in have]
    print(f"pairs to compute: {len(todo)}")
    if not todo:
        print("cache already complete")
        return 0

    # ---- HF auth ----
    token = os.environ.get("HF_TOKEN")
    if token:
        from huggingface_hub import login
        login(token=token, add_to_git_credential=False)
    else:
        from huggingface_hub import notebook_login
        notebook_login()

    compute_dtype = torch.float16
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=compute_dtype, bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(C.MODEL_NAME, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        C.MODEL_NAME, quantization_config=bnb, device_map={"": 0},
        torch_dtype=compute_dtype, low_cpu_mem_usage=True)
    model.eval()

    def fmt(prompt_text: str) -> str:
        return tok.apply_chat_template([{"role": "user", "content": build_user_prompt(prompt_text)}],
                                       tokenize=False, add_generation_prompt=True)

    @torch.no_grad()
    def seq_logprob(prompt_text: str, completion_text: str) -> float:
        prompt_ids = tok(fmt(prompt_text), add_special_tokens=False).input_ids
        if len(prompt_ids) > C.MAX_PROMPT_TOKENS:
            prompt_ids = prompt_ids[-C.MAX_PROMPT_TOKENS:]
        comp_ids = tok(completion_text, add_special_tokens=False).input_ids
        if len(comp_ids) > C.MAX_COMPLETION_TOKENS:
            comp_ids = comp_ids[:C.MAX_COMPLETION_TOKENS]
        input_ids = prompt_ids + comp_ids
        if len(input_ids) < 2 or not comp_ids:
            return float("-inf")
        labels = ([-100] * len(prompt_ids)) + comp_ids
        ids_t = torch.tensor([input_ids], device=model.device)
        lab_t = torch.tensor([labels], device=model.device)
        logits = model(input_ids=ids_t).logits
        log_probs = torch.log_softmax(logits, dim=-1)[:, :-1, :]
        shifted = lab_t[:, 1:]
        mask = shifted.ne(-100)
        gold = shifted.clone(); gold[~mask] = 0
        tok_lp = log_probs.gather(-1, gold.unsqueeze(-1)).squeeze(-1) * mask
        return float(tok_lp.sum().detach().cpu().to(torch.float32))

    log = open(C.LOG_DIR.joinpath("ref_cache.log") if C.LOG_DIR.exists() else os.devnull, "a")
    t0 = time.time()
    n = 0
    with open(C.REF_CACHE_FILE, "a", encoding="utf-8") as f:
        for (p, c) in todo:
            v = seq_logprob(p, c)
            f.write(json.dumps({"prompt": p, "completion": c, "ref_logp": v}, ensure_ascii=False) + "\n")
            f.flush(); os.fsync(f.fileno())
            n += 1
            if n % 25 == 0 or n == len(todo):
                el = time.time() - t0
                msg = f"  {n}/{len(todo)} pairs | {el/60:.1f} min | {el/max(n,1):.2f}s/pair"
                print(msg); log.write(msg + "\n"); log.flush()

    C.REF_MANIFEST_FILE.write_text(json.dumps({
        "model_name": C.MODEL_NAME, "prompt_format_version": C.PROMPT_FORMAT_VERSION,
        "max_prompt_tokens": C.MAX_PROMPT_TOKENS, "max_completion_tokens": C.MAX_COMPLETION_TOKENS,
        "train_frac": C.TRAIN_FRAC, "seed": C.SEED,
        "n_train_prompts": len(train_prompts), "n_pairs_total": len(wanted),
        "n_pairs_computed_this_run": n,
        "elapsed_min": round((time.time() - t0) / 60, 2),
        "bank_run_id": C.BANK_RUN_ID,
    }, indent=2))
    print(f"done: +{n} pairs -> {C.REF_CACHE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
