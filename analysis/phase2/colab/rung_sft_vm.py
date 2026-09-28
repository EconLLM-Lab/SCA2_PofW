#!/usr/bin/env python3
"""rung_sft_vm.py v2.1 — Rung-mixture pilot, VM-side runner (repo-versioned).

Spec : analysis/phase2/RUNG_MIXTURE_SPEC.md (v1.2.1, frozen 2026-08-22)
Host : Colab T4. Inputs: /content/rung_mix/*.jsonl + wvs_scoring_bundle.parquet
Out  : /content/out/{adapter_rung_±k/, rung_pmfs.csv, gate_2_3_report.json,
       run_manifest.json}. Each milestone is pushed to HF dataset repo
       Bonorinoa/sca2-rung-mix so a mid-run death costs only the in-flight step.

Fixes vs the failed 2026-08-22 v1 launch (audit ledger in spec v1.1; mixer formula superseded by v1.2):
  B1 peft order: prepare_model_for_kbit_training BEFORE get_peft_model + hard
     trainable-param assert (v1 froze the LoRA -> zero-trainable-param crash).
  B2 SFT wrapper: shared canonical PRE + scenario + "\\n\\nAnswer:" — the
     per-question option-list suffix is NEVER welded onto training text.
  B3 PMFs scored on option CODES under verbatim formatted_prompt (same surface
     as every banked arm); SFT targets stay free-text variant responses.
  B4 shared 120-prompt holdout (built by 20_build_rung_datasets.py v1.1).
  B6 add_special_tokens=False everywhere (text already carries BOS literally).
  B7 this file is version-controlled; its md5 goes into the run manifest.
  B9 get_peft_model wraps in place: del model AND base after each save, then
     pull any Hub-resident adapter down so a fresh VM can resume mid-ladder.
"""
import gc
import hashlib
import itertools
import json
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd
import torch
from scipy.stats import mannwhitneyu, spearmanr

t0 = time.time()
def log(m):
    print(f"[{time.time()-t0:7.0f}s] {m}", flush=True)

RUNNER_MD5 = hashlib.md5(open(__file__, "rb").read()).hexdigest()
log(f"runner md5: {RUNNER_MD5}")

BASE = "/content/rung_mix"
OUT = "/content/out"
os.makedirs(OUT, exist_ok=True)
RUNGS = [-3, -2, -1, 1, 2, 3]
SEED = 20260822
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
REPO_ID = "Bonorinoa/sca2-rung-mix"
MAX_LEN = 768

if not os.environ.get("HF_TOKEN"):
    log("FATAL: HF_TOKEN not set — chain setenv before launching this script.")
    sys.exit(1)
os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", os.environ["HF_TOKEN"])

import transformers
import peft
import bitsandbytes  # noqa: F401  (presence check)
from huggingface_hub import HfApi, login, snapshot_download
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          BitsAndBytesConfig, DataCollatorForSeq2Seq,
                          TrainingArguments, Trainer, set_seed)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel

login(token=os.environ["HF_TOKEN"], add_to_git_credential=False)

log(f"versions: transformers={transformers.__version__} peft={peft.__version__} "
    f"torch={torch.__version__}")
set_seed(SEED)
API = HfApi(token=os.environ["HF_TOKEN"])

def vram(tag):
    if not torch.cuda.is_available():
        log(f"vram {tag}: no cuda")
        return
    alloc = torch.cuda.memory_allocated() / 1e9
    reserved = torch.cuda.memory_reserved() / 1e9
    log(f"vram {tag}: alloc={alloc:.2f}G reserved={reserved:.2f}G")

def push_file(path, path_in_repo):
    try:
        API.upload_file(path_or_fileobj=path, path_in_repo=path_in_repo,
                        repo_id=REPO_ID, repo_type="dataset")
        log(f"hf-push ok: {path_in_repo}")
    except Exception as e:  # non-fatal: VM copy survives; retry logic upstream
        log(f"hf-push FAILED ({path_in_repo}): {type(e).__name__}: {e}")

def push_folder(folder, path_in_repo):
    try:
        API.upload_folder(folder_path=folder, path_in_repo=path_in_repo,
                          repo_id=REPO_ID, repo_type="dataset")
        log(f"hf-push ok: {path_in_repo}/")
    except Exception as e:
        log(f"hf-push FAILED ({path_in_repo}/): {type(e).__name__}: {e}")

