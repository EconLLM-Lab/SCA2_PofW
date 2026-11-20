# VM-side setup: clone the cohort branch and install the pinned stack.
# Run on the Colab VM via:  colab exec -s pb-a -f paper_b/colab/vm_setup.py
import os, subprocess, sys

REPO = "/content/SCA2_PofW"
BRANCH = "feat/paper-b-cohort"
URL = "https://github.com/EconLLM-Lab/SCA2_PofW"

if not os.path.isdir(os.path.join(REPO, ".git")):
    subprocess.check_call(["git", "clone", "--branch", BRANCH, "--depth", "1", URL, REPO])
else:
    subprocess.check_call(["git", "-C", REPO, "fetch", "origin", BRANCH])
    subprocess.check_call(["git", "-C", REPO, "checkout", BRANCH])
    subprocess.check_call(["git", "-C", REPO, "reset", "--hard", f"origin/{BRANCH}"])
print("repo at:", subprocess.check_output(["git", "-C", REPO, "log", "-1", "--oneline"]).decode().strip())

STACK = ["transformers==4.46.3", "datasets==2.21.0", "accelerate==0.34.0",
         "trl==0.14.0", "peft==0.14.0", "huggingface_hub==0.36.2",
         "bitsandbytes==0.50.2", "safetensors>=0.4.3"]
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-U", *STACK])

import torch, transformers, trl, peft  # noqa: E402
print("torch", torch.__version__, "| cuda", torch.cuda.is_available(),
      "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no-gpu")
print("transformers", transformers.__version__, "| trl", trl.__version__, "| peft", peft.__version__)
print("bitsandbytes available:", transformers.utils.is_bitsandbytes_available())
print("SETUP OK" if torch.cuda.is_available() else "SETUP WARNING: no GPU")
