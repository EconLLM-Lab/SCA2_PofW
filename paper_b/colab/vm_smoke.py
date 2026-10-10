# VM-side smoke test: validate the whole GPU path cheaply before the real run.
# Run on the Colab VM via:  colab exec -s pb-a -f paper_b/colab/vm_smoke.py
import os, subprocess, sys, time

REPO = "/content/SCA2_PofW"
DRIVE = "/content/drive/MyDrive/SCA2_paper_b"
os.environ["SCA2_PB_DATA_ROOT"] = DRIVE
os.environ["ACCELERATE_MIXED_PRECISION"] = "fp16"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["TRANSFORMERS_NO_BF16"] = "1"
sys.path.insert(0, os.path.join(REPO, "paper_b"))

import torch  # noqa: E402
print("=" * 60)
print("1) CUDA:", torch.cuda.is_available(), "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
print("2) Drive mounted:", os.path.isdir("/content/drive/MyDrive"))
print("3) HF_TOKEN in env:", bool(os.environ.get("HF_TOKEN")))

# 4) data gates on the VM
print("=" * 60, "\n4) verify_gates.py")
r = subprocess.run([sys.executable, "paper_b/verify_gates.py"], cwd=REPO)
print("   gates rc:", r.returncode)

# 5) the expensive path: load the 4-bit base model and score TWO pairs
print("=" * 60, "\n5) two-pair reference pass (model load + forward)")
import config as C  # noqa: E402
from lib import build_user_prompt  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # noqa: E402

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
t0 = time.time()
tok = AutoTokenizer.from_pretrained(C.MODEL_NAME, use_fast=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(C.MODEL_NAME, quantization_config=bnb,
                                             device_map={"": 0}, torch_dtype=torch.float16,
                                             low_cpu_mem_usage=True)
model.eval()
print(f"   model loaded in {time.time()-t0:.1f}s")

def fmt(p):
    return tok.apply_chat_template([{"role": "user", "content": build_user_prompt(p)}],
                                   tokenize=False, add_generation_prompt=True)

@torch.no_grad()
def seq_logprob(p, c):
    pid = tok(fmt(p), add_special_tokens=False).input_ids[-C.MAX_PROMPT_TOKENS:]
    cid = tok(c, add_special_tokens=False).input_ids[:C.MAX_COMPLETION_TOKENS]
    ids = pid + cid
    lab = ([-100] * len(pid)) + cid
    it = torch.tensor([ids], device=model.device); lt = torch.tensor([lab], device=model.device)
    lp = torch.log_softmax(model(input_ids=it).logits, dim=-1)[:, :-1, :]
    sh = lt[:, 1:]; m = sh.ne(-100); g = sh.clone(); g[~m] = 0
    return float((lp.gather(-1, g.unsqueeze(-1)).squeeze(-1) * m).sum().detach().cpu())

import json  # noqa: E402
row = json.loads(open(os.path.join(C.BANK_DIR, C.BANK_FILE.format(cc="ARG"))).readline())
t1 = time.time()
v1 = seq_logprob(row["prompt"], row["response_a"])
v2 = seq_logprob(row["prompt"], row["response_b"])
dt = time.time() - t1
print(f"   two pairs in {dt:.1f}s ({dt/2:.2f}s/pair) -> {v1:.3f}, {v2:.3f}")
print(f"   extrapolated ref-cache ({1052} pairs): {1052*dt/2/60:.0f} min")

print("=" * 60)
print("SMOKE OK" if (r.returncode == 0 and dt > 0) else "SMOKE FAILED")
