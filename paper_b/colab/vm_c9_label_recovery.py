# VM-side driver for card C9-4 experiment B: held-out synthetic-label recovery on the 42 cohort-1 adapters.
#   For every cohort country, the 132 held-out training-scenario pairs (the shared eval split of
#   paper_b/prepare_data.py: make_shared_split(TRAIN_FRAC=0.80, SEED=42) over the bank-1 prompts) are scored as
#   sequence log-probabilities of the chosen and the rejected completion, under that country's adapter and under
#   the base model (the reference). The recipe is paper_b/compute_ref_cache.py's seq_logprob, i.e. the exact
#   recipe that produced the training reference log-probs: chat template + build_user_prompt, prompt left-truncated
#   to 256 tokens, completion truncated to 256, summed token log-probs.
#   Outputs per country: runs/<RUN_ID>/logps/<CC>.jsonl with rows
#   {i, ref_chosen, ref_rejected, adapter_chosen, adapter_rejected}; the statistics are computed on the laptop.
#
# Gates before any country is scored (failure exits non-zero, nothing scored):
#   GB1  the base model reproduces the banked cohort-1 reference cache (cohort1/shared_reference_logps.jsonl) on
#        the first 20 train pairs within 1e-2 nats.
#   GB2  the ARG adapter changes the log-probs (max |delta| > 1e-3), and disabling it gives back the base.
# Run as a child with SCA2_PB_PROTOCOL=cohort1 SCA2_PB_UNITS=countries (vm_c9_launch_b.py).
import hashlib
import json
import os
import sys
import time
from pathlib import Path

REPO = Path("/content/SCA2_PofW")
sys.path[:0] = [str(REPO / "paper_b"), str(REPO / "paper_b" / "colab")]

