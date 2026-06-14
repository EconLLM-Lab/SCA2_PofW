"""GPU-backed DPO training and reward-recovery evaluation helpers.

These functions are intended for Colab or another CUDA runtime. Heavy ML
dependencies are imported inside functions so local data checks can run without
installing the training stack.
"""

from __future__ import annotations

import gc
import json
import math
import os
from pathlib import Path
from typing import Any

from .config import COUNTRIES, ExperimentConfig
from .data import load_jsonl, write_jsonl


def configure_torch_environment() -> None:
    os.environ["ACCELERATE_MIXED_PRECISION"] = "fp16"
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    os.environ["TRANSFORMERS_NO_BF16"] = "1"


def require_cuda() -> None:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this DPO replication workflow.")


def build_user_prompt(prompt_text: str) -> str:
    return (
        "You are responding as an individual person. "
        "Respond naturally and thoughtfully. "
        "Do not mention being an AI or assistant. "
        "Keep the answer short, sincere, and in your own voice.\n\n"
        "Situation:\n"
        f"{prompt_text.strip()}\n\n"
        "Answer:"
    )


def format_prompt_text(tokenizer: Any, prompt_text: str) -> str:
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": build_user_prompt(prompt_text)}],
        tokenize=False,
        add_generation_prompt=True,
    )


def format_dataset_example(tokenizer: Any, example: dict[str, Any]) -> dict[str, Any]:
    copied = dict(example)
    copied["prompt"] = format_prompt_text(tokenizer, copied["prompt"])
    return copied


def get_model_device(model: Any):
    return next(model.parameters()).device


def load_tokenizer(model_name: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def make_bnb_config():
    import torch
    from transformers import BitsAndBytesConfig

    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )


def load_base_model_4bit(model_name: str, device_map: str | dict[str, int] = "auto"):
    import torch
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=make_bnb_config(),
        device_map=device_map,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    model.eval()
    return model


def runtime_smoke_check(config: ExperimentConfig) -> None:
    import torch

    configure_torch_environment()
    require_cuda()
    print("CUDA:", torch.version.cuda)
    print("GPU:", torch.cuda.get_device_name(0))
    tokenizer = load_tokenizer(config.model_name)
    model = load_base_model_4bit(config.model_name, device_map={"": 0})
    sample = load_jsonl(config.source_file(COUNTRIES[0]))[0]
    logp = sequence_logprob(
        model=model,
        tokenizer=tokenizer,
        prompt_text=sample["prompt"],
        completion_text=sample["chosen"],
        max_prompt_tokens=config.max_prompt_tokens,
        max_completion_tokens=config.max_completion_tokens,
    )
    print("Sample chosen logp:", logp)
    cleanup_models(model)


def sequence_logprob(
    model: Any,
    tokenizer: Any,
    prompt_text: str,
    completion_text: str,
    max_prompt_tokens: int = 512,
    max_completion_tokens: int = 256,
) -> float:
    import torch

    model.eval()
    device = get_model_device(model)
    formatted_prompt = format_prompt_text(tokenizer, prompt_text)

    prompt_ids = tokenizer(formatted_prompt, add_special_tokens=False).input_ids
    completion_ids = tokenizer(completion_text, add_special_tokens=False).input_ids

    if len(prompt_ids) > max_prompt_tokens:
        prompt_ids = prompt_ids[-max_prompt_tokens:]
    if len(completion_ids) > max_completion_tokens:
        completion_ids = completion_ids[:max_completion_tokens]

    input_ids = prompt_ids + completion_ids
    if len(input_ids) < 2:
        return float("-inf")

    labels = [-100] * len(prompt_ids) + completion_ids
    input_ids_t = torch.tensor([input_ids], device=device)
    labels_t = torch.tensor([labels], device=device)

    outputs = model(input_ids=input_ids_t)
    logits = outputs.logits
    shifted_logits = logits[:, :-1, :]
    shifted_labels = labels_t[:, 1:]
    log_probs = torch.log_softmax(shifted_logits, dim=-1)

    mask = shifted_labels.ne(-100)
    safe_labels = shifted_labels.clone()
    safe_labels[~mask] = 0
    token_log_probs = log_probs.gather(-1, safe_labels.unsqueeze(-1)).squeeze(-1)
    completion_logprob = (token_log_probs * mask).sum()
    return float(completion_logprob.detach().cpu().to(torch.float32))


