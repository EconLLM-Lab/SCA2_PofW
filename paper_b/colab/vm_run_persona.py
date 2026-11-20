# VM-side: launch the C8 persona chain DETACHED: gate one original profile unit (G2), then score the
# country-named persona condition (G1 spec pin and G3 base parity run inside vm_score_t4.py before any persona).
#   colab exec -s pb-p -f paper_b/colab/vm_run_persona.py --timeout 120
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
print("persona chain:", [(n, a, e) for n, a, e in SPL.persona_steps()])
V.launch_detached(SPL.persona_steps())
