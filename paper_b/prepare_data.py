#!/usr/bin/env python3
"""Paper B — prepare per-country DPO files from the shared bank + shared ref cache.

CPU-only when the ref cache exists (no GPU, no HF login needed).
Writes to config.PREPARED_DIR:
  {cc}_train.jsonl         526 rows (raw prompts)
  {cc}_eval.jsonl          132 rows
  {cc}_train_with_ref.jsonl 526 rows + ref_chosen_logps/ref_rejected_logps
Resumable: a country with an already-complete train_with_ref file is skipped
unless --force.

Usage:
  python paper_b/prepare_data.py                 # all 42
  python paper_b/prepare_data.py --countries ARG BGD
  python paper_b/prepare_data.py --force
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
from lib import (cache_coverage, load_country, load_shared_cache, make_shared_split,
                 response_pair, verify_shared_questions, write_jsonl)

EXPECTED_TRAIN = int(C.N_ROWS * C.TRAIN_FRAC)   # 526
EXPECTED_EVAL = C.N_ROWS - EXPECTED_TRAIN       # 132


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", nargs="*", default=C.COHORT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    countries = [c.upper() for c in args.countries]
    unknown = [c for c in countries if c not in C.COHORT]
    if unknown:
        print(f"refusing: not in frozen cohort: {unknown}")
        return 2

    # ---- load all cohort files (need the full cohort to verify the shared bank) ----
    by_prompt_all, rows_all = {}, {}
    for cc in C.COHORT:
        p = C.BANK_DIR / C.BANK_FILE.format(cc=cc)
        rows, by_prompt = load_country(p)
        rows_all[cc], by_prompt_all[cc] = rows, by_prompt

    all_prompts = verify_shared_questions(by_prompt_all, C.COHORT[0])
    train_prompts, eval_prompts = make_shared_split(all_prompts, C.TRAIN_FRAC, C.SEED)
    shared_pairs = {p: response_pair(by_prompt_all[C.COHORT[0]][p]) for p in all_prompts}
    print(f"shared split: {len(train_prompts)} train / {len(eval_prompts)} eval")
    assert len(train_prompts) == EXPECTED_TRAIN, (len(train_prompts), EXPECTED_TRAIN)

    # ---- ref cache is required ----
    if not C.REF_CACHE_FILE.exists():
        print(f"ref cache missing: {C.REF_CACHE_FILE}")
        print("run paper_b/compute_ref_cache.py once on a GPU first.")
        return 3
    cache = load_shared_cache(C.REF_CACHE_FILE)
    missing = cache_coverage(cache, train_prompts, shared_pairs)
    if missing:
        print(f"ref cache incomplete: {len(missing)} missing (prompt, completion) pairs")
        print("  e.g.", missing[0][0][:60])
        return 3
    print(f"ref cache OK: {len(cache)} pairs")

    C.PREPARED_DIR.mkdir(parents=True, exist_ok=True)
    done = []
    for cc in countries:
        out = C.PREPARED_DIR / f"{cc}_train_with_ref.jsonl"
        if out.exists() and not args.force:
            n = sum(1 for _ in open(out))
            if n == EXPECTED_TRAIN:
                print(f"{cc}: already prepared ({n}), skip")
                done.append(cc)
                continue

        by_prompt = by_prompt_all[cc]
        train_rows = []
        for i, prompt in enumerate(sorted(train_prompts)):
            row = dict(by_prompt[prompt])
            row["country"] = cc
            row["item_id"] = f"{cc}_train_{i:04d}"
            row["ref_chosen_logps"] = cache[(row["prompt"], row["chosen"])]
            row["ref_rejected_logps"] = cache[(row["prompt"], row["rejected"])]
            train_rows.append(row)

        eval_rows = []
        for i, prompt in enumerate(sorted(eval_prompts)):
            row = dict(by_prompt[prompt])
            row["country"] = cc
            row["item_id"] = f"{cc}_eval_{i:04d}"
            eval_rows.append(row)

        write_jsonl([{k: v for k, v in r.items() if k not in ("ref_chosen_logps", "ref_rejected_logps")}
                     for r in train_rows], C.PREPARED_DIR / f"{cc}_train.jsonl")
        write_jsonl(eval_rows, C.PREPARED_DIR / f"{cc}_eval.jsonl")
        write_jsonl(train_rows, out)
        print(f"{cc}: wrote train {len(train_rows)} / eval {len(eval_rows)} -> {out}")
        done.append(cc)

    manifest = {
        "protocol": "paper_b frozen 2026-10-09",
        "model_name": C.MODEL_NAME,
        "prompt_format_version": C.PROMPT_FORMAT_VERSION,
        "train_frac": C.TRAIN_FRAC, "seed": C.SEED,
        "n_train": len(train_prompts), "n_eval": len(eval_prompts),
        "ref_cache_file": str(C.REF_CACHE_FILE), "n_ref_pairs": len(cache),
        "countries_prepared": sorted(done),
    }
    (C.PREPARED_DIR / "prepare_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nprepared {len(done)} countries -> {C.PREPARED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
