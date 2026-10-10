# VM-side preflight: token-free checks (python, GPU, Drive, repo, gates).
# colab exec -s pb-a -f paper_b/colab/vm_preflight.py --timeout 600
import os, subprocess, sys

REPO = "/content/SCA2_PofW"
print("python:", sys.version.split()[0])
try:
    import torch
    print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available(),
          "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
except Exception as e:  # noqa: BLE001
    print("torch import failed:", e)

print("drive mounted:", os.path.isdir("/content/drive/MyDrive"))
print("repo:", subprocess.check_output(["git", "-C", REPO, "log", "-1", "--oneline"]).decode().strip())
print("HF_TOKEN env present:", bool(os.environ.get("HF_TOKEN")))

print("-" * 50, "\nverify_gates.py:")
rc = subprocess.call([sys.executable, "paper_b/verify_gates.py"], cwd=REPO)
print("gates rc:", rc)
print("PREFLIGHT OK" if rc == 0 else "PREFLIGHT FAILED")
