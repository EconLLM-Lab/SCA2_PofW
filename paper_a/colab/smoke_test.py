# %% =====================================================================
# smoke_test.py — 15-minute end-to-end probe of the rung-mixture pipeline
# ========================================================================
# Verifies, in order: inputs present + hashes; wrapper extraction (B2);
# B1-correct PEFT assembly with trainable-param assert; 10 real SFT steps;
# adapter save/reload; code-surface scoring on one question (B3); HF push
# round-trip. Writes SMOKE_OK or raises.
# ========================================================================
import hashlib
import json
import os
import sys

BASE = "/content/rung_mix"
OUT = "/content/out"
os.makedirs(OUT, exist_ok=True)
REPO_ID = "Bonorinoa/sca2-rung-mix"

if not os.environ.get("HF_TOKEN"):
    print("FATAL: HF_TOKEN not set"); sys.exit(1)

import torch
from huggingface_hub import HfApi
from transformers import AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

api = HfApi(token=os.environ["HF_TOKEN"])

print("== 1. inputs + hashes")
expect = {f"sft_rung_{k:+d}_{s}.jsonl" for k in (-3, -2, -1, 1, 2, 3)
          for s in ("train", "holdout")} | {"wvs_scoring_bundle.parquet"}
have = set(os.listdir(BASE))
missing = expect - have
assert not missing, f"missing inputs: {missing}"
h = hashlib.sha256(open(f"{BASE}/wvs_scoring_bundle.parquet", "rb").read()).hexdigest()[:16]
n_ho = len(open(f"{BASE}/sft_rung_+1_holdout.jsonl").readlines())
print(f"   all 13 inputs present | bundle sha16={h} | holdout rows={n_ho}")
assert n_ho == 120, f"holdout should be 120, got {n_ho}"

print("== 2. wrapper extraction (B2)")
import pandas as pd
bundle = pd.read_parquet(f"{BASE}/wvs_scoring_bundle.parquet")
qm = bundle.drop_duplicates("question_id")
pres, tails = set(), set()
for _, r in qm.iterrows():
    qt, fp = r.question_text, r.formatted_prompt
    assert fp.count(qt) == 1
    pre, suf = fp.split(qt, 1)
    ANS = "\n\nAnswer:"
    assert suf.count(ANS) == 1 and len(suf) > len(ANS)
    mid, tail = suf.split(ANS, 1)
    pres.add(pre); tails.add(tail)
assert len(pres) == 1 and len(tails) == 1
PRE, TAIL = pres.pop(), tails.pop()
print(f"   PRE shared across {len(qm)} questions ({len(PRE)} chars), "
      f"TAIL constant ({len(TAIL)} chars)")

MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
tok = AutoTokenizer.from_pretrained(MODEL_NAME)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

print("== 3. B1-correct PEFT assembly")
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.float16,
                         bnb_4bit_use_double_quant=True)
gpu_mb = torch.cuda.get_device_properties(0).total_memory // (1024 ** 2)
MAXMEM = {0: f"{int(gpu_mb * 0.92)}MB"}
base = __import__("transformers").AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, quantization_config=bnb, device_map="auto", max_memory=MAXMEM)
base = prepare_model_for_kbit_training(base)
model = get_peft_model(base, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                                        bias="none",
                                        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                                        task_type="CAUSAL_LM"))
n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"   trainable params: {n_train/1e6:.1f}M")
assert n_train > 1_000_000, "B1 guard: LoRA frozen!"

print("== 4. 10 real SFT steps (completion-only loss)")
from transformers import TrainingArguments, Trainer, DataCollatorForSeq2Seq
rows = [json.loads(l) for l in open(f"{BASE}/sft_rung_+1_train.jsonl")][:40]
ex_ids, ex_labels = [], []
for r in rows:
    p = tok(PRE + r["prompt"].strip() + "\n\nAnswer:" + TAIL, add_special_tokens=False,
            truncation=True, max_length=768).input_ids
    t = tok(r["generated_response"].strip(), add_special_tokens=False,
            max_length=64).input_ids + [tok.eos_token_id]
    ex_ids.append(p + t); ex_labels.append([-100] * len(p) + t)
import datasets as hfds
ds = hfds.Dataset.from_dict({"input_ids": ex_ids, "labels": ex_labels})
collator = DataCollatorForSeq2Seq(tokenizer=tok, model=None, padding=True,
                                  label_pad_token_id=-100)
args = TrainingArguments(output_dir=f"{OUT}/smoke_tmp", per_device_train_batch_size=2,
                         gradient_accumulation_steps=4, max_steps=10,
                         learning_rate=1e-4, logging_steps=5, fp16=True,
                         optim="paged_adamw_8bit", report_to=[], save_strategy="no",
                         seed=20260822, disable_tqdm=True)
Trainer(model=model, args=args, train_dataset=ds, data_collator=collator).train()
print("   10 steps completed without error")

print("== 5. save / reload adapter")
model.save_pretrained(f"{OUT}/smoke_adapter")
del model
import gc
gc.collect()
torch.cuda.empty_cache()
from peft import PeftModel
m2 = PeftModel.from_pretrained(
    __import__("transformers").AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb, device_map="auto", max_memory=MAXMEM),
    f"{OUT}/smoke_adapter")
m2.eval()
print("   reload OK")

print("== 6. code-surface scoring on one question (B3)")
@torch.no_grad()
def option_logprobs(model, prompt_text, option_texts):
    import torch.nn.functional as F
    p_ids = tok(prompt_text, add_special_tokens=False, return_tensors="pt").input_ids.to(model.device)
    outs = []
    for ot in option_texts:
        o_ids = tok(ot, add_special_tokens=False, return_tensors="pt").input_ids.to(model.device)
        ids = torch.cat([p_ids, o_ids], dim=1)
        lg = model(ids).logits.float()[0, :-1, :]
        tgt = ids[0, 1:]
        logp = F.log_softmax(lg, dim=-1).gather(1, tgt.unsqueeze(1)).squeeze(1)
        outs.append(float(logp[-o_ids.shape[1]:].sum()))
    return outs

q0 = qm.iloc[10]
opts = bundle[bundle.question_id == q0.question_id].sort_values("option_code")
codes = [str(int(c)) if float(c).is_integer() else str(c) for c in opts.option_code.tolist()]
lps = option_logprobs(m2, q0.formatted_prompt, codes)
import numpy as np
p = np.exp(np.array(lps) - max(lps)); p /= p.sum()
print(f"   Q={q0.question_id} codes={codes} probs={[round(x,3) for x in p]} sum={p.sum():.6f}")

print("== 7. HF push round-trip")
import time
probe = json.dumps({"smoke": "ok", "epoch": time.time()}, indent=2)
open(f"{OUT}/smoke_probe.json", "w").write(probe)
api.upload_file(path_or_fileobj=f"{OUT}/smoke_probe.json",
                path_in_repo="out/smoke_probe.txt", repo_id=REPO_ID, repo_type="dataset")
files = api.list_repo_files(REPO_ID, repo_type="dataset")
assert any("smoke_probe" in f for f in files), "pushed file not visible"
print("   push + list OK")

open(f"{OUT}/SMOKE_OK", "w").write("ok\n")
print("SMOKE_OK")
