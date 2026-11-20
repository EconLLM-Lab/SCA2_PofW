import os, shutil, subprocess, sys
REPO_DIR = "/content/SCA2_PofW"
DATA = "/content/pb_data"
os.makedirs(DATA, exist_ok=True)

# ---- fetch the shared reference cache from the HF Hub (no Drive involved) ----
from huggingface_hub import hf_hub_download
src = hf_hub_download(repo_id="Bonorinoa/SCA2-paper-b-adapters",
                      filename="inputs/shared_reference_logps.jsonl", repo_type="dataset")
dst = os.path.join(DATA, "shared_reference_logps.jsonl")
shutil.copy(src, dst)
print("ref cache ready:", os.path.getsize(dst), "bytes")

env = dict(os.environ, SCA2_PB_DATA_ROOT=DATA, PYTHONUNBUFFERED="1",
           ACCELERATE_MIXED_PRECISION="fp16",
           PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True", TRANSFORMERS_NO_BF16="1")

LOG = os.path.join(DATA, "finish8.log")
with open(LOG, "a") as lg:
    lg.write("\n=== finish8 start ===\n")
    lg.flush()
    r = subprocess.run([sys.executable, "paper_b/run_cohort.py", "--countries",
                        "GRC", "GTM", "IDN", "IND", "IRN", "IRQ", "JOR", "JPN"],
                       cwd=REPO_DIR, env=env, stdout=lg, stderr=subprocess.STDOUT)
print("finish8 rc:", r.returncode)
