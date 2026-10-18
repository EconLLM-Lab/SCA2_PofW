# VM-side: launch the near-zero GATE + SCORING chain DETACHED (card T5): one gate per adapter, then the strict
# scoring of the four adapters under bank2-nearzero-strict-v1-20261018.
#   colab exec -s pb-nz -f paper_b/colab/vm_run_nz_score.py --timeout 120
# Run it only after the four adapters are on the Hub, `nearzero_adapter_revision` is pinned in
# score_plan_pins.json, and the VM checkout contains that pin (vm_sync.py, then check the printed HEAD).
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

rev = SPL.adapter_revision_for("nearzero_strict_v1")     # raises if the pin is not in this checkout
print("VM HEAD:", subprocess.check_output(["git", "-C", REPO, "log", "-1", "--format=%H %s"]).decode().strip())
print("near-zero adapter revision:", rev)
print("children will see HF_TOKEN:", "HF_TOKEN" in V.child_env())
V.launch_detached(SPL.nearzero_score_steps(rev))
