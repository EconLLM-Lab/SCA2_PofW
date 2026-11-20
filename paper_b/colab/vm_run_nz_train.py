# VM-side: launch the near-zero TRAINING chain DETACHED (card T5): prepare the four training files, then train and
# upload the four adapters (refit GBR, COL; control GBR, COL).
#   colab exec -s pb-nz -f paper_b/colab/vm_run_nz_train.py --timeout 120
# Run it only after vm_nearzero_boot.py printed NEARZERO BOOT OK and the token is set in this kernel.
import importlib
import subprocess
import sys

REPO = "/content/SCA2_PofW"
sys.path[:0] = [f"{REPO}/paper_b/colab", f"{REPO}/paper_b"]
for mod in ("vm_fact_common", "score_plan", "protocol_bank2"):
    sys.modules.pop(mod, None)
importlib.invalidate_caches()
import vm_fact_common as V  # noqa: E402
import score_plan as SPL  # noqa: E402

print("VM HEAD:", subprocess.check_output(["git", "-C", REPO, "log", "-1", "--format=%H %s"]).decode().strip())
print("children will see HF_TOKEN:", "HF_TOKEN" in V.child_env())
V.launch_detached(SPL.nearzero_train_steps())
