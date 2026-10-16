# VM-side: factorial wave 1, DETACHED (survives the client), then the one-unit training-noise replicate.
# colab exec -s pb-a -f paper_b/colab/vm_fact_wave1.py --timeout 120
import sys; sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab")
from vm_fact_common import launch_detached
launch_detached([
    ("fact_wave1", ["paper_b/run_cohort.py", "--wave", "1"], {}),
    ("fact_replicate_r1", ["paper_b/run_cohort.py", "--countries", "P_1_0_1_1_0_1"], {"SCA2_PB_REPLICATE": "r1"}),
])
