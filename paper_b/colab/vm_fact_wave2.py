# VM-side: factorial wave 2, DETACHED (survives the client).
# colab exec -s pb-b -f paper_b/colab/vm_fact_wave2.py --timeout 120
import sys; sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab")
from vm_fact_common import launch_detached
launch_detached([("fact_wave2", ["paper_b/run_cohort.py", "--wave", "2"], {})])