RUN_ID = "label-recovery-cohort1-v1-20261019"
COHORT1_REVISION = "7550fd4cfe514470bb8d80918a43c9ae424d26b5"
ARTIFACTS_REPO = "Bonorinoa/SCA2-paper-b-artifacts"
REF_CACHE = "cohort1/shared_reference_logps.jsonl"
BANK_RUN_ID = "gps_sign_relabel_all_20260816_004545Z"
N_EVAL = 132
GATE_COUNTRY = "ARG"
GB1_N, GB1_TOL = 20, 1e-2
MIN_ADAPTER_EFFECT = 1e-3


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("REFUSING: HF_TOKEN is not set"); return 2
    if os.environ.get("SCA2_PB_PROTOCOL") == "bank2" or os.environ.get("SCA2_PB_UNITS") != "countries":
        print("REFUSING: needs the cohort-1 configuration (not bank2, SCA2_PB_UNITS=countries)"); return 2

    import torch
    import config as C
    import eval_config as E
    import score_runtime as R
    from lib import build_user_prompt, load_country, make_shared_split, response_pair, verify_shared_questions
    from huggingface_hub import HfApi, hf_hub_download
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    countries = sorted(C.COHORT)
    if len(countries) != 42 or C.hub_adapter_path(GATE_COUNTRY) != f"adapters/{GATE_COUNTRY}":
        print("REFUSING: not the 42-country cohort-1 configuration"); return 2
    api = HfApi(token=token)
    driver_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    # ---- the shared split, exactly as prepare_data.py builds it
    by_prompt_all = {cc: load_country(C.BANK_DIR / C.BANK_FILE.format(cc=cc))[1] for cc in C.COHORT}
    all_prompts = verify_shared_questions(by_prompt_all, C.COHORT[0])
    train_prompts, eval_prompts = make_shared_split(all_prompts, C.TRAIN_FRAC, C.SEED)
    eval_sorted = sorted(eval_prompts)
    if len(eval_sorted) != N_EVAL:
        print(f"REFUSING: {len(eval_sorted)} eval prompts, expected {N_EVAL}"); return 2
    shared_pairs = {p: response_pair(by_prompt_all[C.COHORT[0]][p]) for p in all_prompts}
    print(f"split: {len(train_prompts)} train / {len(eval_sorted)} eval | bank dir {C.BANK_DIR.name}")

    # ---- the banked reference cache (for GB1)
    man = json.loads(Path(hf_hub_download(ARTIFACTS_REPO, REF_CACHE.replace(".jsonl", "_manifest.json"),
                                          repo_type="dataset", token=token)).read_text())
    if man.get("bank_run_id") != BANK_RUN_ID:
        print(f"REFUSING: reference cache bank {man.get('bank_run_id')!r} != {BANK_RUN_ID}"); return 2
    cache = {}
    for line in open(hf_hub_download(ARTIFACTS_REPO, REF_CACHE, repo_type="dataset", token=token)):
        if line.strip():
            r = json.loads(line)
            cache[(r["prompt"], r["completion"])] = r["ref_logp"]

    # ---- model: compute_ref_cache.py's loader and seq_logprob
    t0 = time.time()
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(C.MODEL_NAME, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    base = AutoModelForCausalLM.from_pretrained(C.MODEL_NAME, quantization_config=bnb, device_map={"": 0},
                                                torch_dtype=torch.float16, low_cpu_mem_usage=True)
    base.eval()
    print(f"base loaded in {time.time() - t0:.0f} s")

    def fmt(prompt_text):
        return tok.apply_chat_template([{"role": "user", "content": build_user_prompt(prompt_text)}],
                                       tokenize=False, add_generation_prompt=True)

    @torch.no_grad()
    def seq_logprob(model, prompt_text, completion_text):
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

    # ---- GB1: reproduce the banked reference cache on the first train pairs
    wanted = [(p, c) for p in sorted(train_prompts) for c in sorted(shared_pairs[p])][:GB1_N]
    gaps = [abs(seq_logprob(base, p, c) - cache[(p, c)]) for p, c in wanted]
    gb1 = {"n": len(gaps), "max_abs_gap": max(gaps), "tol": GB1_TOL, "pass": max(gaps) <= GB1_TOL}
    print(f"GB1 reference-cache parity: {json.dumps(gb1)}")

    # ---- base log-probs on the eval completions (country-independent)
    t = time.time()
    base_lp = {(p, c): seq_logprob(base, p, c) for p in eval_sorted for c in sorted(shared_pairs[p])}
    print(f"base eval log-probs: {len(base_lp)} in {time.time() - t:.0f} s")

    # ---- GB2: adapter acts; switchback
    adir, source = R.resolve_adapter(GATE_COUNTRY, COHORT1_REVISION, E.ADAPTER_CACHE_DIR)
    peft = PeftModel.from_pretrained(base, str(adir), adapter_name=GATE_COUNTRY, is_trainable=False)
    peft.set_adapter(GATE_COUNTRY)
    probe = [(p, c) for p in eval_sorted[:5] for c in sorted(shared_pairs[p])]
    effect = max(abs(seq_logprob(peft, p, c) - base_lp[(p, c)]) for p, c in probe)
    with peft.disable_adapter():
        back = max(abs(seq_logprob(peft, p, c) - base_lp[(p, c)]) for p, c in probe)
    gb2 = {"country": GATE_COUNTRY, "adapter_sha256": R.adapter_sha256(adir), "adapter_source": source,
           "effect_max_abs": effect, "effect_min": MIN_ADAPTER_EFFECT, "switchback_max_abs": back,
           "pass": bool(effect > MIN_ADAPTER_EFFECT and back <= GB1_TOL)}
    print(f"GB2 adapter gate: {json.dumps(gb2)}")

    def upload_bytes(data, path, msg):
        api.upload_file(path_or_fileobj=data, path_in_repo=f"runs/{RUN_ID}/{path}", repo_id=ARTIFACTS_REPO,
                        repo_type="dataset", commit_message=f"{RUN_ID}: {msg}")

    gates = {"run_id": RUN_ID, "driver_sha256": driver_sha, "adapter_revision": COHORT1_REVISION,
             "bank_run_id": BANK_RUN_ID, "n_eval": N_EVAL, "GB1": gb1, "GB2": gb2,
             "gate_pass": bool(gb1["pass"] and gb2["pass"]), "packages": R.package_versions()}
    upload_bytes(json.dumps(gates, indent=2).encode(), "gates.json", "gates")
    if not gates["gate_pass"]:
        print("GATES FAILED: no country scored"); return 3
    print("GATES PASS")

    def present():
        return {f.rsplit("/", 1)[1][:-6] for f in api.list_repo_files(ARTIFACTS_REPO, repo_type="dataset")
                if f.startswith(f"runs/{RUN_ID}/logps/") and f.endswith(".jsonl")}

    timings = {}
    for cc in countries:
        if cc in present():
            print(f"{cc}: on the Hub, skipped"); continue
        t = time.time()
        adir, source = R.resolve_adapter(cc, COHORT1_REVISION, E.ADAPTER_CACHE_DIR)
        if cc not in peft.peft_config:
            peft.load_adapter(str(adir), adapter_name=cc, is_trainable=False)
        peft.set_adapter(cc)
        rows = []
        for i, p in enumerate(eval_sorted):
            row = by_prompt_all[cc][p]
            rows.append({"i": i, "ref_chosen": base_lp[(p, row["chosen"])], "ref_rejected": base_lp[(p, row["rejected"])],
                         "adapter_chosen": seq_logprob(peft, p, row["chosen"]),
                         "adapter_rejected": seq_logprob(peft, p, row["rejected"])})
        data = "".join(json.dumps(r) + "\n" for r in rows).encode()
        upload_bytes(data, f"logps/{cc}.jsonl", f"{cc} held-out log-probs ({len(rows)} pairs)")
        back = hf_hub_download(ARTIFACTS_REPO, f"runs/{RUN_ID}/logps/{cc}.jsonl", repo_type="dataset",
                               token=token, force_download=True)
        if hashlib.sha256(Path(back).read_bytes()).hexdigest() != hashlib.sha256(data).hexdigest():
            print(f"REFUSING: {cc} readback sha256 mismatch"); return 4
        if cc != GATE_COUNTRY:
            peft.delete_adapter(cc)
        timings[cc] = round(time.time() - t, 1)
        print(f"{cc}: {len(rows)} pairs scored + read back from {source} in {timings[cc]} s")

    missing = [cc for cc in countries if cc not in present()]
    summary = {"run_id": RUN_ID, "driver_sha256": driver_sha, "units_expected": len(countries),
               "units_missing": missing, "unit_seconds": timings, "wall_seconds": round(time.time() - t0, 1)}
    upload_bytes(json.dumps(summary, indent=2).encode(), "run_summary.json", "run summary")
    print(f"C9B_DONE missing={len(missing)} {missing[:5]}")
    return 0 if not missing else 4


if __name__ == "__main__":
    sys.exit(main())
