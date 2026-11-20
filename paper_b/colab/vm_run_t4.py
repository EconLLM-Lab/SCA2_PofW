# VM-side: launch the card-T4 chain DETACHED: gate the replicate adapter, then score the three T4 conditions.
#   colab exec -s pb-e -f paper_b/colab/vm_run_t4.py --timeout 120
# Run it only after provisioning printed PROVISION_DONE and the HF token is set in this kernel. The helper
# modules are purged first (the kernel caches them, and with them the environment at their first import).
import importlib
import subprocess
import sys

REPO = "/content/SCA2_PofW"
sys.path[:0] = [f"{REPO}/paper_b/colab", f"{REPO}/paper_b"]
for mod in ("vm_fact_common", "score_plan"):
    sys.modules.pop(mod, None)
importlib.invalidate_caches()
import vm_fact_common as V  # noqa: E402
import score_plan as SPL  # noqa: E402

print("VM HEAD:", subprocess.check_output(["git", "-C", REPO, "log", "-1", "--format=%H %s"]).decode().strip())
print("children will see HF_TOKEN:", "HF_TOKEN" in V.child_env())
V.launch_detached(SPL.t4_steps())
