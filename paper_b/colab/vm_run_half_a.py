# Relaunch half A's scoring chain with a FRESH vm_fact_common.
#
# Needed when an env var (the HF token) is set AFTER vm_fact_common was first imported in this kernel:
# the module stays in sys.modules, so its environment snapshot is stale. Purging the module here makes
# the driver import it again and pick up the current os.environ.
import importlib
import runpy
import sys

REPO = "/content/SCA2_PofW"
sys.path[:0] = [f"{REPO}/paper_b/colab", f"{REPO}/paper_b"]
for mod in ("vm_fact_common", "vm_score_half_a", "score_plan"):
    sys.modules.pop(mod, None)
importlib.invalidate_caches()
import vm_fact_common as V  # noqa: E402
print("children will see HF_TOKEN:", "HF_TOKEN" in V.child_env())
runpy.run_path(f"{REPO}/paper_b/colab/vm_score_half_a.py", run_name="__main__")
