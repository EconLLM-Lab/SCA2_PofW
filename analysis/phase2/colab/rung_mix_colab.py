# %% =====================================================================
# rung_mix_colab.py — Rung-mixture pilot: SFT x6 + Gates 2/3 + WVS scoring
# ========================================================================
# Usage (Colab T4): upload this file next to the data, then paste each
# `# %%` block as one cell, top to bottom. Runtime: ~2h total, ~2 units.
#
# Inputs expected on Drive:
#   DRIVE/rung_mix/sft_rung_{k}_train.jsonl     (from 20_build_rung_datasets.py)
#   DRIVE/rung_mix/sft_rung_{k}_holdout.jsonl   k in {-3,-2,-1,1,2,3}
#   DRIVE/rung_mix/wvs_scoring_bundle.parquet
#
# Predeclared spec: analysis/phase2/RUNG_MIXTURE_SPEC.md (FROZEN 2026-08-22)
# Outputs written to DRIVE/rung_mix/out/: adapter dirs, gate_2_3_report.json,
# rung_pmfs.csv (P_k(q,o) for all 35 WVS questions).
# ========================================================================

# %% [cell 1] setup ------------------------------------------------------
import os
os.environ["HF_TOKEN"] = ""  # paste inside exec only, never commit
# !pip -q install -U "transformers>=4.41.0" "datasets>=2.18.0" "accelerate>=0.30.0" \
#                  "peft>=0.11.1" "bitsandbytes>=0.46.1" "safetensors>=0.4.3" pandas pyarrow

from google.colab import drive
drive.mount("/content/drive")
BASE_DIR = "/content/drive/MyDrive/rung_mix"
OUT_DIR = f"{BASE_DIR}/out"
os.makedirs(OUT_DIR, exist_ok=True)

# %% [cell 2] base model (NF4, house config) ----------------------------
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.float16,
                         bnb_4bit_use_double_quant=True)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

def load_base():
    m = AutoModelForCausalLM.from_pretrained(MODEL_NAME, quantization_config=bnb,
                                             device_map="auto")
    m.eval()
    return m

# NOTE: reload the base fresh for EACH rung (peft wraps in place).
base = load_base()

# %% [cell 3] SFT data prep ---------------------------------------------
import json, pathlib
from datasets import Dataset

RUNGS = [-3, -2, -1, 1, 2, 3]
MAX_LEN = 1024

def fmt(row):
    """Same questionnaire wrapper family as canonical eval (user-turn only)."""
    user = ("Answer this questionnaire as an individual person. Respond naturally "
            "and sincerely, as someone would in real life. Do not mention being an "
            f"AI or assistant.\n\nSituation:\n{row['prompt'].strip()}\n\nAnswer:")
    text = tokenizer.apply_chat_template([{"role": "user", "content": user}],
                                         tokenize=False, add_generation_prompt=True)
    return text + row["generated_response"].strip()

def make_ds(k, split):
    rows = [json.loads(l) for l in open(f"{BASE_DIR}/sft_rung_{k:+d}_{split}.jsonl")]
    return Dataset.from_list([{**r, "_text": fmt(r)} for r in rows])

def tok(batch):
    out = tokenizer(batch["_text"], truncation=True, max_length=MAX_LEN)
    out["labels"] = [ids.copy() for ids in out["input_ids"]]
    return out

# sanity: identical wrapper text as scoring bundle?
import pandas as pd
bundle = pd.read_parquet(f"{BASE_DIR}/wvs_scoring_bundle.parquet")
print("bundle prompts:", bundle.question_id.nunique(), "| options:", len(bundle))

# %% [cell 4] train six rung-adapters -----------------------------------
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import TrainingArguments, Trainer

LORA = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                  target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                  task_type="CAUSAL_LM")

for k in RUNGS:
    print(f"\n=== SFT rung {k:+d} " + "=" * 40)
    model = get_peft_model(base, LORA)
    model = prepare_model_for_kbit_training(model)
    ds = make_ds(k, "train").map(tok, batched=True, remove_columns=[
        c for c in make_ds(k, "train").column_names])
    args = TrainingArguments(
        output_dir=f"{OUT_DIR}/tmp_rung_{k:+d}", per_device_train_batch_size=4,
        gradient_accumulation_steps=2, num_train_epochs=3, learning_rate=1e-4,
        lr_scheduler_type="cosine", warmup_ratio=0.03, logging_steps=20,
        bf16=False, fp16=True, optim="paged_adamw_8bit", report_to=[],
        save_strategy="no", seed=20260822)
    trainer = Trainer(model=model, args=args, train_dataset=ds,
                      data_collator=__import__("transformers").DataCollatorForLanguageModeling(
                          tokenizer, mlm=False))
    trainer.train()
    model.save_pretrained(f"{OUT_DIR}/adapter_rung_{k:+d}")
    # unload adapter weights before next rung
    del model, trainer
    import gc; gc.collect(); torch.cuda.empty_cache()
    base = load_base()  # fresh unwrap

# %% [cell 5] helpers: batched option LL --------------------------------
@torch.no_grad()
def option_logprobs(model, prompt_text: str, option_texts: list[str]):
    """Summed completion-token logprob per option (canonical convention)."""
    fmt_p = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt_text}], tokenize=False,
        add_generation_prompt=True)
    p_ids = tokenizer(fmt_p, add_special_tokens=False, return_tensors="pt").input_ids.to(model.device)
    out = []
    for opt in option_texts:
        o_ids = tokenizer(opt, add_special_tokens=False, return_tensors="pt").input_ids.to(model.device)
        ids = torch.cat([p_ids, o_ids], dim=1)
        logits = model(ids).logits.float()
        lp = torch.log_softmax(logits[:, :-1], dim=-1)
        tgt = ids[:, 1:]
        n_p = p_ids.shape[1]
        sel = lp[0, n_p - 1:, :].gather(1, tgt[0, n_p - 1:].unsqueeze(1)).sum()
        out.append(float(sel))
    return out

