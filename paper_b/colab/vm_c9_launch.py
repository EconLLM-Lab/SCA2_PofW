# VM-side launcher for C9-4 experiment A (adapter + persona). Starts vm_c9_adapter_persona.py DETACHED in the
# cohort-1 configuration (SCA2_PB_PROTOCOL=cohort1, SCA2_PB_UNITS=countries), so the resolver reads
# adapters/<CC> and never a bank-2 path. Run only after PROVISION_DONE and with HF_TOKEN set in this kernel:
#   colab exec -s pb-c9 -f paper_b/colab/vm_c9_launch.py --timeout 120
import hashlib
import importlib
import sys
from pathlib import Path

REPO = "/content/SCA2_PofW"
sys.path[:0] = [f"{REPO}/paper_b/colab", f"{REPO}/paper_b"]
sys.modules.pop("vm_fact_common", None)
importlib.invalidate_caches()
import vm_fact_common as V  # noqa: E402

COHORT1 = {"SCA2_PB_PROTOCOL": "cohort1", "SCA2_PB_UNITS": "countries"}
STEPS = [("c9a_adapter_persona", ["paper_b/colab/vm_c9_adapter_persona.py"], COHORT1),   # experiment A
         ("c9b_label_recovery", ["paper_b/colab/vm_c9_label_recovery.py"], COHORT1)]      # experiment B
for _, args, _ in STEPS:
    print("driver", args[0], "sha256:", hashlib.sha256((Path(REPO) / args[0]).read_bytes()).hexdigest())
print("children will see HF_TOKEN:", "HF_TOKEN" in V.child_env())
V.launch_detached(STEPS)     # sequential; a failed step does not stop the next
print("C9_LAUNCHED")