def precompute_reference_logps(
    config: ExperimentConfig,
    country: str,
    max_examples: int | None = None,
) -> Path:
    config.require_country(country)
    configure_torch_environment()
    require_cuda()

    tokenizer = load_tokenizer(config.model_name)
    ref_model = load_base_model_4bit(config.model_name, device_map={"": 0})
    rows = load_jsonl(config.train_file(country))
    if max_examples is not None:
        rows = rows[:max_examples]

    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows, 1):
        copied = dict(row)
        copied["ref_chosen_logps"] = sequence_logprob(
            model=ref_model,
            tokenizer=tokenizer,
            prompt_text=copied["prompt"],
            completion_text=copied["chosen"],
            max_prompt_tokens=config.max_prompt_tokens,
            max_completion_tokens=config.max_completion_tokens,
        )
        copied["ref_rejected_logps"] = sequence_logprob(
            model=ref_model,
            tokenizer=tokenizer,
            prompt_text=copied["prompt"],
            completion_text=copied["rejected"],
            max_prompt_tokens=config.max_prompt_tokens,
            max_completion_tokens=config.max_completion_tokens,
        )
        out_rows.append(copied)
        if i % 25 == 0:
            print(f"{country}: precomputed {i}/{len(rows)}")

    out_file = config.train_with_ref_file(country)
    write_jsonl(out_rows, out_file)
    cleanup_models(ref_model)
    return out_file


def train_adapter(config: ExperimentConfig, country: str):
    config.require_country(country)
    configure_torch_environment()
    require_cuda()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model
    from trl import DPOConfig, DPOTrainer

    data_file = config.train_with_ref_file(country)
    if not data_file.exists():
        raise FileNotFoundError(f"Missing precomputed reference file: {data_file}")

    tokenizer = load_tokenizer(config.model_name)
    model = load_base_model_4bit(config.model_name, device_map={"": 0})
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()

    dataset = load_dataset("json", data_files={"train": str(data_file)})["train"]
    train_dataset = dataset.map(lambda ex: format_dataset_example(tokenizer, ex))

    peft_cfg = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, peft_cfg)

    for _, parameter in model.named_parameters():
        if parameter.requires_grad:
            parameter.data = parameter.data.to(torch.float16)
    for name, buffer in model.named_buffers():
        if buffer.is_floating_point():
            try:
                model._buffers[name] = buffer.to(torch.float16)
            except Exception:
                pass

    dpo_args = DPOConfig(
        output_dir=str(config.adapter_dir(country)),
        beta=config.beta,
        max_length=config.max_length,
        truncation_mode="keep_end",
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        num_train_epochs=config.num_train_epochs,
        learning_rate=config.learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=config.warmup_ratio,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        report_to="none",
        fp16=True,
        bf16=False,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,
        args=dpo_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )

    for _, parameter in trainer.model.named_parameters():
        if parameter.requires_grad and parameter.dtype != torch.float32:
            parameter.data = parameter.data.to(torch.float32)

    trainer.train()
    adapter_dir = config.adapter_dir(country)
    trainer.model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    print(f"Saved adapter-only model to {adapter_dir}")
    cleanup_models(trainer.model)
    return adapter_dir


def load_adapter_model(config: ExperimentConfig, adapter_country: str):
    from peft import PeftModel

    config.require_country(adapter_country)
    tokenizer = load_tokenizer(config.model_name)
    base_model = load_base_model_4bit(config.model_name, device_map="auto")
    adapter_model = PeftModel.from_pretrained(base_model, config.adapter_dir(adapter_country))
    adapter_model.eval()
    return adapter_model, tokenizer


def dpo_implied_reward_delta(
    adapter_model: Any,
    tokenizer: Any,
    prompt: str,
    chosen: str,
    rejected: str,
    beta: float,
    max_prompt_tokens: int = 512,
    max_completion_tokens: int = 256,
) -> dict[str, float | bool]:
    with adapter_model.disable_adapter():
        ref_chosen_logp = sequence_logprob(
            adapter_model, tokenizer, prompt, chosen, max_prompt_tokens, max_completion_tokens
        )
        ref_rejected_logp = sequence_logprob(
            adapter_model, tokenizer, prompt, rejected, max_prompt_tokens, max_completion_tokens
        )

    adapter_chosen_logp = sequence_logprob(
        adapter_model, tokenizer, prompt, chosen, max_prompt_tokens, max_completion_tokens
    )
    adapter_rejected_logp = sequence_logprob(
        adapter_model, tokenizer, prompt, rejected, max_prompt_tokens, max_completion_tokens
    )

    ref_margin = ref_chosen_logp - ref_rejected_logp
    adapter_margin = adapter_chosen_logp - adapter_rejected_logp
    reward_delta = beta * (adapter_margin - ref_margin)
    dpo_pref_prob = 1.0 / (1.0 + math.exp(-reward_delta))

    return {
        "ref_chosen_logp": ref_chosen_logp,
        "ref_rejected_logp": ref_rejected_logp,
        "adapter_chosen_logp": adapter_chosen_logp,
        "adapter_rejected_logp": adapter_rejected_logp,
        "ref_margin": ref_margin,
        "adapter_margin": adapter_margin,
        "dpo_reward_delta": reward_delta,
        "dpo_pref_prob": dpo_pref_prob,
        "dpo_prefers_chosen": reward_delta > 0,
    }


