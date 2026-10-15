# VM-side: bank-2 shared reference cache + gates for the 64 profile units (GPU).
# colab exec -s pb-a -f paper_b/colab/vm_fact_refcache.py --timeout 5400
import sys; sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab")
from vm_fact_common import run
rc = run(["paper_b/verify_gates.py", "--scan-text"], "fact_gates")
raise SystemExit(rc or run(["paper_b/compute_ref_cache.py"], "fact_refcache"))