# ---- tokenizer + canonical wrapper ------------------------------------------
tok = AutoTokenizer.from_pretrained(MODEL_NAME)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

bundle = pd.read_parquet(f"{BASE}/wvs_scoring_bundle.parquet")
qs_meta = bundle.drop_duplicates("question_id")

pres, tails = set(), set()
for _, r in qs_meta.iterrows():
    qt, fp = r.question_text, r.formatted_prompt
    assert fp.count(qt) == 1, f"question_text not unique in formatted_prompt ({r.question_id})"
    pre, suf = fp.split(qt, 1)
    ANS = "\n\nAnswer:"
    assert suf.count(ANS) == 1 and len(suf) > len(ANS), \
        f"unexpected eval suffix shape ({r.question_id})"
    mid, tail = suf.split(ANS, 1)
    pres.add(pre); tails.add(tail)
assert len(pres) == 1, f"PRE differs across questions: {len(pres)} variants"
assert len(tails) == 1, f"TAIL differs across questions: {len(tails)} variants"
PRE, TAIL = pres.pop(), tails.pop()
log(f"wrapper: PRE={len(PRE)}ch TAIL={len(TAIL)}ch shared across all {len(qs_meta)} "
    f"questions; BOS literal -> add_special_tokens=False everywhere")

def sft_wrap(scenario: str) -> str:
    """B2/B6: training context mirrors the canonical eval surface exactly:
    shared PRE + text + '\\n\\nAnswer:' + constant generation TAIL."""
    return PRE + scenario.strip() + "\n\nAnswer:" + TAIL

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.float16,
                         bnb_4bit_use_double_quant=True)

def fresh_base():
    gpu_mb = torch.cuda.get_device_properties(0).total_memory // (1024 ** 2)
    m = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb, device_map="auto",
        max_memory={0: f"{int(gpu_mb * 0.92)}MB"})
    m.eval()
    return m

def adapter_dir(k):
    return f"{OUT}/adapter_rung_{k:+d}"

def adapter_marker(k):
    return os.path.join(adapter_dir(k), "adapter_model.safetensors")

def pull_adapter_from_hub(k):
    """Copy adapters/adapter_rung_±k/ from the dataset repo into OUT/."""
    tag = f"adapters/adapter_rung_{k:+d}"
    dest = adapter_dir(k)
    log(f"rung {k:+d}: pulling {tag}/ from hub")
    cache = snapshot_download(repo_id=REPO_ID, repo_type="dataset",
                              allow_patterns=[f"{tag}/*"],
                              token=os.environ["HF_TOKEN"])
    src = os.path.join(cache, tag)
    assert os.path.isdir(src), f"hub pull produced no directory {src}"
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    assert os.path.exists(adapter_marker(k)), f"hub pull missing safetensors for rung {k:+d}"
    log(f"rung {k:+d}: local adapter ready ({os.path.getsize(adapter_marker(k))} bytes)")

# ---- B1-correct SFT stage ----------------------------------------------------
LORA = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                  target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                  task_type="CAUSAL_LM")
collator = DataCollatorForSeq2Seq(tokenizer=tok, model=None, padding=True,
                                  label_pad_token_id=-100)

def load_rows(k, split):
    return [json.loads(l) for l in open(f"{BASE}/sft_rung_{k:+d}_{split}.jsonl")]

def make_ds(k):
    rows = load_rows(k, "train")
    ds = {"input_ids": [], "labels": []}
    for r in rows:
        p_ids = tok(sft_wrap(r["prompt"]), add_special_tokens=False,
                    truncation=True, max_length=MAX_LEN).input_ids
        t_ids = tok(r["generated_response"].strip(), add_special_tokens=False,
                    truncation=True, max_length=64).input_ids
        t_ids = t_ids + [tok.eos_token_id]
        ds["input_ids"].append(p_ids + t_ids)
        # completion-only loss: prompt tokens masked, response (+EOS) supervised
        ds["labels"].append([-100] * len(p_ids) + t_ids)
    import datasets as _hfds
    return _hfds.Dataset.from_dict(ds)

