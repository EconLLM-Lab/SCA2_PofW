# VM-side: factorial wave 2 (last 32 of 64 profile units, resumable).
# colab exec -s pb-b -f paper_b/colab/vm_fact_wave2.py --timeout 36000
import sys; sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab")
from vm_fact_common import run
raise SystemExit(run(["paper_b/run_cohort.py", "--wave", "2"], "fact_wave2"))
