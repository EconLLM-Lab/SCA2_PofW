#!/usr/bin/env python3
"""20_build_rung_datasets.py — Gate-1 data prep for the rung-mixture pilot.

Reads Ksennia's variant bank (commit 9bc6f4f), builds per-rung SFT train/holdout
files (stratified 80/20 by GPS dimension, seed 20260822) and the WVS scoring
bundle (35 questions x options, exact eval prompts reused verbatim).
Emits gate_1_report.json. No GPU, no model calls.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
BANK = REPO / "DPO_train_test" / "generated_response_variants_3.csv"
OUTDIR = REPO / "data" / "phase2" / "derived" / "rung_mix"
CANON = REPO / "data" / "phase2" / "raw" / "wvs" / "usamex_canonical"
SEED = 20260822
RUNGS = [-3, -2, -1, 1, 2, 3]
TRAIN_FRAC = 0.80


def log_stage(msg: str) -> None:
    print(f"\n=== {msg} " + "=" * max(0, 66 - len(msg)))


def main() -> None:
    log_stage("Loading variant bank")
    df = pd.read_csv(BANK)
    assert len(df) == 3594, f"bank shape changed: {len(df)}"
    assert sorted(df.target_level.unique()) == RUNGS
    assert (df.generation_status == "ok").all()
    # provenance hash
    h = hashlib.sha256(BANK.read_bytes()).hexdigest()[:16]

    OUTDIR.mkdir(parents=True, exist_ok=True)

    log_stage("Shared stratified 80/20 partition (identical across all rungs)")
    report: dict = {"bank_sha256_16": h, "seed": SEED, "train_frac": TRAIN_FRAC,
                    "split_design": "shared_partition_v1.1",
                    "rungs": {}}
    # ONE partition of the UNIQUE PROMPT UNIVERSE (599 prompts, stratified by their
    # gps_dimension), applied identically to every rung -> all six holdouts are the
    # SAME ~120 prompts (Gate 2 fully paired).
    pu = df.drop_duplicates("original_index")[["original_index", "gps_dimension"]]
    assert (df.groupby("original_index")["gps_dimension"].nunique() == 1).all(), \
        "prompt maps to multiple GPS dimensions"
    train_oids, hold_oids = [], []
    for dim, gd in pu.groupby("gps_dimension"):
        oids = list(gd.original_index)
        rng2 = random.Random(f"{SEED}-{dim}")  # deterministic per stratum
        rng2.shuffle(oids)
        n_train = round(len(oids) * TRAIN_FRAC)
        train_oids.extend(oids[:n_train])
        hold_oids.extend(oids[n_train:])
    train_set, hold_set = set(train_oids), set(hold_oids)
    assert not (train_set & hold_set), "global split leakage"
    assert len(train_set | hold_set) == len(pu), "partition lost prompts"

    for k in RUNGS:
        g = df[df.target_level == k]
        assert g.original_index.nunique() == len(pu), f"rung {k} universe mismatch"
        tr = g[g.original_index.isin(train_set)]
        ho = g[g.original_index.isin(hold_set)]
        # Gate 1 checks under the shared design
        leak = set(tr.original_index) & set(ho.original_index)
        rec = {
            "n_train": len(tr), "n_holdout": len(ho),
            "dims_train": tr.gps_dimension.value_counts().to_dict(),
            "dims_holdout": ho.gps_dimension.value_counts().to_dict(),
            "prompt_leakage": len(leak),
        }
        report["rungs"][str(k)] = rec
        for name, part in [("train", tr), ("holdout", ho)]:
            out = part[["original_index", "gps_dimension", "target_level",
                        "level_description", "prompt", "generated_response",
                        "response_A_original", "response_B_original"]]
            path = OUTDIR / f"sft_rung_{k:+d}_{name}.jsonl"
            out.to_json(path, orient="records", lines=True, force_ascii=False)
        print(f"  rung {k:+d}: train {len(tr)}, holdout {len(ho)}, "
              f"leakage {len(leak)}")

    log_stage("Building WVS scoring bundle (verbatim eval prompts)")
    # Reuse the exact prompts the models saw during canonical eval.
    src = pd.read_csv(CANON / "model_option_probabilities_base_on_USA.csv")
    cols = ["question_id", "question_text", "response_type", "gps_dimension",
            "is_ordered", "option_index", "option_code", "option_value",
            "option_label"]
    bundle = src[cols].copy()
    prompts = src.drop_duplicates("question_id")[
        ["question_id", "prompt_text", "formatted_prompt"]]
    bundle = bundle.merge(prompts, on="question_id", how="left")
    # sanity: identical prompts across models?
    other = pd.read_csv(CANON / "model_option_probabilities_USA_adapter_on_USA.csv",
                        usecols=["question_id", "prompt_text"])
    m = bundle.merge(other.drop_duplicates(), on="question_id",
                     suffixes=("", "_chk"))
    assert (m.prompt_text == m.prompt_text_chk).all(), "eval prompt drift!"
    bundle.to_parquet(OUTDIR / "wvs_scoring_bundle.parquet", index=False)
    report["scoring"] = {
        "questions": int(bundle.question_id.nunique()),
        "options": int(len(bundle)),
        "prompt_source": "usamex_canonical/base_on_USA (verified vs adapter file)",
    }
    print(f"  questions {bundle.question_id.nunique()}, options {len(bundle)}")

    gate_ok = all(r["prompt_leakage"] == 0 and r["n_holdout"] >= 40
                  for r in report["rungs"].values())
    report["gate_1"] = "PASS" if gate_ok else "FAIL"
    (OUTDIR / "gate_1_report.json").write_text(json.dumps(report, indent=2))
    log_stage(f"GATE 1: {report['gate_1'].upper()} -> wrote {OUTDIR}")


if __name__ == "__main__":
    main()