hub_files = set(API.list_repo_files(REPO_ID, repo_type="dataset"))
for k in RUNGS:
    tag = f"adapters/adapter_rung_{k:+d}"
    done_locally = os.path.exists(adapter_marker(k))
    done_on_hub = any(f.startswith(tag + "/") and f.endswith("safetensors") for f in hub_files)
    if done_locally or done_on_hub:
        log(f"rung {k:+d}: adapter already exists ({'local' if done_locally else 'hub'}) — skipping SFT")
        if not done_locally:
            pull_adapter_from_hub(k)
        continue
    log(f"=== SFT rung {k:+d}")
    vram("before-load")
    base = fresh_base()
    base = prepare_model_for_kbit_training(base)          # B1: freeze quantized base FIRST
    model = get_peft_model(base, LORA)                     # THEN attach trainable LoRA
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert n_trainable > 1_000_000, f"B1 guard tripped: {n_trainable} trainable params"
    log(f"trainable params: {n_trainable/1e6:.1f}M")
    vram("after-peft")
    args = TrainingArguments(
        output_dir=f"{OUT}/tmp_{k:+d}", per_device_train_batch_size=2,
        gradient_accumulation_steps=4, num_train_epochs=3, learning_rate=1e-4,
        lr_scheduler_type="cosine", warmup_ratio=0.03, logging_steps=25,
        fp16=True, optim="paged_adamw_8bit", report_to=[], save_strategy="no",
        seed=SEED, disable_tqdm=True)
    Trainer(model=model, args=args, train_dataset=make_ds(k),
            data_collator=collator).train()
    model.save_pretrained(adapter_dir(k))
    log(f"saved adapter_rung_{k:+d}")
    push_folder(adapter_dir(k), tag)
    # B9: get_peft_model wraps in place — drop BOTH handles before the next 8B load
    del model, base
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    vram("after-release")

missing = [k for k in RUNGS if not os.path.exists(adapter_marker(k))]
assert not missing, f"adapters missing locally after SFT stage: {missing}"
log("all six adapters present locally — entering Gate 2")

# ---- scoring helpers (B3/B6 surface) -----------------------------------------
@torch.no_grad()
def option_logprobs(model, prompt_text, option_texts):
    """Summed completion-token logprob per option; text already carries BOS.

    Matches protocols/sca2_2x2_inference_runner.py: gather on the 2-D
    [seq-1, vocab] surface, then sum the last n_option tokens.
    """
    import torch.nn.functional as F
    p_ids = tok(prompt_text, add_special_tokens=False,
                return_tensors="pt").input_ids.to(model.device)
    outs = []
    for ot in option_texts:
        o_ids = tok(ot, add_special_tokens=False,
                    return_tensors="pt").input_ids.to(model.device)
        ids = torch.cat([p_ids, o_ids], dim=1)
        lg = model(ids).logits.float()[0, :-1, :]
        tgt = ids[0, 1:]
        logp = F.log_softmax(lg, dim=-1).gather(1, tgt.unsqueeze(1)).squeeze(1)
        outs.append(float(logp[-o_ids.shape[1]:].sum()))
    return outs

def fresh_adapter(k):
    m = fresh_base()
    m = PeftModel.from_pretrained(m, adapter_dir(k))
    m.eval()
    return m

# ---- GATE 2: purity on the SHARED holdout (fully paired, n=120) --------------
log("=== GATE 2 (shared holdout, uncapped)")
choices, margins = {}, {}
for k in RUNGS:
    m = fresh_adapter(k)
    rows = load_rows(k, "holdout")
    ch, mg = {}, {}
    for i, r in enumerate(rows):
        wp = sft_wrap(r["prompt"])
        a, b = option_logprobs(m, wp, [r["response_A_original"], r["response_B_original"]])
        ch[r["original_index"]] = int(a > b)
        mg[r["original_index"]] = abs(a - b)
        if (i + 1) % 40 == 0:
            log(f"  gate2 rung {k:+d}: {i+1}/{len(rows)}")
    choices[k], margins[k] = ch, mg
    del m
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    vram(f"after-gate2-{k:+d}")

gate = {"choice_agreement": {}, "margin_rho": {}, "n_paired": None}
for sign in (1, -1):
    ks = [sign * j for j in (1, 2, 3)]
    for hi, lo in itertools.combinations(ks, 2):
        common = sorted(set(choices[hi]) & set(choices[lo]))
        gate["choice_agreement"][f"{hi:+d}v{lo:+d}"] = float(np.mean(
            [choices[hi][i] == choices[lo][i] for i in common]))
        gate["margin_rho"][f"{lo:+d}<{hi:+d}"] = float(spearmanr(
            [margins[lo][i] for i in common],
            [margins[hi][i] for i in common]).statistic)
        gate["n_paired"] = len(common)
