"""Tiny DPO LoRA fine-tune: SmolLM2-135M-Instruct on the USA synthetic bank.

The recipe copies the SCA2 paper B recipe (paper_b/config.py:45-54 and
paper_b/train_country.py) at a tiny scale. The DPO loss is written by hand;
trl is not used.

    loss = -logsigmoid(beta * ((pi_c - ref_c) - (pi_r - ref_r)))

Each term is a SUM of completion-token log-probs. The reference is the same
peft model under `model.disable_adapter()`, so no second copy is loaded.

Tokenization mirrors trl's DPOTrainer.tokenize_row, which train_country.py
used: the prompt and the completion are tokenized separately
(add_special_tokens=False), and the EOS id is appended to the completion.

Usage (from the worktree root):
    env -u PYTHONPATH uv run --project workbench python \
        workbench/src/sca2_workbench/train_dpo.py --epochs 1 --out workbench/models/usa_e1
    env -u PYTHONPATH uv run --project workbench python \
        workbench/src/sca2_workbench/train_dpo.py --eval-report workbench/runs/slice3a_dpo.json \
        --adapters workbench/models/usa_e1 workbench/models/usa_e3
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # lock: no network, HF cache only

import argparse
import json
import math
import random
import resource
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

MODEL_NAME = "HuggingFaceTB/SmolLM2-135M-Instruct"
BANK = Path(
    "/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/"
    "synthetic_generation/outputs/gps_sign_relabel_all/D_syn_USA.jsonl"
)
SEED = 20261016
HELDOUT_FRAC = 0.10

# paper_b/config.py:45-54 (frozen)
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj"]
DPO_BETA = 0.1
LEARNING_RATE = 1e-4
MAX_LENGTH = 768
PER_DEVICE_BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 16  # effective batch 16
# transformers.TrainingArguments defaults that DPOConfig inherited in the paper run
MAX_GRAD_NORM = 1.0
WEIGHT_DECAY = 0.0
WARMUP_STEPS = 0


# ------------------------------------------------------------------ prompt
def build_user_prompt(prompt_text: str) -> str:
    """Verbatim copy of paper_b/lib.py:119 build_user_prompt."""
    return (
        "You are answering a questionnaire as an individual person. "
        "Respond naturally and thoughtfully, as someone would in real life. "
        "Do not mention being an AI or assistant. "
        "Keep the answer short, under 3 sentences. "
        "Give a sincere, human-like answer.\n\n"
        "Situation:\n"
        f"{prompt_text.strip()}\n\n"
        "Answer:"
    )


# ------------------------------------------------------------------ pure pieces (tested)
def dpo_loss(pi_c, pi_r, ref_c, ref_r, beta: float) -> dict:
    """Sigmoid DPO loss on summed completion log-probs. Returns per-pair and mean values."""
    chosen_rewards = beta * (pi_c - ref_c)
    rejected_rewards = beta * (pi_r - ref_r)
    margins = chosen_rewards - rejected_rewards
    losses = -F.logsigmoid(margins)
    return {
        "losses": losses,
        "loss": losses.mean(),
        "chosen_rewards": chosen_rewards.detach(),
        "rejected_rewards": rejected_rewards.detach(),
        "margins": margins.detach(),
        "accuracy": (margins.detach() > 0).float().mean(),
    }


def pair_ids(prompt_ids: list[int], completion_ids: list[int], max_length: int) -> tuple[list[int], int, int]:
    """Concatenate prompt + completion; on overflow keep the END (cut the prompt from the left).

    Returns (ids, n_prompt_tokens_kept, n_tokens_cut).
    """
    overflow = len(prompt_ids) + len(completion_ids) - max_length
    if overflow > 0:
        if overflow >= len(prompt_ids):
            raise ValueError("completion alone exceeds max_length")
        prompt_ids = prompt_ids[overflow:]
    else:
        overflow = 0
    return list(prompt_ids) + list(completion_ids), len(prompt_ids), overflow


# ------------------------------------------------------------------ data
def load_bank(path: Path = BANK) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:  # read in place, never copied
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    for i, r in enumerate(rows):
        for k in ("prompt", "chosen", "rejected", "triplet_id"):
            if k not in r:
                raise ValueError(f"row {i} missing {k}")
    return rows


def split_indices(n: int, seed: int = SEED, heldout_frac: float = HELDOUT_FRAC) -> tuple[list[int], list[int]]:
    perm = np.random.default_rng(seed).permutation(n)
    n_train = int(round(n * (1 - heldout_frac)))
    return sorted(perm[:n_train].tolist()), sorted(perm[n_train:].tolist())


def encode_rows(tok, rows: list[dict]) -> list[dict]:
    """Token ids for each pair, trl-style (separate tokenization, EOS on the completion)."""
    out = []
    for r in rows:
        prompt_text = tok.apply_chat_template(
            [{"role": "user", "content": build_user_prompt(r["prompt"])}],
            tokenize=False,
            add_generation_prompt=True,
        )
        p_ids = tok(prompt_text, add_special_tokens=False)["input_ids"]
        item = {"triplet_id": r["triplet_id"], "n_cut": 0}
        for side in ("chosen", "rejected"):
            c_ids = tok(r[side], add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
            ids, n_prompt, n_cut = pair_ids(p_ids, c_ids, MAX_LENGTH)
            item[side] = (ids, n_prompt)
            item["n_cut"] += n_cut
        out.append(item)
    return out


# ------------------------------------------------------------------ model
def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def pick_device() -> torch.device:
    return torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")


def load_base(device):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, dtype=torch.float32)
    model.config.use_cache = False
    return tok, model.to(device)


def completion_logps(model, item: dict, pad_id: int, device) -> torch.Tensor:
    """Summed completion log-probs for [chosen, rejected] in one right-padded batch of 2."""
    seqs = [item["chosen"], item["rejected"]]
    width = max(len(ids) for ids, _ in seqs)
    input_ids = torch.full((2, width), pad_id, dtype=torch.long)
    attn = torch.zeros((2, width), dtype=torch.long)
    mask = torch.zeros((2, width), dtype=torch.float32)  # 1 on completion tokens
    for b, (ids, n_prompt) in enumerate(seqs):
        input_ids[b, : len(ids)] = torch.tensor(ids)
        attn[b, : len(ids)] = 1
        mask[b, n_prompt : len(ids)] = 1.0
    input_ids, attn, mask = input_ids.to(device), attn.to(device), mask.to(device)
    logits = model(input_ids=input_ids, attention_mask=attn).logits[:, :-1, :]
    targets = input_ids[:, 1:]
    tok_logp = torch.gather(logits.log_softmax(-1), 2, targets.unsqueeze(-1)).squeeze(-1)
    return (tok_logp * mask[:, 1:]).sum(-1)  # shape (2,) = [chosen, rejected]


def peak_rss_gb() -> float:
    # macOS ru_maxrss is in bytes
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**3


# ------------------------------------------------------------------ train
def train(epochs: int, out: Path) -> dict:
    from peft import LoraConfig, get_peft_model
    from transformers import get_cosine_schedule_with_warmup

    seed_everything()
    device = pick_device()
    tok, base = load_base(device)
    rows = load_bank()
    train_idx, held_idx = split_indices(len(rows))
    train_items = encode_rows(tok, [rows[i] for i in train_idx])
    held_ids = [rows[i]["triplet_id"] for i in held_idx]

    model = get_peft_model(
        base,
        LoraConfig(
            r=LORA_R,
            lora_alpha=LORA_ALPHA,
            lora_dropout=LORA_DROPOUT,
            target_modules=LORA_TARGETS,
            bias="none",
            task_type="CAUSAL_LM",
        ),
    )
    params = [p for p in model.parameters() if p.requires_grad]
    n_trainable = sum(p.numel() for p in params)
    opt = torch.optim.AdamW(params, lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    steps_per_epoch = math.ceil(len(train_items) / (PER_DEVICE_BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS))
    total_steps = steps_per_epoch * epochs
    sched = get_cosine_schedule_with_warmup(opt, WARMUP_STEPS, total_steps)

    print(
        f"device={device} n_train={len(train_items)} n_heldout={len(held_ids)} "
        f"trainable={n_trainable} epochs={epochs} steps={total_steps} "
        f"truncated_pairs={sum(1 for it in train_items if it['n_cut'])}",
        flush=True,
    )

    log_steps = []
    order_rng = np.random.default_rng(SEED)
    t0 = time.time()
    step = 0
    model.train()
    for epoch in range(epochs):
        order = order_rng.permutation(len(train_items)).tolist()
        for start in range(0, len(order), GRADIENT_ACCUMULATION_STEPS):
            chunk = order[start : start + GRADIENT_ACCUMULATION_STEPS]
            losses, margins, accs = [], [], []
            for j in chunk:
                item = train_items[j]
                with torch.no_grad(), model.disable_adapter():
                    ref = completion_logps(model, item, tok.pad_token_id, device)
                pol = completion_logps(model, item, tok.pad_token_id, device)
                res = dpo_loss(pol[0:1], pol[1:2], ref[0:1], ref[1:2], beta=DPO_BETA)
                (res["loss"] / len(chunk)).backward()
                losses.append(res["loss"].item())
                margins.append(res["margins"].item())
                accs.append(res["accuracy"].item())
            grad_norm = torch.nn.utils.clip_grad_norm_(params, MAX_GRAD_NORM).item()
            lr = sched.get_last_lr()[0]
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            if device.type == "mps":
                # variable-length batches make the MPS caching allocator grow to ~12 GB per
                # process (observed); releasing the cache each step keeps it bounded
                torch.mps.empty_cache()
            step += 1
            rec = {
                "step": step,
                "epoch": epoch + 1,
                "loss": float(np.mean(losses)),
                "reward_margin": float(np.mean(margins)),
                "reward_accuracy": float(np.mean(accs)),
                "grad_norm": grad_norm,
                "lr": lr,
                "wall_s": round(time.time() - t0, 2),
            }
            log_steps.append(rec)
            print(
                f"step {step:3d}/{total_steps} ep {epoch + 1} loss {rec['loss']:.4f} "
                f"margin {rec['reward_margin']:+.4f} acc {rec['reward_accuracy']:.3f} "
                f"gnorm {grad_norm:.3f} lr {lr:.2e} t {rec['wall_s']:.0f}s",
                flush=True,
            )

    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out))
    log = {
        "model_name": MODEL_NAME,
        "bank": str(BANK),
        "seed": SEED,
        "device": str(device),
        "dtype": "float32",
        "epochs": epochs,
        "n_train": len(train_items),
        "n_heldout": len(held_ids),
        "truncated_pairs": sum(1 for it in train_items if it["n_cut"]),
        "optimizer_steps": total_steps,
        "trainable_params": n_trainable,
        "recipe": {
            "lora_r": LORA_R,
            "lora_alpha": LORA_ALPHA,
            "lora_dropout": LORA_DROPOUT,
            "lora_targets": LORA_TARGETS,
            "beta": DPO_BETA,
            "lr": LEARNING_RATE,
            "schedule": "cosine",
            "warmup_steps": WARMUP_STEPS,
            "max_length": MAX_LENGTH,
            "truncation": "keep_end (prompt cut from the left)",
            "per_device_batch": PER_DEVICE_BATCH_SIZE,
            "grad_accum": GRADIENT_ACCUMULATION_STEPS,
            "max_grad_norm": MAX_GRAD_NORM,
            "weight_decay": WEIGHT_DECAY,
            "completion_eos": True,
            "reference": "same peft model under disable_adapter()",
        },
        "wall_time_s": round(time.time() - t0, 2),
        "peak_rss_gb": round(peak_rss_gb(), 3),
        "mps_driver_allocated_gb_at_end": (
            round(torch.mps.driver_allocated_memory() / 1024**3, 3) if device.type == "mps" else None
        ),
        "heldout_triplet_ids": held_ids,
        "steps": log_steps,
    }
    (out / "train_log.json").write_text(json.dumps(log, indent=2))
    print(f"saved -> {out}  wall {log['wall_time_s']}s  peak RSS {log['peak_rss_gb']} GB", flush=True)
    return log


# ------------------------------------------------------------------ evaluate
@torch.no_grad()
def heldout_logps(model, items, pad_id, device) -> np.ndarray:
    return np.array([completion_logps(model, it, pad_id, device).cpu().numpy() for it in items])


def summarize(lp: np.ndarray) -> dict:
    diff = lp[:, 0] - lp[:, 1]
    return {
        "mean_logp_chosen_minus_rejected": float(diff.mean()),
        "frac_chosen_minus_rejected_gt_0": float((diff > 0).mean()),
        "mean_logp_chosen": float(lp[:, 0].mean()),
        "mean_logp_rejected": float(lp[:, 1].mean()),
    }


def check_lora_b_loaded(model, adir: Path) -> dict:
    """Raise unless the loaded LoRA B weights match the file.

    With peft 0.21.2 + transformers 5.20.1, PeftModel.from_pretrained onto a float64
    base silently leaves every LoRA B at zero (PM finding), so the "adapter" model
    scores exactly like the base. Compare the summed B norms to the safetensors file.
    """
    from safetensors.torch import load_file

    in_file = sum(t.float().norm().item() for k, t in load_file(str(adir / "adapter_model.safetensors")).items() if "lora_B" in k)
    loaded = sum(p.detach().float().norm().item() for n, p in model.named_parameters() if "lora_B" in n)
    if not (loaded > 0 and abs(loaded - in_file) <= 1e-4 * in_file):
        raise RuntimeError(f"{adir}: LoRA B not loaded (loaded norm sum {loaded:.6f}, file {in_file:.6f})")
    return {"loaded": loaded, "file": in_file}


def evaluate(adapters: list[Path], report: Path) -> dict:
    from peft import PeftModel

    seed_everything()
    device = pick_device()
    tok, base = load_base(device)
    base.eval()
    rows = load_bank()
    _, held_idx = split_indices(len(rows))
    held_ids = [rows[i]["triplet_id"] for i in held_idx]
    items = encode_rows(tok, [rows[i] for i in held_idx])

    ref_lp = heldout_logps(base, items, tok.pad_token_id, device)
    result = {
        "model_name": MODEL_NAME,
        "bank": str(BANK),
        "seed": SEED,
        "device": str(device),
        "n_heldout": len(items),
        "heldout_triplet_ids": held_ids,
        "metric_note": "logp = summed completion-token log-probs (EOS included), prompt per paper_b/lib.py build_user_prompt + chat template",
        "models": {"base": summarize(ref_lp)},
    }
    for adir in adapters:
        logged = json.loads((adir / "train_log.json").read_text())["heldout_triplet_ids"]
        if logged != held_ids:
            raise ValueError(f"{adir}: held-out ids differ from this split")
        model = PeftModel.from_pretrained(base, str(adir)).to(device)
        model.eval()
        entry_check = check_lora_b_loaded(model, adir)
        lp = heldout_logps(model, items, tok.pad_token_id, device)
        margins = DPO_BETA * ((lp[:, 0] - ref_lp[:, 0]) - (lp[:, 1] - ref_lp[:, 1]))
        entry = summarize(lp)
        entry["dpo_implicit_reward_accuracy"] = float((margins > 0).mean())
        entry["dpo_implicit_reward_margin_mean"] = float(margins.mean())
        entry["lora_b_norm_sum_loaded"] = entry_check["loaded"]
        entry["lora_b_norm_sum_file"] = entry_check["file"]
        result["models"][adir.name] = entry
        base = model.unload()  # strip the LoRA layers so the next adapter starts from the clean base
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2))
    print(json.dumps(result["models"], indent=2))
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--epochs", type=int, help="train: number of epochs")
    ap.add_argument("--out", type=Path, help="train: adapter output dir")
    ap.add_argument("--eval-report", type=Path, help="evaluate base + --adapters on the held-out split")
    ap.add_argument("--adapters", type=Path, nargs="*", default=[])
    a = ap.parse_args(argv)
    if a.eval_report:
        evaluate(a.adapters, a.eval_report)
        return 0
    if a.epochs is None or a.out is None:
        ap.error("training needs --epochs and --out (or use --eval-report)")
    train(a.epochs, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