# %% [cell 6] GATES 2+3 — purity & separation on holdouts ---------------
import itertools, numpy as np
from scipy.stats import spearmanr, mannwhitneyu

gate = {"choice_agreement": {}, "margin_rho": {}, "adjacent_vs_cross_tvd": None}

# 2a. direction agreement across same-sign rungs using ORIGINAL A/B as yardstick
def load_rows(k):
    return [json.loads(l) for l in open(f"{BASE_DIR}/sft_rung_{k:+d}_holdout.jsonl")]

hold = {k: load_rows(k) for k in RUNGS}

def ll_originals(model, row):
    user = ("Answer this questionnaire as an individual person.\n\nSituation:\n"
            f"{row['prompt'].strip()}\n\nAnswer:")
    return option_logprobs(model, user,
                           [row["response_A_original"], row["response_B_original"]])

# evaluate direction choices per rung once, cache
choices, margins = {}, {}
for k in RUNGS:
    ad = f"{OUT_DIR}/adapter_rung_{k:+d}"
    m = AutoModelForCausalLM.from_pretrained(MODEL_NAME, quantization_config=bnb,
                                             device_map="auto")
    from peft import PeftModel
    m = PeftModel.from_pretrained(m, ad); m.eval()
    ch, mg = {}, {}
    for row in hold[k]:  # FULL holdout — no caps (user directive 2026-08-22)
        a, b = ll_originals(m, row)
        ch[row["original_index"]] = int(a > b)
        mg[row["original_index"]] = abs(a - b)
    choices[k], margins[k] = ch, mg
    del m; torch.cuda.empty_cache()

for hi, lo in [(1, 2), (1, 3), (2, 3)]:
    common = set(choices[hi]) & set(choices[lo])
    gate["choice_agreement"][f"+{hi}v+{lo}"] = float(np.mean(
        [choices[hi][i] == choices[lo][i] for i in common]))
for hi, lo in [(1, 2), (1, 3), (2, 3)]:
    common = sorted(set(margins[hi]) & set(margins[lo]))
    gate["margin_rho"][f"+{hi}>{hi-lo}"] = float(spearmanr(
        [margins[lo][i] for i in common], [margins[hi][i] for i in common]).statistic)

# 3. adjacent-vs-cross separation happens after PMFs are computed (cell 8)

# %% [cell 7] WVS scoring per rung -> P_k(q,o) --------------------------
pmf_frames = []
qs = bundle.drop_duplicates("question_id")
for k in RUNGS:
    from peft import PeftModel
    m = AutoModelForCausalLM.from_pretrained(MODEL_NAME, quantization_config=bnb,
                                             device_map="auto")
    m = PeftModel.from_pretrained(m, f"{OUT_DIR}/adapter_rung_{k:+d}"); m.eval()
    rows = []
    for _, q in qs.iterrows():
        opts = bundle[bundle.question_id == q.question_id]
        texts = [t if isinstance(t, str) else str(t)
                 for t in opts.option_label.tolist()]
        lps = option_logprobs(m, q.prompt_text, texts)
        e = np.exp(np.array(lps) - np.max(lps)); p = e / e.sum()
        rows.extend({"rung": k, "question_id": q.question_id,
                     "option_code": c, "prob": float(pi)}
                    for c, pi in zip(opts.option_code, p))
    pmf_frames.append(pd.DataFrame(rows))
    print(f"rung {k:+d}: scored {len(rows)} options")
    del m; torch.cuda.empty_cache()

pmfs = pd.concat(pmf_frames, ignore_index=True)
pmfs.to_csv(f"{OUT_DIR}/rung_pmfs.csv", index=False)

# %% [cell 8] GATE 3 — ladder geometry + finalize report ----------------
wide = pmfs.pivot_table(index=["question_id", "option_code"], columns="rung",
                        values="prob")
def tvd_cols(a, b):
    return 0.5 * float((wide[a] - wide[b]).abs().sum())
adj = [tvd_cols(i, j) for i, j in [(1, 2), (2, 3), (-1, -2), (-2, -3)]]
cross = [tvd_cols(i, j) for i in [1, 2, 3] for j in [-1, -2, -3]]
u = mannwhitneyu(adj, cross, alternative="greater")
gate["adjacent_vs_cross_tvd"] = {
    "median_adjacent": float(np.median(adj)), "median_cross": float(np.median(cross)),
    "p_one_sided": float(u.pvalue)}
gate["gate_2_pass"] = bool(all(v >= 0.85 for v in gate["choice_agreement"].values())
                           and all(r >= 0.5 for r in gate["margin_rho"].values()))
gate["gate_3_pass"] = bool(u.pvalue < 0.05)
json.dump(gate, open(f"{OUT_DIR}/gate_2_3_report.json", "w"), indent=2)
print(json.dumps(gate, indent=2)[:1200])

# %% [cell 9] handoff ----------------------------------------------------
# Download DRIVE/rung_mix/out/{adapter_rung_*/, rung_pmfs.csv, gate_2_3_report.json}
# Mixture arithmetic + Tests A/B/C run LOCALLY (analysis/phase2/21_rung_mixture_eval.py).