gate["gate_2_pass"] = bool(all(v >= 0.85 for v in gate["choice_agreement"].values())
                           and all(r >= 0.5 for r in gate["margin_rho"].values()))
# Persist per-prompt margins so the |k|-vs-margin reading of Gate 2 can be
# audited locally without another GPU pass (spec wording vs pairwise rho).
raw_path = f"{OUT}/gate2_raw.json"
json.dump({"choices": {str(k): v for k, v in choices.items()},
           "margins": {str(k): v for k, v in margins.items()}},
          open(raw_path, "w"))
push_file(raw_path, "out/gate2_raw.json")
json.dump(gate, open(f"{OUT}/gate2_partial.json", "w"), indent=2)
push_file(f"{OUT}/gate2_partial.json", "out/gate2_partial.json")
log("gate2 agreement: " + json.dumps(gate["choice_agreement"]))
log("gate2 margin rho: " + json.dumps(gate["margin_rho"]) +
    f" | paired n={gate['n_paired']}")

# ---- rung PMFs on option CODES (B3) ------------------------------------------
all_rows = []
for k in RUNGS:
    m = fresh_adapter(k)
    rows = []
    for _, q in qs_meta.iterrows():
        opts = bundle[bundle.question_id == q.question_id].sort_values("option_code")
        codes = [str(int(c)) if float(c).is_integer() else str(c)
                 for c in opts.option_code.tolist()]
        lps = option_logprobs(m, q.formatted_prompt, codes)
        e = np.exp(np.array(lps) - np.max(lps))
        p = e / e.sum()
        rows.extend({"rung": k, "question_id": q.question_id,
                     "option_code": int(float(c)), "prob": float(pi)}
                    for c, pi in zip(opts.option_code.tolist(), p))
    all_rows.extend(rows)
    pd.DataFrame(all_rows).to_csv(f"{OUT}/rung_pmfs.csv", index=False)  # incremental
    push_file(f"{OUT}/rung_pmfs.csv", "out/rung_pmfs.csv")
    log(f"pmfs rung {k:+d} done ({len(rows)} option cells)")
    del m
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    vram(f"after-pmf-{k:+d}")

# ---- GATE 3: ladder geometry --------------------------------------------------
pmfs = pd.DataFrame(all_rows)
wide = pmfs.pivot_table(index=["question_id", "option_code"], columns="rung",
                        values="prob")
def tvd(a, b):
    return 0.5 * float((wide[a] - wide[b]).abs().sum())
adj = [tvd(i, j) for i, j in [(1, 2), (2, 3), (-1, -2), (-2, -3)]]
cross = [tvd(i, j) for i in (1, 2, 3) for j in (-1, -2, -3)]
u = mannwhitneyu(adj, cross, alternative="greater")
gate["adjacent_vs_cross_tvd"] = {"median_adjacent": float(np.median(adj)),
                                 "median_cross": float(np.median(cross)),
                                 "p_one_sided": float(u.pvalue)}
gate["gate_3_pass"] = bool(u.pvalue < 0.05)
json.dump(gate, open(f"{OUT}/gate_2_3_report.json", "w"), indent=2)
push_file(f"{OUT}/gate_2_3_report.json", "out/gate_2_3_report.json")
log("GATE2 " + ("PASS" if gate["gate_2_pass"] else "FAIL") +
    " | GATE3 " + ("PASS" if gate["gate_3_pass"] else "FAIL"))

# ---- manifest ------------------------------------------------------------------
manifest = {
    "runner_md5": RUNNER_MD5,
    "spec_version": "v1.2.1",
    "seed": SEED,
    "versions": {"transformers": transformers.__version__, "peft": peft.__version__,
                 "torch": torch.__version__},
    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
    "gate_2_pass": gate.get("gate_2_pass"),
    "gate_3_pass": gate.get("gate_3_pass"),
}
json.dump(manifest, open(f"{OUT}/run_manifest.json", "w"), indent=2)
push_file(f"{OUT}/run_manifest.json", "out/run_manifest.json")
log("ALL DONE")