def generate_model_answer(
    model: Any,
    tokenizer: Any,
    prompt_text: str,
    max_new_tokens: int = 120,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    import torch

    model.eval()
    device = get_model_device(model)
    formatted_prompt = format_prompt_text(tokenizer, prompt_text)
    inputs = tokenizer(formatted_prompt, return_tensors="pt", add_special_tokens=False).to(device)

    output_ids = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temperature,
        top_p=top_p,
        pad_token_id=tokenizer.eos_token_id,
    )
    generated_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


def evaluate_adapter_reward_recovery(
    config: ExperimentConfig,
    adapter_model: Any,
    tokenizer: Any,
    adapter_country: str,
    eval_country: str,
    max_examples: int | None = None,
    generate_answers: bool = True,
    max_new_tokens: int = 120,
    temperature: float = 0.7,
    top_p: float = 0.9,
):
    import pandas as pd
    from tqdm.auto import tqdm

    config.require_country(adapter_country)
    config.require_country(eval_country)
    rows = load_jsonl(config.eval_file(eval_country))
    if max_examples is not None:
        rows = rows[:max_examples]

    results: list[dict[str, Any]] = []
    for row in tqdm(rows, desc=f"Reward recovery: {adapter_country} adapter on {eval_country}"):
        out = dpo_implied_reward_delta(
            adapter_model=adapter_model,
            tokenizer=tokenizer,
            prompt=row["prompt"],
            chosen=row["chosen"],
            rejected=row["rejected"],
            beta=config.beta,
            max_prompt_tokens=config.max_prompt_tokens,
            max_completion_tokens=config.max_completion_tokens,
        )
        generated_answer = None
        if generate_answers:
            generated_answer = generate_model_answer(
                model=adapter_model,
                tokenizer=tokenizer,
                prompt_text=row["prompt"],
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
            )

        results.append(
            {
                "model": f"{adapter_country}_adapter",
                "adapter_country": adapter_country,
                "eval_country": eval_country,
                "country": row.get("country"),
                "item_id": row.get("item_id"),
                "gps_dimension": row.get("gps_dimension"),
                "prompt": row["prompt"],
                "chosen": row["chosen"],
                "rejected": row["rejected"],
                "generated_answer": generated_answer,
                **out,
            }
        )

    return pd.DataFrame(results)


def evaluate_adapter_on_all_countries(
    config: ExperimentConfig,
    adapter_country: str,
    max_examples: int | None = None,
    generate_answers: bool = True,
):
    import pandas as pd

    adapter_model, tokenizer = load_adapter_model(config, adapter_country)
    frames = []
    for eval_country in COUNTRIES:
        frames.append(
            evaluate_adapter_reward_recovery(
                config=config,
                adapter_model=adapter_model,
                tokenizer=tokenizer,
                adapter_country=adapter_country,
                eval_country=eval_country,
                max_examples=max_examples,
                generate_answers=generate_answers,
            )
        )
    result = pd.concat(frames, ignore_index=True)
    out_file = config.adapter_result_file(adapter_country)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_file, index=False)
    cleanup_models(adapter_model)
    return result


def run_full_training(config: ExperimentConfig) -> None:
    for country in COUNTRIES:
        precompute_reference_logps(config, country)
        train_adapter(config, country)


def run_full_evaluation(
    config: ExperimentConfig,
    max_examples: int | None = None,
    generate_answers: bool = True,
) -> Path:
    import pandas as pd

    frames = []
    for adapter_country in COUNTRIES:
        frames.append(
            evaluate_adapter_on_all_countries(
                config,
                adapter_country=adapter_country,
                max_examples=max_examples,
                generate_answers=generate_answers,
            )
        )
    combined = pd.concat(frames, ignore_index=True)
    out_file = config.results_dir / "reward_recovery_adapters_combined.csv"
    combined.to_csv(out_file, index=False)
    return out_file


def write_training_metadata(config: ExperimentConfig, path: Path | None = None) -> Path:
    if path is None:
        path = config.reports_dir / "training_metadata.json"
    payload = {
        "countries": list(COUNTRIES),
        "model_name": config.model_name,
        "train_frac": config.train_frac,
        "seed": config.seed,
        "beta": config.beta,
        "max_prompt_tokens": config.max_prompt_tokens,
        "max_completion_tokens": config.max_completion_tokens,
        "max_length": config.max_length,
        "num_train_epochs": config.num_train_epochs,
        "per_device_train_batch_size": config.per_device_train_batch_size,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "learning_rate": config.learning_rate,
        "warmup_ratio": config.warmup_ratio,
        "source_files": {country: str(config.source_file(country)) for country in COUNTRIES},
        "adapter_dirs": {country: str(config.adapter_dir(country)) for country in COUNTRIES},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def cleanup_models(*models: Any) -> None:
    import torch

    for model in models:
        del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
