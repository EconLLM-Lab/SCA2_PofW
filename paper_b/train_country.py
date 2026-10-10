#!/usr/bin/env python3
"""Paper B — train ONE country adapter (GPU), mirroring DPO_train_599_multi_country.ipynb.

Reads config.PREPARED_DIR/{cc}_train_with_ref.jsonl, writes the adapter to
config.ADAPTER_DIR/{cc}/. Resumable: an existing adapter is skipped unless --force.

Usage (Colab GPU):
  export HF_TOKEN=...
  SCA2_PB_DATA_ROOT=/content/drive/MyDrive/SCA2_paper_b python paper_b/train_country.py --country ARG
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


def train_country(country_code: str) -> Path:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import DPOConfig, DPOTrainer

    data_file = C.PREPARED_DIR / f"{country_code}_train_with_ref.jsonl"
    if not data_file.exists():
        raise FileNotFoundError(f"missing {data_file} — run prepare_data.py first")
    out_dir = C.ADAPTER_DIR / country_code

    free, total = torch.cuda.mem_get_info()
    print(f"===== {country_code} ===== VRAM free {free/1024**3:.2f}/{total/1024**3:.2f} GiB")

    compute_dtype = torch.float16
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=compute_dtype, bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(C.MODEL_NAME, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        C.MODEL_NAME, quantization_config=bnb, device_map={"": 0},
        low_cpu_mem_usage=True, torch_dtype=torch.float16)
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()

    ds = load_dataset("json", data_files={"train": str(data_file)})["train"]
    required = {"prompt", "chosen", "rejected", "ref_chosen_logps", "ref_rejected_logps"}
    missing = required - set(ds.column_names)
    if missing:
        raise ValueError(f"{data_file} missing columns {sorted(missing)}")

    def fmt(ex):
        ex["prompt"] = tok.apply_chat_template(
            [{"role": "user", "content": __import__("lib").build_user_prompt(ex["prompt"])}],
            tokenize=False, add_generation_prompt=True)
        return ex

    ds = ds.map(fmt)

    model = get_peft_model(model, LoraConfig(
        r=C.LORA_R, lora_alpha=C.LORA_ALPHA, lora_dropout=C.LORA_DROPOUT,
        target_modules=C.LORA_TARGETS, bias="none", task_type="CAUSAL_LM"))
    for _, p in model.named_parameters():
        if p.requires_grad:
            p.data = p.data.to(torch.float16)
    model.print_trainable_parameters()

    args = DPOConfig(
        output_dir=str(out_dir), beta=C.DPO_BETA, max_length=C.MAX_LENGTH,
        truncation_mode="keep_end", per_device_train_batch_size=C.PER_DEVICE_BATCH_SIZE,
        gradient_accumulation_steps=C.GRADIENT_ACCUMULATION_STEPS,
        num_train_epochs=C.NUM_TRAIN_EPOCHS, learning_rate=C.LEARNING_RATE,
        lr_scheduler_type="cosine", logging_steps=10, save_strategy="steps",
        save_steps=5, save_total_limit=2, report_to="none", fp16=True, bf16=False)

    trainer = DPOTrainer(model=model, ref_model=None, args=args,
                         train_dataset=ds, processing_class=tok)
    for _, p in trainer.model.named_parameters():
        if p.requires_grad and p.dtype != torch.float32:
            p.data = p.data.to(torch.float32)
    tr = next(p for p in trainer.model.parameters() if p.requires_grad)
    print("trainable dtype:", tr.dtype, "| mixed_precision:", trainer.accelerator.mixed_precision)

    t0 = time.time()
    trainer.train()
    mins = (time.time() - t0) / 60

    out_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(out_dir))
    tok.save_pretrained(str(out_dir))
    # prune intermediate checkpoints: they dominate the artifact size and are
    # never used (a crashed country is retrained whole, not resumed mid-training)
    import glob as _glob
    import shutil as _shutil
    for ck in _glob.glob(str(out_dir / "checkpoint-*")):
        _shutil.rmtree(ck, ignore_errors=True)
    (out_dir / "run_record.json").write_text(json.dumps({
        "country": country_code, "adapter_dir": str(out_dir),
        "train_file": str(data_file), "n_train": len(ds),
        "model_name": C.MODEL_NAME, "beta": C.DPO_BETA, "lr": C.LEARNING_RATE,
        "epochs": C.NUM_TRAIN_EPOCHS, "lora": {"r": C.LORA_R, "alpha": C.LORA_ALPHA},
        "max_length": C.MAX_LENGTH, "grad_accum": C.GRADIENT_ACCUMULATION_STEPS,
        "train_minutes": round(mins, 2), "bank_run_id": C.BANK_RUN_ID,
    }, indent=2))
    print(f"saved adapter -> {out_dir} in {mins:.1f} min")

    del trainer, model, ds
    torch.cuda.empty_cache()
    return out_dir


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    cc = a.country.upper()
    if cc not in C.COHORT:
        print(f"refusing: {cc} not in frozen cohort")
        return 2
    out = C.ADAPTER_DIR / cc
    if (out / "adapter_config.json").exists() and not a.force:
        print(f"{cc}: adapter already exists, skip ({out})")
        return 0
    train_country(cc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
